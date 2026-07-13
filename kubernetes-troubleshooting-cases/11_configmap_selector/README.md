# Case 12: ConfigMap + Selector Mismatch (2 Bugs)

## Difficulty: Hard

## Scenario
A web application is failing to start due to configuration issues.

## Bugs

### Bug 1: ConfigMap Missing Key (Obvious)
- **Location:** ConfigMap `app-config`
- **Issue:** App expects `APP_CONFIG` key but ConfigMap only has `DB_HOST`
- **Symptom:** CrashLoopBackOff, logs show "FATAL ERROR: APP_CONFIG not found!"
- **Fix:** Add `APP_CONFIG: "production"` to ConfigMap

### Bug 2: Service Selector Mismatch (Hidden)
- **Location:** Service `webapp-svc`
- **Issue:** Service selector is `app: webapp` but Deployment label is `app: webapp-v2`
- **Symptom:** After ConfigMap fix, pod runs but service has no endpoints
- **Hint:** `kubectl get endpoints webapp-svc` returns empty
- **Fix:** Change Service selector to `app: webapp-v2` OR change Deployment label to `app: webapp`

## Expected Agent Behavior

### Without Reflexion
- Trial 1: Fix ConfigMap → Pod runs but service fails
- Trial 2: Agent may not check selector/endpoints

### With Reflexion
- Trial 1: Fix ConfigMap → Pod runs but service fails
- Reflection: "Fixed ConfigMap, pod now running, but service not responding. kubectl get endpoints shows no endpoints. Need to check selector labels."
- Trial 2: Fix selector → Success

## Success Criteria
1. Webapp pod is Running and Ready (1/1)
2. Service has endpoints: `kubectl get endpoints webapp-svc` shows IP
3. Test client successfully connects to webapp-svc:80

## Debug Commands
```bash
kubectl get pods -n case12-configmap-selector
kubectl logs -n case12-configmap-selector deployment/webapp
kubectl get configmap app-config -n case12-configmap-selector -o yaml
kubectl get endpoints webapp-svc -n case12-configmap-selector
kubectl get svc webapp-svc -n case12-configmap-selector -o yaml
```
