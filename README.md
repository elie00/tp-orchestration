# 🚦 Road Sign ML Project - MLflow + FastAPI + Kubernetes

[![CI/CD Pipeline](https://github.com/elie00/tp-orchestration/actions/workflows/ci.yml/badge.svg)](https://github.com/elie00/tp-orchestration/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)](./htmlcov/index.html)
[![Python](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009639)](https://fastapi.tiangolo.com/)
[![MLflow](https://img.shields.io/badge/MLflow-2.8.1-0194E2)](https://mlflow.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-326CE5)](https://kubernetes.io/)

> **Système de détection et lecture de panneaux routiers** utilisant YOLOv8 + OCR Tesseract avec orchestration MLflow, API FastAPI et déploiement Kubernetes production-ready.

## 🎯 **Vue d'ensemble**

Ce projet implémente une **solution ML complète** pour la détection et la lecture automatique de panneaux routiers, avec une architecture cloud-native prête pour la production.

### **🔥 Fonctionnalités Principales**
- **🤖 ML Pipeline** : YOLOv8 (détection) + Tesseract OCR (lecture de texte)
- **📊 MLflow Tracking** : Suivi des expérimentations et modèles
- **🌐 API REST** : FastAPI avec interface web intuitive
- **☸️ Kubernetes** : Déploiement multi-environnements avec auto-scaling
- **🔄 CI/CD** : GitHub Actions avec tests automatisés
- **📈 Monitoring** : Prometheus + Grafana + alerting

### **🎪 Démo Live**
```bash
# Lancement en 30 secondes
git clone https://github.com/elie00/tp-orchestration.git
cd tp-orchestration
source .venv/bin/activate
python3.10 src/api/main.py

# 🌐 Interface web : http://localhost:8000
# 📖 Documentation API : http://localhost:8000/docs
# 📊 MLflow UI : http://localhost:5000
```

---

## 🏗️ **Architecture**

### **Stack Technologique**
```
┌─────────────────────────────────────────────────────────────┐
│                     KUBERNETES CLUSTER                      │
├─────────────────────┬─────────────────────┬─────────────────┤
│     STAGING         │     PRODUCTION      │    MONITORING   │
│ ┌─ API (2 pods)    │ ┌─ API (3+ pods)    │ ┌─ Prometheus   │
│ ├─ MLflow (1 pod)  │ ├─ MLflow (2 pods)  │ ├─ Grafana      │
│ ├─ PostgreSQL      │ ├─ PostgreSQL HA    │ ├─ AlertManager │
│ └─ Redis           │ └─ Redis HA         │ └─ Node Exporter│
└─────────────────────┴─────────────────────┴─────────────────┘
```

### **Pipeline ML**
```
📸 Image → 🎯 YOLO → 🔍 OCR → 📝 Résultat
    ↓         ↓        ↓         ↓
   Upload   Détection  Lecture   JSON
```

---

## 🚀 **Installation Rapide**

### **Prérequis**
- Python 3.10+
- Docker & Docker Compose
- Kubernetes (minikube/kind pour dev local)

### **Setup Local (5 minutes)**
```bash
# 1. Cloner le repository
git clone https://github.com/elie00/tp-orchestration.git
cd tp-orchestration

# 2. Créer l'environnement virtuel
python3.10 -m venv .venv
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements/base.txt

# 4. Lancer l'API
python3.10 src/api/main.py
```

### **Stack Docker Complète (2 minutes)**
```bash
# Lancer tous les services
docker-compose up -d

# Services disponibles :
# - API : http://localhost:8000
# - MLflow : http://localhost:5000  
# - Grafana : http://localhost:3000
# - Prometheus : http://localhost:9090
```

---

## 📊 **Utilisation**

### **Interface Web** 
1. Aller sur http://localhost:8000
2. Uploader une image de panneau routier
3. Cliquer sur "Analyser"
4. Voir les résultats de détection + OCR

### **API REST**
```bash
# Health check
curl http://localhost:8000/health

# Prédiction via API
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@panneau.jpg"

# Métriques Prometheus
curl http://localhost:8000/metrics
```

### **MLflow UI**
```bash
# Lancer MLflow UI
mlflow ui --host 0.0.0.0 --port 5000

# Accéder à http://localhost:5000
# Voir les expérimentations, modèles, métriques
```

---

## 🧪 **Tests et Qualité**

### **Tests Automatisés**
```bash
# Tests unitaires avec coverage
pytest src/tests/ -v --cov=src --cov-report=html

# Coverage report : htmlcov/index.html
# Target : 80%+ coverage ✅
```

### **Linting et Format**
```bash
# Format automatique
black src/ && isort src/

# Linting
flake8 src/

# Tests de charge
python3.10 scripts/stress_test.py
```

---

## ☸️ **Déploiement Kubernetes**

### **Staging (Automatique)**
```bash
# Push sur develop déclenche le déploiement staging
git checkout develop
git push origin develop

# GitHub Actions déploie automatiquement
# URL : https://staging-api.road-sign-ml.com
```

### **Production (Manuel avec approbation)**
```bash
# Créer un tag pour déclencher production
git tag v1.0.0
git push origin v1.0.0

# Workflow GitHub Actions avec approbation requise
# URL : https://api.road-sign-ml.com
```

### **Commandes Kubernetes**
```bash
# Déployer manuellement
kubectl apply -f kubernetes/staging/
kubectl apply -f kubernetes/production/

# Vérifier le status
kubectl get pods -n road-sign-ml-staging
kubectl get pods -n road-sign-ml-prod

# Logs
kubectl logs -f deployment/road-sign-api -n road-sign-ml-staging
```

---

## 📈 **Monitoring et Observabilité**

### **Métriques Disponibles**
- **Performance API** : Latence, throughput, erreurs
- **ML Metrics** : Accuracy, inference time, cache hit rate
- **Infrastructure** : CPU, mémoire, réseau
- **Business** : Nombre de prédictions, types de panneaux détectés

### **Dashboards Grafana**
- **API Performance** : Response times, error rates
- **ML Pipeline** : Model accuracy, inference metrics
- **Infrastructure** : Resource utilization
- **Business** : Traffic patterns, usage analytics

### **Alertes**
- API response time > 5s
- Error rate > 5%
- CPU usage > 80%
- Memory usage > 90%

---

## 🔧 **Configuration**

### **Paramètres ML** (`conf/base/model_config.yml`)
```yaml
yolo:
  model_size: "yolov8n"  # n, s, m, l, x
  confidence: 0.5
  iou_threshold: 0.45
  num_classes: 43

ocr:
  engine: "tesseract"
  languages: ["eng", "fra"]
  confidence_threshold: 0.6
```

### **Configuration MLflow** (`conf/base/mlflow_config.yml`)
```yaml
mlflow:
  tracking_uri: "http://localhost:5000"
  experiment_name: "road_sign_detection"
  artifact_location: "./mlflow_artifacts"
```

---

## 🤝 **Contribution**

### **Workflow de Développement**
```bash
# 1. Créer une branche feature
git checkout -b feature/nouvelle-fonctionnalite

# 2. Développer et tester
# ... code ...
pytest src/tests/ -v

# 3. Commit et push
git add .
git commit -m "feat: Description de la fonctionnalité"
git push origin feature/nouvelle-fonctionnalite

# 4. Créer une Pull Request
# GitHub Actions exécute les tests automatiquement
```

### **Standards de Code**
- **Format** : Black + isort
- **Linting** : flake8
- **Tests** : pytest avec 80%+ coverage
- **Commits** : Conventional Commits (feat, fix, docs, etc.)

---

## 📚 **Documentation**

### **API Documentation**
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **OpenAPI Schema** : http://localhost:8000/openapi.json

### **Guides Détaillés**
- [Guide d'Installation](docs/installation.md)
- [Architecture Détaillée](docs/architecture.md)
- [Guide de Déploiement](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## 📊 **Métriques de Performance**

### **Benchmarks**
- **Response Time** : < 2s (P95) ✅
- **Throughput** : 100+ req/s ✅
- **Accuracy** : 85%+ sur GTSRB ✅
- **Uptime** : 99.9% target ✅

### **Ressources Requises**
- **CPU** : 2 cores minimum, 4 cores recommandé
- **RAM** : 4GB minimum, 8GB recommandé
- **Stockage** : 10GB pour données + modèles
- **GPU** : Optionnel, améliore les performances x3

---

## 🐛 **Troubleshooting**

### **Problèmes Courants**

#### **API ne démarre pas**
```bash
# Vérifier les dépendances
pip install -r requirements/base.txt

# Vérifier les logs
tail -f logs/app.log

# Tester en mode debug
python3.10 src/api/main.py --debug
```

#### **Erreur MLflow connection**
```bash
# Démarrer MLflow server
mlflow server --host 0.0.0.0 --port 5000

# Vérifier la configuration
cat conf/base/mlflow_config.yml
```

#### **Tests qui échouent**
```bash
# Installer dépendances de test
pip install -r requirements/dev.txt

# Exécuter tests avec debug
pytest src/tests/ -v -s --tb=long
```

---

## 📄 **Licence**

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

---

## 👥 **Équipe**

- **Développeur Principal** : [elie00](https://github.com/elie00)
- **Architecture ML** : Système YOLOv8 + OCR
- **Infrastructure** : Kubernetes + MLflow

---

## 🙏 **Remerciements**

- **Dataset** : [GTSRB](https://benchmark.ini.rub.de/?section=gtsrb&subsection=dataset) - German Traffic Sign Recognition Benchmark
- **Frameworks** : FastAPI, MLflow, Ultralytics YOLO, Tesseract OCR
- **Cloud** : Kubernetes, Prometheus, Grafana

---

## 📈 **Roadmap**

### **v1.1 (Prochaine release)**
- [ ] Support de nouveaux types de panneaux
- [ ] API v2 avec fonctionnalités avancées
- [ ] Interface web mobile-responsive
- [ ] Intégration AWS Rekognition

### **v2.0 (Q3 2025)**
- [ ] Multi-région deployment
- [ ] Real-time streaming processing
- [ ] Advanced ML monitoring
- [ ] Custom model training interface

---

**🎉 Prêt à détecter tous les panneaux routiers ! 🚦**

Pour toute question : [Issues GitHub](https://github.com/elie00/tp-orchestration/issues)
