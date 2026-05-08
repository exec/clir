import asyncio
from clir import ClirApp, option

app = ClirApp(name="async-demo")

@app.command()
@option("--url", default="https://example.com")
async def fetch(url: str = "https://example.com"):
    """Async command -- runs on the same event loop as run_async."""
    await asyncio.sleep(0.05)
    print(f"Fetched {url}")

asyncio.run(app.run_async(["fetch"]))
