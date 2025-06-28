#!/usr/bin/env python3.10
"""
Script de lancement sécurisé du projet Road Sign ML
Ce script installe les dépendances progressivement et lance l'API
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def run_command(cmd, description=""):
    """Exécute une commande et gère les erreurs"""
    logger.info(f"🔄 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            logger.info(f"✅ {description} - Succès")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - Erreur: {e}")
        if e.stdout:
            logger.error(f"STDOUT: {e.stdout}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr}")
        return False

def install_minimal_dependencies():
    """Installe d'abord les dépendances minimales"""
    logger.info("📦 Installation des dépendances minimales...")
    
    if not run_command("pip install --upgrade pip", "Mise à jour de pip"):
        return False
    
    if not run_command("pip install -r requirements/minimal.txt", "Installation dépendances minimales"):
        return False
    
    return True

def test_minimal_imports():
    """Teste les imports minimaux"""
    logger.info("🧪 Test des imports minimaux...")
    
    try:
        import fastapi
        logger.info("✅ FastAPI OK")
        
        import uvicorn
        logger.info("✅ Uvicorn OK")
        
        import pydantic
        logger.info("✅ Pydantic OK")
        
        import numpy
        logger.info("✅ NumPy OK")
        
        import PIL
        logger.info("✅ Pillow OK")
        
        logger.info("✅ Tous les imports minimaux réussis")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Erreur d'import: {e}")
        return False

def launch_simple_api():
    """Lance l'API simple"""
    logger.info("🚀 Lancement de l'API simple...")
    
    # Vérification du fichier API
    api_file = Path("src/api/main_simple.py")
    if not api_file.exists():
        logger.error("❌ Fichier src/api/main_simple.py non trouvé")
        return False
    
    logger.info("🌐 API disponible sur: http://localhost:8000")
    logger.info("📖 Documentation sur: http://localhost:8000/docs") 
    logger.info("💚 Health check sur: http://localhost:8000/health")
    logger.info("\n⚠️  Pour arrêter l'API, utilisez Ctrl+C")
    
    # Lancement de l'API
    try:
        subprocess.run([sys.executable, "src/api/main_simple.py"], check=True)
    except KeyboardInterrupt:
        logger.info("\n🛑 Arrêt de l'API demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement de l'API: {e}")
        return False
    
    return True

def install_full_dependencies():
    """Installe les dépendances complètes (optionnel)"""
    logger.info("📦 Installation des dépendances complètes...")
    
    if not run_command("pip install -r requirements/base_fixed.txt", "Installation dépendances complètes"):
        logger.warning("⚠️ Échec installation complète, utilisation du mode simple")
        return False
    
    return True

def main():
    """Point d'entrée principal"""
    logger.info("🚀 === LANCEMENT ROAD SIGN ML PROJECT ===")
    
    # Vérification du répertoire
    if not Path("requirements/minimal.txt").exists():
        logger.error("❌ Fichier requirements/minimal.txt non trouvé")
        logger.error("Assurez-vous d'être dans le répertoire du projet")
        sys.exit(1)
    
    # Étape 1: Installation minimale
    if not install_minimal_dependencies():
        logger.error("❌ Échec installation dépendances minimales")
        sys.exit(1)
    
    # Étape 2: Test des imports
    if not test_minimal_imports():
        logger.error("❌ Échec test des imports")
        sys.exit(1)
    
    # Étape 3: Proposer installation complète
    print("\n" + "="*60)
    print("✅ INFRASTRUCTURE API PRÊTE!")
    print("="*60)
    print("\n🎯 Options de lancement:")
    print("1. Lancer l'API simple maintenant (recommandé)")
    print("2. Installer d'abord toutes les dépendances ML")
    print("3. Quitter")
    
    try:
        choice = input("\nVotre choix (1/2/3): ").strip()
        
        if choice == "1" or choice == "":
            logger.info("🎯 Lancement en mode simple")
            launch_simple_api()
            
        elif choice == "2":
            if install_full_dependencies():
                logger.info("✅ Installation complète réussie")
                print("\nVous pouvez maintenant lancer:")
                print("python3.10 src/api/main.py")
            else:
                logger.warning("⚠️ Installation partielle, lancement en mode simple")
                launch_simple_api()
                
        elif choice == "3":
            logger.info("👋 Au revoir!")
            
        else:
            logger.warning("Choix invalide, lancement en mode simple")
            launch_simple_api()
            
    except KeyboardInterrupt:
        logger.info("\n👋 Au revoir!")

if __name__ == "__main__":
    main()
