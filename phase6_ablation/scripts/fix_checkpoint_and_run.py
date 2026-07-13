# -*- coding: utf-8 -*-
"""
Fix checkpoint by removing missing file entries, then run missing experiments.
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


def extract_exp_id(filename: str) -> str:
    """Extract experiment ID from filename."""
    # haiku45_baseline_case7_run9_20251216_061019.json -> haiku45_baseline_case7_run9
    parts = filename.replace('.json', '').split('_')

    if 'baseline' in filename:
        idx = parts.index('baseline')
        return '_'.join(parts[:idx+3])  # model_baseline_caseX_runY
    else:
        idx = parts.index('reflexion')
        return '_'.join(parts[:idx+3])  # model_full_reflexion_caseX_runY


def fix_checkpoint():
    """Remove entries from checkpoint that don't have corresponding files."""
    checkpoint_file = Path(__file__).parent / "results" / "checkpoint.json"
    raw_dir = Path(__file__).parent / "results" / "raw"

    # Load checkpoint
    with open(checkpoint_file) as f:
        checkpoint = json.load(f)

    # Get all existing file IDs
    existing_ids = set()
    for json_file in raw_dir.rglob("*.json"):
        exp_id = extract_exp_id(json_file.name)
        existing_ids.add(exp_id)

    print(f"Files found: {len(existing_ids)}")
    print(f"Checkpoint entries: {len(checkpoint['completed_ids'])}")

    # Keep only entries that have files
    original_count = len(checkpoint['completed_ids'])
    checkpoint['completed_ids'] = [
        eid for eid in checkpoint['completed_ids']
        if eid in existing_ids
    ]
    checkpoint['completed_experiments'] = len(checkpoint['completed_ids'])

    removed = original_count - len(checkpoint['completed_ids'])
    print(f"Removed {removed} orphan entries")

    # Save fixed checkpoint
    checkpoint['last_update'] = datetime.now().isoformat()
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)

    print(f"Checkpoint fixed: {checkpoint['completed_experiments']} entries")
    return checkpoint


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


async def run_missing_experiments(checkpoint: dict):
    """Run all missing Haiku 4.5 experiments."""
    results_dir = Path(__file__).parent / "results" / "raw"
    checkpoint_file = Path(__file__).parent / "results" / "checkpoint.json"

    completed = set(checkpoint.get("completed_ids", []))

    # Generate all expected Haiku 4.5 experiment IDs
    all_expected = []
    for config in ["baseline", "full_reflexion"]:
        for case_num in range(1, 9):
            for run in range(1, 11):
                exp_id = f"haiku45_{config}_case{case_num}_run{run}"
                all_expected.append((exp_id, "haiku45", config, f"case{case_num}", run))

    # Filter to missing only
    missing = [(eid, m, c, cs, r) for eid, m, c, cs, r in all_expected if eid not in completed]

    print(f"\nMissing experiments: {len(missing)}")
    if not missing:
        print("All experiments completed!")
        return

    runner = ExperimentRunner(results_dir)

    total = len(missing)
    done = 0

    for exp_id, model_name, config_name, case_id, run_num in missing:
        print(f"\n{'='*60}")
        print(f"[{done+1}/{total}] Running: {exp_id}")
        print(f"{'='*60}")

        try:
            result = await runner.run_experiment(
                model_name=model_name,
                config_name=config_name,
                case_id=case_id,
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
            import traceback
            traceback.print_exc()

        done += 1

    print(f"\n{'='*60}")
    print(f"Completed: {done}/{total} experiments")
    print(f"{'='*60}")


async def main():
    print("Step 1: Fixing checkpoint...")
    checkpoint = fix_checkpoint()

    print("\nStep 2: Running missing experiments...")
    await run_missing_experiments(checkpoint)


if __name__ == "__main__":
    asyncio.run(main())
