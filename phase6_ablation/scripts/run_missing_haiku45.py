# -*- coding: utf-8 -*-
"""
Run missing Haiku 4.5 experiments.
Total: 65 missing tests
- Baseline: case7 (run 9-10), case8 (run 4-10) = 9 tests
- Full Reflexion: all cases (run 4-10) = 56 tests
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))

from runners.experiment_runner import ExperimentRunner
from configs.experiment_configs import (
    ALL_MODEL_CONFIGS, ALL_ABLATION_CONFIGS, TEST_CASES
)


# Define missing experiments
MISSING_EXPERIMENTS = []

# Baseline missing: case7 run 9-10, case8 run 4-10
for run in [9, 10]:
    MISSING_EXPERIMENTS.append(("haiku45", "baseline", "case7", run))

for run in range(4, 11):
    MISSING_EXPERIMENTS.append(("haiku45", "baseline", "case8", run))

# Full reflexion missing: all cases run 4-10
for case_num in range(1, 9):
    for run in range(4, 11):
        MISSING_EXPERIMENTS.append(("haiku45", "full_reflexion", f"case{case_num}", run))

print(f"Total missing experiments: {len(MISSING_EXPERIMENTS)}")


def get_model_config(name: str):
    for m in ALL_MODEL_CONFIGS:
        if m.name == name:
            return m
    raise ValueError(f"Model not found: {name}")


def get_ablation_config(name: str):
    for c in ALL_ABLATION_CONFIGS:
        if c.name == name:
            return c
    raise ValueError(f"Config not found: {name}")


def get_test_case(case_id: str):
    for t in TEST_CASES:
        if t.case_id == case_id:
            return t
    raise ValueError(f"Test case not found: {case_id}")


async def run_missing_experiments():
    """Run all missing experiments."""
    results_dir = Path(__file__).parent / "results" / "raw"
    checkpoint_file = Path(__file__).parent / "results" / "checkpoint.json"

    # Load existing checkpoint
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            checkpoint = json.load(f)
        completed = set(checkpoint.get("completed_ids", []))
    else:
        completed = set()

    runner = ExperimentRunner(results_dir)

    total = len(MISSING_EXPERIMENTS)
    done = 0

    for model_name, config_name, case_id, run_num in MISSING_EXPERIMENTS:
        exp_id = f"{model_name}_{config_name}_{case_id}_run{run_num}"

        # Skip if already completed
        if exp_id in completed:
            print(f"[SKIP] {exp_id} already completed")
            done += 1
            continue

        print(f"\n{'='*60}")
        print(f"[{done+1}/{total}] Running: {exp_id}")
        print(f"{'='*60}")

        try:
            model_config = get_model_config(model_name)
            ablation_config = get_ablation_config(config_name)
            test_case = get_test_case(case_id)

            result = await runner.run_experiment(
                model_config=model_config,
                ablation_config=ablation_config,
                test_case=test_case,
                run_id=run_num
            )

            # Update checkpoint
            completed.add(exp_id)
            checkpoint["completed_ids"] = list(completed)
            checkpoint["completed_experiments"] = len(completed)
            checkpoint["last_update"] = datetime.now().isoformat()

            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)

            status = "SUCCESS" if result.success else "FAILED"
            print(f"[{status}] {exp_id} - Trials: {result.trials_used}, Cost: ${result.total_cost:.4f}")

        except Exception as e:
            print(f"[ERROR] {exp_id}: {e}")

        done += 1

    print(f"\n{'='*60}")
    print(f"Completed: {done}/{total} experiments")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run_missing_experiments())
