"""
agent_2_analyst.py
Agent 2 — المحلل
- يقرأ agent_1_output.json
- openai/gpt-oss-120b يستخرج insights عميقة
- يحفظ → agent_2_output.json
"""

import os, re, json, time, sys
from groq import Groq

INPUT_FILE  = "agent_1_output.json"
OUTPUT_FILE = "agent_2_output.json"
GROQ_MODEL  = "openai/gpt-oss-120b"

ANALYSIS_PROMPT = """
أنت محلل SEO ومحتوى متخصص في سوق التأمين السعودي.

لديك البيانات المستخرجة التالية من صفحات تأمين:

=== صفحاتنا ===
{our_summary}

=== صفحات المنافسين ===
{comp_summary}

مهمتك: استخرج insights عميقة ومقارنة شاملة.
أجب فقط بـ JSON صحيح ومكتمل بدون أي نص خارجه:

{{
  "our_brand_analysis": {{
    "vehicle_insurance": {{
      "content_quality": "strong | medium | weak",
      "seo_signals": ["..."],
      "content_gaps": ["..."],
      "unique_strengths": ["..."],
      "tone_summary": "..."
    }},
    "home_insurance": {{
      "content_quality": "strong | medium | weak",
      "seo_signals": ["..."],
      "content_gaps": ["..."],
      "unique_strengths": ["..."],
      "tone_summary": "..."
    }}
  }},
  "competitor_analysis": {{
    "vehicle_insurance": {{
      "strongest_competitor": "...",
      "common_keywords": ["..."],
      "common_cta_patterns": ["..."],
      "content_strategies": ["..."],
      "gaps_we_can_exploit": ["..."]
    }},
    "home_insurance": {{
      "strongest_competitor": "...",
      "common_keywords": ["..."],
      "common_cta_patterns": ["..."],
      "content_strategies": ["..."],
      "gaps_we_can_exploit": ["..."]
    }}
  }},
  "competitive_positioning": {{
    "vehicle_insurance": "...",
    "home_insurance": "..."
  }},
  "keyword_opportunities": {{
    "vehicle_insurance": ["..."],
    "home_insurance": ["..."]
  }},
  "content_recommendations": ["..."],
  "analysis_confidence": "high | medium | low",
  "analysis_notes": "..."
}}
"""


def fix_json(raw):
    """إصلاح JSON مقطوع أو مغلف بـ markdown."""
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
        if last and not last[-1] in ('}', ']', '"', ','):
            lines = lines[:-1]
            raw = '\n'.join(lines)
    raw = raw.rstrip().rstrip(',')
    for _ in range(max(0, open_brackets)):
        raw += ']'
    for _ in range(max(0, open_braces)):
        raw += '}'
    return raw


def get_client():
    key = (os.environ.get("GROQ_API_KEY") or
           os.environ.get("OPENAI_API_KEY_1") or
           os.environ.get("OPENAI_API_KEY_2"))
    if not key:
        raise EnvironmentError("لم يتم العثور على مفتاح API")
    return Groq(api_key=key)


def page_to_summary(page, label):
    identity = page.get("identity_analysis", {})
    identity_text = ""
    if identity and "error" not in identity:
        identity_text = (
            f"\n  التون: {identity.get('tone','')}"
            f"\n  الأسلوب: {identity.get('style','')}"
            f"\n  نقاط القوة: {', '.join(identity.get('strengths',[])[:3])}"
            f"\n  نقاط الضعف: {', '.join(identity.get('weaknesses',[])[:3])}"
        )
    return (
        f"\n[{label}]"
        f"\n  الرابط: {page.get('url','')}"
        f"\n  الحالة: {page.get('fetch_status','')}"
        f"\n  العنوان: {page.get('title','(missing)')[:80]}"
        f"\n  الوصف: {page.get('meta_description','(missing)')[:100]}"
        f"\n  عدد الأحرف: {len(page.get('body_content',''))}"
        f"\n  الكلمات: {', '.join(page.get('keywords_used',[])[:12])}"
        f"\n  العبارات: {', '.join(page.get('top_phrases',[])[:8])}"
        f"{identity_text}"
        f"\n  محتوى: {page.get('body_content','')[:300]}"
    )


def run_analysis(client, our_pages, comp_pages):
    our_summary = "\n".join(
        page_to_summary(v, f"صفحتنا / {k}") for k, v in our_pages.items()
    )
    comp_summary = ""
    for product_key, pages in comp_pages.items():
        for p in pages:
            comp_summary += page_to_summary(p, f"{p.get('competitor_brand','?')} / {product_key}")

    prompt = ANALYSIS_PROMPT.format(
        our_summary=our_summary,
        comp_summary=comp_summary,
    )

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=4000,
        )
        raw = resp.choices[0].message.content.strip()
        raw = fix_json(raw)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse فشل: {e}")
        return {"error": "json_parse_failed"}
    except Exception as e:
        print(f"  [WARN] التحليل فشل: {e}")
        return {"error": str(e)}


def run_agent_2():
    print("=" * 60)
    print("AGENT 2 — المحلل (openai/gpt-oss-120b)")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        print(f"  [خطأ] الملف غير موجود: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        agent1_data = json.load(f)

    print(f"  تم تحميل: {INPUT_FILE}")
    print(f"  توقيت Agent 1: {agent1_data.get('timestamp','?')}")

    our_pages  = agent1_data.get("our_pages", {})
    comp_pages = agent1_data.get("competitor_pages", {})

    print("\n  تشغيل التحليل العميق ...")
    client = get_client()
    analysis = run_analysis(client, our_pages, comp_pages)

    output = {
        "agent"           : "agent_2_analyst",
        "version"         : "1.0",
        "timestamp"       : time.strftime("%Y-%m-%dT%H:%M:%S"),
        "input_file"      : INPUT_FILE,
        "agent1_timestamp": agent1_data.get("timestamp","?"),
        "model_used"      : GROQ_MODEL,
        "analysis"        : analysis,
    }
    return output


def save_output(data, path=OUTPUT_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ تم الحفظ → {path}")


if __name__ == "__main__":
    result = run_agent_2()
    print("\n" + "=" * 60)
    print("AGENT 2 — اكتمل")
    print("=" * 60)
    analysis = result.get("analysis", {})
    print(f"  مستوى الثقة: {analysis.get('analysis_confidence','?')}")
    print(f"  ملاحظات: {analysis.get('analysis_notes','')[:200]}")
    save_output(result)