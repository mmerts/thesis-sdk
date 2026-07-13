# Case 12: Double Trouble (2 Bugs)

## Difficulty: HARD

## Scenario
Frontend pod is in CrashLoopBackOff because it cannot connect to the backend service.

## Bugs (Must fix BOTH)

### Bug 1: Service Selector Mismatch
- `backend-svc` selector: `app: backend-wrong`
- `backend` pod label: `app: backend`
- **Result:** Service endpoints are EMPTY

### Bug 2: Port Mismatch
- Backend container listens on: **port 3000**
- Service targetPort: **8080**
- **Result:** Even if selector fixed, connection fails

## Expected Agent Behavior

### Without Reflection
```
Trial 1: Fix selector -> Still FAIL (port wrong)
Trial 2: Maybe try selector again, or give up
```

### With Reflection
```
Trial 1: Fix selector -> Still FAIL
Reflection: "I fixed the selector and endpoints appeared,
             but connection still fails. Let me check the ports..."
Trial 2: Fix port -> SUCCESS
```

## Solution
```bash
# Fix 1: Correct the selector
kubectl patch svc backend-svc -n case12-double -p '{"spec":{"selector":{"app":"backend"}}}'

# Fix 2: Correct the port
kubectl patch svc backend-svc -n case12-double -p '{"spec":{"ports":[{"port":8080,"targetPort":3000}]}}'

# Or combined:
kubectl patch svc backend-svc -n case12-double -p '{"spec":{"selector":{"app":"backend"},"ports":[{"port":8080,"targetPort":3000}]}}'
```

## Verification
```bash
# Check endpoints (should have backend pod IP)
kubectl get endpoints backend-svc -n case12-double

# Check frontend logs
kubectl logs -n case12-double -l app=frontend

# Test connectivity
kubectl exec -n case12-double deploy/frontend -- curl -s http://backend-svc:8080
```
