#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R2.1 Feedback-Only Kontrol Deneyi Runner
=========================================

two_try_feedback config'i ile two_try_no_reflection matrisini aynalar:
  case9:  haiku45=25, sonnet45=25, opus45=15
  case10: haiku45=15, sonnet45=15, opus45=15
  case11: haiku45=11, sonnet45=10, opus45=11
Toplam: 142 run, ~$28-33, ~5.5-6.5 saat.

Resume: sonuç JSON'u zaten varsa o run atlanır. Script'i yeniden
çalıştırmak eksikleri tamamlar.

Kullanım:
  python phase6_ablation/scripts/run_feedback_experiment.py --dry-run   # plan
  python phase6_ablation/scripts/run_feedback_experiment.py --pilot     # 1 run
  python phase6_ablation/scripts/run_feedback_experiment.py             # tam batch
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

CONFIG = "two_try_feedback"
RESULTS_RAW = Path(__file__).parent.parent / "results" / "raw"

# two_try_no_reflection matrisinin aynası (DB'den 2026-08-20 doğrulandı)
MATRIX = {
    "case9":  {"haiku45": 25, "sonnet45": 25, "opus45": 15},
    "case10": {"haiku45": 15, "sonnet45": 15, "opus45": 15},
    "case11": {"haiku45": 11, "sonnet45": 10, "opus45": 11},
}


def build_todo():
    """(model, case, run_id) listesi - tamamlanmışlar hariç."""
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
    """Minikube + kubectl erişimini doğrula."""
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
                        help="Sadece ilk eksik run'i kos (case9/haiku45)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Kosulacak listeyi yaz, hicbir sey calistirma")
    args = parser.parse_args()

    todo, done = build_todo()
    total = sum(n for models in MATRIX.values() for n in models.values())

    print("=" * 70)
    print(f"R2.1 FEEDBACK-ONLY DENEYI  [{datetime.now().isoformat(timespec='seconds')}]")
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
        # Pilot: case9/haiku45'in ilk eksik run'i
        pilot = [t for t in todo if t[0] == "haiku45" and t[1] == "case9"]
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
