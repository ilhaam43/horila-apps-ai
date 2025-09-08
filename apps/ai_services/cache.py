from django.core.cache import cache
from django.conf import settings
import json
import hashlib
from functools import wraps
from typing import Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class AICache:
    """
    Advanced caching system for AI services with intelligent cache management
    """
    
    # Cache timeouts in seconds
    CACHE_TIMEOUTS = {
        'prediction': 3600,  # 1 hour
        'embedding': 86400,  # 24 hours
        'nlp_analysis': 7200,  # 2 hours
        'search_results': 1800,  # 30 minutes
        'model_config': 43200,  # 12 hours
        'document_classification': 3600,  # 1 hour
    }
    
    @staticmethod
    def generate_cache_key(prefix: str, data: Any) -> str:
        """
        Generate a consistent cache key from data
        """
        if isinstance(data, dict):
            # Sort dict keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, (list, tuple)):
            data_str = json.dumps(sorted(data) if all(isinstance(x, (str, int, float)) for x in data) else list(data))
        else:
            data_str = str(data)
        
        # Create hash of the data
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:16]
        return f"ai_cache:{prefix}:{data_hash}"
    
    @classmethod
    def get(cls, prefix: str, data: Any) -> Optional[Any]:
        """
        Get cached result
        """
        try:
            cache_key = cls.generate_cache_key(prefix, data)
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result
            logger.debug(f"Cache miss for {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @classmethod
    def set(cls, prefix: str, data: Any, result: Any, timeout: Optional[int] = None) -> bool:
        """
        Set cached result
        """
        try:
            cache_key = cls.generate_cache_key(prefix, data)
            if timeout is None:
                timeout = cls.CACHE_TIMEOUTS.get(prefix, 3600)
            
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache set for {cache_key} with timeout {timeout}s")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @classmethod
    def delete(cls, prefix: str, data: Any) -> bool:
        """
        Delete cached result
        """
        try:
            cache_key = cls.generate_cache_key(prefix, data)
            cache.delete(cache_key)
            logger.debug(f"Cache deleted for {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    @classmethod
    def clear_prefix(cls, prefix: str) -> bool:
        """
        Clear all cache entries with given prefix
        """
        try:
            # This is a simplified version - in production, you might want to use Redis SCAN
            pattern = f"ai_cache:{prefix}:*"
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(pattern)
            logger.info(f"Cleared cache for pattern {pattern}")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

def cache_ai_result(cache_type: str, timeout: Optional[int] = None):
    """
    Decorator for caching AI function results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function arguments
            cache_data = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            
            # Try to get from cache first
            cached_result = AICache.get(cache_type, cache_data)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            AICache.set(cache_type, cache_data, result, timeout)
            
            return result
        return wrapper
    return decorator

class EmbeddingCache:
    """
    Specialized cache for embedding vectors
    """
    
    @staticmethod
    def get_text_embedding(text: str, model_name: str) -> Optional[list]:
        """
        Get cached embedding for text
        """
        cache_data = {'text': text, 'model': model_name}
        return AICache.get('embedding', cache_data)
    
    @staticmethod
    def set_text_embedding(text: str, model_name: str, embedding: list) -> bool:
        """
        Cache embedding for text
        """
        cache_data = {'text': text, 'model': model_name}
        return AICache.set('embedding', cache_data, embedding)

class ModelCache:
    """
    Cache for AI model configurations and metadata
    """
    
    @staticmethod
    def get_model_config(model_name: str, version: str) -> Optional[dict]:
        """
        Get cached model configuration
        """
        cache_data = {'model': model_name, 'version': version}
        return AICache.get('model_config', cache_data)
    
    @staticmethod
    def set_model_config(model_name: str, version: str, config: dict) -> bool:
        """
        Cache model configuration
        """
        cache_data = {'model': model_name, 'version': version}
        return AICache.set('model_config', cache_data, config)

# Cache warming functions
def warm_embedding_cache():
    """
    Pre-populate embedding cache with common queries
    """
    common_queries = [
        "employee handbook",
        "leave policy",
        "salary information",
        "performance review",
        "training materials"
    ]
    
    # This would be implemented with actual embedding generation
    logger.info(f"Warming embedding cache with {len(common_queries)} common queries")

def warm_model_cache():
    """
    Pre-populate model cache with active model configurations
    """
    from .models import AIModelRegistry
    
    active_models = AIModelRegistry.objects.filter(is_active=True)
    for model in active_models:
        ModelCache.set_model_config(model.name, model.version, model.get_config())
    
    logger.info(f"Warmed model cache with {active_models.count()} active models")