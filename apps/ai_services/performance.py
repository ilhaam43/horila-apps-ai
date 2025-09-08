from django.core.cache import cache
from django.db import connection
from django.conf import settings
from celery import group, chain
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Callable
from functools import wraps
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .cache import AICache, EmbeddingCache, ModelCache
# from .tasks import (
#     # process_budget_prediction,  # Commented out - function removed from tasks.py
#     classify_document_async,
#     analyze_text_sentiment,
#     perform_intelligent_search,
#     execute_rag_n8n_workflow
# )
# All task imports commented out - functions removed from tasks.py for HR focus
from .models import AIServiceLog, AIAnalytics

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """
    Advanced performance optimization for AI services
    """
    
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.performance_metrics = {}
        self.active_connections = 0
        self.max_connections = getattr(settings, 'AI_MAX_CONNECTIONS', 50)
    
    def monitor_performance(self, func_name: str):
        """Decorator to monitor function performance"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                    raise
                finally:
                    end_time = time.time()
                    memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    
                    # Record performance metrics
                    self.record_performance_metric(
                        func_name=func_name,
                        execution_time=end_time - start_time,
                        memory_used=memory_after - memory_before,
                        success=success,
                        error=error
                    )
                
                return result
            return wrapper
        return decorator
    
    def record_performance_metric(self, func_name: str, execution_time: float, 
                                memory_used: float, success: bool, error: Optional[str] = None):
        """Record performance metrics"""
        try:
            metric_key = f"perf:{func_name}"
            current_metrics = cache.get(metric_key, [])
            
            metric = {
                'timestamp': time.time(),
                'execution_time': execution_time,
                'memory_used': memory_used,
                'success': success,
                'error': error
            }
            
            current_metrics.append(metric)
            
            # Keep only last 100 metrics per function
            if len(current_metrics) > 100:
                current_metrics = current_metrics[-100:]
            
            cache.set(metric_key, current_metrics, timeout=3600)  # 1 hour
            
            # Log critical performance issues
            if execution_time > 10:  # More than 10 seconds
                logger.warning(f"Slow execution detected: {func_name} took {execution_time:.2f}s")
            
            if memory_used > 100:  # More than 100MB
                logger.warning(f"High memory usage detected: {func_name} used {memory_used:.2f}MB")
                
        except Exception as e:
            logger.error(f"Failed to record performance metric: {e}")
    
    def get_performance_stats(self, func_name: str) -> Dict[str, Any]:
        """Get performance statistics for a function"""
        try:
            metric_key = f"perf:{func_name}"
            metrics = cache.get(metric_key, [])
            
            if not metrics:
                return {'error': 'No metrics available'}
            
            execution_times = [m['execution_time'] for m in metrics if m['success']]
            memory_usage = [m['memory_used'] for m in metrics if m['success']]
            
            if not execution_times:
                return {'error': 'No successful executions'}
            
            return {
                'total_calls': len(metrics),
                'successful_calls': len(execution_times),
                'success_rate': len(execution_times) / len(metrics) * 100,
                'avg_execution_time': sum(execution_times) / len(execution_times),
                'max_execution_time': max(execution_times),
                'min_execution_time': min(execution_times),
                'avg_memory_usage': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'max_memory_usage': max(memory_usage) if memory_usage else 0
            }
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {'error': str(e)}

class BatchProcessor:
    """
    Batch processing for AI operations to improve efficiency
    """
    
    def __init__(self, batch_size: int = 10, max_workers: int = 5):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    
    def process_documents_batch(self, document_paths: List[str], user_id: int) -> List[Dict[str, Any]]:
        """Process multiple documents in batches - DISABLED: task functions removed"""
        logger.warning("Document batch processing disabled - task functions removed for HR focus")
        return [{'error': 'Document processing disabled', 'document': path} for path in document_paths]
    
    def process_text_analysis_batch(self, texts: List[str], user_id: int, 
                                  analysis_type: str = 'sentiment') -> List[Dict[str, Any]]:
        """Process multiple texts for NLP analysis in batches - DISABLED: task functions removed"""
        logger.warning("Text analysis batch processing disabled - task functions removed for HR focus")
        return [{'error': 'Text analysis processing disabled', 'text': text[:50] + '...'} for text in texts]

class ConnectionPool:
    """
    Connection pool manager for external AI services
    """
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self.active_connections = 0
        self.connection_lock = threading.Lock()
        self.session_pool = []
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get an HTTP session from the pool"""
        with self.connection_lock:
            if self.session_pool:
                return self.session_pool.pop()
            elif self.active_connections < self.max_connections:
                self.active_connections += 1
                connector = aiohttp.TCPConnector(
                    limit=100,
                    limit_per_host=30,
                    keepalive_timeout=30
                )
                return aiohttp.ClientSession(connector=connector)
            else:
                raise Exception("Connection pool exhausted")
    
    async def return_session(self, session: aiohttp.ClientSession):
        """Return session to the pool"""
        with self.connection_lock:
            if len(self.session_pool) < self.max_connections // 2:
                self.session_pool.append(session)
            else:
                await session.close()
                self.active_connections -= 1

class QueryOptimizer:
    """
    Database query optimization for AI services
    """
    
    @staticmethod
    def optimize_ai_queries():
        """Optimize database queries for AI services"""
        try:
            with connection.cursor() as cursor:
                # Create indexes for better performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_ai_prediction_created_at ON ai_services_aiprediction(created_at);",
                    "CREATE INDEX IF NOT EXISTS idx_ai_prediction_user ON ai_services_aiprediction(created_by_id);",
                    "CREATE INDEX IF NOT EXISTS idx_knowledge_base_status ON ai_services_knowledgebase(status);",
                    "CREATE INDEX IF NOT EXISTS idx_document_classification_type ON ai_services_documentclassification(classification_type);",
                    "CREATE INDEX IF NOT EXISTS idx_search_query_created_at ON ai_services_searchquery(created_at);",
                    "CREATE INDEX IF NOT EXISTS idx_nlp_analysis_type ON ai_services_nlpanalysis(analysis_type);",
                    "CREATE INDEX IF NOT EXISTS idx_workflow_execution_status ON ai_services_workflowexecution(status);",
                ]
                
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                        logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                    except Exception as e:
                        logger.warning(f"Index creation failed: {e}")
                
                # Analyze tables for better query planning
                tables = [
                    'ai_services_aiprediction',
                    'ai_services_knowledgebase',
                    'ai_services_documentclassification',
                    'ai_services_searchquery',
                    'ai_services_nlpanalysis',
                    'ai_services_workflowexecution'
                ]
                
                for table in tables:
                    try:
                        cursor.execute(f"ANALYZE {table};")
                    except Exception as e:
                        logger.warning(f"Table analysis failed for {table}: {e}")
                
                logger.info("Database optimization completed")
                
        except Exception as e:
            logger.error(f"Query optimization failed: {e}")

# Global instances
performance_optimizer = PerformanceOptimizer()
batch_processor = BatchProcessor()
connection_pool = ConnectionPool()
query_optimizer = QueryOptimizer()

# Performance monitoring decorators
monitor_budget_ai = performance_optimizer.monitor_performance('budget_ai')
monitor_knowledge_ai = performance_optimizer.monitor_performance('knowledge_ai')
monitor_nlp = performance_optimizer.monitor_performance('indonesian_nlp')
monitor_document_classifier = performance_optimizer.monitor_performance('document_classifier')
monitor_intelligent_search = performance_optimizer.monitor_performance('intelligent_search')
monitor_rag_n8n = performance_optimizer.monitor_performance('rag_n8n')

def get_system_health() -> Dict[str, Any]:
    """Get overall system health metrics"""
    try:
        # CPU and Memory usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database connections
        db_connections = len(connection.queries)
        
        # Cache statistics
        cache_stats = {
            'cache_hits': cache.get('cache_hits', 0),
            'cache_misses': cache.get('cache_misses', 0)
        }
        
        # AI Service performance
        ai_services = ['budget_ai', 'knowledge_ai', 'indonesian_nlp', 
                      'document_classifier', 'intelligent_search', 'rag_n8n']
        
        service_stats = {}
        for service in ai_services:
            stats = performance_optimizer.get_performance_stats(service)
            service_stats[service] = stats
        
        return {
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            },
            'database': {
                'active_connections': db_connections,
                'max_connections': getattr(settings, 'DATABASES', {}).get('default', {}).get('CONN_MAX_AGE', 'unknown')
            },
            'cache': cache_stats,
            'ai_services': service_stats,
            'connection_pool': {
                'active_connections': connection_pool.active_connections,
                'max_connections': connection_pool.max_connections
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return {'error': str(e)}

def optimize_all_services():
    """Run all optimization procedures"""
    try:
        logger.info("Starting comprehensive AI services optimization...")
        
        # 1. Optimize database queries
        query_optimizer.optimize_ai_queries()
        
        # 2. Warm up caches
        from .cache import warm_embedding_cache, warm_model_cache
        warm_embedding_cache()
        warm_model_cache()
        
        # 3. Clear old performance metrics
        cache.delete_many([f"perf:{service}" for service in 
                          ['budget_ai', 'knowledge_ai', 'indonesian_nlp', 
                           'document_classifier', 'intelligent_search', 'rag_n8n']])
        
        logger.info("AI services optimization completed successfully")
        return {'status': 'success', 'message': 'All optimizations applied'}
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return {'status': 'error', 'message': str(e)}