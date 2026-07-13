# Case 12: Cleanup Script
Write-Host "Cleaning up Case 12: ConfigMap + Selector Mismatch..." -ForegroundColor Cyan
kubectl delete namespace case12-configmap-selector --ignore-not-found=true
Write-Host "Case 12 cleanup complete!" -ForegroundColor Green
