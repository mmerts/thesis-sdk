# -*- coding: utf-8 -*-
"""Continue Case10 Power Test - only missing runs (haiku45, sonnet45, opus45)"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

# Missing runs for case10 (run 11-15) - haiku35 DONE, skip it
MISSING = [
    # haiku45 - all 10 missing
    ("haiku45", "two_try_no_reflection", "case10", 11),
    ("haiku45", "two_try_no_reflection", "case10", 12),
    ("haiku45", "two_try_no_reflection", "case10", 13),
    ("haiku45", "two_try_no_reflection", "case10", 14),
    ("haiku45", "two_try_no_reflection", "case10", 15),
    ("haiku45", "full_reflexion", "case10", 11),
    ("haiku45", "full_reflexion", "case10", 12),
    ("haiku45", "full_reflexion", "case10", 13),
    ("haiku45", "full_reflexion", "case10", 14),
    ("haiku45", "full_reflexion", "case10", 15),
    # sonnet45 - all 10 missing
    ("sonnet45", "two_try_no_reflection", "case10", 11),
    ("sonnet45", "two_try_no_reflection", "case10", 12),
    ("sonnet45", "two_try_no_reflection", "case10", 13),
    ("sonnet45", "two_try_no_reflection", "case10", 14),
    ("sonnet45", "two_try_no_reflection", "case10", 15),
    ("sonnet45", "full_reflexion", "case10", 11),
    ("sonnet45", "full_reflexion", "case10", 12),
    ("sonnet45", "full_reflexion", "case10", 13),
    ("sonnet45", "full_reflexion", "case10", 14),
    ("sonnet45", "full_reflexion", "case10", 15),
    # opus45 - all 10 missing
    ("opus45", "two_try_no_reflection", "case10", 11),
    ("opus45", "two_try_no_reflection", "case10", 12),
    ("opus45", "two_try_no_reflection", "case10", 13),
    ("opus45", "two_try_no_reflection", "case10", 14),
    ("opus45", "two_try_no_reflection", "case10", 15),
    ("opus45", "full_reflexion", "case10", 11),
    ("opus45", "full_reflexion", "case10", 12),
    ("opus45", "full_reflexion", "case10", 13),
    ("opus45", "full_reflexion", "case10", 14),
    ("opus45", "full_reflexion", "case10", 15),
]

async def main():
    runner = ExperimentRunner()

    total = len(MISSING)
    success_count = 0
    fail_count = 0

    print(f"Case10 Power Test - {total} eksik run (haiku45, sonnet45, opus45)")
    print("="*70)

    for i, (model, config, case, run_id) in enumerate(MISSING, 1):
        print(f"\n[{i}/{total}] {model} + {config} + {case} (run {run_id})")

        try:
            result = await runner.run_experiment(
                model_name=model,
                config_name=config,
                case_id=case,
                run_id=run_id
            )

            if result.success:
                success_count += 1
                print(f"  -> SUCCESS (trial {result.trials_used})")
            else:
                fail_count += 1
                print(f"  -> FAILED")

        except Exception as e:
            print(f"  -> ERROR: {e}")
            fail_count += 1

        await asyncio.sleep(2)

    print("\n" + "="*70)
    print(f"DONE: {success_count} success, {fail_count} failed")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
