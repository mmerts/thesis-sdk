# Liveness Probe Misconfiguration Test Case

## Problem
Liveness probe is configured with a non-existent endpoint, causing continuous pod restarts.

## Issue Details
- **Application:** Only has `/` and `/ready` endpoints
- **Liveness Probe:** Checks `/health` endpoint ❌ (doesn't exist!)
- **Readiness Probe:** Checks `/ready` endpoint ✅ (exists)

## Expected Behavior
```bash
$ kubectl get pods
NAME                   READY   STATUS             RESTARTS
liveness-probe-app     0/1     CrashLoopBackOff   5
```

## Symptoms
- Pod keeps restarting
- Application actually works fine
- Kubernetes thinks it's unhealthy
- Restart count keeps increasing
- Events show: "Liveness probe failed: HTTP probe failed with statuscode: 404"

## Solution
1. Change liveness probe path from `/health` to `/ready`
2. OR implement `/health` endpoint in server.py
3. OR change to a different probe type (exec, tcpSocket)

## Test Commands
```bash
# Build and deploy
docker build -t liveness-probe-app:latest .
kubectl apply -f deployment.yaml

# Watch the problem
kubectl get pods -w  # Watch restarts
kubectl describe pod liveness-probe-app  # See probe failures
kubectl logs liveness-probe-app  # App logs look fine!
```

## Root Cause
Incorrect health check configuration causing false-positive failures.
This is a common issue when copy-pasting configurations.
