# -*- coding: utf-8 -*-
"""Power Test: Case9 + Case10 ek 5 run (p < 0.05 hedefi)"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

MODELS = ["haiku35", "haiku45", "sonnet45", "opus45"]  # haiku30 hariç (zayıf)
CONFIGS = ["two_try_no_reflection", "full_reflexion"]
CASES = ["case9", "case10"]
RUNS = range(11, 16)  # run 11-15 (ek 5 run)

async def main():
    runner = ExperimentRunner()
    results = {}

    # Toplam deney sayısı
    total = len(MODELS) * len(CONFIGS) * len(CASES) * len(RUNS)
    current = 0

    print(f"Power Test: {total} deney")
    print(f"Case9 + Case10, run 11-15, 4 model, 2 config")
    print("="*70)

    for case in CASES:
        results[case] = {"two_try": {"success": 0, "fail": 0},
                         "reflexion": {"success": 0, "fail": 0}}

        for model in MODELS:
            for config in CONFIGS:
                config_key = "two_try" if "two_try" in config else "reflexion"

                for run_id in RUNS:
                    current += 1
                    print(f"\n[{current}/{total}] {model} + {config} + {case} (run {run_id})")

                    try:
                        result = await runner.run_experiment(
                            model_name=model,
                            config_name=config,
                            case_id=case,
                            run_id=run_id
                        )

                        if result.success:
                            results[case][config_key]["success"] += 1
                            print(f"  -> SUCCESS (trial {result.trials_used})")
                        else:
                            results[case][config_key]["fail"] += 1
                            print(f"  -> FAILED")

                    except Exception as e:
                        print(f"  -> ERROR: {e}")
                        results[case][config_key]["fail"] += 1

                    await asyncio.sleep(2)

    # Summary
    print("\n" + "="*70)
    print("POWER TEST SUMMARY (this session)")
    print("="*70)
    print(f"{'Case':<10} {'two_try':<15} {'reflexion':<15} {'Benefit'}")
    print("-"*70)

    total_two_success = 0
    total_two_total = 0
    total_ref_success = 0
    total_ref_total = 0

    for case in CASES:
        two = results[case]["two_try"]
        ref = results[case]["reflexion"]
        two_total = two["success"] + two["fail"]
        ref_total = ref["success"] + ref["fail"]

        two_rate = two["success"]/two_total*100 if two_total else 0
        ref_rate = ref["success"]/ref_total*100 if ref_total else 0
        benefit = ref_rate - two_rate
        sign = "+" if benefit > 0 else ""

        print(f"{case:<10} {two['success']}/{two_total} ({two_rate:.0f}%){'':<5} {ref['success']}/{ref_total} ({ref_rate:.0f}%){'':<5} {sign}{benefit:.0f}pp")

        total_two_success += two["success"]
        total_two_total += two_total
        total_ref_success += ref["success"]
        total_ref_total += ref_total

    print("-"*70)
    two_rate = total_two_success/total_two_total*100 if total_two_total else 0
    ref_rate = total_ref_success/total_ref_total*100 if total_ref_total else 0
    benefit = ref_rate - two_rate
    sign = "+" if benefit > 0 else ""
    print(f"{'TOTAL':<10} {total_two_success}/{total_two_total} ({two_rate:.0f}%){'':<5} {total_ref_success}/{total_ref_total} ({ref_rate:.0f}%){'':<5} {sign}{benefit:.0f}pp")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
