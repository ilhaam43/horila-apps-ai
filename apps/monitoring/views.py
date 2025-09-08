import json
import os
import time
import psutil
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views import View
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

try:
    import redis
except ImportError:
    redis = None

try:
    from celery import current_app as celery_app
except ImportError:
    celery_app = None


@method_decorator(require_http_methods(["GET"]), name='dispatch')
class HealthCheckView(View):
    """Basic health check endpoint"""
    
    def get(self, request):
        """Return basic health status"""
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': getattr(settings, 'VERSION', '1.0.0')
        })


@method_decorator(require_http_methods(["GET"]), name='dispatch')
class ReadinessCheckView(View):
    """Readiness check for Kubernetes"""
    
    def get(self, request):
        """Check if application is ready to serve requests"""
        database_check = self._check_database()
        cache_check = self._check_cache()
        migrations_check = self._check_migrations()
        
        all_healthy = database_check and cache_check and migrations_check
        
        return JsonResponse({
            'status': 'ready' if all_healthy else 'not_ready',
            'database': database_check,
            'cache': cache_check,
            'migrations': migrations_check,
            'timestamp': timezone.now().isoformat()
        }, status=200 if all_healthy else 503)
    
    def _check_database(self):
        """Check database connectivity"""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                return True
        except Exception:
            return False
    
    def _check_cache(self):
        """Check cache connectivity"""
        try:
            cache.set('health_check', 'ok', 10)
            return cache.get('health_check') == 'ok'
        except Exception:
            return False
    
    def _check_migrations(self):
        """Check if migrations are up to date"""
        try:
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            return len(plan) == 0
        except Exception:
            return False


@method_decorator(require_http_methods(["GET"]), name='dispatch')
class LivenessCheckView(View):
    """Liveness check for Kubernetes"""
    
    def get(self, request):
        """Check if application is alive"""
        # Simple check - if we can respond, we're alive
        return JsonResponse({
            'status': 'alive',
            'timestamp': timezone.now().isoformat(),
            'uptime': self._get_uptime()
        })
    
    def _get_uptime(self):
        """Get application uptime"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            return {
                'seconds': int(uptime_seconds),
                'human_readable': str(timedelta(seconds=int(uptime_seconds)))
            }
        except Exception:
            return {'seconds': 0, 'human_readable': 'unknown'}


@method_decorator(require_http_methods(["GET"]), name='dispatch')
class DetailedHealthCheckView(View):
    """Detailed health check with system metrics"""
    
    def get(self, request):
        """Return detailed health information"""
        start_time = time.time()
        
        checks = {
            'database': self._check_database_detailed(),
            'cache': self._check_cache_detailed(),
            'redis': self._check_redis(),
            'celery': self._check_celery(),
            'disk_space': self._check_disk_space(),
            'memory': self._check_memory(),
            'cpu': self._check_cpu(),
            'external_services': self._check_external_services()
        }
        
        # Calculate overall health
        critical_services = ['database', 'cache']
        critical_healthy = all(checks[service]['healthy'] for service in critical_services if service in checks)
        
        overall_status = 'healthy' if critical_healthy else 'unhealthy'
        
        response_time = (time.time() - start_time) * 1000
        
        return JsonResponse({
            'status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'response_time_ms': round(response_time, 2),
            'checks': checks,
            'summary': self._generate_summary(checks)
        })
    
    def _check_database_detailed(self):
        """Detailed database health check"""
        try:
            start_time = time.time()
            
            with connection.cursor() as cursor:
                # Test basic connectivity
                cursor.execute('SELECT 1')
                
                # Database-specific queries
                if connection.vendor == 'postgresql':
                    # Check active connections for PostgreSQL
                    cursor.execute("""
                        SELECT count(*) 
                        FROM pg_stat_activity 
                        WHERE state = 'active'
                    """)
                    active_connections = cursor.fetchone()[0]
                    
                    # Check database size for PostgreSQL
                    cursor.execute("""
                        SELECT pg_size_pretty(pg_database_size(current_database()))
                    """)
                    db_size = cursor.fetchone()[0]
                elif connection.vendor == 'sqlite':
                    # SQLite doesn't have active connections concept
                    active_connections = 1  # SQLite is single-connection
                    
                    # Get database file size for SQLite
                    db_path = connection.settings_dict['NAME']
                    if os.path.exists(db_path):
                        size_bytes = os.path.getsize(db_path)
                        db_size = f"{size_bytes / (1024*1024):.2f} MB"
                    else:
                        db_size = "Unknown"
                else:
                    # Default for other databases
                    active_connections = "N/A"
                    db_size = "N/A"
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'healthy': True,
                'response_time_ms': round(response_time, 2),
                'active_connections': active_connections,
                'database_size': db_size,
                'engine': connection.vendor
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_cache_detailed(self):
        """Detailed cache health check"""
        try:
            start_time = time.time()
            
            # Test set/get operations
            test_key = f'health_check_{int(time.time())}'
            cache.set(test_key, 'test_value', 10)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'healthy': retrieved_value == 'test_value',
                'response_time_ms': round(response_time, 2),
                'backend': settings.CACHES['default']['BACKEND']
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_redis(self):
        """Check Redis connectivity"""
        if not redis:
            return {'healthy': False, 'error': 'Redis client not available'}
        
        try:
            # Try to connect to Redis using Django cache settings
            cache_config = settings.CACHES.get('default', {})
            if 'redis' not in cache_config.get('BACKEND', '').lower():
                return {'healthy': False, 'error': 'Redis not configured as cache backend'}
            
            start_time = time.time()
            
            # Test Redis operations
            r = redis.Redis.from_url(getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0'))
            r.ping()
            
            # Get Redis info
            info = r.info()
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'healthy': True,
                'response_time_ms': round(response_time, 2),
                'version': info.get('redis_version'),
                'connected_clients': info.get('connected_clients'),
                'used_memory_human': info.get('used_memory_human')
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_celery(self):
        """Check Celery worker status"""
        if not celery_app:
            return {'healthy': False, 'error': 'Celery not available'}
        
        try:
            # Check active workers
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            
            if not active_workers:
                return {
                    'healthy': False,
                    'error': 'No active Celery workers found'
                }
            
            # Get worker stats
            stats = inspect.stats()
            
            return {
                'healthy': True,
                'active_workers': len(active_workers),
                'worker_names': list(active_workers.keys()),
                'stats': stats
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_disk_space(self):
        """Check available disk space"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            return {
                'healthy': free_percent > 10,  # Alert if less than 10% free
                'free_percent': round(free_percent, 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'total_gb': round(disk_usage.total / (1024**3), 2)
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_memory(self):
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            
            return {
                'healthy': memory.percent < 90,  # Alert if more than 90% used
                'used_percent': memory.percent,
                'available_gb': round(memory.available / (1024**3), 2),
                'total_gb': round(memory.total / (1024**3), 2)
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_cpu(self):
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'healthy': cpu_percent < 80,  # Alert if more than 80% used
                'usage_percent': cpu_percent,
                'cpu_count': psutil.cpu_count()
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_external_services(self):
        """Check external service dependencies"""
        services = {}
        
        # Check Ollama if configured
        ollama_url = getattr(settings, 'OLLAMA_BASE_URL', None)
        if ollama_url:
            services['ollama'] = self._check_http_service(f"{ollama_url}/api/tags")
        
        # Check Elasticsearch if configured
        es_url = getattr(settings, 'ELASTICSEARCH_URL', None)
        if es_url:
            services['elasticsearch'] = self._check_http_service(f"{es_url}/_cluster/health")
        
        # Check N8N if configured
        n8n_url = getattr(settings, 'N8N_BASE_URL', None)
        if n8n_url:
            services['n8n'] = self._check_http_service(f"{n8n_url}/healthz")
        
        return services
    
    def _check_http_service(self, url, timeout=5):
        """Check HTTP service availability"""
        try:
            import requests
            start_time = time.time()
            response = requests.get(url, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            return {
                'healthy': response.status_code == 200,
                'status_code': response.status_code,
                'response_time_ms': round(response_time, 2)
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _generate_summary(self, checks):
        """Generate health summary"""
        total_checks = len(checks)
        healthy_checks = sum(1 for check in checks.values() 
                           if isinstance(check, dict) and check.get('healthy', False))
        
        return {
            'total_checks': total_checks,
            'healthy_checks': healthy_checks,
            'health_percentage': round((healthy_checks / total_checks) * 100, 2) if total_checks > 0 else 0
        }


@require_http_methods(["GET"])
def metrics_view(request):
    """Return metrics in Prometheus format - GET only"""
    metrics = []
    
    # Basic system metrics
    import psutil
    import time
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    metrics.append(f'system_cpu_usage_percent {cpu_percent}')
    
    # Memory usage
    memory = psutil.virtual_memory()
    metrics.append(f'system_memory_usage_percent {memory.percent}')
    metrics.append(f'system_memory_total_bytes {memory.total}')
    metrics.append(f'system_memory_used_bytes {memory.used}')
    
    # Disk usage
    disk = psutil.disk_usage('/')
    metrics.append(f'system_disk_usage_percent {(disk.used / disk.total) * 100:.2f}')
    metrics.append(f'system_disk_total_bytes {disk.total}')
    metrics.append(f'system_disk_used_bytes {disk.used}')
    
    # Django-specific metrics
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            metrics.append('django_database_connection_status 1')
    except Exception:
        metrics.append('django_database_connection_status 0')
    
    # Application uptime (approximate)
    uptime = time.time() - getattr(metrics_view, '_start_time', time.time())
    metrics.append(f'django_application_uptime_seconds {uptime:.2f}')
    
    # Health check summary
    health_data = _get_health_summary()
    if health_data['status'] == 'healthy':
        metrics.append('application_health_status 1')
    else:
        metrics.append('application_health_status 0')
    
    metrics_text = '\n'.join(metrics) + '\n'
    from django.http import HttpResponse
    return HttpResponse(metrics_text, content_type='text/plain; version=0.0.4; charset=utf-8')


def _get_health_summary():
    """Helper function to get basic health status"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return {'status': 'healthy'}
    except Exception:
        return {'status': 'unhealthy'}