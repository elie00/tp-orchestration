#!/usr/bin/env python3.10
"""
Script de lancement simple et robuste pour Road Sign ML API
"""

import sys
import subprocess
import os
from pathlib import Path

def main():
    print("🚀 === LANCEMENT RAPIDE ROAD SIGN ML ===")
    
    # Vérification du répertoire
    if not Path("requirements/minimal.txt").exists():
        print("❌ Erreur: Fichier requirements/minimal.txt non trouvé")
        print("Assurez-vous d'être dans le répertoire du projet")
        return 1
    
    print("📦 Installation des dépendances minimales...")
    
    # Installation des dépendances
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        print("✅ pip mis à jour")
        
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements/minimal.txt"], 
                      check=True, capture_output=True)
        print("✅ Dépendances installées")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur d'installation: {e}")
        return 1
    
    # Test des imports
    print("🧪 Test des imports...")
    try:
        import fastapi
        import uvicorn
        import pydantic
        import numpy
        import PIL
        print("✅ Tous les imports OK")
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return 1
    
    # Vérification du fichier API
    if not Path("src/api/main_simple.py").exists():
        print("❌ Fichier src/api/main_simple.py non trouvé")
        return 1
    
    # Lancement de l'API
    print("\n" + "="*50)
    print("✅ LANCEMENT DE L'API!")
    print("="*50)
    print("🌐 API: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("💚 Health: http://localhost:8000/health")
    print("\n⚠️  Appuyez sur Ctrl+C pour arrêter")
    print("="*50)
    
    try:
        subprocess.run([sys.executable, "src/api/main_simple.py"])
    except KeyboardInterrupt:
        print("\n🛑 API arrêtée")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
