#!/bin/bash

# AI Services POC - Docker Runner Script
# This script helps you run the POC using Docker

set -e

echo "🚀 AI Services POC - Docker Setup"
echo "================================="

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
    echo "✅ Docker is running"
}

# Function to build and run POC
run_poc() {
    echo "📦 Building Docker image..."
    docker-compose -f docker-compose.poc.yml build
    
    echo "🔧 Starting services..."
    docker-compose -f docker-compose.poc.yml up -d
    
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    echo "🏥 Checking health status..."
    docker-compose -f docker-compose.poc.yml ps
    
    echo ""
    echo "✅ POC is ready!"
    echo "🌐 Access the application at: http://localhost:8000"
    echo "📊 API Status: http://localhost:8000/api/status/"
    echo "🔍 Health Check: http://localhost:8000/health/"
    echo "⚙️  Admin Panel: http://localhost:8000/admin/"
    echo ""
    echo "📋 Available API Endpoints:"
    echo "   GET  /api/models/          - List AI models"
    echo "   POST /api/models/          - Create new model"
    echo "   POST /api/predict/         - Make predictions"
    echo "   POST /api/train/           - Train models"
    echo "   GET  /api/predictions/     - Prediction history"
    echo "   GET  /api/training/        - Training history"
    echo ""
    echo "🛑 To stop: docker-compose -f docker-compose.poc.yml down"
    echo "📝 To view logs: docker-compose -f docker-compose.poc.yml logs -f"
}

# Function to stop POC
stop_poc() {
    echo "🛑 Stopping POC services..."
    docker-compose -f docker-compose.poc.yml down
    echo "✅ POC stopped"
}

# Function to show logs
show_logs() {
    echo "📝 Showing POC logs..."
    docker-compose -f docker-compose.poc.yml logs -f
}

# Function to clean up
cleanup() {
    echo "🧹 Cleaning up Docker resources..."
    docker-compose -f docker-compose.poc.yml down -v
    docker system prune -f
    echo "✅ Cleanup completed"
}

# Main script logic
case "$1" in
    start)
        check_docker
        run_poc
        ;;
    stop)
        stop_poc
        ;;
    logs)
        show_logs
        ;;
    restart)
        stop_poc
        sleep 2
        check_docker
        run_poc
        ;;
    cleanup)
        cleanup
        ;;
    status)
        echo "📊 POC Status:"
        docker-compose -f docker-compose.poc.yml ps
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|cleanup}"
        echo ""
        echo "Commands:"
        echo "  start    - Build and start the POC"
        echo "  stop     - Stop the POC services"
        echo "  restart  - Restart the POC services"
        echo "  logs     - Show live logs"
        echo "  status   - Show service status"
        echo "  cleanup  - Stop and remove all containers/volumes"
        echo ""
        echo "Example: $0 start"
        exit 1
        ;;
esac