# Incorrect Selector Test Case

## Problem
Service selector doesn't match Pod labels, causing zero endpoints.

## Issue Details
- **Pod Labels:** `app: myapp-v1` ❌
- **Service Selector:** `app: myapp` ❌
- **Result:** Service cannot find any pods

## Expected Behavior
```bash
$ kubectl describe service myapp-service
Endpoints: <none>  # No pods found!
```

## Symptoms
- Pods are running and healthy
- Service exists but has no endpoints
- Traffic cannot reach pods
- `kubectl get endpoints myapp-service` shows no IPs

## Solution
Change pod label from `app: myapp-v1` to `app: myapp` OR change service selector to `app: myapp-v1`

## Test Commands
```bash
# Build and deploy
docker build -t incorrect-selector-app:latest .
kubectl apply -f deployment.yaml

# Verify the problem
kubectl get pods -l app=myapp-v1  # Pods exist
kubectl get endpoints myapp-service  # No endpoints!
kubectl describe service myapp-service  # Shows selector mismatch
```

## Root Cause
Label-selector mismatch is one of the most common Kubernetes misconfigurations.
