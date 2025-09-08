# Troubleshooting Guide - Horilla HR System

## 🔧 Panduan Pemecahan Masalah

Panduan ini berisi solusi untuk masalah umum yang mungkin Anda temui saat menggunakan Horilla HR System.

## 📋 Daftar Isi
1. [Masalah Instalasi](#masalah-instalasi)
2. [Masalah Database](#masalah-database)
3. [Masalah Server](#masalah-server)
4. [Masalah AI/Ollama](#masalah-aiollama)
5. [Masalah Performance](#masalah-performance)
6. [Masalah Security](#masalah-security)
7. [FAQ](#faq)

## 🚨 Masalah Instalasi

### Error: "ModuleNotFoundError"
**Gejala**: Import error saat menjalankan aplikasi
```
ModuleNotFoundError: No module named 'django'
```

**Solusi**:
```bash
# Pastikan virtual environment aktif
source venv/bin/activate

# Install ulang dependencies
pip install -r requirements.txt

# Atau install manual
pip install Django==4.2.21
```

### Error: "Python command not found"
**Gejala**: `python: command not found`

**Solusi**:
```bash
# Gunakan python3 sebagai gantinya
python3 manage.py runserver

# Atau buat alias
alias python=python3
```

### Error: "Permission denied"
**Gejala**: Permission error saat menjalankan script

**Solusi**:
```bash
# Berikan permission execute
chmod +x setup.sh

# Atau jalankan dengan bash
bash setup.sh
```

## 🗄️ Masalah Database

### Error: "Database is locked"
**Gejala**: `database is locked` atau `OperationalError`

**Solusi**:
```bash
# Tutup semua koneksi database
pkill -f "python.*manage.py"

# Restart aplikasi
python3 manage.py runserver

# Jika masih bermasalah, reset database (development only)
rm db.sqlite3
python3 manage.py migrate
python3 manage.py createsuperuser
```

### Error: "Migration conflicts"
**Gejala**: Conflict saat menjalankan migrate

**Solusi**:
```bash
# Reset migrations (hati-hati!)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Buat migrations baru
python3 manage.py makemigrations
python3 manage.py migrate
```

### Error: "Table doesn't exist"
**Gejala**: `no such table` atau `relation does not exist`

**Solusi**:
```bash
# Jalankan migrations
python3 manage.py makemigrations
python3 manage.py migrate

# Jika masih error, migrate dengan fake-initial
python3 manage.py migrate --fake-initial
```

## 🖥️ Masalah Server

### Error: "Port already in use"
**Gejala**: `Error: That port is already in use`

**Solusi**:
```bash
# Gunakan port lain
python3 manage.py runserver 8001

# Atau kill process yang menggunakan port 8000
lsof -ti:8000 | xargs kill -9

# macOS alternative
sudo lsof -i :8000
sudo kill -9 <PID>
```

### Error: "Static files not loading"
**Gejala**: CSS/JS tidak load, 404 error untuk static files

**Solusi**:
```bash
# Collect static files
python3 manage.py collectstatic --clear --noinput

# Pastikan DEBUG=True untuk development
echo "DEBUG=True" >> .env

# Atau serve static files manual
python3 manage.py runserver --insecure
```

### Error: "CSRF verification failed"
**Gejala**: 403 Forbidden, CSRF token missing

**Solusi**:
```bash
# Tambahkan ke .env
echo "CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000" >> .env

# Restart server
python3 manage.py runserver
```

## 🤖 Masalah AI/Ollama

### Error: "Ollama connection failed"
**Gejala**: AI features tidak berfungsi

**Solusi**:
```bash
# Check apakah Ollama running
ps aux | grep ollama

# Start Ollama service
ollama serve &

# Test connection
curl http://localhost:11434/api/version

# Download model jika belum ada
ollama pull llama2
```

### Error: "Model not found"
**Gejala**: `model 'llama2' not found`

**Solusi**:
```bash
# List available models
ollama list

# Download required model
ollama pull llama2
ollama pull mistral

# Verify model
ollama run llama2 "Hello"
```

### Error: "Out of memory"
**Gejala**: Ollama crashes dengan memory error

**Solusi**:
```bash
# Gunakan model yang lebih kecil
ollama pull llama2:7b-chat-q4_0

# Atau adjust memory limit
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_PARALLEL=1
```

## ⚡ Masalah Performance

### Aplikasi lambat
**Gejala**: Response time tinggi, loading lama

**Solusi**:
```bash
# Enable caching
echo "CACHE_ENABLED=True" >> .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env

# Start Redis
redis-server --daemonize yes

# Optimize database
python3 manage.py dbshell
# Jalankan: VACUUM; ANALYZE;
```

### Memory usage tinggi
**Gejala**: High RAM consumption

**Solusi**:
```bash
# Monitor memory usage
ps aux | grep python
top -p $(pgrep -f "python.*manage.py")

# Restart aplikasi secara berkala
pkill -f "python.*manage.py"
python3 manage.py runserver

# Gunakan production server
gunicorn horilla.wsgi:application --workers 2 --max-requests 1000
```

## 🔒 Masalah Security

### Error: "Rate limit exceeded"
**Gejala**: 429 Too Many Requests

**Solusi**:
```bash
# Check rate limit settings
grep -r "RATE_LIMIT" .

# Reset rate limit (development)
redis-cli FLUSHDB

# Atau tunggu beberapa menit
```

### Error: "Authentication failed"
**Gejala**: Login tidak berhasil, session expired

**Solusi**:
```bash
# Clear sessions
python3 manage.py clearsessions

# Reset user password
python3 manage.py changepassword <username>

# Check user status
python3 manage.py shell
# >>> from django.contrib.auth.models import User
# >>> User.objects.filter(username='admin').first()
```

## ❓ FAQ (Frequently Asked Questions)

### Q: Bagaimana cara backup data?
**A**: 
```bash
# Backup database
python3 manage.py dumpdata > backup.json

# Backup media files
tar -czf media_backup.tar.gz media/

# Restore
python3 manage.py loaddata backup.json
```

### Q: Bagaimana cara update aplikasi?
**A**:
```bash
# Backup terlebih dahulu
python3 manage.py dumpdata > backup_$(date +%Y%m%d).json

# Pull update
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Migrate database
python3 manage.py migrate

# Collect static
python3 manage.py collectstatic --noinput
```

### Q: Bagaimana cara menambah user baru?
**A**:
```bash
# Via command line
python3 manage.py createsuperuser

# Via admin panel
# Akses http://127.0.0.1:8000/admin/
# Login sebagai admin
# Pilih Users > Add user
```

### Q: Bagaimana cara mengubah port default?
**A**:
```bash
# Temporary
python3 manage.py runserver 0.0.0.0:8080

# Permanent (production)
# Edit gunicorn config atau docker-compose.yml
```

### Q: Bagaimana cara enable HTTPS?
**A**:
```bash
# Development (self-signed)
python3 manage.py runsslserver 0.0.0.0:8443

# Production
# Setup Nginx dengan SSL certificate
# Atau gunakan Cloudflare/Let's Encrypt
```

### Q: Bagaimana cara monitoring performance?
**A**:
```bash
# Check health
curl http://127.0.0.1:8000/health/

# Check metrics
curl http://127.0.0.1:8000/metrics/

# Monitor logs
tail -f logs/django.log

# System monitoring
top
htop
iostat
```

## 🆘 Mendapatkan Bantuan

### Log Files Locations
- **Django Logs**: `logs/django.log`
- **Celery Logs**: `logs/celery.log`
- **Nginx Logs**: `/var/log/nginx/error.log`
- **System Logs**: `/var/log/syslog` (Linux), `Console.app` (macOS)

### Debug Commands
```bash
# Enable verbose logging
export DJANGO_LOG_LEVEL=DEBUG
python3 manage.py runserver --verbosity=2

# Django shell untuk debugging
python3 manage.py shell

# Check system status
python3 manage.py check --deploy

# Database shell
python3 manage.py dbshell
```

### Informasi System
```bash
# Python version
python3 --version

# Django version
python3 -m django --version

# Installed packages
pip list

# System info
uname -a
df -h
free -m
```

### Contact Support
- **GitHub Issues**: Untuk bug reports
- **Documentation**: Lihat file README.md dan dokumentasi lainnya
- **Community**: GitHub Discussions
- **Email**: Untuk enterprise support

---

**💡 Tips**: Selalu backup data sebelum melakukan troubleshooting yang melibatkan perubahan database atau file sistem.