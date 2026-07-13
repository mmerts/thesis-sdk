# Quick Start Guide

## 🚀 Hızlı Başlangıç

### Ortam Hazırlığı

```bash
# 1. Minikube başlat (eğer yoksa)
minikube start

# 2. Docker daemon'ı Minikube'a yönlendir
eval $(minikube docker-env)

# Veya Docker Desktop kullanıyorsanız:
# Kubernetes'i Docker Desktop'tan aktifleştirin
```

### Test Case'leri Çalıştırma

#### Seçenek 1: Elle Adım Adım

```bash
# Test case klasörüne git
cd 1_wrong_port/

# Image build et
docker build -t wrong-port-app:latest .

# Deploy et (hatalı)
kubectl apply -f deployment.yaml

# Hatayı gözlemle
kubectl get pods
kubectl describe pod wrong-port-app
kubectl logs wrong-port-app

# Düzelt ve yeniden deploy et
# (README'deki talimatları takip et)
```

#### Seçenek 2: Otomatik Test Script'i (Opsiyonel)

Her test case için basit bir test script'i oluşturabilirsiniz:

```bash
#!/bin/bash
# test.sh

set -e

echo "Building Docker image..."
docker build -t $1:latest .

echo "Deploying to Kubernetes..."
kubectl apply -f deployment.yaml

echo "Waiting for pod..."
sleep 5

echo "Pod status:"
kubectl get pods

echo "Pod description:"
kubectl describe pod $2

echo "Pod logs:"
kubectl logs $2 || true

echo "Cleanup:"
kubectl delete -f deployment.yaml
```

Kullanım:
```bash
cd 1_wrong_port/
chmod +x test.sh
./test.sh wrong-port-app wrong-port-app
```

## 📝 Her Test Case için Genel Workflow

### 1. Build Phase
```bash
docker build -t <app-name>:latest .
```

### 2. Deploy Phase
```bash
kubectl apply -f deployment.yaml
# Bazı test case'lerde önce ConfigMap gerekir:
# kubectl apply -f configmap.yaml
```

### 3. Debug Phase
```bash
# Pod durumunu kontrol et
kubectl get pods

# Detaylı inceleme
kubectl describe pod <pod-name>

# Logları oku
kubectl logs <pod-name>

# Events
kubectl get events --sort-by='.lastTimestamp'
```

### 4. Fix Phase
README.md dosyasındaki talimatları takip ederek:
- Dockerfile'ı düzenle
- deployment.yaml'ı düzenle
- server.py'yi düzenle (gerekirse)

### 5. Rebuild & Redeploy
```bash
# Eski deployment'ı sil
kubectl delete -f deployment.yaml

# Yeniden build et
docker build -t <app-name>:latest .

# Yeniden deploy et
kubectl apply -f deployment.yaml

# Doğrula
kubectl get pods
# Pod Running durumda olmalı!
```

### 6. Cleanup
```bash
kubectl delete -f deployment.yaml
```

## 🎯 Test Case Sırası (Zorluk Seviyesine Göre)

### Başlangıç Seviyesi
1. ✅ **Misspelling** (6_misspelling) - En kolay, ImagePullBackOff
2. ✅ **Wrong Port** (1_wrong_port) - Basit port düzeltme

### Orta Seviye
3. ✅ **Incorrect Selector** (2_incorrect_selector) - Label matching
4. ✅ **Liveness Probe** (3_liveness_probe) - Probe configuration
5. ✅ **Volume Mount** (7_volume_mount) - ConfigMap reference

### İleri Seviye
6. ✅ **Environment Variable** (8_environment_variable) - Env var management
7. ✅ **Wrong Interface** (4_wrong_interface) - Network binding
8. ✅ **Port Mismatch** (5_port_mismatch) - Multi-layer debugging

## 🔍 Yaygın Kubectl Komutları

### Pod İnceleme
```bash
kubectl get pods                          # Tüm pod'ları listele
kubectl get pods -o wide                  # IP ve node bilgisiyle
kubectl get pods --watch                  # Gerçek zamanlı izle
kubectl describe pod <pod-name>           # Detaylı bilgi
kubectl logs <pod-name>                   # Log'ları göster
kubectl logs <pod-name> --previous        # Önceki crash logları
kubectl logs <pod-name> -f                # Log'ları takip et
```

### Service İnceleme
```bash
kubectl get svc                           # Service'leri listele
kubectl describe svc <service-name>       # Detaylı bilgi
kubectl get endpoints <service-name>      # Backend pod'ları
```

### ConfigMap & Secrets
```bash
kubectl get configmaps                    # ConfigMap'leri listele
kubectl describe configmap <name>         # İçeriği göster
kubectl get secrets                       # Secret'ları listele
```

### Debugging İçin
```bash
kubectl exec -it <pod-name> -- /bin/sh    # Pod içine gir
kubectl exec <pod-name> -- curl localhost:8080  # Komut çalıştır
kubectl port-forward pod/<pod-name> 8080:8080   # Local'e port forward
kubectl get events --sort-by='.lastTimestamp'   # Events
```

### Temizlik
```bash
kubectl delete pod <pod-name>             # Pod'u sil
kubectl delete -f deployment.yaml         # Tüm kaynakları sil
kubectl delete pods --all                 # Tüm pod'ları sil (dikkat!)
```

## 💡 Debug İpuçları

### Problem: Pod ImagePullBackOff
```bash
kubectl describe pod <pod-name>
# "Failed to pull image" mesajına bak
# Image adını ve tag'ini kontrol et
# Typo var mı?
```

### Problem: Pod CrashLoopBackOff
```bash
kubectl logs <pod-name>
kubectl logs <pod-name> --previous
# Uygulama neden crash oluyor?
# Environment variable eksik mi?
# Liveness probe başarısız mı?
```

### Problem: Pod Running ama erişilemiyor
```bash
kubectl exec <pod-name> -- netstat -tlnp
# Hangi port'ta dinliyor?

kubectl exec <pod-name> -- curl localhost:<port>
# Container içinden erişilebiliyor mu?

kubectl describe svc <service-name>
# Endpoints var mı?
```

### Problem: Service'in endpoint'i yok
```bash
kubectl get pods --show-labels
# Pod label'ları

kubectl describe svc <service-name>
# Service selector

# Label ve selector eşleşiyor mu?
```

## 📚 Ek Kaynaklar

### Kubernetes Debugging
- [Official Debugging Guide](https://kubernetes.io/docs/tasks/debug/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

### Test Tools
```bash
# Geçici test pod'u oluştur
kubectl run test-pod --image=curlimages/curl -it --rm -- sh

# Içinden service'lere curl at
curl http://<service-name>.<namespace>.svc.cluster.local
```

## ⚠️ Önemli Notlar

1. **Docker Context:** Minikube kullanıyorsanız `eval $(minikube docker-env)` yapmayı unutmayın
2. **Image Pull Policy:** `imagePullPolicy: Never` kullanarak local image'ları kullanabilirsiniz
3. **Namespace:** Default namespace kullanıyoruz, farklı namespace için `-n <namespace>` ekleyin
4. **Cleanup:** Her test sonrası `kubectl delete -f deployment.yaml` ile temizleyin

## 🎓 Öğrenme Hedefleri

Bu test case'leri tamamladıktan sonra:
- ✅ Kubernetes pod lifecycle'ını anlayacaksınız
- ✅ kubectl debugging komutlarını kullanabileceksiniz
- ✅ Yaygın configuration hatalarını tanıyacaksınız
- ✅ Multi-layer (app/container/k8s) düşünmeyi öğreneceksiniz
- ✅ Production-ready deployment yapabileceksiniz

Başarılar! 🚀
