# Environment Variable Test Case

## Problem
Application requires environment variables that are not defined in the deployment.

## Issue Details
**Application requires:**
- `APP_MODE` ❌ Missing
- `DATABASE_URL` ✅ Defined
- `API_KEY` ❌ Missing

**Deployment defines:**
- Only `DATABASE_URL`

## Expected Behavior

**Pod Status:**
```bash
NAME          READY   STATUS             RESTARTS
env-var-app   0/1     CrashLoopBackOff   3
```

**Pod Logs:**
```
ERROR: Missing required environment variables: APP_MODE, API_KEY
Traceback (most recent call last):
  File "server.py", line 21, in <module>
    raise EnvironmentError(error_msg)
EnvironmentError: Missing required environment variables: APP_MODE, API_KEY
```

## Symptoms
1. Pod starts but crashes immediately
2. Container restarts repeatedly (CrashLoopBackOff)
3. Logs show EnvironmentError
4. Back-off delay increases: 10s, 20s, 40s, 80s, 160s (max 5 minutes)
5. Pod never reaches Running state

## Root Cause Analysis

### Application Code (server.py):
```python
REQUIRED_ENV_VARS = ['APP_MODE', 'DATABASE_URL', 'API_KEY']

missing_vars = check_environment()
if missing_vars:
    raise EnvironmentError(f"Missing: {', '.join(missing_vars)}")
```

### Deployment Config (INCOMPLETE):
```yaml
env:
- name: DATABASE_URL
  value: "postgresql://db:5432/mydb"
# Missing APP_MODE and API_KEY!
```

## Solution

Add missing environment variables to `deployment.yaml`:

```yaml
env:
- name: DATABASE_URL
  value: "postgresql://db:5432/mydb"
- name: APP_MODE
  value: "production"
- name: API_KEY
  value: "secret-key-here"
```

**Better approach using ConfigMap/Secret:**

```yaml
# Create ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: "production"
  DATABASE_URL: "postgresql://db:5432/mydb"

---
# Create Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  API_KEY: "secret-key-here"

---
# Use in deployment
spec:
  containers:
  - name: env-var-app
    envFrom:
    - configMapRef:
        name: app-config
    - secretRef:
        name: app-secrets
```

## Test Commands

```bash
# Build image
docker build -t env-var-app:latest .

# Deploy (will fail)
kubectl apply -f deployment.yaml

# Check status
kubectl get pods
# env-var-app   0/1   CrashLoopBackOff   3   2m

# Check logs
kubectl logs env-var-app
# ERROR: Missing required environment variables: APP_MODE, API_KEY

# Fix and redeploy
kubectl apply -f deployment-fixed.yaml

# Verify success
kubectl get pods
# env-var-app   1/1   Running   0   10s

kubectl logs env-var-app
# Starting in production mode
```

## Common Scenarios

### 1. Different environments
```
Development: APP_MODE=dev
Staging: APP_MODE=staging
Production: APP_MODE=production
```
Easy to forget when moving between environments

### 2. Secrets management
```
API_KEY should come from:
- Kubernetes Secret
- External secret manager (Vault, AWS Secrets Manager)
- NOT hardcoded in deployment files!
```

### 3. Optional vs Required
```python
# Optional (with default)
log_level = os.environ.get('LOG_LEVEL', 'INFO')

# Required (will crash if missing)
api_key = os.environ['API_KEY']  # KeyError if missing
```

## Learning Points
1. **Always validate required environment variables** at startup
2. **Use ConfigMaps** for non-sensitive configuration
3. **Use Secrets** for sensitive data (API keys, passwords)
4. **Document required env vars** in README or comments
5. **Consider using envFrom** for cleaner syntax
6. **Use dotenv files** locally, ConfigMaps/Secrets in Kubernetes

## Real-World Impact
- Very common issue when:
  - Moving from local development to Kubernetes
  - Switching between environments (dev/staging/prod)
  - Multiple developers with different configs
  - CI/CD pipelines with environment-specific settings

- Can cause:
  - Deployment failures
  - CrashLoopBackOff loops
  - Security issues (hardcoded secrets)
  - Configuration drift between environments

## Debug Checklist
- [ ] Check application logs for environment variable errors
- [ ] List required env vars in application code
- [ ] Compare with deployment.yaml env section
- [ ] Verify ConfigMaps/Secrets exist
- [ ] Check env var names for typos
- [ ] Ensure correct namespace for ConfigMaps/Secrets
