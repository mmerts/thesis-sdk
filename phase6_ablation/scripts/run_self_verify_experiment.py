#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R3.2 Self-Verify Ablation Deneyi Runner
========================================

baseline_self_verify config'i: tek trial, ama Actor'in verify/retry yasagi
kaldirilmis (en fazla 3 ic dongu). Amac: +29.8pp retry etkisinin ne kadari
dis dogrulamadan geliyor?

Matris: 3 canli model x case1-8 (single-fault) x 5 run = 120 run.
case9/10 EKLENMEZ: Aralik baseline kollari decoy-varyantla kosuldu,
guncel varyantla karsilastirilamaz. case1-8 donemler arasi stabil.

Resume: sonuc JSON'u zaten varsa o run atlanir.

Kullanim:
  python phase6_ablation/scripts/run_self_verify_experiment.py --dry-run
  python phase6_ablation/scripts/run_self_verify_experiment.py --pilot
  python phase6_ablation/scripts/run_self_verify_experiment.py
"""
import argparse
import asyncio
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from runners.experiment_runner import ExperimentRunner

CONFIG = "baseline_self_verify"
RESULTS_RAW = Path(__file__).parent.parent / "results" / "raw"

CASES = [f"case{i}" for i in range(1, 9)]
MODELS = ["haiku45", "sonnet45", "opus45"]
N_RUNS = 5

MATRIX = {case_id: {m: N_RUNS for m in MODELS} for case_id in CASES}


def build_todo():
    """(model, case, run_id) listesi - tamamlanmislar haric."""
    todo, done = [], []
    for case_id, models in MATRIX.items():
        for model, n_runs in models.items():
            for run_id in range(1, n_runs + 1):
                pattern = f"{model}_{CONFIG}_{case_id}_run{run_id}_*.json"
                if list((RESULTS_RAW / model).glob(pattern)):
                    done.append((model, case_id, run_id))
                else:
                    todo.append((model, case_id, run_id))
    return todo, done


def precheck() -> bool:
    """Minikube + kubectl erisimini dogrula."""
    try:
        r = subprocess.run(["kubectl", "get", "nodes"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print(f"[HATA] kubectl calismiyor: {r.stderr.strip()[:200]}")
            return False
        print(f"[OK] kubectl: {r.stdout.strip().splitlines()[-1]}")
        return True
    except Exception as e:
        print(f"[HATA] kubectl kontrolu: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true",
                        help="Sadece ilk eksik run'i kos (case1/haiku45)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Kosulacak listeyi yaz, hicbir sey calistirma")
    args = parser.parse_args()

    todo, done = build_todo()
    total = sum(n for models in MATRIX.values() for n in models.values())

    print("=" * 70)
    print(f"R3.2 SELF-VERIFY DENEYI  [{datetime.now().isoformat(timespec='seconds')}]")
    print(f"Toplam matris: {total} | Tamamlanan: {len(done)} | Kalan: {len(todo)}")
    print("=" * 70)

    if args.dry_run:
        for model, case_id, run_id in todo:
            print(f"  TODO {model:9} {case_id:7} run{run_id}")
        return

    if not todo:
        print("Tum matris tamamlanmis. Yapilacak is yok.")
        return

    if not precheck():
        sys.exit(1)

    if args.pilot:
        pilot = [t for t in todo if t[0] == "haiku45" and t[1] == "case1"]
        todo = pilot[:1] if pilot else todo[:1]
        print(f"[PILOT] Tek run: {todo[0]}")

    runner = ExperimentRunner()
    batch_cost, ok, fail = 0.0, 0, 0
    batch_start = time.time()

    for i, (model, case_id, run_id) in enumerate(todo, 1):
        label = f"{model}_{CONFIG}_{case_id}_run{run_id}"
        print(f"\n[{i}/{len(todo)}] {label}  "
              f"(gecen: {(time.time()-batch_start)/60:.0f} dk, maliyet: ${batch_cost:.2f})")
        try:
            result = await runner.run_experiment(
                model_name=model,
                config_name=CONFIG,
                case_id=case_id,
                run_id=run_id
            )
            batch_cost += result.total_cost
            if result.final_status.startswith("Error:"):
                fail += 1
                print(f"[SETUP-HATA] {label}: {result.final_status}")
            else:
                ok += 1
        except Exception as e:
            fail += 1
            print(f"[HATA] {label}: {e}")
            # Dosya olusmadigi icin bir sonraki calistirmada yeniden denenir
        await asyncio.sleep(2)

    elapsed = (time.time() - batch_start) / 3600
    print("\n" + "=" * 70)
    print(f"BITTI: {ok} tamam, {fail} hatali | ${batch_cost:.2f} | {elapsed:.1f} saat")
    remaining, _ = build_todo()
    if remaining:
        print(f"[UYARI] {len(remaining)} run eksik kaldi - script'i yeniden calistir.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
