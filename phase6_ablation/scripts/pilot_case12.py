# -*- coding: utf-8 -*-
"""Pilot: Case12 (ConfigMap + Selector) - Opus 4.5"""
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
        run_id=1
    )

    status1 = "SUCCESS" if result1.success else "FAILED"
    print(f"\n>>> Case12 TWO_TRY: {status1} | {result1.trials_used} trials | ${result1.total_cost:.4f}")

    await asyncio.sleep(5)

    # Test 2: full_reflexion
    print("\n" + "="*70)
    print("TEST 2: Haiku 4.5 + Case12 + FULL_REFLEXION")
    print("="*70)

    result2 = await runner.run_experiment(
        model_name="haiku45",
        config_name="full_reflexion",
        case_id="case12",
        run_id=1
    )

    status2 = "SUCCESS" if result2.success else "FAILED"
    print(f"\n>>> Case12 REFLEXION: {status2} | {result2.trials_used} trials | ${result2.total_cost:.4f}")

    # Summary
    print("\n" + "="*70)
    print("CASE12 PILOT SUMMARY (ConfigMap + Selector)")
    print("="*70)
    print(f"TWO_TRY:    {'SUCCESS' if result1.success else 'FAILED'} ({result1.trials_used} trials)")
    print(f"REFLEXION:  {'SUCCESS' if result2.success else 'FAILED'} ({result2.trials_used} trials)")

    if not result1.success and result2.success:
        print("\n*** REFLEXION BENEFIT DEMONSTRATED! ***")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
