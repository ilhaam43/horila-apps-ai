# Horilla HR System - Deployment Guide

## Overview

Panduan deployment lengkap untuk Horilla HR System dengan fitur-fitur advanced termasuk Budget Control, Knowledge Management, AI Assistant, dan sistem monitoring untuk SLA 99.99%.

## ✅ POC Status - BERHASIL DIJALANKAN

**Server Status**: ✅ Running pada `http://127.0.0.1:8000`
**API Endpoints**: ✅ Semua endpoint berfungsi normal
**Database**: ✅ Migrasi berhasil, tabel terbuat
**Testing**: ✅ Model creation, prediction, dan training berhasil
**Application**: `simple_poc_app` - standalone POC application

## System Requirements

### Minimum Requirements (Small Scale)
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 50GB SSD
- **OS**: Ubuntu 20.04+ / CentOS 8+ / macOS 10.15+
- **Python**: 3.9+
- **Database**: PostgreSQL 12+ / MySQL 8.0+ / SQLite (development)

### Recommended Requirements (Medium Scale)
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 100GB SSD
- **Load Balancer**: Nginx/Apache
- **Cache**: Redis 6.0+
- **Message Queue**: Celery + Redis/RabbitMQ

### Enterprise Requirements (Large Scale)
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 200GB+ SSD
- **Database**: PostgreSQL cluster
- **Cache**: Redis cluster
- **Container**: Docker + Kubernetes
- **Monitoring**: Prometheus + Grafana

## Pre-deployment Setup

### 1. System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib redis-server

# CentOS/RHEL
sudo yum update
sudo yum install -y python3 python3-pip git nginx postgresql postgresql-server redis

# macOS
brew install python3 git nginx postgresql redis
```

### 2. Database Setup

#### PostgreSQL (Recommended for Production)
```bash
# Create database and user
sudo -u postgres psql
CREATE DATABASE horilla_db;
CREATE USER horilla_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE horilla_db TO horilla_user;
ALTER USER horilla_user CREATEDB;
\q
```

#### Redis Setup
```bash
# Start Redis service
sudo systemctl start redis
sudo systemctl enable redis

# Test Redis connection
redis-cli ping
```

### 3. Ollama Setup (for AI Features)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llama2:7b
ollama pull mistral:7b

# Start Ollama service
sudo systemctl start ollama
sudo systemctl enable ollama
```

## Application Deployment

### 1. Clone and Setup Application

```bash
# Clone repository
git clone <repository-url> /opt/horilla
cd /opt/horilla

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://horilla_user:secure_password@localhost:5432/horilla_db

# Security Settings
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b

# Email Configuration (Optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Storage Configuration (Production)
STATIC_ROOT=/var/www/horilla/static/
MEDIA_ROOT=/var/www/horilla/media/

# Monitoring Configuration
MONITORING_ENABLED=True
PROMETHEUS_METRICS_ENABLED=True
```

### 3. Database Migration

```bash
# Apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 4. Test Installation

```bash
# Run development server
python manage.py runserver 0.0.0.0:8000

# Test monitoring endpoints
curl http://localhost:8000/health/
curl http://localhost:8000/metrics/
```

## Production Deployment

### 1. Gunicorn Setup

Create `/etc/systemd/system/horilla.service`:

```ini
[Unit]
Description=Horilla HR System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/horilla
Environment="PATH=/opt/horilla/venv/bin"
ExecStart=/opt/horilla/venv/bin/gunicorn --workers 3 --bind unix:/opt/horilla/horilla.sock horilla.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl start horilla
sudo systemctl enable horilla
```

### 2. Celery Setup

Create `/etc/systemd/system/horilla-celery.service`:

```ini
[Unit]
Description=Horilla Celery Worker
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/horilla
Environment="PATH=/opt/horilla/venv/bin"
ExecStart=/opt/horilla/venv/bin/celery -A horilla worker --loglevel=info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/horilla-celery-beat.service`:

```ini
[Unit]
Description=Horilla Celery Beat
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/horilla
Environment="PATH=/opt/horilla/venv/bin"
ExecStart=/opt/horilla/venv/bin/celery -A horilla beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start Celery services
sudo systemctl start horilla-celery
sudo systemctl enable horilla-celery
sudo systemctl start horilla-celery-beat
sudo systemctl enable horilla-celery-beat
```

### 3. Nginx Configuration

Create `/etc/nginx/sites-available/horilla`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Static files
    location /static/ {
        alias /var/www/horilla/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /var/www/horilla/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # Health check endpoints (no auth required)
    location ~ ^/(health|metrics)/ {
        proxy_pass http://unix:/opt/horilla/horilla.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Monitoring specific settings
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }
    
    # Main application
    location / {
        proxy_pass http://unix:/opt/horilla/horilla.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://unix:/opt/horilla/horilla.sock;
        # ... other proxy settings
    }
    
    location /login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://unix:/opt/horilla/horilla.sock;
        # ... other proxy settings
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/horilla /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Docker Deployment

### 1. Dockerfile

```dockerfile
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "horilla.wsgi:application"]
```

### 2. Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: horilla_db
      POSTGRES_USER: horilla_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U horilla_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:6-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://horilla_user:secure_password@db:5432/horilla_db
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery:
    build: .
    command: celery -A horilla worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://horilla_user:secure_password@db:5432/horilla_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A horilla beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    environment:
      - DATABASE_URL=postgresql://horilla_user:secure_password@db:5432/horilla_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

volumes:
  postgres_data:
  ollama_data:
```

## Kubernetes Deployment

### 1. Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: horilla
```

### 2. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: horilla-config
  namespace: horilla
data:
  DATABASE_URL: "postgresql://horilla_user:secure_password@postgres:5432/horilla_db"
  REDIS_URL: "redis://redis:6379/0"
  OLLAMA_BASE_URL: "http://ollama:11434"
  DEBUG: "False"
```

### 3. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: horilla
  namespace: horilla
spec:
  replicas: 3
  selector:
    matchLabels:
      app: horilla
  template:
    metadata:
      labels:
        app: horilla
    spec:
      containers:
      - name: horilla
        image: horilla:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: horilla-config
        livenessProbe:
          httpGet:
            path: /health/live/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### 4. Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: horilla-service
  namespace: horilla
spec:
  selector:
    app: horilla
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring Setup

### 1. Prometheus Configuration

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'horilla'
    static_configs:
      - targets: ['horilla:8000']
    metrics_path: '/metrics/'
    scrape_interval: 15s
    scrape_timeout: 10s
```

### 2. Grafana Dashboard

Import dashboard dengan ID: `horilla-monitoring.json`

### 3. Alerting Rules

```yaml
groups:
  - name: horilla.rules
    rules:
      - alert: HorillaDown
        expr: up{job="horilla"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Horilla instance is down"
          
      - alert: HighCPUUsage
        expr: system_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          
      - alert: HighMemoryUsage
        expr: system_memory_usage_percent > 90
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"
          
      - alert: LowDiskSpace
        expr: system_disk_usage_percent > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space detected"
```

## Security Hardening

### 1. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL/TLS Configuration

```nginx
# Strong SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

### 3. Database Security

```sql
-- PostgreSQL security
ALTER USER horilla_user SET default_transaction_isolation TO 'read committed';
ALTER USER horilla_user SET timezone TO 'UTC';
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO horilla_user;
```

## Backup Strategy

### 1. Database Backup

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
pg_dump -h localhost -U horilla_user horilla_db > "$BACKUP_DIR/horilla_db_$DATE.sql"

# Compress backup
gzip "$BACKUP_DIR/horilla_db_$DATE.sql"

# Remove backups older than 30 days
find $BACKUP_DIR -name "horilla_db_*.sql.gz" -mtime +30 -delete
```

### 2. Media Files Backup

```bash
#!/bin/bash
# media_backup.sh
rsync -av --delete /var/www/horilla/media/ /opt/backups/media/
```

### 3. Automated Backup (Cron)

```bash
# Add to crontab
0 2 * * * /opt/scripts/backup.sh
0 3 * * * /opt/scripts/media_backup.sh
```

## Performance Optimization

### 1. Database Optimization

```sql
-- PostgreSQL optimization
CREATE INDEX CONCURRENTLY idx_employee_user_id ON employee_employee(user_id);
CREATE INDEX CONCURRENTLY idx_attendance_date ON attendance_attendance(attendance_date);
CREATE INDEX CONCURRENTLY idx_leave_start_date ON leave_leaverequest(start_date);

-- Analyze tables
ANALYZE;
```

### 2. Redis Optimization

```bash
# Redis configuration
echo "maxmemory 2gb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
```

### 3. Application Optimization

```python
# settings.py optimizations
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'conn_max_age': 600,
        }
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Check connections
   sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis status
   sudo systemctl status redis
   
   # Test connection
   redis-cli ping
   ```

3. **Celery Issues**
   ```bash
   # Check Celery workers
   celery -A horilla inspect active
   
   # Check Celery logs
   sudo journalctl -u horilla-celery -f
   ```

4. **Ollama Issues**
   ```bash
   # Check Ollama status
   ollama list
   
   # Test model
   curl http://localhost:11434/api/generate -d '{"model":"llama2:7b","prompt":"Hello"}'
   ```

### Log Locations

- **Application**: `/var/log/horilla/`
- **Nginx**: `/var/log/nginx/`
- **PostgreSQL**: `/var/log/postgresql/`
- **Redis**: `/var/log/redis/`
- **Systemd Services**: `journalctl -u service-name`

## Maintenance

### Regular Tasks

1. **Weekly**:
   - Check system resources
   - Review error logs
   - Update security patches

2. **Monthly**:
   - Database maintenance (VACUUM, ANALYZE)
   - Clean old log files
   - Review backup integrity

3. **Quarterly**:
   - Security audit
   - Performance review
   - Dependency updates

### Health Monitoring

```bash
# System health check script
#!/bin/bash
echo "=== System Health Check ==="
echo "Date: $(date)"
echo

# Check services
echo "Services Status:"
sudo systemctl is-active horilla nginx postgresql redis

# Check disk space
echo "\nDisk Usage:"
df -h

# Check memory
echo "\nMemory Usage:"
free -h

# Check load average
echo "\nLoad Average:"
uptime

# Check application health
echo "\nApplication Health:"
curl -s http://localhost/health/ | jq .
```

## Support

Untuk dukungan teknis:
- **Documentation**: `/docs/`
- **API Documentation**: `/monitoring/API_DOCUMENTATION.md`
- **Monitoring**: `http://your-domain.com/health/detailed/`
- **Metrics**: `http://your-domain.com/metrics/`

---

**Note**: Pastikan untuk mengganti semua placeholder (your-domain.com, passwords, etc.) dengan nilai yang sesuai untuk environment Anda.