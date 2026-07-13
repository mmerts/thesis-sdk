# Misspelling Test Case

## Problem
Multiple typos causing various failures across the deployment.

## Issue Details - Multiple Typos!

### 1. Image Name Typo
```yaml
image: misspeling-app:latset
         ^^^^^^^       ^^^^
    Should be: misspelling    latest
```
**Result:** `ImagePullBackOff` - Image not found

### 2. Label Typo
```yaml
# Pod labels
tier: fronted
      ^^^^^^^
# Service selector
tier: frontend
```
**Result:** Service has no endpoints (selector mismatch)

### 3. Environment Variable Typo
```yaml
APP_NAME: "MyApplicaton"
               ^^^^^^^^^
          Should be: MyApplication
```
**Result:** Incorrect configuration value (less critical but still wrong)

## Expected Behavior

**Pod Status:**
```bash
NAME                        READY   STATUS              RESTARTS
misspelling-xxx-yyy         0/1     ImagePullBackOff    0
```

**Service Status:**
```bash
$ kubectl describe service misspelling-service
Endpoints: <none>  # Even if pods were running, selector wouldn't match
```

## Symptoms
1. **ImagePullBackOff:**
   - Kubernetes cannot find `misspeling-app:latset`
   - Events show: "Failed to pull image"
   - Pod never starts

2. **Selector Mismatch:**
   - Even if image name is fixed, service won't route traffic
   - Labels don't match selectors
   - Zero endpoints

## Solution

### Fix 1: Image Name
```yaml
# From:
image: misspeling-app:latset

# To:
image: misspelling-app:latest
```

### Fix 2: Label
```yaml
# From:
tier: fronted

# To:
tier: frontend
```

### Fix 3: Environment Variable (optional)
```yaml
# From:
APP_NAME: "MyApplicaton"

# To:
APP_NAME: "MyApplication"
```

## Test Commands
```bash
# Try to deploy (will fail)
kubectl apply -f deployment.yaml

# Check pod status
kubectl get pods  # ImagePullBackOff

# Check events
kubectl describe pod <pod-name>  # Shows image pull failures

# Check service
kubectl describe service misspelling-service  # No endpoints
```

## Why This is Common
- Copy-paste errors
- Manual typing mistakes
- No spell-checker for YAML files
- Case sensitivity issues
- Similar-looking words (frontend/fronted)
- No validation until runtime

## Learning Points
1. Image tags are case-sensitive and must match exactly
2. Label-selector pairs must match character-for-character
3. Typos can cascade into multiple issues
4. Static analysis tools might catch some (not all) of these
5. Use image digests instead of tags for immutability

## Real-World Impact
These simple typos can cause:
- Failed deployments
- Production outages
- Hours of debugging time
- "It works on my machine" syndrome
