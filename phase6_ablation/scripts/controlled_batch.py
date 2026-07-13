# -*- coding: utf-8 -*-
"""
Controlled Batch Test
=====================
1 model x 1 case x 2 configs x 3 runs = 6 experiments
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import run_single


async def controlled_batch():
    model = 'haiku30'
    case = 'case6'
    configs = ['baseline', 'full_reflexion']
    runs = [1, 2, 3]

    results = []

    for config in configs:
        print(f'\n{"="*70}')
        print(f'CONFIG: {config.upper()}')
        print("="*70)

        for run in runs:
            print(f'\n--- Run {run}/3 ---')
            result = await run_single(model, config, case, run)
            results.append({
                'config': config,
                'run': run,
                'success': result.success,
                'trials': result.trials_used,
                'time': result.total_time,
                'cost': result.total_cost
            })
            print(f'Result: {"SUCCESS" if result.success else "FAIL"} in {result.trials_used} trial(s)')

    # Summary
    print(f'\n{"="*70}')
    print('SUMMARY')
    print("="*70)

    for config in configs:
        config_results = [r for r in results if r['config'] == config]
        successes = sum(1 for r in config_results if r['success'])
        avg_time = sum(r['time'] for r in config_results) / len(config_results)
        avg_cost = sum(r['cost'] for r in config_results) / len(config_results)
        avg_trials = sum(r['trials'] for r in config_results) / len(config_results)

        print(f'{config:15} | Success: {successes}/3 | Avg Trials: {avg_trials:.1f} | Avg Time: {avg_time:.1f}s | Avg Cost: ${avg_cost:.4f}')


if __name__ == '__main__':
    asyncio.run(controlled_batch())
