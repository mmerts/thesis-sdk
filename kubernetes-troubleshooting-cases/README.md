# Kubernetes Troubleshooting Test Cases

Bu repository, KubeLLM makalesinde kullanılan 8 farklı Kubernetes konfigürasyon hatası senaryosunu içermektedir. Her test case, gerçek dünyada sık karşılaşılan sorunları simüle eder.

## 📋 Test Case'leri

### 1. Wrong Port
**Klasör:** `1_wrong_port/`
**Problem:** Uygulama, Dockerfile ve Kubernetes manifest'i arasında port uyumsuzluğu
**Hata Türü:** Runtime connectivity issue
**Zorluk:** ⭐⭐

### 2. Incorrect Selector
**Klasör:** `2_incorrect_selector/`
**Problem:** Service selector ile Pod label'ları eşleşmiyor
**Hata Türü:** Service endpoint discovery failure
**Zorluk:** ⭐⭐⭐

### 3. Liveness Probe Misconfiguration
**Klasör:** `3_liveness_probe/`
**Problem:** Liveness probe var olmayan endpoint'i kontrol ediyor
**Hata Türü:** Pod restart loop (CrashLoopBackOff)
**Zorluk:** ⭐⭐⭐

### 4. Wrong Interface
**Klasör:** `4_wrong_interface/`
**Problem:** Uygulama localhost'a bind oluyor, 0.0.0.0 yerine
**Hata Türü:** Network connectivity from outside container
**Zorluk:** ⭐⭐⭐⭐

### 5. Port Mismatch
**Klasör:** `5_port_mismatch/`
**Problem:** Çoklu layer'da (app, Dockerfile, Pod, Service) farklı portlar
**Hata Türü:** Multi-layer configuration inconsistency
**Zorluk:** ⭐⭐⭐⭐

### 6. Misspelling
**Klasör:** `6_misspelling/`
**Problem:** Image adı, label'lar ve değişkenlerde yazım hataları
**Hata Türü:** Multiple typos causing ImagePullBackOff and selector mismatch
**Zorluk:** ⭐⭐

### 7. Volume Mount
**Klasör:** `7_volume_mount/`
**Problem:** Volume var olmayan bir ConfigMap'i reference ediyor
**Hata Türü:** CreateContainerConfigError
**Zorluk:** ⭐⭐⭐

### 8. Environment Variable
**Klasör:** `8_environment_variable/`
**Problem:** Gerekli environment variable'lar tanımlanmamış
**Hata Türü:** Application startup failure (CrashLoopBackOff)
**Zorluk:** ⭐⭐⭐⭐

## 🚀 Kullanım

### Gereksinimler
- Docker
- Kubernetes (Minikube, kind, veya herhangi bir cluster)
- kubectl

### Test Case Çalıştırma

Her test case için:

```bash
cd <test-case-folder>

# 1. Docker image build et
docker build -t <app-name>:latest .

# 2. Kubernetes'e deploy et (hatalı konfigürasyon)
kubectl apply -f deployment.yaml

# 3. Hatayı gözlemle
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>

# 4. README'deki çözümü uygula

# 5. Temizlik
kubectl delete -f deployment.yaml
```

### Örnek: Wrong Port Test Case

```bash
cd 1_wrong_port/

# Build
docker build -t wrong-port-app:latest .

# Deploy
kubectl apply -f deployment.yaml

# Hatayı gözlemle
kubectl get pods
kubectl describe pod wrong-port-app
# Port 8000 exposed ama uygulama 8765'te dinliyor

# Fix
# Dockerfile: EXPOSE 8000 -> EXPOSE 8765
# deployment.yaml: containerPort: 8000 -> containerPort: 8765

# Rebuild & redeploy
docker build -t wrong-port-app:latest .
kubectl delete -f deployment.yaml
kubectl apply -f deployment.yaml
```

## 📊 Test Case Özeti Tablosu

| # | Test Case | Ana Hata | Kubernetes Status | Çözüm Zorluğu |
|---|-----------|----------|-------------------|---------------|
| 1 | Wrong Port | Port mismatch | Running (unreachable) | Kolay |
| 2 | Incorrect Selector | Label-selector mismatch | Running (no endpoints) | Orta |
| 3 | Liveness Probe | Wrong probe path | CrashLoopBackOff | Orta |
| 4 | Wrong Interface | Localhost binding | Running (unreachable) | Zor |
| 5 | Port Mismatch | Multi-layer port conflicts | Running (unreachable) | Zor |
| 6 | Misspelling | Typos | ImagePullBackOff | Kolay |
| 7 | Volume Mount | Missing ConfigMap | CreateContainerConfigError | Orta |
| 8 | Environment Variable | Missing env vars | CrashLoopBackOff | Zor |

## 🎯 Öğrenme Hedefleri

Bu test case'leri kullanarak:

1. **Kubernetes debugging** becerilerini geliştirin
2. **kubectl** komutlarını öğrenin (`describe`, `logs`, `get events`)
3. **Runtime vs. compile-time** hatalarını ayırt edin
4. **Multi-layer configuration** tutarlılığının önemini anlayın
5. **Production-ready** deployment best practices'lerini öğrenin

## 🔍 Debug Araçları

Her test case'te kullanılabilecek temel komutlar:

```bash
# Pod durumunu kontrol et
kubectl get pods
kubectl get pods -o wide

# Detaylı bilgi
kubectl describe pod <pod-name>

# Logları incele
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Önceki crash'in logları

# Events
kubectl get events --sort-by='.lastTimestamp'

# Service endpoints
kubectl get endpoints <service-name>
kubectl describe service <service-name>

# ConfigMap/Secret kontrolü
kubectl get configmaps
kubectl describe configmap <name>

# Port-forward ile test
kubectl port-forward pod/<pod-name> 8080:8080

# Pod içine exec
kubectl exec -it <pod-name> -- /bin/sh
kubectl exec <pod-name> -- curl localhost:8080
```

## 📚 Kaynaklar

- **KubeLLM Paper:** "LLM-Based Multi-Agent Framework For Troubleshooting Distributed Systems"
- **Original Repository:** https://github.com/cloudsyslab/KubeLLM
- **Kubernetes Documentation:** https://kubernetes.io/docs/
- **Troubleshooting Guide:** https://kubernetes.io/docs/tasks/debug/

## 🤝 Katkıda Bulunma

Yeni test case'leri eklemek için:

1. Yeni klasör oluşturun: `<number>_<test-name>/`
2. Gerekli dosyaları ekleyin:
   - `server.py` (uygulama kodu)
   - `Dockerfile` (container tanımı)
   - `deployment.yaml` (Kubernetes manifest - HATALI)
   - `README.md` (problem açıklaması ve çözüm)
3. Ana README'yi güncelleyin

## 📝 Notlar

- Bu test case'leri **eğitim amaçlıdır**
- Gerçek production ortamında kullanmayın
- Her test case kasıtlı olarak **hatalı** konfigürasyon içerir
- Çözümler README dosyalarında açıklanmıştır

## 🏆 Başarı Kriterleri

Bir test case'i başarıyla çözdüğünüzde:

- ✅ Pod `Running` durumuna geçmeli
- ✅ Health check'ler başarılı olmalı
- ✅ Service endpoint'leri görünür olmalı
- ✅ Application erişilebilir olmalı
- ✅ Log'larda hata olmamalı

## 📞 İletişim

Sorularınız için issue açabilir veya pull request gönderebilirsiniz.

---

**⚠️ Uyarı:** Bu repository eğitim amaçlıdır. Production kullanımı için Kubernetes best practices'lerini takip edin.
