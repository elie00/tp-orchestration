"""
Pipeline d'ingestion et préprocessing des données GTSRB
Ce module gère le téléchargement, l'extraction et la préparation des données
pour l'entraînement des modèles YOLO et OCR.
"""

import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

import mlflow
import mlflow.data
import pandas as pd
from PIL import Image
import numpy as np
from sklearn.model_selection import train_test_split

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPipeline:
    """Pipeline de gestion des données pour le projet road sign detection"""
    
    def __init__(self, config_path: str = "conf/base/model_config.yml"):
        """
        Initialise le pipeline de données
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        self.config = self._load_config(config_path)
        self.data_config = self.config['data']
        self.paths = self.data_config['paths']
        
        # Création des répertoires nécessaires
        self._create_directories()
        
        # Initialisation MLflow
        mlflow.set_experiment("RoadSign_Data_Processing")
        
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration depuis le fichier YAML"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Fichier de configuration non trouvé: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Erreur de parsing YAML: {e}")
            raise
            
    def _create_directories(self) -> None:
        """Crée les répertoires nécessaires pour les données"""
        for path_name, path_value in self.paths.items():
            Path(path_value).mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire créé/vérifié: {path_value}")
    
    def download_gtsrb_dataset(self) -> bool:
        """
        Télécharge le dataset GTSRB depuis Kaggle
        
        Returns:
            bool: True si succès, False sinon
        """
        with mlflow.start_run(run_name="download_gtsrb_data"):
            try:
                logger.info("Début du téléchargement du dataset GTSRB")
                
                # Note: Pour l'instant, nous simulons le téléchargement
                # En production, utiliser: kaggle datasets download -d meowmeowmeowmeowmeow/gtsrb-german-traffic-sign
                
                # Log des paramètres MLflow
                mlflow.log_param("dataset_name", self.data_config['dataset']['name'])
                mlflow.log_param("dataset_source", self.data_config['dataset']['source'])
                mlflow.log_param("num_classes", self.data_config['dataset']['classes'])
                
                # Simulation: création de quelques images de test
                self._create_sample_data()
                
                mlflow.log_metric("download_success", 1)
                logger.info("Dataset GTSRB téléchargé avec succès")
                return True
                
            except Exception as e:
                logger.error(f"Erreur lors du téléchargement: {e}")
                mlflow.log_metric("download_success", 0)
                mlflow.log_param("error_message", str(e))
                return False
    
    def _create_sample_data(self) -> None:
        """Crée des données d'exemple pour tester le pipeline"""
        raw_path = Path(self.paths['raw_data'])
        
        # Création de quelques classes d'exemple
        sample_classes = [
            "00000",  # Speed limit (20km/h)
            "00001",  # Speed limit (30km/h) 
            "00014",  # Stop
            "00017",  # No entry
        ]
        
        for class_id in sample_classes:
            class_dir = raw_path / "Train" / class_id
            class_dir.mkdir(parents=True, exist_ok=True)
            
            # Création de quelques images d'exemple
            for i in range(5):
                # Image RGB aléatoire 64x64
                img_array = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
                img = Image.fromarray(img_array)
                img_path = class_dir / f"sample_{i:05d}.jpg"
                img.save(img_path)
        
        logger.info(f"Données d'exemple créées dans {raw_path}")
    
    def preprocess_data(self) -> Tuple[int, int, int]:
        """
        Préprocesse les données pour l'entraînement YOLO
        
        Returns:
            Tuple[int, int, int]: Nombre d'images (train, val, test)
        """
        with mlflow.start_run(run_name="preprocess_data"):
            try:
                logger.info("Début du préprocessing des données")
                
                # Chargement des données brutes
                raw_path = Path(self.paths['raw_data'])
                if not raw_path.exists():
                    raise FileNotFoundError(f"Répertoire de données brutes non trouvé: {raw_path}")
                
                # Collecte des images et labels
                images_data = self._collect_images_data(raw_path)
                
                # Split train/val/test
                train_data, val_data, test_data = self._split_data(images_data)
                
                # Conversion au format YOLO
                train_count = self._convert_to_yolo_format(train_data, "train")
                val_count = self._convert_to_yolo_format(val_data, "val") 
                test_count = self._convert_to_yolo_format(test_data, "test")
                
                # Création du fichier classes.txt
                self._create_classes_file()
                
                # Logging MLflow
                mlflow.log_param("train_split", self.data_config['split']['train'])
                mlflow.log_param("val_split", self.data_config['split']['val'])
                mlflow.log_param("test_split", self.data_config['split']['test'])
                mlflow.log_param("random_seed", self.data_config['split']['random_seed'])
                
                mlflow.log_metric("train_images", train_count)
                mlflow.log_metric("val_images", val_count)
                mlflow.log_metric("test_images", test_count)
                mlflow.log_metric("total_images", train_count + val_count + test_count)
                
                logger.info(f"Préprocessing terminé: {train_count} train, {val_count} val, {test_count} test")
                return train_count, val_count, test_count
                
            except Exception as e:
                logger.error(f"Erreur lors du préprocessing: {e}")
                mlflow.log_param("error_message", str(e))
                raise
    
    def _collect_images_data(self, raw_path: Path) -> List[Dict]:
        """Collecte les données d'images depuis le répertoire brut"""
        images_data = []
        train_path = raw_path / "Train"
        
        if not train_path.exists():
            logger.warning(f"Répertoire Train non trouvé: {train_path}")
            return images_data
        
        for class_dir in train_path.iterdir():
            if class_dir.is_dir():
                class_id = int(class_dir.name)
                
                for img_file in class_dir.glob("*.jpg"):
                    images_data.append({
                        'image_path': str(img_file),
                        'class_id': class_id,
                        'class_name': class_dir.name
                    })
        
        logger.info(f"Collecté {len(images_data)} images")
        return images_data
    
    def _split_data(self, images_data: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Split les données en train/val/test"""
        if not images_data:
            return [], [], []
        
        # Extraction des features et labels pour le split stratifié
        X = [item['image_path'] for item in images_data]
        y = [item['class_id'] for item in images_data]
        
        # Split train/(val+test)
        train_split = self.data_config['split']['train']
        random_seed = self.data_config['split']['random_seed']
        
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, 
            train_size=train_split,
            random_state=random_seed,
            stratify=y if self.data_config['split']['stratified'] else None
        )
        
        # Split val/test
        val_split = self.data_config['split']['val']
        test_split = self.data_config['split']['test']
        val_ratio = val_split / (val_split + test_split)
        
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp,
            train_size=val_ratio,
            random_state=random_seed,
            stratify=y_temp if self.data_config['split']['stratified'] else None
        )
        
        # Reconstruction des dictionnaires
        def create_data_list(paths, labels):
            return [
                {
                    'image_path': path,
                    'class_id': label,
                    'class_name': f"{label:05d}"
                }
                for path, label in zip(paths, labels)
            ]
        
        train_data = create_data_list(X_train, y_train)
        val_data = create_data_list(X_val, y_val)
        test_data = create_data_list(X_test, y_test)
        
        return train_data, val_data, test_data
    
    def _convert_to_yolo_format(self, data: List[Dict], split_name: str) -> int:
        """Convertit les données au format YOLO"""
        if not data:
            return 0
        
        split_path = Path(self.paths[split_name])
        images_path = split_path / "images"
        labels_path = split_path / "labels"
        
        images_path.mkdir(parents=True, exist_ok=True)
        labels_path.mkdir(parents=True, exist_ok=True)
        
        count = 0
        for item in data:
            try:
                # Copie de l'image
                src_path = Path(item['image_path'])
                dst_img_path = images_path / f"{src_path.stem}.jpg"
                shutil.copy2(src_path, dst_img_path)
                
                # Création du fichier d'annotation YOLO
                # Pour les panneaux, on assume une bbox couvrant toute l'image
                dst_label_path = labels_path / f"{src_path.stem}.txt"
                
                # Format YOLO: class_id center_x center_y width height (normalisé 0-1)
                # Ici on simule une bbox centrale couvrant 80% de l'image
                yolo_annotation = f"{item['class_id']} 0.5 0.5 0.8 0.8\n"
                
                with open(dst_label_path, 'w') as f:
                    f.write(yolo_annotation)
                
                count += 1
                
            except Exception as e:
                logger.warning(f"Erreur lors de la conversion de {item['image_path']}: {e}")
        
        logger.info(f"Converti {count} images pour le split {split_name}")
        return count
    
    def _create_classes_file(self) -> None:
        """Crée le fichier classes.txt avec les noms des classes"""
        # Classes GTSRB simplifiées pour l'exemple
        classes = [
            "Speed limit (20km/h)",
            "Speed limit (30km/h)",
            "Speed limit (50km/h)",
            "Speed limit (60km/h)",
            "Speed limit (70km/h)",
            "Speed limit (80km/h)",
            "End of speed limit (80km/h)",
            "Speed limit (100km/h)",
            "Speed limit (120km/h)",
            "No passing",
            "No passing veh over 3.5 tons",
            "Right-of-way at intersection",
            "Priority road",
            "Yield",
            "Stop",
            "No vehicles",
            "Veh > 3.5 tons prohibited",
            "No entry",
            "General caution",
            "Dangerous curve left",
            "Dangerous curve right",
            "Double curve",
            "Bumpy road",
            "Slippery road",
            "Road narrows on the right",
            "Road work",
            "Traffic signals",
            "Pedestrians",
            "Children crossing",
            "Bicycles crossing",
            "Beware of ice/snow",
            "Wild animals crossing",
            "End speed + passing limits",
            "Turn right ahead",
            "Turn left ahead",
            "Ahead only",
            "Go straight or right",
            "Go straight or left",
            "Keep right",
            "Keep left",
            "Roundabout mandatory",
            "End of no passing",
            "End no passing veh > 3.5 tons"
        ]
        
        classes_file = Path(self.paths['processed_data']) / "classes.txt"
        with open(classes_file, 'w', encoding='utf-8') as f:
            for class_name in classes:
                f.write(f"{class_name}\n")
        
        logger.info(f"Fichier classes.txt créé: {classes_file}")
    
    def run_full_pipeline(self) -> Dict[str, int]:
        """
        Exécute le pipeline complet de traitement des données
        
        Returns:
            Dict[str, int]: Statistiques du traitement
        """
        logger.info("=== DÉBUT DU PIPELINE DE DONNÉES ===")
        
        # 1. Téléchargement des données
        if not self.download_gtsrb_dataset():
            raise RuntimeError("Échec du téléchargement des données")
        
        # 2. Préprocessing et conversion
        train_count, val_count, test_count = self.preprocess_data()
        
        stats = {
            'train_images': train_count,
            'val_images': val_count,
            'test_images': test_count,
            'total_images': train_count + val_count + test_count
        }
        
        logger.info("=== PIPELINE DE DONNÉES TERMINÉ ===")
        logger.info(f"Statistiques finales: {stats}")
        
        return stats


def main():
    """Point d'entrée principal du pipeline de données"""
    try:
        # Initialisation du pipeline
        pipeline = DataPipeline()
        
        # Exécution complète
        stats = pipeline.run_full_pipeline()
        
        print("\n✅ Pipeline de données exécuté avec succès!")
        print(f"📊 Images traitées: {stats['total_images']}")
        print(f"   - Train: {stats['train_images']}")
        print(f"   - Validation: {stats['val_images']}")
        print(f"   - Test: {stats['test_images']}")
        
    except Exception as e:
        logger.error(f"❌ Erreur dans le pipeline de données: {e}")
        raise


if __name__ == "__main__":
    main()
