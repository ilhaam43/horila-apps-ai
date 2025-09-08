#!/bin/bash

# Model Deployment Entrypoint Script
# Handles initialization and startup for AI model deployment container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Environment variables with defaults
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"horilla.settings"}
export DEBUG=${DEBUG:-"False"}
export ALLOWED_HOSTS=${ALLOWED_HOSTS:-"localhost,127.0.0.1"}
export DATABASE_URL=${DATABASE_URL:-"sqlite:///db.sqlite3"}
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
export CELERY_BROKER_URL=${CELERY_BROKER_URL:-$REDIS_URL}
export CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-$REDIS_URL}

# AI Model specific environment variables
export AI_MODEL_CACHE_TTL=${AI_MODEL_CACHE_TTL:-"3600"}
export AI_MODEL_MAX_WORKERS=${AI_MODEL_MAX_WORKERS:-"4"}
export AI_MODEL_TIMEOUT=${AI_MODEL_TIMEOUT:-"120"}
export DEPLOYMENT_DIR=${DEPLOYMENT_DIR:-"/app/deployed_models"}

# Function to wait for database
wait_for_db() {
    log "Waiting for database connection..."
    
    python << END
import os
import sys
import time
import django
from django.conf import settings
from django.db import connections
from django.core.management.color import no_style
from django.db.utils import OperationalError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_SETTINGS_MODULE')
django.setup()

style = no_style()
connection = connections['default']

for i in range(30):
    try:
        connection.ensure_connection()
        print("Database connection successful!")
        sys.exit(0)
    except OperationalError:
        print(f"Database unavailable, waiting... ({i+1}/30)")
        time.sleep(2)

print("Database connection failed after 30 attempts")
sys.exit(1)
END

    if [ $? -eq 0 ]; then
        log_success "Database connection established"
    else
        log_error "Failed to connect to database"
        exit 1
    fi
}

# Function to wait for Redis
wait_for_redis() {
    log "Waiting for Redis connection..."
    
    python << END
import redis
import time
import sys
from urllib.parse import urlparse

redis_url = "$REDIS_URL"
parsed = urlparse(redis_url)

for i in range(30):
    try:
        r = redis.Redis(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            db=int(parsed.path.lstrip('/')) if parsed.path else 0
        )
        r.ping()
        print("Redis connection successful!")
        sys.exit(0)
    except Exception as e:
        print(f"Redis unavailable, waiting... ({i+1}/30): {e}")
        time.sleep(2)

print("Redis connection failed after 30 attempts")
sys.exit(1)
END

    if [ $? -eq 0 ]; then
        log_success "Redis connection established"
    else
        log_warning "Redis connection failed, continuing without cache"
    fi
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    python manage.py migrate --noinput
    
    if [ $? -eq 0 ]; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        exit 1
    fi
}

# Function to collect static files
collect_static() {
    log "Collecting static files..."
    python manage.py collectstatic --noinput --clear
    
    if [ $? -eq 0 ]; then
        log_success "Static files collected"
    else
        log_warning "Static files collection failed, continuing..."
    fi
}

# Function to create superuser if needed
create_superuser() {
    if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
        log "Creating superuser..."
        python manage.py createsuperuser --noinput || log_warning "Superuser creation failed or user already exists"
    fi
}

# Function to initialize AI models
init_ai_models() {
    log "Initializing AI models..."
    
    # Create deployment directory
    mkdir -p "$DEPLOYMENT_DIR"
    
    # Run AI model initialization commands
    python manage.py setup_indonesian_nlp || log_warning "Indonesian NLP setup failed"
    
    # Check for existing deployments
    if [ -d "$DEPLOYMENT_DIR" ] && [ "$(ls -A $DEPLOYMENT_DIR)" ]; then
        log "Found existing model deployments:"
        ls -la "$DEPLOYMENT_DIR"
        
        # Validate existing deployments
        python manage.py deploy_model health || log_warning "Some deployments may be unhealthy"
    else
        log "No existing model deployments found"
    fi
    
    log_success "AI models initialization completed"
}

# Function to start Celery worker in background
start_celery_worker() {
    if [ "$START_CELERY_WORKER" = "true" ]; then
        log "Starting Celery worker..."
        celery -A horilla worker --loglevel=info --detach
        
        if [ $? -eq 0 ]; then
            log_success "Celery worker started"
        else
            log_warning "Celery worker failed to start"
        fi
    fi
}

# Function to start Celery beat scheduler
start_celery_beat() {
    if [ "$START_CELERY_BEAT" = "true" ]; then
        log "Starting Celery beat scheduler..."
        celery -A horilla beat --loglevel=info --detach
        
        if [ $? -eq 0 ]; then
            log_success "Celery beat scheduler started"
        else
            log_warning "Celery beat scheduler failed to start"
        fi
    fi
}

# Function to validate deployment environment
validate_environment() {
    log "Validating deployment environment..."
    
    # Check Python version
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    log "Python version: $python_version"
    
    # Check Django version
    django_version=$(python -c "import django; print(django.get_version())")
    log "Django version: $django_version"
    
    # Check available memory
    if command -v free >/dev/null 2>&1; then
        memory_info=$(free -h | grep '^Mem:' | awk '{print $2}')
        log "Available memory: $memory_info"
    fi
    
    # Check disk space
    if command -v df >/dev/null 2>&1; then
        disk_space=$(df -h /app | tail -1 | awk '{print $4}')
        log "Available disk space: $disk_space"
    fi
    
    # Validate Django settings
    python manage.py check --deploy || log_warning "Django deployment check found issues"
    
    log_success "Environment validation completed"
}

# Function to setup logging
setup_logging() {
    log "Setting up logging..."
    
    # Create log directories
    mkdir -p /app/logs
    
    # Set log file permissions
    touch /app/logs/django.log
    touch /app/logs/celery.log
    touch /app/logs/deployment.log
    
    log_success "Logging setup completed"
}

# Function to run health checks
run_health_checks() {
    log "Running health checks..."
    
    # Check Django application
    python -c "import django; django.setup(); from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', 'check'])" || {
        log_error "Django health check failed"
        exit 1
    }
    
    # Check AI services
    python manage.py deploy_model status || log_warning "AI deployment status check failed"
    
    log_success "Health checks completed"
}

# Main initialization function
init_container() {
    log "Starting AI Model Deployment Container Initialization..."
    
    setup_logging
    validate_environment
    wait_for_db
    wait_for_redis
    run_migrations
    collect_static
    create_superuser
    init_ai_models
    start_celery_worker
    start_celery_beat
    run_health_checks
    
    log_success "Container initialization completed successfully!"
}

# Signal handlers for graceful shutdown
handle_signal() {
    log "Received shutdown signal, cleaning up..."
    
    # Stop Celery processes
    pkill -f "celery worker" || true
    pkill -f "celery beat" || true
    
    # Wait for processes to stop
    sleep 5
    
    log_success "Cleanup completed"
    exit 0
}

trap handle_signal SIGTERM SIGINT

# Main execution
if [ "$1" = "init-only" ]; then
    # Run initialization only
    init_container
    log "Initialization completed. Exiting."
    exit 0
elif [ "$1" = "shell" ]; then
    # Start interactive shell
    init_container
    log "Starting interactive shell..."
    exec /bin/bash
elif [ "$1" = "manage" ]; then
    # Run Django management command
    shift
    init_container
    log "Running Django management command: $@"
    exec python manage.py "$@"
else
    # Normal startup
    init_container
    log "Starting application server..."
    exec "$@"
fi