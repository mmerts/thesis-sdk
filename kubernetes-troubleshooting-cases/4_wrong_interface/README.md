# Wrong Interface Test Case

## Problem
Application binds to localhost (127.0.0.1) instead of all interfaces (0.0.0.0).

## Issue Details
- **Application:** Binds to `127.0.0.1:8080` ❌
- **Expected:** Should bind to `0.0.0.0:8080` ✅
- **Result:** Pod cannot receive external traffic

## Expected Behavior
```bash
# Inside container: works
kubectl exec wrong-interface-app -- curl localhost:8080  # Success!

# From another pod or service: fails
curl http://wrong-interface-service  # Timeout!
```

## Symptoms
- Pod shows as Running
- No error logs in container
- Application works when tested locally inside container
- External connections timeout
- Network connectivity appears fine

## Root Cause Analysis
When an application binds to `127.0.0.1`:
- Only accepts connections from the same host (loopback interface)
- Connections from other pods/services are rejected
- This is a common mistake when containerizing applications

When binding to `0.0.0.0`:
- Accepts connections from all network interfaces
- Allows external traffic from other pods/services
- Correct for containerized applications

## Solution
Change `server.py` line:
```python
# From:
app.run(host='127.0.0.1', port=8080)

# To:
app.run(host='0.0.0.0', port=8080)
```

## Test Commands
```bash
# Build and deploy
docker build -t wrong-interface-app:latest .
kubectl apply -f deployment.yaml

# Test the problem
kubectl get pods
kubectl exec wrong-interface-app -- curl localhost:8080  # Works!
kubectl run test-pod --image=curlimages/curl -it --rm -- curl http://wrong-interface-service  # Fails!
```

## Common in These Scenarios
- Local development apps moved to containers
- Flask/Django apps without proper host configuration
- Node.js apps binding to localhost by default
