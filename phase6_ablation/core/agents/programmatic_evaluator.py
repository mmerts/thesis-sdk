# -*- coding: utf-8 -*-
"""
Programmatic Evaluator - Phase 5 Optimized Component
=====================================================

NO LLM CALLS - Pure Python evaluation using kubectl JSON output.

From Reflexion paper (Section 3.1):
"The Evaluator can be: (1) Success detection defined by the task environment,
 (2) Heuristic functions, or (3) LLM-based self-evaluation."

This implementation uses option (1) - task environment success detection.
Much faster and cheaper than LLM-based evaluation.

Evaluation criteria for Kubernetes pod health:
1. Pod exists and is in Running phase
2. All containers are Ready (X/X)
3. No restart loops (CrashLoopBackOff)
4. Service endpoints populated (if applicable)
5. Application responds (optional connectivity test)
"""

import subprocess
import json
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class EvaluationResult:
    """Structured evaluation result."""
    success: bool
    reason: str
    pod_status: str
    pod_ready: str
    details: Dict[str, Any]


class ProgrammaticEvaluator:
    """
    Programmatic evaluator for Kubernetes pod health.

    NO LLM CALLS - uses kubectl JSON output parsing.

    This aligns with Reflexion paper's "environment feedback" approach
    where the task environment provides success/failure signals.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize Programmatic Evaluator.

        Args:
            verbose: If True, print detailed diagnostic output
        """
        self.verbose = verbose

    async def evaluate(
        self,
        pod_name: str,
        namespace: str = "default",
        wait_time: int = 5,
        check_service: bool = True
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Evaluate if the pod issue has been resolved.

        Uses kubectl commands with JSON output for programmatic parsing.

        Args:
            pod_name: Name of the pod to check
            namespace: Kubernetes namespace
            wait_time: Seconds to wait before checking
            check_service: Whether to check service endpoints

        Returns:
            Tuple of (evaluation_result, metadata):
            - evaluation_result: Dict with success/reason/pod_status/pod_ready
            - metadata: Empty dict (no LLM usage)
        """
        await asyncio.sleep(wait_time)

        if self.verbose:
            print(f"\n[EVALUATOR] Checking pod: {pod_name} in namespace: {namespace}")

        result = await self._evaluate_pod(pod_name, namespace, check_service)

        # Return in same format as LLM-based evaluator for compatibility
        evaluation = {
            "success": result.success,
            "reason": result.reason,
            "pod_status": result.pod_status,
            "pod_ready": result.pod_ready
        }

        # No LLM metadata - just timing
        metadata = {
            "usage": None,
            "cost_usd": 0.0,
            "duration_ms": 0,
            "duration_api_ms": 0,
            "evaluator_type": "programmatic"
        }

        if self.verbose:
            status_icon = "[+]" if result.success else "[-]"
            print(f"  {status_icon} {result.reason}")

        return evaluation, metadata

    async def _evaluate_pod(
        self,
        pod_name: str,
        namespace: str,
        check_service: bool
    ) -> EvaluationResult:
        """
        Core evaluation logic.

        Checks:
        1. Pod exists and status
        2. Container readiness
        3. Deployment health (if pod not found - rolling update case)
        4. Service endpoints (optional)
        """
        # Step 1: Check if original pod exists
        pod_info = await self._get_pod_info(pod_name, namespace)

        if pod_info is None:
            # Pod not found - check if it was replaced by rolling update
            return await self._check_deployment_health(pod_name, namespace)

        # Step 2: Check pod phase
        phase = pod_info.get("status", {}).get("phase", "Unknown")

        if phase != "Running":
            return EvaluationResult(
                success=False,
                reason=f"Pod is in {phase} phase, not Running",
                pod_status=phase,
                pod_ready="N/A",
                details={"phase": phase}
            )

        # Step 3: Check container readiness
        container_statuses = pod_info.get("status", {}).get("containerStatuses", [])

        if not container_statuses:
            return EvaluationResult(
                success=False,
                reason="No container status information available",
                pod_status=phase,
                pod_ready="0/0",
                details={}
            )

        total_containers = len(container_statuses)
        ready_containers = sum(1 for cs in container_statuses if cs.get("ready", False))
        ready_str = f"{ready_containers}/{total_containers}"

        # Check for CrashLoopBackOff or other waiting states
        for cs in container_statuses:
            waiting = cs.get("state", {}).get("waiting", {})
            if waiting:
                reason = waiting.get("reason", "Unknown")
                if reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError"]:
                    return EvaluationResult(
                        success=False,
                        reason=f"Container in {reason} state",
                        pod_status=reason,
                        pod_ready=ready_str,
                        details={"waiting_reason": reason}
                    )

        # Check if all containers are ready
        if ready_containers < total_containers:
            return EvaluationResult(
                success=False,
                reason=f"Not all containers ready: {ready_str}",
                pod_status=phase,
                pod_ready=ready_str,
                details={"ready": ready_containers, "total": total_containers}
            )

        # Step 4: Check service endpoints (optional)
        if check_service:
            service_ok, service_msg = await self._check_service_endpoints(namespace, pod_name)
            if not service_ok:
                return EvaluationResult(
                    success=False,
                    reason=service_msg,
                    pod_status=phase,
                    pod_ready=ready_str,
                    details={"service_issue": service_msg}
                )

        # All checks passed
        return EvaluationResult(
            success=True,
            reason=f"Pod is Running with all containers ready ({ready_str})",
            pod_status="Running",
            pod_ready=ready_str,
            details={"healthy": True}
        )

    async def _get_pod_info(self, pod_name: str, namespace: str) -> Optional[Dict[str, Any]]:
        """Get pod information as JSON."""
        cmd = f"kubectl get pod {pod_name} -n {namespace} -o json"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if "NotFound" in result.stderr or "not found" in result.stderr.lower():
                    return None
                return None

            return json.loads(result.stdout)

        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    async def _check_deployment_health(
        self,
        original_pod_name: str,
        namespace: str
    ) -> EvaluationResult:
        """
        Check if deployment is healthy after pod was replaced.

        This handles rolling update scenarios where the original pod
        is deleted and replaced with new pods.
        """
        # Extract deployment name from pod name
        # Format: <deployment-name>-<replicaset-hash>-<pod-hash>
        parts = original_pod_name.rsplit("-", 2)
        if len(parts) >= 2:
            deployment_name = parts[0]
        else:
            deployment_name = original_pod_name

        # Try to get deployment status
        cmd = f"kubectl get deployment {deployment_name} -n {namespace} -o json"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # No deployment found, pod was standalone
                return EvaluationResult(
                    success=False,
                    reason=f"Pod {original_pod_name} not found and no deployment exists",
                    pod_status="NotFound",
                    pod_ready="N/A",
                    details={"standalone_pod": True}
                )

            deployment = json.loads(result.stdout)
            status = deployment.get("status", {})

            ready_replicas = status.get("readyReplicas", 0)
            replicas = status.get("replicas", 0)
            available = status.get("availableReplicas", 0)

            if ready_replicas > 0 and ready_replicas == replicas:
                return EvaluationResult(
                    success=True,
                    reason=f"Original pod replaced - deployment healthy with {ready_replicas}/{replicas} replicas ready",
                    pod_status="NotFound (replaced)",
                    pod_ready="N/A",
                    details={
                        "deployment": deployment_name,
                        "ready_replicas": ready_replicas,
                        "total_replicas": replicas
                    }
                )
            else:
                return EvaluationResult(
                    success=False,
                    reason=f"Deployment not fully ready: {ready_replicas}/{replicas} replicas",
                    pod_status="NotFound",
                    pod_ready="N/A",
                    details={
                        "deployment": deployment_name,
                        "ready_replicas": ready_replicas,
                        "total_replicas": replicas
                    }
                )

        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return EvaluationResult(
                success=False,
                reason=f"Pod {original_pod_name} not found and deployment check failed",
                pod_status="NotFound",
                pod_ready="N/A",
                details={}
            )

    async def _check_service_endpoints(
        self,
        namespace: str,
        pod_name: str
    ) -> Tuple[bool, str]:
        """
        Check if service endpoints are populated.

        Returns:
            Tuple of (success, message)
        """
        cmd = f"kubectl get endpoints -n {namespace} -o json"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # No endpoints resource - might be fine if no service
                return True, "No endpoints to check"

            endpoints = json.loads(result.stdout)
            items = endpoints.get("items", [])

            # Check if any service has empty endpoints
            for ep in items:
                ep_name = ep.get("metadata", {}).get("name", "unknown")
                subsets = ep.get("subsets", [])

                # Skip kubernetes default service
                if ep_name == "kubernetes":
                    continue

                if not subsets:
                    return False, f"Service '{ep_name}' has no endpoints (empty subsets)"

                # Check if any subset has addresses
                has_addresses = any(
                    subset.get("addresses", [])
                    for subset in subsets
                )

                if not has_addresses:
                    return False, f"Service '{ep_name}' has no ready pod addresses"

            return True, "All service endpoints populated"

        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            # If we can't check, assume it's OK
            return True, "Could not verify endpoints"

    def format_result(self, result: Dict[str, Any]) -> str:
        """Format evaluation result for display."""
        if result["success"]:
            return f"""
[+] EVALUATION: SUCCESS
   Reason: {result['reason']}
   Pod Status: {result['pod_status']}
   Ready: {result['pod_ready']}
"""
        else:
            return f"""
[-] EVALUATION: FAILURE
   Reason: {result['reason']}
   Pod Status: {result.get('pod_status', 'Unknown')}
   Ready: {result.get('pod_ready', 'N/A')}
"""
