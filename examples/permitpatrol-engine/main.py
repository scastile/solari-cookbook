"""PermitPatrol — Solari browser + sandbox code interpreter, in 60 lines.

A compact example showing why the cookbook's Browser and Sandbox products
pair well together: a real browser session fetches a public county
land-records portal, then a stateful Python kernel inside a sandbox parses
the raw HTML and prints structured rows as JSON.

We use Solari Browser to load Delta Computer Systems' deeds & records
search for Alcorn County, MS (FIPS `ms02`) — a 1997-era CGI app that no
modern scraper would touch directly. Then we hand the raw HTML to a
Solari Sandbox code interpreter that extracts structured rows.

This is the same browser→sandbox shape as the full PermitPatrol engine
(github.com/scastile/permitpatrol) — a 300-line version that adds
snapshot diffing, alert delivery, and a web layer on top of this loop.
"""

import asyncio
import os

from solari_browser import Solari
from solari_sandbox import SandboxClient

BASE_URL = "https://api.getsolari.com"

# We submit the search with a fixed date so we always get a non-empty
# results table. Without this, the landing page is just a search form
# with no <TR> rows for the kernel to parse.
DELTA_SEARCH_URL = (
    "https://www.deltacomputersystems.com/cgi-iiy5/iimcgi06"
    "?HTMCNTY=MS02&HTMSEARCH=BEGIN&HTMBASE=C"
    "&HTMMONTH=08&HTMDAY=29&HTMYEAR=2026"
)


async def fetch_html() -> str:
    """Drive the Solari browser to the Delta deeds portal and capture HTML."""
    async with Solari(api_key=os.environ["SOLARI_API_KEY"]) as solari:
        async with await solari.launch() as browser:
            page = await browser.new_page()
            await page.goto(DELTA_SEARCH_URL, wait_until="domcontentloaded", timeout=60_000)
            return await page.content()


async def extract_filings_with_kernel(html: str) -> None:
    """Hand the HTML to a sandbox Python kernel. The kernel parses rows in-state."""
    client = SandboxClient(api_key=os.environ["SOLARI_API_KEY"], base_url=BASE_URL)
    sandbox = await client.create(template="base", timeout_ms=5 * 60_000)
    print("sandbox:", sandbox.sandboxId)
    try:
        await sandbox.connect()
        # The cookbook's signature feature: a stateful code context. Variables
        # and imports survive between `run_code` calls. We push the HTML in
        # cell one, then parse it in cell two — the kernel owns `html`.
        ctx = await sandbox.create_code_context("python")
        await sandbox.run_code(f"html = {html!r}", context_id=ctx)
        result = await sandbox.run_code(
            "import re, json\n"
            "row_re = re.compile(r'<TR\\s+BGCOLOR=\"#(?:FFFFFF|C8D3DE)\">(.*?)</TR>', re.IGNORECASE | re.DOTALL)\n"
            "rows = row_re.findall(html)\n"
            "parsed = []\n"
            "for row in rows[:5]:\n"
            "    cells = re.findall(r'<TD[^>]*>(.*?)</TD>', row, re.IGNORECASE | re.DOTALL)\n"
            "    cells = [re.sub(r'<[^>]+>|&nbsp;', ' ', c, flags=re.IGNORECASE).strip() for c in cells]\n"
            "    if len(cells) >= 7 and cells[1][:1].isdigit():\n"
            "        parsed.append({'instrument': cells[1], 'grantor': cells[2], 'type': cells[4]})\n"
            "print(json.dumps(parsed, indent=2))\n",
            context_id=ctx,
        )
        if result.error:
            print("kernel error:", result.error)
            return
        for item in result.results:
            label = getattr(item, "type", "result")
            text = getattr(item, "text", None)
            if text:
                print(f"[{label}] {text.strip()}")
                return
    finally:
        # kill() ends the VM. Don't skip this — sandboxed VMs idle-bill
        # until timeout otherwise. (close() drops the local control channel
        # but leaves the VM running.)
        await sandbox.kill()


async def main() -> None:
    print(f"navigating to {DELTA_SEARCH_URL}")
    html = await fetch_html()
    print(f"fetched {len(html)} bytes of HTML")
    print("parsing via sandbox code interpreter ...")
    await extract_filings_with_kernel(html)


if __name__ == "__main__":
    asyncio.run(main())