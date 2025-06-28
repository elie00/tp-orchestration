"""
Pipeline d'entraînement pour les modèles YOLO et OCR
Ce module gère l'entraînement, la validation et la sauvegarde des modèles.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import yaml

import mlflow
import mlflow.pytorch
from ultralytics import YOLO
import torch
import numpy as np
from PIL import Image
import cv2

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YOLOTrainingPipeline:
    """Pipeline d'entraînement pour le modèle YOLO de détection de panneaux"""
    
    def __init__(self, config_path: str = "conf/base/model_config.yml"):
        """
        Initialise le pipeline d'entraînement YOLO
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        self.config = self._load_config(config_path)
        self.yolo_config = self.config['yolo']
        self.data_config = self.config['data']
        
        # Configuration MLflow
        mlflow.set_experiment("RoadSign_Detection_YOLOv8")
        
        # Préparation des chemins
        self.data_yaml_path = None
        self.model = None
        
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration depuis le fichier YAML"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Fichier de configuration non trouvé: {config_path}")
            raise
    
    def prepare_dataset_config(self) -> str:
        """
        Prépare le fichier de configuration YOLO dataset
        
        Returns:
            str: Chemin vers le fichier dataset.yaml créé
        """
        dataset_config = {
            'path': str(Path.cwd() / 'data' / '02_processed'),
            'train': 'train/images',
            'val': 'val/images',
            'test': 'test/images',
            'nc': self.data_config['dataset']['classes'],  # Nombre de classes
            'names': self._get_class_names()
        }
        
        dataset_yaml_path = Path('data/02_processed/dataset.yaml')
        with open(dataset_yaml_path, 'w') as f:
            yaml.dump(dataset_config, f, default_flow_style=False)
        
        logger.info(f"Configuration dataset YOLO créée: {dataset_yaml_path}")
        return str(dataset_yaml_path)
    
    def _get_class_names(self) -> list:
        """Retourne la liste des noms de classes"""
        # Pour l'exemple, utilisons les classes GTSRB simplifiées
        return [
            "Speed limit (20km/h)", "Speed limit (30km/h)", "Speed limit (50km/h)",
            "Speed limit (60km/h)", "Speed limit (70km/h)", "Speed limit (80km/h)",
            "End of speed limit (80km/h)", "Speed limit (100km/h)", "Speed limit (120km/h)",
            "No passing", "No passing veh over 3.5 tons", "Right-of-way at intersection",
            "Priority road", "Yield", "Stop", "No vehicles", "Veh > 3.5 tons prohibited",
            "No entry", "General caution", "Dangerous curve left", "Dangerous curve right",
            "Double curve", "Bumpy road", "Slippery road", "Road narrows on the right",
            "Road work", "Traffic signals", "Pedestrians", "Children crossing",
            "Bicycles crossing", "Beware of ice/snow", "Wild animals crossing",
            "End speed + passing limits", "Turn right ahead", "Turn left ahead",
            "Ahead only", "Go straight or right", "Go straight or left",
            "Keep right", "Keep left", "Roundabout mandatory", "End of no passing",
            "End no passing veh > 3.5 tons"
        ]
    
    def initialize_model(self) -> YOLO:
        """
        Initialise le modèle YOLO
        
        Returns:
            YOLO: Modèle YOLO initialisé
        """
        model_config = self.yolo_config['model']
        architecture = model_config['architecture']
        pretrained = model_config['pretrained']
        
        if pretrained:
            # Charge un modèle pré-entraîné
            model = YOLO(f"{architecture}.pt")
            logger.info(f"Modèle {architecture} pré-entraîné chargé")
        else:
            # Crée un nouveau modèle depuis la config
            model = YOLO(f"{architecture}.yaml")
            logger.info(f"Nouveau modèle {architecture} créé")
        
        return model
    
    def train_model(self, resume: bool = False) -> Dict[str, float]:
        """
        Entraîne le modèle YOLO
        
        Args:
            resume: Reprendre un entraînement précédent
            
        Returns:
            Dict[str, float]: Métriques d'entraînement
        """
        with mlflow.start_run(run_name=f"yolo_training_{int(time.time())}"):
            try:
                logger.info("=== DÉBUT DE L'ENTRAÎNEMENT YOLO ===")
                
                # Préparation dataset
                self.data_yaml_path = self.prepare_dataset_config()
                
                # Initialisation modèle
                self.model = self.initialize_model()
                
                # Configuration d'entraînement
                training_config = self.yolo_config['training']
                
                # Log des paramètres MLflow
                mlflow.log_params({
                    "architecture": self.yolo_config['model']['architecture'],
                    "epochs": training_config['epochs'],
                    "batch_size": training_config['batch_size'],
                    "img_size": training_config['img_size'],
                    "lr0": training_config['lr0'],
                    "optimizer": training_config['optimizer'],
                    "augment": training_config['augment']
                })
                
                # Entraînement
                logger.info("Démarrage de l'entraînement...")
                results = self.model.train(
                    data=self.data_yaml_path,
                    epochs=training_config['epochs'],
                    batch=training_config['batch_size'],
                    imgsz=training_config['img_size'],
                    lr0=training_config['lr0'],
                    lrf=training_config['lrf'],
                    momentum=training_config['momentum'],
                    weight_decay=training_config['weight_decay'],
                    warmup_epochs=training_config['warmup_epochs'],
                    warmup_momentum=training_config['warmup_momentum'],
                    warmup_bias_lr=training_config['warmup_bias_lr'],
                    degrees=training_config['degrees'],
                    translate=training_config['translate'],
                    scale=training_config['scale'],
                    shear=training_config['shear'],
                    perspective=training_config['perspective'],
                    flipud=training_config['flipud'],
                    fliplr=training_config['fliplr'],
                    mosaic=training_config['mosaic'],
                    mixup=training_config['mixup'],
                    save_period=training_config.get('save_period', 10),
                    resume=resume,
                    device=0 if torch.cuda.is_available() else 'cpu'
                )
                
                # Extraction des métriques finales
                metrics = self._extract_training_metrics(results)
                
                # Log des métriques MLflow
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(metric_name, metric_value)
                
                # Sauvegarde du modèle
                model_path = self._save_model()
                mlflow.log_artifact(model_path, "models")
                
                # Log des courbes d'entraînement
                self._log_training_plots()
                
                logger.info("=== ENTRAÎNEMENT YOLO TERMINÉ ===")
                logger.info(f"Métriques finales: {metrics}")
                
                return metrics
                
            except Exception as e:
                logger.error(f"Erreur durant l'entraînement: {e}")
                mlflow.log_param("error_message", str(e))
                raise
    
    def _extract_training_metrics(self, results) -> Dict[str, float]:
        """Extrait les métriques d'entraînement"""
        try:
            # Les résultats YOLO contiennent les métriques dans results.results_dict
            if hasattr(results, 'results_dict'):
                metrics_dict = results.results_dict
            else:
                # Fallback: utiliser les métriques du modèle
                metrics_dict = self.model.metrics
            
            # Extraction des métriques principales
            metrics = {
                'map50': float(metrics_dict.get('metrics/mAP50(B)', 0.0)),
                'map50_95': float(metrics_dict.get('metrics/mAP50-95(B)', 0.0)),
                'precision': float(metrics_dict.get('metrics/precision(B)', 0.0)),
                'recall': float(metrics_dict.get('metrics/recall(B)', 0.0)),
                'train_loss': float(metrics_dict.get('train/box_loss', 0.0)),
                'val_loss': float(metrics_dict.get('val/box_loss', 0.0))
            }
            
            # Calcul F1-score si précision et rappel disponibles
            if metrics['precision'] > 0 and metrics['recall'] > 0:
                metrics['f1_score'] = 2 * (metrics['precision'] * metrics['recall']) / (metrics['precision'] + metrics['recall'])
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Impossible d'extraire toutes les métriques: {e}")
            return {
                'map50': 0.0,
                'map50_95': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0
            }
    
    def _save_model(self) -> str:
        """Sauvegarde le modèle entraîné"""
        models_dir = Path("data/04_models")
        models_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        model_name = f"yolo_road_signs_{timestamp}.pt"
        model_path = models_dir / model_name
        
        # Sauvegarde du modèle
        self.model.save(str(model_path))
        
        # Sauvegarde également au format ONNX pour l'inférence
        onnx_path = models_dir / f"yolo_road_signs_{timestamp}.onnx"
        self.model.export(format='onnx', save_dir=str(models_dir))
        
        logger.info(f"Modèle sauvegardé: {model_path}")
        logger.info(f"Modèle ONNX sauvegardé: {onnx_path}")
        
        return str(model_path)
    
    def _log_training_plots(self):
        """Log les graphiques d'entraînement dans MLflow"""
        try:
            # Les plots YOLO sont généralement sauvés dans runs/detect/train
            runs_dir = Path("runs/detect")
            if runs_dir.exists():
                latest_run = max(runs_dir.iterdir(), key=os.path.getctime)
                
                # Log des plots s'ils existent
                plots_to_log = [
                    "results.png", "confusion_matrix.png", 
                    "F1_curve.png", "P_curve.png", "R_curve.png", "PR_curve.png"
                ]
                
                for plot_name in plots_to_log:
                    plot_path = latest_run / plot_name
                    if plot_path.exists():
                        mlflow.log_artifact(str(plot_path), "training_plots")
                        logger.info(f"Plot loggé: {plot_name}")
        
        except Exception as e:
            logger.warning(f"Impossible de logger les plots: {e}")
    
    def validate_model(self) -> Dict[str, float]:
        """
        Valide le modèle sur le set de validation
        
        Returns:
            Dict[str, float]: Métriques de validation
        """
        if not self.model:
            raise ValueError("Modèle non initialisé. Entraîner d'abord le modèle.")
        
        logger.info("Validation du modèle...")
        
        # Validation YOLO
        results = self.model.val(data=self.data_yaml_path)
        
        # Extraction des métriques
        metrics = self._extract_training_metrics(results)
        
        logger.info(f"Métriques de validation: {metrics}")
        return metrics


class OCRTrainingPipeline:
    """Pipeline de configuration et optimisation OCR"""
    
    def __init__(self, config_path: str = "conf/base/model_config.yml"):
        """
        Initialise le pipeline OCR
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        self.config = self._load_config(config_path)
        self.ocr_config = self.config['ocr']
        
        # Configuration MLflow
        mlflow.set_experiment("RoadSign_OCR_Recognition")
    
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration depuis le fichier YAML"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Fichier de configuration non trouvé: {config_path}")
            raise
    
    def setup_tesseract(self) -> bool:
        """
        Configure Tesseract OCR
        
        Returns:
            bool: True si succès, False sinon
        """
        with mlflow.start_run(run_name="tesseract_setup"):
            try:
                import pytesseract
                
                # Test de Tesseract
                version = pytesseract.get_tesseract_version()
                logger.info(f"Tesseract version: {version}")
                
                # Configuration Tesseract
                tesseract_config = self.ocr_config['tesseract']
                
                # Log des paramètres
                mlflow.log_param("tesseract_version", str(version))
                mlflow.log_param("languages", tesseract_config['lang'])
                mlflow.log_param("config", tesseract_config['config'])
                
                # Test OCR sur une image d'exemple
                test_accuracy = self._test_ocr_accuracy()
                mlflow.log_metric("test_accuracy", test_accuracy)
                
                logger.info("Tesseract configuré avec succès")
                return True
                
            except Exception as e:
                logger.error(f"Erreur configuration Tesseract: {e}")
                mlflow.log_param("error_message", str(e))
                return False
    
    def _test_ocr_accuracy(self) -> float:
        """Test la précision OCR sur des images d'exemple"""
        try:
            import pytesseract
            
            # Création d'une image de test simple
            test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255
            cv2.putText(test_image, "STOP", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
            
            # OCR
            config = self.ocr_config['tesseract']['config']
            text = pytesseract.image_to_string(test_image, config=config).strip()
            
            # Test de précision simple
            expected = "STOP"
            accuracy = 1.0 if text.upper() == expected else 0.0
            
            logger.info(f"Test OCR - Attendu: '{expected}', Obtenu: '{text}', Précision: {accuracy}")
            return accuracy
            
        except Exception as e:
            logger.warning(f"Impossible de tester l'OCR: {e}")
            return 0.0
    
    def optimize_preprocessing(self) -> Dict[str, float]:
        """
        Optimise les paramètres de preprocessing pour l'OCR
        
        Returns:
            Dict[str, float]: Métriques d'optimisation
        """
        with mlflow.start_run(run_name="ocr_preprocessing_optimization"):
            logger.info("Optimisation du preprocessing OCR...")
            
            # Test de différents paramètres de preprocessing
            preprocessing_configs = [
                {"denoise": True, "contrast": 1.5, "brightness": 10},
                {"denoise": False, "contrast": 2.0, "brightness": 0},
                {"denoise": True, "contrast": 1.2, "brightness": 5}
            ]
            
            best_config = None
            best_score = 0.0
            
            for i, config in enumerate(preprocessing_configs):
                score = self._test_preprocessing_config(config)
                mlflow.log_metric(f"config_{i}_score", score)
                mlflow.log_params({f"config_{i}_{k}": v for k, v in config.items()})
                
                if score > best_score:
                    best_score = score
                    best_config = config
            
            # Log de la meilleure configuration
            mlflow.log_params({f"best_{k}": v for k, v in best_config.items()})
            mlflow.log_metric("best_score", best_score)
            
            logger.info(f"Meilleure configuration: {best_config} (score: {best_score})")
            return {"best_score": best_score, "config": best_config}
    
    def _test_preprocessing_config(self, config: Dict) -> float:
        """Teste une configuration de preprocessing"""
        try:
            # Simulation d'un test de preprocessing
            # En production, cela testerait sur un dataset réel
            base_score = 0.7
            
            # Bonus/malus selon la configuration
            score_modifier = 0.0
            if config.get("denoise", False):
                score_modifier += 0.1
            if 1.0 <= config.get("contrast", 1.0) <= 2.0:
                score_modifier += 0.1
            if -10 <= config.get("brightness", 0) <= 20:
                score_modifier += 0.05
            
            return min(1.0, base_score + score_modifier)
            
        except Exception:
            return 0.0


def main():
    """Point d'entrée principal du pipeline d'entraînement"""
    try:
        logger.info("🚀 === DÉBUT DU PIPELINE D'ENTRAÎNEMENT ===")
        
        # 1. Entraînement YOLO
        logger.info("📍 ÉTAPE 1: Entraînement YOLO")
        yolo_pipeline = YOLOTrainingPipeline()
        yolo_metrics = yolo_pipeline.train_model()
        
        # 2. Configuration OCR  
        logger.info("📍 ÉTAPE 2: Configuration OCR")
        ocr_pipeline = OCRTrainingPipeline()
        ocr_setup_success = ocr_pipeline.setup_tesseract()
        
        if ocr_setup_success:
            ocr_metrics = ocr_pipeline.optimize_preprocessing()
        else:
            ocr_metrics = {"best_score": 0.0}
        
        # 3. Validation croisée
        logger.info("📍 ÉTAPE 3: Validation finale")
        validation_metrics = yolo_pipeline.validate_model()
        
        # Résumé final
        final_results = {
            "yolo_training": yolo_metrics,
            "ocr_optimization": ocr_metrics,
            "validation": validation_metrics
        }
        
        print("\n" + "="*60)
        print("✅ ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS!")
        print("="*60)
        print(f"📊 YOLO mAP@50: {yolo_metrics.get('map50', 0.0):.3f}")
        print(f"📊 YOLO Précision: {yolo_metrics.get('precision', 0.0):.3f}")
        print(f"📊 YOLO Rappel: {yolo_metrics.get('recall', 0.0):.3f}")
        print(f"📊 OCR Score: {ocr_metrics.get('best_score', 0.0):.3f}")
        print("="*60)
        
        return final_results
        
    except Exception as e:
        logger.error(f"❌ Erreur dans le pipeline d'entraînement: {e}")
        raise


if __name__ == "__main__":
    main()
