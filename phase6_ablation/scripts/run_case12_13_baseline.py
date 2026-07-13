# -*- coding: utf-8 -*-
"""
Run baseline experiments for case12 and case13.
Total: 5 models x 2 cases x 10 runs = 100 experiments
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from runners.experiment_runner import ExperimentRunner


MODELS = ["haiku30", "haiku35", "haiku45", "sonnet45", "opus45"]
CASES = ["case12", "case13"]
CONFIG = "baseline"
RUNS_PER_CASE = 10


async def main():
    runner = ExperimentRunner()

    total = len(MODELS) * len(CASES) * RUNS_PER_CASE
    completed = 0

    print(f"Starting {total} baseline experiments for case12/case13")
    print(f"Models: {MODELS}")
    print(f"Cases: {CASES}")
    print(f"Runs per case: {RUNS_PER_CASE}")
    print("=" * 70)

    for case_id in CASES:
        for model in MODELS:
            for run_id in range(1, RUNS_PER_CASE + 1):
                completed += 1
                print(f"\n[{completed}/{total}] {model} - {case_id} - run{run_id}")

                try:
                    result = await runner.run_experiment(
                        model_name=model,
                        config_name=CONFIG,
                        case_id=case_id,
                        run_id=run_id
                    )
                    print(f"  Result: {'SUCCESS' if result.success else 'FAILED'}")
                except Exception as e:
                    print(f"  ERROR: {e}")
                    continue

    print("\n" + "=" * 70)
    print(f"Completed {completed}/{total} experiments")


if __name__ == "__main__":
    asyncio.run(main())
