# -*- coding: utf-8 -*-
"""Pilot: Haiku 4.5 + Case12 + both configs (sequential)"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

async def main():
    runner = ExperimentRunner()

    # Test 1: two_try_no_reflection
    print("\n" + "="*70)
    print("TEST 1: Haiku 4.5 + Case12 + TWO_TRY_NO_REFLECTION")
    print("="*70)

    result1 = await runner.run_experiment(
        model_name="haiku45",
        config_name="two_try_no_reflection",
        case_id="case12",
        run_id=98
    )

    print(f"\n>>> TWO_TRY: {'SUCCESS' if result1.success else 'FAILED'} | {result1.trials_used} trials | {result1.total_time:.1f}s | ${result1.total_cost:.4f}")

    # Wait a bit between tests
    print("\n[Waiting 5s before next test...]")
    await asyncio.sleep(5)

    # Test 2: full_reflexion
    print("\n" + "="*70)
    print("TEST 2: Haiku 4.5 + Case12 + FULL_REFLEXION")
    print("="*70)

    result2 = await runner.run_experiment(
        model_name="haiku45",
        config_name="full_reflexion",
        case_id="case12",
        run_id=98
    )

    print(f"\n>>> REFLEXION: {'SUCCESS' if result2.success else 'FAILED'} | {result2.trials_used} trials | {result2.total_time:.1f}s | ${result2.total_cost:.4f}")

    # Summary
    print("\n" + "="*70)
    print("PILOT SUMMARY - CASE12 HAIKU 4.5")
    print("="*70)
    print(f"two_try_no_reflection: {'✓ SUCCESS' if result1.success else '✗ FAILED'}")
    print(f"full_reflexion:        {'✓ SUCCESS' if result2.success else '✗ FAILED'}")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
