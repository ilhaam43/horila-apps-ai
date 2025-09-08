# Quick Start Guide - Horilla HR System

## 🚀 Mulai Cepat (5 Menit Setup)

### Prasyarat
- Python 3.8+ sudah terinstall
- Git sudah terinstall
- Koneksi internet

### Langkah 1: Setup Environment
```bash
# Clone atau masuk ke direktori aplikasi
cd /path/to/horilla-app

# Buat dan aktifkan virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
```

### Langkah 2: Install Dependencies
```bash
# Install dependencies utama
pip install Django==4.2.7 djangorestframework django-cors-headers
pip install celery redis psycopg2-binary Pillow python-decouple
pip install requests pandas numpy scikit-learn nltk transformers
pip install torch sentence-transformers chromadb langchain ollama
pip install prometheus-client gunicorn
```

### Langkah 3: Setup Database
```bash
# Buat file .env
echo "SECRET_KEY=your-secret-key-$(date +%s)" > .env
echo "DEBUG=True" >> .env
echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env

# Setup database
python manage.py makemigrations
python manage.py migrate

# Buat superuser
python manage.py createsuperuser
```

### Langkah 4: Jalankan Aplikasi
```bash
# Jalankan server
python manage.py runserver

# Akses aplikasi di: http://127.0.0.1:8000/
```

## 🎯 Akses Cepat

| Fitur | URL | Deskripsi |
|-------|-----|----------|
| **Dashboard Utama** | http://127.0.0.1:8000/ | Halaman utama aplikasi |
| **Admin Panel** | http://127.0.0.1:8000/admin/ | Panel administrasi |
| **Budget Control** | http://127.0.0.1:8000/budget/ | Manajemen anggaran |
| **Knowledge Base** | http://127.0.0.1:8000/knowledge/ | Sistem manajemen pengetahuan |
| **Recruitment** | http://127.0.0.1:8000/recruitment/ | Modul rekrutmen |
| **Health Check** | http://127.0.0.1:8000/health/ | Status sistem |
| **Metrics** | http://127.0.0.1:8000/metrics/ | Monitoring metrics |

## 🔧 Konfigurasi Opsional

### Setup Ollama (untuk AI Features)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start service
ollama serve &

# Download model
ollama pull llama2
```

### Setup Redis (untuk Background Tasks)
```bash
# macOS
brew install redis
redis-server &

# Ubuntu
sudo apt install redis-server
sudo systemctl start redis
```

### Jalankan Background Services
```bash
# Terminal baru - Celery worker
celery -A horilla worker --loglevel=info

# Terminal baru - Celery beat
celery -A horilla beat --loglevel=info
```

## ✅ Verifikasi Cepat

```bash
# Test sistem
python manage.py check

# Test health endpoint
curl http://127.0.0.1:8000/health/

# Test metrics
curl http://127.0.0.1:8000/metrics/
```

## 🆘 Troubleshooting Cepat

### Error: Port sudah digunakan
```bash
python manage.py runserver 8001
```

### Error: Module tidak ditemukan
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Error: Database locked
```bash
python manage.py migrate --run-syncdb
```

### Reset database (development only)
```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

## 📚 Dokumentasi Lengkap

- **Panduan Instalasi Lengkap**: `PANDUAN_INSTALASI.md`
- **Deployment Guide**: `DEPLOYMENT_GUIDE.md`
- **System Architecture**: `SYSTEM_ARCHITECTURE.md`
- **API Documentation**: `monitoring/API_DOCUMENTATION.md`

---

**💡 Tips**: Untuk penggunaan production, selalu gunakan `DEBUG=False` dan konfigurasi database yang proper (PostgreSQL/MySQL).