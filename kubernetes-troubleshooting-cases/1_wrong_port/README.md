# Wrong Port Test Case

## Problem
Port mismatch between application, Dockerfile, and Kubernetes manifest.

## Issue Details
- **Application (server.py):** Listens on port `8765`
- **Dockerfile:** Exposes port `8000` ❌
- **Kubernetes YAML:** Expects port `8000` ❌

## Expected Behavior
GET requests to the service will timeout because the wrong port is exposed.

## Solution
1. Update Dockerfile: `EXPOSE 8765`
2. Update deployment.yaml: `containerPort: 8765`
3. Update service targetPort: `8765`
4. Rebuild Docker image (no cache)
5. Reapply Kubernetes manifests

## Test Commands
```bash
# Build and deploy
docker build -t wrong-port-app:latest .
kubectl apply -f deployment.yaml

# Test (will fail)
kubectl get pods
kubectl describe pod wrong-port-app
kubectl logs wrong-port-app
curl http://<service-ip>  # Timeout!
```

## Expected Error
- Connection timeout when trying to access the service
- Container appears healthy but unreachable
