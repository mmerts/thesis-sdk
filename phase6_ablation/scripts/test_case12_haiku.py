# -*- coding: utf-8 -*-
"""Quick test for Case12 with Haiku 4.5"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner


async def main():
    runner = ExperimentRunner()

    print("Testing Case12 (Env + Liveness) with Haiku 4.5 + full_reflexion")
    print("=" * 70)

    result = await runner.run_experiment(
        model_name="haiku45",
        config_name="full_reflexion",
        case_id="case12",
        run_id=1
    )

    print("\n" + "=" * 70)
    print("RESULT SUMMARY")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Trials Used: {result.trials_used}")
    print(f"Final Status: {result.final_status}")
    print(f"Total Time: {result.total_time:.1f}s")
    print(f"Total Cost: ${result.total_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
