# -*- coding: utf-8 -*-
"""Complete missing experiments for round numbers"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

EXPERIMENTS = []

# Case9 full_reflexion: 109 → 110 (+1)
# sonnet45 has 24, add 1 more (run 25)
EXPERIMENTS.append(("sonnet45", "full_reflexion", "case9", 25))

# Case11 baseline: 0 → 50 (+50)
# 5 models × 10 runs
for model in ["haiku30", "haiku35", "haiku45", "sonnet45", "opus45"]:
    for run_id in range(1, 11):
        EXPERIMENTS.append((model, "baseline", "case11", run_id))

# Case11 full_reflexion: 41 → 50 (+9)
# haiku30 has 0, add 9 runs
for run_id in range(1, 10):
    EXPERIMENTS.append(("haiku30", "full_reflexion", "case11", run_id))

# Case11 two_try_no_reflection: 42 → 50 (+8)
# haiku30 has 0, add 8 runs
for run_id in range(1, 9):
    EXPERIMENTS.append(("haiku30", "two_try_no_reflection", "case11", run_id))

async def main():
    runner = ExperimentRunner()

    total = len(EXPERIMENTS)
    success_count = 0
    fail_count = 0

    print(f"Completing experiments - {total} total")
    print("=" * 70)

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

    print("\n" + "=" * 70)
    print(f"COMPLETED: {success_count} success, {fail_count} failed")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
