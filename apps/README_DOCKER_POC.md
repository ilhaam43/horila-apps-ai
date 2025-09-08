# 🐳 AI Services POC - Docker Setup

## 🎯 Quick Start dengan Docker

POC ini telah dikonfigurasi untuk berjalan dengan Docker, memudahkan deployment dan testing.

### ✅ Prerequisites

- Docker Desktop installed dan running
- Docker Compose (biasanya sudah termasuk dengan Docker Desktop)
- Port 8000 tersedia

### 🚀 Menjalankan POC

#### Opsi 1: Menggunakan Script (Recommended)

```bash
# Start POC
./run_docker_poc.sh start

# Stop POC
./run_docker_poc.sh stop

# Restart POC
./run_docker_poc.sh restart

# View logs
./run_docker_poc.sh logs

# Check status
./run_docker_poc.sh status

# Cleanup (remove containers and volumes)
./run_docker_poc.sh cleanup
```

#### Opsi 2: Manual Docker Compose

```bash
# Build dan start
docker-compose -f docker-compose.poc.yml up -d --build

# Stop
docker-compose -f docker-compose.poc.yml down

# View logs
docker-compose -f docker-compose.poc.yml logs -f
```

### 🌐 Akses Aplikasi

Setelah container berjalan:

- **Main Application**: http://localhost:8000
- **API Status**: http://localhost:8000/api/status/
- **Health Check**: http://localhost:8000/health/
- **Admin Panel**: http://localhost:8000/admin/

### 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Health check |
| GET | `/api/status/` | API status dan statistik |
| GET | `/api/models/` | List semua AI models |
| POST | `/api/models/` | Create model baru |
| POST | `/api/predict/` | Make prediction |
| POST | `/api/train/` | Train model |
| GET | `/api/predictions/` | Prediction history |
| GET | `/api/training/` | Training history |

### 🧪 Testing API

#### 1. Check API Status
```bash
curl http://localhost:8000/api/status/ | python3 -m json.tool
```

#### 2. Create Model
```bash
curl -X POST http://localhost:8000/api/models/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Text Classifier",
    "model_type": "classification",
    "description": "Simple text classification model",
    "version": "1.0"
  }' | python3 -m json.tool
```

#### 3. Make Prediction
```bash
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "input_data": {"text": "This is a test message"}
  }' | python3 -m json.tool
```

### 🔧 Configuration

#### Environment Variables

Docker setup menggunakan environment variables berikut:

- `DJANGO_SETTINGS_MODULE=settings_poc`
- `DEBUG=True` (untuk POC)

#### Services

Docker Compose setup termasuk:

1. **web**: Django application (port 8000)
2. **db**: PostgreSQL database (port 5432) - optional
3. **redis**: Redis cache (port 6379) - optional

### 📝 Logs dan Debugging

#### View Logs
```bash
# All services
docker-compose -f docker-compose.poc.yml logs -f

# Specific service
docker-compose -f docker-compose.poc.yml logs -f web
```

#### Debug Container
```bash
# Access container shell
docker-compose -f docker-compose.poc.yml exec web bash

# Run Django commands
docker-compose -f docker-compose.poc.yml exec web python manage.py shell
```

### 🛠 Development

#### Rebuild After Changes
```bash
# Rebuild and restart
./run_docker_poc.sh restart

# Or manually
docker-compose -f docker-compose.poc.yml up -d --build
```

#### Volume Mounts

- `./media:/app/media` - Media files
- `./logs:/app/logs` - Application logs

### 🚨 Troubleshooting

#### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

#### Container Won't Start
```bash
# Check container status
docker-compose -f docker-compose.poc.yml ps

# Check logs for errors
docker-compose -f docker-compose.poc.yml logs web
```

#### Database Issues
```bash
# Reset database
docker-compose -f docker-compose.poc.yml down -v
docker-compose -f docker-compose.poc.yml up -d --build
```

#### Clean Start
```bash
# Complete cleanup and restart
./run_docker_poc.sh cleanup
./run_docker_poc.sh start
```

### 📈 Performance

#### Resource Usage
```bash
# Check resource usage
docker stats

# Check container health
docker-compose -f docker-compose.poc.yml ps
```

#### Health Checks

Container includes health checks:
- Web service: `curl -f http://localhost:8000/health/`
- Database: `pg_isready` (if using PostgreSQL)
- Redis: `redis-cli ping` (if using Redis)

### 🔒 Security Notes

- POC menggunakan `DEBUG=True` - **JANGAN** gunakan untuk production
- Default passwords dalam docker-compose - ganti untuk production
- SQLite database untuk simplicity - gunakan PostgreSQL untuk production

### 📦 Production Deployment

Untuk production deployment:

1. Ganti `DEBUG=False`
2. Set proper `SECRET_KEY`
3. Gunakan PostgreSQL database
4. Setup proper SSL/TLS
5. Configure proper logging
6. Use production WSGI server (Gunicorn)

Lihat `DEPLOYMENT_GUIDE.md` untuk panduan production lengkap.

---

**🎉 POC berhasil dikonfigurasi dengan Docker!**

Untuk pertanyaan atau issues, silakan check logs atau buat issue di repository.