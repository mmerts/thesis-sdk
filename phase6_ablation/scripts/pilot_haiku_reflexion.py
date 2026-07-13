# -*- coding: utf-8 -*-
"""Pilot: Haiku 4.5 + Case11 + full_reflexion"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

async def main():
    runner = ExperimentRunner()
    print("="*70)
    print("PILOT: Haiku 4.5 + Case11 + FULL_REFLEXION")
    print("="*70)

    result = await runner.run_experiment(
        model_name="haiku45",
        config_name="full_reflexion",
        case_id="case11",
        run_id=99
    )

    print("\n" + "="*70)
    print(f"SUCCESS: {result.success}")
    print(f"Trials: {result.trials_used}")
    print(f"Time: {result.total_time:.1f}s")
    print(f"Cost: ${result.total_cost:.4f}")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
