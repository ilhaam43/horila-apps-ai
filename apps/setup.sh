#!/bin/bash

# Horilla HR System - Setup Script
# Script untuk instalasi dan konfigurasi otomatis

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.8"
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "Python $PYTHON_VERSION detected"
            return 0
        else
            print_error "Python $PYTHON_VERSION detected, but Python 3.8+ is required"
            return 1
        fi
    else
        print_error "Python 3 is not installed"
        return 1
    fi
}

# Function to setup virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing old one..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Virtual environment created and activated"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed from requirements.txt"
    else
        print_warning "requirements.txt not found. Installing core dependencies..."
        pip install Django==4.2.21 djangorestframework django-cors-headers
        pip install celery redis psycopg2-binary Pillow python-dateutil
        pip install requests pandas numpy scikit-learn nltk transformers
        pip install chromadb langchain sentence-transformers
        pip install prometheus-client gunicorn whitenoise
        print_success "Core dependencies installed"
    fi
}

# Function to setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.dist" ]; then
            cp .env.dist .env
            print_success "Environment file created from template"
        else
            # Create basic .env file
            cat > .env << EOF
# Django Configuration
SECRET_KEY=django-insecure-$(openssl rand -base64 32)
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
DATABASE_URL=sqlite:///db.sqlite3

# AI Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security Settings
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
EOF
            print_success "Basic environment file created"
        fi
    else
        print_warning "Environment file already exists"
    fi
}

# Function to setup database
setup_database() {
    print_status "Setting up database..."
    
    # Make migrations
    python manage.py makemigrations
    
    # Apply migrations
    python manage.py migrate
    
    print_success "Database setup completed"
}

# Function to collect static files
collect_static() {
    print_status "Collecting static files..."
    
    python manage.py collectstatic --noinput
    
    print_success "Static files collected"
}

# Function to create superuser
create_superuser() {
    print_status "Creating superuser..."
    
    echo "Please create an admin user for the system:"
    python manage.py createsuperuser
    
    print_success "Superuser created"
}

# Function to run tests
run_tests() {
    print_status "Running system tests..."
    
    python manage.py check
    
    print_success "System check completed"
}

# Function to setup Ollama (optional)
setup_ollama() {
    print_status "Checking Ollama installation..."
    
    if command_exists ollama; then
        print_success "Ollama is already installed"
        
        # Check if Ollama service is running
        if pgrep -x "ollama" > /dev/null; then
            print_success "Ollama service is running"
        else
            print_status "Starting Ollama service..."
            ollama serve &
            sleep 5
            print_success "Ollama service started"
        fi
        
        # Download required models
        print_status "Downloading AI models..."
        ollama pull llama2 || print_warning "Failed to download llama2 model"
        
    else
        print_warning "Ollama is not installed. AI features will be limited."
        echo "To install Ollama, run: curl -fsSL https://ollama.ai/install.sh | sh"
    fi
}

# Function to setup Redis (optional)
setup_redis() {
    print_status "Checking Redis installation..."
    
    if command_exists redis-server; then
        print_success "Redis is installed"
        
        # Check if Redis is running
        if pgrep -x "redis-server" > /dev/null; then
            print_success "Redis service is running"
        else
            print_status "Starting Redis service..."
            redis-server --daemonize yes
            print_success "Redis service started"
        fi
    else
        print_warning "Redis is not installed. Background tasks will be limited."
        echo "To install Redis:"
        echo "  macOS: brew install redis"
        echo "  Ubuntu: sudo apt install redis-server"
    fi
}

# Function to display final instructions
show_final_instructions() {
    echo ""
    echo "======================================"
    print_success "Horilla HR System Setup Complete!"
    echo "======================================"
    echo ""
    echo "To start the application:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Start the server: python manage.py runserver"
    echo "  3. Open browser: http://127.0.0.1:8000/"
    echo ""
    echo "Admin Panel: http://127.0.0.1:8000/admin/"
    echo "Health Check: http://127.0.0.1:8000/health/"
    echo "Metrics: http://127.0.0.1:8000/metrics/"
    echo ""
    echo "Optional Background Services:"
    echo "  - Celery Worker: celery -A horilla worker --loglevel=info"
    echo "  - Celery Beat: celery -A horilla beat --loglevel=info"
    echo ""
    echo "Documentation:"
    echo "  - Installation Guide: PANDUAN_INSTALASI.md"
    echo "  - Quick Start: QUICK_START.md"
    echo "  - Deployment Guide: DEPLOYMENT_GUIDE.md"
    echo ""
}

# Main setup function
main() {
    echo "======================================"
    echo "    Horilla HR System Setup Script"
    echo "======================================"
    echo ""
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! check_python; then
        print_error "Python 3.8+ is required. Please install Python and try again."
        exit 1
    fi
    
    if ! command_exists pip; then
        print_error "pip is not installed. Please install pip and try again."
        exit 1
    fi
    
    # Setup steps
    setup_venv
    install_dependencies
    setup_env
    setup_database
    collect_static
    
    # Optional components
    setup_ollama
    setup_redis
    
    # System verification
    run_tests
    
    # Create superuser (interactive)
    read -p "Do you want to create a superuser now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_superuser
    fi
    
    # Show final instructions
    show_final_instructions
}

# Run main function
main "$@"