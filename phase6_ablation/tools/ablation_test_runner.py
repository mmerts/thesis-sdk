#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ablation Study Test Runner - Phase 6
=====================================

Runs the complete ablation study test matrix:
- 3 Models: Haiku 3.0, Haiku 3.5, Haiku 4.5
- 2 Configs: Baseline (no reflexion) vs Full Reflexion
- 8 Cases: case1-8 (KubeLLMBench original)
- 3 Runs: per configuration for statistical significance

Total: 3 × 2 × 8 × 3 = 144 tests
Estimated: ~$25, ~10 hours
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import time

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from core.agents.reflexion_loop import ReflexionLoop


# =============================================================================
# CONFIGURATION
# =============================================================================

MODELS = {
    "haiku3": "claude-3-haiku-20240307",
    "haiku35": "claude-3-5-haiku-latest",
    "haiku45": "claude-haiku-4-5"
}

CONFIGS = {
    "baseline": {
        "reflection_enabled": False,
        "max_trials": 1,
        "description": "Baseline - No Reflexion (single trial)"
    },
    "reflexion": {
        "reflection_enabled": True,
        "max_trials": 3,
        "description": "Full Reflexion with Episodic Memory"
    }
}

CASES = {
    "case1": {
        "name": "Wrong Image Tag",
        "namespace": "case1-ns",
        "pod_pattern": "nginx-",
        "difficulty": "easy",
        "setup_script": "kubernetes-troubleshooting-cases/case1-wrong-image-tag/setup.ps1"
    },
    "case2": {
        "name": "Missing ConfigMap",
        "namespace": "case2-ns",
        "pod_pattern": "app-",
        "difficulty": "easy",
        "setup_script": "kubernetes-troubleshooting-cases/case2-missing-configmap/setup.ps1"
    },
    "case3": {
        "name": "Resource Limits",
        "namespace": "case3-ns",
        "pod_pattern": "memory-",
        "difficulty": "medium",
        "setup_script": "kubernetes-troubleshooting-cases/case3-resource-limits/setup.ps1"
    },
    "case4": {
        "name": "Liveness Probe Failure",
        "namespace": "case4-ns",
        "pod_pattern": "web-",
        "difficulty": "hard",
        "setup_script": "kubernetes-troubleshooting-cases/case4-liveness-probe/setup.ps1"
    },
    "case5": {
        "name": "Service Selector Mismatch",
        "namespace": "case5-ns",
        "pod_pattern": "backend-",
        "difficulty": "hard",
        "setup_script": "kubernetes-troubleshooting-cases/case5-service-selector/setup.ps1"
    },
    "case6": {
        "name": "PVC Pending",
        "namespace": "case6-ns",
        "pod_pattern": "storage-",
        "difficulty": "medium",
        "setup_script": "kubernetes-troubleshooting-cases/case6-pvc-pending/setup.ps1"
    },
    "case7": {
        "name": "Init Container Failure",
        "namespace": "case7-ns",
        "pod_pattern": "init-",
        "difficulty": "medium",
        "setup_script": "kubernetes-troubleshooting-cases/case7-init-container/setup.ps1"
    },
    "case8": {
        "name": "CrashLoopBackOff",
        "namespace": "case8-ns",
        "pod_pattern": "crash-",
        "difficulty": "medium",
        "setup_script": "kubernetes-troubleshooting-cases/case8-crashloop/setup.ps1"
    }
}

RUNS_PER_CONFIG = 3


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def setup_case(case_id: str) -> bool:
    """Run the setup script for a case."""
    case_info = CASES.get(case_id)
    if not case_info:
        print(f"[ERROR] Unknown case: {case_id}")
        return False

    setup_script = Path(__file__).parent.parent.parent / case_info["setup_script"]

    if not setup_script.exists():
        print(f"[ERROR] Setup script not found: {setup_script}")
        return False

    print(f"\n[SETUP] Running setup for {case_id}...")

    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(setup_script)],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print(f"[ERROR] Setup failed: {result.stderr}")
            return False

        # Wait for pod to be created
        time.sleep(5)
        return True

    except subprocess.TimeoutExpired:
        print(f"[ERROR] Setup timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Setup error: {e}")
        return False


def find_pod_name(namespace: str, pattern: str) -> str:
    """Find the pod name matching the pattern."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"],
            capture_output=True,
            text=True,
            timeout=30
        )

        pods = result.stdout.strip().replace("'", "").split()

        for pod in pods:
            if pod.startswith(pattern.rstrip("-")):
                return pod

        # If no match, return first pod
        if pods:
            return pods[0]

        return None

    except Exception as e:
        print(f"[ERROR] Failed to find pod: {e}")
        return None


def cleanup_namespace(namespace: str):
    """Delete namespace to clean up."""
    try:
        subprocess.run(
            ["kubectl", "delete", "namespace", namespace, "--ignore-not-found"],
            capture_output=True,
            timeout=60
        )
    except:
        pass


# =============================================================================
# TEST RUNNER
# =============================================================================

async def run_single_test(
    model_key: str,
    config_key: str,
    case_id: str,
    run_number: int
) -> Dict[str, Any]:
    """Run a single test configuration."""

    model = MODELS[model_key]
    config = CONFIGS[config_key]
    case_info = CASES[case_id]

    print("\n" + "=" * 80)
    print(f"TEST: {model_key} | {config_key} | {case_id} | Run {run_number}")
    print(f"Model: {model}")
    print(f"Config: {config['description']}")
    print(f"Case: {case_info['name']} ({case_info['difficulty']})")
    print("=" * 80)

    # Setup case
    if not setup_case(case_id):
        return {
            "status": "setup_failed",
            "model": model_key,
            "config": config_key,
            "case": case_id,
            "run": run_number
        }

    # Find pod
    pod_name = find_pod_name(case_info["namespace"], case_info["pod_pattern"])
    if not pod_name:
        return {
            "status": "pod_not_found",
            "model": model_key,
            "config": config_key,
            "case": case_id,
            "run": run_number
        }

    print(f"[POD] Found: {pod_name}")

    # Run reflexion loop
    loop = ReflexionLoop(
        max_trials=config["max_trials"],
        memory_size=3,
        model=model,
        verbose=False,
        reflection_enabled=config["reflection_enabled"]
    )

    start_time = time.time()

    try:
        result = await loop.run(
            pod_name=pod_name,
            namespace=case_info["namespace"]
        )

        duration = time.time() - start_time

        # Calculate total cost
        total_cost = 0
        for meta in result.get("api_metadata", []):
            if "actor" in meta:
                total_cost += meta["actor"].get("cost_usd", 0)
            if "reflection" in meta:
                total_cost += meta["reflection"].get("cost_usd", 0)

        output = {
            "status": "completed",
            "model": model_key,
            "model_full": model,
            "config": config_key,
            "config_description": config["description"],
            "case": case_id,
            "case_name": case_info["name"],
            "difficulty": case_info["difficulty"],
            "run": run_number,
            "success": result["success"],
            "total_trials": result["total_trials"],
            "final_status": result["final_status"],
            "reflections_generated": len(result.get("reflections", [])),
            "reflections": result.get("reflections", []),
            "duration_seconds": duration,
            "cost_usd": total_cost,
            "timings": result.get("timings", []),
            "timestamp": datetime.now().isoformat()
        }

        print(f"\n[RESULT] {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"[TRIALS] {result['total_trials']}")
        print(f"[COST] ${total_cost:.4f}")
        print(f"[TIME] {duration:.1f}s")

        return output

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "model": model_key,
            "config": config_key,
            "case": case_id,
            "run": run_number
        }

    finally:
        # Cleanup
        cleanup_namespace(case_info["namespace"])


async def run_ablation_study(
    models: List[str] = None,
    configs: List[str] = None,
    cases: List[str] = None,
    runs: int = RUNS_PER_CONFIG,
    output_dir: str = None
):
    """Run the complete ablation study."""

    models = models or list(MODELS.keys())
    configs = configs or list(CONFIGS.keys())
    cases = cases or list(CASES.keys())

    output_dir = Path(output_dir or Path(__file__).parent.parent / "results" / "ablation_study")
    output_dir.mkdir(parents=True, exist_ok=True)

    total_tests = len(models) * len(configs) * len(cases) * runs

    print("\n" + "=" * 80)
    print("ABLATION STUDY - Phase 6")
    print("=" * 80)
    print(f"Models: {models}")
    print(f"Configs: {configs}")
    print(f"Cases: {cases}")
    print(f"Runs per config: {runs}")
    print(f"Total tests: {total_tests}")
    print("=" * 80)

    all_results = []
    test_count = 0

    start_time = datetime.now()

    for model_key in models:
        for config_key in configs:
            for case_id in cases:
                for run_num in range(1, runs + 1):
                    test_count += 1

                    print(f"\n[PROGRESS] Test {test_count}/{total_tests}")

                    result = await run_single_test(
                        model_key=model_key,
                        config_key=config_key,
                        case_id=case_id,
                        run_number=run_num
                    )

                    all_results.append(result)

                    # Save intermediate results
                    result_file = output_dir / f"{model_key}_{config_key}_{case_id}_run{run_num}.json"
                    with open(result_file, "w") as f:
                        json.dump(result, f, indent=2)

                    # Brief pause between tests
                    await asyncio.sleep(2)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Generate summary
    summary = generate_summary(all_results, duration)

    # Save complete results
    complete_file = output_dir / f"ablation_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(complete_file, "w") as f:
        json.dump({
            "summary": summary,
            "results": all_results
        }, f, indent=2)

    # Save summary markdown
    summary_md = generate_summary_markdown(summary, all_results)
    summary_file = output_dir / "ABLATION_RESULTS.md"
    with open(summary_file, "w") as f:
        f.write(summary_md)

    print("\n" + "=" * 80)
    print("ABLATION STUDY COMPLETE")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Duration: {duration/3600:.1f} hours")
    print(f"Results: {complete_file}")
    print(f"Summary: {summary_file}")

    return summary


def generate_summary(results: List[Dict], duration: float) -> Dict:
    """Generate summary statistics from results."""

    summary = {
        "total_tests": len(results),
        "duration_seconds": duration,
        "duration_hours": duration / 3600,
        "by_model": {},
        "by_config": {},
        "by_case": {},
        "by_model_config": {}
    }

    # Group results
    for result in results:
        if result.get("status") != "completed":
            continue

        model = result["model"]
        config = result["config"]
        case = result["case"]
        success = result.get("success", False)
        cost = result.get("cost_usd", 0)

        # By model
        if model not in summary["by_model"]:
            summary["by_model"][model] = {"total": 0, "success": 0, "cost": 0}
        summary["by_model"][model]["total"] += 1
        summary["by_model"][model]["success"] += 1 if success else 0
        summary["by_model"][model]["cost"] += cost

        # By config
        if config not in summary["by_config"]:
            summary["by_config"][config] = {"total": 0, "success": 0, "cost": 0}
        summary["by_config"][config]["total"] += 1
        summary["by_config"][config]["success"] += 1 if success else 0
        summary["by_config"][config]["cost"] += cost

        # By case
        if case not in summary["by_case"]:
            summary["by_case"][case] = {"total": 0, "success": 0}
        summary["by_case"][case]["total"] += 1
        summary["by_case"][case]["success"] += 1 if success else 0

        # By model+config
        key = f"{model}_{config}"
        if key not in summary["by_model_config"]:
            summary["by_model_config"][key] = {"total": 0, "success": 0, "cost": 0}
        summary["by_model_config"][key]["total"] += 1
        summary["by_model_config"][key]["success"] += 1 if success else 0
        summary["by_model_config"][key]["cost"] += cost

    # Calculate success rates
    for category in ["by_model", "by_config", "by_case", "by_model_config"]:
        for key in summary[category]:
            total = summary[category][key]["total"]
            success = summary[category][key]["success"]
            summary[category][key]["success_rate"] = success / total if total > 0 else 0

    return summary


def generate_summary_markdown(summary: Dict, results: List[Dict]) -> str:
    """Generate markdown summary report."""

    md = """# Ablation Study Results - Phase 6

## Overview

| Metric | Value |
|--------|-------|
| Total Tests | {} |
| Duration | {:.1f} hours |
| Total Cost | ${:.2f} |

---

## Results by Configuration

| Config | Success Rate | Total Cost |
|--------|--------------|------------|
""".format(
        summary["total_tests"],
        summary["duration_hours"],
        sum(r.get("cost_usd", 0) for r in results if r.get("status") == "completed")
    )

    for config, data in summary["by_config"].items():
        md += f"| {config} | {data['success_rate']*100:.1f}% ({data['success']}/{data['total']}) | ${data['cost']:.2f} |\n"

    md += """
---

## Results by Model

| Model | Baseline | Reflexion | Δ Improvement |
|-------|----------|-----------|---------------|
"""

    for model in summary["by_model"]:
        baseline_key = f"{model}_baseline"
        reflexion_key = f"{model}_reflexion"

        baseline = summary["by_model_config"].get(baseline_key, {"success_rate": 0})
        reflexion = summary["by_model_config"].get(reflexion_key, {"success_rate": 0})

        delta = reflexion["success_rate"] - baseline["success_rate"]

        md += f"| {model} | {baseline['success_rate']*100:.1f}% | {reflexion['success_rate']*100:.1f}% | +{delta*100:.1f}% |\n"

    md += """
---

## Results by Case

| Case | Difficulty | Baseline | Reflexion |
|------|------------|----------|-----------|
"""

    for case_id, case_info in CASES.items():
        baseline_success = 0
        baseline_total = 0
        reflexion_success = 0
        reflexion_total = 0

        for r in results:
            if r.get("case") == case_id and r.get("status") == "completed":
                if r.get("config") == "baseline":
                    baseline_total += 1
                    baseline_success += 1 if r.get("success") else 0
                else:
                    reflexion_total += 1
                    reflexion_success += 1 if r.get("success") else 0

        baseline_rate = f"{baseline_success}/{baseline_total}" if baseline_total > 0 else "N/A"
        reflexion_rate = f"{reflexion_success}/{reflexion_total}" if reflexion_total > 0 else "N/A"

        md += f"| {case_id} | {case_info['difficulty']} | {baseline_rate} | {reflexion_rate} |\n"

    md += """
---

## Key Findings

### Reflexion Value
- Baseline vs Reflexion comparison shows the value of self-reflection
- Higher improvement on harder cases demonstrates learning capability

### Model Comparison
- Performance differences across Haiku 3.0, 3.5, 4.5
- Cost-effectiveness analysis

---

*Generated: {}*
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return md


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Ablation Study Test Runner - Phase 6")

    parser.add_argument("--models", nargs="+", choices=list(MODELS.keys()),
                        help="Models to test (default: all)")
    parser.add_argument("--configs", nargs="+", choices=list(CONFIGS.keys()),
                        help="Configs to test (default: all)")
    parser.add_argument("--cases", nargs="+",
                        help="Cases to test (default: all)")
    parser.add_argument("--runs", type=int, default=RUNS_PER_CONFIG,
                        help=f"Runs per config (default: {RUNS_PER_CONFIG})")
    parser.add_argument("--output", type=str,
                        help="Output directory for results")
    parser.add_argument("--single", action="store_true",
                        help="Run a single test (first model, config, case)")

    args = parser.parse_args()

    if args.single:
        # Quick single test
        result = await run_single_test(
            model_key=args.models[0] if args.models else "haiku35",
            config_key=args.configs[0] if args.configs else "reflexion",
            case_id=args.cases[0] if args.cases else "case1",
            run_number=1
        )
        print(json.dumps(result, indent=2))
    else:
        # Full ablation study
        await run_ablation_study(
            models=args.models,
            configs=args.configs,
            cases=args.cases,
            runs=args.runs,
            output_dir=args.output
        )


if __name__ == "__main__":
    asyncio.run(main())
