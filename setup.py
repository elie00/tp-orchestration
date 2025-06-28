#!/usr/bin/env python3
"""
Script de setup et d'initialisation du projet road-sign-ml
Ce script configure l'environnement, installe les dépendances et teste les composants de base.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Vérifie que la version de Python est compatible"""
    min_version = (3, 10)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        logger.error(f"Python {min_version[0]}.{min_version[1]}+ requis. Version actuelle: {current_version[0]}.{current_version[1]}")
        return False
    
    logger.info(f"✅ Version Python OK: {current_version[0]}.{current_version[1]}")
    return True

def check_project_structure():
    """Vérifie que la structure du projet est correcte"""
    required_dirs = [
        "conf/base",
        "data",
        "src/ml_pipelines", 
        "src/api",
        "requirements",
        "logs"
    ]
    
    required_files = [
        "conf/base/model_config.yml",
        "conf/base/mlflow_config.yml",
        "conf/base/logging.yml",
        "requirements/base.txt",
        "pyproject.toml"
    ]
    
    project_root = Path.cwd()
    logger.info(f"Vérification de la structure dans: {project_root}")
    
    # Vérification des dossiers
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            logger.error(f"❌ Dossier manquant: {dir_path}")
            return False
        logger.info(f"✅ Dossier trouvé: {dir_path}")
    
    # Vérification des fichiers
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            logger.error(f"❌ Fichier manquant: {file_path}")
            return False
        logger.info(f"✅ Fichier trouvé: {file_path}")
    
    return True

def setup_virtual_environment():
    """Configure l'environnement virtuel si nécessaire"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        logger.info("Création de l'environnement virtuel...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            logger.info("✅ Environnement virtuel créé")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Erreur création venv: {e}")
            return False
    else:
        logger.info("✅ Environnement virtuel existant trouvé")
    
    return True

def install_dependencies():
    """Installe les dépendances de base"""
    logger.info("Installation des dépendances de base...")
    
    # Déterminer l'exécutable pip dans le venv
    if sys.platform == "win32":
        pip_executable = "venv/Scripts/pip"
        python_executable = "venv/Scripts/python"
    else:
        pip_executable = "venv/bin/pip"
        python_executable = "venv/bin/python"
    
    try:
        # Mise à jour de pip
        subprocess.run([python_executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        logger.info("✅ pip mis à jour")
        
        # Installation des dépendances de base
        subprocess.run([pip_executable, "install", "-r", "requirements/base.txt"], check=True)
        logger.info("✅ Dépendances de base installées")
        
        # Installation des dépendances de développement
        subprocess.run([pip_executable, "install", "-r", "requirements/dev.txt"], check=True)
        logger.info("✅ Dépendances de développement installées")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur installation dépendances: {e}")
        return False

def test_imports():
    """Teste que les imports principaux fonctionnent"""
    logger.info("Test des imports principaux...")
    
    test_imports = [
        ("mlflow", "MLflow"),
        ("fastapi", "FastAPI"),
        ("ultralytics", "Ultralytics YOLO"),
        ("cv2", "OpenCV"),
        ("PIL", "Pillow"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("torch", "PyTorch"),
        ("yaml", "PyYAML")
    ]
    
    failed_imports = []
    
    for module, name in test_imports:
        try:
            __import__(module)
            logger.info(f"✅ {name} importé avec succès")
        except ImportError as e:
            logger.error(f"❌ Échec import {name}: {e}")
            failed_imports.append(name)
    
    if failed_imports:
        logger.error(f"❌ Imports échoués: {', '.join(failed_imports)}")
        return False
    
    logger.info("✅ Tous les imports principaux réussis")
    return True

def test_mlflow_setup():
    """Teste la configuration MLflow"""
    logger.info("Test de la configuration MLflow...")
    
    try:
        import mlflow
        
        # Test de connexion locale
        mlflow.set_tracking_uri("sqlite:///mlflow.db")
        
        # Création d'un run de test
        with mlflow.start_run(run_name="setup_test"):
            mlflow.log_param("setup_test", "success")
            mlflow.log_metric("test_metric", 1.0)
            mlflow.set_tag("test_tag", "setup")
        
        logger.info("✅ MLflow configuré et testé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur test MLflow: {e}")
        return False

def test_data_pipeline():
    """Teste le pipeline de données de base"""
    logger.info("Test du pipeline de données...")
    
    try:
        # Import du pipeline
        sys.path.append("src")
        from ml_pipelines.data_pipeline import DataPipeline
        
        # Test d'initialisation
        pipeline = DataPipeline()
        logger.info("✅ Pipeline de données initialisé")
        
        # Test de création des répertoires
        pipeline._create_directories()
        logger.info("✅ Répertoires créés")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur test pipeline données: {e}")
        return False

def create_readme():
    """Crée un README de base pour le projet"""
    readme_content = """# 🚦 Road Sign ML Project

Système d'industrialisation ML pour la détection et reconnaissance de panneaux routiers.

## 🎯 Objectifs

- **Détection** : YOLOv8 pour identifier les panneaux routiers
- **OCR** : Tesseract/EasyOCR pour lire le texte des panneaux
- **Stack** : MLflow + FastAPI + Kubernetes

## 🛠️ Stack Technique

- **ML Pipeline** : MLflow pour tracking et gestion des modèles
- **API** : FastAPI avec documentation automatique
- **Containerisation** : Docker multi-stage
- **Orchestration** : Kubernetes + Helm
- **CI/CD** : GitHub Actions
- **Monitoring** : Prometheus + Grafana

## 🚀 Quick Start

### 1. Setup initial

```bash
# Clone et setup
cd road_sign_ml_project
python3.10 setup.py

# Activation environnement virtuel
source venv/bin/activate  # Linux/Mac
# ou
venv\\Scripts\\activate  # Windows
```

### 2. Lancement pipeline données

```bash
python3.10 src/ml_pipelines/data_pipeline.py
```

### 3. Interface MLflow

```bash
mlflow ui --host 0.0.0.0 --port 5000
```

Accès : http://localhost:5000

## 📁 Structure du projet

```
road_sign_ml_project/
├── conf/base/              # Configuration
├── data/                   # Données (gitignore)
├── src/
│   ├── ml_pipelines/       # Pipelines ML
│   ├── api/               # API FastAPI
│   └── tests/             # Tests unitaires
├── docker/                # Containers
├── kubernetes/            # Manifests K8s
├── requirements/          # Dépendances
└── logs/                  # Logs applicatifs
```

## 📊 Métriques cibles

- **Coverage tests** : ≥ 80%
- **Performance API** : < 2s par prédiction
- **Scalabilité K8s** : 1-10 replicas auto
- **Disponibilité** : 99.9% uptime

## 📝 Documentation

- **Configuration** : `conf/base/`
- **Récapitulatif** : `RECAPITULATIF.md`
- **API Docs** : http://localhost:8000/docs (après lancement API)

## 🔧 Développement

```bash
# Tests
pytest src/tests/ --cov=src --cov-report=html

# Linting
black src/
isort src/
flake8 src/

# Type checking
mypy src/
```

## 🐳 Docker

```bash
# Build
docker build -t road-sign-ml:latest .

# Run
docker run -p 8000:8000 road-sign-ml:latest
```

## ☸️ Kubernetes

```bash
# Deploy
kubectl apply -f kubernetes/

# Check status
kubectl get pods,svc,hpa
```

---

**Auteur :** eybo  
**Statut :** En développement actif  
**Version :** 0.1.0
"""
    
    readme_path = Path("README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    logger.info("✅ README.md créé")

def main():
    """Point d'entrée principal du script de setup"""
    logger.info("🚀 === SETUP DU PROJET ROAD-SIGN-ML ===")
    
    # Vérifications préliminaires
    if not check_python_version():
        sys.exit(1)
    
    if not check_project_structure():
        logger.error("❌ Structure de projet incorrecte")
        sys.exit(1)
    
    # Setup environnement virtuel
    if not setup_virtual_environment():
        logger.error("❌ Échec création environnement virtuel")
        sys.exit(1)
    
    # Installation dépendances
    logger.info("⚠️  Installation des dépendances (cela peut prendre plusieurs minutes)...")
    if not install_dependencies():
        logger.error("❌ Échec installation dépendances")
        sys.exit(1)
    
    # Tests de base
    if not test_imports():
        logger.error("❌ Échec tests d'imports")
        sys.exit(1)
    
    if not test_mlflow_setup():
        logger.error("❌ Échec test MLflow")
        sys.exit(1)
    
    if not test_data_pipeline():
        logger.error("❌ Échec test pipeline données")
        sys.exit(1)
    
    # Création documentation
    create_readme()
    
    # Message de succès
    logger.info("🎉 === SETUP TERMINÉ AVEC SUCCÈS ===")
    print("\n" + "="*60)
    print("✅ PROJET ROAD-SIGN-ML PRÊT POUR LE DÉVELOPPEMENT!")
    print("="*60)
    print("\n📋 PROCHAINES ÉTAPES:")
    print("1. Activer l'environnement virtuel:")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("\n2. Lancer le pipeline de données:")
    print("   python3.10 src/ml_pipelines/data_pipeline.py")
    print("\n3. Démarrer MLflow UI:")
    print("   mlflow ui --host 0.0.0.0 --port 5000")
    print("   Accès: http://localhost:5000")
    print("\n4. Consulter le récapitulatif:")
    print("   cat RECAPITULATIF.md")
    print("\n🔗 Documentation complète: README.md")
    print("="*60)

if __name__ == "__main__":
    main()
