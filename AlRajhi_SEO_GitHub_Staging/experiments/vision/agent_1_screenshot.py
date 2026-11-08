"""
agent_1_screenshot.py
=====================
Agent 1 — Visual Page Capture (Playwright)

Role: visit each provided URL, capture a full-page desktop screenshot,
      return base64-encoded PNG bytes ready for a Vision LLM.

Does NOT:
- crawl or follow links
- interact with the page (no cookie banners, no clicks)
- write anything to disk
- analyse or interpret content
"""

import asyncio
import base64
import time
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    TimeoutError as PlaywrightTimeoutError,
)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

VIEWPORT        = {"width": 1440, "height": 900}
TIMEOUT_MS        = 60_000   # 60 s navigation timeout
NETWORK_IDLE_MS   = 10_000   # extra wait after load for JS-heavy pages
SCREENSHOT_MS     = 90_000   # 90 s screenshot timeout (fonts + full-page render)
MAX_CONCURRENT    = 2        # reduced to avoid resource contention on 8 pages

OUR_URLS = [
    "https://www.alrajhitakaful.com/ar/personal/car-insurance",
    "https://www.alrajhitakaful.com/ar/personal/home-insurance",
    "https://www.alrajhitakaful.com/ar/personal/travel-insurance",
    "https://www.alrajhitakaful.com/ar/visit-visa-extension",
    "https://www.alrajhitakaful.com/ar/personal/medical-malpractice-insurance",
    "https://www.alrajhitakaful.com/ar/domestic-helper-insurance",
    "https://www.alrajhitakaful.com/ar/personal/cyber-insurance",
    "https://www.alrajhitakaful.com/ar/personal/domestic-worker-insurance",
]

# User-agent that looks like a real desktop Chrome
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────────
# SINGLE PAGE CAPTURE
# ─────────────────────────────────────────────

async def _capture_one(
    context: BrowserContext,
    url: str,
    semaphore: asyncio.Semaphore,
) -> dict:
    """
    Open `url` in a fresh page, wait for it to fully settle,
    take a full-page screenshot, return base64 PNG.
    Never interacts with the page beyond navigation.
    """
    async with semaphore:
        page = None
        try:
            page = await context.new_page()
            await page.set_viewport_size(VIEWPORT)

            # Navigate — wait for initial load
            await page.goto(url, wait_until="load", timeout=TIMEOUT_MS)

            # Extra settle time for JS-rendered content (SPAs, lazy images)
            try:
                await page.wait_for_load_state(
                    "networkidle", timeout=NETWORK_IDLE_MS
                )
            except PlaywrightTimeoutError:
                # networkidle timeout is acceptable — page is likely usable
                pass

            # Capture full-page screenshot as raw bytes (no disk I/O)
            png_bytes: bytes = await page.screenshot(
                full_page=True,
                type="png",
                timeout=SCREENSHOT_MS,
            )
            screenshot_b64: str = base64.b64encode(png_bytes).decode("utf-8")

            print(f"  ✓  {url}  ({len(png_bytes) // 1024} KB)")
            return {
                "url"            : url,
                "screenshot_b64" : screenshot_b64,
                "status"         : "success",
            }

        except Exception as exc:
            print(f"  ✗  {url}  — {exc}")
            return {
                "url"            : url,
                "screenshot_b64" : None,
                "status"         : "failed",
                "error"          : str(exc),
            }

        finally:
            if page:
                await page.close()


# ─────────────────────────────────────────────
# CONCURRENT RUNNER
# ─────────────────────────────────────────────

async def _capture_all(urls: list[str]) -> list[dict]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=True)

        context: BrowserContext = await browser.new_context(
            user_agent=_USER_AGENT,
            viewport=VIEWPORT,
            # Disable unnecessary permissions — we only need to load pages
            java_script_enabled=True,
        )

        # Block ads / tracking to speed up load and reduce noise
        await context.route(
            "**/{ads,analytics,tracking,doubleclick,google-analytics}**",
            lambda route, _: route.abort(),
        )

        tasks = [_capture_one(context, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        await context.close()
        await browser.close()

    return list(results)


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def capture_pages(urls: list[str]) -> list[dict]:
    """
    Synchronous entry point.

    Parameters
    ----------
    urls : list of page URLs to screenshot (Al Rajhi Takaful product pages)

    Returns
    -------
    list of dicts:
        {"url": "...", "screenshot_b64": "...", "status": "success"}
        {"url": "...", "screenshot_b64": None,  "status": "failed", "error": "..."}
    """
    if not urls:
        return []
    return asyncio.run(_capture_all(urls))


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("AGENT 1 — Visual Page Capture (Playwright)")
    print(f"Pages  : {len(OUR_URLS)}")
    print(f"Viewport: {VIEWPORT['width']}×{VIEWPORT['height']}")
    print("=" * 60)

    t0 = time.time()
    results = capture_pages(OUR_URLS)
    elapsed = time.time() - t0

    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    ok     = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    print(f"  Success : {len(ok)}")
    print(f"  Failed  : {len(failed)}")
    print(f"  Time    : {elapsed:.1f}s")

    for r in failed:
        print(f"\n  [FAILED] {r['url']}")
        print(f"           {r.get('error', 'unknown error')}")
