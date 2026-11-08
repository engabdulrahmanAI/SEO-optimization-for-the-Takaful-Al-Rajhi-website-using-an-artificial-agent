"""
test_1_2.py
===========
Test pipeline: Agent 1 (screenshot) → Agent 2 (visual brand analysis)

Flow:
  1. Agent 1 captures full-page screenshots via Playwright
  2. Agent 2 sends each screenshot to a Vision LLM for brand analysis
  3. Results saved to agent_2_visual_output.json
"""

import os
import re
import json
import time

from groq import Groq

from agent_1_screenshot import capture_pages, OUR_URLS

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
OUTPUT_FILE  = "agent_2_visual_output.json"

ANALYSIS_PROMPT = """
أنت محلل هوية بصرية متخصص في مواقع التأمين السعودية.

انظر إلى لقطة الشاشة الكاملة لصفحة منتج تأمين من موقع تكافل الراجحي.

حلل الهوية البصرية للصفحة وأجب فقط بـ JSON صحيح بدون أي نص خارجه — جميع القيم النصية باللغة العربية:

{
  "url": "...",
  "الألوان_الرئيسية": ["اذكر الألوان السائدة في الصفحة"],
  "نوع_التخطيط": "عمود واحد | متعدد الأعمدة | قائم على الهيرو | قائم على البطاقات | أخرى",
  "التسلسل_البصري": "صف كيف يتم ترتيب المحتوى بصرياً",
  "وضوح_الأزرار": "عالي | متوسط | منخفض",
  "أمثلة_الأزرار": ["اذكر نصوص أزرار الدعوة للإجراء المرئية"],
  "كثافة_المحتوى": "عالية | متوسطة | منخفضة",
  "عناصر_الثقة": ["الشعارات والشهادات والإحصائيات والأوسمة المرئية"],
  "ملاحظات_تجربة_المستخدم": ["أنماط أو مشكلات UX الملحوظة"],
  "وضوح_النص_العربي": "قوي | متوسط | ضعيف",
  "اتساق_العلامة_التجارية": "قوي | متوسط | ضعيف",
  "ملخص_الجزء_الظاهر": "ما يراه المستخدم دون تمرير الصفحة",
  "الملخص_العام": "ملخص من جملتين إلى ثلاث جمل عن هوية العلامة التجارية البصرية"
}
"""


# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────

def get_client() -> Groq:
    key = (
        os.environ.get("GROQ_API_KEY") or
        os.environ.get("OPENAI_API_KEY_1") or
        os.environ.get("OPENAI_API_KEY_2")
    )
    if not key:
        raise EnvironmentError("API key not found — set GROQ_API_KEY")
    return Groq(api_key=key)


# ─────────────────────────────────────────────
# JSON REPAIR
# ─────────────────────────────────────────────

def fix_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    open_braces   = raw.count('{') - raw.count('}')
    open_brackets = raw.count('[') - raw.count(']')
    lines = raw.split('\n')
    if lines:
        last = lines[-1].strip()
        if last and last[-1] not in ('}', ']', '"', ','):
            lines = lines[:-1]
            raw = '\n'.join(lines)
    raw = raw.rstrip().rstrip(',')
    for _ in range(max(0, open_brackets)):
        raw += ']'
    for _ in range(max(0, open_braces)):
        raw += '}'
    return raw


# ─────────────────────────────────────────────
# AGENT 2 — VISUAL ANALYSIS
# ─────────────────────────────────────────────

def analyze_screenshot(client: Groq, url: str, screenshot_b64: str) -> dict:
    """Send one screenshot to the Vision LLM and return structured analysis."""
    try:
        resp = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_b64}"
                            },
                        },
                        {
                            "type": "text",
                            "text": ANALYSIS_PROMPT,
                        },
                    ],
                }
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        raw = resp.choices[0].message.content.strip()
        raw = fix_json(raw)
        result = json.loads(raw)
        result["url"] = url
        return result

    except json.JSONDecodeError as e:
        print(f"    [WARN] JSON parse failed for {url}: {e}")
        return {"url": url, "error": "json_parse_failed"}
    except Exception as e:
        print(f"    [WARN] Vision analysis failed for {url}: {e}")
        return {"url": url, "error": str(e)}


# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

def run_pipeline(urls: list[str]) -> dict:
    print("=" * 60)
    print("PIPELINE TEST — Agent 1 → Agent 2")
    print(f"Model  : {VISION_MODEL}")
    print(f"Pages  : {len(urls)}")
    print("=" * 60)

    # ── Agent 1: capture screenshots ──────────
    print("\n[1/2] Agent 1 — capturing screenshots ...")
    t0 = time.time()
    captures = capture_pages(urls)
    print(f"  Done in {time.time() - t0:.1f}s")

    ok     = [c for c in captures if c["status"] == "success"]
    failed = [c for c in captures if c["status"] == "failed"]
    print(f"  Success: {len(ok)}  |  Failed: {len(failed)}")
    for f in failed:
        print(f"  [FAILED] {f['url']} — {f.get('error','?')}")

    if not ok:
        print("\n  No screenshots captured — aborting.")
        return {}

    # ── Agent 2: visual analysis ───────────────
    print("\n[2/2] Agent 2 — visual brand analysis ...")
    client = get_client()
    analyses = []

    for capture in ok:
        url = capture["url"]
        print(f"\n  ► {url}")
        result = analyze_screenshot(client, url, capture["screenshot_b64"])
        analyses.append(result)
        print(f"    brand_consistency : {result.get('brand_consistency', '?')}")
        print(f"    cta_visibility    : {result.get('cta_visibility', '?')}")
        print(f"    content_density   : {result.get('content_density', '?')}")
        summary = result.get("overall_summary", "")
        if summary:
            print(f"    summary           : {summary[:120]}")
        time.sleep(1)  # avoid rate limiting

    output = {
        "pipeline"  : "agent_1_screenshot → agent_2_visual",
        "timestamp" : time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model"     : VISION_MODEL,
        "pages"     : len(urls),
        "results"   : analyses,
    }
    return output


# ─────────────────────────────────────────────
# SAVE + ENTRY POINT
# ─────────────────────────────────────────────

def save_output(data: dict, path: str = OUTPUT_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ Saved → {path}")


if __name__ == "__main__":
    result = run_pipeline(OUR_URLS)

    if result:
        print("\n" + "=" * 60)
        print("PIPELINE — Complete")
        print("=" * 60)
        for r in result.get("results", []):
            url    = r.get("url", "?")
            status = "✓" if "error" not in r else "✗"
            print(f"  {status}  {url}")
            if "overall_summary" in r:
                print(f"     {r['overall_summary'][:150]}")

        save_output(result)
