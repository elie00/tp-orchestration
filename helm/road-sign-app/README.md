# Chart Helm road-sign-app

Ce chart déploie l'application Road Sign ML Project (API FastAPI, MLflow, monitoring) sur Kubernetes.

## Structure
- `values.yaml` : valeurs par défaut (image, ressources, ingress, etc.)
- `templates/` : manifests K8s (deployment, service, ingress, hpa, etc.)

## Paramètres principaux
- `image.repository` : repo de l'image Docker API
- `image.tag` : tag de l'image
- `ingress.enabled` : activer l'ingress
- `resources` : limites/requests CPU/mémoire
- `replicaCount` : nombre de pods

## Exemple d'installation
```bash
helm install road-sign-app ./helm/road-sign-app \
  --set image.repository=eybo/road-sign-api \
  --set image.tag=latest
```

## Personnalisation
Voir `values.yaml` pour tous les paramètres configurables. 