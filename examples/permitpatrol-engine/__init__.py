"""Stateful code interpreter (Python) — `sandbox-code-interpreter-py`."""

async def main() -> None:
    import asyncio
    import os
    from solari_sandbox import SandboxClient

    async with SandboxClient(api_key=os.environ["SOLARI_API_KEY"], base_url="https://api.getsolari.com") as client:
        sandbox = await client.create(template="base", timeout_ms=5 * 60_000)
        await sandbox.connect()
        ctx = await sandbox.create_code_context("python")

        await sandbox.run_code("import math\nradius = 7", context_id=ctx)
        result = await sandbox.run_code(
            "area = math.pi * radius ** 2\n"
            "print(f'area = {area:.2f}')\n"
            "area\n",
            context_id=ctx,
        )
        if result.error:
            print("error:", result.error)
        else:
            for item in result.results:
                text = getattr(item, "text", None)
                if text:
                    print(f"  [{item.type}] {text.strip()}")
        await sandbox.kill()