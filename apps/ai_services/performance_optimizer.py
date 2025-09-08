#!/usr/bin/env python3
"""
AI Services Performance Optimizer
Optimizes all AI services with caching, async processing, and efficient queries
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import threading
import queue
import psutil
from django.core.cache import cache
from django.conf import settings
from django.db import connection
from django.db.models import QuerySet

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """
    Comprehensive performance optimizer for AI services
    """
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'AI_CACHE_TIMEOUT', 3600)  # 1 hour
        self.batch_size = getattr(settings, 'AI_BATCH_SIZE', 100)
        self.max_workers = getattr(settings, 'AI_MAX_WORKERS', 4)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=2)
        self.request_queue = queue.Queue(maxsize=1000)
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'async_tasks': 0,
            'batch_operations': 0,
            'optimized_queries': 0
        }
        self.lock = threading.Lock()
        
    def cache_result(self, key_prefix: str, timeout: Optional[int] = None):
        """
        Decorator for caching function results
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # Try to get from cache
                result = cache.get(cache_key)
                if result is not None:
                    with self.lock:
                        self.metrics['cache_hits'] += 1
                    logger.debug(f"Cache hit for {cache_key}")
                    return result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                cache_timeout = timeout or self.cache_timeout
                cache.set(cache_key, result, cache_timeout)
                
                with self.lock:
                    self.metrics['cache_misses'] += 1
                logger.debug(f"Cache miss for {cache_key}, result cached")
                return result
            return wrapper
        return decorator
    
    def async_task(self, func):
        """
        Decorator for running tasks asynchronously
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            future = self.thread_pool.submit(func, *args, **kwargs)
            with self.lock:
                self.metrics['async_tasks'] += 1
            return future
        return wrapper
    
    def batch_process(self, items: List[Any], process_func, batch_size: Optional[int] = None):
        """
        Process items in batches for better performance
        """
        batch_size = batch_size or self.batch_size
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = process_func(batch)
            results.extend(batch_results)
            
            with self.lock:
                self.metrics['batch_operations'] += 1
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.01)
        
        return results
    
    def optimize_queryset(self, queryset: QuerySet, select_related: List[str] = None, 
                         prefetch_related: List[str] = None) -> QuerySet:
        """
        Optimize Django QuerySet with select_related and prefetch_related
        """
        optimized_qs = queryset
        
        if select_related:
            optimized_qs = optimized_qs.select_related(*select_related)
        
        if prefetch_related:
            optimized_qs = optimized_qs.prefetch_related(*prefetch_related)
        
        with self.lock:
            self.metrics['optimized_queries'] += 1
        
        return optimized_qs
    
    def monitor_performance(self, func):
        """
        Decorator for monitoring function performance
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                logger.error(f"Performance monitoring caught error in {func.__name__}: {str(e)}")
                success = False
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                duration = end_time - start_time
                memory_delta = end_memory - start_memory
                
                logger.info(f"Performance: {func.__name__} - Duration: {duration:.3f}s, "
                           f"Memory: {memory_delta/1024/1024:.2f}MB, Success: {success}")
            
            return result
        return wrapper
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics
        """
        with self.lock:
            return {
                **self.metrics.copy(),
                'timestamp': datetime.now().isoformat(),
                'thread_pool_active': self.thread_pool._threads,
                'queue_size': self.request_queue.qsize(),
                'system_metrics': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'active_connections': len(connection.queries)
                }
            }
    
    def clear_cache(self, pattern: str = None):
        """
        Clear cache with optional pattern matching
        """
        if pattern:
            # Clear specific pattern (implementation depends on cache backend)
            logger.info(f"Clearing cache pattern: {pattern}")
        else:
            cache.clear()
            logger.info("Cleared all cache")
    
    def shutdown(self):
        """
        Gracefully shutdown the optimizer
        """
        logger.info("Shutting down performance optimizer...")
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        logger.info("Performance optimizer shutdown complete")

class AIServiceOptimizer:
    """
    Specific optimizations for AI services
    """
    
    def __init__(self, performance_optimizer: PerformanceOptimizer):
        self.optimizer = performance_optimizer
    
    @property
    def cache_prediction(self):
        return self.optimizer.cache_result('ai_prediction', timeout=1800)  # 30 minutes
    
    @property
    def cache_model_load(self):
        return self.optimizer.cache_result('ai_model', timeout=7200)  # 2 hours
    
    @property
    def cache_search_results(self):
        return self.optimizer.cache_result('ai_search', timeout=900)  # 15 minutes
    
    @property
    def async_prediction(self):
        return self.optimizer.async_task
    
    @property
    def monitor_ai_performance(self):
        return self.optimizer.monitor_performance
    
    def optimize_batch_predictions(self, inputs: List[Dict[str, Any]], 
                                 prediction_func) -> List[Dict[str, Any]]:
        """
        Optimize batch predictions with caching and async processing
        """
        # Group similar inputs for better caching
        grouped_inputs = self._group_similar_inputs(inputs)
        results = []
        
        for group in grouped_inputs:
            # Use batch processing for each group
            group_results = self.optimizer.batch_process(
                group, 
                lambda batch: [prediction_func(item) for item in batch]
            )
            results.extend(group_results)
        
        return results
    
    def _group_similar_inputs(self, inputs: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group similar inputs for better batch processing
        """
        # Simple grouping by input type/size
        groups = {}
        for item in inputs:
            key = f"{type(item.get('text', ''))}-{len(str(item))//100}"
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        
        return list(groups.values())
    
    def preload_models(self, model_names: List[str]):
        """
        Preload AI models asynchronously
        """
        @self.async_prediction
        def load_model(model_name):
            logger.info(f"Preloading model: {model_name}")
            # Model loading logic would go here
            time.sleep(0.1)  # Simulate loading time
            return f"Model {model_name} loaded"
        
        futures = [load_model(name) for name in model_names]
        return futures

class DatabaseOptimizer:
    """
    Database-specific optimizations
    """
    
    def __init__(self, performance_optimizer: PerformanceOptimizer):
        self.optimizer = performance_optimizer
    
    def optimize_ai_queries(self):
        """
        Apply common optimizations to AI-related database queries
        """
        optimizations = {
            'ai_service_logs': {
                'select_related': ['user', 'service_type'],
                'prefetch_related': ['analytics']
            },
            'ai_analytics': {
                'select_related': ['log'],
                'prefetch_related': []
            }
        }
        
        return optimizations
    
    def bulk_create_logs(self, log_data: List[Dict[str, Any]]):
        """
        Bulk create AI service logs for better performance
        """
        from .models import AIServiceLog
        
        # Process in batches
        batch_size = 100
        for i in range(0, len(log_data), batch_size):
            batch = log_data[i:i + batch_size]
            log_objects = [AIServiceLog(**data) for data in batch]
            AIServiceLog.objects.bulk_create(log_objects, ignore_conflicts=True)
            
            with self.optimizer.lock:
                self.optimizer.metrics['batch_operations'] += 1

# Global optimizer instances
performance_optimizer = PerformanceOptimizer()
ai_service_optimizer = AIServiceOptimizer(performance_optimizer)
database_optimizer = DatabaseOptimizer(performance_optimizer)

# Convenience decorators
cache_prediction = ai_service_optimizer.cache_prediction
cache_model_load = ai_service_optimizer.cache_model_load
cache_search_results = ai_service_optimizer.cache_search_results
async_prediction = ai_service_optimizer.async_prediction
monitor_ai_performance = ai_service_optimizer.monitor_ai_performance

# Utility functions
def get_optimization_metrics() -> Dict[str, Any]:
    """
    Get comprehensive optimization metrics
    """
    return performance_optimizer.get_metrics()

def clear_ai_cache(pattern: str = None):
    """
    Clear AI-related cache
    """
    performance_optimizer.clear_cache(pattern)

def optimize_ai_service(cls):
    """
    Class decorator to optimize an entire AI service
    """
    # Apply optimizations to all methods
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            if 'predict' in attr_name.lower():
                setattr(cls, attr_name, cache_prediction(monitor_ai_performance(attr)))
            elif 'search' in attr_name.lower():
                setattr(cls, attr_name, cache_search_results(monitor_ai_performance(attr)))
            else:
                setattr(cls, attr_name, monitor_ai_performance(attr))
    
    return cls

__all__ = [
    'PerformanceOptimizer',
    'AIServiceOptimizer', 
    'DatabaseOptimizer',
    'performance_optimizer',
    'ai_service_optimizer',
    'database_optimizer',
    'cache_prediction',
    'cache_model_load',
    'cache_search_results',
    'async_prediction',
    'monitor_ai_performance',
    'get_optimization_metrics',
    'clear_ai_cache',
    'optimize_ai_service'
]