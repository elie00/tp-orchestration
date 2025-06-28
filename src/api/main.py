"""
API FastAPI pour le service de détection et reconnaissance de panneaux routiers
Cette API expose les endpoints pour l'inférence et le monitoring.
"""

import logging
import time
import io
import uuid
from pathlib import Path
from typing import Dict, List, Optional
import json

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
from PIL import Image
import cv2

# Import des modules internes
import sys
sys.path.append("src")
from ml_pipelines.inference_pipeline import RoadSignInferencePipeline

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application FastAPI
app = FastAPI(
    title="🚦 Road Sign ML API",
    description="API pour la détection et reconnaissance de panneaux routiers avec YOLOv8 + OCR",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pipeline global (initialisé au démarrage)
pipeline: Optional[RoadSignInferencePipeline] = None

# Statistiques globales
app_stats = {
    "total_predictions": 0,
    "total_detections": 0,
    "total_processing_time": 0.0,
    "start_time": time.time()
}


# ==========================================
# MODÈLES PYDANTIC POUR VALIDATION
# ==========================================

class DetectionResult(BaseModel):
    """Modèle pour une détection individuelle"""
    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiance de détection")
    class_id: int = Field(..., description="ID de la classe")
    class_name: str = Field(..., description="Nom de la classe")
    ocr: Dict = Field(..., description="Résultat OCR")
    has_text: bool = Field(..., description="Présence de texte détecté")


class PredictionResponse(BaseModel):
    """Modèle pour la réponse de prédiction"""
    success: bool = Field(..., description="Succès de la prédiction")
    image_shape: List[int] = Field(..., description="Dimensions de l'image [H, W, C]")
    detections_count: int = Field(..., description="Nombre de détections")
    results: List[DetectionResult] = Field(..., description="Liste des détections")
    processing_time: float = Field(..., description="Temps de traitement en secondes")
    pipeline_version: str = Field(..., description="Version du pipeline")
    request_id: str = Field(..., description="ID unique de la requête")


class HealthResponse(BaseModel):
    """Modèle pour la réponse de santé"""
    status: str = Field(..., description="Statut de l'API")
    pipeline_loaded: bool = Field(..., description="Pipeline chargé")
    uptime: float = Field(..., description="Temps de fonctionnement en secondes")
    total_predictions: int = Field(..., description="Nombre total de prédictions")
    version: str = Field(..., description="Version de l'API")


class MetricsResponse(BaseModel):
    """Modèle pour les métriques Prometheus"""
    total_predictions: int
    total_detections: int
    average_processing_time: float
    uptime: float
    pipeline_status: str


# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def initialize_pipeline():
    """Initialise le pipeline ML global"""
    global pipeline
    try:
        logger.info("Initialisation du pipeline ML...")
        pipeline = RoadSignInferencePipeline()
        logger.info("✅ Pipeline ML initialisé avec succès")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur initialisation pipeline: {e}")
        return False


def update_stats(detections_count: int, processing_time: float):
    """Met à jour les statistiques globales"""
    global app_stats
    app_stats["total_predictions"] += 1
    app_stats["total_detections"] += detections_count
    app_stats["total_processing_time"] += processing_time


def process_uploaded_file(file: UploadFile) -> np.ndarray:
    """
    Traite un fichier uploadé et le convertit en image numpy
    
    Args:
        file: Fichier uploadé
        
    Returns:
        np.ndarray: Image sous forme de tableau numpy
    """
    # Vérification du type de fichier
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400, 
            detail=f"Type de fichier non supporté: {file.content_type}. Utilisez une image."
        )
    
    try:
        # Lecture du fichier
        image_data = file.file.read()
        
        # Conversion en image PIL puis numpy
        pil_image = Image.open(io.BytesIO(image_data))
        
        # Conversion en RGB si nécessaire
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Conversion en numpy array
        numpy_image = np.array(pil_image)
        
        # Conversion RGB vers BGR pour OpenCV
        bgr_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
        
        return bgr_image
        
    except Exception as e:
        logger.error(f"Erreur traitement fichier: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de traiter l'image: {str(e)}"
        )


# ==========================================
# ÉVÉNEMENTS DE CYCLE DE VIE
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage de l'application"""
    logger.info("🚀 Démarrage de l'API Road Sign ML")
    
    # Création des répertoires nécessaires
    Path("logs").mkdir(exist_ok=True)
    Path("temp").mkdir(exist_ok=True)
    
    # Initialisation du pipeline
    if not initialize_pipeline():
        logger.warning("⚠️ Pipeline non initialisé - fonctionnement en mode dégradé")
    
    logger.info("✅ API Road Sign ML démarrée avec succès")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt de l'application"""
    logger.info("🛑 Arrêt de l'API Road Sign ML")
    
    # Nettoyage des fichiers temporaires
    temp_dir = Path("temp")
    if temp_dir.exists():
        for temp_file in temp_dir.glob("*"):
            try:
                temp_file.unlink()
            except Exception:
                pass
    
    logger.info("✅ API Road Sign ML arrêtée proprement")


# ==========================================
# ROUTES PRINCIPALES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Page d'accueil avec interface de test"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🚦 Road Sign ML API</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; }
            .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .upload-area { border: 2px dashed #3498db; padding: 40px; text-align: center; border-radius: 10px; }
            .upload-area:hover { background-color: #ecf0f1; }
            input[type="file"] { margin: 20px 0; }
            button { background-color: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background-color: #2980b9; }
            .result { margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }
            .error { background-color: #f8d7da; color: #721c24; }
            .success { background-color: #d4edda; color: #155724; }
            .stats { display: flex; justify-content: space-around; text-align: center; }
            .stat-item { padding: 15px; }
            .stat-number { font-size: 24px; font-weight: bold; color: #3498db; }
            pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚦 Road Sign ML API</h1>
            <p style="text-align: center; color: #7f8c8d;">
                API de détection et reconnaissance de panneaux routiers avec YOLOv8 + OCR
            </p>
            
            <div class="section">
                <h2>📊 Statistiques en temps réel</h2>
                <div class="stats" id="stats">
                    <div class="stat-item">
                        <div class="stat-number" id="predictions">-</div>
                        <div>Prédictions</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="detections">-</div>
                        <div>Détections</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="uptime">-</div>
                        <div>Uptime (min)</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🖼️ Test de prédiction</h2>
                <div class="upload-area">
                    <p>📁 Glissez-déposez une image ici ou cliquez pour sélectionner</p>
                    <input type="file" id="imageInput" accept="image/*" />
                    <br>
                    <button onclick="predictImage()">🔍 Analyser l'image</button>
                </div>
                <div id="result" class="result" style="display: none;"></div>
                <div id="imagePreview" style="margin-top: 20px; text-align: center;"></div>
            </div>
            
            <div class="section">
                <h2>📚 Documentation</h2>
                <p>
                    <strong>Endpoints disponibles :</strong><br>
                    • <a href="/docs" target="_blank">📖 Documentation Swagger</a><br>
                    • <a href="/health" target="_blank">💚 Health Check</a><br>
                    • <a href="/metrics" target="_blank">📊 Métriques Prometheus</a><br>
                    • <code>POST /predict</code> - Prédiction sur image<br>
                    • <code>POST /predict/batch</code> - Prédiction batch
                </p>
            </div>
        </div>
        
        <script>
            // Mise à jour des statistiques
            async function updateStats() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    document.getElementById('predictions').textContent = data.total_predictions;
                    document.getElementById('uptime').textContent = Math.round(data.uptime / 60);
                    
                    const metricsResponse = await fetch('/metrics');
                    const metricsData = await metricsResponse.json();
                    document.getElementById('detections').textContent = metricsData.total_detections;
                } catch (error) {
                    console.error('Erreur mise à jour stats:', error);
                }
            }
            
            // Prédiction d'image
            async function predictImage() {
                const fileInput = document.getElementById('imageInput');
                const resultDiv = document.getElementById('result');
                const previewDiv = document.getElementById('imagePreview');
                
                if (!fileInput.files[0]) {
                    alert('Veuillez sélectionner une image');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                resultDiv.style.display = 'block';
                resultDiv.className = 'result';
                resultDiv.innerHTML = '⏳ Analyse en cours...';
                
                // Aperçu de l'image
                const file = fileInput.files[0];
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewDiv.innerHTML = `<img src="${e.target.result}" style="max-width: 400px; max-height: 300px; border-radius: 5px;">`;
                };
                reader.readAsDataURL(file);
                
                try {
                    const response = await fetch('/predict', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.className = 'result success';
                        let html = `<h3>✅ Analyse réussie!</h3>
                            <p><strong>Détections trouvées:</strong> ${data.detections_count}</p>
                            <p><strong>Temps de traitement:</strong> ${data.processing_time.toFixed(3)}s</p>`;
                        
                        if (data.results && data.results.length > 0) {
                            html += '<h4>📋 Détails des détections:</h4>';
                            data.results.forEach((result, index) => {
                                html += `
                                    <div style="margin: 10px 0; padding: 10px; background: #e8f4f8; border-radius: 5px;">
                                        <strong>Détection ${index + 1}:</strong><br>
                                        • Classe: ${result.class_name}<br>
                                        • Confiance: ${(result.confidence * 100).toFixed(1)}%<br>
                                        • Texte OCR: "${result.ocr.text}"<br>
                                        • Confiance OCR: ${(result.ocr.confidence * 100).toFixed(1)}%
                                    </div>
                                `;
                            });
                        }
                        
                        resultDiv.innerHTML = html;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<h3>❌ Erreur</h3><p>${data.error || 'Erreur inconnue'}</p>`;
                    }
                    
                    updateStats();
                    
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<h3>❌ Erreur de connexion</h3><p>${error.message}</p>`;
                }
            }
            
            // Mise à jour initiale et périodique des stats
            updateStats();
            setInterval(updateStats, 10000); // Toutes les 10 secondes
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/predict", response_model=PredictionResponse)
async def predict_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Image à analyser")
):
    """
    Effectue une prédiction sur une image uploadée
    
    Args:
        file: Fichier image (JPEG, PNG, etc.)
        
    Returns:
        PredictionResponse: Résultats de la prédiction
    """
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Pipeline ML non initialisé - service indisponible"
        )
    
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"Nouvelle prédiction - ID: {request_id}")
        
        # Traitement du fichier uploadé
        image = process_uploaded_file(file)
        
        # Prédiction
        result = pipeline.predict_image(image)
        
        # Vérification des erreurs
        if 'error' in result:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur de prédiction: {result['error']}"
            )
        
        # Mise à jour des statistiques
        processing_time = result['processing_time']
        detections_count = result['detections_count']
        update_stats(detections_count, processing_time)
        
        # Préparation de la réponse
        response = PredictionResponse(
            success=True,
            image_shape=result['image_shape'],
            detections_count=detections_count,
            results=result['results'],
            processing_time=processing_time,
            pipeline_version=result['pipeline_version'],
            request_id=request_id
        )
        
        # Log asynchrone des métriques
        background_tasks.add_task(
            log_prediction_async, 
            request_id, 
            detections_count, 
            processing_time
        )
        
        logger.info(f"Prédiction réussie - ID: {request_id} - {detections_count} détections")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur prédiction - ID: {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne: {str(e)}"
        )


@app.post("/predict/batch")
async def predict_batch(
    files: List[UploadFile] = File(..., description="Images à analyser en batch")
):
    """
    Effectue une prédiction sur plusieurs images
    
    Args:
        files: Liste de fichiers images
        
    Returns:
        List[PredictionResponse]: Résultats pour chaque image
    """
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Pipeline ML non initialisé - service indisponible"
        )
    
    if len(files) > 10:  # Limite pour éviter la surcharge
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 images par batch"
        )
    
    request_id = str(uuid.uuid4())
    logger.info(f"Prédiction batch - ID: {request_id} - {len(files)} images")
    
    results = []
    
    for i, file in enumerate(files):
        try:
            # Traitement de chaque image
            image = process_uploaded_file(file)
            result = pipeline.predict_image(image)
            
            if 'error' not in result:
                update_stats(result['detections_count'], result['processing_time'])
                
                response = PredictionResponse(
                    success=True,
                    image_shape=result['image_shape'],
                    detections_count=result['detections_count'],
                    results=result['results'],
                    processing_time=result['processing_time'],
                    pipeline_version=result['pipeline_version'],
                    request_id=f"{request_id}_{i}"
                )
            else:
                response = PredictionResponse(
                    success=False,
                    image_shape=[0, 0, 0],
                    detections_count=0,
                    results=[],
                    processing_time=0.0,
                    pipeline_version="1.0.0",
                    request_id=f"{request_id}_{i}"
                )
            
            results.append(response)
            
        except Exception as e:
            logger.error(f"Erreur image {i} dans batch {request_id}: {e}")
            results.append({
                "success": False,
                "error": str(e),
                "request_id": f"{request_id}_{i}"
            })
    
    logger.info(f"Batch terminé - ID: {request_id}")
    return results


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Vérification de l'état de santé de l'API"""
    uptime = time.time() - app_stats["start_time"]
    
    return HealthResponse(
        status="healthy" if pipeline else "degraded",
        pipeline_loaded=pipeline is not None,
        uptime=uptime,
        total_predictions=app_stats["total_predictions"],
        version="1.0.0"
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Métriques Prometheus pour monitoring"""
    uptime = time.time() - app_stats["start_time"]
    avg_processing_time = (
        app_stats["total_processing_time"] / app_stats["total_predictions"]
        if app_stats["total_predictions"] > 0 else 0.0
    )
    
    return MetricsResponse(
        total_predictions=app_stats["total_predictions"],
        total_detections=app_stats["total_detections"],
        average_processing_time=avg_processing_time,
        uptime=uptime,
        pipeline_status="loaded" if pipeline else "not_loaded"
    )


# ==========================================
# TÂCHES ASYNCHRONES
# ==========================================

async def log_prediction_async(request_id: str, detections_count: int, processing_time: float):
    """Log asynchrone des métriques de prédiction"""
    try:
        # Log dans les fichiers
        logger.info(f"METRICS - ID: {request_id}, Detections: {detections_count}, Time: {processing_time:.3f}s")
        
        # Ici on pourrait ajouter d'autres systèmes de monitoring
        # comme Prometheus, Grafana, etc.
        
    except Exception as e:
        logger.warning(f"Erreur log asynchrone: {e}")


# ==========================================
# POINT D'ENTRÉE
# ==========================================

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Lance le serveur FastAPI
    
    Args:
        host: Adresse d'écoute
        port: Port d'écoute  
        reload: Rechargement automatique en développement
    """
    import uvicorn
    
    logger.info(f"🚀 Lancement du serveur API sur {host}:{port}")
    uvicorn.run(
        "src.api.main:app" if not reload else "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server(reload=True)
