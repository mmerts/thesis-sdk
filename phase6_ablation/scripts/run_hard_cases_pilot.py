# -*- coding: utf-8 -*-
"""
Hard Cases Pilot Test Runner
=============================

Tests cases 9, 10, 11 with Haiku 4.5 and Haiku 3.5.
Matrix: 2 models x 3 cases x 2 configs x 10 runs = 120 experiments

Purpose: Test if Reflexion helps on hard cases where simple retry might not be enough.
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.batch_runner import BatchRunner


async def main():
    print("""
======================================================================
          MULTI-BUG CASES PILOT TEST - Phase 8
======================================================================
  Models: Haiku 4.5, Haiku 3.5
  Cases:  case12 (2 bugs), case13 (3 bugs), case14 (4 bugs)
  Configs: two_try_no_reflection, full_reflexion
  Runs:   10 per config
  Total:  2 x 3 x 2 x 10 = 120 experiments

  Estimated cost: ~$15-20
  Estimated time: ~3-4 hours
======================================================================
    """)

    # Configure pilot test - only two-try vs reflexion (multi-bug cases)
    runner = BatchRunner(
        models=["haiku45", "haiku35"],
        configs=["two_try_no_reflection", "full_reflexion"],
        cases=["case12", "case13", "case14"],
        runs=10
    )

    # Run with checkpoint support
    results = await runner.run_all(resume=True)

    print("\n" + "=" * 70)
    print("PILOT TEST COMPLETE")
    print("=" * 70)

    return results


if __name__ == "__main__":
    asyncio.run(main())
