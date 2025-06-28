#!/usr/bin/env python3
"""
Script pour créer la structure complète du projet road_sign_ml_project
"""

import os
from pathlib import Path

def create_project_structure():
    """Crée la structure complète du projet"""
    
    # Répertoire racine du projet
    project_root = Path("/Users/eybo/PycharmProjects/road_sign_ml_project")
    
    # Liste des dossiers à créer
    directories = [
        # Configuration
        "conf/base",
        
        # Données (sera dans .gitignore)
        "data/01_raw",
        "data/02_processed", 
        "data/03_features",
        "data/04_models",
        
        # Code source
        "src/ml_pipelines",
        "src/api",
        "src/api/routes",
        "src/api/services", 
        "src/tests",
        
        # Docker
        "docker",
        
        # Kubernetes
        "kubernetes/api",
        "kubernetes/mlflow",
        "kubernetes/monitoring",
        
        # CI/CD
        ".github/workflows",
        
        # Scripts
        "scripts",
        
        # Requirements
        "requirements",
        
        # MLflow
        "mlflow",
        
        # Helm (optionnel)
        "helm/road-sign-app",
        
        # Notebooks pour exploration
        "notebooks",
        
        # Documentation
        "docs",
        
        # Logs
        "logs"
    ]
    
    # Créer tous les dossiers
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Créé: {directory}")
    
    print(f"\n🎉 Structure du projet créée dans {project_root}")

if __name__ == "__main__":
    create_project_structure()
