# Panduan Instalasi Komprehensif Horilla HR System

## Daftar Isi

1. [Pengenalan Sistem](#pengenalan-sistem)
2. [Persyaratan Sistem](#persyaratan-sistem)
3. [Persiapan Lingkungan](#persiapan-lingkungan)
4. [Instalasi Aplikasi](#instalasi-aplikasi)
5. [Konfigurasi Sistem](#konfigurasi-sistem)
6. [Menjalankan Aplikasi](#menjalankan-aplikasi)
7. [Verifikasi Instalasi](#verifikasi-instalasi)
8. [Panduan Operasional](#panduan-operasional)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)
11. [Deployment Production](#deployment-production)

---

## Pengenalan Sistem

### Tentang Horilla HR System

Horilla HR System adalah platform manajemen sumber daya manusia (HRMS) yang komprehensif dan modern, dilengkapi dengan teknologi AI dan automasi untuk memudahkan pengelolaan karyawan, rekrutmen, dan operasional HR.

### Arsitektur Sistem

- **Backend**: Django 4.2.21 dengan Python 3.9+
- **Database**: SQLite (development) / PostgreSQL (production)
- **Cache**: Redis untuk session dan caching
- **Task Queue**: Celery dengan Redis broker
- **AI Engine**: Ollama untuk LLM, ChromaDB untuk vector storage
- **Frontend**: HTML/CSS/JavaScript dengan Bootstrap 5
- **Monitoring**: Prometheus metrics dan health checks

### Fitur Utama

- ✅ **Manajemen Karyawan**: Profil lengkap, data personal, riwayat kerja
- ✅ **Sistem Absensi**: Real-time tracking dengan geofencing
- ✅ **Manajemen Cuti**: Workflow persetujuan otomatis
- ✅ **Rekrutmen Cerdas**: AI-powered CV screening dan ranking
- ✅ **Payroll**: Perhitungan gaji otomatis dan slip gaji digital
- ✅ **Performance Management**: Evaluasi kinerja dan goal tracking
- ✅ **Budget Control**: Monitoring anggaran real-time
- ✅ **Knowledge Management**: AI Assistant dengan RAG system
- ✅ **Indonesian NLP**: Processing bahasa Indonesia
- ✅ **Monitoring & Analytics**: Dashboard real-time dengan insights

---

## Persyaratan Sistem

### Minimum Requirements

| Komponen | Minimum | Recommended |
|----------|---------|-------------|
| **OS** | macOS 10.15+, Ubuntu 18.04+, Windows 10+ | macOS 12+, Ubuntu 20.04+, Windows 11 |
| **Python** | 3.8+ | 3.9+ atau 3.10+ |
| **RAM** | 4GB | 8GB+ |
| **Storage** | 10GB | 20GB+ SSD |
| **CPU** | 2 cores | 4+ cores |
| **Network** | Broadband internet | Stable broadband |

### Software Dependencies

#### Core Requirements
- **Python 3.9+** dengan pip
- **Git** untuk version control
- **Node.js 14+** untuk frontend assets
- **Redis** untuk caching dan task queue
- **SQLite** (included) atau **PostgreSQL** untuk production

#### AI/ML Requirements
- **Ollama** untuk Large Language Models
- **ChromaDB** untuk vector database
- **Sentence Transformers** untuk embeddings
- **NLTK** untuk natural language processing

#### Optional Services
- **Docker** untuk containerized deployment
- **Nginx** untuk reverse proxy (production)
- **Prometheus** untuk monitoring
- **Grafana** untuk visualization

---

## Persiapan Lingkungan

### 1. Install Python 3.9+

#### macOS
```bash
# Menggunakan Homebrew (recommended)
brew install python@3.10

# Atau menggunakan pyenv untuk multiple versions
brew install pyenv
pyenv install 3.10.12
pyenv global 3.10.12
```

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install Python 3.10
sudo apt install python3.10 python3.10-pip python3.10-venv python3.10-dev

# Install build essentials
sudo apt install build-essential libpq-dev libffi-dev libssl-dev
```

#### Windows
```powershell
# Download dari https://www.python.org/downloads/
# Atau menggunakan Chocolatey
choco install python --version=3.10.11

# Atau menggunakan winget
winget install Python.Python.3.10
```

### 2. Install Git

#### macOS
```bash
brew install git
```

#### Ubuntu/Debian
```bash
sudo apt install git
```

#### Windows
```powershell
# Download dari https://git-scm.com/download/win
# Atau menggunakan winget
winget install Git.Git
```

### 3. Install Node.js (untuk Frontend Assets)

#### macOS
```bash
brew install node@18
```

#### Ubuntu/Debian
```bash
# Install NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### Windows
```powershell
# Download dari https://nodejs.org/
# Atau menggunakan winget
winget install OpenJS.NodeJS
```

### 4. Install Redis

#### macOS
```bash
brew install redis
brew services start redis
```

#### Ubuntu/Debian
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

#### Windows
```powershell
# Download dari https://github.com/microsoftarchive/redis/releases
# Atau menggunakan WSL dengan Ubuntu
```

### 5. Install Ollama (untuk AI Features)

#### macOS/Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows
```powershell
# Download dari https://ollama.ai/download/windows
```

---

## Instalasi Aplikasi

### 1. Persiapan Direktori

```bash
# Buat direktori untuk aplikasi
mkdir -p ~/horilla-hr-system
cd ~/horilla-hr-system

# Clone repository (jika menggunakan Git)
# git clone <repository-url> .

# Atau copy semua file aplikasi ke direktori ini
```

### 2. Setup Virtual Environment

```bash
# Buat virtual environment
python3 -m venv venv

# Aktifkan virtual environment
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Upgrade pip ke versi terbaru
pip install --upgrade pip setuptools wheel
```

### 3. Install Python Dependencies

```bash
# Install dari requirements.txt (recommended)
pip install -r requirements.txt

# Jika requirements.txt tidak ada, install manual:
pip install Django==4.2.21
pip install djangorestframework==3.14.0
pip install django-cors-headers==4.3.1
pip install django-environ==0.11.2
pip install django-filter==23.3
pip install django-simple-history==3.4.0
pip install celery==5.3.4
pip install redis==5.0.1
pip install psycopg2-binary==2.9.9
pip install Pillow==10.1.0
pip install gunicorn==21.2.0
pip install whitenoise==6.6.0

# AI/ML Dependencies
pip install chromadb==0.4.15
pip install langchain==0.0.350
pip install sentence-transformers==2.2.2
pip install faiss-cpu==1.7.4
pip install nltk==3.8.1
pip install transformers==4.35.2
pip install torch==2.1.1
pip install numpy==1.24.4
pip install pandas==2.0.3
pip install scikit-learn==1.3.2

# Document Processing
pip install PyPDF2==3.0.1
pip install python-docx==0.8.11
pip install python-pptx==0.6.21

# Monitoring
pip install prometheus-client==0.19.0
```

### 4. Install Frontend Dependencies

```bash
# Install Node.js dependencies
npm install

# Atau install manual jika package.json tidak lengkap
npm install bootstrap@5.3.2
npm install jquery@3.7.1
npm install alpinejs@3.13.3
npm install select2@4.1.0-rc.0
```

### 5. Setup Ollama Models

```bash
# Start Ollama service
ollama serve &

# Download required models
ollama pull phi3:mini        # Lightweight model (recommended)
ollama pull llama2:7b        # Alternative model
ollama pull mistral:7b       # Another alternative

# Verify installation
ollama list
```

---

## Konfigurasi Sistem

### 1. Environment Configuration

```bash
# Copy template environment file
cp .env.dist .env

# Edit konfigurasi
nano .env  # atau gunakan editor favorit Anda
```

#### Konfigurasi Development (.env)
```env
# Django Core Settings
DEBUG=True
SECRET_KEY=django-insecure-your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Database Configuration
DATABASE_URL=sqlite:///db.sqlite3
# Untuk PostgreSQL: DATABASE_URL=postgresql://user:password@localhost:5432/horilla_db

# Time Zone
TIME_ZONE=Asia/Jakarta

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# AI Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=phi3:mini
SLM_TEXT_MODEL=gpt2
SLM_QA_MODEL=t5-small
SLM_SUMMARY_MODEL=t5-small
SLM_INDONESIAN_MODEL=gpt2
SLM_MAX_RESPONSE_LENGTH=300
SLM_USE_INDONESIAN=True
CHATBOT_MAX_CONTEXT_LENGTH=2000
CHATBOT_SIMILARITY_THRESHOLD=0.3

# Email Configuration (Development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Logging
LOG_LEVEL=INFO

# Security (Development)
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

### 2. Database Setup

```bash
# Buat direktori logs
mkdir -p logs

# Generate dan apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (admin account)
python manage.py createsuperuser
# Atau gunakan command khusus Horilla:
python manage.py createhorillauser --first_name Admin --last_name User --username admin --password admin123 --email admin@company.com --phone 1234567890
```

### 3. Static Files Setup

```bash
# Collect static files
python manage.py collectstatic --noinput

# Build frontend assets (jika menggunakan Laravel Mix)
npm run development
```

### 4. Initial Data Setup

```bash
# Load initial data (jika ada fixtures)
python manage.py loaddata initial_data.json

# Atau jalankan setup script
python manage.py setup_initial_data
```

---

## Menjalankan Aplikasi

### 1. Development Mode

#### Single Process (Simple)
```bash
# Pastikan virtual environment aktif
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate    # Windows

# Jalankan development server
python manage.py runserver 127.0.0.1:8000

# Server akan berjalan di http://127.0.0.1:8000/
```

#### Multi Process (Full Features)

**Terminal 1 - Django Server**
```bash
source venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

**Terminal 2 - Celery Worker**
```bash
source venv/bin/activate
celery -A horilla worker --loglevel=info --concurrency=4
```

**Terminal 3 - Celery Beat (Scheduler)**
```bash
source venv/bin/activate
celery -A horilla beat --loglevel=info
```

**Terminal 4 - Ollama Service**
```bash
ollama serve
```

### 2. Production Mode

#### Using Gunicorn
```bash
# Install gunicorn (sudah termasuk di requirements.txt)
pip install gunicorn

# Jalankan dengan gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 horilla.wsgi:application
```

#### Using Docker
```bash
# Build Docker image
docker build -t horilla-hr:latest .

# Run container
docker run -d -p 8000:8000 --name horilla-hr horilla-hr:latest
```

#### Using Docker Compose
```bash
# Jalankan semua services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Main Application** | http://127.0.0.1:8000/ | Web interface utama |
| **Admin Panel** | http://127.0.0.1:8000/admin/ | Django admin interface |
| **API Documentation** | http://127.0.0.1:8000/api/docs/ | Swagger API docs |
| **Health Check** | http://127.0.0.1:8000/health/ | System health status |
| **Metrics** | http://127.0.0.1:8000/metrics/ | Prometheus metrics |
| **AI Services** | http://127.0.0.1:8000/api/ai/ | AI endpoints |

---

## Verifikasi Instalasi

### 1. System Health Check

```bash
# Django system check
python manage.py check --deploy

# Database connectivity
python manage.py dbshell

# Static files check
python manage.py findstatic admin/css/base.css

# Cache connectivity
python manage.py shell -c "from django.core.cache import cache; print(cache.get('test') or 'Cache OK')"
```

### 2. Service Connectivity Tests

```bash
# Test Redis connection
redis-cli ping

# Test Ollama connection
curl http://localhost:11434/api/tags

# Test application health
curl http://127.0.0.1:8000/health/

# Test API endpoints
curl -H "Content-Type: application/json" http://127.0.0.1:8000/api/
```

### 3. Functional Tests

```bash
# Run Django tests
python manage.py test --verbosity=2

# Run specific app tests
python manage.py test employee --verbosity=2
python manage.py test ai_services --verbosity=2

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### 4. Web Interface Verification

1. **Login Test**
   - Akses http://127.0.0.1:8000/
   - Login dengan superuser credentials
   - Verifikasi dashboard loading

2. **Module Tests**
   - Employee Management: Tambah/edit karyawan
   - Attendance: Test clock in/out
   - Leave Management: Submit leave request
   - Knowledge Base: Upload dan search dokumen
   - AI Assistant: Test chat functionality

3. **Admin Panel Test**
   - Akses http://127.0.0.1:8000/admin/
   - Verifikasi semua models accessible
   - Test CRUD operations

### 5. Performance Verification

```bash
# Check memory usage
ps aux | grep python

# Check database queries
python manage.py shell -c "from django.db import connection; print(len(connection.queries))"

# Load testing (install apache2-utils)
ab -n 100 -c 10 http://127.0.0.1:8000/
```

---

## Panduan Operasional

### 1. Prosedur Startup Harian

```bash
#!/bin/bash
# startup.sh - Daily startup script

# Activate virtual environment
source venv/bin/activate

# Check system health
python manage.py check

# Start Redis (if not running)
redis-server --daemonize yes

# Start Ollama
ollama serve &

# Start Celery worker
celery -A horilla worker --detach --loglevel=info

# Start Celery beat
celery -A horilla beat --detach --loglevel=info

# Start Django server
python manage.py runserver 127.0.0.1:8000
```

### 2. Backup Procedures

#### Database Backup
```bash
# SQLite backup
cp db.sqlite3 backups/db_$(date +%Y%m%d_%H%M%S).sqlite3

# PostgreSQL backup
pg_dump horilla_db > backups/horilla_$(date +%Y%m%d_%H%M%S).sql
```

#### Media Files Backup
```bash
# Backup media files
tar -czf backups/media_$(date +%Y%m%d_%H%M%S).tar.gz media/
```

#### Full System Backup
```bash
#!/bin/bash
# backup.sh - Full system backup

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Database
cp db.sqlite3 $BACKUP_DIR/

# Media files
cp -r media/ $BACKUP_DIR/

# Configuration
cp .env $BACKUP_DIR/

# Logs
cp -r logs/ $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### 3. Monitoring dan Maintenance

#### Log Monitoring
```bash
# Monitor Django logs
tail -f logs/django.log

# Monitor Celery logs
tail -f logs/celery.log

# Monitor system performance
top -p $(pgrep -f "python manage.py runserver")
```

#### Database Maintenance
```bash
# Optimize SQLite database
python manage.py dbshell -c "VACUUM; ANALYZE;"

# Clean old sessions
python manage.py clearsessions

# Clean old notifications
python manage.py cleanup_notifications --days=30
```

#### Cache Management
```bash
# Clear all cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Clear specific cache keys
redis-cli FLUSHDB
```

### 4. User Management

#### Create New User
```bash
# Via management command
python manage.py createhorillauser --first_name John --last_name Doe --username johndoe --password secure123 --email john@company.com --phone 1234567890

# Via Django shell
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from employee.models import Employee
>>> user = User.objects.create_user('username', 'email@example.com', 'password')
>>> employee = Employee.objects.create(user=user, employee_id='EMP001')
```

#### Reset User Password
```bash
# Via management command
python manage.py changepassword username

# Via Django shell
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='username')
>>> user.set_password('new_password')
>>> user.save()
```

---

## Troubleshooting

### Masalah Umum dan Solusi

#### 1. ModuleNotFoundError

**Gejala**: `ModuleNotFoundError: No module named 'django'`

**Solusi**:
```bash
# Pastikan virtual environment aktif
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
python -c "import django; print(django.get_version())"
```

#### 2. Database Migration Errors

**Gejala**: `django.db.utils.OperationalError`

**Solusi**:
```bash
# Reset migrations (HATI-HATI: akan menghapus data)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Create new migrations
python manage.py makemigrations
python manage.py migrate

# Atau fake initial migration
python manage.py migrate --fake-initial
```

#### 3. Static Files Not Loading

**Gejala**: CSS/JS files tidak load, 404 errors

**Solusi**:
```bash
# Collect static files
python manage.py collectstatic --clear --noinput

# Check static files configuration
python manage.py findstatic admin/css/base.css

# Untuk development, pastikan DEBUG=True
echo "DEBUG=True" >> .env
```

#### 4. Redis Connection Error

**Gejala**: `ConnectionError: Error 111 connecting to 127.0.0.1:6379`

**Solusi**:
```bash
# Start Redis server
# macOS
brew services start redis

# Ubuntu
sudo systemctl start redis-server

# Manual start
redis-server

# Test connection
redis-cli ping
```

#### 5. Ollama Connection Error

**Gejala**: AI features tidak berfungsi

**Solusi**:
```bash
# Check Ollama status
ollama list

# Start Ollama service
ollama serve

# Test connection
curl http://localhost:11434/api/tags

# Restart if needed
pkill ollama
ollama serve &
```

#### 6. Port Already in Use

**Gejala**: `Error: That port is already in use`

**Solusi**:
```bash
# Find process using port 8000
lsof -ti:8000

# Kill process
kill -9 $(lsof -ti:8000)

# Atau gunakan port lain
python manage.py runserver 8001
```

#### 7. Permission Denied Errors

**Gejala**: Permission denied saat akses file/direktori

**Solusi**:
```bash
# Fix permissions
chmod -R 755 .
chown -R $USER:$USER .

# Untuk media directory
mkdir -p media
chmod 755 media
```

#### 8. Memory/Performance Issues

**Gejala**: Aplikasi lambat atau crash

**Solusi**:
```bash
# Monitor memory usage
ps aux | grep python

# Reduce Celery workers
celery -A horilla worker --concurrency=2

# Use lighter AI models
echo "OLLAMA_DEFAULT_MODEL=phi3:mini" >> .env

# Enable database connection pooling
echo "CONN_MAX_AGE=600" >> .env
```

### Debug Mode dan Logging

#### Enable Debug Mode
```bash
# Set debug environment
echo "DEBUG=True" >> .env
echo "LOG_LEVEL=DEBUG" >> .env

# Restart server
python manage.py runserver --verbosity=2
```

#### Advanced Logging
```bash
# Enable SQL query logging
echo "LOGGING_LEVEL=DEBUG" >> .env

# Monitor logs in real-time
tail -f logs/django.log | grep ERROR

# Check performance logs
tail -f logs/performance.log
```

### Health Check Commands

```bash
#!/bin/bash
# health_check.sh - System health verification

echo "=== Horilla HR System Health Check ==="

# Python environment
echo "Python version: $(python --version)"
echo "Virtual env: $VIRTUAL_ENV"

# Django check
echo "Django check:"
python manage.py check --deploy

# Database connectivity
echo "Database check:"
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); print('Database OK')"

# Redis connectivity
echo "Redis check:"
redis-cli ping

# Ollama connectivity
echo "Ollama check:"
curl -s http://localhost:11434/api/tags | jq '.models | length' || echo "Ollama not available"

# Disk space
echo "Disk usage:"
df -h .

# Memory usage
echo "Memory usage:"
free -h

echo "=== Health Check Complete ==="
```

---

## Best Practices

### 1. Security Best Practices

#### Production Security
```env
# .env for production
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# SSL/HTTPS Settings
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

#### Database Security
```bash
# Use PostgreSQL for production
DATABASE_URL=postgresql://username:password@localhost:5432/horilla_prod

# Regular backups
0 2 * * * /path/to/backup.sh

# Monitor failed login attempts
python manage.py shell -c "from django.contrib.admin.models import LogEntry; print(LogEntry.objects.filter(action_flag=1).count())"
```

### 2. Performance Optimization

#### Database Optimization
```python
# settings.py additions
DATABASES = {
    'default': {
        # ... existing config ...
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'MAX_CONNS': 20,
            'CONN_HEALTH_CHECKS': True,
        }
    }
}
```

#### Caching Strategy
```python
# Enable template caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# Cache timeout settings
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'horilla'
```

#### Static Files Optimization
```bash
# Compress static files
pip install django-compressor

# Use CDN for static files (production)
STATIC_URL = 'https://cdn.yourdomain.com/static/'
```

### 3. Monitoring dan Alerting

#### System Monitoring
```bash
# Install monitoring tools
pip install django-prometheus
pip install sentry-sdk

# Add to settings.py
INSTALLED_APPS += ['django_prometheus']
MIDDLEWARE = ['django_prometheus.middleware.PrometheusBeforeMiddleware'] + MIDDLEWARE + ['django_prometheus.middleware.PrometheusAfterMiddleware']
```

#### Log Rotation
```bash
# Setup logrotate
sudo nano /etc/logrotate.d/horilla

# Content:
/path/to/horilla/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
```

### 4. Backup Strategy

#### Automated Backups
```bash
#!/bin/bash
# automated_backup.sh

BACKUP_DIR="/backups/horilla"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump horilla_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep only last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 sync $BACKUP_DIR s3://your-backup-bucket/horilla/
```

#### Crontab Setup
```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/automated_backup.sh

# Weekly health check
0 6 * * 0 /path/to/health_check.sh | mail -s "Horilla Health Report" admin@company.com
```

---

## Deployment Production

### 1. Server Requirements

#### Minimum Production Server
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **OS**: Ubuntu 20.04 LTS atau CentOS 8
- **Network**: Static IP dengan domain

#### Recommended Production Server
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Load Balancer**: Nginx atau HAProxy
- **Database**: PostgreSQL cluster
- **Cache**: Redis cluster

### 2. Production Setup

#### System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y redis-server
sudo apt install -y nginx
sudo apt install -y supervisor
sudo apt install -y certbot python3-certbot-nginx
```

#### Database Setup
```bash
# Setup PostgreSQL
sudo -u postgres createuser --interactive horilla
sudo -u postgres createdb horilla_prod -O horilla

# Set password
sudo -u postgres psql
\password horilla
\q
```

#### Application Deployment
```bash
# Create application user
sudo useradd -m -s /bin/bash horilla
sudo su - horilla

# Clone application
git clone <repository> /home/horilla/app
cd /home/horilla/app

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with production settings

# Setup database
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createhorillauser --username admin --password secure_password
```

#### Nginx Configuration
```nginx
# /etc/nginx/sites-available/horilla
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /home/horilla/app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /home/horilla/app/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
}
```

#### Supervisor Configuration
```ini
# /etc/supervisor/conf.d/horilla.conf
[program:horilla]
command=/home/horilla/app/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 horilla.wsgi:application
directory=/home/horilla/app
user=horilla
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/horilla.log

[program:horilla-celery]
command=/home/horilla/app/venv/bin/celery -A horilla worker --loglevel=info
directory=/home/horilla/app
user=horilla
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/horilla-celery.log

[program:horilla-beat]
command=/home/horilla/app/venv/bin/celery -A horilla beat --loglevel=info
directory=/home/horilla/app
user=horilla
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/horilla-beat.log
```

#### SSL Certificate
```bash
# Install SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Production Checklist

- [ ] **Security**
  - [ ] DEBUG=False
  - [ ] Strong SECRET_KEY
  - [ ] HTTPS enabled
  - [ ] Firewall configured
  - [ ] Database password secured

- [ ] **Performance**
  - [ ] Database optimized
  - [ ] Caching enabled
  - [ ] Static files served by Nginx
  - [ ] Gzip compression enabled

- [ ] **Monitoring**
  - [ ] Log rotation configured
  - [ ] Health checks enabled
  - [ ] Error tracking (Sentry)
  - [ ] Performance monitoring

- [ ] **Backup**
  - [ ] Automated database backups
  - [ ] Media files backup
  - [ ] Configuration backup
  - [ ] Disaster recovery plan

---

## Kesimpulan

Dokumen ini menyediakan panduan lengkap untuk instalasi, konfigurasi, dan operasional Horilla HR System. Untuk dukungan lebih lanjut:

- **Dokumentasi API**: `/monitoring/API_DOCUMENTATION.md`
- **Panduan Pengguna**: `/PANDUAN_PENGGUNA.md`
- **Arsitektur Sistem**: `/SYSTEM_ARCHITECTURE.md`
- **Panduan Keamanan**: `/SECURITY.md`

**Catatan Penting**: Selalu test instalasi di environment development sebelum deploy ke production. Pastikan backup data secara regular dan monitor sistem secara berkala.

---

*Dokumen ini dibuat pada: $(date +"%Y-%m-%d %H:%M:%S")*
*Versi Aplikasi: Horilla HR System v2.0*
*Versi Django: 4.2.21*
*Versi Python: 3.9+*