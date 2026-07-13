# -*- coding: utf-8 -*-
"""
Batch Runner - Phase 6
=======================

Runs the full experiment matrix with checkpoint support.
Matrix: 3 models x 2 configs x 8 cases x 3 runs = 144 experiments
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.experiment_runner import ExperimentRunner, ExperimentResult
from configs.experiment_configs import (
    ALL_MODEL_CONFIGS, ALL_ABLATION_CONFIGS, TEST_CASES,
    ModelConfig, AblationConfig, TestCase
)


@dataclass
class BatchProgress:
    """Tracks batch progress for checkpointing."""
    total_experiments: int
    completed_experiments: int
    completed_ids: List[str]
    start_time: str
    last_update: str


class BatchRunner:
    """
    Runs full experiment matrix with checkpoint/resume support.
    """

    def __init__(
        self,
        models: Optional[List[str]] = None,
        configs: Optional[List[str]] = None,
        cases: Optional[List[str]] = None,
        runs: int = 3,
        results_dir: Optional[Path] = None
    ):
        """
        Initialize batch runner.

        Args:
            models: List of model names (default: all)
            configs: List of config names (default: all)
            cases: List of case IDs (default: all)
            runs: Number of runs per configuration
        """
        self.models = models or [m.name for m in ALL_MODEL_CONFIGS]
        self.configs = configs or [c.name for c in ALL_ABLATION_CONFIGS]
        self.cases = cases or [c.case_id for c in TEST_CASES]
        self.runs = runs

        self.results_dir = results_dir or Path(__file__).parent.parent / "results"
        self.checkpoint_file = self.results_dir / "checkpoint.json"

        self.experiment_runner = ExperimentRunner(self.results_dir / "raw")

    def _generate_experiment_ids(self) -> List[str]:
        """Generate all experiment IDs in the matrix."""
        ids = []
        for model in self.models:
            for config in self.configs:
                for case in self.cases:
                    for run in range(1, self.runs + 1):
                        ids.append(f"{model}_{config}_{case}_run{run}")
        return ids

    def _load_checkpoint(self) -> Optional[BatchProgress]:
        """Load checkpoint if exists."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file) as f:
                data = json.load(f)
                return BatchProgress(**data)
        return None

    def _save_checkpoint(self, progress: BatchProgress) -> None:
        """Save checkpoint."""
        self.results_dir.mkdir(parents=True, exist_ok=True)
        progress.last_update = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(asdict(progress), f, indent=2)

    async def run_all(self, resume: bool = True) -> Dict[str, any]:
        """
        Run all experiments in the matrix.

        Args:
            resume: If True, resume from checkpoint

        Returns:
            Summary of results
        """
        all_ids = self._generate_experiment_ids()
        total = len(all_ids)

        print(f"\n{'=' * 70}")
        print("PHASE 6 ABLATION STUDY - BATCH RUNNER")
        print("=" * 70)
        print(f"Models: {self.models}")
        print(f"Configs: {self.configs}")
        print(f"Cases: {self.cases}")
        print(f"Runs per config: {self.runs}")
        print(f"Total experiments: {total}")
        print("=" * 70)

        # Load or create checkpoint
        progress = None
        if resume:
            progress = self._load_checkpoint()

        if progress and progress.completed_ids:
            print(f"\n[RESUME] Found checkpoint with {len(progress.completed_ids)} completed")
            remaining_ids = [id for id in all_ids if id not in progress.completed_ids]
        else:
            progress = BatchProgress(
                total_experiments=total,
                completed_experiments=0,
                completed_ids=[],
                start_time=datetime.now().isoformat(),
                last_update=datetime.now().isoformat()
            )
            remaining_ids = all_ids

        print(f"[INFO] {len(remaining_ids)} experiments remaining\n")

        # Run experiments
        results = []

        for i, exp_id in enumerate(remaining_ids):
            # Parse experiment ID
            parts = exp_id.rsplit("_run", 1)
            model_config_case = parts[0]
            run_id = int(parts[1])

            # Smart parsing: find model, config, and case
            # Format: {model}_{config}_{case} where config can be "baseline", "full_reflexion", or "two_try_no_reflection"
            if "_two_try_no_reflection_" in model_config_case:
                model = model_config_case.split("_two_try_no_reflection_")[0]
                config = "two_try_no_reflection"
                case = model_config_case.split("_two_try_no_reflection_")[1]
            elif "_full_reflexion_" in model_config_case:
                model = model_config_case.split("_full_reflexion_")[0]
                config = "full_reflexion"
                case = model_config_case.split("_full_reflexion_")[1]
            elif "_baseline_" in model_config_case:
                model = model_config_case.split("_baseline_")[0]
                config = "baseline"
                case = model_config_case.split("_baseline_")[1]
            else:
                # Fallback to old method
                model, config, case = model_config_case.split("_", 2)

            # Progress indicator
            completed = len(progress.completed_ids)
            print(f"\n[{completed + 1}/{total}] Running: {exp_id}")

            try:
                result = await self.experiment_runner.run_experiment(
                    model_name=model,
                    config_name=config,
                    case_id=case,
                    run_id=run_id
                )
                results.append(result)

                # Update checkpoint
                progress.completed_ids.append(exp_id)
                progress.completed_experiments = len(progress.completed_ids)
                self._save_checkpoint(progress)

                status = "SUCCESS" if result.success else "FAILED"
                print(f"[{status}] {exp_id} - {result.total_time:.1f}s, ${result.total_cost:.4f}")

            except Exception as e:
                print(f"[ERROR] {exp_id}: {str(e)}")
                # Still mark as completed to avoid infinite retry
                progress.completed_ids.append(exp_id)
                self._save_checkpoint(progress)

        # Generate summary
        summary = self._generate_summary(results)
        self._save_summary(summary)

        return summary

    def _generate_summary(self, results: List[ExperimentResult]) -> Dict[str, any]:
        """Generate summary statistics."""
        summary = {
            "total_experiments": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_cost": sum(r.total_cost for r in results),
            "total_time": sum(r.total_time for r in results),
            "by_model": {},
            "by_config": {},
            "by_case": {},
            "timestamp": datetime.now().isoformat()
        }

        # Group by model
        for model in self.models:
            model_results = [r for r in results if r.model == model]
            summary["by_model"][model] = {
                "total": len(model_results),
                "success": sum(1 for r in model_results if r.success),
                "success_rate": sum(1 for r in model_results if r.success) / len(model_results) if model_results else 0,
                "avg_cost": sum(r.total_cost for r in model_results) / len(model_results) if model_results else 0,
                "avg_time": sum(r.total_time for r in model_results) / len(model_results) if model_results else 0
            }

        # Group by config
        for config in self.configs:
            config_results = [r for r in results if r.config == config]
            summary["by_config"][config] = {
                "total": len(config_results),
                "success": sum(1 for r in config_results if r.success),
                "success_rate": sum(1 for r in config_results if r.success) / len(config_results) if config_results else 0,
                "avg_trials": sum(r.trials_used for r in config_results) / len(config_results) if config_results else 0
            }

        # Group by case
        for case in self.cases:
            case_results = [r for r in results if r.case_id == case]
            summary["by_case"][case] = {
                "total": len(case_results),
                "success": sum(1 for r in case_results if r.success),
                "success_rate": sum(1 for r in case_results if r.success) / len(case_results) if case_results else 0
            }

        return summary

    def _save_summary(self, summary: Dict) -> None:
        """Save summary to file."""
        summary_dir = self.results_dir / "aggregated"
        summary_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = summary_dir / f"summary_{timestamp}.json"

        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[SAVED] Summary: {filepath}")

    def print_summary(self, summary: Dict) -> None:
        """Print summary to console."""
        print(f"\n{'=' * 70}")
        print("BATCH RUN SUMMARY")
        print("=" * 70)
        print(f"Total: {summary['total_experiments']}")
        print(f"Success: {summary['successful']} ({100*summary['successful']/summary['total_experiments']:.1f}%)")
        print(f"Failed: {summary['failed']}")
        print(f"Total Cost: ${summary['total_cost']:.4f}")
        print(f"Total Time: {summary['total_time']:.1f}s ({summary['total_time']/60:.1f} min)")

        print("\nBy Model:")
        for model, stats in summary['by_model'].items():
            print(f"  {model}: {stats['success']}/{stats['total']} ({100*stats['success_rate']:.1f}%)")

        print("\nBy Config:")
        for config, stats in summary['by_config'].items():
            print(f"  {config}: {stats['success']}/{stats['total']} ({100*stats['success_rate']:.1f}%)")

        print("=" * 70)


async def run_batch(
    models: Optional[List[str]] = None,
    configs: Optional[List[str]] = None,
    cases: Optional[List[str]] = None,
    runs: int = 3,
    resume: bool = True
) -> Dict:
    """Convenience function to run batch."""
    runner = BatchRunner(models=models, configs=configs, cases=cases, runs=runs)
    summary = await runner.run_all(resume=resume)
    runner.print_summary(summary)
    return summary
