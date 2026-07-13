# Port Mismatch Test Case

## Problem
Inconsistent port configuration across multiple layers of the stack.

## Issue Details - Port Conflicts Everywhere!
- **Application (server.py):** Runs on port `5000` ✅
- **Dockerfile:** Exposes port `8080` ❌
- **Pod Spec:** Defines containerPort `8080` ❌
- **Service:** Targets port `3000` ❌

**3 different wrong ports across 4 different files!**

## Expected Behavior
Complete failure - traffic cannot route to the application.

## Architecture Layers
```
External Request (port 80)
    ↓
Service (targetPort: 3000) ❌ WRONG
    ↓
Pod (containerPort: 8080) ❌ WRONG
    ↓
Container (exposed: 8080) ❌ WRONG
    ↓
Application (listening: 5000) ✅ CORRECT
```

## Symptoms
- Service shows endpoints (pods are selected correctly)
- Pods are running without errors
- Application logs show it's listening on 5000
- All health checks fail
- Zero successful requests
- Connection refused or timeout errors

## Solution
Align all ports to `5000`:
1. Dockerfile: `EXPOSE 5000`
2. deployment.yaml Pod spec: `containerPort: 5000`
3. deployment.yaml Service: `targetPort: 5000`

## Test Commands
```bash
# Build and deploy
docker build -t port-mismatch-app:latest .
kubectl apply -f deployment.yaml

# Verify the problem
kubectl get pods
kubectl logs <pod-name>  # Shows "Running on port 5000"
kubectl get svc port-mismatch-service
kubectl describe svc port-mismatch-service  # Shows endpoints
curl http://<service-ip>  # Timeout!

# Debug
kubectl exec <pod-name> -- netstat -tlnp  # Shows port 5000 listening
kubectl exec <pod-name> -- curl localhost:5000  # Works!
kubectl exec <pod-name> -- curl localhost:8080  # Connection refused!
```

## Why This Happens
- Copy-paste from different examples
- Refactoring application port without updating configs
- Multiple team members working on different files
- No single source of truth for port configuration

## Learning Point
Port configuration must be consistent across:
1. Application code
2. Dockerfile EXPOSE
3. Kubernetes containerPort
4. Service targetPort

This is one of the most frustrating debugging scenarios!
