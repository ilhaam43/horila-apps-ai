import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from django.core.cache import cache
from django.conf import settings
from django.db import connection
import logging
import json

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Comprehensive metrics collector for AI services
    Compatible with Prometheus, Grafana, and other monitoring systems
    """
    
    def __init__(self):
        self.metrics = defaultdict(lambda: defaultdict(list))
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(lambda: deque(maxlen=1000))
        self.start_time = time.time()
        self.lock = threading.Lock()
        
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """
        Increment a counter metric
        """
        with self.lock:
            key = self._build_key(name, labels)
            self.counters[key] += value
            
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """
        Set a gauge metric
        """
        with self.lock:
            key = self._build_key(name, labels)
            self.gauges[key] = value
            
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """
        Add observation to histogram
        """
        with self.lock:
            key = self._build_key(name, labels)
            self.histograms[key].append({
                'value': value,
                'timestamp': time.time()
            })
            
    def _build_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """
        Build metric key with labels
        """
        if not labels:
            return name
        
        label_str = ','.join([f'{k}={v}' for k, v in sorted(labels.items())])
        return f'{name}{{{label_str}}}'
        
    def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format
        """
        lines = []
        
        # Counters
        for key, value in self.counters.items():
            lines.append(f'# TYPE {key.split("{")[0]} counter')
            lines.append(f'{key} {value}')
            
        # Gauges
        for key, value in self.gauges.items():
            lines.append(f'# TYPE {key.split("{")[0]} gauge')
            lines.append(f'{key} {value}')
            
        # Histograms
        for key, observations in self.histograms.items():
            if observations:
                values = [obs['value'] for obs in observations]
                lines.append(f'# TYPE {key.split("{")[0]} histogram')
                lines.append(f'{key}_count {len(values)}')
                lines.append(f'{key}_sum {sum(values)}')
                
                # Calculate percentiles
                sorted_values = sorted(values)
                for percentile in [0.5, 0.9, 0.95, 0.99]:
                    idx = int(len(sorted_values) * percentile)
                    if idx < len(sorted_values):
                        lines.append(f'{key}_bucket{{le="{percentile}"}} {sorted_values[idx]}')
                        
        return '\n'.join(lines)
        
    def get_json_metrics(self) -> Dict[str, Any]:
        """
        Export metrics in JSON format
        """
        with self.lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {
                    key: {
                        'count': len(observations),
                        'values': [obs['value'] for obs in observations[-100:]]  # Last 100 values
                    }
                    for key, observations in self.histograms.items()
                },
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time() - self.start_time
            }
    
    def get_counter(self, name: str, labels: Dict[str, str] = None) -> int:
        """
        Get counter value
        """
        key = self._build_key(name, labels)
        return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> float:
        """
        Get gauge value
        """
        key = self._build_key(name, labels)
        return self.gauges.get(key, 0.0)
    
    def get_histogram_avg(self, name: str, labels: Dict[str, str] = None) -> float:
        """
        Get histogram average
        """
        key = self._build_key(name, labels)
        observations = self.histograms.get(key, [])
        if observations:
            values = [obs['value'] for obs in observations]
            return sum(values) / len(values)
        return 0.0
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def get_ai_metrics(self) -> Dict[str, Any]:
        """
        Get AI service specific metrics
        """
        return {
            'total_requests': self.get_counter('ai_predictions_total'),
            'successful_requests': self.get_counter('ai_predictions_total', {'status': 'success'}),
            'failed_requests': self.get_counter('ai_predictions_total', {'status': 'error'}),
            'avg_response_time': self.get_histogram_avg('ai_prediction_duration_seconds'),
            'cache_hits': self.get_counter('ai_cache_operations_total', {'result': 'hit'}),
            'cache_misses': self.get_counter('ai_cache_operations_total', {'result': 'miss'}),
            'models_loaded': self.get_counter('ai_model_loads_total'),
            'timestamp': datetime.now().isoformat()
        }

class AIServiceMetrics:
    """
    Specific metrics for AI services
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        
    def record_prediction_request(self, service_name: str, model_name: str, 
                                success: bool, duration: float, 
                                input_size: int = None):
        """
        Record AI prediction request metrics
        """
        labels = {
            'service': service_name,
            'model': model_name,
            'status': 'success' if success else 'error'
        }
        
        self.collector.increment_counter('ai_predictions_total', 1, labels)
        self.collector.observe_histogram('ai_prediction_duration_seconds', duration, labels)
        
        if input_size:
            self.collector.observe_histogram('ai_input_size_bytes', input_size, labels)
            
    def record_cache_operation(self, operation: str, hit: bool, service: str):
        """
        Record cache operation metrics
        """
        labels = {
            'operation': operation,
            'service': service,
            'result': 'hit' if hit else 'miss'
        }
        
        self.collector.increment_counter('ai_cache_operations_total', 1, labels)
        
    def record_model_load(self, model_name: str, load_time: float, success: bool):
        """
        Record model loading metrics
        """
        labels = {
            'model': model_name,
            'status': 'success' if success else 'error'
        }
        
        self.collector.increment_counter('ai_model_loads_total', 1, labels)
        self.collector.observe_histogram('ai_model_load_duration_seconds', load_time, labels)
        
    def record_batch_processing(self, service: str, batch_size: int, 
                              processing_time: float, success_count: int):
        """
        Record batch processing metrics
        """
        labels = {'service': service}
        
        self.collector.observe_histogram('ai_batch_size', batch_size, labels)
        self.collector.observe_histogram('ai_batch_processing_duration_seconds', processing_time, labels)
        self.collector.set_gauge('ai_batch_success_rate', success_count / batch_size if batch_size > 0 else 0, labels)

class SystemMetrics:
    """
    System-level metrics collection
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        
    def collect_system_metrics(self):
        """
        Collect current system metrics
        """
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.collector.set_gauge('system_cpu_usage_percent', cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.collector.set_gauge('system_memory_usage_percent', memory.percent)
            self.collector.set_gauge('system_memory_available_bytes', memory.available)
            self.collector.set_gauge('system_memory_total_bytes', memory.total)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.collector.set_gauge('system_disk_usage_percent', disk.percent)
            self.collector.set_gauge('system_disk_free_bytes', disk.free)
            self.collector.set_gauge('system_disk_total_bytes', disk.total)
            
            # Network metrics
            network = psutil.net_io_counters()
            self.collector.set_gauge('system_network_bytes_sent', network.bytes_sent)
            self.collector.set_gauge('system_network_bytes_recv', network.bytes_recv)
            
            # Process metrics
            process = psutil.Process()
            self.collector.set_gauge('process_memory_rss_bytes', process.memory_info().rss)
            self.collector.set_gauge('process_cpu_percent', process.cpu_percent())
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            
    def collect_database_metrics(self):
        """
        Collect database connection metrics
        """
        try:
            # Database connection pool metrics
            db_connections = len(connection.queries)
            self.collector.set_gauge('database_connections_active', db_connections)
            
            # Query performance (if available)
            if hasattr(connection, 'queries_log'):
                recent_queries = connection.queries_log.get_stats()
                if recent_queries:
                    avg_time = sum(float(q.get('time', 0)) for q in recent_queries) / len(recent_queries)
                    self.collector.set_gauge('database_query_avg_duration_seconds', avg_time)
                    
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")

class MetricsExporter:
    """
    Export metrics to various monitoring systems
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        
    def export_to_cache(self, key_prefix: str = 'ai_metrics'):
        """
        Export metrics to Django cache for API access
        """
        try:
            metrics_data = self.collector.get_json_metrics()
            cache.set(f'{key_prefix}_current', metrics_data, timeout=300)  # 5 minutes
            
            # Store historical data
            historical_key = f'{key_prefix}_history'
            history = cache.get(historical_key, [])
            history.append({
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics_data
            })
            
            # Keep only last 24 hours of data (assuming 5-minute intervals)
            if len(history) > 288:  # 24 * 60 / 5
                history = history[-288:]
                
            cache.set(historical_key, history, timeout=86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error exporting metrics to cache: {e}")
            
    def export_to_file(self, filepath: str, format: str = 'json'):
        """
        Export metrics to file
        """
        try:
            if format == 'json':
                data = self.collector.get_json_metrics()
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            elif format == 'prometheus':
                data = self.collector.get_prometheus_metrics()
                with open(filepath, 'w') as f:
                    f.write(data)
                    
        except Exception as e:
            logger.error(f"Error exporting metrics to file: {e}")

# Global metrics instances
metrics_collector = MetricsCollector()
ai_metrics = AIServiceMetrics(metrics_collector)
system_metrics = SystemMetrics(metrics_collector)
metrics_exporter = MetricsExporter(metrics_collector)

# Decorator for automatic metrics collection
def track_ai_performance(service_name: str, model_name: str = None):
    """
    Decorator to automatically track AI service performance
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                logger.error(f"Error in {service_name}: {e}")
                raise
            finally:
                duration = time.time() - start_time
                ai_metrics.record_prediction_request(
                    service_name=service_name,
                    model_name=model_name or 'default',
                    success=success,
                    duration=duration
                )
                
        return wrapper
    return decorator

# Background metrics collection
def start_metrics_collection(interval: int = 60):
    """
    Start background metrics collection
    """
    def collect_metrics():
        while True:
            try:
                system_metrics.collect_system_metrics()
                system_metrics.collect_database_metrics()
                metrics_exporter.export_to_cache()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                time.sleep(interval)
                
    thread = threading.Thread(target=collect_metrics, daemon=True)
    thread.start()
    logger.info(f"Started metrics collection with {interval}s interval")

# Export for use in other modules
__all__ = [
    'metrics_collector',
    'ai_metrics', 
    'system_metrics',
    'metrics_exporter',
    'track_ai_performance',
    'start_metrics_collection'
]