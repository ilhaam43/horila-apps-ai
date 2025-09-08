# Monitoring System Documentation

## Overview

Sistem monitoring Horilla menyediakan comprehensive health checks, metrics collection, dan security monitoring untuk memastikan SLA 99.99% uptime. Sistem ini dirancang dengan prinsip redundancy dan real-time monitoring.

## Features

### 1. Health Check Endpoints

#### Basic Health Check (`/health/`)
- **Method**: GET only
- **Purpose**: Basic application health status
- **Response**: JSON dengan status, timestamp, dan version
- **Use Case**: Load balancer health checks

#### Readiness Check (`/health/ready/`)
- **Method**: GET only
- **Purpose**: Kubernetes readiness probe
- **Checks**: Database, cache, migrations
- **Response**: Detailed status untuk setiap komponen

#### Liveness Check (`/health/live/`)
- **Method**: GET only
- **Purpose**: Kubernetes liveness probe
- **Checks**: Basic application uptime
- **Response**: Uptime information

#### Detailed Health Check (`/health/detailed/`)
- **Method**: GET only
- **Purpose**: Comprehensive system status
- **Checks**: Database, cache, Redis, Celery, disk, memory, CPU
- **Response**: Detailed metrics untuk semua komponen

### 2. Metrics Collection (`/metrics/`)

- **Method**: GET only (enforced by `@require_http_methods`)
- **Format**: Prometheus-compatible metrics
- **Content-Type**: `text/plain; version=0.0.4; charset=utf-8`
- **Metrics Included**:
  - System CPU usage
  - Memory usage (total, available, used)
  - Disk usage (total, used, percentage)
  - Django database connection status
  - Application uptime
  - Health status summary

### 3. Security Features

- **HTTP Method Restriction**: Semua endpoints hanya menerima GET requests
- **405 Error Handling**: Custom middleware untuk proper HTTP 405 responses
- **No Sensitive Data**: Endpoints tidak mengekspos informasi sensitif
- **Rate Limiting Ready**: Struktur siap untuk implementasi rate limiting

## Architecture

### Components

1. **Views** (`monitoring/views.py`)
   - Function-based views dengan security decorators
   - Modular health check functions
   - Prometheus metrics generation

2. **URLs** (`monitoring/urls.py`)
   - RESTful endpoint structure
   - Clear naming convention

3. **Tests** (`monitoring/tests.py`)
   - Comprehensive test coverage
   - Security testing
   - Performance testing
   - Integration testing

4. **Middleware Integration**
   - Custom `MethodNotAllowedMiddleware` untuk proper 405 handling
   - Thread-local middleware untuk request context

### Security Implementation

```python
# HTTP Method Restriction
@require_http_methods(["GET"])
def metrics_view(request):
    # Implementation

# Custom Middleware untuk 405 Handling
class MethodNotAllowedMiddleware:
    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, HttpResponseNotAllowed):
            rendered_response = render(request, "405.html")
            rendered_response.status_code = 405
            return rendered_response
        return response
```

## Usage

### For Kubernetes

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: horilla
    livenessProbe:
      httpGet:
        path: /health/live/
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health/ready/
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
```

### For Prometheus

```yaml
scrape_configs:
  - job_name: 'horilla'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/'
    scrape_interval: 15s
```

### For Load Balancer

```nginx
upstream horilla {
    server 127.0.0.1:8000;
    # Health check
    check interval=3000 rise=2 fall=5 timeout=1000 type=http;
    check_http_send "GET /health/ HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx http_3xx;
}
```

## Testing

### Running Tests

```bash
# All monitoring tests
python manage.py test monitoring

# Security tests only
python manage.py test monitoring.tests.MonitoringSecurityTests

# Performance tests
python manage.py test monitoring.tests.MonitoringPerformanceTests
```

### Test Coverage

- **Security Tests**: HTTP method restrictions, sensitive data exposure
- **Functional Tests**: All endpoints functionality
- **Performance Tests**: Response time, concurrent access
- **Integration Tests**: Database, cache, external services

## Monitoring Metrics

### System Metrics
- `system_cpu_usage_percent`: CPU usage percentage
- `system_memory_total_bytes`: Total system memory
- `system_memory_available_bytes`: Available memory
- `system_memory_usage_percent`: Memory usage percentage
- `system_disk_usage_percent`: Disk usage percentage
- `system_disk_total_bytes`: Total disk space
- `system_disk_used_bytes`: Used disk space

### Application Metrics
- `django_database_connection_status`: Database connectivity (1=healthy, 0=unhealthy)
- `django_application_uptime_seconds`: Application uptime
- `application_health_status`: Overall health status (1=healthy, 0=unhealthy)

## Troubleshooting

### Common Issues

1. **405 Method Not Allowed returning 200**
   - **Cause**: `MethodNotAllowedMiddleware` tidak mengatur status code
   - **Solution**: Middleware sudah diperbaiki untuk mempertahankan status 405

2. **Database Connection Issues**
   - **Check**: `/health/detailed/` untuk database status
   - **Solution**: Verify database configuration dan connectivity

3. **High Memory Usage**
   - **Monitor**: Memory metrics di `/metrics/`
   - **Action**: Scale application atau optimize queries

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger('monitoring').setLevel(logging.DEBUG)

# Test endpoints manually
from django.test import Client
c = Client()
response = c.get('/health/detailed/')
print(response.json())
```

## Performance Considerations

- **Caching**: Health check results dapat di-cache untuk mengurangi load
- **Async**: Pertimbangkan async views untuk high-traffic scenarios
- **Database**: Gunakan connection pooling untuk database checks
- **Monitoring**: Set appropriate scrape intervals untuk Prometheus

## Security Considerations

- **Access Control**: Pertimbangkan authentication untuk detailed endpoints
- **Rate Limiting**: Implementasi rate limiting untuk mencegah abuse
- **Network Security**: Gunakan internal networks untuk monitoring traffic
- **Data Sanitization**: Pastikan tidak ada sensitive data di metrics

## Future Enhancements

1. **Custom Metrics**: Support untuk application-specific metrics
2. **Alerting**: Integration dengan alerting systems
3. **Dashboard**: Web-based monitoring dashboard
4. **Historical Data**: Metrics storage dan trending
5. **Auto-scaling**: Integration dengan Kubernetes HPA

## Dependencies

- `psutil`: System metrics collection
- `django`: Web framework
- `redis` (optional): Redis health checks
- `celery` (optional): Celery health checks

## Configuration

Tidak ada konfigurasi khusus diperlukan. Sistem monitoring menggunakan Django settings yang ada dan auto-detect available services.