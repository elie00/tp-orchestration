# 🤝 Guide de Contribution - Road Sign ML Project

Merci de contribuer au **Road Sign ML Project** ! Ce guide décrit les bonnes pratiques pour développer, tester et déployer le projet de manière collaborative.

---

## 🎯 **Aperçu du Projet**

Ce projet implémente un système ML de détection de panneaux routiers avec :
- **ML Pipeline** : YOLOv8 + OCR Tesseract
- **API Production** : FastAPI + interface web
- **Infrastructure** : Kubernetes + MLflow + monitoring

---

## 🚀 **Démarrage Rapide**

### **Setup Initial**
```bash
# 1. Fork et clone
git clone https://github.com/elie00/tp-orchestration.git
cd tp-orchestration

# 2. Configuration environnement
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt

# 3. Tests de validation
pytest src/tests/ -v
python3.10 src/api/main.py

# 4. Vérification
curl http://localhost:8000/health
```

---

## 🌳 **Workflow Git**

### **Modèle de Branches**
```
main          ← Production (tags v1.0.0, v1.1.0...)
├── develop   ← Intégration (déploiement staging auto)
│   ├── feature/nouvelle-detection
│   ├── feature/api-v2
│   └── hotfix/security-patch
```

### **Création de Fonctionnalité**
```bash
# 1. Partir de develop
git checkout develop
git pull origin develop

# 2. Créer une branche feature
git checkout -b feature/description-courte

# 3. Développer avec commits atomiques
git add .
git commit -m "feat: Description de la fonctionnalité"

# 4. Push et Pull Request
git push origin feature/description-courte
# Créer PR vers develop sur GitHub
```

### **Types de Branches**
- **`feature/`** : Nouvelles fonctionnalités
- **`bugfix/`** : Corrections de bugs
- **`hotfix/`** : Corrections urgentes
- **`refactor/`** : Refactoring sans nouvelle fonctionnalité
- **`docs/`** : Documentation uniquement

---

## 📝 **Standards de Code**

### **Messages de Commit (Conventional Commits)**
```bash
# Types autorisés :
feat:     # Nouvelle fonctionnalité
fix:      # Correction de bug
docs:     # Documentation
style:    # Format, pas de changement de logique
refactor: # Refactoring
test:     # Ajout de tests
chore:    # Maintenance, dépendances

# Exemples :
git commit -m "feat: Ajouter support panneaux européens"
git commit -m "fix: Corriger detection YOLO avec petites images"
git commit -m "docs: Mettre à jour guide API"
git commit -m "test: Ajouter tests pipeline OCR"
```

### **Format du Code**
```bash
# Formater automatiquement avant commit
black src/ --line-length 88
isort src/ --profile black

# Linting
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503

# Type checking (optionnel)
mypy src/ --ignore-missing-imports
```

### **Standards Python**
- **Style** : PEP 8 + Black formatting
- **Docstrings** : Google style
- **Type Hints** : Encouragés pour les fonctions publiques
- **Imports** : isort avec profil black

---

## 🧪 **Tests et Qualité**

### **Exigences de Tests**
- **Coverage minimum** : 80%
- **Tests unitaires** : Chaque nouvelle fonction
- **Tests d'intégration** : Chaque nouveau endpoint API
- **Tests E2E** : Chaque nouveau pipeline ML

### **Exécution des Tests**
```bash
# Tests complets avec coverage
pytest src/tests/ -v --cov=src --cov-report=html

# Tests spécifiques
pytest src/tests/test_api.py::test_health_endpoint -v

# Tests en mode watch (développement)
pytest-watch src/tests/

# Coverage report
open htmlcov/index.html
```

### **Écriture de Tests**
```python
# Exemple de test unitaire
def test_yolo_detection():
    """Test de détection YOLO avec image de test."""
    from src.ml_pipelines.inference_pipeline import InferencePipeline
    
    pipeline = InferencePipeline()
    result = pipeline.detect_objects("test_images/stop_sign.jpg")
    
    assert result is not None
    assert len(result["detections"]) > 0
    assert result["detections"][0]["class"] == "stop_sign"

# Exemple de test API
def test_predict_endpoint(client):
    """Test endpoint de prédiction."""
    with open("test_images/stop_sign.jpg", "rb") as f:
        response = client.post(
            "/predict",
            files={"file": ("test.jpg", f, "image/jpeg")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "predictions" in data
```

---

## 🏗️ **Développement par Composant**

### **API FastAPI**
```bash
# Structure des endpoints
src/api/
├── main.py              # Point d'entrée
├── routes/
│   ├── predict.py       # Endpoints ML
│   ├── health.py        # Health checks
│   └── monitoring.py    # Métriques
└── services/
    ├── ml_service.py    # Logique ML
    └── image_service.py # Traitement images
```

**Ajouter un endpoint :**
1. Créer la route dans `src/api/routes/`
2. Ajouter les tests dans `src/tests/test_api.py`
3. Documenter avec docstrings FastAPI
4. Tester manuellement avec Swagger UI

### **Pipeline ML**
```bash
# Structure des pipelines
src/ml_pipelines/
├── data_pipeline.py      # Ingestion données
├── training_pipeline.py  # Entraînement modèles
├── inference_pipeline.py # Prédictions
└── evaluation_pipeline.py # Métriques
```

**Ajouter un pipeline :**
1. Créer la classe dans `src/ml_pipelines/`
2. Intégrer tracking MLflow
3. Ajouter tests unitaires
4. Documenter paramètres et outputs

### **Configuration**
```bash
# Configuration centralisée
conf/base/
├── model_config.yml    # Paramètres ML
├── mlflow_config.yml   # Configuration MLflow
└── logging.yml         # Logs
```

**Modifier configuration :**
1. Mettre à jour le fichier YAML
2. Valider avec schema si disponible
3. Tester impact sur tests existants
4. Documenter changements

---

## 🐳 **Docker et Déploiement**

### **Images Docker**
```bash
# Build local pour tests
docker build -f docker/Dockerfile.api -t road-sign-api:dev .

# Test de l'image
docker run -p 8000:8000 road-sign-api:dev

# Push vers registry (automatique via CI/CD)
```

### **Docker Compose**
```bash
# Stack de développement complète
docker-compose up -d

# Services disponibles :
# - API : http://localhost:8000
# - MLflow : http://localhost:5000
# - Grafana : http://localhost:3000
# - Prometheus : http://localhost:9090

# Logs
docker-compose logs -f api
```

### **Kubernetes**
```bash
# Test local avec minikube
minikube start
kubectl apply -f kubernetes/staging/

# Vérification
kubectl get pods -n road-sign-ml-staging
kubectl port-forward svc/road-sign-api 8000:80 -n road-sign-ml-staging
```

---

## 📊 **MLflow et Expérimentations**

### **Tracking des Expérimentations**
```python
import mlflow

# Dans un pipeline ML
with mlflow.start_run(run_name="experiment_name"):
    # Log paramètres
    mlflow.log_params({
        "learning_rate": 0.01,
        "batch_size": 32
    })
    
    # Log métriques
    mlflow.log_metrics({
        "accuracy": 0.95,
        "mAP": 0.87
    })
    
    # Log modèle
    mlflow.sklearn.log_model(model, "model")
```

### **Registre de Modèles**
```python
# Enregistrer un modèle
mlflow.register_model(
    model_uri="runs:/12345/model",
    name="road_sign_yolo"
)

# Promouvoir vers production
client = MlflowClient()
client.transition_model_version_stage(
    name="road_sign_yolo",
    version=1,
    stage="Production"
)
```

---

## 🔍 **Review et Validation**

### **Checklist Pull Request**

#### **Code Quality ✅**
- [ ] Code formaté avec Black + isort
- [ ] Linting flake8 sans erreurs
- [ ] Type hints ajoutés (recommandé)
- [ ] Docstrings pour fonctions publiques

#### **Tests ✅**
- [ ] Tests unitaires ajoutés
- [ ] Coverage ≥ 80% maintenu
- [ ] Tests existants passent
- [ ] Tests E2E si nécessaire

#### **Documentation ✅**
- [ ] README mis à jour si nécessaire
- [ ] Docstrings API mises à jour
- [ ] Changelog mis à jour
- [ ] Comments dans le code complexe

#### **Sécurité ✅**
- [ ] Pas de secrets hardcodés
- [ ] Validation des inputs utilisateur
- [ ] Gestion d'erreurs appropriée
- [ ] Logs appropriés (pas de données sensibles)

#### **Performance ✅**
- [ ] Pas de régression de performance
- [ ] Optimisations si nécessaire
- [ ] Tests de charge si impact attendu

### **Processus de Review**
1. **Auto-checks** : CI/CD exécute tests automatiquement
2. **Review par les pairs** : Au moins 1 approbation
3. **Tests manuels** : Vérifier fonctionnalité
4. **Security check** : Scan automatique des vulnérabilités

---

## 🚀 **Déploiement**

### **Environnements**

#### **Development** (Local)
- **URL** : http://localhost:8000
- **MLflow** : http://localhost:5000
- **Auto-deploy** : Manuel

#### **Staging** (Auto-deploy)
- **URL** : https://staging-api.road-sign-ml.com
- **Trigger** : Push sur `develop`
- **Tests** : Automatiques + manuels

#### **Production** (Approval required)
- **URL** : https://api.road-sign-ml.com
- **Trigger** : Tag `v*.*.*`
- **Approval** : 1+ reviewer requis

### **Processus de Release**
```bash
# 1. Merge develop vers main
git checkout main
git merge develop
git push origin main

# 2. Créer tag de version
git tag v1.2.0
git push origin v1.2.0

# 3. GitHub Actions déclenche déploiement production
# 4. Approbation manuelle requise
# 5. Déploiement automatique après approbation
```

---

## 📈 **Monitoring et Debugging**

### **Logs**
```bash
# Logs locaux
tail -f logs/app.log

# Logs Kubernetes
kubectl logs -f deployment/road-sign-api -n road-sign-ml-prod

# Logs centralisés (Grafana)
# Accéder à Grafana → Explore → Loki
```

### **Métriques**
- **API** : Response time, error rate, throughput
- **ML** : Inference time, model accuracy, cache hit rate
- **Infrastructure** : CPU, memory, disk usage

### **Alertes**
- **Critical** : API down, error rate > 10%
- **Warning** : Response time > 5s, memory > 80%
- **Info** : Déploiement réussi, nouveau modèle

---

## 🆘 **Support et Aide**

### **Problèmes Courants**

#### **Tests qui échouent**
```bash
# Nettoyer cache
pytest --cache-clear
rm -rf .pytest_cache/

# Réinstaller dépendances
pip install -r requirements/dev.txt --force-reinstall

# Debug mode
pytest -v -s --tb=long
```

#### **API ne démarre pas**
```bash
# Vérifier port disponible
lsof -i :8000

# Vérifier dépendances
pip check

# Mode debug
python3.10 src/api/main.py --debug
```

#### **MLflow connection error**
```bash
# Démarrer MLflow server
mlflow server --host 0.0.0.0 --port 5000

# Vérifier configuration
cat conf/base/mlflow_config.yml
```

### **Où Demander de l'Aide**
1. **Documentation** : README.md, docs/
2. **Issues GitHub** : https://github.com/elie00/tp-orchestration/issues
3. **Discussions** : GitHub Discussions
4. **Slack** : #road-sign-ml (si configuré)

---

## 🏆 **Best Practices**

### **Développement**
- **Commits fréquents** : Petits commits atomiques
- **Tests first** : Écrire tests avant fonctionnalité
- **Documentation** : Code self-documented + comments
- **Performance** : Profiler avant optimiser

### **Collaboration**
- **Communication** : Commenter les PRs
- **Reviews constructives** : Suggestions, pas juste critiques
- **Partage de connaissances** : Documentation à jour

### **Déploiement**
- **Gradual rollout** : Staging → Production
- **Monitoring** : Vérifier métriques post-deploy
- **Rollback plan** : Toujours prêt à revenir en arrière

---

## 📞 **Contact**

- **Maintainer** : [elie00](https://github.com/elie00) - elieyvon.b.o@gmail.com
- **Issues** : https://github.com/elie00/tp-orchestration/issues
- **Discussions** : https://github.com/elie00/tp-orchestration/discussions

---

**🎉 Merci de contribuer au Road Sign ML Project ! 🚦**

*Ensemble, construisons le meilleur système de détection de panneaux routiers !*
