#!/bin/bash

# Horilla HR System Monitoring Setup Script
# This script sets up comprehensive monitoring and alerting infrastructure
# Designed for production deployment with SLA compliance

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MONITORING_DIR="$PROJECT_DIR/monitoring"
PROMETHEUS_DIR="$PROJECT_DIR/prometheus"
GRAFANA_DIR="$PROJECT_DIR/grafana"
LOG_DIR="/var/log/horilla"

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
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
    esac
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log "ERROR" "This script must be run as root for system-level setup"
        log "INFO" "Please run: sudo $0"
        exit 1
    fi
}

# Install required packages
install_dependencies() {
    log "INFO" "Installing monitoring dependencies..."
    
    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log "ERROR" "Cannot detect OS version"
        exit 1
    fi
    
    case $OS in
        "Ubuntu"*|"Debian"*)
            apt-get update
            apt-get install -y \
                curl \
                wget \
                jq \
                bc \
                htop \
                iotop \
                netstat-nat \
                postgresql-client \
                redis-tools \
                mailutils \
                sendmail \
                logrotate \
                cron
            ;;
        "CentOS"*|"Red Hat"*|"Rocky"*|"AlmaLinux"*)
            yum update -y
            yum install -y \
                curl \
                wget \
                jq \
                bc \
                htop \
                iotop \
                net-tools \
                postgresql \
                redis \
                mailx \
                sendmail \
                logrotate \
                cronie
            ;;
        "macOS"*|"Darwin"*)
            # For macOS, use Homebrew
            if ! command -v brew >/dev/null 2>&1; then
                log "ERROR" "Homebrew is required for macOS. Please install it first."
                exit 1
            fi
            
            brew install jq bc postgresql redis
            ;;
        *)
            log "WARN" "Unsupported OS: $OS. Please install dependencies manually."
            ;;
    esac
    
    log "INFO" "Dependencies installed successfully"
}

# Setup log directories and rotation
setup_logging() {
    log "INFO" "Setting up logging infrastructure..."
    
    # Create log directories
    mkdir -p "$LOG_DIR"
    mkdir -p "$LOG_DIR/monitoring"
    mkdir -p "$LOG_DIR/backup"
    mkdir -p "$LOG_DIR/alerts"
    
    # Set proper permissions
    chown -R www-data:www-data "$LOG_DIR" 2>/dev/null || chown -R $(whoami):$(whoami) "$LOG_DIR"
    chmod -R 755 "$LOG_DIR"
    
    # Setup logrotate configuration
    cat > /etc/logrotate.d/horilla << 'EOF'
/var/log/horilla/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        # Restart services if needed
        systemctl reload horilla-monitor 2>/dev/null || true
    endscript
}

/var/log/horilla/monitoring/*.log {
    hourly
    missingok
    rotate 168
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    size 100M
}

/var/log/horilla/backup/*.log {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
EOF
    
    log "INFO" "Logging infrastructure setup completed"
}

# Setup systemd service for monitoring
setup_systemd_service() {
    log "INFO" "Setting up systemd service for monitoring..."
    
    # Create systemd service file
    cat > /etc/systemd/system/horilla-monitor.service << EOF
[Unit]
Description=Horilla HR System Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$SCRIPT_DIR/monitor.sh --daemon
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

# Environment variables
Environment=PYTHONPATH=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=horilla.settings
EnvironmentFile=-$PROJECT_DIR/.env

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $PROJECT_DIR/media $PROJECT_DIR/static /tmp

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
    
    # Create backup service
    cat > /etc/systemd/system/horilla-backup.service << EOF
[Unit]
Description=Horilla HR System Backup
After=network.target

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$SCRIPT_DIR/backup.sh --auto
Environment=PYTHONPATH=$PROJECT_DIR
Environment=DJANGO_SETTINGS_MODULE=horilla.settings
EnvironmentFile=-$PROJECT_DIR/.env
EOF
    
    # Create backup timer
    cat > /etc/systemd/system/horilla-backup.timer << 'EOF'
[Unit]
Description=Run Horilla backup daily
Requires=horilla-backup.service

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=1800

[Install]
WantedBy=timers.target
EOF
    
    # Make scripts executable
    chmod +x "$SCRIPT_DIR/monitor.sh"
    chmod +x "$SCRIPT_DIR/backup.sh"
    chmod +x "$SCRIPT_DIR/restore.sh"
    chmod +x "$SCRIPT_DIR/deploy.sh"
    
    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable horilla-monitor.service
    systemctl enable horilla-backup.timer
    
    log "INFO" "Systemd services setup completed"
}

# Setup Prometheus node exporter
setup_node_exporter() {
    log "INFO" "Setting up Prometheus Node Exporter..."
    
    local node_exporter_version="1.7.0"
    local node_exporter_url="https://github.com/prometheus/node_exporter/releases/download/v${node_exporter_version}/node_exporter-${node_exporter_version}.linux-amd64.tar.gz"
    
    # Download and install node exporter
    cd /tmp
    wget -q "$node_exporter_url" -O node_exporter.tar.gz
    tar -xzf node_exporter.tar.gz
    
    # Move binary to system path
    mv "node_exporter-${node_exporter_version}.linux-amd64/node_exporter" /usr/local/bin/
    chmod +x /usr/local/bin/node_exporter
    
    # Create user for node exporter
    useradd --no-create-home --shell /bin/false node_exporter 2>/dev/null || true
    
    # Create systemd service
    cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=:9100
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable and start node exporter
    systemctl daemon-reload
    systemctl enable node_exporter
    systemctl start node_exporter
    
    # Cleanup
    rm -rf /tmp/node_exporter*
    
    log "INFO" "Node Exporter setup completed"
}

# Setup PostgreSQL monitoring
setup_postgres_monitoring() {
    log "INFO" "Setting up PostgreSQL monitoring..."
    
    # Install postgres_exporter
    local postgres_exporter_version="0.15.0"
    local postgres_exporter_url="https://github.com/prometheus-community/postgres_exporter/releases/download/v${postgres_exporter_version}/postgres_exporter-${postgres_exporter_version}.linux-amd64.tar.gz"
    
    cd /tmp
    wget -q "$postgres_exporter_url" -O postgres_exporter.tar.gz
    tar -xzf postgres_exporter.tar.gz
    
    # Move binary to system path
    mv "postgres_exporter-${postgres_exporter_version}.linux-amd64/postgres_exporter" /usr/local/bin/
    chmod +x /usr/local/bin/postgres_exporter
    
    # Create user for postgres exporter
    useradd --no-create-home --shell /bin/false postgres_exporter 2>/dev/null || true
    
    # Create environment file
    cat > /etc/default/postgres_exporter << 'EOF'
DATA_SOURCE_NAME="postgresql://horilla_user:horilla_password@localhost:5432/horilla_db?sslmode=disable"
PG_EXPORTER_WEB_LISTEN_ADDRESS=":9187"
PG_EXPORTER_WEB_TELEMETRY_PATH="/metrics"
EOF
    
    # Create systemd service
    cat > /etc/systemd/system/postgres_exporter.service << 'EOF'
[Unit]
Description=PostgreSQL Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=postgres_exporter
Group=postgres_exporter
Type=simple
EnvironmentFile=/etc/default/postgres_exporter
ExecStart=/usr/local/bin/postgres_exporter
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable postgres exporter
    systemctl daemon-reload
    systemctl enable postgres_exporter
    
    # Cleanup
    rm -rf /tmp/postgres_exporter*
    
    log "INFO" "PostgreSQL monitoring setup completed"
}

# Setup Redis monitoring
setup_redis_monitoring() {
    log "INFO" "Setting up Redis monitoring..."
    
    # Install redis_exporter
    local redis_exporter_version="1.55.0"
    local redis_exporter_url="https://github.com/oliver006/redis_exporter/releases/download/v${redis_exporter_version}/redis_exporter-v${redis_exporter_version}.linux-amd64.tar.gz"
    
    cd /tmp
    wget -q "$redis_exporter_url" -O redis_exporter.tar.gz
    tar -xzf redis_exporter.tar.gz
    
    # Move binary to system path
    mv "redis_exporter-v${redis_exporter_version}.linux-amd64/redis_exporter" /usr/local/bin/
    chmod +x /usr/local/bin/redis_exporter
    
    # Create user for redis exporter
    useradd --no-create-home --shell /bin/false redis_exporter 2>/dev/null || true
    
    # Create systemd service
    cat > /etc/systemd/system/redis_exporter.service << 'EOF'
[Unit]
Description=Redis Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=redis_exporter
Group=redis_exporter
Type=simple
ExecStart=/usr/local/bin/redis_exporter -redis.addr=redis://localhost:6379
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable redis exporter
    systemctl daemon-reload
    systemctl enable redis_exporter
    
    # Cleanup
    rm -rf /tmp/redis_exporter*
    
    log "INFO" "Redis monitoring setup completed"
}

# Setup health check endpoints in Django
setup_django_monitoring() {
    log "INFO" "Setting up Django monitoring endpoints..."
    
    # Add monitoring URLs to main urls.py
    local main_urls_file="$PROJECT_DIR/horilla/urls.py"
    
    if [ -f "$main_urls_file" ]; then
        # Check if monitoring URLs are already added
        if ! grep -q "monitoring.urls" "$main_urls_file"; then
            # Backup original file
            cp "$main_urls_file" "${main_urls_file}.backup"
            
            # Add monitoring URLs
            sed -i '/urlpatterns = \[/a\    path("health/", include("monitoring.urls")),' "$main_urls_file"
            
            # Add import if not present
            if ! grep -q "from django.urls import.*include" "$main_urls_file"; then
                sed -i '1i\from django.urls import path, include' "$main_urls_file"
            fi
            
            log "INFO" "Added monitoring URLs to Django configuration"
        else
            log "INFO" "Monitoring URLs already configured in Django"
        fi
    else
        log "WARN" "Django main urls.py not found at $main_urls_file"
    fi
    
    # Add monitoring app to INSTALLED_APPS
    local settings_file="$PROJECT_DIR/horilla/settings.py"
    
    if [ -f "$settings_file" ]; then
        if ! grep -q "'monitoring'" "$settings_file"; then
            # Backup original file
            cp "$settings_file" "${settings_file}.backup"
            
            # Add monitoring to INSTALLED_APPS
            sed -i "/INSTALLED_APPS = \[/a\    'monitoring'," "$settings_file"
            
            log "INFO" "Added monitoring app to Django INSTALLED_APPS"
        else
            log "INFO" "Monitoring app already in Django INSTALLED_APPS"
        fi
    else
        log "WARN" "Django settings.py not found at $settings_file"
    fi
}

# Setup alerting configuration
setup_alerting() {
    log "INFO" "Setting up alerting configuration..."
    
    # Create alerting configuration directory
    mkdir -p "$PROJECT_DIR/config/alerting"
    
    # Create alert configuration template
    cat > "$PROJECT_DIR/config/alerting/config.env.template" << 'EOF'
# Horilla HR System Alerting Configuration
# Copy this file to config.env and configure your alert channels

# Slack Integration
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Email Alerts
EMAIL_RECIPIENTS="admin@yourcompany.com,ops@yourcompany.com"
SMTP_SERVER="smtp.yourcompany.com"
SMTP_PORT="587"
SMTP_USERNAME="alerts@yourcompany.com"
SMTP_PASSWORD="your_smtp_password"

# Discord Integration
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK"

# PagerDuty Integration (for critical alerts)
PAGERDUTY_INTEGRATION_KEY="your_pagerduty_integration_key"

# Microsoft Teams Integration
TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK"

# Monitoring Thresholds
MONITOR_CHECK_INTERVAL="30"          # seconds
MONITOR_ALERT_COOLDOWN="300"         # seconds
MONITOR_MAX_RESPONSE_TIME="2000"     # milliseconds
MONITOR_MIN_DISK_SPACE="10"          # percentage
MONITOR_MAX_CPU_USAGE="80"           # percentage
MONITOR_MAX_MEMORY_USAGE="85"        # percentage

# Service Endpoints
WEB_ENDPOINT="http://localhost:8000"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_USER="horilla_user"
REDIS_HOST="localhost"
REDIS_PORT="6379"
ELASTICSEARCH_HOST="localhost"
ELASTICSEARCH_PORT="9200"
OLLAMA_HOST="localhost"
OLLAMA_PORT="11434"
N8N_HOST="localhost"
N8N_PORT="5678"
CHROMADB_HOST="localhost"
CHROMADB_PORT="8000"
EOF
    
    # Create alert test script
    cat > "$PROJECT_DIR/scripts/test_alerts.sh" << 'EOF'
#!/bin/bash

# Test alert channels configuration
# This script sends test alerts to verify configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load configuration
if [ -f "$PROJECT_DIR/config/alerting/config.env" ]; then
    source "$PROJECT_DIR/config/alerting/config.env"
else
    echo "Alert configuration not found. Please copy config.env.template to config.env and configure it."
    exit 1
fi

# Test Slack
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    echo "Testing Slack integration..."
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"Test alert from Horilla HR System - Slack integration working!"}' \
        "$SLACK_WEBHOOK_URL" && echo "Slack: OK" || echo "Slack: FAILED"
fi

# Test Discord
if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
    echo "Testing Discord integration..."
    curl -X POST -H 'Content-type: application/json' \
        --data '{"content":"Test alert from Horilla HR System - Discord integration working!"}' \
        "$DISCORD_WEBHOOK_URL" && echo "Discord: OK" || echo "Discord: FAILED"
fi

# Test Email
if [ -n "${EMAIL_RECIPIENTS:-}" ]; then
    echo "Testing Email integration..."
    echo "Test alert from Horilla HR System - Email integration working!" | \
        mail -s "Horilla Test Alert" "$EMAIL_RECIPIENTS" && echo "Email: OK" || echo "Email: FAILED"
fi

echo "Alert testing completed!"
EOF
    
    chmod +x "$PROJECT_DIR/scripts/test_alerts.sh"
    
    log "INFO" "Alerting configuration setup completed"
    log "INFO" "Please configure $PROJECT_DIR/config/alerting/config.env with your alert channels"
}

# Setup monitoring dashboard
setup_monitoring_dashboard() {
    log "INFO" "Setting up monitoring dashboard..."
    
    # Create simple monitoring dashboard
    cat > "$PROJECT_DIR/monitoring/dashboard.py" << 'EOF'
#!/usr/bin/env python3
"""
Simple monitoring dashboard for Horilla HR System
Provides a web interface to view system status and metrics
"""

import json
import subprocess
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class MonitoringHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_dashboard()
        elif parsed_path.path == '/api/status':
            self.serve_status_api()
        elif parsed_path.path == '/api/metrics':
            self.serve_metrics_api()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Horilla HR System Monitoring</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #2c3e50; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .status-ok { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-error { color: #e74c3c; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .timestamp { color: #7f8c8d; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Horilla HR System Monitoring</h1>
            <p>Real-time system health and performance metrics</p>
            <button class="refresh-btn" onclick="refreshData()">Refresh Data</button>
            <span class="timestamp" id="lastUpdate"></span>
        </div>
        
        <div class="metrics-grid" id="metricsGrid">
            <div class="metric-card">
                <div class="metric-title">Loading...</div>
                <div class="metric-value">Please wait</div>
            </div>
        </div>
    </div>
    
    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error:', error));
        }
        
        function updateDashboard(data) {
            const grid = document.getElementById('metricsGrid');
            grid.innerHTML = '';
            
            // System Status
            addMetricCard('System Status', data.system_status || 'Unknown', 
                         data.system_status === 'healthy' ? 'status-ok' : 'status-error');
            
            // Application Status
            addMetricCard('Application', data.application_status || 'Unknown',
                         data.application_status === 'running' ? 'status-ok' : 'status-error');
            
            // Database Status
            addMetricCard('Database', data.database_status || 'Unknown',
                         data.database_status === 'connected' ? 'status-ok' : 'status-error');
            
            // Cache Status
            addMetricCard('Redis Cache', data.cache_status || 'Unknown',
                         data.cache_status === 'connected' ? 'status-ok' : 'status-error');
            
            // CPU Usage
            const cpuUsage = data.cpu_usage || 0;
            addMetricCard('CPU Usage', cpuUsage + '%',
                         cpuUsage < 70 ? 'status-ok' : cpuUsage < 90 ? 'status-warning' : 'status-error');
            
            // Memory Usage
            const memUsage = data.memory_usage || 0;
            addMetricCard('Memory Usage', memUsage + '%',
                         memUsage < 80 ? 'status-ok' : memUsage < 95 ? 'status-warning' : 'status-error');
            
            // Disk Usage
            const diskUsage = data.disk_usage || 0;
            addMetricCard('Disk Usage', diskUsage + '%',
                         diskUsage < 80 ? 'status-ok' : diskUsage < 95 ? 'status-warning' : 'status-error');
            
            // Response Time
            const responseTime = data.response_time || 0;
            addMetricCard('Response Time', responseTime + 'ms',
                         responseTime < 500 ? 'status-ok' : responseTime < 2000 ? 'status-warning' : 'status-error');
            
            document.getElementById('lastUpdate').textContent = 'Last updated: ' + new Date().toLocaleString();
        }
        
        function addMetricCard(title, value, statusClass) {
            const grid = document.getElementById('metricsGrid');
            const card = document.createElement('div');
            card.className = 'metric-card';
            card.innerHTML = `
                <div class="metric-title">${title}</div>
                <div class="metric-value ${statusClass}">${value}</div>
            `;
            grid.appendChild(card);
        }
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
        
        // Initial load
        refreshData();
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_status_api(self):
        try:
            # Get system metrics
            status = self.get_system_status()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_metrics_api(self):
        try:
            # Get detailed metrics
            metrics = self.get_detailed_metrics()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())
        except Exception as e:
            self.send_error(500, str(e))
    
    def get_system_status(self):
        status = {
            'timestamp': datetime.now().isoformat(),
            'system_status': 'healthy',
            'application_status': 'unknown',
            'database_status': 'unknown',
            'cache_status': 'unknown',
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_usage': 0,
            'response_time': 0
        }
        
        try:
            # Check application health
            result = subprocess.run(['curl', '-f', 'http://localhost:8000/health/'], 
                                  capture_output=True, timeout=5)
            status['application_status'] = 'running' if result.returncode == 0 else 'error'
        except:
            status['application_status'] = 'error'
        
        try:
            # Get CPU usage
            result = subprocess.run(['top', '-bn1'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'Cpu(s)' in line:
                    cpu_usage = line.split()[1].replace('%us,', '')
                    status['cpu_usage'] = float(cpu_usage)
                    break
        except:
            pass
        
        try:
            # Get memory usage
            result = subprocess.run(['free'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                mem_line = lines[1].split()
                total = int(mem_line[1])
                used = int(mem_line[2])
                status['memory_usage'] = round((used / total) * 100, 1)
        except:
            pass
        
        try:
            # Get disk usage
            result = subprocess.run(['df', '/'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                disk_line = lines[1].split()
                usage = disk_line[4].replace('%', '')
                status['disk_usage'] = int(usage)
        except:
            pass
        
        return status
    
    def get_detailed_metrics(self):
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime': self.get_uptime(),
            'load_average': self.get_load_average(),
            'network_connections': self.get_network_connections(),
            'process_count': self.get_process_count()
        }
    
    def get_uptime(self):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return uptime_seconds
        except:
            return 0
    
    def get_load_average(self):
        try:
            with open('/proc/loadavg', 'r') as f:
                load_avg = f.readline().split()[:3]
                return [float(x) for x in load_avg]
        except:
            return [0, 0, 0]
    
    def get_network_connections(self):
        try:
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
            return len(result.stdout.split('\n')) - 1
        except:
            return 0
    
    def get_process_count(self):
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            return len(result.stdout.split('\n')) - 1
        except:
            return 0

def run_dashboard(port=8080):
    server = HTTPServer(('0.0.0.0', port), MonitoringHandler)
    print(f"Monitoring dashboard running on http://localhost:{port}")
    server.serve_forever()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_dashboard(port)
EOF
    
    chmod +x "$PROJECT_DIR/monitoring/dashboard.py"
    
    log "INFO" "Monitoring dashboard setup completed"
}

# Start monitoring services
start_monitoring_services() {
    log "INFO" "Starting monitoring services..."
    
    # Start node exporter
    systemctl start node_exporter
    
    # Start postgres exporter (if PostgreSQL is configured)
    if systemctl is-enabled postgres_exporter >/dev/null 2>&1; then
        systemctl start postgres_exporter
    fi
    
    # Start redis exporter (if Redis is configured)
    if systemctl is-enabled redis_exporter >/dev/null 2>&1; then
        systemctl start redis_exporter
    fi
    
    # Start horilla monitor
    systemctl start horilla-monitor
    
    # Start backup timer
    systemctl start horilla-backup.timer
    
    log "INFO" "Monitoring services started successfully"
}

# Show monitoring status
show_monitoring_status() {
    log "INFO" "Monitoring Services Status:"
    echo
    
    # Check service status
    services=("horilla-monitor" "node_exporter" "postgres_exporter" "redis_exporter")
    
    for service in "${services[@]}"; do
        if systemctl is-active "$service" >/dev/null 2>&1; then
            echo -e "  $service: ${GREEN}ACTIVE${NC}"
        else
            echo -e "  $service: ${RED}INACTIVE${NC}"
        fi
    done
    
    echo
    log "INFO" "Monitoring endpoints:"
    echo "  Health Check: http://localhost:8000/health/"
    echo "  Metrics: http://localhost:8000/metrics/"
    echo "  Node Exporter: http://localhost:9100/metrics"
    echo "  Postgres Exporter: http://localhost:9187/metrics"
    echo "  Redis Exporter: http://localhost:9121/metrics"
    echo "  Monitoring Dashboard: http://localhost:8080/"
    echo
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup comprehensive monitoring and alerting for Horilla HR System

OPTIONS:
    --install-deps         Install required dependencies
    --setup-logging        Setup logging infrastructure
    --setup-systemd        Setup systemd services
    --setup-exporters      Setup Prometheus exporters
    --setup-django         Setup Django monitoring endpoints
    --setup-alerting       Setup alerting configuration
    --setup-dashboard      Setup monitoring dashboard
    --start-services       Start all monitoring services
    --status               Show monitoring status
    --full-setup           Run complete setup (all options)
    -h, --help             Show this help message

Examples:
    $0 --full-setup        # Complete monitoring setup
    $0 --status            # Show current status
    $0 --start-services    # Start monitoring services

Note: This script requires root privileges for system-level setup.

EOF
}

# Main function
main() {
    local install_deps=false
    local setup_logging=false
    local setup_systemd=false
    local setup_exporters=false
    local setup_django=false
    local setup_alerting=false
    local setup_dashboard=false
    local start_services=false
    local show_status=false
    local full_setup=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --install-deps)
                install_deps=true
                shift
                ;;
            --setup-logging)
                setup_logging=true
                shift
                ;;
            --setup-systemd)
                setup_systemd=true
                shift
                ;;
            --setup-exporters)
                setup_exporters=true
                shift
                ;;
            --setup-django)
                setup_django=true
                shift
                ;;
            --setup-alerting)
                setup_alerting=true
                shift
                ;;
            --setup-dashboard)
                setup_dashboard=true
                shift
                ;;
            --start-services)
                start_services=true
                shift
                ;;
            --status)
                show_status=true
                shift
                ;;
            --full-setup)
                full_setup=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
            *)
                echo "Unexpected argument: $1" >&2
                exit 1
                ;;
        esac
    done
    
    # Show status and exit
    if [ "$show_status" = true ]; then
        show_monitoring_status
        exit 0
    fi
    
    # Full setup
    if [ "$full_setup" = true ]; then
        install_deps=true
        setup_logging=true
        setup_systemd=true
        setup_exporters=true
        setup_django=true
        setup_alerting=true
        setup_dashboard=true
        start_services=true
    fi
    
    # Check if any action is requested
    if [ "$install_deps" = false ] && [ "$setup_logging" = false ] && \
       [ "$setup_systemd" = false ] && [ "$setup_exporters" = false ] && \
       [ "$setup_django" = false ] && [ "$setup_alerting" = false ] && \
       [ "$setup_dashboard" = false ] && [ "$start_services" = false ]; then
        show_usage
        exit 1
    fi
    
    log "INFO" "Starting Horilla HR System monitoring setup"
    
    # Execute requested actions
    if [ "$install_deps" = true ]; then
        check_root
        install_dependencies
    fi
    
    if [ "$setup_logging" = true ]; then
        check_root
        setup_logging
    fi
    
    if [ "$setup_systemd" = true ]; then
        check_root
        setup_systemd_service
    fi
    
    if [ "$setup_exporters" = true ]; then
        check_root
        setup_node_exporter
        setup_postgres_monitoring
        setup_redis_monitoring
    fi
    
    if [ "$setup_django" = true ]; then
        setup_django_monitoring
    fi
    
    if [ "$setup_alerting" = true ]; then
        setup_alerting
    fi
    
    if [ "$setup_dashboard" = true ]; then
        setup_monitoring_dashboard
    fi
    
    if [ "$start_services" = true ]; then
        check_root
        start_monitoring_services
    fi
    
    log "INFO" "Monitoring setup completed successfully!"
    
    if [ "$full_setup" = true ]; then
        echo
        log "INFO" "Next steps:"
        echo "1. Configure alerting: $PROJECT_DIR/config/alerting/config.env"
        echo "2. Test alerts: $PROJECT_DIR/scripts/test_alerts.sh"
        echo "3. Access monitoring dashboard: http://localhost:8080/"
        echo "4. Check service status: $0 --status"
        echo
    fi
}

# Run main function
main "$@"