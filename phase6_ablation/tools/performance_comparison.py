#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5 vs Phase 4 Performance Comparison
==========================================

Runs test cases with Phase 5 (optimized) and compares with Phase 4 results.

Key differences to measure:
- Evaluator: LLM-based (Phase 4) vs Programmatic (Phase 5)
- Self-Reflection: Agentic (Phase 4) vs Single-call (Phase 5)
- Expected: ~50% cost reduction, ~40% time reduction
"""

import asyncio
import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
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


# Case configurations (same as Phase 4)
CASES = {
    "case1": {
        "name": "Wrong Port",
        "namespace": "case1-test",
        "case_dir": "1_wrong_port",
        "difficulty": "easy",
        "docker_image": "wrong-port-app:latest"
    },
    "case2": {
        "name": "Incorrect Selector",
        "namespace": "case2-test",
        "case_dir": "2_incorrect_selector",
        "difficulty": "easy",
        "docker_image": None,
        "deployment_file": "deployment_fixed_for_test.yaml"
    },
    "case3": {
        "name": "Liveness Probe",
        "namespace": "case3-test",
        "case_dir": "3_liveness_probe",
        "difficulty": "medium",
        "docker_image": "liveness-probe-app:latest"
    },
    "case4": {
        "name": "Wrong Interface (127.0.0.1)",
        "namespace": "case4-test",
        "case_dir": "4_wrong_interface",
        "difficulty": "hard",
        "docker_image": "wrong-interface-app:latest"
    },
    "case5": {
        "name": "Port Mismatch (multi-layer)",
        "namespace": "case5-test",
        "case_dir": "5_port_mismatch",
        "difficulty": "hard",
        "docker_image": "port-mismatch-app:latest"
    },
    "case6": {
        "name": "Image Misspelling",
        "namespace": "case6-test",
        "case_dir": "6_misspelling",
        "difficulty": "easy",
        "docker_image": None
    },
    "case7": {
        "name": "Volume Mount (ConfigMap)",
        "namespace": "case7-test",
        "case_dir": "7_volume_mount",
        "difficulty": "medium",
        "docker_image": "volume-mount-app:latest"
    },
    "case8": {
        "name": "Environment Variables",
        "namespace": "case8-test",
        "case_dir": "8_environment_variable",
        "difficulty": "easy",
        "docker_image": "env-var-app:latest"
    },
    "case9": {
        "name": "Red Herring - Database Connection",
        "namespace": "case9-test",
        "case_dir": "9_red_herring_db",
        "difficulty": "hard",
        "docker_image": "redherring-db-app:latest",
        "target_pod_prefix": "redherring-app"
    },
    "case10": {
        "name": "Cascading Failure - OOMKilled",
        "namespace": "case10-test",
        "case_dir": "10_cascading_failure",
        "difficulty": "hard",
        "docker_image": "cascading-failure-app:latest",
        "target_pod_prefix": "cache-app"
    }
}

BASE_DIR = Path(__file__).parent.parent.parent / "kubernetes-troubleshooting-cases"
RESULTS_DIR = Path(__file__).parent.parent / "results"


class PerformanceRunner:
    """Runs Phase 5 and compares with Phase 4."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        max_trials: int = 3,
        memory_size: int = 3,
        verbose: bool = True
    ):
        self.model = model
        self.max_trials = max_trials
        self.memory_size = memory_size
        self.verbose = verbose

    async def setup_namespace(self, namespace: str) -> bool:
        """Create dedicated namespace."""
        print(f"\n[SETUP] Creating namespace: {namespace}")

        subprocess.run(
            f"kubectl delete namespace {namespace} --ignore-not-found",
            shell=True,
            capture_output=True
        )
        await asyncio.sleep(2)

        result = subprocess.run(
            f"kubectl create namespace {namespace}",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[ERROR] Failed to create namespace: {result.stderr}")
            return False

        print(f"   [+] Namespace created: {namespace}")
        return True

    async def build_and_deploy(self, case_id: str) -> bool:
        """Build Docker image and deploy case."""
        case = CASES[case_id]
        case_dir = BASE_DIR / case["case_dir"]
        namespace = case["namespace"]

        print(f"\n[BUILD] Setting up {case['name']}...")

        # Build Docker image if needed
        if case["docker_image"]:
            image_name = case["docker_image"]
            result = subprocess.run(
                f"docker build -t {image_name} {case_dir}",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"[ERROR] Failed to build Docker image: {result.stderr}")
                return False

            print(f"   [+] Docker image built: {image_name}")

            # Load into minikube
            subprocess.run(
                f"minikube image load {image_name}",
                shell=True,
                capture_output=True
            )

        # Apply deployment
        deployment_filename = case.get("deployment_file", "deployment.yaml")
        deployment_file = case_dir / deployment_filename
        if not deployment_file.exists():
            print(f"[ERROR] Deployment file not found: {deployment_file}")
            return False

        result = subprocess.run(
            f"kubectl apply -f {deployment_file} -n {namespace}",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[ERROR] Failed to apply deployment: {result.stderr}")
            return False

        print(f"   [+] Deployment applied")
        await asyncio.sleep(15)
        return True

    async def find_pod(self, namespace: str, case_id: str = None) -> Optional[str]:
        """Find the problematic pod.
        
        Priority:
        1. If case has target_pod_prefix, find pod matching that prefix
        2. Find pod with restarts (problematic)
        3. Fall back to first pod
        """
        result = subprocess.run(
            f"kubectl get pods -n {namespace} -o json",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        pods_data = json.loads(result.stdout)
        items = pods_data.get("items", [])

        if not items:
            return None

        # Check if case has a specific target pod prefix
        if case_id and case_id in CASES:
            target_prefix = CASES[case_id].get("target_pod_prefix")
            if target_prefix:
                for pod in items:
                    pod_name = pod.get("metadata", {}).get("name", "")
                    if pod_name.startswith(target_prefix):
                        return pod_name

        # Find problematic pod (has restarts)
        for pod in items:
            container_statuses = pod.get("status", {}).get("containerStatuses", [])
            for cs in container_statuses:
                if cs.get("restartCount", 0) > 0:
                    return pod.get("metadata", {}).get("name")

        # Fall back to first pod
        return items[0].get("metadata", {}).get("name")

    async def run_single_case(self, case_id: str, run_id: str) -> Dict[str, Any]:
        """Run a single case with Phase 5 framework."""
        case = CASES[case_id]
        namespace = case["namespace"]

        print(f"\n{'='*80}")
        print(f"PHASE 5 TEST: {case_id} - {case['name']}")
        print(f"{'='*80}")

        # Setup
        if not await self.setup_namespace(namespace):
            return self._create_error_result(run_id, case_id, "Namespace setup failed")

        if not await self.build_and_deploy(case_id):
            return self._create_error_result(run_id, case_id, "Build/deploy failed")

        pod_name = await self.find_pod(namespace, case_id)
        if not pod_name:
            return self._create_error_result(run_id, case_id, "Pod not found")

        print(f"\n[FOUND] Target pod: {pod_name}")

        # Run Phase 5 Reflexion
        started_at = datetime.now().isoformat()

        loop = ReflexionLoop(
            max_trials=self.max_trials,
            memory_size=self.memory_size,
            model=self.model,
            verbose=self.verbose
        )

        start_time = time.time()
        result = await loop.run(pod_name=pod_name, namespace=namespace)
        duration = time.time() - start_time

        completed_at = datetime.now().isoformat()

        # Build structured result
        return self._build_result(
            run_id=run_id,
            case_id=case_id,
            case=case,
            pod_name=pod_name,
            result=result,
            started_at=started_at,
            completed_at=completed_at,
            duration=duration
        )

    def _create_error_result(self, run_id: str, case_id: str, error: str) -> Dict[str, Any]:
        """Create error result."""
        return {
            "run_id": run_id,
            "case_id": case_id,
            "error": error,
            "success": False,
            "framework": "phase5_optimized"
        }

    def _build_result(
        self,
        run_id: str,
        case_id: str,
        case: Dict,
        pod_name: str,
        result: Dict,
        started_at: str,
        completed_at: str,
        duration: float
    ) -> Dict[str, Any]:
        """Build structured result."""

        # Calculate costs
        total_cost = 0
        total_input_tokens = 0
        total_output_tokens = 0

        for meta in result.get("api_metadata", []):
            # Actor cost
            actor_cost = meta.get("actor", {}).get("cost_usd", 0) or 0
            total_cost += actor_cost

            # Evaluator cost (should be 0 for programmatic)
            eval_cost = meta.get("evaluator", {}).get("cost_usd", 0) or 0
            total_cost += eval_cost

            # Reflection cost
            refl_meta = meta.get("reflection", {})
            refl_cost = refl_meta.get("cost_usd", 0) or 0
            total_cost += refl_cost

            # Tokens
            actor_usage = meta.get("actor", {}).get("usage", {})
            if isinstance(actor_usage, dict):
                total_input_tokens += actor_usage.get("input_tokens", 0) or 0
                total_output_tokens += actor_usage.get("output_tokens", 0) or 0

            refl_usage = refl_meta.get("usage", {})
            if isinstance(refl_usage, dict):
                total_input_tokens += refl_usage.get("input_tokens", 0) or 0
                total_output_tokens += refl_usage.get("output_tokens", 0) or 0

        # Build trials
        trials = []
        for i in range(result["total_trials"]):
            trial_data = {
                "trial_num": i + 1,
                "duration_seconds": result["timings"][i]["total"] if i < len(result["timings"]) else 0,
            }

            # Actor data
            if i < len(result["trajectories"]):
                trial_data["actor"] = {
                    "trajectory": result["trajectories"][i],
                    "trajectory_length": len(result["trajectories"][i])
                }

            # Evaluator data
            if i < len(result["evaluations"]):
                eval_data = result["evaluations"][i]
                trial_data["evaluator"] = {
                    "success": eval_data.get("success", False),
                    "reason": eval_data.get("reason", ""),
                    "pod_status": eval_data.get("pod_status", "Unknown"),
                    "pod_ready": eval_data.get("pod_ready", eval_data.get("ready", "N/A"))
                }

            # Reflection data (only for failed trials)
            if i < len(result["reflections"]) and result["reflections"][i]:
                trial_data["reflection"] = result["reflections"][i]

            # API metadata (tokens, cost) per trial
            if i < len(result["api_metadata"]):
                meta = result["api_metadata"][i]

                actor_usage = meta.get("actor", {}).get("usage", {})
                eval_usage = meta.get("evaluator", {}).get("usage", {})
                refl_usage = meta.get("reflection", {}).get("usage", {})

                # Handle different usage formats
                if isinstance(actor_usage, dict):
                    actor_input = actor_usage.get("input_tokens", 0) or 0
                    actor_output = actor_usage.get("output_tokens", 0) or 0
                else:
                    actor_input = 0
                    actor_output = 0

                if isinstance(eval_usage, dict):
                    eval_input = eval_usage.get("input_tokens", 0) or 0
                    eval_output = eval_usage.get("output_tokens", 0) or 0
                else:
                    eval_input = 0
                    eval_output = 0

                if isinstance(refl_usage, dict):
                    refl_input = refl_usage.get("input_tokens", 0) or 0
                    refl_output = refl_usage.get("output_tokens", 0) or 0
                else:
                    refl_input = 0
                    refl_output = 0

                input_tokens = actor_input + eval_input + refl_input
                output_tokens = actor_output + eval_output + refl_output

                cost = (
                    (meta.get("actor", {}).get("cost_usd") or 0) +
                    (meta.get("evaluator", {}).get("cost_usd") or 0) +
                    (meta.get("reflection", {}).get("cost_usd") or 0)
                )

                trial_data["tokens"] = {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens
                }
                trial_data["cost_usd"] = cost

            trials.append(trial_data)

        return {
            "run_id": run_id,
            "experiment_id": "phase5_optimized",
            "config_id": "default",
            "test_case": {
                "id": case_id,
                "name": case["name"],
                "namespace": case["namespace"],
                "difficulty": case["difficulty"]
            },
            "parameters": {
                "model": self.model,
                "max_trials": self.max_trials,
                "memory_size": self.memory_size,
                "reflection_enabled": True,
                "evaluator_type": "programmatic",
                "reflection_type": "single_call"
            },
            "execution": {
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_seconds": duration,
                "pod_name": pod_name
            },
            "results": {
                "success": result["success"],
                "final_trial": result["total_trials"],
                "trials": trials
            },
            "totals": {
                "tokens": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_input_tokens + total_output_tokens
                },
                "cost_usd": total_cost,
                "reflections_generated": len([r for r in result["reflections"] if r])
            },
            "metadata": {
                "framework_version": "phase5_optimized",
                "git_commit": self._get_git_commit(),
                "hostname": os.environ.get("COMPUTERNAME", "unknown")
            }
        }

    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                "git rev-parse --short HEAD",
                shell=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"

    def save_result(self, result: Dict, filename: str):
        """Save result to JSON file."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output_file = RESULTS_DIR / filename

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n[SAVED] {output_file}")


async def run_performance_test(case_ids: List[str], model: str = "claude-haiku-4-5", verbose: bool = True):
    """Run performance test on specified cases."""
    runner = PerformanceRunner(model=model, verbose=verbose)
    results = {}

    for i, case_id in enumerate(case_ids):
        run_id = f"p5_run_{i+1:03d}"
        result = await runner.run_single_case(case_id, run_id)
        results[case_id] = result

        # Save individual result
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        runner.save_result(result, f"phase5_{case_id}_{timestamp}.json")

    # Save combined results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    runner.save_result(results, f"phase5_combined_{timestamp}.json")

    # Print summary
    print_summary(results)

    return results


def print_summary(results: Dict):
    """Print performance summary."""
    print("\n" + "=" * 80)
    print("PHASE 5 PERFORMANCE SUMMARY")
    print("=" * 80)

    success_count = 0
    total_time = 0
    total_cost = 0

    for case_id, result in results.items():
        if result.get("results", {}).get("success", False):
            success_count += 1

        total_time += result.get("execution", {}).get("duration_seconds", 0)
        total_cost += result.get("totals", {}).get("cost_usd", 0)

    print(f"\nSuccess Rate: {success_count}/{len(results)}")
    print(f"Total Time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Total Cost: ${total_cost:.4f}")
    print(f"Average Time: {total_time/len(results):.1f}s per case")
    print(f"Average Cost: ${total_cost/len(results):.4f} per case")

    print("\nPer-Case Results:")
    print("-" * 80)

    for case_id, result in results.items():
        success = result.get("results", {}).get("success", False)
        trials = result.get("results", {}).get("final_trial", 0)
        duration = result.get("execution", {}).get("duration_seconds", 0)
        cost = result.get("totals", {}).get("cost_usd", 0)

        status = "[+]" if success else "[-]"
        print(f"  {status} {case_id}: Trial {trials}, {duration:.1f}s, ${cost:.4f}")

    print("=" * 80)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 5 Performance Test")
    parser.add_argument("--case", type=str, help="Run specific case")
    parser.add_argument("--cases", type=str, help="Run multiple cases (comma-separated)")
    parser.add_argument("--all", action="store_true", help="Run all cases")
    parser.add_argument("--model", type=str, default="claude-haiku-4-5",
                       help="Model to use (claude-haiku-4-5, claude-3-5-haiku, claude-3-haiku)")
    parser.add_argument("--verbose", action="store_true", default=True)

    args = parser.parse_args()

    if args.case:
        await run_performance_test([args.case], args.model, args.verbose)
    elif args.cases:
        case_list = [c.strip() for c in args.cases.split(",")]
        await run_performance_test(case_list, args.model, args.verbose)
    elif args.all:
        await run_performance_test(list(CASES.keys()), args.model, args.verbose)
    else:
        print("Usage:")
        print("  python performance_comparison.py --case case1")
        print("  python performance_comparison.py --cases case1,case2,case3")
        print("  python performance_comparison.py --all")


if __name__ == "__main__":
    asyncio.run(main())
