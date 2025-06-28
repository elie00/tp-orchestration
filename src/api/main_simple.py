"""
API FastAPI simplifiée pour le service de détection et reconnaissance de panneaux routiers
Version de démarrage sans dépendances ML complexes
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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
from PIL import Image

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application FastAPI
app = FastAPI(
    title="🚦 Road Sign ML API (Version Simple)",
    description="API pour la détection et reconnaissance de panneaux routiers - Version de démarrage",
    version="1.0.0-simple",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        
        return numpy_image
        
    except Exception as e:
        logger.error(f"Erreur traitement fichier: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de traiter l'image: {str(e)}"
        )

def mock_prediction(image: np.ndarray) -> Dict:
    """
    Pipeline de prédiction fictif pour tester l'API
    
    Args:
        image: Image sous forme de tableau numpy
        
    Returns:
        Dict: Résultats de prédiction fictifs
    """
    start_time = time.time()
    
    # Simulation du traitement
    time.sleep(0.1)  # Simulation d'un temps de traitement
    
    # Résultats fictifs
    mock_results = [
        {
            "bbox": [100, 100, 200, 200],
            "confidence": 0.85,
            "class_id": 1,
            "class_name": "Speed Limit",
            "ocr": {
                "text": "50",
                "confidence": 0.92
            },
            "has_text": True
        },
        {
            "bbox": [300, 150, 400, 250],
            "confidence": 0.75,
            "class_id": 2,
            "class_name": "Stop Sign",
            "ocr": {
                "text": "STOP",
                "confidence": 0.98
            },
            "has_text": True
        }
    ]
    
    processing_time = time.time() - start_time
    
    return {
        "success": True,
        "image_shape": list(image.shape),
        "detections_count": len(mock_results),
        "results": mock_results,
        "processing_time": processing_time,
        "pipeline_version": "1.0.0-mock"
    }

# ==========================================
# ÉVÉNEMENTS DE CYCLE DE VIE
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage de l'application"""
    logger.info("🚀 Démarrage de l'API Road Sign ML (Version Simple)")
    
    # Création des répertoires nécessaires
    Path("logs").mkdir(exist_ok=True)
    Path("temp").mkdir(exist_ok=True)
    
    logger.info("✅ API Road Sign ML démarrée avec succès (Mode Simple)")

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
        <title>🚦 Road Sign ML API (Simple)</title>
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
            .warning { background-color: #fff3cd; color: #856404; }
            .stats { display: flex; justify-content: space-around; text-align: center; }
            .stat-item { padding: 15px; }
            .stat-number { font-size: 24px; font-weight: bold; color: #3498db; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚦 Road Sign ML API</h1>
            <p style="text-align: center; color: #7f8c8d;">
                Version de démarrage - Test de l'infrastructure API
            </p>
            
            <div class="section warning">
                <h3>⚠️ Mode de démonstration</h3>
                <p>Cette version utilise des résultats de prédiction fictifs pour tester l'infrastructure de l'API. 
                Les vrais modèles ML seront ajoutés après validation de la base.</p>
            </div>
            
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
                <h2>🖼️ Test de prédiction (Mode démo)</h2>
                <div class="upload-area">
                    <p>📁 Glissez-déposez une image ici ou cliquez pour sélectionner</p>
                    <input type="file" id="imageInput" accept="image/*" />
                    <br>
                    <button onclick="predictImage()">🔍 Analyser l'image (Démo)</button>
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
                    • <code>POST /predict</code> - Prédiction sur image (Mode démo)<br>
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
                resultDiv.innerHTML = '⏳ Analyse en cours (mode démo)...';
                
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
                        let html = `<h3>✅ Test d'analyse réussi! (Résultats fictifs)</h3>
                            <p><strong>Détections trouvées:</strong> ${data.detections_count}</p>
                            <p><strong>Temps de traitement:</strong> ${data.processing_time.toFixed(3)}s</p>
                            <p><strong>Version pipeline:</strong> ${data.pipeline_version}</p>`;
                        
                        if (data.results && data.results.length > 0) {
                            html += '<h4>📋 Détections simulées:</h4>';
                            data.results.forEach((result, index) => {
                                html += `
                                    <div style="margin: 10px 0; padding: 10px; background: #e8f4f8; border-radius: 5px;">
                                        <strong>Détection ${index + 1} (fictive):</strong><br>
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
    Effectue une prédiction fictive sur une image uploadée
    
    Args:
        file: Fichier image (JPEG, PNG, etc.)
        
    Returns:
        PredictionResponse: Résultats de la prédiction
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"Nouvelle prédiction (mode démo) - ID: {request_id}")
        
        # Traitement du fichier uploadé
        image = process_uploaded_file(file)
        
        # Prédiction fictive
        result = mock_prediction(image)
        
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
        
        logger.info(f"Prédiction réussie (mode démo) - ID: {request_id} - {detections_count} détections")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur prédiction - ID: {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne: {str(e)}"
        )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Vérification de l'état de santé de l'API"""
    uptime = time.time() - app_stats["start_time"]
    
    return HealthResponse(
        status="healthy",
        pipeline_loaded=True,  # Toujours vrai en mode simple
        uptime=uptime,
        total_predictions=app_stats["total_predictions"],
        version="1.0.0-simple"
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
        pipeline_status="mock_loaded"
    )

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
    
    logger.info(f"🚀 Lancement du serveur API (Mode Simple) sur {host}:{port}")
    uvicorn.run(
        "main_simple:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    run_server(reload=True)
