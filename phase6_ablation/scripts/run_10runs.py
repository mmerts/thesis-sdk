# -*- coding: utf-8 -*-
"""
Phase 6 - 10 Run Batch Script
==============================

3 run'dan 10 run'a genisletme icin batch script.
Mevcut 144 deney atlanir, ek 336 deney calistirilir.

Kullanim:
    python scripts/run_10runs.py

Tahmini:
    - Ek deney sayisi: 336 (7 run x 48 kombinasyon)
    - Tahmini sure: ~13 saat
    - Tahmini maliyet: ~$28
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.batch_runner import run_batch


async def main():
    print("=" * 70)
    print("PHASE 6 ABLATION STUDY - 10 RUN EXTENSION")
    print("=" * 70)
    print()
    print("Mevcut durum:")
    print("  - Tamamlanan: 144 deney (3 run)")
    print("  - Hedef: 480 deney (10 run)")
    print("  - Calistirilacak: 336 ek deney")
    print()
    print("Tahminler:")
    print("  - Sure: ~13 saat (ortalama 139s/deney)")
    print("  - Maliyet: ~$28 ek, toplam ~$40")
    print()
    print("Baslatmak icin Enter'a basin, iptal icin Ctrl+C...")

    try:
        input()
    except KeyboardInterrupt:
        print("\nIptal edildi.")
        return

    print("\nBaslatiliyor...\n")

    # Run with 10 runs, resume from checkpoint
    summary = await run_batch(
        models=None,      # All models: haiku30, haiku35, haiku45
        configs=None,     # All configs: baseline, full_reflexion
        cases=None,       # All cases: case1-case8
        runs=10,          # 10 runs per combination
        resume=True       # Resume from checkpoint (skip existing 144)
    )

    print("\n" + "=" * 70)
    print("TAMAMLANDI!")
    print("=" * 70)
    print(f"Toplam deney: {summary['total_experiments']}")
    print(f"Basarili: {summary['successful']}")
    print(f"Basarisiz: {summary['failed']}")
    print(f"Toplam maliyet: ${summary['total_cost']:.2f}")
    print(f"Toplam sure: {summary['total_time']/3600:.1f} saat")


if __name__ == "__main__":
    asyncio.run(main())
