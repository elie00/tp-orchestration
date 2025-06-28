"""
Pipeline d'inférence pour la détection et reconnaissance de panneaux routiers
Ce module combine YOLO (détection) et OCR (reconnaissance texte) pour un pipeline complet.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import yaml

import mlflow
import numpy as np
import cv2
from PIL import Image
import torch
from ultralytics import YOLO
import pytesseract

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RoadSignInferencePipeline:
    """Pipeline d'inférence complet pour la détection et reconnaissance de panneaux routiers"""
    
    def __init__(self, 
                 yolo_model_path: Optional[str] = None,
                 config_path: str = "conf/base/model_config.yml"):
        """
        Initialise le pipeline d'inférence
        
        Args:
            yolo_model_path: Chemin vers le modèle YOLO entraîné
            config_path: Chemin vers le fichier de configuration
        """
        self.config = self._load_config(config_path)
        self.pipeline_config = self.config['pipeline']
        self.yolo_config = self.config['yolo']
        self.ocr_config = self.config['ocr']
        
        # Initialisation des modèles
        self.yolo_model = None
        self.load_models(yolo_model_path)
        
        # Configuration MLflow pour tracking des prédictions
        mlflow.set_experiment("RoadSign_E2E_Pipeline")
        
        # Cache pour optimiser les performances
        self.cache_enabled = self.pipeline_config['performance'].get('enable_cache', True)
        self.prediction_cache = {} if self.cache_enabled else None
        
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration depuis le fichier YAML"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Fichier de configuration non trouvé: {config_path}")
            raise
    
    def load_models(self, yolo_model_path: Optional[str] = None) -> bool:
        """
        Charge les modèles YOLO et configure OCR
        
        Args:
            yolo_model_path: Chemin vers le modèle YOLO
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            # Chargement du modèle YOLO
            if yolo_model_path and Path(yolo_model_path).exists():
                self.yolo_model = YOLO(yolo_model_path)
                logger.info(f"Modèle YOLO chargé: {yolo_model_path}")
            else:
                # Modèle par défaut si pas de modèle spécifique
                architecture = self.yolo_config['model']['architecture']
                self.yolo_model = YOLO(f"{architecture}.pt")
                logger.info(f"Modèle YOLO par défaut chargé: {architecture}")
            
            # Test OCR
            try:
                pytesseract.get_tesseract_version()
                logger.info("OCR Tesseract configuré")
            except Exception as e:
                logger.warning(f"Problème avec Tesseract: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles: {e}")
            return False
    
    def preprocess_image(self, image: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
        """
        Préprocesse une image pour l'inférence
        
        Args:
            image: Image (chemin, array numpy ou PIL)
            
        Returns:
            np.ndarray: Image préprocessée
        """
        # Conversion en array numpy
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                raise ValueError(f"Impossible de charger l'image: {image}")
        elif isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            img = image.copy()
        
        # Validation de l'image
        if img is None or img.size == 0:
            raise ValueError("Image invalide ou vide")
        
        return img
    
    def detect_road_signs(self, image: np.ndarray) -> List[Dict]:
        """
        Détecte les panneaux routiers dans l'image
        
        Args:
            image: Image preprocessée
            
        Returns:
            List[Dict]: Liste des détections avec bboxes et confiances
        """
        if self.yolo_model is None:
            raise ValueError("Modèle YOLO non chargé")
        
        # Configuration des seuils
        conf_threshold = self.pipeline_config['confidence_thresholds']['detection_min']
        nms_threshold = self.pipeline_config['confidence_thresholds']['detection_nms']
        
        # Inférence YOLO
        results = self.yolo_model(
            image, 
            conf=conf_threshold,
            iou=nms_threshold,
            verbose=False
        )
        
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Extraction des informations de la bbox
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    
                    # Validation de la détection
                    if self._validate_detection(x1, y1, x2, y2, image.shape):
                        detections.append({
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': confidence,
                            'class_id': class_id,
                            'class_name': self.yolo_model.names.get(class_id, f"class_{class_id}")
                        })
        
        logger.info(f"Détecté {len(detections)} panneaux")
        return detections
    
    def _validate_detection(self, x1: float, y1: float, x2: float, y2: float, 
                          image_shape: Tuple[int, int, int]) -> bool:
        """Valide une détection selon les critères configurés"""
        h, w = image_shape[:2]
        
        # Vérification des coordonnées
        if x1 < 0 or y1 < 0 or x2 > w or y2 > h or x1 >= x2 or y1 >= y2:
            return False
        
        # Vérification de l'aire minimale
        area = (x2 - x1) * (y2 - y1)
        min_area = self.pipeline_config['roi']['min_area']
        if area < min_area:
            return False
        
        # Vérification du ratio d'aspect
        width = x2 - x1
        height = y2 - y1
        aspect_ratio = width / height if height > 0 else float('inf')
        max_aspect_ratio = self.pipeline_config['roi']['max_aspect_ratio']
        if aspect_ratio > max_aspect_ratio:
            return False
        
        return True
    
    def extract_roi(self, image: np.ndarray, bbox: List[int]) -> np.ndarray:
        """
        Extrait la région d'intérêt (ROI) depuis la bbox
        
        Args:
            image: Image source
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            np.ndarray: ROI extraite
        """
        x1, y1, x2, y2 = bbox
        
        # Ajout de padding si configuré
        padding_ratio = self.pipeline_config['roi']['padding_ratio']
        if padding_ratio > 0:
            width = x2 - x1
            height = y2 - y1
            pad_w = int(width * padding_ratio)
            pad_h = int(height * padding_ratio)
            
            x1 = max(0, x1 - pad_w)
            y1 = max(0, y1 - pad_h)
            x2 = min(image.shape[1], x2 + pad_w)
            y2 = min(image.shape[0], y2 + pad_h)
        
        roi = image[y1:y2, x1:x2]
        return roi
    
    def preprocess_roi_for_ocr(self, roi: np.ndarray) -> np.ndarray:
        """
        Préprocesse la ROI pour améliorer l'OCR
        
        Args:
            roi: Région d'intérêt
            
        Returns:
            np.ndarray: ROI préprocessée pour OCR
        """
        preprocessed = roi.copy()
        
        # Configuration preprocessing
        preprocess_config = self.ocr_config['preprocessing']
        
        # Conversion en niveaux de gris
        if len(preprocessed.shape) == 3:
            preprocessed = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
        
        # Débruitage
        if preprocess_config.get('denoise', False):
            preprocessed = cv2.fastNlMeansDenoising(preprocessed)
        
        # Amélioration du contraste
        if preprocess_config.get('contrast_enhancement', False):
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            preprocessed = clahe.apply(preprocessed)
        
        # Ajustement de la luminosité
        if preprocess_config.get('brightness_adjustment', False):
            # Ajustement automatique basé sur l'histogramme
            mean_brightness = np.mean(preprocessed)
            if mean_brightness < 100:  # Image sombre
                preprocessed = cv2.convertScaleAbs(preprocessed, alpha=1.2, beta=30)
        
        # Redimensionnement pour optimiser l'OCR
        min_height = preprocess_config.get('min_height', 32)
        current_height = preprocessed.shape[0]
        
        if current_height < min_height:
            scale_factor = min_height / current_height
            new_width = int(preprocessed.shape[1] * scale_factor)
            preprocessed = cv2.resize(preprocessed, (new_width, min_height), 
                                    interpolation=cv2.INTER_CUBIC)
        
        # Binarisation
        threshold_method = preprocess_config.get('threshold_method', 'adaptive')
        if threshold_method == 'adaptive':
            preprocessed = cv2.adaptiveThreshold(
                preprocessed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
        elif threshold_method == 'otsu':
            _, preprocessed = cv2.threshold(
                preprocessed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        
        return preprocessed
    
    def recognize_text(self, roi: np.ndarray) -> Dict[str, Union[str, float]]:
        """
        Reconnaît le texte dans la ROI
        
        Args:
            roi: Région d'intérêt préprocessée
            
        Returns:
            Dict: Résultat OCR avec texte et confiance
        """
        try:
            # Configuration Tesseract
            tesseract_config = self.ocr_config['tesseract']
            config = tesseract_config['config']
            
            # OCR avec données détaillées
            data = pytesseract.image_to_data(
                roi, 
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extraction du texte et calcul de confiance
            text_parts = []
            confidences = []
            
            for i, word in enumerate(data['text']):
                if word.strip():  # Ignore les mots vides
                    conf = int(data['conf'][i])
                    if conf > 0:  # Ignore les mots avec confiance nulle
                        text_parts.append(word.strip())
                        confidences.append(conf)
            
            # Assemblage du résultat
            text = ' '.join(text_parts) if text_parts else ""
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0
            
            # Post-processing
            processed_text = self._postprocess_text(text)
            
            return {
                'text': processed_text,
                'confidence': avg_confidence,
                'raw_text': text,
                'word_count': len(text_parts)
            }
            
        except Exception as e:
            logger.warning(f"Erreur OCR: {e}")
            return {
                'text': "",
                'confidence': 0.0,
                'raw_text': "",
                'word_count': 0
            }
    
    def _postprocess_text(self, text: str) -> str:
        """Post-traite le texte OCR"""
        if not text:
            return ""
        
        # Configuration post-processing
        postprocess_config = self.ocr_config['postprocessing']
        
        processed = text
        
        # Suppression des caractères spéciaux si configuré
        if postprocess_config.get('remove_special_chars', False):
            import re
            processed = re.sub(r'[^\w\s-/]', '', processed)
        
        # Nettoyage des espaces
        processed = ' '.join(processed.split())
        
        # Mise en majuscules pour panneaux (optionnel)
        processed = processed.upper()
        
        # Vérification contre les patterns connus
        known_patterns = postprocess_config.get('known_patterns', [])
        for pattern in known_patterns:
            if isinstance(pattern, str):
                if pattern.upper() in processed.upper():
                    return pattern.upper()
        
        return processed
    
    def predict_image(self, image: Union[str, np.ndarray, Image.Image]) -> Dict:
        """
        Pipeline complet de prédiction sur une image
        
        Args:
            image: Image à analyser
            
        Returns:
            Dict: Résultats complets avec détections et textes
        """
        start_time = time.time()
        
        try:
            # Préprocessing
            img = self.preprocess_image(image)
            
            # Détection des panneaux
            detections = self.detect_road_signs(img)
            
            # OCR sur chaque détection
            results = []
            for detection in detections:
                # Extraction ROI
                roi = self.extract_roi(img, detection['bbox'])
                
                # Preprocessing OCR
                roi_processed = self.preprocess_roi_for_ocr(roi)
                
                # Reconnaissance texte
                ocr_result = self.recognize_text(roi_processed)
                
                # Combinaison des résultats
                combined_result = {
                    **detection,
                    'ocr': ocr_result,
                    'has_text': len(ocr_result['text']) > 0
                }
                
                results.append(combined_result)
            
            # Calcul du temps total
            total_time = time.time() - start_time
            
            # Résultat final
            final_result = {
                'image_shape': img.shape,
                'detections_count': len(detections),
                'results': results,
                'processing_time': total_time,
                'pipeline_version': "1.0.0"
            }
            
            # Log MLflow pour monitoring
            self._log_prediction_metrics(final_result)
            
            logger.info(f"Prédiction terminée en {total_time:.3f}s - {len(detections)} détections")
            return final_result
            
        except Exception as e:
            logger.error(f"Erreur lors de la prédiction: {e}")
            return {
                'error': str(e),
                'detections_count': 0,
                'results': [],
                'processing_time': time.time() - start_time
            }
    
    def _log_prediction_metrics(self, result: Dict):
        """Log les métriques de prédiction dans MLflow"""
        try:
            with mlflow.start_run(run_name="inference_prediction"):
                mlflow.log_metric("detections_count", result['detections_count'])
                mlflow.log_metric("processing_time", result['processing_time'])
                
                # Métriques OCR moyennes
                if result['results']:
                    avg_ocr_confidence = np.mean([
                        r['ocr']['confidence'] for r in result['results'] 
                        if r['ocr']['confidence'] > 0
                    ])
                    if not np.isnan(avg_ocr_confidence):
                        mlflow.log_metric("avg_ocr_confidence", avg_ocr_confidence)
                
                # Performance check
                target_time = 2.0  # 2 secondes cible
                mlflow.log_metric("meets_performance_target", 
                                int(result['processing_time'] <= target_time))
                
        except Exception as e:
            logger.warning(f"Impossible de logger les métriques: {e}")
    
    def predict_batch(self, images: List[Union[str, np.ndarray, Image.Image]]) -> List[Dict]:
        """
        Prédiction en batch pour plusieurs images
        
        Args:
            images: Liste d'images à analyser
            
        Returns:
            List[Dict]: Résultats pour chaque image
        """
        logger.info(f"Traitement batch de {len(images)} images")
        
        results = []
        for i, image in enumerate(images):
            logger.info(f"Traitement image {i+1}/{len(images)}")
            result = self.predict_image(image)
            results.append(result)
        
        return results


def main():
    """Point d'entrée principal du pipeline d'inférence"""
    try:
        logger.info("🚀 === TEST DU PIPELINE D'INFÉRENCE ===")
        
        # Initialisation du pipeline
        pipeline = RoadSignInferencePipeline()
        
        # Test avec une image d'exemple (simulée)
        logger.info("Création d'une image de test...")
        test_image = np.ones((400, 600, 3), dtype=np.uint8) * 255
        cv2.putText(test_image, "STOP", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 5)
        cv2.rectangle(test_image, (150, 150), (450, 250), (255, 0, 0), 3)
        
        # Prédiction
        logger.info("Exécution de la prédiction...")
        result = pipeline.predict_image(test_image)
        
        # Affichage des résultats
        print("\n" + "="*60)
        print("✅ PIPELINE D'INFÉRENCE TESTÉ AVEC SUCCÈS!")
        print("="*60)
        print(f"📊 Détections trouvées: {result['detections_count']}")
        print(f"⏱️  Temps de traitement: {result['processing_time']:.3f}s")
        
        if result['results']:
            for i, detection in enumerate(result['results']):
                print(f"\n🔍 Détection {i+1}:")
                print(f"   Classe: {detection.get('class_name', 'Inconnue')}")
                print(f"   Confiance: {detection.get('confidence', 0.0):.3f}")
                print(f"   Texte OCR: '{detection['ocr']['text']}'")
                print(f"   Confiance OCR: {detection['ocr']['confidence']:.3f}")
        
        print("="*60)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur dans le pipeline d'inférence: {e}")
        raise


if __name__ == "__main__":
    main()
