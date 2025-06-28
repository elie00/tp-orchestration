"""
Tests unitaires pour le pipeline de données
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
import numpy as np
from PIL import Image

import sys
sys.path.append("src")
from ml_pipelines.data_pipeline import DataPipeline


class TestDataPipeline:
    """Tests pour le pipeline de données"""
    
    @pytest.fixture
    def temp_config(self):
        """Crée une configuration temporaire pour les tests"""
        config = {
            'data': {
                'dataset': {
                    'name': 'GTSRB_TEST',
                    'source': 'test_source',
                    'classes': 5
                },
                'paths': {
                    'raw_data': 'test_data/01_raw',
                    'processed_data': 'test_data/02_processed',
                    'annotations': 'test_data/02_processed/annotations',
                    'train': 'test_data/02_processed/train',
                    'val': 'test_data/02_processed/val',
                    'test': 'test_data/02_processed/test'
                },
                'split': {
                    'train': 0.7,
                    'val': 0.2,
                    'test': 0.1,
                    'random_seed': 42,
                    'stratified': True
                }
            }
        }
        
        # Création du fichier de config temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
        
        yield config_path
        
        # Nettoyage
        Path(config_path).unlink()
    
    @pytest.fixture
    def data_pipeline(self, temp_config):
        """Instance du pipeline avec config temporaire"""
        return DataPipeline(temp_config)
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup et cleanup pour chaque test"""
        # Setup
        test_data_dir = Path("test_data")
        test_data_dir.mkdir(exist_ok=True)
        
        yield
        
        # Cleanup
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
    
    def test_init(self, data_pipeline):
        """Test l'initialisation du pipeline"""
        assert data_pipeline.config is not None
        assert 'data' in data_pipeline.config
        assert data_pipeline.data_config is not None
        assert data_pipeline.paths is not None
    
    def test_load_config_file_not_found(self):
        """Test le chargement d'un fichier de config inexistant"""
        with pytest.raises(FileNotFoundError):
            DataPipeline("nonexistent_config.yml")
    
    def test_create_directories(self, data_pipeline):
        """Test la création des répertoires"""
        data_pipeline._create_directories()
        
        for path_value in data_pipeline.paths.values():
            assert Path(path_value).exists()
    
    def test_create_sample_data(self, data_pipeline):
        """Test la création de données d'exemple"""
        data_pipeline._create_directories()
        data_pipeline._create_sample_data()
        
        raw_path = Path(data_pipeline.paths['raw_data'])
        train_path = raw_path / "Train"
        
        assert train_path.exists()
        
        # Vérifier qu'au moins une classe a été créée
        class_dirs = list(train_path.iterdir())
        assert len(class_dirs) > 0
        
        # Vérifier qu'il y a des images dans au moins une classe
        for class_dir in class_dirs:
            if class_dir.is_dir():
                images = list(class_dir.glob("*.jpg"))
                assert len(images) > 0
                break
    
    def test_collect_images_data(self, data_pipeline):
        """Test la collecte des données d'images"""
        data_pipeline._create_directories()
        data_pipeline._create_sample_data()
        
        raw_path = Path(data_pipeline.paths['raw_data'])
        images_data = data_pipeline._collect_images_data(raw_path)
        
        assert len(images_data) > 0
        
        # Vérifier la structure des données
        for item in images_data:
            assert 'image_path' in item
            assert 'class_id' in item
            assert 'class_name' in item
            assert Path(item['image_path']).exists()
    
    def test_split_data(self, data_pipeline):
        """Test le split des données"""
        # Données d'exemple
        images_data = [
            {'image_path': f'image_{i}.jpg', 'class_id': i % 3, 'class_name': f'class_{i % 3}'}
            for i in range(30)
        ]
        
        train_data, val_data, test_data = data_pipeline._split_data(images_data)
        
        # Vérifier les proportions approximatives
        total = len(images_data)
        assert len(train_data) == int(total * 0.7)
        assert len(val_data) + len(test_data) == total - len(train_data)
        
        # Vérifier qu'il n'y a pas de chevauchement
        train_paths = {item['image_path'] for item in train_data}
        val_paths = {item['image_path'] for item in val_data}
        test_paths = {item['image_path'] for item in test_data}
        
        assert len(train_paths & val_paths) == 0
        assert len(train_paths & test_paths) == 0
        assert len(val_paths & test_paths) == 0
    
    def test_split_data_empty(self, data_pipeline):
        """Test le split avec des données vides"""
        train_data, val_data, test_data = data_pipeline._split_data([])
        
        assert len(train_data) == 0
        assert len(val_data) == 0
        assert len(test_data) == 0
    
    def test_create_classes_file(self, data_pipeline):
        """Test la création du fichier classes.txt"""
        data_pipeline._create_directories()
        data_pipeline._create_classes_file()
        
        classes_file = Path(data_pipeline.paths['processed_data']) / "classes.txt"
        assert classes_file.exists()
        
        # Vérifier le contenu
        with open(classes_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) > 0
        assert "Stop" in ''.join(lines)
    
    def test_convert_to_yolo_format(self, data_pipeline):
        """Test la conversion au format YOLO"""
        data_pipeline._create_directories()
        
        # Créer une image de test
        test_dir = Path("test_images")
        test_dir.mkdir(exist_ok=True)
        
        test_image_path = test_dir / "test_image.jpg"
        test_image = Image.new('RGB', (100, 100), color='red')
        test_image.save(test_image_path)
        
        # Données de test
        test_data = [{
            'image_path': str(test_image_path),
            'class_id': 0,
            'class_name': 'test_class'
        }]
        
        try:
            count = data_pipeline._convert_to_yolo_format(test_data, "train")
            assert count == 1
            
            # Vérifier que les fichiers ont été créés
            train_path = Path(data_pipeline.paths['train'])
            images_path = train_path / "images"
            labels_path = train_path / "labels"
            
            assert images_path.exists()
            assert labels_path.exists()
            
            # Vérifier qu'il y a bien les fichiers image et label
            assert len(list(images_path.glob("*.jpg"))) == 1
            assert len(list(labels_path.glob("*.txt"))) == 1
            
        finally:
            # Nettoyage
            if test_dir.exists():
                shutil.rmtree(test_dir)
    
    def test_run_full_pipeline(self, data_pipeline):
        """Test du pipeline complet"""
        # Mock MLflow pour éviter les dépendances
        import unittest.mock
        
        with unittest.mock.patch('ml_pipelines.data_pipeline.mlflow'):
            stats = data_pipeline.run_full_pipeline()
            
            assert isinstance(stats, dict)
            assert 'train_images' in stats
            assert 'val_images' in stats
            assert 'test_images' in stats
            assert 'total_images' in stats
            
            assert stats['total_images'] == (
                stats['train_images'] + 
                stats['val_images'] + 
                stats['test_images']
            )
            
            assert stats['total_images'] > 0


class TestDataPipelineIntegration:
    """Tests d'intégration pour le pipeline de données"""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup et cleanup pour les tests d'intégration"""
        # Setup
        test_dirs = ["test_integration_data", "test_mlruns"]
        for test_dir in test_dirs:
            Path(test_dir).mkdir(exist_ok=True)
        
        yield
        
        # Cleanup
        for test_dir in test_dirs:
            if Path(test_dir).exists():
                shutil.rmtree(test_dir)
    
    def test_pipeline_with_real_images(self):
        """Test avec de vraies images créées"""
        # Créer une configuration de test
        config = {
            'data': {
                'dataset': {'name': 'TEST', 'source': 'test', 'classes': 2},
                'paths': {
                    'raw_data': 'test_integration_data/raw',
                    'processed_data': 'test_integration_data/processed',
                    'train': 'test_integration_data/processed/train',
                    'val': 'test_integration_data/processed/val',
                    'test': 'test_integration_data/processed/test'
                },
                'split': {'train': 0.8, 'val': 0.1, 'test': 0.1, 'random_seed': 42, 'stratified': True}
            }
        }
        
        config_path = "test_config_integration.yml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        try:
            # Créer des images de test réalistes
            raw_path = Path(config['data']['paths']['raw_data'])
            train_path = raw_path / "Train"
            
            # Créer 2 classes avec plusieurs images chacune
            for class_id in range(2):
                class_dir = train_path / f"{class_id:05d}"
                class_dir.mkdir(parents=True, exist_ok=True)
                
                for img_id in range(10):  # 10 images par classe
                    # Créer une image colorée différente par classe
                    color = (255, 0, 0) if class_id == 0 else (0, 255, 0)
                    img = Image.new('RGB', (64, 64), color=color)
                    img_path = class_dir / f"img_{img_id:03d}.jpg"
                    img.save(img_path)
            
            # Test du pipeline
            import unittest.mock
            with unittest.mock.patch('ml_pipelines.data_pipeline.mlflow'):
                pipeline = DataPipeline(config_path)
                stats = pipeline.run_full_pipeline()
                
                # Vérifications
                assert stats['total_images'] == 20  # 2 classes * 10 images
                assert stats['train_images'] > 0
                assert stats['val_images'] > 0
                assert stats['test_images'] > 0
                
                # Vérifier que les fichiers YOLO ont été créés
                for split in ['train', 'val', 'test']:
                    split_path = Path(config['data']['paths'][split])
                    images_path = split_path / "images"
                    labels_path = split_path / "labels"
                    
                    assert images_path.exists()
                    assert labels_path.exists()
                    
                    images = list(images_path.glob("*.jpg"))
                    labels = list(labels_path.glob("*.txt"))
                    
                    assert len(images) == len(labels)
                    assert len(images) > 0
        
        finally:
            # Nettoyage
            if Path(config_path).exists():
                Path(config_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
