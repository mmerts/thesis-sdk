# -*- coding: utf-8 -*-
"""
Programmatic Evaluator - Phase 6
=================================

NO LLM CALLS - Pure Python evaluation using kubectl JSON output.

Evaluation criteria:
1. Pod exists and is in Running phase
2. All containers are Ready (X/X)
3. No restart loops (CrashLoopBackOff)
4. Service endpoints populated (if applicable)
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
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    async def evaluate(
        self,
        pod_name: str,
        namespace: str = "default",
        wait_time: int = 5,
        check_service: bool = True,
        requires_connectivity_check: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Evaluate if the pod issue has been resolved.

        Returns:
            Tuple of (evaluation_result, metadata)
        """
        await asyncio.sleep(wait_time)

        if self.verbose:
            print(f"\n[EVALUATOR] Checking pod: {pod_name} in namespace: {namespace}")

        result = await self._evaluate_pod(pod_name, namespace, check_service, requires_connectivity_check)

        evaluation = {
            "success": result.success,
            "reason": result.reason,
            "pod_status": result.pod_status,
            "pod_ready": result.pod_ready
        }

        metadata = {
            "usage": None,
            "cost_usd": 0.0,
            "duration_ms": 0,
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
        check_service: bool,
        requires_connectivity_check: bool = False
    ) -> EvaluationResult:
        """Core evaluation logic."""

        # Step 1: Check if original pod exists
        pod_info = await self._get_pod_info(pod_name, namespace)

        if pod_info is None:
            return await self._check_deployment_health(pod_name, namespace, requires_connectivity_check)

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

        # Check for error states
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

        if ready_containers < total_containers:
            return EvaluationResult(
                success=False,
                reason=f"Not all containers ready: {ready_str}",
                pod_status=phase,
                pod_ready=ready_str,
                details={"ready": ready_containers, "total": total_containers}
            )

        # Step 4: Check service endpoints (basic check)
        if check_service:
            service_ok, service_msg = await self._check_service_endpoints_basic(namespace)
            if not service_ok:
                return EvaluationResult(
                    success=False,
                    reason=service_msg,
                    pod_status=phase,
                    pod_ready=ready_str,
                    details={"service_issue": service_msg}
                )

        # Step 5: Check actual service connectivity (only for specific cases)
        if requires_connectivity_check:
            conn_ok, conn_msg = await self._check_service_connectivity(namespace)
            if not conn_ok:
                return EvaluationResult(
                    success=False,
                    reason=conn_msg,
                    pod_status=phase,
                    pod_ready=ready_str,
                    details={"connectivity_issue": conn_msg}
                )

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
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return None
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    async def _check_deployment_health(
        self,
        original_pod_name: str,
        namespace: str,
        requires_connectivity_check: bool = False
    ) -> EvaluationResult:
        """Check deployment health after pod replacement."""

        parts = original_pod_name.rsplit("-", 2)
        deployment_name = parts[0] if len(parts) >= 2 else original_pod_name

        cmd = f"kubectl get deployment {deployment_name} -n {namespace} -o json"

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
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

            if ready_replicas > 0 and ready_replicas == replicas:
                # Check connectivity if required
                if requires_connectivity_check:
                    conn_ok, conn_msg = await self._check_service_connectivity(namespace)
                    if not conn_ok:
                        return EvaluationResult(
                            success=False,
                            reason=conn_msg,
                            pod_status="Replaced",
                            pod_ready=f"{ready_replicas}/{replicas}",
                            details={"connectivity_issue": conn_msg}
                        )

                return EvaluationResult(
                    success=True,
                    reason=f"Deployment healthy with {ready_replicas}/{replicas} replicas",
                    pod_status="Replaced",
                    pod_ready=f"{ready_replicas}/{replicas}",
                    details={"deployment": deployment_name}
                )
            else:
                return EvaluationResult(
                    success=False,
                    reason=f"Deployment not ready: {ready_replicas}/{replicas} replicas",
                    pod_status="NotFound",
                    pod_ready="N/A",
                    details={"deployment": deployment_name}
                )

        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return EvaluationResult(
                success=False,
                reason=f"Pod {original_pod_name} not found",
                pod_status="NotFound",
                pod_ready="N/A",
                details={}
            )

    async def _check_service_endpoints_basic(self, namespace: str) -> Tuple[bool, str]:
        """Check if service endpoints are populated (basic check, no connectivity test)."""
        cmd = f"kubectl get endpoints -n {namespace} -o json"

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return True, "No endpoints to check"

            endpoints = json.loads(result.stdout)

            for ep in endpoints.get("items", []):
                ep_name = ep.get("metadata", {}).get("name", "unknown")
                if ep_name == "kubernetes":
                    continue

                subsets = ep.get("subsets", [])
                if not subsets:
                    return False, f"Service '{ep_name}' has no endpoints"

                has_addresses = any(s.get("addresses", []) for s in subsets)
                if not has_addresses:
                    return False, f"Service '{ep_name}' has no ready addresses"

            return True, "All endpoints OK"

        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return True, "Could not verify endpoints"

    async def _check_service_connectivity(self, namespace: str) -> Tuple[bool, str]:
        """Check actual service connectivity by making HTTP request."""
        # Get services in namespace
        cmd = f"kubectl get services -n {namespace} -o json"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return True, "No services to check"

            services = json.loads(result.stdout)

            for svc in services.get("items", []):
                svc_name = svc.get("metadata", {}).get("name", "")
                if svc_name == "kubernetes":
                    continue

                ports = svc.get("spec", {}).get("ports", [])
                if not ports:
                    continue

                port = ports[0].get("port", 80)

                # Test connectivity using a temporary pod
                test_cmd = f'kubectl run test-conn --image=busybox --rm -i --restart=Never -n {namespace} --timeout=15s -- wget -q -O- --timeout=5 http://{svc_name}:{port}/ 2>&1'

                test_result = subprocess.run(
                    test_cmd, shell=True, capture_output=True, text=True, timeout=25
                )

                # Cleanup
                subprocess.run(
                    f"kubectl delete pod test-conn -n {namespace} --ignore-not-found",
                    shell=True, capture_output=True, timeout=10
                )

                output = test_result.stdout + test_result.stderr
                if "Connection refused" in output or "timed out" in output.lower():
                    return False, f"Service '{svc_name}' not responding on port {port}"

            return True, "Service connectivity OK"

        except subprocess.TimeoutExpired:
            return False, "Service connectivity test timed out"
        except json.JSONDecodeError:
            return True, "Could not parse services"

    async def _test_service_connectivity(self, service_name: str, namespace: str) -> Tuple[bool, str]:
        """Test actual service connectivity using kubectl exec or a test pod."""
        # Get service port
        svc_cmd = f"kubectl get service {service_name} -n {namespace} -o json"
        try:
            result = subprocess.run(
                svc_cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return True, "Could not get service info"

            svc = json.loads(result.stdout)
            ports = svc.get("spec", {}).get("ports", [])
            if not ports:
                return True, "No ports defined"

            port = ports[0].get("port", 80)

            # Use kubectl run to test connectivity
            test_cmd = f'kubectl run test-conn-{namespace} --image=busybox --rm -i --restart=Never -n {namespace} --timeout=10s -- wget -q -O- --timeout=5 http://{service_name}:{port}/ 2>&1'

            result = subprocess.run(
                test_cmd, shell=True, capture_output=True, text=True, timeout=20
            )

            # Clean up test pod if it exists
            subprocess.run(
                f"kubectl delete pod test-conn-{namespace} -n {namespace} --ignore-not-found",
                shell=True, capture_output=True, timeout=10
            )

            if result.returncode == 0:
                return True, f"Service {service_name} is reachable"
            else:
                # Check if it's a connection refused or timeout
                output = result.stdout + result.stderr
                if "Connection refused" in output or "timed out" in output.lower() or "connection timed out" in output.lower():
                    return False, f"Service '{service_name}' not responding on port {port}"
                # Other errors might be OK (e.g., 404 means service is reachable)
                return True, f"Service {service_name} responded"

        except subprocess.TimeoutExpired:
            return False, f"Service connectivity test timed out"
        except json.JSONDecodeError:
            return True, "Could not parse service info"

    def format_result(self, result: Dict[str, Any]) -> str:
        """Format evaluation result for display."""
        icon = "[+]" if result["success"] else "[-]"
        status = "SUCCESS" if result["success"] else "FAILURE"
        return f"""
{icon} EVALUATION: {status}
   Reason: {result['reason']}
   Pod Status: {result['pod_status']}
   Ready: {result['pod_ready']}
"""
