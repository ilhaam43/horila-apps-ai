# Panduan Menjalankan Aplikasi Horilla HRMS

## 📋 Daftar Isi
1. [Persyaratan Sistem](#persyaratan-sistem)
2. [Cara Memulai Aplikasi](#cara-memulai-aplikasi)
3. [Fitur Utama dan Fungsionalitas](#fitur-utama-dan-fungsionalitas)
4. [Troubleshooting](#troubleshooting)
5. [Tips Optimasi](#tips-optimasi)

---

## 🖥️ Persyaratan Sistem

### Persyaratan Minimum
- **Python**: 3.8 atau lebih tinggi
- **RAM**: 4GB minimum, 8GB direkomendasikan
- **Storage**: 2GB ruang kosong minimum
- **OS**: Windows 10+, macOS 10.14+, atau Linux (Ubuntu 18.04+)
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, atau Edge 90+

### Dependencies Utama
- Django 4.2.21
- PostgreSQL/MySQL (opsional, default SQLite)
- Redis (untuk caching dan Celery)
- Node.js (untuk asset compilation)

### Services Eksternal (Opsional)
- **Ollama**: Untuk fitur AI lokal
- **N8N**: Untuk workflow automation
- **SMTP Server**: Untuk notifikasi email

---

## 🚀 Cara Memulai Aplikasi

### Metode 1: Quick Start (Recommended)
```bash
# 1. Masuk ke direktori aplikasi
cd /Users/haryanto.bonti/apps

# 2. Aktifkan virtual environment (jika sudah ada)
source venv/bin/activate

# 3. Jalankan aplikasi
python3 manage.py runserver
```

### Metode 2: Setup Lengkap (Jika Belum Pernah Dijalankan)
```bash
# 1. Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment variables
cp .env.example .env
# Edit .env sesuai kebutuhan

# 4. Setup database
python3 manage.py makemigrations
python3 manage.py migrate

# 5. Buat superuser (admin)
python3 manage.py createsuperuser

# 6. Collect static files
python3 manage.py collectstatic --noinput

# 7. Jalankan aplikasi
python3 manage.py runserver
```

### Akses Aplikasi
Setelah aplikasi berjalan, buka browser dan akses:
- **Dashboard Utama**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **Health Check**: http://127.0.0.1:8000/health/

### Menjalankan Services Tambahan

#### Redis (untuk caching)
```bash
# macOS dengan Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server
```

#### Celery (untuk background tasks)
```bash
# Terminal terpisah
celery -A horilla worker --loglevel=info

# Celery Beat (untuk scheduled tasks)
celery -A horilla beat --loglevel=info
```

#### Ollama (untuk AI features)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model
ollama pull phi3:mini

# Start Ollama service
ollama serve
```

---

## 🎯 Fitur Utama dan Fungsionalitas

### 1. Employee Management
- **Lokasi**: http://127.0.0.1:8000/employee/
- **Fungsi**: Manajemen data karyawan, profil, dan informasi personal
- **Fitur**: CRUD karyawan, upload foto, manajemen departemen

### 2. Attendance Management
- **Lokasi**: http://127.0.0.1:8000/attendance/
- **Fungsi**: Pelacakan kehadiran dan jam kerja
- **Fitur**: Clock in/out, overtime tracking, attendance reports

### 3. Leave Management
- **Lokasi**: http://127.0.0.1:8000/leave/
- **Fungsi**: Manajemen cuti dan izin karyawan
- **Fitur**: Apply leave, approval workflow, leave balance

### 4. Recruitment
- **Lokasi**: http://127.0.0.1:8000/recruitment/
- **Fungsi**: Proses rekrutmen end-to-end
- **Fitur**: Job posting, candidate management, AI screening

### 5. Payroll
- **Lokasi**: http://127.0.0.1:8000/payroll/
- **Fungsi**: Perhitungan dan manajemen gaji
- **Fitur**: Salary calculation, payslip generation, tax calculation

### 6. Budget Management
- **Lokasi**: http://127.0.0.1:8000/budget/
- **Fungsi**: Kontrol dan monitoring anggaran
- **Fitur**: Budget planning, expense tracking, real-time monitoring

### 7. Performance Management (PMS)
- **Lokasi**: http://127.0.0.1:8000/pms/
- **Fungsi**: Evaluasi kinerja karyawan
- **Fitur**: Goal setting, performance reviews, 360-degree feedback

### 8. Knowledge Management
- **Lokasi**: http://127.0.0.1:8000/knowledge/
- **Fungsi**: Manajemen pengetahuan dan dokumentasi
- **Fitur**: Document storage, AI-powered search, knowledge base

### 9. AI Services
- **Lokasi**: http://127.0.0.1:8000/ai/
- **Fungsi**: Layanan AI dan automasi
- **Fitur**: Chatbot, document classification, Indonesian NLP

### 10. Asset Management
- **Lokasi**: http://127.0.0.1:8000/asset/
- **Fungsi**: Manajemen aset perusahaan
- **Fitur**: Asset tracking, maintenance scheduling, depreciation

### 11. Onboarding
- **Lokasi**: http://127.0.0.1:8000/onboarding/
- **Fungsi**: Proses orientasi karyawan baru
- **Fitur**: Onboarding checklist, document collection, training

### 12. Monitoring & Analytics
- **Lokasi**: http://127.0.0.1:8000/monitoring/
- **Fungsi**: Monitoring sistem dan analytics
- **Fitur**: System health, performance metrics, usage analytics

---

## 🔧 Troubleshooting

### Masalah Umum dan Solusi

#### 1. Aplikasi Tidak Bisa Dijalankan

**Error**: `ModuleNotFoundError: No module named 'django'`
```bash
# Solusi:
source venv/bin/activate
pip install -r requirements.txt
```

**Error**: `Port already in use`
```bash
# Solusi:
# Gunakan port lain
python3 manage.py runserver 8001

# Atau kill process yang menggunakan port 8000
lsof -ti:8000 | xargs kill -9
```

#### 2. Database Issues

**Error**: `database is locked`
```bash
# Solusi:
pkill -f "python.*manage.py"
python3 manage.py runserver
```

**Error**: `no such table`
```bash
# Solusi:
python3 manage.py makemigrations
python3 manage.py migrate
```

#### 3. Static Files Issues

**Error**: CSS/JS tidak load
```bash
# Solusi:
python3 manage.py collectstatic --noinput
# Pastikan DEBUG=True di .env untuk development
```

#### 4. Redis Connection Error

**Error**: `ConnectionError: Error connecting to Redis`
```bash
# Solusi:
# Start Redis service
brew services start redis  # macOS
sudo systemctl start redis-server  # Linux

# Atau gunakan local memory cache (edit settings.py)
# Ganti CACHES default ke 'locmem'
```

#### 5. AI Services Error

**Error**: Ollama connection failed
```bash
# Solusi:
# Install dan start Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
ollama pull phi3:mini
```

#### 6. Permission Errors

**Error**: `Permission denied`
```bash
# Solusi:
chmod +x manage.py
# Atau jalankan dengan python3
python3 manage.py runserver
```

#### 7. Memory Issues

**Error**: `MemoryError` atau aplikasi lambat
```bash
# Solusi:
# Restart aplikasi
pkill -f "python.*manage.py"
python3 manage.py runserver

# Atau gunakan production server
gunicorn horilla.wsgi:application --bind 127.0.0.1:8000
```

### Debugging Tips

1. **Check Logs**:
   ```bash
   tail -f logs/django.log
   tail -f logs/performance.log
   ```

2. **Check System Status**:
   ```bash
   # Health check
   curl http://127.0.0.1:8000/health/
   
   # Metrics
   curl http://127.0.0.1:8000/metrics/
   ```

3. **Database Shell**:
   ```bash
   python3 manage.py dbshell
   ```

4. **Django Shell**:
   ```bash
   python3 manage.py shell
   ```

---

## ⚡ Tips Optimasi

### Performance Tips

1. **Enable Redis Caching**:
   ```bash
   # Install Redis
   brew install redis
   brew services start redis
   
   # Pastikan REDIS_URL di .env
   REDIS_URL=redis://127.0.0.1:6379/1
   ```

2. **Use Production Database**:
   ```bash
   # PostgreSQL (recommended)
   pip install psycopg2-binary
   # Update DATABASE_URL di .env
   DATABASE_URL=postgresql://user:password@localhost:5432/horilla
   ```

3. **Enable Static File Compression**:
   ```bash
   # Sudah dikonfigurasi dengan WhiteNoise
   python3 manage.py collectstatic --noinput
   ```

### Security Tips

1. **Production Settings**:
   ```bash
   # Update .env untuk production
   DEBUG=False
   SECRET_KEY=your-secure-secret-key
   ALLOWED_HOSTS=your-domain.com
   SECURE_SSL_REDIRECT=True
   ```

2. **Regular Backups**:
   ```bash
   # Backup database
   python3 manage.py dumpdata > backup.json
   
   # Backup media files
   tar -czf media_backup.tar.gz media/
   ```

### Monitoring Tips

1. **Enable Logging**:
   ```bash
   # Logs tersimpan di logs/
   tail -f logs/django.log
   tail -f logs/performance.log
   ```

2. **Monitor System Resources**:
   ```bash
   # Check memory usage
   ps aux | grep python
   
   # Check disk usage
   df -h
   ```

---

## 📞 Bantuan Lebih Lanjut

Jika masih mengalami masalah:

1. **Check Documentation**: Lihat file dokumentasi lainnya di direktori proyek
2. **Check Logs**: Periksa file log di direktori `logs/`
3. **System Health**: Akses http://127.0.0.1:8000/health/ untuk status sistem
4. **Debug Mode**: Set `DEBUG=True` di `.env` untuk informasi error detail

---

## 🔍 Verifikasi Instalasi

### Quick Health Check
Setelah menjalankan aplikasi, lakukan verifikasi berikut:

1. **Akses Dashboard**:
   ```bash
   curl -I http://127.0.0.1:8000/
   # Harus return HTTP/1.1 200 OK
   ```

2. **Check Database Connection**:
   ```bash
   python3 manage.py check --database default
   ```

3. **Verify Static Files**:
   ```bash
   curl -I http://127.0.0.1:8000/static/css/style.css
   # Harus return HTTP/1.1 200 OK
   ```

4. **Test Admin Access**:
   - Buka http://127.0.0.1:8000/admin/
   - Login dengan superuser yang dibuat
   - Pastikan dapat mengakses admin panel

### System Status Commands
```bash
# Check deployment readiness
python3 manage.py check --deploy

# Verify migrations
python3 manage.py showmigrations

# Test database connection
python3 manage.py dbshell
```

---

## 📊 Monitoring dan Maintenance

### Log Files Location
- **Django Logs**: `logs/django.log`
- **Performance Logs**: `logs/performance.log`
- **Error Logs**: Check console output saat development

### Regular Maintenance Tasks
```bash
# Weekly database cleanup
python3 manage.py clearsessions

# Monthly static files update
python3 manage.py collectstatic --noinput

# Backup database (recommended weekly)
python3 manage.py dumpdata > backup_$(date +%Y%m%d).json
```

### Performance Monitoring
```bash
# Check system resources
ps aux | grep python | grep manage.py

# Monitor database size
du -sh db.sqlite3  # untuk SQLite

# Check Redis status (jika digunakan)
redis-cli ping
```

---

## 🚨 Emergency Procedures

### Aplikasi Crash atau Tidak Responsif
```bash
# 1. Stop semua proses
pkill -f "python.*manage.py"

# 2. Check log untuk error
tail -n 50 logs/django.log

# 3. Restart aplikasi
python3 manage.py runserver
```

### Database Corruption
```bash
# Backup current database
cp db.sqlite3 db.sqlite3.backup

# Restore from backup
cp backup_YYYYMMDD.json restore.json
python3 manage.py flush --noinput
python3 manage.py loaddata restore.json
```

### Reset ke Default State
```bash
# HATI-HATI: Ini akan menghapus semua data!
rm db.sqlite3
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py collectstatic --noinput
```

---

## 📋 Checklist Pre-Production

Sebelum deploy ke production, pastikan:

- [ ] `DEBUG=False` di `.env`
- [ ] `SECRET_KEY` yang kuat dan unik
- [ ] `ALLOWED_HOSTS` dikonfigurasi dengan benar
- [ ] Database production sudah setup
- [ ] Redis/cache server berjalan
- [ ] SSL certificate terpasang
- [ ] Backup strategy sudah ada
- [ ] Monitoring tools aktif
- [ ] Log rotation dikonfigurasi

---

**Catatan**: Panduan ini dibuat berdasarkan konfigurasi saat ini dan telah diverifikasi dengan testing. Pastikan untuk selalu backup data sebelum melakukan perubahan konfigurasi. Untuk bantuan lebih lanjut, periksa file dokumentasi lainnya di direktori proyek atau hubungi administrator sistem.