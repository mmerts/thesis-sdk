# -*- coding: utf-8 -*-
"""
Experiment Runner - Phase 6
============================

Runs single experiments with proper setup and teardown.
"""

import asyncio
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.reflexion_loop import ReflexionLoop, ReflexionResult
from configs.experiment_configs import (
    AblationConfig, ModelConfig, TestCase,
    get_ablation_config, get_model_config, get_test_case
)


@dataclass
class ExperimentResult:
    """Result of a single experiment."""
    # Identification
    experiment_id: str
    model: str
    config: str
    case_id: str
    run_id: int

    # Outcome
    success: bool
    trials_used: int
    final_status: str

    # Metrics
    total_time: float
    total_cost: float
    total_tokens: int

    # Trial details
    trial_details: list

    # Metadata
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperimentRunner:
    """
    Runs a single experiment (model + config + case + run).
    """

    def __init__(self, results_dir: Optional[Path] = None):
        self.results_dir = results_dir or Path(__file__).parent.parent / "results" / "raw"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def run_experiment(
        self,
        model_name: str,
        config_name: str,
        case_id: str,
        run_id: int = 1
    ) -> ExperimentResult:
        """
        Run a single experiment.

        Args:
            model_name: Model name (haiku30, haiku35, haiku45)
            config_name: Config name (baseline, full_reflexion)
            case_id: Test case ID (case1, case2, ...)
            run_id: Run number for this configuration

        Returns:
            ExperimentResult with all metrics
        """
        model_config = get_model_config(model_name)
        ablation_config = get_ablation_config(config_name)
        test_case = get_test_case(case_id)

        experiment_id = f"{model_name}_{config_name}_{case_id}_run{run_id}"

        print(f"\n{'=' * 70}")
        print(f"EXPERIMENT: {experiment_id}")
        print(f"Model: {model_config.model_id}")
        print(f"Config: {ablation_config.name} ({ablation_config.description})")
        print(f"Case: {test_case.name} ({test_case.difficulty})")
        print("=" * 70)

        # Setup test case
        pod_name = await self._setup_test_case(test_case)
        if not pod_name:
            return self._create_error_result(experiment_id, model_name, config_name, case_id, run_id, "Setup failed")

        try:
            # Run Reflexion loop
            loop = ReflexionLoop(
                max_trials=ablation_config.max_trials,
                reflection_enabled=ablation_config.reflection_enabled,
                model=model_config.model_id,
                verbose=False
            )

            result = await loop.run(
                pod_name=pod_name,
                namespace=test_case.namespace,
                requires_connectivity_check=test_case.requires_connectivity_check
            )

            # Build experiment result with full details
            experiment_result = ExperimentResult(
                experiment_id=experiment_id,
                model=model_name,
                config=config_name,
                case_id=case_id,
                run_id=run_id,
                success=result.success,
                trials_used=result.total_trials,
                final_status=result.final_status,
                total_time=result.total_time,
                total_cost=result.total_cost,
                total_tokens=result.total_tokens,
                trial_details=[
                    {
                        # Basic info
                        "trial": t.trial_num,
                        "success": t.success,
                        "pod_status": t.pod_status,
                        "eval_reason": t.eval_reason,

                        # Timing
                        "actor_time": t.actor_time,
                        "eval_time": t.eval_time,
                        "reflection_time": t.reflection_time,

                        # Cost
                        "actor_cost": t.actor_cost,
                        "reflection_cost": t.reflection_cost,

                        # Tokens (detailed)
                        "actor_input_tokens": t.actor_input_tokens,
                        "actor_output_tokens": t.actor_output_tokens,
                        "actor_cache_read_tokens": t.actor_cache_read_tokens,
                        "actor_cache_creation_tokens": t.actor_cache_creation_tokens,
                        "reflection_tokens": t.reflection_tokens,

                        # Trajectory (truncate output to 1000 chars each)
                        "trajectory": t.trajectory,
                        "commands": [
                            {
                                "command": cmd.get("command", ""),
                                "output": cmd.get("output", "")[:1000] if cmd.get("output") else None
                            }
                            for cmd in t.commands
                        ],

                        # Reflection content
                        "reflection_content": t.reflection_content
                    }
                    for t in result.trials
                ],
                timestamp=datetime.now().isoformat()
            )

            # Save result
            self._save_result(experiment_result)

            return experiment_result

        finally:
            # Cleanup
            await self._cleanup_test_case(test_case)

    async def _setup_test_case(self, test_case: TestCase) -> Optional[str]:
        """Setup the test case and return pod name."""
        print(f"\n[SETUP] {test_case.case_id}: {test_case.name}")

        namespace = test_case.namespace

        # Delete namespace if exists
        subprocess.run(
            f"kubectl delete namespace {namespace} --ignore-not-found",
            shell=True, capture_output=True, timeout=120
        )

        # Create namespace
        subprocess.run(
            f"kubectl create namespace {namespace}",
            shell=True, capture_output=True, timeout=30
        )

        # Find and apply the test case YAML
        case_yaml = self._find_case_yaml(test_case.case_id)
        if not case_yaml:
            print(f"  [ERROR] Could not find YAML for {test_case.case_id}")
            return None

        result = subprocess.run(
            f"kubectl apply -f {case_yaml} -n {namespace}",
            shell=True, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            print(f"  [ERROR] Failed to apply YAML: {result.stderr}")
            return None

        # Wait for pod to be created
        await asyncio.sleep(5)

        # Find the pod name
        pod_name = self._find_pod_name(namespace, test_case.pod_pattern)
        if pod_name:
            print(f"  [OK] Pod: {pod_name}")
        else:
            print(f"  [ERROR] Pod not found matching {test_case.pod_pattern}")

        return pod_name

    def _find_case_yaml(self, case_id: str) -> Optional[str]:
        """Find the YAML file for a test case."""
        base_path = Path(__file__).parent.parent.parent

        # Try different paths
        paths_to_try = [
            base_path / "kubernetes-troubleshooting-cases" / case_id.replace("case", "") / "deployment.yaml",
            base_path / "kubernetes-troubleshooting-cases" / f"{case_id.replace('case', '')}_*" / "deployment.yaml",
        ]

        # Map case IDs to folder names
        case_mapping = {
            "case1": "1_wrong_port",
            "case2": "2_incorrect_selector",
            "case3": "3_liveness_probe",
            "case4": "4_wrong_interface",
            "case5": "5_port_mismatch",
            "case6": "6_misspelling",
            "case7": "7_volume_mount",
            "case8": "8_environment_variable",
            "case9": "9_red_herring_db",
            "case10": "10_cascading_failure",
            "case11": "11_multi_layer_dependency",
            "case12": "12_double_trouble",
            "case13": "13_triple_threat",
            "case14": "14_nightmare_mode",
        }

        if case_id in case_mapping:
            yaml_path = base_path / "kubernetes-troubleshooting-cases" / case_mapping[case_id] / "deployment.yaml"
            if yaml_path.exists():
                return str(yaml_path)

        # Fallback: search
        cases_dir = base_path / "kubernetes-troubleshooting-cases"
        if cases_dir.exists():
            for folder in cases_dir.iterdir():
                if folder.is_dir():
                    yaml_file = folder / "deployment.yaml"
                    if yaml_file.exists() and case_id.replace("case", "") in folder.name:
                        return str(yaml_file)

        return None

    def _find_pod_name(self, namespace: str, pod_pattern: str) -> Optional[str]:
        """Find actual pod name from pattern."""
        result = subprocess.run(
            f'kubectl get pods -n {namespace} -o jsonpath="{{.items[*].metadata.name}}"',
            shell=True, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        pods = result.stdout.strip().split()

        # If pattern has wildcard, find matching pod
        if "*" in pod_pattern:
            prefix = pod_pattern.replace("-*", "").replace("*", "")
            for pod in pods:
                if pod.startswith(prefix):
                    return pod

        # Return first pod
        return pods[0] if pods else None

    async def _cleanup_test_case(self, test_case: TestCase) -> None:
        """Cleanup after test."""
        print(f"\n[CLEANUP] Deleting namespace {test_case.namespace}")
        subprocess.run(
            f"kubectl delete namespace {test_case.namespace} --ignore-not-found",
            shell=True, capture_output=True, timeout=60
        )

    def _save_result(self, result: ExperimentResult) -> None:
        """Save experiment result to JSON."""
        # Create model subdirectory
        model_dir = self.results_dir / result.model
        model_dir.mkdir(parents=True, exist_ok=True)

        # Add timestamp to filename: experiment_id_YYYYMMDD_HHMMSS.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.experiment_id}_{timestamp}.json"
        filepath = model_dir / filename

        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"\n[SAVED] {filepath}")

    def _create_error_result(
        self,
        experiment_id: str,
        model: str,
        config: str,
        case_id: str,
        run_id: int,
        error: str
    ) -> ExperimentResult:
        """Create error result."""
        return ExperimentResult(
            experiment_id=experiment_id,
            model=model,
            config=config,
            case_id=case_id,
            run_id=run_id,
            success=False,
            trials_used=0,
            final_status=f"Error: {error}",
            total_time=0,
            total_cost=0,
            total_tokens=0,
            trial_details=[],
            timestamp=datetime.now().isoformat()
        )


async def run_single(
    model: str,
    config: str,
    case: str,
    run: int = 1
) -> ExperimentResult:
    """Convenience function to run a single experiment."""
    runner = ExperimentRunner()
    return await runner.run_experiment(model, config, case, run)
