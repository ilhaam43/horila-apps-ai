# Monitoring API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Tidak ada authentication yang diperlukan untuk monitoring endpoints.

## Endpoints

### 1. Basic Health Check

**Endpoint:** `GET /health/`

**Description:** Basic health check untuk load balancer dan simple monitoring.

**Request:**
```http
GET /health/ HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK`: Application is healthy
- `405 Method Not Allowed`: Invalid HTTP method

---

### 2. Readiness Check

**Endpoint:** `GET /health/ready/`

**Description:** Kubernetes readiness probe - checks if application is ready to serve requests.

**Request:**
```http
GET /health/ready/ HTTP/1.1
Host: localhost:8000
```

**Response (Healthy):**
```json
{
  "status": "ready",
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "checks": {
    "database": true,
    "cache": true,
    "migrations": true
  }
}
```

**Response (Unhealthy):**
```json
{
  "status": "not_ready",
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "checks": {
    "database": false,
    "cache": true,
    "migrations": true
  }
}
```

**Status Codes:**
- `200 OK`: Application is ready
- `503 Service Unavailable`: Application is not ready
- `405 Method Not Allowed`: Invalid HTTP method

---

### 3. Liveness Check

**Endpoint:** `GET /health/live/`

**Description:** Kubernetes liveness probe - checks if application is alive and should not be restarted.

**Request:**
```http
GET /health/live/ HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "uptime": {
    "seconds": 3600,
    "human_readable": "1 hour, 0 minutes"
  }
}
```

**Status Codes:**
- `200 OK`: Application is alive
- `405 Method Not Allowed`: Invalid HTTP method

---

### 4. Detailed Health Check

**Endpoint:** `GET /health/detailed/`

**Description:** Comprehensive health check dengan detailed information untuk semua komponen sistem.

**Request:**
```http
GET /health/detailed/ HTTP/1.1
Host: localhost:8000
```

**Response (Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "response_time_ms": 45.67,
  "checks": {
    "database": {
      "healthy": true,
      "response_time_ms": 12.34,
      "connection_count": 5
    },
    "cache": {
      "healthy": true,
      "response_time_ms": 0.89,
      "backend": "django.core.cache.backends.locmem.LocMemCache"
    },
    "redis": {
      "healthy": true,
      "response_time_ms": 2.45,
      "version": "6.2.6"
    },
    "celery": {
      "healthy": true,
      "active_tasks": 3,
      "workers": 2
    },
    "disk_space": {
      "healthy": true,
      "free_percent": 75.5,
      "free_gb": 150.2,
      "total_gb": 200.0
    },
    "memory": {
      "healthy": true,
      "used_percent": 65.3,
      "available_gb": 2.8,
      "total_gb": 8.0
    },
    "cpu": {
      "healthy": true,
      "usage_percent": 45.2,
      "load_average": [1.2, 1.1, 0.9]
    },
    "external_services": {
      "api_service": {
        "healthy": true,
        "response_time_ms": 234.56
      }
    }
  },
  "summary": {
    "total_checks": 8,
    "healthy_checks": 8,
    "health_percentage": 100.0
  }
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "response_time_ms": 156.78,
  "checks": {
    "database": {
      "healthy": false,
      "error": "Connection timeout"
    },
    "cache": {
      "healthy": true,
      "response_time_ms": 0.89,
      "backend": "django.core.cache.backends.locmem.LocMemCache"
    },
    "redis": {
      "healthy": false,
      "error": "Connection refused"
    },
    "celery": {
      "healthy": false,
      "error": "No workers available"
    },
    "disk_space": {
      "healthy": false,
      "free_percent": 5.2,
      "free_gb": 10.4,
      "total_gb": 200.0,
      "error": "Low disk space"
    },
    "memory": {
      "healthy": false,
      "used_percent": 95.8,
      "available_gb": 0.3,
      "total_gb": 8.0,
      "error": "High memory usage"
    },
    "cpu": {
      "healthy": false,
      "usage_percent": 98.7,
      "load_average": [5.2, 4.8, 4.5],
      "error": "High CPU usage"
    },
    "external_services": {}
  },
  "summary": {
    "total_checks": 7,
    "healthy_checks": 1,
    "health_percentage": 14.3
  }
}
```

**Status Codes:**
- `200 OK`: Health check completed (check individual components for status)
- `405 Method Not Allowed`: Invalid HTTP method

---

### 5. Prometheus Metrics

**Endpoint:** `GET /metrics/`

**Description:** Prometheus-compatible metrics untuk monitoring dan alerting.

**Request:**
```http
GET /metrics/ HTTP/1.1
Host: localhost:8000
```

**Response:**
```
# HELP system_cpu_usage_percent Current CPU usage percentage
# TYPE system_cpu_usage_percent gauge
system_cpu_usage_percent 45.2

# HELP system_memory_total_bytes Total system memory in bytes
# TYPE system_memory_total_bytes gauge
system_memory_total_bytes 8589934592

# HELP system_memory_available_bytes Available system memory in bytes
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes 3006477312

# HELP system_memory_usage_percent Memory usage percentage
# TYPE system_memory_usage_percent gauge
system_memory_usage_percent 65.0

# HELP system_disk_usage_percent Disk usage percentage
# TYPE system_disk_usage_percent gauge
system_disk_usage_percent 24.5

# HELP system_disk_total_bytes Total disk space in bytes
# TYPE system_disk_total_bytes gauge
system_disk_total_bytes 214748364800

# HELP system_disk_used_bytes Used disk space in bytes
# TYPE system_disk_used_bytes gauge
system_disk_used_bytes 52613349376

# HELP django_database_connection_status Database connection status (1=healthy, 0=unhealthy)
# TYPE django_database_connection_status gauge
django_database_connection_status 1

# HELP django_application_uptime_seconds Application uptime in seconds
# TYPE django_application_uptime_seconds counter
django_application_uptime_seconds 3600.45

# HELP application_health_status Overall application health status (1=healthy, 0=unhealthy)
# TYPE application_health_status gauge
application_health_status 1
```

**Headers:**
- `Content-Type: text/plain; version=0.0.4; charset=utf-8`

**Status Codes:**
- `200 OK`: Metrics retrieved successfully
- `405 Method Not Allowed`: Invalid HTTP method

---

## Error Responses

### 405 Method Not Allowed

Semua endpoints hanya menerima GET requests. Jika method lain digunakan:

**Response:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>405 Method Not Allowed</title>
</head>
<body>
    <h1>405 Method Not Allowed</h1>
    <p>The requested method is not allowed for this endpoint.</p>
</body>
</html>
```

**Status Code:** `405 Method Not Allowed`

---

## Usage Examples

### cURL Examples

```bash
# Basic health check
curl -X GET http://localhost:8000/health/

# Readiness check
curl -X GET http://localhost:8000/health/ready/

# Liveness check
curl -X GET http://localhost:8000/health/live/

# Detailed health check
curl -X GET http://localhost:8000/health/detailed/

# Prometheus metrics
curl -X GET http://localhost:8000/metrics/

# Test method restriction (should return 405)
curl -X POST http://localhost:8000/health/
```

### Python Examples

```python
import requests

# Basic health check
response = requests.get('http://localhost:8000/health/')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Detailed health check
response = requests.get('http://localhost:8000/health/detailed/')
health_data = response.json()
print(f"Overall Status: {health_data['status']}")
print(f"Health Percentage: {health_data['summary']['health_percentage']}%")

# Prometheus metrics
response = requests.get('http://localhost:8000/metrics/')
print(f"Metrics:\n{response.text}")
```

### JavaScript Examples

```javascript
// Basic health check
fetch('/health/')
  .then(response => response.json())
  .then(data => {
    console.log('Health Status:', data.status);
    console.log('Timestamp:', data.timestamp);
  })
  .catch(error => console.error('Error:', error));

// Detailed health check
fetch('/health/detailed/')
  .then(response => response.json())
  .then(data => {
    console.log('Overall Status:', data.status);
    console.log('Database Health:', data.checks.database.healthy);
    console.log('Health Percentage:', data.summary.health_percentage + '%');
  })
  .catch(error => console.error('Error:', error));
```

---

## Integration Examples

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: horilla
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
```

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'horilla'
    static_configs:
      - targets: ['horilla:8000']
    metrics_path: '/metrics/'
    scrape_interval: 15s
    scrape_timeout: 10s
    honor_labels: true
```

### Docker Health Check

```dockerfile
FROM python:3.9

# Application setup...

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

---

## Rate Limiting

Saat ini tidak ada rate limiting yang diimplementasi, tetapi struktur sudah siap untuk implementasi:

```python
# Future implementation
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/m', method='GET')
@require_http_methods(["GET"])
def metrics_view(request):
    # Implementation
```

---

## Monitoring Best Practices

1. **Health Check Frequency**:
   - Liveness: 10-30 seconds
   - Readiness: 5-10 seconds
   - Detailed: 1-5 minutes

2. **Metrics Scraping**:
   - Prometheus: 15-30 seconds
   - Avoid too frequent scraping

3. **Alerting Thresholds**:
   - CPU > 80% for 5 minutes
   - Memory > 90% for 2 minutes
   - Disk > 85% for 10 minutes
   - Health percentage < 70%

4. **Timeout Settings**:
   - Health checks: 3-5 seconds
   - Metrics: 10 seconds
   - Detailed checks: 30 seconds