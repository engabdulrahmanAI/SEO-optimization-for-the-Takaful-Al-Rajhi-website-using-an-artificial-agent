"""
agent_3_critic.py
Agent 3 — الناقد
- يقرأ agent_2_output.json
- openai/gpt-oss-120b ينتقد ويقيّم الجاهزية
- يحفظ → agent_3_output.json
"""

import os, re, json, time, sys
from groq import Groq

INPUT_FILE  = "agent_2_output.json"
OUTPUT_FILE = "agent_3_output.json"
GROQ_MODEL  = "openai/gpt-oss-120b"

CRITIC_PROMPT = """
أنت ناقد SEO متخصص ومتشدد في معايير الجودة.

لديك تحليل مفصّل لصفحات تأمين:

=== التحليل ===
{analysis_summary}

انتقد هذا التحليل وقرر هل البيانات جاهزة لتوليد المحتوى.
أجب فقط بـ JSON صحيح ومكتمل بدون أي نص خارجه:

{{
  "overall_status": "ready | partially_ready | not_ready",
  "critique": {{
    "our_data_quality": {{
      "vehicle_insurance": {{
        "verdict": "sufficient | insufficient | needs_improvement",
        "issues": ["..."],
        "trusted_elements": ["..."]
      }},
      "home_insurance": {{
        "verdict": "sufficient | insufficient | needs_improvement",
        "issues": ["..."],
        "trusted_elements": ["..."]
      }}
    }},
    "competitor_data_quality": {{
      "vehicle_insurance": {{
        "verdict": "sufficient | insufficient | needs_improvement",
        "reliable_competitors": ["..."],
        "unreliable_competitors": ["..."],
        "issues": ["..."]
      }},
      "home_insurance": {{
        "verdict": "sufficient | insufficient | needs_improvement",
        "reliable_competitors": ["..."],
        "unreliable_competitors": ["..."],
        "issues": ["..."]
      }}
    }}
  }},
  "safe_inputs_for_generation": {{
    "vehicle_insurance": {{
      "our_brand_signals": ["..."],
      "trusted_keywords": ["..."],
      "competitor_patterns": ["..."]
    }},
    "home_insurance": {{
      "our_brand_signals": ["..."],
      "trusted_keywords": ["..."],
      "competitor_patterns": ["..."]
    }}
  }},
  "improvements_needed": ["..."],
  "next_agent_handoff": {{
    "can_generate": true,
    "confidence": "high | medium | low",
    "reason": "...",
    "recommended_action": "..."
  }},
  "executive_summary": "..."
}}
"""


def fix_json(raw):
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


def run_critique(client, analysis):
    analysis_summary = json.dumps(analysis, ensure_ascii=False, indent=2)[:3000]
    prompt = CRITIC_PROMPT.format(analysis_summary=analysis_summary)
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=4000,
        )
        raw = resp.choices[0].message.content.strip()
        raw = fix_json(raw)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse فشل: {e}")
        return {"error": "json_parse_failed"}
    except Exception as e:
        print(f"  [WARN] النقد فشل: {e}")
        return {"error": str(e)}


def run_agent_3():
    print("=" * 60)
    print("AGENT 3 — الناقد (openai/gpt-oss-120b)")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        print(f"  [خطأ] الملف غير موجود: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        agent2_data = json.load(f)

    print(f"  تم تحميل: {INPUT_FILE}")
    print(f"  توقيت Agent 2: {agent2_data.get('timestamp','?')}")

    analysis = agent2_data.get("analysis", {})
    if not analysis or "error" in analysis:
        print("  [خطأ] تحليل Agent 2 فارغ أو فاشل.")
        sys.exit(1)

    print("\n  تشغيل النقد ...")
    client = get_client()
    critique = run_critique(client, analysis)

    output = {
        "agent"           : "agent_3_critic",
        "version"         : "1.0",
        "timestamp"       : time.strftime("%Y-%m-%dT%H:%M:%S"),
        "input_file"      : INPUT_FILE,
        "agent2_timestamp": agent2_data.get("timestamp","?"),
        "model_used"      : GROQ_MODEL,
        "critique"        : critique,
    }

    if "error" not in critique:
        output["overall_status"]         = critique.get("overall_status","?")
        output["next_agent_handoff"]     = critique.get("next_agent_handoff",{})
        output["safe_inputs_for_agent4"] = critique.get("safe_inputs_for_generation",{})
        output["executive_summary"]      = critique.get("executive_summary","")

    return output


def save_output(data, path=OUTPUT_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ تم الحفظ → {path}")


if __name__ == "__main__":
    result = run_agent_3()
    print("\n" + "=" * 60)
    print("AGENT 3 — اكتمل")
    print("=" * 60)
    print(f"  الحالة        : {result.get('overall_status','?')}")
    handoff = result.get("next_agent_handoff", {})
    print(f"  جاهز للتوليد : {handoff.get('can_generate','?')}")
    print(f"  مستوى الثقة  : {handoff.get('confidence','?')}")
    print(f"  السبب        : {handoff.get('reason','')[:150]}")
    summary = result.get("executive_summary","")
    if summary:
        print(f"\nالملخص:\n  {summary[:400]}")
    save_output(result)