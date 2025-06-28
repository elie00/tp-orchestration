"""
Tests unitaires pour l'API FastAPI
"""

import pytest
import tempfile
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from PIL import Image

from fastapi.testclient import TestClient
import sys
sys.path.append("src")
from api.main import app, initialize_pipeline, process_uploaded_file


# Client de test FastAPI
client = TestClient(app)


class TestAPIEndpoints:
    """Tests pour les endpoints de l'API"""
    
    def test_root_endpoint(self):
        """Test de l'endpoint racine"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Road Sign ML API" in response.text
        assert "text/html" in response.headers["content-type"]
    
    def test_health_endpoint(self):
        """Test de l'endpoint health"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "pipeline_loaded" in data
        assert "uptime" in data
        assert "total_predictions" in data
        assert "version" in data
        
        assert data["version"] == "1.0.0"
        assert isinstance(data["uptime"], float)
        assert isinstance(data["total_predictions"], int)
    
    def test_metrics_endpoint(self):
        """Test de l'endpoint metrics"""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_predictions" in data
        assert "total_detections" in data
        assert "average_processing_time" in data
        assert "uptime" in data
        assert "pipeline_status" in data
        
        assert isinstance(data["total_predictions"], int)
        assert isinstance(data["total_detections"], int)
        assert isinstance(data["average_processing_time"], float)
    
    def test_docs_endpoint(self):
        """Test de l'endpoint de documentation"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()


class TestImageProcessing:
    """Tests pour le traitement d'images"""
    
    def create_test_image(self, format="JPEG", size=(100, 100), color="red"):
        """Crée une image de test en mémoire"""
        img = Image.new('RGB', size, color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=format)
        img_bytes.seek(0)
        return img_bytes
    
    def test_process_uploaded_file_valid_image(self):
        """Test du traitement d'un fichier image valide"""
        # Mock d'un fichier uploadé
        mock_file = Mock()
        mock_file.content_type = "image/jpeg"
        mock_file.file = self.create_test_image()
        
        # Test
        result = process_uploaded_file(mock_file)
        
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 3  # H, W, C
        assert result.shape[2] == 3    # BGR
    
    def test_process_uploaded_file_invalid_content_type(self):
        """Test avec un type de contenu invalide"""
        from fastapi import HTTPException
        
        mock_file = Mock()
        mock_file.content_type = "text/plain"
        
        with pytest.raises(HTTPException) as exc_info:
            process_uploaded_file(mock_file)
        
        assert exc_info.value.status_code == 400
        assert "Type de fichier non supporté" in str(exc_info.value.detail)
    
    def test_process_uploaded_file_corrupted_image(self):
        """Test avec une image corrompue"""
        from fastapi import HTTPException
        
        mock_file = Mock()
        mock_file.content_type = "image/jpeg"
        mock_file.file = io.BytesIO(b"corrupted data")
        
        with pytest.raises(HTTPException) as exc_info:
            process_uploaded_file(mock_file)
        
        assert exc_info.value.status_code == 400
        assert "Impossible de traiter l'image" in str(exc_info.value.detail)


class TestPredictionEndpoints:
    """Tests pour les endpoints de prédiction"""
    
    def create_mock_pipeline_result(self):
        """Crée un résultat de pipeline mocké"""
        return {
            'image_shape': [100, 100, 3],
            'detections_count': 2,
            'results': [
                {
                    'bbox': [10, 10, 50, 50],
                    'confidence': 0.85,
                    'class_id': 0,
                    'class_name': 'Stop',
                    'ocr': {
                        'text': 'STOP',
                        'confidence': 0.9,
                        'raw_text': 'STOP',
                        'word_count': 1
                    },
                    'has_text': True
                },
                {
                    'bbox': [60, 60, 90, 90],
                    'confidence': 0.75,
                    'class_id': 1,
                    'class_name': 'Speed limit',
                    'ocr': {
                        'text': '50',
                        'confidence': 0.8,
                        'raw_text': '50',
                        'word_count': 1
                    },
                    'has_text': True
                }
            ],
            'processing_time': 0.5,
            'pipeline_version': '1.0.0'
        }
    
    def create_test_image_file(self):
        """Crée un fichier image de test pour upload"""
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return ("test.jpg", img_bytes, "image/jpeg")
    
    @patch('api.main.pipeline')
    def test_predict_endpoint_success(self, mock_pipeline):
        """Test réussi de l'endpoint predict"""
        # Setup du mock
        mock_pipeline.predict_image.return_value = self.create_mock_pipeline_result()
        
        # Préparation du fichier de test
        files = {"file": self.create_test_image_file()}
        
        # Test
        response = client.post("/predict", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["detections_count"] == 2
        assert len(data["results"]) == 2
        assert "request_id" in data
        assert data["pipeline_version"] == "1.0.0"
        
        # Vérifier la structure des détections
        for result in data["results"]:
            assert "bbox" in result
            assert "confidence" in result
            assert "class_name" in result
            assert "ocr" in result
    
    def test_predict_endpoint_no_pipeline(self):
        """Test avec pipeline non initialisé"""
        with patch('api.main.pipeline', None):
            files = {"file": self.create_test_image_file()}
            response = client.post("/predict", files=files)
            
            assert response.status_code == 503
            assert "Pipeline ML non initialisé" in response.json()["detail"]
    
    @patch('api.main.pipeline')
    def test_predict_endpoint_pipeline_error(self, mock_pipeline):
        """Test avec erreur du pipeline"""
        # Setup du mock pour retourner une erreur
        mock_pipeline.predict_image.return_value = {"error": "Test error"}
        
        files = {"file": self.create_test_image_file()}
        response = client.post("/predict", files=files)
        
        assert response.status_code == 500
        assert "Erreur de prédiction" in response.json()["detail"]
    
    def test_predict_endpoint_invalid_file(self):
        """Test avec fichier invalide"""
        # Fichier texte au lieu d'image
        files = {"file": ("test.txt", io.StringIO("test content"), "text/plain")}
        response = client.post("/predict", files=files)
        
        assert response.status_code == 400
        assert "Type de fichier non supporté" in response.json()["detail"]
    
    @patch('api.main.pipeline')
    def test_predict_batch_endpoint_success(self, mock_pipeline):
        """Test réussi de l'endpoint predict batch"""
        # Setup du mock
        mock_pipeline.predict_image.return_value = self.create_mock_pipeline_result()
        
        # Préparation de plusieurs fichiers
        files = [
            ("files", self.create_test_image_file()),
            ("files", self.create_test_image_file())
        ]
        
        response = client.post("/predict/batch", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2
        
        for result in data:
            assert "success" in result
            assert "request_id" in result
    
    def test_predict_batch_endpoint_too_many_files(self):
        """Test avec trop de fichiers en batch"""
        # Créer plus de 10 fichiers (limite)
        files = [("files", self.create_test_image_file()) for _ in range(15)]
        
        response = client.post("/predict/batch", files=files)
        
        assert response.status_code == 400
        assert "Maximum 10 images par batch" in response.json()["detail"]


class TestPipelineInitialization:
    """Tests pour l'initialisation du pipeline"""
    
    @patch('api.main.RoadSignInferencePipeline')
    def test_initialize_pipeline_success(self, mock_pipeline_class):
        """Test d'initialisation réussie du pipeline"""
        # Setup du mock
        mock_instance = Mock()
        mock_pipeline_class.return_value = mock_instance
        
        # Test
        result = initialize_pipeline()
        
        assert result is True
        mock_pipeline_class.assert_called_once()
    
    @patch('api.main.RoadSignInferencePipeline')
    def test_initialize_pipeline_failure(self, mock_pipeline_class):
        """Test d'échec d'initialisation du pipeline"""
        # Setup du mock pour lever une exception
        mock_pipeline_class.side_effect = Exception("Test error")
        
        # Test
        result = initialize_pipeline()
        
        assert result is False


class TestStatsAndMetrics:
    """Tests pour les statistiques et métriques"""
    
    def test_update_stats(self):
        """Test de mise à jour des statistiques"""
        from api.main import update_stats, app_stats
        
        # Valeurs initiales
        initial_predictions = app_stats["total_predictions"]
        initial_detections = app_stats["total_detections"] 
        initial_time = app_stats["total_processing_time"]
        
        # Mise à jour
        update_stats(5, 1.5)
        
        # Vérifications
        assert app_stats["total_predictions"] == initial_predictions + 1
        assert app_stats["total_detections"] == initial_detections + 5
        assert app_stats["total_processing_time"] == initial_time + 1.5
    
    def test_metrics_calculation(self):
        """Test du calcul des métriques moyennes"""
        from api.main import app_stats
        
        # Reset des stats pour le test
        app_stats["total_predictions"] = 10
        app_stats["total_processing_time"] = 25.0
        
        response = client.get("/metrics")
        data = response.json()
        
        expected_avg = 25.0 / 10  # 2.5
        assert data["average_processing_time"] == expected_avg
    
    def test_metrics_no_predictions(self):
        """Test des métriques sans prédictions"""
        from api.main import app_stats
        
        # Reset des stats
        app_stats["total_predictions"] = 0
        app_stats["total_processing_time"] = 0.0
        
        response = client.get("/metrics")
        data = response.json()
        
        assert data["average_processing_time"] == 0.0


class TestAPIIntegration:
    """Tests d'intégration de l'API"""
    
    @patch('api.main.RoadSignInferencePipeline')
    def test_full_prediction_workflow(self, mock_pipeline_class):
        """Test du workflow complet de prédiction"""
        # Setup du pipeline mock
        mock_pipeline = Mock()
        mock_pipeline.predict_image.return_value = {
            'image_shape': [100, 100, 3],
            'detections_count': 1,
            'results': [{
                'bbox': [10, 10, 50, 50],
                'confidence': 0.9,
                'class_id': 0,
                'class_name': 'Test',
                'ocr': {'text': 'TEST', 'confidence': 0.8, 'raw_text': 'TEST', 'word_count': 1},
                'has_text': True
            }],
            'processing_time': 0.3,
            'pipeline_version': '1.0.0'
        }
        mock_pipeline_class.return_value = mock_pipeline
        
        # Initialisation forcée du pipeline
        from api.main import initialize_pipeline
        initialize_pipeline()
        
        # Test de prédiction
        files = {"file": ("test.jpg", io.BytesIO(b"fake image data"), "image/jpeg")}
        
        with patch('api.main.process_uploaded_file') as mock_process:
            mock_process.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
            
            response = client.post("/predict", files=files)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["detections_count"] == 1
        
        # Vérifier que les stats ont été mises à jour
        health_response = client.get("/health")
        health_data = health_response.json()
        assert health_data["total_predictions"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
