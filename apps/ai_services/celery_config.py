from celery import Celery
from celery.schedules import crontab
from django.conf import settings
import os

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')

app = Celery('ai_services')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery Beat Schedule for AI Services
app.conf.beat_schedule = {
    # Performance optimization every 6 hours
    'optimize-ai-performance': {
        'task': 'ai_services.tasks.optimize_ai_performance_task',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    
    # Cache cleanup every 2 hours
    'cleanup-ai-cache': {
        'task': 'ai_services.tasks.cleanup_cache_task',
        'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
    },
    
    # Generate AI analytics daily at 2 AM
    'generate-ai-analytics': {
        'task': 'ai_services.tasks.generate_ai_analytics_task',
        'schedule': crontab(minute=0, hour=2),  # Daily at 2 AM
    },
    
    # Health check every 30 minutes
    'ai-health-check': {
        'task': 'ai_services.tasks.ai_health_check_task',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Model performance monitoring every hour
    'monitor-model-performance': {
        'task': 'ai_services.tasks.monitor_model_performance_task',
        'schedule': crontab(minute=0),  # Every hour
    },
    
    # Batch process pending AI requests every 15 minutes
    'process-batch-ai-requests': {
        'task': 'ai_services.tasks.process_batch_ai_requests_task',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}

# Celery Configuration
app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Jakarta',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'ai_services.tasks.classify_document_task': {'queue': 'ai_processing'},
        'ai_services.tasks.nlp_analysis_task': {'queue': 'ai_processing'},
        'ai_services.tasks.intelligent_search_task': {'queue': 'ai_processing'},
        'ai_services.tasks.rag_n8n_workflow_task': {'queue': 'ai_processing'},
        'ai_services.tasks.optimize_ai_performance_task': {'queue': 'maintenance'},
        'ai_services.tasks.cleanup_cache_task': {'queue': 'maintenance'},
        'ai_services.tasks.generate_ai_analytics_task': {'queue': 'analytics'},
        'ai_services.tasks.ai_health_check_task': {'queue': 'monitoring'},
        'ai_services.tasks.monitor_model_performance_task': {'queue': 'monitoring'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Result backend
    result_backend='redis://localhost:6379/1',
    result_expires=3600,  # 1 hour
    
    # Broker settings
    broker_url='redis://localhost:6379/0',
    broker_transport_options={
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True
    },
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# AI Service specific configurations
AI_TASK_CONFIG = {
    'max_retries': 3,
    'retry_delay': 60,  # seconds
    'batch_size': 10,
    'timeout': 300,  # 5 minutes
}

# Performance monitoring thresholds
PERFORMANCE_THRESHOLDS = {
    'response_time_warning': 2.0,  # seconds
    'response_time_critical': 5.0,  # seconds
    'memory_usage_warning': 80,    # percentage
    'memory_usage_critical': 95,   # percentage
    'cpu_usage_warning': 80,       # percentage
    'cpu_usage_critical': 95,      # percentage
    'cache_hit_rate_warning': 70,  # percentage
    'error_rate_warning': 5,       # percentage
    'error_rate_critical': 10,     # percentage
}

# Cache configuration for AI services
AI_CACHE_CONFIG = {
    'default_timeout': 3600,  # 1 hour
    'embedding_timeout': 86400,  # 24 hours
    'model_config_timeout': 43200,  # 12 hours
    'search_results_timeout': 1800,  # 30 minutes
    'analytics_timeout': 7200,  # 2 hours
}

# Monitoring configuration
MONITORING_CONFIG = {
    'alert_cooldown': 300,  # 5 minutes between same alerts
    'max_alerts_per_hour': 10,
    'notification_channels': ['email', 'slack'],
    'critical_services': ['budget_ai', 'knowledge_ai', 'indonesian_nlp'],
}

# Export configurations for use in tasks
__all__ = [
    'app',
    'AI_TASK_CONFIG',
    'PERFORMANCE_THRESHOLDS',
    'AI_CACHE_CONFIG',
    'MONITORING_CONFIG'
]