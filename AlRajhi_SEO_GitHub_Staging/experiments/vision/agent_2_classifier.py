"""
agent_2_classifier.py
=====================
Agent 2 — Content Classifier (Vision)

Role: receive screenshots from Agent 1, read ALL visible text,
      classify each phrase by language / type / importance.

Output: agent_2_classifier_output.json
"""

import os
import json
import time

from groq import Groq

from agent_1_screenshot import capture_pages, OUR_URLS

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
OUTPUT_FILE  = "agent_2_classifier_output.json"

CLASSIFIER_PROMPT = """You are a precise multilingual content classifier for an e-commerce product page team.

You will receive a screenshot of a webpage.

Your job is to:
1. Read ALL visible text directly from the screenshot.
2. Split the text into meaningful phrases or sentences (not word by word, not full paragraphs).
3. For each phrase, identify:
   - language: "ar" (Arabic only) | "en" (English only) | "mixed" (both in same phrase)
   - type: "product_name" | "cta_button" | "price" | "description" | "label" | "navigation" | "badge" | "heading" | "body_text" | "other"
   - importance: "high" (key copy that defines the page) | "low" (supporting or decorative text)
   - clean_phrase: the phrase cleaned of extra spaces, symbols, or formatting artifacts

Rules:
- Do NOT merge phrases of different languages into one entry.
- Do NOT skip any phrase, even short ones like button labels or badges.
- Be precise — these phrases will be used by a future agent to write product descriptions, so type and language labels must be accurate.
- Preserve Arabic phrases as-is, preserve English phrases as-is.

Respond ONLY with valid JSON, no markdown, no explanation:
{
  "phrases": [
    {
      "clean_phrase": "...",
      "language": "ar | en | mixed",
      "type": "...",
      "importance": "high | low"
    }
  ]
}"""


# ─────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────

def get_client() -> Groq:
    key = (
        os.environ.get("GROQ_API_KEY") or
        os.environ.get("OPENAI_API_KEY_1") or
        os.environ.get("OPENAI_API_KEY_2")
    )
    if not key:
        raise EnvironmentError("API key not found")
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
# CLASSIFY ONE PAGE
# ─────────────────────────────────────────────

def classify_page(client: Groq, url: str, screenshot_b64: str, retries: int = 3) -> dict:
    for attempt in range(retries):
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
                                "text": CLASSIFIER_PROMPT,
                            },
                        ],
                    }
                ],
                temperature=0.1,
            )
            raw = resp.choices[0].message.content.strip()
            if not raw:
                raise ValueError("empty response from model")
            raw = fix_json(raw)
            result = json.loads(raw)
            result["url"] = url
            result["status"] = "success"
            return result

        except (json.JSONDecodeError, ValueError) as e:
            if attempt < retries - 1:
                print(f"    [retry {attempt + 1}] {e}")
                time.sleep(2)
            else:
                return {"url": url, "status": "failed", "error": f"{e}"}
        except Exception as e:
            return {"url": url, "status": "failed", "error": str(e)}


# ─────────────────────────────────────────────
# PRINT RESULTS
# ─────────────────────────────────────────────

def print_result(result: dict):
    sep = "─" * 60
    url  = result.get("url", "?")
    slug = url.rstrip("/").split("/")[-1]

    print(f"\n{sep}")
    print(f"  PAGE: {slug}")
    print(f"  URL : {url}")
    print(sep)

    if result.get("status") == "failed":
        print(f"  ✗ {result.get('error')}")
        return

    phrases = result.get("phrases", [])
    high    = [p for p in phrases if p.get("importance") == "high"]
    low     = [p for p in phrases if p.get("importance") == "low"]
    ar      = [p for p in phrases if p.get("language") == "ar"]
    en      = [p for p in phrases if p.get("language") == "en"]
    mixed   = [p for p in phrases if p.get("language") == "mixed"]

    print(f"  Total phrases : {len(phrases)}")
    print(f"  High importance: {len(high)}  |  Low: {len(low)}")
    print(f"  Arabic: {len(ar)}  |  English: {len(en)}  |  Mixed: {len(mixed)}")

    print(f"\n  ── High Importance Phrases ──")
    for p in high:
        lang = p.get("language", "?")
        ptype = p.get("type", "?")
        phrase = p.get("clean_phrase", "")
        print(f"    [{lang}] [{ptype}]  {phrase}")

    print(f"\n  ── CTA Buttons ──")
    for p in phrases:
        if p.get("type") == "cta_button":
            print(f"    {p.get('clean_phrase', '')}")


# ─────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────

def run_agent_2_classifier(urls: list = None) -> dict:
    if urls is None:
        urls = OUR_URLS

    print("=" * 60)
    print("AGENT 2 — Content Classifier (Vision)")
    print(f"Model : {VISION_MODEL}")
    print(f"Pages : {len(urls)}")
    print("=" * 60)

    # Agent 1: capture
    print("\n[1/2] Agent 1 — capturing screenshots ...")
    captures = capture_pages(urls)
    ok = [c for c in captures if c["status"] == "success"]
    print(f"  Success: {len(ok)} / {len(urls)}")

    # Agent 2: classify
    print("\n[2/2] Agent 2 — classifying content ...")
    client  = get_client()
    results = []

    for c in ok:
        slug = c["url"].rstrip("/").split("/")[-1]
        print(f"  classifying {slug} ...")
        result = classify_page(client, c["url"], c["screenshot_b64"])
        results.append(result)
        print_result(result)
        time.sleep(1)

    output = {
        "agent"    : "agent_2_classifier",
        "version"  : "1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model"    : VISION_MODEL,
        "pages"    : len(urls),
        "results"  : results,
    }
    return output


def save_output(data: dict, path: str = OUTPUT_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ Saved → {path}")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    result = run_agent_2_classifier()

    print("\n" + "=" * 60)
    print("AGENT 2 CLASSIFIER — Summary")
    print("=" * 60)
    total_phrases = sum(len(r.get("phrases", [])) for r in result["results"])
    print(f"  Pages processed : {len(result['results'])}")
    print(f"  Total phrases   : {total_phrases}")

    save_output(result)
