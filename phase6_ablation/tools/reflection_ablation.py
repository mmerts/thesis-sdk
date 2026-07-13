#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reflection Ablation Study Runner
=================================

Runs controlled experiments comparing with-reflection vs without-reflection
to empirically validate that reflection improves success rate.

Key experiment: Case 11 (Multi-Layer Dependency)
- Without reflection: Expected to fail (fixes only 1 of 2 bugs)
- With reflection: Expected to succeed (learns from failure, fixes both)

Usage:
    python reflection_ablation.py --case case11 --mode both
    python reflection_ablation.py --case case11 --mode without
    python reflection_ablation.py --case case11 --mode with
"""

import asyncio
import subprocess
import sys
import json
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import time

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agents.reflexion_loop import ReflexionLoop


# Hard cases designed to trigger reflection
ABLATION_CASES = {
    "case11": {
        "name": "Multi-Layer Dependency Chain",
        "namespace": "case11-multilayer",
        "case_dir": "11_multi_layer_dependency",
        "difficulty": "very_hard",
        "expected_bugs": 2,
        "description": "Frontend→Backend→Database chain with selector AND port mismatch"
    },
    "case12": {
        "name": "Cascading ConfigMap Corruption",
        "namespace": "case12-cascading",
        "case_dir": "12_cascading_config",
        "difficulty": "very_hard",
        "expected_bugs": 3,
        "description": "Multiple ConfigMap issues causing different symptoms"
    },
    "case13": {
        "name": "Network Policy Blockage",
        "namespace": "case13-netpol",
        "case_dir": "13_network_policy",
        "difficulty": "very_hard",
        "expected_bugs": 1,
        "description": "NetworkPolicy blocking traffic despite healthy pods"
    }
}


class ReflectionAblationRunner:
    """Runs controlled experiments for reflection ablation study."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        max_trials: int = 5,
        verbose: bool = True
    ):
        self.model = model
        self.max_trials = max_trials
        self.verbose = verbose
        self.base_path = Path(__file__).parent.parent.parent
        self.results_dir = self.base_path / "phase5_optimized" / "results" / "ablation"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def deploy_case(self, case_id: str) -> bool:
        """Deploy test case to Kubernetes."""
        case = ABLATION_CASES.get(case_id)
        if not case:
            print(f"[ERROR] Unknown case: {case_id}")
            return False

        case_path = self.base_path / "kubernetes-troubleshooting-cases" / case["case_dir"]
        deployment_file = case_path / "deployment.yaml"

        if not deployment_file.exists():
            print(f"[ERROR] Deployment file not found: {deployment_file}")
            return False

        print(f"\n[DEPLOY] Setting up {case['name']}...")

        # Delete namespace if exists
        subprocess.run(
            f"kubectl delete namespace {case['namespace']} --ignore-not-found",
            shell=True,
            capture_output=True
        )
        time.sleep(2)

        # Apply deployment
        result = subprocess.run(
            f"kubectl apply -f {deployment_file}",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[ERROR] Deploy failed: {result.stderr}")
            return False

        print(f"[DEPLOY] Waiting for pods to stabilize...")
        time.sleep(15)  # Wait for pods to enter their broken state

        # Show current state
        subprocess.run(
            f"kubectl get pods -n {case['namespace']}",
            shell=True
        )

        return True

    def cleanup_case(self, case_id: str):
        """Clean up test case from Kubernetes."""
        case = ABLATION_CASES.get(case_id)
        if case:
            print(f"\n[CLEANUP] Removing namespace {case['namespace']}...")
            subprocess.run(
                f"kubectl delete namespace {case['namespace']} --ignore-not-found",
                shell=True,
                capture_output=True
            )

    def get_target_pod(self, case_id: str) -> Optional[str]:
        """Get the target pod name for troubleshooting."""
        case = ABLATION_CASES.get(case_id)
        if not case:
            return None

        # Get the problematic pod (usually frontend in multi-layer cases)
        result = subprocess.run(
            f"kubectl get pods -n {case['namespace']} -o jsonpath=\"{{.items[*].metadata.name}}\"",
            shell=True,
            capture_output=True,
            text=True
        )

        # Clean up pod names (remove quotes if present)
        pods = [p.strip("'\"") for p in result.stdout.strip().split()]

        # Priority: frontend > app > first pod
        for pod in pods:
            if "frontend" in pod:
                return pod

        for pod in pods:
            if "app" in pod and "database" not in pod:
                return pod

        return pods[0] if pods else None

    async def run_single_experiment(
        self,
        case_id: str,
        reflection_enabled: bool
    ) -> Dict[str, Any]:
        """Run a single experiment (one case, one configuration)."""
        case = ABLATION_CASES.get(case_id)
        if not case:
            return {"error": f"Unknown case: {case_id}"}

        config_name = "with_reflection" if reflection_enabled else "without_reflection"
        print(f"\n{'='*80}")
        print(f"EXPERIMENT: {case['name']} ({config_name})")
        print(f"{'='*80}")

        # Deploy fresh instance
        if not self.deploy_case(case_id):
            return {"error": "Deployment failed"}

        # Get target pod
        pod_name = self.get_target_pod(case_id)
        if not pod_name:
            return {"error": "Could not find target pod"}

        print(f"\n[TARGET] Pod: {pod_name}")
        print(f"[CONFIG] Reflection: {'ENABLED' if reflection_enabled else 'DISABLED'}")
        print(f"[CONFIG] Max Trials: {self.max_trials}")

        # Create Reflexion loop with specified configuration
        loop = ReflexionLoop(
            model=self.model,
            max_trials=self.max_trials,
            memory_size=3,
            verbose=self.verbose,
            reflection_enabled=reflection_enabled
        )

        # Run the loop
        start_time = time.time()
        result = await loop.run(
            pod_name=pod_name,
            namespace=case["namespace"]
        )
        total_duration = time.time() - start_time

        # Build result
        experiment_result = {
            "case_id": case_id,
            "case_name": case["name"],
            "difficulty": case["difficulty"],
            "reflection_enabled": reflection_enabled,
            "config_name": config_name,
            "success": result["success"],
            "total_trials": result["total_trials"],
            "reflections_generated": len(result["reflections"]),
            "total_duration_seconds": total_duration,
            "timings": result["timings"],
            "api_metadata": result["api_metadata"],
            "final_status": result["final_status"],
            "timestamp": datetime.now().isoformat()
        }

        # Print summary
        print(loop.format_summary(result))

        # Cleanup
        self.cleanup_case(case_id)

        return experiment_result

    async def run_ablation(self, case_id: str) -> Dict[str, Any]:
        """Run full ablation: with AND without reflection."""
        print(f"\n{'#'*80}")
        print(f"ABLATION STUDY: {case_id}")
        print(f"{'#'*80}")

        results = {
            "case_id": case_id,
            "model": self.model,
            "max_trials": self.max_trials,
            "experiments": {}
        }

        # Run WITHOUT reflection first
        print("\n" + "="*80)
        print("PHASE 1: Running WITHOUT reflection (baseline)")
        print("="*80)

        without_result = await self.run_single_experiment(case_id, reflection_enabled=False)
        results["experiments"]["without_reflection"] = without_result

        # Wait between experiments
        print("\n[PAUSE] Waiting 10 seconds before next experiment...")
        await asyncio.sleep(10)

        # Run WITH reflection
        print("\n" + "="*80)
        print("PHASE 2: Running WITH reflection")
        print("="*80)

        with_result = await self.run_single_experiment(case_id, reflection_enabled=True)
        results["experiments"]["with_reflection"] = with_result

        # Generate comparison
        results["comparison"] = self._generate_comparison(without_result, with_result)

        # Save results
        self._save_results(case_id, results)

        # Print comparison
        self._print_comparison(results)

        return results

    def _generate_comparison(
        self,
        without: Dict[str, Any],
        with_refl: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comparison metrics."""
        return {
            "success_improvement": with_refl.get("success", False) and not without.get("success", False),
            "without_success": without.get("success", False),
            "with_success": with_refl.get("success", False),
            "without_trials": without.get("total_trials", 0),
            "with_trials": with_refl.get("total_trials", 0),
            "trials_difference": without.get("total_trials", 0) - with_refl.get("total_trials", 0),
            "reflections_used": with_refl.get("reflections_generated", 0),
            "time_without": without.get("total_duration_seconds", 0),
            "time_with": with_refl.get("total_duration_seconds", 0),
            "reflection_helped": (
                with_refl.get("success", False) and
                not without.get("success", False) and
                with_refl.get("reflections_generated", 0) > 0
            )
        }

    def _save_results(self, case_id: str, results: Dict[str, Any]):
        """Save results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ablation_{case_id}_{timestamp}.json"
        filepath = self.results_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n[SAVED] Results: {filepath}")

    def _print_comparison(self, results: Dict[str, Any]):
        """Print comparison summary."""
        comp = results.get("comparison", {})

        print("\n" + "="*80)
        print("ABLATION STUDY RESULTS")
        print("="*80)

        print(f"\nCase: {results['case_id']}")
        print(f"Model: {results['model']}")

        print("\n" + "-"*40)
        print("Configuration Comparison:")
        print("-"*40)

        print(f"\n{'Metric':<30} {'Without Refl':<15} {'With Refl':<15}")
        print("-"*60)
        print(f"{'Success':<30} {str(comp.get('without_success', 'N/A')):<15} {str(comp.get('with_success', 'N/A')):<15}")
        print(f"{'Trials Used':<30} {comp.get('without_trials', 'N/A'):<15} {comp.get('with_trials', 'N/A'):<15}")
        print(f"{'Reflections Generated':<30} {'0':<15} {comp.get('reflections_used', 0):<15}")
        print(f"{'Duration (seconds)':<30} {comp.get('time_without', 0):.1f}{'s':<14} {comp.get('time_with', 0):.1f}s")

        print("\n" + "-"*40)
        print("CONCLUSION:")
        print("-"*40)

        if comp.get("reflection_helped"):
            print("\n[+] REFLECTION HELPED!")
            print(f"    - Without reflection: FAILED")
            print(f"    - With reflection: SUCCEEDED in {comp.get('with_trials', '?')} trials")
            print(f"    - {comp.get('reflections_used', 0)} reflection(s) generated and used")
        elif comp.get("with_success") and comp.get("without_success"):
            print("\n[=] Both configurations succeeded")
            print("    (Case may be too easy to demonstrate reflection value)")
        elif not comp.get("with_success") and not comp.get("without_success"):
            print("\n[-] Both configurations failed")
            print("    (Case may be too hard or has issues)")
        else:
            print("\n[?] Unexpected result pattern")

        print("\n" + "="*80)


async def main():
    parser = argparse.ArgumentParser(description="Reflection Ablation Study")
    parser.add_argument(
        "--case",
        type=str,
        default="case11",
        choices=list(ABLATION_CASES.keys()),
        help="Case to run"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="both",
        choices=["with", "without", "both"],
        help="Run mode: with/without reflection, or both for full ablation"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-haiku-4-5",
        help="Model to use"
    )
    parser.add_argument(
        "--max-trials",
        type=int,
        default=5,
        help="Maximum trials per run"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )

    args = parser.parse_args()

    runner = ReflectionAblationRunner(
        model=args.model,
        max_trials=args.max_trials,
        verbose=not args.quiet
    )

    if args.mode == "both":
        await runner.run_ablation(args.case)
    elif args.mode == "with":
        result = await runner.run_single_experiment(args.case, reflection_enabled=True)
        print(json.dumps(result, indent=2))
    else:  # without
        result = await runner.run_single_experiment(args.case, reflection_enabled=False)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
