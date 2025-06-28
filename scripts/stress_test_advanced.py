#!/usr/bin/env python3.10
"""
Script de test de charge avancé pour Road Sign ML API
Tests de performance, stress et endurance
"""

import requests
import concurrent.futures
import time
import random
import json
import argparse
import logging
import statistics
from pathlib import Path
from datetime import datetime
import io
from PIL import Image
import numpy as np

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIStressTester:
    """Testeur de stress pour l'API Road Sign ML"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'requests': [],
            'errors': [],
            'stats': {}
        }
        
    def create_test_image(self, width=640, height=480):
        """Crée une image de test"""
        # Génération d'une image aléatoire
        image_array = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        image = Image.fromarray(image_array)
        
        # Conversion en bytes
        image_buffer = io.BytesIO()
        image.save(image_buffer, format='JPEG')
        image_buffer.seek(0)
        
        return image_buffer.getvalue()
        
    def health_check(self):
        """Vérifie la santé de l'API"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
            
    def single_request(self, request_id=None, use_test_image=True):
        """Envoie une seule requête de prédiction"""
        start_time = time.time()
        
        try:
            if use_test_image:
                # Utilisation d'une image générée
                image_data = self.create_test_image()
                files = {"file": ("test.jpg", image_data, "image/jpeg")}
            else:
                # Utilisation d'une image réelle si disponible
                test_image_path = Path("test_images/sample.jpg")
                if test_image_path.exists():
                    with open(test_image_path, "rb") as f:
                        files = {"file": f}
                else:
                    # Fallback vers image générée
                    image_data = self.create_test_image()
                    files = {"file": ("test.jpg", image_data, "image/jpeg")}
            
            # Envoi de la requête
            response = self.session.post(
                f"{self.base_url}/predict",
                files=files,
                timeout=30
            )
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            result = {
                'id': request_id,
                'status_code': response.status_code,
                'response_time': elapsed,
                'timestamp': datetime.now().isoformat(),
                'success': response.status_code == 200,
                'response_size': len(response.content) if response.content else 0
            }
            
            # Ajout des détails de la réponse pour les requêtes réussies
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    result['predictions'] = len(response_data.get('predictions', []))
                except:
                    result['predictions'] = 0
            
            return result
            
        except Exception as e:
            end_time = time.time()
            elapsed = end_time - start_time
            
            error_result = {
                'id': request_id,
                'status_code': 0,
                'response_time': elapsed,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            }
            
            return error_result
            
    def load_test(self, num_requests=100, concurrency=10, duration=None):
        """Test de charge avec nombre de requêtes ou durée"""
        logger.info(f"🚀 Démarrage du test de charge: {num_requests} requêtes, concurrence: {concurrency}")
        
        if not self.health_check():
            logger.error("❌ API non disponible, abandon du test")
            return False
            
        start_time = time.time()
        completed_requests = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            
            if duration:
                # Test basé sur la durée
                logger.info(f"Test de durée: {duration} secondes")
                end_time = start_time + duration
                
                futures = []
                request_id = 0
                
                while time.time() < end_time:
                    # Soumission de nouvelles requêtes
                    while len(futures) < concurrency and time.time() < end_time:
                        future = executor.submit(self.single_request, request_id)
                        futures.append(future)
                        request_id += 1
                    
                    # Récupération des résultats terminés
                    completed_futures = []
                    for future in futures:
                        if future.done():
                            try:
                                result = future.result()
                                self.results['requests'].append(result)
                                completed_requests += 1
                                
                                if not result['success']:
                                    self.results['errors'].append(result)
                                    
                            except Exception as e:
                                logger.error(f"Erreur lors de la récupération du résultat: {e}")
                                
                            completed_futures.append(future)
                    
                    # Suppression des futures terminées
                    for future in completed_futures:
                        futures.remove(future)
                        
                    time.sleep(0.1)  # Petite pause pour éviter la surcharge CPU
                
                # Attente des dernières requêtes
                for future in futures:
                    try:
                        result = future.result(timeout=30)
                        self.results['requests'].append(result)
                        completed_requests += 1
                        
                        if not result['success']:
                            self.results['errors'].append(result)
                            
                    except Exception as e:
                        logger.error(f"Erreur lors de la récupération du résultat final: {e}")
                        
            else:
                # Test basé sur le nombre de requêtes
                futures = [
                    executor.submit(self.single_request, i) 
                    for i in range(num_requests)
                ]
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        self.results['requests'].append(result)
                        completed_requests += 1
                        
                        if not result['success']:
                            self.results['errors'].append(result)
                        
                        # Affichage du progrès
                        if completed_requests % max(1, num_requests // 10) == 0:
                            logger.info(f"Progrès: {completed_requests}/{num_requests} requêtes")
                            
                    except Exception as e:
                        logger.error(f"Erreur lors de la récupération du résultat: {e}")
        
        total_time = time.time() - start_time
        logger.info(f"✅ Test terminé en {total_time:.2f}s - {completed_requests} requêtes complétées")
        
        return True
        
    def stress_test(self, max_concurrency=50, step=5, requests_per_step=20):
        """Test de stress avec augmentation progressive de la charge"""
        logger.info(f"🔥 Démarrage du test de stress: jusqu'à {max_concurrency} requêtes simultanées")
        
        stress_results = []
        
        for concurrency in range(step, max_concurrency + 1, step):
            logger.info(f"Test avec {concurrency} requêtes simultanées...")
            
            # Reset des résultats pour cette étape
            step_results = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [
                    executor.submit(self.single_request, f"{concurrency}_{i}")
                    for i in range(requests_per_step)
                ]
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        step_results.append(result)
                        self.results['requests'].append(result)
                        
                        if not result['success']:
                            self.results['errors'].append(result)
                            
                    except Exception as e:
                        logger.error(f"Erreur lors du test de stress: {e}")
            
            # Analyse des résultats de cette étape
            if step_results:
                success_rate = sum(1 for r in step_results if r['success']) / len(step_results)
                avg_response_time = statistics.mean(r['response_time'] for r in step_results)
                
                stress_result = {
                    'concurrency': concurrency,
                    'requests': len(step_results),
                    'success_rate': success_rate,
                    'avg_response_time': avg_response_time,
                    'errors': len([r for r in step_results if not r['success']])
                }
                
                stress_results.append(stress_result)
                
                logger.info(f"Concurrence {concurrency}: {success_rate:.1%} succès, {avg_response_time:.2f}s moyen")
                
                # Arrêt si le taux de succès devient trop faible
                if success_rate < 0.8:
                    logger.warning(f"⚠️ Taux de succès faible ({success_rate:.1%}), arrêt du test de stress")
                    break
        
        self.results['stress_analysis'] = stress_results
        return True
        
    def endurance_test(self, duration=3600, requests_per_minute=60):
        """Test d'endurance sur une durée prolongée"""
        logger.info(f"⏱️ Démarrage du test d'endurance: {duration}s à {requests_per_minute} req/min")
        
        interval = 60 / requests_per_minute  # Intervalle entre les requêtes
        end_time = time.time() + duration
        request_count = 0
        
        while time.time() < end_time:
            # Envoi d'une requête
            result = self.single_request(f"endurance_{request_count}")
            self.results['requests'].append(result)
            
            if not result['success']:
                self.results['errors'].append(result)
            
            request_count += 1
            
            # Affichage du progrès toutes les 10 minutes
            if request_count % (10 * requests_per_minute) == 0:
                elapsed = time.time() - (end_time - duration)
                logger.info(f"Endurance: {request_count} requêtes en {elapsed/60:.1f} minutes")
            
            # Attente avant la prochaine requête
            time.sleep(interval)
        
        logger.info(f"✅ Test d'endurance terminé: {request_count} requêtes")
        return True
        
    def analyze_results(self):
        """Analyse les résultats des tests"""
        if not self.results['requests']:
            logger.warning("Aucun résultat à analyser")
            return
            
        requests = self.results['requests']
        successful_requests = [r for r in requests if r['success']]
        
        # Statistiques générales
        total_requests = len(requests)
        successful_count = len(successful_requests)
        error_count = len(self.results['errors'])
        success_rate = successful_count / total_requests if total_requests > 0 else 0
        
        # Statistiques de temps de réponse
        if successful_requests:
            response_times = [r['response_time'] for r in successful_requests]
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = np.percentile(response_times, 95)
            p99_response_time = np.percentile(response_times, 99)
        else:
            avg_response_time = median_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        # Calcul du débit (requêtes par seconde)
        if requests:
            duration = max(r['response_time'] for r in requests)
            throughput = total_requests / duration if duration > 0 else 0
        else:
            throughput = 0
            
        # Stockage des statistiques
        self.results['stats'] = {
            'total_requests': total_requests,
            'successful_requests': successful_count,
            'failed_requests': error_count,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'median_response_time': median_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'p95_response_time': p95_response_time,
            'p99_response_time': p99_response_time,
            'throughput': throughput
        }
        
    def print_results(self):
        """Affiche les résultats des tests"""
        self.analyze_results()
        
        stats = self.results['stats']
        
        print("\n" + "="*60)
        print("📊 RÉSULTATS DES TESTS DE PERFORMANCE")
        print("="*60)
        
        print(f"\n📈 STATISTIQUES GÉNÉRALES:")
        print(f"  Requêtes totales     : {stats['total_requests']:,}")
        print(f"  Requêtes réussies    : {stats['successful_requests']:,}")
        print(f"  Requêtes échouées    : {stats['failed_requests']:,}")
        print(f"  Taux de succès       : {stats['success_rate']:.1%}")
        print(f"  Débit                : {stats['throughput']:.1f} req/s")
        
        print(f"\n⏱️ TEMPS DE RÉPONSE:")
        print(f"  Moyenne              : {stats['avg_response_time']:.3f}s")
        print(f"  Médiane              : {stats['median_response_time']:.3f}s")
        print(f"  Minimum              : {stats['min_response_time']:.3f}s")
        print(f"  Maximum              : {stats['max_response_time']:.3f}s")
        print(f"  95e percentile       : {stats['p95_response_time']:.3f}s")
        print(f"  99e percentile       : {stats['p99_response_time']:.3f}s")
        
        if self.results['errors']:
            print(f"\n❌ ERREURS ({len(self.results['errors'])}):")
            error_types = {}
            for error in self.results['errors']:
                error_key = error.get('error', f"HTTP {error['status_code']}")
                error_types[error_key] = error_types.get(error_key, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"  {error_type}: {count}")
        
        # Analyse du stress test si disponible
        if 'stress_analysis' in self.results:
            print(f"\n🔥 ANALYSE DU STRESS TEST:")
            for result in self.results['stress_analysis']:
                print(f"  Concurrence {result['concurrency']:2d}: "
                      f"{result['success_rate']:.1%} succès, "
                      f"{result['avg_response_time']:.3f}s moyen")
        
        print("\n" + "="*60)
        
    def save_results(self, filename=None):
        """Sauvegarde les résultats dans un fichier JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stress_test_results_{timestamp}.json"
        
        results_to_save = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'api_url': self.base_url,
                'total_requests': len(self.results['requests'])
            },
            'stats': self.results['stats'],
            'stress_analysis': self.results.get('stress_analysis', []),
            'sample_requests': self.results['requests'][:100],  # Échantillon
            'errors': self.results['errors']
        }
        
        with open(filename, 'w') as f:
            json.dump(results_to_save, f, indent=2)
            
        logger.info(f"✅ Résultats sauvegardés dans {filename}")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Test de stress pour l'API Road Sign ML")
    
    parser.add_argument("--url", default="http://localhost:8000",
                       help="URL de base de l'API")
    parser.add_argument("--test-type", choices=['load', 'stress', 'endurance', 'all'],
                       default='load', help="Type de test à exécuter")
    
    # Options pour le test de charge
    parser.add_argument("--requests", type=int, default=100,
                       help="Nombre de requêtes pour le test de charge")
    parser.add_argument("--concurrency", type=int, default=10,
                       help="Nombre de requêtes simultanées")
    parser.add_argument("--duration", type=int, default=None,
                       help="Durée du test en secondes (au lieu du nombre de requêtes)")
    
    # Options pour le test de stress
    parser.add_argument("--max-concurrency", type=int, default=50,
                       help="Concurrence maximale pour le test de stress")
    parser.add_argument("--stress-step", type=int, default=5,
                       help="Incrément de concurrence pour le test de stress")
    parser.add_argument("--requests-per-step", type=int, default=20,
                       help="Requêtes par étape de stress")
    
    # Options pour le test d'endurance
    parser.add_argument("--endurance-duration", type=int, default=3600,
                       help="Durée du test d'endurance en secondes")
    parser.add_argument("--requests-per-minute", type=int, default=60,
                       help="Requêtes par minute pour le test d'endurance")
    
    # Options générales
    parser.add_argument("--output", default=None,
                       help="Fichier de sortie pour les résultats")
    parser.add_argument("--no-save", action="store_true",
                       help="Ne pas sauvegarder les résultats")
    
    args = parser.parse_args()
    
    # Initialisation du testeur
    tester = APIStressTester(base_url=args.url)
    
    # Vérification de la santé de l'API
    if not tester.health_check():
        logger.error("❌ L'API n'est pas accessible, abandon des tests")
        return 1
    
    logger.info(f"✅ API accessible à {args.url}")
    
    try:
        # Exécution des tests selon le type demandé
        if args.test_type == 'load' or args.test_type == 'all':
            tester.load_test(
                num_requests=args.requests,
                concurrency=args.concurrency,
                duration=args.duration
            )
        
        if args.test_type == 'stress' or args.test_type == 'all':
            tester.stress_test(
                max_concurrency=args.max_concurrency,
                step=args.stress_step,
                requests_per_step=args.requests_per_step
            )
        
        if args.test_type == 'endurance' or args.test_type == 'all':
            tester.endurance_test(
                duration=args.endurance_duration,
                requests_per_minute=args.requests_per_minute
            )
        
        # Affichage des résultats
        tester.print_results()
        
        # Sauvegarde des résultats
        if not args.no_save:
            tester.save_results(args.output)
        
        # Code de sortie basé sur le taux de succès
        success_rate = tester.results['stats'].get('success_rate', 0)
        if success_rate >= 0.95:
            logger.info("✅ Tests réussis (taux de succès ≥ 95%)")
            return 0
        elif success_rate >= 0.90:
            logger.warning("⚠️ Tests partiellement réussis (taux de succès ≥ 90%)")
            return 1
        else:
            logger.error("❌ Tests échoués (taux de succès < 90%)")
            return 2
            
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrompus par l'utilisateur")
        tester.print_results()
        return 1
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale lors des tests: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
