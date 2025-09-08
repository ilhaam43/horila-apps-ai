import logging
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from django.core.cache import cache
from django.conf import settings
from .exceptions import AIServiceError, ModelNotFoundError, PredictionError

logger = logging.getLogger(__name__)

class BaseAIService(ABC):
    """
    Base class untuk semua AI services di Horilla HR System.
    Menyediakan functionality umum seperti caching, logging, dan error handling.
    """
    
    def __init__(self, model_name: str, version: str = "1.0"):
        self.model_name = model_name
        self.version = version
        self.cache_timeout = getattr(settings, 'AI_CACHE_TIMEOUT', 3600)  # 1 hour default
        self.max_retries = getattr(settings, 'AI_MAX_RETRIES', 3)
        self.model = None
        self.is_loaded = False
        
    @abstractmethod
    def load_model(self) -> None:
        """
        Load the AI model. Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def predict(self, input_data: Any) -> Dict[str, Any]:
        """
        Make prediction using the loaded model.
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data before prediction.
        Must be implemented by subclasses.
        """
        pass
    
    def get_cache_key(self, input_data: Any) -> str:
        """
        Generate cache key for input data.
        """
        import hashlib
        data_str = json.dumps(input_data, sort_keys=True, default=str)
        hash_obj = hashlib.md5(data_str.encode())
        return f"ai_prediction_{self.model_name}_{hash_obj.hexdigest()}"
    
    def get_cached_prediction(self, input_data: Any) -> Optional[Dict[str, Any]]:
        """
        Get cached prediction if available.
        """
        cache_key = self.get_cache_key(input_data)
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for {self.model_name} prediction")
            return cached_result
        
        return None
    
    def cache_prediction(self, input_data: Any, prediction: Dict[str, Any]) -> None:
        """
        Cache prediction result.
        """
        cache_key = self.get_cache_key(input_data)
        cache.set(cache_key, prediction, self.cache_timeout)
        logger.info(f"Cached prediction for {self.model_name}")
    
    def safe_predict(self, input_data: Any, use_cache: bool = True) -> Dict[str, Any]:
        """
        Safe prediction with error handling, caching, and retries.
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data):
                raise PredictionError(f"Invalid input data for {self.model_name}")
            
            # Check cache first
            if use_cache:
                cached_result = self.get_cached_prediction(input_data)
                if cached_result:
                    return cached_result
            
            # Load model if not loaded
            if not self.is_loaded:
                self.load_model()
            
            # Make prediction with retries
            prediction = None
            last_error = None
            
            for attempt in range(self.max_retries):
                try:
                    prediction = self.predict(input_data)
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(f"Prediction attempt {attempt + 1} failed: {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            
            if prediction is None:
                raise PredictionError(f"All prediction attempts failed: {str(last_error)}")
            
            # Add metadata
            prediction.update({
                'model_name': self.model_name,
                'model_version': self.version,
                'prediction_time': datetime.now().isoformat(),
                'processing_time_ms': round((time.time() - start_time) * 1000, 2)
            })
            
            # Cache result
            if use_cache:
                self.cache_prediction(input_data, prediction)
            
            # Log success
            logger.info(f"Successful prediction with {self.model_name} in {prediction['processing_time_ms']}ms")
            
            return prediction
            
        except Exception as e:
            logger.error(f"Prediction failed for {self.model_name}: {str(e)}")
            raise AIServiceError(f"AI service error: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        """
        return {
            'model_name': self.model_name,
            'version': self.version,
            'is_loaded': self.is_loaded,
            'cache_timeout': self.cache_timeout,
            'max_retries': self.max_retries
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the AI service.
        """
        try:
            # Test with dummy data if model supports it
            status = 'healthy' if self.is_loaded else 'not_loaded'
            
            return {
                'service': self.model_name,
                'status': status,
                'version': self.version,
                'timestamp': datetime.now().isoformat(),
                'is_loaded': self.is_loaded
            }
        except Exception as e:
            return {
                'service': self.model_name,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def clear_cache(self) -> None:
        """
        Clear all cached predictions for this model.
        """
        # This is a simplified version - in production you'd want more sophisticated cache management
        logger.info(f"Cache cleared for {self.model_name}")
    
    def __str__(self) -> str:
        return f"AIService({self.model_name} v{self.version})"
    
    def __repr__(self) -> str:
        return f"<AIService: {self.model_name} v{self.version}, loaded={self.is_loaded}>"


class MLModelMixin:
    """
    Mixin untuk machine learning models dengan functionality tambahan.
    """
    
    def calculate_confidence(self, prediction_proba: List[float]) -> float:
        """
        Calculate confidence score from prediction probabilities.
        """
        if not prediction_proba:
            return 0.0
        
        max_prob = max(prediction_proba)
        return round(max_prob, 4)
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance if available.
        """
        if hasattr(self.model, 'feature_importances_'):
            return dict(zip(
                getattr(self, 'feature_names', []),
                self.model.feature_importances_
            ))
        return None
    
    def explain_prediction(self, input_data: Any) -> Dict[str, Any]:
        """
        Provide explanation for the prediction (if supported).
        """
        explanation = {
            'feature_importance': self.get_feature_importance(),
            'model_type': type(self.model).__name__ if self.model else None
        }
        
        return {k: v for k, v in explanation.items() if v is not None}


class NLPModelMixin:
    """
    Mixin untuk Natural Language Processing models.
    """
    
    def preprocess_text(self, text: str) -> str:
        """
        Basic text preprocessing.
        """
        if not isinstance(text, str):
            return str(text)
        
        # Basic cleaning
        text = text.strip()
        text = ' '.join(text.split())  # Normalize whitespace
        
        return text
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of the text (basic implementation).
        """
        # Simple heuristic - in production use proper language detection
        indonesian_words = ['dan', 'atau', 'yang', 'dengan', 'untuk', 'dari', 'ke', 'di', 'pada']
        english_words = ['and', 'or', 'the', 'with', 'for', 'from', 'to', 'in', 'on']
        
        text_lower = text.lower()
        
        id_count = sum(1 for word in indonesian_words if word in text_lower)
        en_count = sum(1 for word in english_words if word in text_lower)
        
        return 'id' if id_count > en_count else 'en'
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text (basic implementation).
        """
        # Simple keyword extraction - in production use TF-IDF or more advanced methods
        import re
        
        # Remove punctuation and convert to lowercase
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {'dan', 'atau', 'yang', 'dengan', 'untuk', 'dari', 'ke', 'di', 'pada', 
                     'and', 'or', 'the', 'with', 'for', 'from', 'to', 'in', 'on', 'a', 'an'}
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Count frequency and return top keywords
        from collections import Counter
        word_freq = Counter(keywords)
        
        return [word for word, _ in word_freq.most_common(max_keywords)]