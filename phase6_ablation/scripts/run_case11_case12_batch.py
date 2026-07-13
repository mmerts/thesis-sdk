# -*- coding: utf-8 -*-
"""
Batch Runner: Case11 + Case12 × 5 Models × 2 Configs × 10 Runs
==============================================================

Total: 2 cases × 5 models × 2 configs × 10 runs = 200 experiments
Estimated time: ~10-12 hours
Estimated cost: ~$60-80

Models: haiku30, haiku35, haiku45, sonnet45, opus45
Configs: two_try_no_reflection, full_reflexion
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

# Configuration
CASES = ["case11", "case12"]
MODELS = ["haiku45", "sonnet45", "opus45"]
CONFIGS = ["two_try_no_reflection", "full_reflexion"]
RUNS = 10

async def main():
    runner = ExperimentRunner()
    results_dir = Path(__file__).parent.parent / "results"

    # Checkpoint file
    checkpoint_file = results_dir / "checkpoint_case11_12.json"

    # Load checkpoint
    if checkpoint_file.exists():
        with open(checkpoint_file, encoding='utf-8') as f:
            checkpoint = json.load(f)
        completed = set(checkpoint.get("completed", []))
        print(f"[RESUME] Found {len(completed)} completed experiments")
    else:
        completed = set()
        checkpoint = {"completed": [], "start_time": datetime.now().isoformat()}

    # Build experiment list
    experiments = []
    for case in CASES:
        for model in MODELS:
            for config in CONFIGS:
                for run in range(1, RUNS + 1):
                    exp_id = f"{model}_{config}_{case}_run{run}"
                    if exp_id not in completed:
                        experiments.append((model, config, case, run, exp_id))

    total = len(experiments)
    print(f"\n{'='*70}")
    print(f"BATCH RUN: Case11 + Case12")
    print(f"{'='*70}")
    print(f"Cases: {CASES}")
    print(f"Models: {MODELS}")
    print(f"Configs: {CONFIGS}")
    print(f"Runs per config: {RUNS}")
    print(f"Total experiments: {total}")
    print(f"Already completed: {len(completed)}")
    print(f"Remaining: {total}")
    print(f"{'='*70}\n")

    # Results tracking
    summary = {
        "success": 0,
        "failed": 0,
        "total_cost": 0.0,
        "total_time": 0.0,
        "by_case": {},
        "by_model": {},
        "by_config": {}
    }

    for i, (model, config, case, run, exp_id) in enumerate(experiments, 1):
        print(f"\n{'='*70}")
        print(f"[{i}/{total}] {exp_id}")
        print(f"{'='*70}")

        try:
            result = await runner.run_experiment(
                model_name=model,
                config_name=config,
                case_id=case,
                run_id=run
            )

            # Update summary
            if result.success:
                summary["success"] += 1
            else:
                summary["failed"] += 1
            summary["total_cost"] += result.total_cost
            summary["total_time"] += result.total_time

            # Track by case
            if case not in summary["by_case"]:
                summary["by_case"][case] = {"success": 0, "total": 0}
            summary["by_case"][case]["total"] += 1
            if result.success:
                summary["by_case"][case]["success"] += 1

            # Track by model
            if model not in summary["by_model"]:
                summary["by_model"][model] = {"success": 0, "total": 0}
            summary["by_model"][model]["total"] += 1
            if result.success:
                summary["by_model"][model]["success"] += 1

            # Track by config
            if config not in summary["by_config"]:
                summary["by_config"][config] = {"success": 0, "total": 0}
            summary["by_config"][config]["total"] += 1
            if result.success:
                summary["by_config"][config]["success"] += 1

            # Save checkpoint
            completed.add(exp_id)
            checkpoint["completed"] = list(completed)
            checkpoint["last_update"] = datetime.now().isoformat()
            checkpoint["summary"] = summary
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)

            status = "SUCCESS" if result.success else "FAILED"
            print(f"\n>>> {status} | {result.trials_used} trials | {result.total_time:.1f}s | ${result.total_cost:.4f}")

        except Exception as e:
            print(f"\n>>> ERROR: {e}")
            summary["failed"] += 1

        # Brief pause between experiments
        await asyncio.sleep(3)

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Total: {summary['success'] + summary['failed']}")
    print(f"Success: {summary['success']}")
    print(f"Failed: {summary['failed']}")
    print(f"Total Cost: ${summary['total_cost']:.2f}")
    print(f"Total Time: {summary['total_time']/60:.1f} minutes")
    print(f"\nBy Case:")
    for case, stats in summary["by_case"].items():
        rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {case}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
    print(f"\nBy Model:")
    for model, stats in summary["by_model"].items():
        rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {model}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
    print(f"\nBy Config:")
    for config, stats in summary["by_config"].items():
        rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {config}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
    print(f"{'='*70}")

    # Save final summary
    summary_file = results_dir / f"summary_case11_12_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")

if __name__ == "__main__":
    asyncio.run(main())
