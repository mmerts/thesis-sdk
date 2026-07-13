# Volume Mount Test Case

## Problem
Volume references a non-existent ConfigMap, preventing pod from starting.

## Issue Details
- **ConfigMap name:** `app-config` (exists)
- **Volume reference:** `app-configuration` (doesn't exist) ❌
- **Application:** Expects config file at `/etc/config/app.conf`

## Expected Behavior

**Pod Status:**
```bash
NAME                 READY   STATUS                   RESTARTS
volume-mount-app     0/1     CreateContainerConfigError   0
```

**Error Message:**
```
MountVolume.SetUp failed for volume "config-volume" :
configmap "app-configuration" not found
```

## Symptoms
1. Pod stuck in `CreateContainerConfigError` state
2. Container never starts
3. Events show volume mount failures
4. Application code never runs (failure at infrastructure level)

## Root Cause Analysis

### Volume Definition in Pod Spec:
```yaml
volumes:
- name: config-volume
  configMap:
    name: app-configuration  # ❌ This ConfigMap doesn't exist!
```

### Actual ConfigMap:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config  # ✅ This is the real name
```

**Mismatch!** → Kubernetes cannot mount the volume → Pod cannot start

## Solution

Change `deployment.yaml`:
```yaml
# From:
volumes:
- name: config-volume
  configMap:
    name: app-configuration

# To:
volumes:
- name: config-volume
  configMap:
    name: app-config
```

## Test Commands

```bash
# Create ConfigMap
kubectl apply -f configmap.yaml

# Try to create pod (will fail)
kubectl apply -f deployment.yaml

# Check status
kubectl get pods  # CreateContainerConfigError

# See detailed error
kubectl describe pod volume-mount-app
# Events will show:
#   MountVolume.SetUp failed for volume "config-volume"
#   configmap "app-configuration" not found
```

## Alternative Scenarios (Not in this test)

### Scenario 2: Volume name mismatch
```yaml
volumeMounts:
- name: config-vol  # Different name!

volumes:
- name: config-volume  # Different name!
```

### Scenario 3: Secret instead of ConfigMap
```yaml
volumes:
- name: config-volume
  secret:
    secretName: app-secret  # But app-secret doesn't exist
```

## Common Causes
1. Copy-paste errors between environments
2. ConfigMap/Secret renamed but deployment not updated
3. Typos in resource names
4. Wrong namespace (ConfigMap in different namespace)
5. Resource not created yet (ordering issue)

## Learning Points
- Volume mounts are validated at pod creation time
- Name must match exactly (case-sensitive)
- ConfigMap/Secret must exist in the same namespace
- This is caught before the container starts (fail-fast)
- Unlike application errors, this prevents pod from running entirely

## Real-World Impact
- Deployments fail during rollouts
- Pods never reach Running state
- Cannot debug application code (it never runs)
- Requires fixing infrastructure before testing app
