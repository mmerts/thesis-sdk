# -*- coding: utf-8 -*-
"""Run 3 more Opus experiments for case1"""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from runners.experiment_runner import ExperimentRunner
from pathlib import Path


async def main():
    runner = ExperimentRunner(Path('results/raw'))

    print('Running Opus 4.5 baseline case1 - runs 2,3,4')
    print('='*50)

    for run in [2, 3, 4]:
        print(f'\n>>> Run {run}/4')
        result = await runner.run_experiment('opus45', 'baseline', 'case1', run)
        status = 'SUCCESS' if result.success else 'FAILED'
        print(f'    Result: {status} in {result.total_time:.1f}s')
        print(f'    Cost: ${result.total_cost:.4f}')
        print(f'    Trials: {result.trials_used}')

    print('\n' + '='*50)
    print('Done!')


if __name__ == '__main__':
    asyncio.run(main())
