"""
main.py — منسّق البايبلاين
يشغّل الثلاثة وكلاء بالترتيب تلقائياً
"""

import sys, time, argparse

def run_full_pipeline():
    print("\n" + "=" * 60)
    print("SEO PIPELINE — تشغيل كامل")
    print("=" * 60)
    print("\nالهيكل:")
    print("  Agent 1 → Selenium يقرأ + llama يحلل الهوية")
    print("  Agent 2 → llama يستخرج insights ويقارن")
    print("  Agent 3 → llama ينتقد ويقرر الجاهزية")
    print("=" * 60)

    # Agent 1
    print("\n>>> المرحلة 1: قراءة الصفحات (Agent 1)")
    print("-" * 60)
    from agent_1_reader import run_agent_1, save_output as save_1
    result_1 = run_agent_1()
    save_1(result_1)
    print("\n>>> المرحلة 1 اكتملت. انتظار 3 ثواني ...")
    time.sleep(3)

    # Agent 2
    print("\n>>> المرحلة 2: التحليل العميق (Agent 2)")
    print("-" * 60)
    from agent_2_analyst import run_agent_2, save_output as save_2
    result_2 = run_agent_2()
    save_2(result_2)
    print("\n>>> المرحلة 2 اكتملت. انتظار 3 ثواني ...")
    time.sleep(3)

    # Agent 3
    print("\n>>> المرحلة 3: النقد والتقييم (Agent 3)")
    print("-" * 60)
    from agent_3_critic import run_agent_3, save_output as save_3
    result_3 = run_agent_3()
    save_3(result_3)

    # ملخص نهائي
    print("\n" + "=" * 60)
    print("PIPELINE — اكتمل بنجاح")
    print("=" * 60)
    print("\nالملفات المنتجة:")
    print("  agent_1_output.json  ← بيانات الاستخراج")
    print("  agent_2_output.json  ← التحليل والمقارنة")
    print("  agent_3_output.json  ← النقد وقرار الجاهزية")

    handoff = result_3.get("next_agent_handoff", {})
    print(f"\nالنتيجة النهائية:")
    print(f"  الحالة         : {result_3.get('overall_status','?')}")
    print(f"  جاهز للتوليد  : {handoff.get('can_generate','?')}")
    print(f"  مستوى الثقة   : {handoff.get('confidence','?')}")
    print(f"  السبب         : {handoff.get('reason','')[:150]}")

def main():
    parser = argparse.ArgumentParser(description="SEO Multi-Agent Pipeline")
    parser.add_argument("--agent", type=int, choices=[1,2,3],
                        help="شغّل وكيل محدد فقط (1، 2، أو 3)")
    args = parser.parse_args()

    if args.agent == 1:
        from agent_1_reader import run_agent_1, save_output as save_1
        save_1(run_agent_1())
    elif args.agent == 2:
        from agent_2_analyst import run_agent_2, save_output as save_2
        save_2(run_agent_2())
    elif args.agent == 3:
        from agent_3_critic import run_agent_3, save_output as save_3
        save_3(run_agent_3())
    else:
        run_full_pipeline()

if __name__ == "__main__":
    main()
