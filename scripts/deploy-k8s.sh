#!/bin/bash
# Script de déploiement Kubernetes pour Road Sign ML

set -euo pipefail

# Configuration
NAMESPACE="road-sign-ml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KUBE_DIR="${SCRIPT_DIR}/../kubernetes"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check required files
    local required_files=(
        "${KUBE_DIR}/namespace.yaml"
        "${KUBE_DIR}/configmap.yaml"
        "${KUBE_DIR}/secret.yaml"
        "${KUBE_DIR}/api/deployment.yaml"
        "${KUBE_DIR}/api/service.yaml"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    
    log_success "Prerequisites check passed"
}

create_namespace() {
    log_info "Creating namespace..."
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE already exists"
    else
        kubectl apply -f "${KUBE_DIR}/namespace.yaml"
        log_success "Namespace $NAMESPACE created"
    fi
}

deploy_secrets() {
    log_info "Deploying secrets..."
    
    # Check if secrets file has been customized
    if grep -q "WU9VUl9BV1NfQUNDRVNTX0tFWV9JRA==" "${KUBE_DIR}/secret.yaml"; then
        log_warning "Secrets file contains template values. Please update with actual secrets."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    kubectl apply -f "${KUBE_DIR}/secret.yaml" -n "$NAMESPACE"
    log_success "Secrets deployed"
}

deploy_config() {
    log_info "Deploying configuration..."
    
    kubectl apply -f "${KUBE_DIR}/configmap.yaml" -n "$NAMESPACE"
    log_success "Configuration deployed"
}

deploy_storage() {
    log_info "Deploying storage..."
    
    # Deploy PVCs
    if [[ -f "${KUBE_DIR}/api/pvc.yaml" ]]; then
        kubectl apply -f "${KUBE_DIR}/api/pvc.yaml" -n "$NAMESPACE"
    fi
    
    if [[ -f "${KUBE_DIR}/mlflow/pvc.yaml" ]]; then
        kubectl apply -f "${KUBE_DIR}/mlflow/pvc.yaml" -n "$NAMESPACE"
    fi
    
    log_success "Storage deployed"
}

deploy_mlflow() {
    log_info "Deploying MLflow..."
    
    # Deploy PostgreSQL first
    kubectl apply -f "${KUBE_DIR}/mlflow/pvc.yaml" -n "$NAMESPACE"
    kubectl apply -f "${KUBE_DIR}/mlflow/deployment.yaml" -n "$NAMESPACE"
    kubectl apply -f "${KUBE_DIR}/mlflow/service.yaml" -n "$NAMESPACE"
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=mlflow-postgres -n "$NAMESPACE" --timeout=300s
    
    log_success "MLflow deployed"
}

deploy_api() {
    log_info "Deploying API..."
    
    # Deploy API components
    kubectl apply -f "${KUBE_DIR}/api/deployment.yaml" -n "$NAMESPACE"
    kubectl apply -f "${KUBE_DIR}/api/service.yaml" -n "$NAMESPACE"
    kubectl apply -f "${KUBE_DIR}/api/hpa.yaml" -n "$NAMESPACE"
    
    # Wait for deployment to be ready
    log_info "Waiting for API deployment to be ready..."
    kubectl rollout status deployment/road-sign-api -n "$NAMESPACE" --timeout=600s
    
    log_success "API deployed"
}

deploy_ingress() {
    log_info "Deploying ingress..."
    
    if [[ -f "${KUBE_DIR}/api/ingress.yaml" ]]; then
        kubectl apply -f "${KUBE_DIR}/api/ingress.yaml" -n "$NAMESPACE"
        log_success "Ingress deployed"
    else
        log_warning "Ingress file not found, skipping"
    fi
}

deploy_monitoring() {
    log_info "Deploying monitoring..."
    
    if [[ -d "${KUBE_DIR}/monitoring" ]]; then
        kubectl apply -f "${KUBE_DIR}/monitoring/" -n "$NAMESPACE"
        log_success "Monitoring deployed"
    else
        log_warning "Monitoring directory not found, skipping"
    fi
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pods
    log_info "Checking pod status..."
    kubectl get pods -n "$NAMESPACE"
    
    # Check services
    log_info "Checking service status..."
    kubectl get services -n "$NAMESPACE"
    
    # Health check
    log_info "Running health check..."
    local api_pod=$(kubectl get pods -n "$NAMESPACE" -l app=road-sign-api -o jsonpath='{.items[0].metadata.name}')
    if [[ -n "$api_pod" ]]; then
        kubectl exec -n "$NAMESPACE" "$api_pod" -- curl -f http://localhost:8000/health
        log_success "Health check passed"
    else
        log_warning "API pod not found, skipping health check"
    fi
}

cleanup() {
    log_info "Cleaning up..."
    
    read -p "Are you sure you want to delete all resources in namespace $NAMESPACE? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace "$NAMESPACE"
        log_success "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
}

show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy    Deploy complete application"
    echo "  update    Update existing deployment"
    echo "  cleanup   Delete all resources"
    echo "  status    Show deployment status"
    echo "  logs      Show application logs"
    echo "  help      Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  NAMESPACE    Kubernetes namespace (default: road-sign-ml)"
    echo "  KUBE_CONFIG  Path to kubeconfig file"
}

show_status() {
    log_info "Deployment status for namespace: $NAMESPACE"
    
    echo ""
    echo "=== PODS ==="
    kubectl get pods -n "$NAMESPACE" -o wide
    
    echo ""
    echo "=== SERVICES ==="
    kubectl get services -n "$NAMESPACE"
    
    echo ""
    echo "=== INGRESS ==="
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo "No ingress found"
    
    echo ""
    echo "=== HPA ==="
    kubectl get hpa -n "$NAMESPACE" 2>/dev/null || echo "No HPA found"
    
    echo ""
    echo "=== PVC ==="
    kubectl get pvc -n "$NAMESPACE" 2>/dev/null || echo "No PVC found"
}

show_logs() {
    local component=${1:-api}
    
    log_info "Showing logs for component: $component"
    
    case $component in
        api)
            kubectl logs -f -n "$NAMESPACE" -l app=road-sign-api
            ;;
        mlflow)
            kubectl logs -f -n "$NAMESPACE" -l app=mlflow
            ;;
        postgres)
            kubectl logs -f -n "$NAMESPACE" -l app=mlflow-postgres
            ;;
        *)
            log_error "Unknown component: $component"
            echo "Available components: api, mlflow, postgres"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    local command=${1:-help}
    
    case $command in
        deploy)
            check_prerequisites
            create_namespace
            deploy_secrets
            deploy_config
            deploy_storage
            deploy_mlflow
            deploy_api
            deploy_ingress
            deploy_monitoring
            verify_deployment
            log_success "Deployment completed successfully!"
            ;;
        update)
            check_prerequisites
            deploy_config
            deploy_api
            verify_deployment
            log_success "Update completed successfully!"
            ;;
        cleanup)
            cleanup
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-api}"
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
