#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 6 Ablation Study - Main Entry Point
==========================================

Usage:
    # Run single experiment
    python run_ablation.py --model haiku30 --config baseline --case case1 --run 1

    # Run full batch (all 144 experiments)
    python run_ablation.py --batch

    # Run batch with specific models
    python run_ablation.py --batch --models haiku30,haiku35

    # Resume interrupted batch
    python run_ablation.py --batch --resume
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import run_single
from runners.batch_runner import run_batch


async def main():
    parser = argparse.ArgumentParser(description="Phase 6 Ablation Study")

    # Single experiment args
    parser.add_argument("--model", type=str, help="Model: haiku30, haiku35, haiku45")
    parser.add_argument("--config", type=str, help="Config: baseline, full_reflexion")
    parser.add_argument("--case", type=str, help="Case: case1, case2, ..., case8")
    parser.add_argument("--run", type=int, default=1, help="Run number")

    # Batch args
    parser.add_argument("--batch", action="store_true", help="Run full batch")
    parser.add_argument("--models", type=str, help="Comma-separated models for batch")
    parser.add_argument("--configs", type=str, help="Comma-separated configs for batch")
    parser.add_argument("--cases", type=str, help="Comma-separated cases for batch")
    parser.add_argument("--runs", type=int, default=3, help="Runs per config")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")

    args = parser.parse_args()

    if args.batch:
        # Parse optional filters
        models = args.models.split(",") if args.models else None
        configs = args.configs.split(",") if args.configs else None
        cases = args.cases.split(",") if args.cases else None

        await run_batch(
            models=models,
            configs=configs,
            cases=cases,
            runs=args.runs,
            resume=args.resume
        )

    elif args.model and args.config and args.case:
        result = await run_single(
            model=args.model,
            config=args.config,
            case=args.case,
            run=args.run
        )

        print(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Trials: {result.trials_used}")
        print(f"Time: {result.total_time:.1f}s")
        print(f"Cost: ${result.total_cost:.4f}")

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python run_ablation.py --model haiku30 --config baseline --case case1")
        print("  python run_ablation.py --batch")
        print("  python run_ablation.py --batch --models haiku30,haiku35 --cases case1,case2")


if __name__ == "__main__":
    asyncio.run(main())
