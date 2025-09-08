#!/bin/bash

# Production Deployment Script for Horilla
# This script helps configure the application for production deployment

set -e  # Exit on any error

echo "🚀 Starting Horilla Production Deployment Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    cp .env.example .env
    print_warning "Please edit .env file with your production settings before continuing."
    exit 1
fi

# Check if DEBUG is set to False
if grep -q "DEBUG=True" .env; then
    print_error "DEBUG is set to True in .env file. This is not safe for production!"
    print_warning "Please set DEBUG=False in your .env file."
    exit 1
fi

print_status "Environment configuration validated ✓"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p static
mkdir -p media
mkdir -p staticfiles

# Set proper permissions
print_status "Setting directory permissions..."
chmod 755 logs
chmod 755 static
chmod 755 media
chmod 755 staticfiles

# Install/update dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Run database migrations
print_status "Running database migrations..."
python manage.py migrate

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
print_status "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Please create one:')
    exit(1)
else:
    print('Superuser exists ✓')
"

# Optimize database
print_status "Optimizing database..."
python manage.py optimize_database --create-indexes --vacuum

# Run security checks
print_status "Running Django security checks..."
python manage.py check --deploy

# Test server startup
print_status "Testing server startup..."
timeout 10s python manage.py runserver 0.0.0.0:8000 --noreload &
SERVER_PID=$!
sleep 5

if kill -0 $SERVER_PID 2>/dev/null; then
    print_status "Server startup test successful ✓"
    kill $SERVER_PID
else
    print_error "Server failed to start properly"
    exit 1
fi

print_status "🎉 Production deployment setup completed successfully!"
print_warning "Remember to:"
echo "  1. Configure your web server (nginx/apache)"
echo "  2. Set up SSL certificates"
echo "  3. Configure firewall rules"
echo "  4. Set up monitoring and backups"
echo "  5. Review security settings in .env file"

print_status "To start the production server, use:"
echo "  gunicorn horilla.wsgi:application --bind 0.0.0.0:8000 --workers 3"