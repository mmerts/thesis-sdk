# -*- coding: utf-8 -*-
"""Haiku 3.0 - Complete missing tests (26 tests needed)."""
import asyncio
import json
import glob
from runners.experiment_runner import run_single


async def run_haiku30_missing():
    """Run all missing Haiku 3.0 tests to reach 48 total."""

    # Find existing tests
    files = glob.glob('results/raw/haiku30/**/*.json', recursive=True)
    existing = set()
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
            key = (data['case_id'], data['config'], data['run_id'])
            existing.add(key)

    print(f'Existing Haiku 3.0 tests: {len(existing)}')

    # Find missing tests
    missing = []
    for case in ['case1','case2','case3','case4','case5','case6','case7','case8']:
        for run in [1, 2, 3]:
            for config in ['baseline', 'full_reflexion']:
                key = (case, config, run)
                if key not in existing:
                    missing.append((case, config, run))

    print(f'Missing tests: {len(missing)}')
    results = []

    for i, (case, config, run_id) in enumerate(missing):
        print('\n' + '=' * 60)
        print(f'[{i+1}/{len(missing)}] {case.upper()} - HAIKU 3.0 - {config.upper()} - RUN {run_id}')
        print('=' * 60)

        result = await run_single(
            model='haiku30',
            config=config,
            case=case,
            run=run_id
        )
        status = 'SUCCESS' if result.success else 'FAIL'
        print(f'>>> {config.upper()} RUN {run_id}: {status} | {result.trials_used} trial(s) | {result.total_time:.1f}s | ${result.total_cost:.4f} <<<')

        results.append({
            'case': case,
            'config': config,
            'run': run_id,
            'success': status,
            'cost': result.total_cost
        })

    print('\n' + '=' * 60)
    print('FINAL SUMMARY - HAIKU 3.0 MISSING TESTS')
    print('=' * 60)
    success_count = sum(1 for r in results if r['success'] == 'SUCCESS')
    print(f'Success: {success_count}/{len(results)}')
    for r in results:
        print(f"  {r['case']} {r['config']} Run {r['run']}: {r['success']} | ${r['cost']:.4f}")


if __name__ == "__main__":
    asyncio.run(run_haiku30_missing())
