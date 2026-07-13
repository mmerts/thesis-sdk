# -*- coding: utf-8 -*-
"""
Runner for Sonnet 4.5 and Opus 4.5 Experiments
===============================================

Runs experiments for the two premium models:
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929) - $3/$15 per MTok
- Claude Opus 4.5 (claude-opus-4-5-20251101) - $5/$25 per MTok

Matrix: 2 models x 2 configs x 8 cases x 10 runs = 320 experiments

Estimated Cost:
- Sonnet 4.5: ~$16-20
- Opus 4.5: ~$27-35
- Total: ~$45-55

Usage:
    python run_sonnet_opus.py                    # Run all 320 experiments
    python run_sonnet_opus.py --models sonnet45  # Only Sonnet
    python run_sonnet_opus.py --models opus45    # Only Opus
    python run_sonnet_opus.py --dry-run          # Show plan without running
    python run_sonnet_opus.py --runs 3           # Only 3 runs per config
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))

from runners.experiment_runner import ExperimentRunner


def load_checkpoint(results_dir: Path):
    """Load or create checkpoint."""
    checkpoint_file = results_dir / "checkpoint_sonnet_opus.json"
    if checkpoint_file.exists():
        with open(checkpoint_file, encoding='utf-8') as f:
            return json.load(f)
    return {
        "completed_ids": [],
        "start_time": datetime.now().isoformat(),
        "last_update": datetime.now().isoformat()
    }


def save_checkpoint(results_dir: Path, checkpoint: dict):
    """Save checkpoint."""
    results_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = results_dir / "checkpoint_sonnet_opus.json"
    checkpoint["last_update"] = datetime.now().isoformat()
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, indent=2)


def estimate_cost(models: list, configs: list, cases: list, runs: int) -> dict:
    """Estimate cost based on Haiku 4.5 reference data."""
    # Per-run costs from Haiku 4.5 experiments (baseline ~$0.08, reflexion ~$0.12)
    baseline_per_run = 0.08
    reflexion_per_run = 0.12

    # Cost multipliers relative to Haiku 4.5
    multipliers = {"sonnet45": 3.0, "opus45": 5.0}

    estimates = {}
    for model in models:
        mult = multipliers.get(model, 1.0)
        baseline_cost = len(cases) * runs * baseline_per_run * mult if "baseline" in configs else 0
        reflexion_cost = len(cases) * runs * reflexion_per_run * mult if "full_reflexion" in configs else 0
        estimates[model] = baseline_cost + reflexion_cost

    return estimates


async def run_experiments(
    models: list,
    configs: list,
    cases: list,
    runs: int,
    resume: bool = True
):
    """Run specified experiments."""
    results_dir = Path(__file__).parent / "results"
    raw_dir = results_dir / "raw"

    checkpoint = load_checkpoint(results_dir) if resume else {"completed_ids": []}
    completed = set(checkpoint.get("completed_ids", []))

    # Generate all experiment IDs
    all_experiments = []
    for model in models:
        for config in configs:
            for case in cases:
                for run in range(1, runs + 1):
                    exp_id = f"{model}_{config}_{case}_run{run}"
                    if exp_id not in completed:
                        all_experiments.append((exp_id, model, config, case, run))

    total = len(all_experiments)
    already_done = len(completed)

    print(f"\n[INFO] Already completed: {already_done}")
    print(f"[INFO] Remaining: {total}")

    if not all_experiments:
        print("\n[DONE] All experiments already completed!")
        return {"completed": already_done, "new": 0, "total_cost": 0}

    runner = ExperimentRunner(raw_dir)

    total_cost = 0
    success_count = 0

    for i, (exp_id, model_name, config_name, case_id, run_num) in enumerate(all_experiments):
        print(f"\n{'='*70}")
        print(f"[{i+1}/{total}] Running: {exp_id}")
        print(f"{'='*70}")

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
            save_checkpoint(results_dir, checkpoint)

            total_cost += result.total_cost
            if result.success:
                success_count += 1

            status = "SUCCESS" if result.success else "FAILED"
            print(f"[{status}] Trials: {result.trials_used}, Cost: ${result.total_cost:.4f}, Time: {result.total_time:.1f}s")

        except Exception as e:
            print(f"[ERROR] {exp_id}: {e}")
            import traceback
            traceback.print_exc()
            # Still mark as completed to avoid infinite retries
            completed.add(exp_id)
            checkpoint["completed_ids"] = list(completed)
            save_checkpoint(results_dir, checkpoint)

    return {
        "completed": len(completed),
        "new": total,
        "success": success_count,
        "total_cost": total_cost
    }


async def main():
    parser = argparse.ArgumentParser(
        description="Run Sonnet 4.5 and Opus 4.5 experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_sonnet_opus.py                      # Run all 320 experiments
  python run_sonnet_opus.py --models sonnet45    # Only Sonnet 4.5
  python run_sonnet_opus.py --models opus45      # Only Opus 4.5
  python run_sonnet_opus.py --runs 3             # 3 runs instead of 10
  python run_sonnet_opus.py --dry-run            # Preview without running
  python run_sonnet_opus.py --no-resume          # Start fresh
        """
    )
    parser.add_argument(
        "--models", nargs="+",
        default=["sonnet45", "opus45"],
        choices=["sonnet45", "opus45"],
        help="Models to run (default: both)"
    )
    parser.add_argument(
        "--configs", nargs="+",
        default=["baseline", "full_reflexion"],
        choices=["baseline", "full_reflexion"],
        help="Configurations to run (default: both)"
    )
    parser.add_argument(
        "--cases", nargs="+",
        default=[f"case{i}" for i in range(1, 9)],
        help="Cases to run (default: case1-case8)"
    )
    parser.add_argument(
        "--runs", type=int, default=10,
        help="Runs per configuration (default: 10)"
    )
    parser.add_argument(
        "--no-resume", action="store_true",
        help="Start fresh, ignore checkpoint"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show plan without executing"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # Calculate totals
    total = len(args.models) * len(args.configs) * len(args.cases) * args.runs
    cost_estimates = estimate_cost(args.models, args.configs, args.cases, args.runs)
    total_cost = sum(cost_estimates.values())

    # Print header
    print("\n" + "=" * 70)
    print("PHASE 6 ABLATION - SONNET 4.5 & OPUS 4.5 EXPERIMENTS")
    print("=" * 70)
    print(f"\nModels:  {', '.join(args.models)}")
    print(f"Configs: {', '.join(args.configs)}")
    print(f"Cases:   {', '.join(args.cases)}")
    print(f"Runs:    {args.runs} per config")
    print(f"\nTotal experiments: {total}")

    print("\n--- COST ESTIMATE ---")
    for model, cost in cost_estimates.items():
        print(f"  {model}: ~${cost:.2f}")
    print(f"  TOTAL:  ~${total_cost:.2f}")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY RUN] Experiments that would run:\n")
        count = 0
        for model in args.models:
            for config in args.configs:
                for case in args.cases:
                    for run in range(1, args.runs + 1):
                        print(f"  {model}_{config}_{case}_run{run}")
                        count += 1
        print(f"\nTotal: {count} experiments")
        return

    # Confirmation
    if not args.yes:
        confirm = input(f"\nProceed with {total} experiments (est. ${total_cost:.2f})? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    # Run
    summary = await run_experiments(
        models=args.models,
        configs=args.configs,
        cases=args.cases,
        runs=args.runs,
        resume=not args.no_resume
    )

    # Final report
    print("\n" + "=" * 70)
    print("FINAL REPORT")
    print("=" * 70)
    print(f"Completed: {summary['new']} new experiments")
    print(f"Success:   {summary.get('success', 0)}/{summary['new']}")
    print(f"Est. Cost: ${total_cost:.2f}")
    print(f"Act. Cost: ${summary['total_cost']:.4f}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
