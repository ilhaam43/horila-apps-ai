# Panduan Instalasi dan Menjalankan Aplikasi Horilla HR System

## Daftar Isi
1. [Persyaratan Sistem](#persyaratan-sistem)
2. [Persiapan Lingkungan](#persiapan-lingkungan)
3. [Instalasi Aplikasi](#instalasi-aplikasi)
4. [Konfigurasi Awal](#konfigurasi-awal)
5. [Menjalankan Aplikasi](#menjalankan-aplikasi)
6. [Verifikasi Instalasi](#verifikasi-instalasi)
7. [Pemecahan Masalah](#pemecahan-masalah)
8. [Fitur Utama](#fitur-utama)

## Persyaratan Sistem

### Minimum Requirements
- **OS**: macOS 10.15+, Ubuntu 18.04+, Windows 10+
- **Python**: 3.8 atau lebih tinggi
- **RAM**: 4GB minimum (8GB direkomendasikan)
- **Storage**: 10GB ruang kosong
- **Network**: Koneksi internet untuk instalasi dependensi

### Software Dependencies
- Python 3.8+
- pip (Python package manager)
- Git
- SQLite (sudah termasuk dengan Python)
- Node.js 14+ (untuk frontend assets)
- Ollama (untuk AI features)

## Persiapan Lingkungan

### 1. Install Python
```bash
# macOS (menggunakan Homebrew)
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# Windows
# Download dari https://www.python.org/downloads/
```

### 2. Install Git
```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt install git

# Windows
# Download dari https://git-scm.com/download/win
```

### 3. Install Node.js (Opsional untuk development)
```bash
# macOS
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows
# Download dari https://nodejs.org/
```

### 4. Install Ollama (untuk AI Features)
```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download dari https://ollama.ai/download/windows
```

## Instalasi Aplikasi

### 1. Clone Repository
```bash
# Buat direktori untuk aplikasi
mkdir ~/horilla-app
cd ~/horilla-app

# Clone repository (jika menggunakan Git)
# git clone <repository-url> .

# Atau copy semua file aplikasi ke direktori ini
```

### 2. Buat Virtual Environment
```bash
# Buat virtual environment
python3 -m venv venv

# Aktifkan virtual environment
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies Python
```bash
# Upgrade pip
pip install --upgrade pip

# Install dependencies dari requirements.txt (jika ada)
pip install -r requirements.txt

# Atau install dependencies manual
pip install Django==4.2.7
pip install djangorestframework
pip install django-cors-headers
pip install celery
pip install redis
pip install psycopg2-binary
pip install Pillow
pip install python-decouple
pip install django-extensions
pip install requests
pip install beautifulsoup4
pip install pandas
pip install numpy
pip install scikit-learn
pip install nltk
pip install transformers
pip install torch
pip install sentence-transformers
pip install chromadb
pip install langchain
pip install ollama
pip install prometheus-client
pip install gunicorn
```

### 4. Install Frontend Dependencies (Opsional)
```bash
# Jika ada package.json
npm install

# Atau install dependencies manual
npm install bootstrap@5.3.0
npm install jquery
npm install htmx.org
```

## Konfigurasi Awal

### 1. Setup Environment Variables
```bash
# Copy file environment template
cp .env.dist .env

# Edit file .env dengan konfigurasi Anda
nano .env
```

**Contoh konfigurasi .env:**
```env
# Database Configuration
DATABASE_URL=sqlite:///db.sqlite3

# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Email Configuration (Opsional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Redis Configuration (untuk Celery)
REDIS_URL=redis://localhost:6379/0

# Security Settings
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

### 2. Setup Database
```bash
# Buat migrasi database
python manage.py makemigrations

# Terapkan migrasi
python manage.py migrate

# Buat superuser (admin)
python manage.py createsuperuser
```

### 3. Collect Static Files
```bash
# Kumpulkan file static
python manage.py collectstatic --noinput
```

### 4. Setup Ollama Models (untuk AI Features)
```bash
# Start Ollama service
ollama serve &

# Download model yang diperlukan
ollama pull llama2
ollama pull mistral
```

## Menjalankan Aplikasi

### 1. Menjalankan Development Server
```bash
# Pastikan virtual environment aktif
source venv/bin/activate  # macOS/Linux
# atau venv\Scripts\activate  # Windows

# Jalankan Django development server
python manage.py runserver

# Server akan berjalan di http://127.0.0.1:8000/
```

### 2. Menjalankan Background Services (Opsional)
```bash
# Terminal baru - Jalankan Celery worker (untuk background tasks)
celery -A horilla worker --loglevel=info

# Terminal baru - Jalankan Celery beat (untuk scheduled tasks)
celery -A horilla beat --loglevel=info

# Terminal baru - Jalankan Redis server (jika belum berjalan)
redis-server
```

### 3. Akses Aplikasi
- **Web Interface**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Documentation**: http://127.0.0.1:8000/api/docs/
- **Health Check**: http://127.0.0.1:8000/health/
- **Metrics**: http://127.0.0.1:8000/metrics/

## Verifikasi Instalasi

### 1. Test Basic Functionality
```bash
# Test management commands
python manage.py check
python manage.py test --verbosity=2
```

### 2. Test Web Interface
1. Buka browser dan akses http://127.0.0.1:8000/
2. Login menggunakan superuser yang telah dibuat
3. Navigasi ke berbagai modul untuk memastikan semuanya berfungsi

### 3. Test API Endpoints
```bash
# Test health check
curl http://127.0.0.1:8000/health/

# Test metrics
curl http://127.0.0.1:8000/metrics/

# Test API endpoints
curl -H "Content-Type: application/json" http://127.0.0.1:8000/api/
```

### 4. Test AI Features
1. Akses Knowledge Management module
2. Upload dokumen dan test AI classification
3. Test chat dengan AI Assistant
4. Verifikasi Indonesian NLP processing

## Pemecahan Masalah

### Masalah Umum dan Solusi

#### 1. Error "ModuleNotFoundError"
```bash
# Pastikan virtual environment aktif
source venv/bin/activate

# Install ulang dependencies
pip install -r requirements.txt
```

#### 2. Database Migration Error
```bash
# Reset migrations (hati-hati, akan menghapus data)
python manage.py migrate --fake-initial

# Atau buat migrasi baru
python manage.py makemigrations --empty <app_name>
```

#### 3. Static Files Not Loading
```bash
# Collect static files ulang
python manage.py collectstatic --clear --noinput

# Pastikan DEBUG=True untuk development
```

#### 4. Ollama Connection Error
```bash
# Pastikan Ollama service berjalan
ollama serve

# Check status
ollama list

# Restart service jika perlu
pkill ollama
ollama serve &
```

#### 5. Port Already in Use
```bash
# Gunakan port lain
python manage.py runserver 8001

# Atau kill process yang menggunakan port 8000
lsof -ti:8000 | xargs kill -9
```

### Log Files
- **Django Logs**: `logs/django.log`
- **Celery Logs**: `logs/celery.log`
- **Nginx Logs**: `/var/log/nginx/` (untuk production)
- **System Logs**: `/var/log/syslog` (Linux)

### Debug Mode
```bash
# Jalankan dengan debug verbose
python manage.py runserver --verbosity=2

# Atau set environment variable
export DJANGO_DEBUG=True
python manage.py runserver
```

## Fitur Utama

### 1. Budget Control System
- Real-time budget tracking
- Automated approval workflows
- Cost center management
- Financial reporting

### 2. Knowledge Management
- AI-powered document classification
- Intelligent search dengan RAG
- Knowledge base dengan versioning
- Collaborative editing

### 3. Indonesian NLP Processing
- Sentiment analysis untuk feedback
- Text classification untuk dokumen
- Named Entity Recognition
- Language detection

### 4. Recruitment Automation
- CV parsing dan ranking
- Automated interview scheduling
- Candidate communication
- Integration dengan N8N workflows

### 5. Monitoring & Analytics
- Real-time system monitoring
- Performance metrics
- Health checks
- Prometheus integration

### 6. Security Features
- Role-based access control
- API rate limiting
- Audit logging
- Data encryption

## Langkah Selanjutnya

1. **Kustomisasi**: Sesuaikan konfigurasi sesuai kebutuhan organisasi
2. **Data Import**: Import data existing dari sistem lama
3. **User Training**: Latih pengguna untuk menggunakan sistem
4. **Backup Setup**: Konfigurasi backup otomatis
5. **Production Deployment**: Deploy ke production environment

## Dukungan

- **Dokumentasi API**: `/monitoring/API_DOCUMENTATION.md`
- **Deployment Guide**: `/DEPLOYMENT_GUIDE.md`
- **System Architecture**: `/SYSTEM_ARCHITECTURE.md`
- **Security Guide**: `/SECURITY.md`

---

**Catatan**: Panduan ini dibuat untuk development environment. Untuk production deployment, silakan merujuk ke `DEPLOYMENT_GUIDE.md` untuk konfigurasi yang lebih aman dan optimal.