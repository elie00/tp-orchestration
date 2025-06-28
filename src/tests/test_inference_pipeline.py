"""
Tests unitaires pour le pipeline d'inférence
"""

import pytest
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import cv2
import yaml

import sys
sys.path.append("src")
from ml_pipelines.inference_pipeline import RoadSignInferencePipeline


class TestRoadSignInferencePipeline:
    """Tests pour le pipeline d'inférence"""
    
    @pytest.fixture
    def mock_config(self):
        """Configuration mock pour les tests"""
        return {
            'pipeline': {
                'confidence_thresholds': {
                    'detection_min': 0.3,
                    'detection_nms': 0.45,
                    'ocr_min': 0.5
                },
                'roi': {
                    'padding_ratio': 0.1,
                    'min_area': 100,
                    'max_aspect_ratio': 5.0
                },
                'performance': {
                    'enable_cache': True,
                    'max_batch_size': 8
                }
            },
            'yolo': {
                'model': {
                    'architecture': 'yolov8n',
                    'pretrained': True,
                    'num_classes': 43
                }
            },
            'ocr': {
                'tesseract': {
                    'lang': 'eng',
                    'config': '--psm 6 --oem 3'
                },
                'preprocessing': {
                    'denoise': True,
                    'contrast_enhancement': True,
                    'brightness_adjustment': True,
                    'min_height': 32,
                    'threshold_method': 'adaptive'
                },
                'postprocessing': {
                    'remove_special_chars': True,
                    'known_patterns': ['STOP', 'YIELD']
                }
            }
        }
    
    @pytest.fixture
    def temp_config_file(self, mock_config):
        """Fichier de configuration temporaire"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(mock_config, f)
            config_path = f.name
        
        yield config_path
        
        Path(config_path).unlink()
    
    @pytest.fixture
    def pipeline(self, temp_config_file):
        """Instance du pipeline avec config mock"""
        with patch('ml_pipelines.inference_pipeline.mlflow'):
            return RoadSignInferencePipeline(config_path=temp_config_file)
    
    def test_init(self, pipeline):
        """Test l'initialisation du pipeline"""
        assert pipeline.config is not None
        assert pipeline.pipeline_config is not None
        assert pipeline.yolo_config is not None
        assert pipeline.ocr_config is not None
        assert pipeline.cache_enabled is True
        assert pipeline.prediction_cache is not None
    
    def test_load_config_file_not_found(self):
        """Test le chargement d'un fichier de config inexistant"""
        with pytest.raises(FileNotFoundError):
            RoadSignInferencePipeline(config_path="nonexistent.yml")
    
    def test_preprocess_image_from_path(self, pipeline):
        """Test le preprocessing d'une image depuis un chemin"""
        # Créer une image de test
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
            cv2.imwrite(temp_path, test_image)
        
        try:
            result = pipeline.preprocess_image(temp_path)
            assert isinstance(result, np.ndarray)
            assert len(result.shape) == 3
        finally:
            Path(temp_path).unlink()
    
    def test_preprocess_image_from_numpy(self, pipeline):
        """Test le preprocessing d'une image numpy"""
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = pipeline.preprocess_image(test_image)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == test_image.shape
    
    def test_preprocess_image_from_pil(self, pipeline):
        """Test le preprocessing d'une image PIL"""
        pil_image = Image.new('RGB', (100, 100), color='red')
        result = pipeline.preprocess_image(pil_image)
        
        assert isinstance(result, np.ndarray)
        assert len(result.shape) == 3
        assert result.shape[2] == 3  # BGR
    
    def test_preprocess_image_invalid(self, pipeline):
        """Test avec une image invalide"""
        with pytest.raises(ValueError):
            pipeline.preprocess_image("nonexistent_image.jpg")
    
    @patch('ml_pipelines.inference_pipeline.YOLO')
    def test_load_models_with_path(self, mock_yolo_class, pipeline):
        """Test le chargement des modèles avec chemin spécifique"""
        mock_model = Mock()
        mock_yolo_class.return_value = mock_model
        
        # Créer un fichier modèle factice
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as f:
            model_path = f.name
        
        try:
            result = pipeline.load_models(model_path)
            assert result is True
            assert pipeline.yolo_model == mock_model
            mock_yolo_class.assert_called_with(model_path)
        finally:
            Path(model_path).unlink()
    
    @patch('ml_pipelines.inference_pipeline.YOLO')
    def test_load_models_default(self, mock_yolo_class, pipeline):
        """Test le chargement du modèle par défaut"""
        mock_model = Mock()
        mock_yolo_class.return_value = mock_model
        
        result = pipeline.load_models()
        assert result is True
        assert pipeline.yolo_model == mock_model
        mock_yolo_class.assert_called_with("yolov8n.pt")
    
    def test_validate_detection_valid(self, pipeline):
        """Test la validation d'une détection valide"""
        image_shape = (200, 300, 3)  # H, W, C
        x1, y1, x2, y2 = 50, 50, 150, 100
        
        result = pipeline._validate_detection(x1, y1, x2, y2, image_shape)
        assert result is True
    
    def test_validate_detection_invalid_coordinates(self, pipeline):
        """Test avec coordonnées invalides"""
        image_shape = (200, 300, 3)
        
        # Coordonnées en dehors de l'image
        assert pipeline._validate_detection(-10, 50, 150, 100, image_shape) is False
        assert pipeline._validate_detection(50, 50, 350, 100, image_shape) is False
        
        # x1 >= x2 ou y1 >= y2
        assert pipeline._validate_detection(150, 50, 50, 100, image_shape) is False
        assert pipeline._validate_detection(50, 100, 150, 50, image_shape) is False
    
    def test_validate_detection_too_small(self, pipeline):
        """Test avec une détection trop petite"""
        image_shape = (200, 300, 3)
        # Aire de 5x5 = 25 pixels (< min_area de 100)
        x1, y1, x2, y2 = 50, 50, 55, 55
        
        result = pipeline._validate_detection(x1, y1, x2, y2, image_shape)
        assert result is False
    
    def test_validate_detection_wrong_aspect_ratio(self, pipeline):
        """Test avec un ratio d'aspect incorrect"""
        image_shape = (200, 300, 3)
        # Ratio de 6 (> max_aspect_ratio de 5.0)
        x1, y1, x2, y2 = 50, 50, 350, 100  # width=300, height=50, ratio=6
        
        result = pipeline._validate_detection(x1, y1, x2, y2, image_shape)
        assert result is False
    
    def test_extract_roi(self, pipeline):
        """Test l'extraction de ROI"""
        image = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        bbox = [50, 50, 150, 100]
        
        roi = pipeline.extract_roi(image, bbox)
        
        # Avec padding de 10%, la ROI devrait être plus grande que la bbox originale
        assert roi.shape[0] > (100 - 50)  # height
        assert roi.shape[1] > (150 - 50)  # width
    
    def test_extract_roi_no_padding(self, pipeline):
        """Test l'extraction de ROI sans padding"""
        # Modifier temporairement la config
        pipeline.pipeline_config['roi']['padding_ratio'] = 0.0
        
        image = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        bbox = [50, 50, 150, 100]
        
        roi = pipeline.extract_roi(image, bbox)
        
        expected_height = 100 - 50  # 50
        expected_width = 150 - 50   # 100
        
        assert roi.shape[0] == expected_height
        assert roi.shape[1] == expected_width
    
    def test_preprocess_roi_for_ocr(self, pipeline):
        """Test le preprocessing de ROI pour OCR"""
        # ROI couleur
        roi = np.random.randint(0, 255, (50, 100, 3), dtype=np.uint8)
        
        processed = pipeline.preprocess_roi_for_ocr(roi)
        
        # Doit être en niveaux de gris
        assert len(processed.shape) == 2
        
        # Doit être redimensionnée si trop petite
        min_height = pipeline.ocr_config['preprocessing']['min_height']
        if roi.shape[0] < min_height:
            assert processed.shape[0] >= min_height
    
    def test_preprocess_roi_for_ocr_already_gray(self, pipeline):
        """Test avec une ROI déjà en niveaux de gris"""
        roi = np.random.randint(0, 255, (50, 100), dtype=np.uint8)
        
        processed = pipeline.preprocess_roi_for_ocr(roi)
        
        assert len(processed.shape) == 2
        assert processed.shape[0] >= pipeline.ocr_config['preprocessing']['min_height']
    
    @patch('ml_pipelines.inference_pipeline.pytesseract')
    def test_recognize_text_success(self, mock_tesseract, pipeline):
        """Test reconnaissance de texte réussie"""
        # Mock des données OCR
        mock_tesseract.image_to_data.return_value = {
            'text': ['', 'STOP', ''],
            'conf': [0, 95, 0]
        }
        
        roi = np.ones((50, 100), dtype=np.uint8) * 255
        result = pipeline.recognize_text(roi)
        
        assert result['text'] == 'STOP'
        assert result['confidence'] == 0.95
        assert result['word_count'] == 1
        assert 'raw_text' in result
    
    @patch('ml_pipelines.inference_pipeline.pytesseract')
    def test_recognize_text_no_text(self, mock_tesseract, pipeline):
        """Test avec aucun texte détecté"""
        mock_tesseract.image_to_data.return_value = {
            'text': ['', '', ''],
            'conf': [0, 0, 0]
        }
        
        roi = np.ones((50, 100), dtype=np.uint8) * 255
        result = pipeline.recognize_text(roi)
        
        assert result['text'] == ''
        assert result['confidence'] == 0.0
        assert result['word_count'] == 0
    
    @patch('ml_pipelines.inference_pipeline.pytesseract')
    def test_recognize_text_error(self, mock_tesseract, pipeline):
        """Test avec erreur OCR"""
        mock_tesseract.image_to_data.side_effect = Exception("OCR Error")
        
        roi = np.ones((50, 100), dtype=np.uint8) * 255
        result = pipeline.recognize_text(roi)
        
        assert result['text'] == ''
        assert result['confidence'] == 0.0
        assert result['word_count'] == 0
    
    def test_postprocess_text(self, pipeline):
        """Test le post-traitement de texte"""
        # Texte avec caractères spéciaux
        text = "ST0P!"
        result = pipeline._postprocess_text(text)
        
        assert result == "ST0P"  # Caractères spéciaux supprimés et mis en majuscules
    
    def test_postprocess_text_known_pattern(self, pipeline):
        """Test avec un pattern connu"""
        text = "stop sign"
        result = pipeline._postprocess_text(text)
        
        # Devrait reconnaître STOP dans le texte
        assert "STOP" in result.upper()
    
    def test_postprocess_text_empty(self, pipeline):
        """Test avec texte vide"""
        result = pipeline._postprocess_text("")
        assert result == ""
    
    @patch('ml_pipelines.inference_pipeline.mlflow')
    def test_log_prediction_metrics(self, mock_mlflow, pipeline):
        """Test du logging des métriques"""
        result = {
            'detections_count': 2,
            'processing_time': 1.5,
            'results': [
                {'ocr': {'confidence': 0.9}},
                {'ocr': {'confidence': 0.8}}
            ]
        }
        
        pipeline._log_prediction_metrics(result)
        
        # Vérifier que MLflow a été appelé
        mock_mlflow.start_run.assert_called()
        mock_mlflow.log_metric.assert_called()


class TestPredictionWorkflow:
    """Tests pour le workflow complet de prédiction"""
    
    @pytest.fixture
    def pipeline_with_mocks(self):
        """Pipeline avec tous les composants mockés"""
        with patch('ml_pipelines.inference_pipeline.mlflow'), \
             patch('ml_pipelines.inference_pipeline.YOLO') as mock_yolo_class:
            
            # Configuration minimale
            config = {
                'pipeline': {
                    'confidence_thresholds': {'detection_min': 0.3, 'detection_nms': 0.45},
                    'roi': {'padding_ratio': 0.1, 'min_area': 100, 'max_aspect_ratio': 5.0},
                    'performance': {'enable_cache': True}
                },
                'yolo': {'model': {'architecture': 'yolov8n'}},
                'ocr': {
                    'tesseract': {'config': '--psm 6'},
                    'preprocessing': {'min_height': 32, 'threshold_method': 'adaptive'},
                    'postprocessing': {'remove_special_chars': True, 'known_patterns': []}
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(config, f)
                config_path = f.name
            
            # Mock du modèle YOLO
            mock_model = Mock()
            mock_yolo_class.return_value = mock_model
            
            # Mock des résultats YOLO
            mock_result = Mock()
            mock_box = Mock()
            mock_box.xyxy = [torch.tensor([10.0, 10.0, 50.0, 50.0])]
            mock_box.conf = [torch.tensor(0.85)]
            mock_box.cls = [torch.tensor(0)]
            mock_result.boxes = [mock_box]
            mock_model.return_value = [mock_result]
            mock_model.names = {0: 'Stop'}
            
            try:
                pipeline = RoadSignInferencePipeline(config_path=config_path)
                pipeline.yolo_model = mock_model
                yield pipeline
            finally:
                Path(config_path).unlink()
    
    @patch('ml_pipelines.inference_pipeline.pytesseract')
    @patch('ml_pipelines.inference_pipeline.torch')
    def test_predict_image_complete_workflow(self, mock_torch, mock_tesseract, pipeline_with_mocks):
        """Test du workflow complet de prédiction"""
        # Mock pour torch.tensor
        mock_torch.tensor = lambda x: Mock(tolist=lambda: x if isinstance(x, list) else [x])
        
        # Mock OCR
        mock_tesseract.image_to_data.return_value = {
            'text': ['STOP'],
            'conf': [90]
        }
        
        # Image de test
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        # Prédiction
        result = pipeline_with_mocks.predict_image(test_image)
        
        # Vérifications
        assert 'image_shape' in result
        assert 'detections_count' in result
        assert 'results' in result
        assert 'processing_time' in result
        assert 'pipeline_version' in result
        
        assert result['detections_count'] >= 0
        assert result['processing_time'] > 0
        assert isinstance(result['results'], list)
    
    def test_predict_image_error_handling(self, pipeline_with_mocks):
        """Test de la gestion d'erreurs"""
        # Forcer une erreur en passant une image invalide
        result = pipeline_with_mocks.predict_image(None)
        
        assert 'error' in result
        assert result['detections_count'] == 0
        assert result['results'] == []
        assert 'processing_time' in result
    
    @patch('ml_pipelines.inference_pipeline.pytesseract')
    def test_predict_batch(self, mock_tesseract, pipeline_with_mocks):
        """Test de prédiction en batch"""
        mock_tesseract.image_to_data.return_value = {
            'text': ['TEST'],
            'conf': [85]
        }
        
        # Images de test
        images = [
            np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
            np.random.randint(0, 255, (120, 120, 3), dtype=np.uint8)
        ]
        
        results = pipeline_with_mocks.predict_batch(images)
        
        assert len(results) == 2
        for result in results:
            assert 'detections_count' in result
            assert 'processing_time' in result


class TestInferencePipelineIntegration:
    """Tests d'intégration pour le pipeline d'inférence"""
    
    @patch('ml_pipelines.inference_pipeline.mlflow')
    @patch('ml_pipelines.inference_pipeline.pytesseract')
    @patch('ml_pipelines.inference_pipeline.YOLO')
    def test_full_integration_with_real_image(self, mock_yolo_class, mock_tesseract, mock_mlflow):
        """Test d'intégration avec une vraie image"""
        # Création d'une image réaliste avec texte
        image = np.ones((200, 300, 3), dtype=np.uint8) * 255
        cv2.putText(image, "STOP", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
        cv2.rectangle(image, (80, 70), (220, 130), (255, 0, 0), 2)
        
        # Mock YOLO pour détecter le rectangle
        mock_model = Mock()
        mock_yolo_class.return_value = mock_model
        
        # Simulation d'une détection YOLO
        mock_result = Mock()
        mock_box = Mock()
        
        # Mock pour torch.tensor si nécessaire
        with patch('ml_pipelines.inference_pipeline.torch') as mock_torch:
            mock_torch.tensor = lambda x: Mock(tolist=lambda: x if isinstance(x, list) else [x])
            
            mock_box.xyxy = [mock_torch.tensor([80.0, 70.0, 220.0, 130.0])]
            mock_box.conf = [mock_torch.tensor(0.9)]
            mock_box.cls = [mock_torch.tensor(0)]
            mock_result.boxes = [mock_box]
            mock_model.return_value = [mock_result]
            mock_model.names = {0: 'Stop'}
            
            # Mock OCR pour reconnaître STOP
            mock_tesseract.image_to_data.return_value = {
                'text': ['', 'STOP', ''],
                'conf': [0, 95, 0]
            }
            mock_tesseract.get_tesseract_version.return_value = "5.0.0"
            
            # Configuration complète
            config = {
                'pipeline': {
                    'confidence_thresholds': {'detection_min': 0.3, 'detection_nms': 0.45},
                    'roi': {'padding_ratio': 0.1, 'min_area': 100, 'max_aspect_ratio': 5.0},
                    'performance': {'enable_cache': True}
                },
                'yolo': {'model': {'architecture': 'yolov8n'}},
                'ocr': {
                    'tesseract': {'config': '--psm 6'},
                    'preprocessing': {'min_height': 32, 'threshold_method': 'adaptive'},
                    'postprocessing': {'remove_special_chars': True, 'known_patterns': ['STOP']}
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(config, f)
                config_path = f.name
            
            try:
                # Test du pipeline complet
                pipeline = RoadSignInferencePipeline(config_path=config_path)
                result = pipeline.predict_image(image)
                
                # Vérifications
                assert result['detections_count'] >= 0
                assert 'results' in result
                assert 'processing_time' in result
                assert result['processing_time'] > 0
                
                # Si détection trouvée, vérifier la structure
                if result['detections_count'] > 0:
                    detection = result['results'][0]
                    assert 'bbox' in detection
                    assert 'confidence' in detection
                    assert 'ocr' in detection
                    assert 'class_name' in detection
                
            finally:
                Path(config_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
