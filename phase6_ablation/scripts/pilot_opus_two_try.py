# -*- coding: utf-8 -*-
"""Pilot: Opus 4.5 + Case11 & Case12 + two_try_no_reflection"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

async def main():
    runner = ExperimentRunner()

    # Test 1: Case11 two_try
    print("\n" + "="*70)
    print("TEST 1: Opus 4.5 + Case11 + TWO_TRY_NO_REFLECTION")
    print("="*70)

    result1 = await runner.run_experiment(
        model_name="opus45",
        config_name="two_try_no_reflection",
        case_id="case11",
        run_id=96
    )

    print(f"\n>>> Case11 TWO_TRY: {'SUCCESS' if result1.success else 'FAILED'} | {result1.trials_used} trials")

    await asyncio.sleep(5)

    # Test 2: Case12 two_try
    print("\n" + "="*70)
    print("TEST 2: Opus 4.5 + Case12 + TWO_TRY_NO_REFLECTION")
    print("="*70)

    result2 = await runner.run_experiment(
        model_name="opus45",
        config_name="two_try_no_reflection",
        case_id="case12",
        run_id=96
    )

    print(f"\n>>> Case12 TWO_TRY: {'SUCCESS' if result2.success else 'FAILED'} | {result2.trials_used} trials")

    # Summary
    print("\n" + "="*70)
    print("OPUS TWO_TRY_NO_REFLECTION SUMMARY")
    print("="*70)
    print(f"Case11: {'✓ SUCCESS' if result1.success else '✗ FAILED'} ({result1.trials_used} trials)")
    print(f"Case12: {'✓ SUCCESS' if result2.success else '✗ FAILED'} ({result2.trials_used} trials)")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
