# -*- coding: utf-8 -*-
"""Batch Test: Case12 - All models, two_try vs full_reflexion"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner

MODELS = ["haiku45", "sonnet45", "opus45"]  # haiku35 tamamlandı
CONFIGS = ["two_try_no_reflection", "full_reflexion"]
RUNS = 10

# Checkpoint - 8 Ocak 2026 (son durum)
SKIP_UNTIL = {
    "haiku45": {
        "two_try_no_reflection": 10,  # tamamlandı
        "full_reflexion": 10,  # tamamlandı
    },
    "sonnet45": {
        "two_try_no_reflection": 10,  # tamamlandı
        "full_reflexion": 10,  # tamamlandı
    },
    "opus45": {
        "two_try_no_reflection": 4,  # run 5'ten devam
        "full_reflexion": 1,  # run 2'den devam
    },
}

async def main():
    runner = ExperimentRunner()
    results = {}

    # Kalan deney sayısını hesapla
    remaining = 0
    for model in MODELS:
        for config in CONFIGS:
            skip = SKIP_UNTIL.get(model, {}).get(config, 0)
            remaining += RUNS - skip

    current = 0

    for model in MODELS:
        results[model] = {}
        for config in CONFIGS:
            results[model][config] = {"success": 0, "fail": 0}
            skip_count = SKIP_UNTIL.get(model, {}).get(config, 0)

            for run_id in range(1, RUNS + 1):
                # Tamamlanmış deneyleri atla
                if run_id <= skip_count:
                    continue

                current += 1
                print(f"\n[{current}/{remaining}] {model} + {config} + case12 (run {run_id})")

                try:
                    result = await runner.run_experiment(
                        model_name=model,
                        config_name=config,
                        case_id="case12",
                        run_id=run_id
                    )

                    if result.success:
                        results[model][config]["success"] += 1
                        print(f"  -> SUCCESS (trial {result.trials_used})")
                    else:
                        results[model][config]["fail"] += 1
                        print(f"  -> FAILED")

                except Exception as e:
                    print(f"  -> ERROR: {e}")
                    results[model][config]["fail"] += 1

                await asyncio.sleep(3)

    # Summary (sadece bu session'da çalışan modeller)
    print("\n" + "="*70)
    print("CASE12 BATCH TEST SUMMARY (this session)")
    print("="*70)
    print(f"{'Model':<12} {'two_try':<15} {'reflexion':<15} {'Benefit'}")
    print("-"*70)

    for model in MODELS:
        skip_two = SKIP_UNTIL.get(model, {}).get("two_try_no_reflection", 0)
        skip_ref = SKIP_UNTIL.get(model, {}).get("full_reflexion", 0)
        runs_two = RUNS - skip_two
        runs_ref = RUNS - skip_ref

        two_try = results[model]["two_try_no_reflection"]["success"]
        reflexion = results[model]["full_reflexion"]["success"]
        benefit = reflexion - two_try
        sign = "+" if benefit > 0 else ""
        print(f"{model:<12} {two_try}/{runs_two}{'':<10} {reflexion}/{runs_ref}{'':<10} {sign}{benefit}")

    print("="*70)
    print("Not: haiku35 sonuçları (0/10 two_try, 1/10 reflexion) önceki session'da tamamlandı")

if __name__ == "__main__":
    asyncio.run(main())
