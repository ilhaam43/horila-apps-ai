#!/bin/bash

# Horilla HR System Deployment Script
# This script automates the deployment of Horilla HR System
# Supports Docker Compose and Kubernetes deployments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/tmp/horilla_deploy_$(date +"%Y%m%d_%H%M%S").log"

# Default values
DEPLOYMENT_TYPE="docker-compose"
ENVIRONMENT="development"
SKIP_BACKUP="false"
SKIP_TESTS="false"
FORCE_REBUILD="false"
VERBOSE="false"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            if [ "$VERBOSE" = "true" ]; then
                echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE"
            else
                echo "[$timestamp] [DEBUG] $message" >> "$LOG_FILE"
            fi
            ;;
        *)
            echo "[$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    log "ERROR" "Deployment failed. Check logs at: $LOG_FILE"
    exit 1
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Horilla HR System

OPTIONS:
    -t, --type TYPE         Deployment type: docker-compose, kubernetes, ha (default: docker-compose)
    -e, --environment ENV   Environment: development, staging, production (default: development)
    -b, --skip-backup      Skip backup before deployment
    -s, --skip-tests       Skip running tests
    -f, --force-rebuild    Force rebuild of Docker images
    -v, --verbose          Enable verbose output
    -h, --help             Show this help message

DEPLOYMENT TYPES:
    docker-compose         Standard Docker Compose deployment
    kubernetes            Kubernetes deployment
    ha                    High Availability Docker Compose deployment

ENVIRONMENTS:
    development           Development environment with debug enabled
    staging               Staging environment for testing
    production            Production environment with optimizations

Examples:
    $0                                    # Deploy with defaults
    $0 -t ha -e production               # Deploy HA setup for production
    $0 -t kubernetes -e staging -v       # Deploy to Kubernetes staging with verbose output
    $0 -f -s                             # Force rebuild and skip tests

EOF
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [ ! -f "$PROJECT_DIR/manage.py" ]; then
        error_exit "Not in Horilla project directory. Please run from project root."
    fi
    
    # Check required tools based on deployment type
    case $DEPLOYMENT_TYPE in
        "docker-compose"|"ha")
            command -v docker >/dev/null 2>&1 || error_exit "Docker not found"
            command -v docker-compose >/dev/null 2>&1 || error_exit "Docker Compose not found"
            ;;
        "kubernetes")
            command -v kubectl >/dev/null 2>&1 || error_exit "kubectl not found"
            command -v helm >/dev/null 2>&1 || log "WARN" "Helm not found (optional)"
            ;;
    esac
    
    # Check other required tools
    command -v git >/dev/null 2>&1 || error_exit "Git not found"
    
    log "INFO" "Prerequisites check passed"
}

# Backup current deployment
backup_current_deployment() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        log "INFO" "Skipping backup as requested"
        return 0
    fi
    
    log "INFO" "Creating backup of current deployment..."
    
    if [ -f "$PROJECT_DIR/scripts/backup.sh" ]; then
        if bash "$PROJECT_DIR/scripts/backup.sh"; then
            log "INFO" "Backup completed successfully"
        else
            log "WARN" "Backup failed, but continuing with deployment"
        fi
    else
        log "WARN" "Backup script not found, skipping backup"
    fi
}

# Run tests
run_tests() {
    if [ "$SKIP_TESTS" = "true" ]; then
        log "INFO" "Skipping tests as requested"
        return 0
    fi
    
    log "INFO" "Running tests..."
    
    cd "$PROJECT_DIR"
    
    # Run different test suites based on what's available
    local test_failed=false
    
    # Django tests
    if [ -f "manage.py" ]; then
        log "DEBUG" "Running Django tests..."
        if python manage.py test --verbosity=1 2>>"$LOG_FILE"; then
            log "INFO" "Django tests passed"
        else
            log "WARN" "Some Django tests failed"
            test_failed=true
        fi
    fi
    
    # Python unit tests
    if command -v pytest >/dev/null 2>&1 && [ -d "tests" ]; then
        log "DEBUG" "Running pytest..."
        if pytest tests/ -v 2>>"$LOG_FILE"; then
            log "INFO" "Pytest tests passed"
        else
            log "WARN" "Some pytest tests failed"
            test_failed=true
        fi
    fi
    
    if [ "$test_failed" = "true" ] && [ "$ENVIRONMENT" = "production" ]; then
        error_exit "Tests failed in production environment. Aborting deployment."
    elif [ "$test_failed" = "true" ]; then
        log "WARN" "Tests failed but continuing deployment in $ENVIRONMENT environment"
    fi
}

# Build Docker images
build_images() {
    log "INFO" "Building Docker images..."
    
    cd "$PROJECT_DIR"
    
    local build_args=""
    if [ "$FORCE_REBUILD" = "true" ]; then
        build_args="--no-cache"
    fi
    
    # Build main application image
    log "DEBUG" "Building main application image..."
    if docker build $build_args -t horilla/hr-system:latest . 2>>"$LOG_FILE"; then
        log "INFO" "Main application image built successfully"
    else
        error_exit "Failed to build main application image"
    fi
    
    # Tag image with environment and timestamp
    local tag="$ENVIRONMENT-$(date +%Y%m%d-%H%M%S)"
    docker tag horilla/hr-system:latest horilla/hr-system:$tag
    log "INFO" "Tagged image as horilla/hr-system:$tag"
}

# Deploy with Docker Compose
deploy_docker_compose() {
    log "INFO" "Deploying with Docker Compose..."
    
    cd "$PROJECT_DIR"
    
    local compose_file="docker-compose.yml"
    local env_file=".env.$ENVIRONMENT"
    
    # Use environment-specific compose file if available
    if [ -f "docker-compose.$ENVIRONMENT.yml" ]; then
        compose_file="docker-compose.$ENVIRONMENT.yml"
    fi
    
    # Create environment file if it doesn't exist
    if [ ! -f "$env_file" ]; then
        log "WARN" "Environment file $env_file not found, creating default"
        create_env_file "$env_file"
    fi
    
    # Stop existing services
    log "DEBUG" "Stopping existing services..."
    docker-compose -f "$compose_file" --env-file "$env_file" down 2>>"$LOG_FILE" || true
    
    # Start services
    log "DEBUG" "Starting services..."
    if docker-compose -f "$compose_file" --env-file "$env_file" up -d 2>>"$LOG_FILE"; then
        log "INFO" "Services started successfully"
    else
        error_exit "Failed to start services"
    fi
    
    # Wait for services to be ready
    wait_for_services_docker_compose "$compose_file" "$env_file"
}

# Deploy High Availability setup
deploy_ha() {
    log "INFO" "Deploying High Availability setup..."
    
    cd "$PROJECT_DIR"
    
    local compose_file="docker-compose.ha.yml"
    local env_file=".env.$ENVIRONMENT"
    
    if [ ! -f "$compose_file" ]; then
        error_exit "HA compose file not found: $compose_file"
    fi
    
    # Create environment file if it doesn't exist
    if [ ! -f "$env_file" ]; then
        log "WARN" "Environment file $env_file not found, creating default"
        create_env_file "$env_file"
    fi
    
    # Stop existing services
    log "DEBUG" "Stopping existing services..."
    docker-compose -f "$compose_file" --env-file "$env_file" down 2>>"$LOG_FILE" || true
    
    # Start services in order
    log "DEBUG" "Starting infrastructure services..."
    docker-compose -f "$compose_file" --env-file "$env_file" up -d postgres_primary redis_primary 2>>"$LOG_FILE"
    
    sleep 10
    
    log "DEBUG" "Starting application services..."
    if docker-compose -f "$compose_file" --env-file "$env_file" up -d 2>>"$LOG_FILE"; then
        log "INFO" "HA services started successfully"
    else
        error_exit "Failed to start HA services"
    fi
    
    # Wait for services to be ready
    wait_for_services_docker_compose "$compose_file" "$env_file"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log "INFO" "Deploying to Kubernetes..."
    
    cd "$PROJECT_DIR"
    
    local k8s_dir="k8s"
    local deployment_file="$k8s_dir/horilla-ha-deployment.yaml"
    
    if [ ! -f "$deployment_file" ]; then
        error_exit "Kubernetes deployment file not found: $deployment_file"
    fi
    
    # Check kubectl connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        error_exit "Cannot connect to Kubernetes cluster"
    fi
    
    # Apply namespace first
    log "DEBUG" "Creating namespace..."
    kubectl apply -f "$deployment_file" --dry-run=client -o yaml | \
        grep -A 10 "kind: Namespace" | \
        kubectl apply -f - 2>>"$LOG_FILE"
    
    # Apply ConfigMaps and Secrets
    log "DEBUG" "Applying ConfigMaps and Secrets..."
    kubectl apply -f "$deployment_file" --dry-run=client -o yaml | \
        grep -A 20 -E "kind: (ConfigMap|Secret)" | \
        kubectl apply -f - 2>>"$LOG_FILE"
    
    # Apply PVCs
    log "DEBUG" "Applying PersistentVolumeClaims..."
    kubectl apply -f "$deployment_file" --dry-run=client -o yaml | \
        grep -A 10 "kind: PersistentVolumeClaim" | \
        kubectl apply -f - 2>>"$LOG_FILE"
    
    # Apply StatefulSets (databases)
    log "DEBUG" "Applying StatefulSets..."
    kubectl apply -f "$deployment_file" --dry-run=client -o yaml | \
        grep -A 50 "kind: StatefulSet" | \
        kubectl apply -f - 2>>"$LOG_FILE"
    
    # Wait for StatefulSets to be ready
    log "DEBUG" "Waiting for databases to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n horilla-hr --timeout=300s 2>>"$LOG_FILE" || true
    kubectl wait --for=condition=ready pod -l app=redis -n horilla-hr --timeout=300s 2>>"$LOG_FILE" || true
    
    # Apply Deployments
    log "DEBUG" "Applying Deployments..."
    kubectl apply -f "$deployment_file" 2>>"$LOG_FILE"
    
    # Wait for deployments to be ready
    log "DEBUG" "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available deployment --all -n horilla-hr --timeout=600s 2>>"$LOG_FILE"
    
    log "INFO" "Kubernetes deployment completed successfully"
}

# Wait for services to be ready (Docker Compose)
wait_for_services_docker_compose() {
    local compose_file=$1
    local env_file=$2
    
    log "INFO" "Waiting for services to be ready..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        log "DEBUG" "Health check attempt $attempt/$max_attempts"
        
        # Check if web service is responding
        if curl -f http://localhost:8000/health/ >/dev/null 2>&1; then
            log "INFO" "Web service is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error_exit "Services failed to become ready within timeout"
        fi
        
        sleep 10
    done
}

# Create environment file
create_env_file() {
    local env_file=$1
    
    log "DEBUG" "Creating environment file: $env_file"
    
    cat > "$env_file" << EOF
# Horilla HR System Environment Configuration
# Generated on $(date)

# Environment
DEBUG=$([ "$ENVIRONMENT" = "development" ] && echo "True" || echo "False")
ENVIRONMENT=$ENVIRONMENT

# Security
SECRET_KEY=super-secret-key-for-horilla-hr-system-change-in-production
ALLOWED_HOSTS=*

# Database
POSTGRES_HOST=postgres_primary
POSTGRES_DB=horilla_db
POSTGRES_USER=horilla_user
POSTGRES_PASSWORD=horilla_pass

# Redis
REDIS_HOST=redis_primary
REDIS_PORT=6379
REDIS_PASSWORD=redis_pass

# Celery
CELERY_BROKER_URL=redis://redis_primary:6379/0
CELERY_RESULT_BACKEND=redis://redis_primary:6379/0

# External Services
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200
OLLAMA_HOST=ollama
OLLAMA_PORT=11434
N8N_HOST=n8n
N8N_PORT=5678
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000

# Backup
BACKUP_RETENTION_DAYS=30
EOF
    
    log "INFO" "Environment file created: $env_file"
}

# Run database migrations
run_migrations() {
    log "INFO" "Running database migrations..."
    
    case $DEPLOYMENT_TYPE in
        "docker-compose"|"ha")
            if docker-compose exec web python manage.py migrate 2>>"$LOG_FILE"; then
                log "INFO" "Migrations completed successfully"
            else
                log "WARN" "Migrations failed or no web service running"
            fi
            ;;
        "kubernetes")
            local pod=$(kubectl get pods -n horilla-hr -l app=horilla-web -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
            if [ -n "$pod" ]; then
                if kubectl exec -n horilla-hr "$pod" -- python manage.py migrate 2>>"$LOG_FILE"; then
                    log "INFO" "Migrations completed successfully"
                else
                    log "WARN" "Migrations failed"
                fi
            else
                log "WARN" "No web pods found for migrations"
            fi
            ;;
    esac
}

# Collect static files
collect_static() {
    log "INFO" "Collecting static files..."
    
    case $DEPLOYMENT_TYPE in
        "docker-compose"|"ha")
            if docker-compose exec web python manage.py collectstatic --noinput 2>>"$LOG_FILE"; then
                log "INFO" "Static files collected successfully"
            else
                log "WARN" "Static files collection failed or no web service running"
            fi
            ;;
        "kubernetes")
            local pod=$(kubectl get pods -n horilla-hr -l app=horilla-web -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
            if [ -n "$pod" ]; then
                if kubectl exec -n horilla-hr "$pod" -- python manage.py collectstatic --noinput 2>>"$LOG_FILE"; then
                    log "INFO" "Static files collected successfully"
                else
                    log "WARN" "Static files collection failed"
                fi
            else
                log "WARN" "No web pods found for static files collection"
            fi
            ;;
    esac
}

# Post-deployment tasks
post_deployment_tasks() {
    log "INFO" "Running post-deployment tasks..."
    
    run_migrations
    collect_static
    
    # Create superuser in development
    if [ "$ENVIRONMENT" = "development" ]; then
        log "INFO" "Creating development superuser..."
        case $DEPLOYMENT_TYPE in
            "docker-compose"|"ha")
                docker-compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@horilla.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
" 2>>"$LOG_FILE" || log "WARN" "Failed to create superuser"
                ;;
        esac
    fi
    
    log "INFO" "Post-deployment tasks completed"
}

# Show deployment status
show_deployment_status() {
    log "INFO" "Deployment Status:"
    
    case $DEPLOYMENT_TYPE in
        "docker-compose"|"ha")
            echo
            docker-compose ps
            echo
            log "INFO" "Application URL: http://localhost:8000"
            if [ "$DEPLOYMENT_TYPE" = "ha" ]; then
                log "INFO" "HAProxy Stats: http://localhost:8404/stats"
                log "INFO" "Grafana: http://localhost:3000"
                log "INFO" "Prometheus: http://localhost:9090"
            fi
            ;;
        "kubernetes")
            echo
            kubectl get pods -n horilla-hr
            echo
            kubectl get services -n horilla-hr
            echo
            local ingress_ip=$(kubectl get ingress -n horilla-hr horilla-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
            log "INFO" "Ingress IP: $ingress_ip"
            ;;
    esac
}

# Main deployment function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -b|--skip-backup)
                SKIP_BACKUP="true"
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            -f|--force-rebuild)
                FORCE_REBUILD="true"
                shift
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                error_exit "Unexpected argument: $1"
                ;;
        esac
    done
    
    # Validate arguments
    case $DEPLOYMENT_TYPE in
        "docker-compose"|"kubernetes"|"ha")
            ;;
        *)
            error_exit "Invalid deployment type: $DEPLOYMENT_TYPE"
            ;;
    esac
    
    case $ENVIRONMENT in
        "development"|"staging"|"production")
            ;;
        *)
            error_exit "Invalid environment: $ENVIRONMENT"
            ;;
    esac
    
    log "INFO" "Starting Horilla HR System deployment"
    log "INFO" "Deployment Type: $DEPLOYMENT_TYPE"
    log "INFO" "Environment: $ENVIRONMENT"
    log "INFO" "Log File: $LOG_FILE"
    
    local start_time=$(date +%s)
    
    # Run deployment steps
    check_prerequisites
    backup_current_deployment
    run_tests
    
    if [ "$DEPLOYMENT_TYPE" != "kubernetes" ]; then
        build_images
    fi
    
    case $DEPLOYMENT_TYPE in
        "docker-compose")
            deploy_docker_compose
            ;;
        "ha")
            deploy_ha
            ;;
        "kubernetes")
            deploy_kubernetes
            ;;
    esac
    
    post_deployment_tasks
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "INFO" "Deployment completed successfully in ${duration} seconds"
    
    show_deployment_status
    
    log "INFO" "Deployment log saved to: $LOG_FILE"
}

# Error handling
trap 'error_exit "Deployment interrupted"' INT TERM

# Run main function
main "$@"