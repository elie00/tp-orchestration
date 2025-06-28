import requests
import concurrent.futures
import time
import random

API_URL = "http://localhost:8000/predict"
TEST_IMAGE_PATH = "test_images/sample.jpg"  # À adapter selon ton projet
NUM_REQUESTS = 100
CONCURRENCY = 10

def send_request():
    with open(TEST_IMAGE_PATH, "rb") as f:
        files = {"file": f}
        start = time.time()
        response = requests.post(API_URL, files=files)
        elapsed = time.time() - start
        return response.status_code, elapsed

def main():
    times = []
    statuses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_request) for _ in range(NUM_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            status, elapsed = future.result()
            statuses.append(status)
            times.append(elapsed)
            print(f"Status: {status}, Time: {elapsed:.2f}s")
    print("\n--- Résumé ---")
    print(f"Requêtes totales : {NUM_REQUESTS}")
    print(f"Succès : {statuses.count(200)}")
    print(f"Échecs : {NUM_REQUESTS - statuses.count(200)}")
    print(f"Temps moyen : {sum(times)/len(times):.2f}s")
    print(f"Temps max : {max(times):.2f}s")
    print(f"Temps min : {min(times):.2f}s")

if __name__ == "__main__":
    main() 