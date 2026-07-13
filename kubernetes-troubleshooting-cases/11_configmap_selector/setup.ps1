# Case 12: ConfigMap + Selector Mismatch Setup Script
Write-Host "Setting up Case 12: ConfigMap + Selector Mismatch (2 bugs)..." -ForegroundColor Cyan
kubectl apply -f "$PSScriptRoot\deployment.yaml"
Write-Host "Waiting for pods to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
Write-Host "`nCurrent pod status:" -ForegroundColor Green
kubectl get pods -n case12-configmap-selector
Write-Host "`nCase 12 setup complete!" -ForegroundColor Cyan
Write-Host "Expected: webapp pod in CrashLoopBackOff (ConfigMap key not found)" -ForegroundColor Yellow
