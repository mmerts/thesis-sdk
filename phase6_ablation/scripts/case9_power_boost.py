# -*- coding: utf-8 -*-
"""Case9 Power Boost - Add 10 runs per model/config for statistical significance"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

# Case9: +10 run per model/config
# Goal: p < 0.05 (currently p = 0.063)
EXPERIMENTS = []

# haiku30: currently 10 runs, add run 11-20
for run_id in range(11, 21):
    EXPERIMENTS.append(("haiku30", "two_try_no_reflection", "case9", run_id))
    EXPERIMENTS.append(("haiku30", "full_reflexion", "case9", run_id))

# haiku35: currently 15 runs, add run 16-25
for run_id in range(16, 26):
    EXPERIMENTS.append(("haiku35", "two_try_no_reflection", "case9", run_id))
    EXPERIMENTS.append(("haiku35", "full_reflexion", "case9", run_id))

# haiku45: currently 15 runs, add run 16-25
for run_id in range(16, 26):
    EXPERIMENTS.append(("haiku45", "two_try_no_reflection", "case9", run_id))
    EXPERIMENTS.append(("haiku45", "full_reflexion", "case9", run_id))

# sonnet45: currently 15 runs, add run 16-25
for run_id in range(16, 26):
    EXPERIMENTS.append(("sonnet45", "two_try_no_reflection", "case9", run_id))
    EXPERIMENTS.append(("sonnet45", "full_reflexion", "case9", run_id))

# opus45: currently 15 runs, add run 16-25
for run_id in range(16, 26):
    EXPERIMENTS.append(("opus45", "two_try_no_reflection", "case9", run_id))
    EXPERIMENTS.append(("opus45", "full_reflexion", "case9", run_id))

async def main():
    runner = ExperimentRunner()

    total = len(EXPERIMENTS)
    success_count = 0
    fail_count = 0

    print(f"Case9 Power Boost - {total} experiments")
    print(f"Goal: Achieve p < 0.05 for reflexion benefit")
    print("="*70)

    for i, (model, config, case, run_id) in enumerate(EXPERIMENTS, 1):
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
    print(f"COMPLETED: {success_count} success, {fail_count} failed")
    print("="*70)
    print("\nRun import script to update database:")
    print("python phase6_ablation/scripts/import_missing_to_db.py")

if __name__ == "__main__":
    asyncio.run(main())
