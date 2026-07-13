#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5 Test Runner
====================

Runs Phase 5 optimized Reflexion framework on KubeLLMBench test cases.
Compares performance with Phase 4 (LLM-based evaluator).
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agents.reflexion_loop import ReflexionLoop


# Test case definitions (from KubeLLMBench)
TEST_CASES = {
    "case1": {
        "name": "Missing Image",
        "namespace": "case1-test",
        "pod_pattern": "myapp-deployment-*",
        "difficulty": "easy"
    },
    "case2": {
        "name": "Incorrect Selector",
        "namespace": "case2-test",
        "pod_pattern": "myapp-deployment-*",
        "difficulty": "easy"
    },
    "case3": {
        "name": "Resource Limit (OOM)",
        "namespace": "case3-test",
        "pod_pattern": "memory-hungry-*",
        "difficulty": "medium"
    },
    "case4": {
        "name": "Wrong Interface (127.0.0.1)",
        "namespace": "case4-test",
        "pod_pattern": "wrong-interface-app",
        "difficulty": "hard"
    },
    "case5": {
        "name": "Port Mismatch (multi-layer)",
        "namespace": "case5-test",
        "pod_pattern": "port-mismatch-deployment-*",
        "difficulty": "hard"
    },
    "case6": {
        "name": "Missing Environment Variable",
        "namespace": "case6-test",
        "pod_pattern": "env-app",
        "difficulty": "medium"
    },
    "case7": {
        "name": "Volume Mount (ConfigMap)",
        "namespace": "case7-test",
        "pod_pattern": "volume-mount-app",
        "difficulty": "medium"
    },
    "case8": {
        "name": "Liveness Probe Misconfiguration",
        "namespace": "case8-test",
        "pod_pattern": "probe-app",
        "difficulty": "medium"
    },
    "case9": {
        "name": "Red Herring Database",
        "namespace": "case9-test",
        "pod_pattern": "redherring-app-*",
        "difficulty": "hard"
    },
    "case10": {
        "name": "Cascading Failure",
        "namespace": "case10-cascade",
        "pod_pattern": "app-*",
        "difficulty": "hard"
    },
    "case11": {
        "name": "Multi-Layer Dependency",
        "namespace": "case11-multilayer",
        "pod_pattern": "frontend-*",
        "difficulty": "very_hard"
    },
    "easy": {
        "name": "Wrong Image Name (ngnix typo)",
        "namespace": "case-easy-test",
        "pod_pattern": "webapp-*",
        "difficulty": "easy"
    }
}


def find_pod_name(namespace: str, pod_pattern: str) -> str:
    """Find actual pod name from pattern."""
    import subprocess

    # If pattern has wildcard, search for matching pod
    if "*" in pod_pattern:
        prefix = pod_pattern.replace("-*", "").replace("*", "")
        cmd = f'kubectl get pods -n {namespace} -o jsonpath="{{.items[*].metadata.name}}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pods = result.stdout.strip().replace("'", "").split()
            for pod in pods:
                if pod.startswith(prefix):
                    return pod

    # Fallback: get first pod
    cmd = f'kubectl get pods -n {namespace} -o jsonpath="{{.items[0].metadata.name}}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    # Fallback to pattern
    if "*" in pod_pattern:
        return pod_pattern.replace("-*", "")
    return pod_pattern


def setup_test_case(case_id: str) -> bool:
    """Setup test case using minikube scripts."""
    import subprocess

    case_dir = Path(__file__).parent.parent.parent / "KubeLLMBench" / "cases" / case_id.replace("case", "")

    if not case_dir.exists():
        # Try alternate naming
        case_mapping = {
            "case1": "1_missing_image",
            "case2": "2_incorrect_selector",
            "case3": "3_resource_limit",
            "case4": "4_wrong_interface",
            "case5": "5_port_mismatch",
            "case6": "6_missing_env",
            "case7": "7_volume_mount",
            "case8": "8_liveness_probe"
        }
        case_dir = Path(__file__).parent.parent.parent / "KubeLLMBench" / "cases" / case_mapping.get(case_id, case_id)

    if not case_dir.exists():
        print(f"[WARN] Case directory not found: {case_dir}")
        return False

    setup_script = case_dir / "minikube" / "setup.sh"

    if setup_script.exists():
        print(f"[SETUP] Running setup script for {case_id}...")
        result = subprocess.run(
            f"bash {setup_script}",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(case_dir / "minikube")
        )

        if result.returncode != 0:
            print(f"[WARN] Setup script failed: {result.stderr[:200]}")
            return False

        # Wait for pod to be created
        time.sleep(5)
        return True

    return False


async def run_single_test(
    case_id: str,
    max_trials: int = 3,
    memory_size: int = 3,
    model: str = "claude-haiku-4-5",
    verbose: bool = False
) -> dict:
    """Run a single test case."""
    case_info = TEST_CASES.get(case_id)

    if not case_info:
        return {"error": f"Unknown case: {case_id}"}

    namespace = case_info["namespace"]
    pod_pattern = case_info["pod_pattern"]

    # Find actual pod name
    pod_name = find_pod_name(namespace, pod_pattern)

    print(f"\n{'=' * 80}")
    print(f"TEST CASE: {case_id} - {case_info['name']}")
    print(f"Pod: {pod_name} | Namespace: {namespace}")
    print(f"Difficulty: {case_info['difficulty']}")
    print("=" * 80)

    # Initialize Reflexion loop
    loop = ReflexionLoop(
        max_trials=max_trials,
        memory_size=memory_size,
        model=model,
        verbose=verbose
    )

    # Run
    start_time = time.time()
    result = await loop.run(pod_name, namespace)
    total_duration = time.time() - start_time

    # Print summary
    print(loop.format_summary(result))

    # Build output
    output = {
        "case_id": case_id,
        "case_name": case_info["name"],
        "namespace": namespace,
        "pod_name": pod_name,
        "difficulty": case_info["difficulty"],
        "parameters": {
            "model": model,
            "max_trials": max_trials,
            "memory_size": memory_size
        },
        "results": {
            "success": result["success"],
            "total_trials": result["total_trials"],
            "final_status": result["final_status"],
            "total_duration_seconds": total_duration
        },
        "timings": result.get("timings", []),
        "api_metadata": result.get("api_metadata", []),
        "reflections": result.get("reflections", []),  # Store reflection content for quality analysis
        "timestamp": datetime.now().isoformat()
    }

    return output


async def run_all_tests(
    max_trials: int = 3,
    memory_size: int = 3,
    model: str = "claude-haiku-4-5",
    verbose: bool = False,
    setup: bool = False
) -> dict:
    """Run all 8 test cases."""
    results = {}

    for case_id in TEST_CASES.keys():
        if setup:
            setup_test_case(case_id)

        result = await run_single_test(
            case_id=case_id,
            max_trials=max_trials,
            memory_size=memory_size,
            model=model,
            verbose=verbose
        )

        results[case_id] = result

        # Save intermediate results
        save_results(results, "phase5_results_intermediate.json")

    return results


def save_results(results: dict, filename: str):
    """Save results to JSON file."""
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / filename

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[SAVED] Results saved to: {output_file}")


def print_comparison_summary(results: dict):
    """Print summary comparing with Phase 4 expectations."""
    print("\n" + "=" * 80)
    print("PHASE 5 RESULTS SUMMARY")
    print("=" * 80)

    success_count = sum(1 for r in results.values() if r.get("results", {}).get("success", False))
    total_count = len(results)

    print(f"\nSuccess Rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)")

    # Calculate total time and cost
    total_time = 0
    total_cost = 0

    for case_id, result in results.items():
        case_time = result.get("results", {}).get("total_duration_seconds", 0)
        total_time += case_time

        # Sum costs from API metadata
        for trial_meta in result.get("api_metadata", []):
            actor_cost = trial_meta.get("actor", {}).get("cost_usd", 0) or 0
            eval_cost = trial_meta.get("evaluator", {}).get("cost_usd", 0) or 0
            refl_cost = trial_meta.get("reflection", {}).get("cost_usd", 0) or 0
            total_cost += actor_cost + eval_cost + refl_cost

    print(f"Total Time: {total_time:.2f}s ({total_time/60:.1f} min)")
    print(f"Total Cost: ${total_cost:.4f}")
    print(f"Average Time per Case: {total_time/total_count:.2f}s")
    print(f"Average Cost per Case: ${total_cost/total_count:.4f}")

    print("\nPer-Case Results:")
    print("-" * 80)

    for case_id, result in results.items():
        success = result.get("results", {}).get("success", False)
        trials = result.get("results", {}).get("total_trials", 0)
        duration = result.get("results", {}).get("total_duration_seconds", 0)
        status_icon = "[+]" if success else "[-]"

        print(f"  {status_icon} {case_id}: Trial {trials}, {duration:.1f}s - {result.get('case_name', '')}")

    print("=" * 80)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 5 Test Runner")
    parser.add_argument("--case", type=str, help="Run specific case (e.g., case1)")
    parser.add_argument("--all", action="store_true", help="Run all 8 cases")
    parser.add_argument("--max-trials", type=int, default=3)
    parser.add_argument("--memory-size", type=int, default=3)
    parser.add_argument("--model", type=str, default="claude-haiku-4-5")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--setup", action="store_true", help="Run setup scripts before tests")

    args = parser.parse_args()

    # Model name mapping
    model_mapping = {
        "haiku3": "claude-3-haiku-20240307",
        "haiku35": "claude-3-5-haiku-latest",
        "haiku45": "claude-haiku-4-5",
        "sonnet": "claude-sonnet-4-5-20250514",
        "opus": "claude-opus-4-5-20250514"
    }
    model = model_mapping.get(args.model, args.model)

    if args.case:
        result = await run_single_test(
            case_id=args.case,
            max_trials=args.max_trials,
            memory_size=args.memory_size,
            model=model,
            verbose=args.verbose
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_results(result, f"phase5_{args.case}_{timestamp}.json")

    elif args.all:
        results = await run_all_tests(
            max_trials=args.max_trials,
            memory_size=args.memory_size,
            model=model,
            verbose=args.verbose,
            setup=args.setup
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_results(results, f"phase5_all_cases_{timestamp}.json")
        print_comparison_summary(results)

    else:
        print("Usage: python run_test.py --case case1  OR  --all")
        print("\nAvailable cases:")
        for case_id, info in TEST_CASES.items():
            print(f"  {case_id}: {info['name']} ({info['difficulty']})")


if __name__ == "__main__":
    asyncio.run(main())
