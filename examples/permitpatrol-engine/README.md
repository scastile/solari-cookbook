# PermitPatrol engine — Solari example

A compact Solari example showing why the **Browser** and **Sandbox** products
pair well together: a real browser session fetches a public county
land-records portal, then a stateful Python kernel inside a sandbox parses
the raw HTML and prints structured rows.

## What it does

1. **Solari Browser** navigates to Delta Computer Systems' deeds & records
   search for Alcorn County, MS (FIPS `ms02`).
2. The page HTML is handed to a **Solari Sandbox** running a stateful
   Python code context.
3. The kernel parses rows with regex, prints the first five structured
   records as JSON.

This is the same browser→sandbox shape as the full
[github.com/scastile/permitpatrol](https://github.com/scastile/permitpatrol)
engine (300 lines + web layer + Stripe), shrunk to 60 lines so the
combination fits in one example.

## Run

```bash
pip install -r requirements.txt
export SOLARI_API_KEY=slr_live_...
python main.py
```

## Why this example exists

The Solari Cookbook has a *Browser* section and a *Sandbox* section. Most
real workloads need **both**. PermitPatrol is one shape:

- **Browser does the I/O** — fetches a page that's behind no auth but is
  too ugly to scrape with `requests` alone (table-in-table, server-rendered
  CGI from1997).
- **Sandbox does the diff** — the code interpreter's signature feature
  (variables survive between `run_code` calls) is exactly what an
  agent loop looks like, and is exactly what a "watch this list for new
  rows" engine needs.

## What Solari features this uses

- **Browser**: `Solari.launch()` returns a Playwright object. We do not
  need stealth, captcha solving, or residential proxy for this specific
  target — Delta's CGI is publicly readable. Keep them in your back
  pocket for sites that do.
- **Sandbox code interpreter**: `create_code_context("python")` gives us a
  named Python kernel; `run_code(..., context_id=ctx)` keeps state
  between calls. This is the cookbook's signature feature.
- **`kill()` not `close()`**: per the README, `close()` drops the local
  control channel but the VM keeps running until its idle timeout.
  `kill()` actually ends the VM.

## Gotchas we hit while writing this

- **Playwright version drift.** Solari's browser pool has hosts running
  both Playwright v1.59 and v1.62. The version installed via pip may not
  match the host you get assigned. The full engine retries with backoff
  to absorb this; this example doesn't retry, so a bad draw will error.
  See `requirements.txt` for the pin that worked for us.
- **`results` is a list, not a string.** `run_code` returns
  `result.results`, where each item has a `type` ("stdout" / "stderr" /
  "result") and `text`. Loop through them — don't `.stdout`.
- **Delta's HTML is lowercase.** The form-page `<tr>` and `<td>` tags are
  lowercase, even though the page-header tables use uppercase `<TR>`. The
  parser regex needs `re.IGNORECASE` on both the row-matcher and the
  cell-matcher. The colors that actually appear on data rows are
  `#FFFFFF` and `#C8D3DE` — anything else returns `[]`.
- **Hit the search endpoint, not the landing page.** The landing page at
  `/ms/<fips>/drlinkquerym2.html` is just the search form; it has zero
  `<TR>` rows. Submit a date query to `/cgi-iiy5/iimcgi06` to get the
  results table the kernel can parse.

## License

MIT.