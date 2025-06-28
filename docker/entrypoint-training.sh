#!/bin/bash
# ==========================================
# SCRIPT D'ENTRÉE POUR LE CONTENEUR D'ENTRAÎNEMENT
# Configure l'environnement et lance les services appropriés
# ==========================================

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 === INITIALISATION CONTENEUR D'ENTRAÎNEMENT ===${NC}"

# ==========================================
# CONFIGURATION DE L'ENVIRONNEMENT
# ==========================================

# Vérification des variables d'environnement nécessaires
if [ -z "$ENVIRONMENT" ]; then
    export ENVIRONMENT="training"
fi

echo -e "${GREEN}📋 Environnement: ${ENVIRONMENT}${NC}"

# Configuration CUDA si disponible
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}🔥 GPU NVIDIA détecté:${NC}"
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits
    export CUDA_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  Aucun GPU NVIDIA détecté - mode CPU${NC}"
    export CUDA_AVAILABLE=false
fi

# Configuration des répertoires
mkdir -p /workspace/data/{01_raw,02_processed,03_features,04_models}
mkdir -p /workspace/logs
mkdir -p /workspace/mlruns
mkdir -p /workspace/artifacts

# Configuration des permissions
chmod -R 755 /workspace/data
chmod -R 755 /workspace/logs

echo -e "${GREEN}✅ Répertoires configurés${NC}"

# ==========================================
# CONFIGURATION MLFLOW
# ==========================================

# Configuration de la base de données MLflow
if [ ! -f "/workspace/mlflow.db" ]; then
    echo -e "${BLUE}📊 Initialisation de la base MLflow...${NC}"
    cd /workspace
    python -c "
import mlflow
mlflow.set_tracking_uri('sqlite:///mlflow.db')
print('✅ Base MLflow initialisée')
"
fi

# ==========================================
# CONFIGURATION KAGGLE (si clés disponibles)
# ==========================================

if [ -f "/workspace/.kaggle/kaggle.json" ]; then
    echo -e "${GREEN}🔑 Configuration Kaggle détectée${NC}"
    chmod 600 /workspace/.kaggle/kaggle.json
    export KAGGLE_CONFIG_DIR="/workspace/.kaggle"
else
    echo -e "${YELLOW}⚠️  Pas de configuration Kaggle - téléchargement manuel nécessaire${NC}"
fi

# ==========================================
# CONFIGURATION DES MODÈLES PRÉ-ENTRAÎNÉS
# ==========================================

echo -e "${BLUE}📦 Vérification des modèles pré-entraînés...${NC}"

# Téléchargement des modèles YOLO de base si nécessaires
MODELS_DIR="/workspace/models"
mkdir -p $MODELS_DIR

if [ ! -f "$MODELS_DIR/yolov8n.pt" ]; then
    echo -e "${BLUE}⬇️  Téléchargement YOLOv8n...${NC}"
    cd $MODELS_DIR
    wget -q https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt
    echo -e "${GREEN}✅ YOLOv8n téléchargé${NC}"
fi

if [ ! -f "$MODELS_DIR/yolov8s.pt" ]; then
    echo -e "${BLUE}⬇️  Téléchargement YOLOv8s...${NC}"
    cd $MODELS_DIR
    wget -q https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt
    echo -e "${GREEN}✅ YOLOv8s téléchargé${NC}"
fi

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

start_mlflow_ui() {
    echo -e "${BLUE}🖥️  Démarrage MLflow UI...${NC}"
    cd /workspace
    nohup mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db > logs/mlflow.log 2>&1 &
    echo -e "${GREEN}✅ MLflow UI démarré sur http://localhost:5000${NC}"
}

start_jupyter() {
    echo -e "${BLUE}📓 Démarrage Jupyter Lab...${NC}"
    nohup jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root > logs/jupyter.log 2>&1 &
    echo -e "${GREEN}✅ Jupyter Lab démarré sur http://localhost:8888${NC}"
}

start_tensorboard() {
    echo -e "${BLUE}📈 Démarrage TensorBoard...${NC}"
    nohup tensorboard --logdir=/workspace/logs --host=0.0.0.0 --port=6006 > logs/tensorboard.log 2>&1 &
    echo -e "${GREEN}✅ TensorBoard démarré sur http://localhost:6006${NC}"
}

run_training() {
    echo -e "${BLUE}🏋️  Lancement de l'entraînement...${NC}"
    cd /workspace
    python src/ml_pipelines/training_pipeline.py
}

run_data_pipeline() {
    echo -e "${BLUE}📊 Lancement du pipeline de données...${NC}"
    cd /workspace
    python src/ml_pipelines/data_pipeline.py
}

run_inference_test() {
    echo -e "${BLUE}🔍 Test du pipeline d'inférence...${NC}"
    cd /workspace
    python src/ml_pipelines/inference_pipeline.py
}

run_tests() {
    echo -e "${BLUE}🧪 Exécution des tests...${NC}"
    cd /workspace
    python -m pytest src/tests/ -v --cov=src --cov-report=html --cov-report=term
}

show_help() {
    echo -e "${BLUE}🚀 === AIDE CONTENEUR D'ENTRAÎNEMENT ===${NC}"
    echo ""
    echo "Commandes disponibles:"
    echo "  training          - Lance l'entraînement complet"
    echo "  data-pipeline     - Lance le pipeline de données"
    echo "  inference-test    - Test le pipeline d'inférence"
    echo "  mlflow-ui         - Démarre MLflow UI"
    echo "  jupyter           - Démarre Jupyter Lab"
    echo "  tensorboard       - Démarre TensorBoard"
    echo "  tests             - Exécute les tests"
    echo "  shell             - Ouvre un shell interactif"
    echo "  help              - Affiche cette aide"
    echo ""
    echo "Services disponibles:"
    echo "  - MLflow UI: http://localhost:5000"
    echo "  - Jupyter Lab: http://localhost:8888"
    echo "  - TensorBoard: http://localhost:6006"
    echo ""
}

# ==========================================
# GESTION DES COMMANDES
# ==========================================

case "${1:-help}" in
    "training")
        start_mlflow_ui
        sleep 2
        run_data_pipeline
        run_training
        ;;
    "data-pipeline")
        start_mlflow_ui
        sleep 2
        run_data_pipeline
        ;;
    "inference-test")
        start_mlflow_ui
        sleep 2
        run_inference_test
        ;;
    "mlflow-ui")
        start_mlflow_ui
        tail -f logs/mlflow.log
        ;;
    "jupyter")
        start_jupyter
        tail -f logs/jupyter.log
        ;;
    "tensorboard")
        start_tensorboard
        tail -f logs/tensorboard.log
        ;;
    "all-services")
        start_mlflow_ui
        start_jupyter
        start_tensorboard
        echo -e "${GREEN}✅ Tous les services démarrés${NC}"
        echo -e "${BLUE}📋 Logs disponibles dans /workspace/logs/${NC}"
        tail -f logs/*.log
        ;;
    "tests")
        run_tests
        ;;
    "shell")
        echo -e "${GREEN}🐚 Shell interactif - tapez 'exit' pour quitter${NC}"
        /bin/bash
        ;;
    "help"|*)
        show_help
        ;;
esac

echo -e "${GREEN}🎉 === CONTENEUR D'ENTRAÎNEMENT PRÊT ===${NC}"
