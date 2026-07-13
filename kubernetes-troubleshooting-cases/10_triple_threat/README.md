# Case 13: Triple Threat (3 Bugs)

## Difficulty: VERY HARD

## Scenario
A webapp deployment is completely broken with multiple simultaneous issues.

## Bugs (Must fix ALL THREE)

### Bug 1: Wrong Image Tag (Typo)
- Image specified: `nginx:latets`
- Should be: `nginx:latest`
- **Result:** ImagePullBackOff

### Bug 2: ConfigMap Not Mounted
- ConfigMap `webapp-config` exists with nginx config
- Volume mount is MISSING in deployment
- **Result:** Even if image fixed, custom config not applied

### Bug 3: Service Port Mismatch
- Nginx listens on: **port 80**
- Service targetPort: **8080**
- **Result:** Connection refused even if pod runs

## Expected Agent Behavior

### Without Reflection (likely to fail)
```
Trial 1: Fix image typo -> Pod runs but test-client fails
Trial 2: ??? (might not identify remaining issues)
```

### With Reflection (better chance)
```
Trial 1: Fix image typo -> Still FAIL
Reflection: "Image is fixed, pod running, but connectivity fails.
             Need to check service ports and app config..."
Trial 2: Fix port -> Still might fail (config)
Reflection: "Port fixed but app behavior wrong. ConfigMap exists
             but might not be mounted..."
```

## Solution
```bash
# Fix 1: Correct image tag
kubectl set image deployment/webapp -n case13-triple nginx=nginx:latest

# Fix 2: Add ConfigMap mount (need to patch deployment)
kubectl patch deployment webapp -n case13-triple --type='json' -p='[
  {"op":"add","path":"/spec/template/spec/volumes","value":[{"name":"config","configMap":{"name":"webapp-config"}}]},
  {"op":"add","path":"/spec/template/spec/containers/0/volumeMounts","value":[{"name":"config","mountPath":"/etc/nginx/conf.d"}]}
]'

# Fix 3: Correct service port
kubectl patch svc webapp-svc -n case13-triple -p '{"spec":{"ports":[{"port":80,"targetPort":80}]}}'
```

## Verification
```bash
# Check pod status (should be Running)
kubectl get pods -n case13-triple

# Check service endpoints
kubectl get endpoints webapp-svc -n case13-triple

# Test from test-client
kubectl logs test-client -n case13-triple
```
