"""
view_results.py
===============
1. Runs the pipeline (Agent 1 + Agent 2)
2. Saves screenshots as PNG files to /screenshots folder
3. Prints full analysis results in readable format
"""

import os
import json
import base64
import time

from agent_1_screenshot import capture_pages, OUR_URLS
from test_1_2 import get_client, analyze_screenshot, VISION_MODEL, OUTPUT_FILE

SCREENSHOTS_DIR = "screenshots"

# ── Save screenshots to disk ──────────────────

def save_screenshots(captures: list) -> None:
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    for c in captures:
        if c["status"] != "success":
            continue
        # Build filename from URL slug
        slug = c["url"].rstrip("/").split("/")[-1] or "index"
        path = os.path.join(SCREENSHOTS_DIR, f"{slug}.png")
        png_bytes = base64.b64decode(c["screenshot_b64"])
        with open(path, "wb") as f:
            f.write(png_bytes)
        print(f"  saved → {path}  ({len(png_bytes) // 1024} KB)")


# ── Print full analysis ───────────────────────

def print_analysis(results: list) -> None:
    sep = "─" * 60
    for r in results:
        print(f"\n{sep}")
        url = r.get("url", "?")
        slug = url.rstrip("/").split("/")[-1]
        print(f"  PAGE : {slug}")
        print(f"  URL  : {url}")
        print(sep)

        if "error" in r:
            print(f"  ✗ Error: {r['error']}")
            continue

        print(f"  الألوان الرئيسية        : {', '.join(r.get('الألوان_الرئيسية', []))}")
        print(f"  نوع التخطيط             : {r.get('نوع_التخطيط', '?')}")
        print(f"  اتساق العلامة التجارية : {r.get('اتساق_العلامة_التجارية', '?')}")
        print(f"  وضوح الأزرار            : {r.get('وضوح_الأزرار', '?')}")
        print(f"  أمثلة الأزرار           : {', '.join(r.get('أمثلة_الأزرار', []))}")
        print(f"  كثافة المحتوى           : {r.get('كثافة_المحتوى', '?')}")
        print(f"  وضوح النص العربي        : {r.get('وضوح_النص_العربي', '?')}")
        print(f"\n  التسلسل البصري :")
        print(f"    {r.get('التسلسل_البصري', '')}")
        print(f"\n  الجزء الظاهر :")
        print(f"    {r.get('ملخص_الجزء_الظاهر', '')}")
        print(f"\n  عناصر الثقة :")
        for t in r.get("عناصر_الثقة", []):
            print(f"    • {t}")
        print(f"\n  ملاحظات تجربة المستخدم :")
        for u in r.get("ملاحظات_تجربة_المستخدم", []):
            print(f"    • {u}")
        print(f"\n  الملخص العام :")
        print(f"    {r.get('الملخص_العام', '')}")


# ── Main ─────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("VIEWER — Agent 1 + Agent 2 Full Results")
    print("=" * 60)

    # Step 1: capture screenshots
    print("\n[1/3] Capturing screenshots ...")
    captures = capture_pages(OUR_URLS)
    ok = [c for c in captures if c["status"] == "success"]
    print(f"  Success: {len(ok)} / {len(OUR_URLS)}")

    # Step 2: save to disk
    print(f"\n[2/3] Saving screenshots to /{SCREENSHOTS_DIR} ...")
    save_screenshots(ok)

    # Step 3: run visual analysis
    print(f"\n[3/3] Running visual analysis ({VISION_MODEL}) ...")
    client = get_client()
    results = []
    for c in ok:
        print(f"  analysing {c['url'].split('/')[-1]} ...")
        result = analyze_screenshot(client, c["url"], c["screenshot_b64"])
        results.append(result)
        time.sleep(1)

    # Print full results
    print("\n\n" + "=" * 60)
    print("FULL ANALYSIS RESULTS")
    print("=" * 60)
    print_analysis(results)

    # Save JSON
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": VISION_MODEL,
        "results": results,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n\n  ✓ Screenshots saved to  → /{SCREENSHOTS_DIR}/")
    print(f"  ✓ JSON results saved to → {OUTPUT_FILE}")
