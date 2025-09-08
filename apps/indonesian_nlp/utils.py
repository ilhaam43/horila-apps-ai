import re
import string
import unicodedata
import logging
import hashlib
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import statistics

from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import PorterStemmer
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

logger = logging.getLogger(__name__)


class IndonesianTextProcessor:
    """Indonesian text processing utilities"""
    
    def __init__(self):
        self.stemmer = None
        self.stopword_remover = None
        self._setup_processors()
    
    def _setup_processors(self):
        """Setup Indonesian text processors"""
        try:
            # Setup Sastrawi stemmer
            factory = StemmerFactory()
            self.stemmer = factory.create_stemmer()
            
            # Setup stopword remover
            stopword_factory = StopWordRemoverFactory()
            self.stopword_remover = stopword_factory.create_stop_word_remover()
            
            logger.info("Indonesian text processors initialized")
        except Exception as e:
            logger.error(f"Failed to setup Indonesian processors: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize Indonesian text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove phone numbers (Indonesian format)
        text = re.sub(r'\b(?:\+62|62|0)\d{8,13}\b', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{3,}', '...', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove special characters but keep Indonesian characters
        text = re.sub(r'[^\w\s\-.,!?;:()"\']', '', text)
        
        return text.strip()
    
    def normalize_slang(self, text: str) -> str:
        """Normalize Indonesian slang and informal words"""
        # Common Indonesian slang normalization
        slang_dict = {
            'gw': 'saya', 'gue': 'saya', 'aku': 'saya',
            'lo': 'kamu', 'lu': 'kamu', 'elo': 'kamu',
            'udah': 'sudah', 'udh': 'sudah',
            'blm': 'belum', 'blom': 'belum',
            'ga': 'tidak', 'gak': 'tidak', 'nggak': 'tidak',
            'yg': 'yang', 'dgn': 'dengan',
            'krn': 'karena', 'krna': 'karena',
            'tp': 'tapi', 'tpi': 'tapi',
            'bgt': 'banget', 'bgt': 'banget',
            'org': 'orang', 'orng': 'orang',
            'hrs': 'harus', 'hrus': 'harus',
            'jd': 'jadi', 'jdi': 'jadi',
            'bs': 'bisa', 'bsa': 'bisa',
            'gmn': 'gimana', 'gmna': 'gimana',
            'knp': 'kenapa', 'knpa': 'kenapa',
            'emg': 'memang', 'emng': 'memang',
            'skrg': 'sekarang', 'skrang': 'sekarang',
            'bsk': 'besok', 'bsok': 'besok',
            'kmrn': 'kemarin', 'kemaren': 'kemarin'
        }
        
        words = text.split()
        normalized_words = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower in slang_dict:
                normalized_words.append(slang_dict[word_lower])
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def remove_stopwords(self, text: str) -> str:
        """Remove Indonesian stopwords"""
        if self.stopword_remover:
            return self.stopword_remover.remove(text)
        return text
    
    def stem_text(self, text: str) -> str:
        """Stem Indonesian text"""
        if self.stemmer:
            return self.stemmer.stem(text)
        return text
    
    def tokenize_words(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Simple word tokenization for Indonesian
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def tokenize_sentences(self, text: str) -> List[str]:
        """Tokenize text into sentences"""
        # Indonesian sentence tokenization
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[Tuple[str, int]]:
        """Extract keywords from Indonesian text"""
        # Clean and normalize text
        cleaned_text = self.clean_text(text)
        normalized_text = self.normalize_slang(cleaned_text)
        
        # Remove stopwords
        no_stopwords = self.remove_stopwords(normalized_text)
        
        # Tokenize
        words = self.tokenize_words(no_stopwords)
        
        # Filter out short words and numbers
        words = [word for word in words if len(word) > 2 and not word.isdigit()]
        
        # Count word frequency
        word_freq = Counter(words)
        
        return word_freq.most_common(top_k)
    
    def calculate_readability(self, text: str) -> Dict[str, float]:
        """Calculate readability metrics for Indonesian text"""
        sentences = self.tokenize_sentences(text)
        words = self.tokenize_words(text)
        
        if not sentences or not words:
            return {'score': 0.0, 'level': 'unknown'}
        
        # Basic metrics
        num_sentences = len(sentences)
        num_words = len(words)
        num_chars = len(text.replace(' ', ''))
        
        # Average metrics
        avg_words_per_sentence = num_words / num_sentences
        avg_chars_per_word = num_chars / num_words
        
        # Simple readability score (adapted for Indonesian)
        score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_chars_per_word / 4.7)
        
        # Determine readability level
        if score >= 90:
            level = 'very_easy'
        elif score >= 80:
            level = 'easy'
        elif score >= 70:
            level = 'fairly_easy'
        elif score >= 60:
            level = 'standard'
        elif score >= 50:
            level = 'fairly_difficult'
        elif score >= 30:
            level = 'difficult'
        else:
            level = 'very_difficult'
        
        return {
            'score': max(0, min(100, score)),
            'level': level,
            'num_sentences': num_sentences,
            'num_words': num_words,
            'avg_words_per_sentence': avg_words_per_sentence,
            'avg_chars_per_word': avg_chars_per_word
        }


class ModelPerformanceTracker:
    """Track and analyze model performance"""
    
    def __init__(self, cache_timeout: int = 3600):
        self.cache_timeout = cache_timeout
    
    def record_prediction(self, model_name: str, processing_time: float, 
                         confidence: float, success: bool = True):
        """Record a model prediction for performance tracking"""
        cache_key = f"model_perf_{model_name}"
        
        # Get existing data
        data = cache.get(cache_key, {
            'predictions': [],
            'total_count': 0,
            'success_count': 0,
            'avg_processing_time': 0.0,
            'avg_confidence': 0.0
        })
        
        # Add new prediction
        prediction = {
            'timestamp': time.time(),
            'processing_time': processing_time,
            'confidence': confidence,
            'success': success
        }
        
        data['predictions'].append(prediction)
        
        # Keep only last 1000 predictions
        if len(data['predictions']) > 1000:
            data['predictions'] = data['predictions'][-1000:]
        
        # Update aggregated metrics
        data['total_count'] += 1
        if success:
            data['success_count'] += 1
        
        # Calculate averages
        recent_predictions = data['predictions'][-100:]  # Last 100 predictions
        if recent_predictions:
            data['avg_processing_time'] = statistics.mean(
                [p['processing_time'] for p in recent_predictions]
            )
            data['avg_confidence'] = statistics.mean(
                [p['confidence'] for p in recent_predictions if p['success']]
            )
        
        # Cache updated data
        cache.set(cache_key, data, timeout=self.cache_timeout)
    
    def get_model_stats(self, model_name: str) -> Dict[str, Any]:
        """Get performance statistics for a model"""
        cache_key = f"model_perf_{model_name}"
        data = cache.get(cache_key, {})
        
        if not data or not data.get('predictions'):
            return {
                'total_predictions': 0,
                'success_rate': 0.0,
                'avg_processing_time': 0.0,
                'avg_confidence': 0.0,
                'predictions_per_hour': 0.0
            }
        
        predictions = data['predictions']
        now = time.time()
        
        # Filter predictions from last hour
        hour_ago = now - 3600
        recent_predictions = [p for p in predictions if p['timestamp'] > hour_ago]
        
        # Calculate metrics
        total_predictions = len(predictions)
        successful_predictions = [p for p in predictions if p['success']]
        success_rate = len(successful_predictions) / total_predictions if total_predictions > 0 else 0.0
        
        avg_processing_time = statistics.mean(
            [p['processing_time'] for p in predictions]
        ) if predictions else 0.0
        
        avg_confidence = statistics.mean(
            [p['confidence'] for p in successful_predictions]
        ) if successful_predictions else 0.0
        
        predictions_per_hour = len(recent_predictions)
        
        return {
            'total_predictions': total_predictions,
            'success_rate': success_rate,
            'avg_processing_time': avg_processing_time,
            'avg_confidence': avg_confidence,
            'predictions_per_hour': predictions_per_hour,
            'last_prediction': predictions[-1]['timestamp'] if predictions else None
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide performance overview"""
        from .models import NLPModel
        
        models = NLPModel.objects.filter(is_active=True)
        overview = {
            'total_models': models.count(),
            'loaded_models': models.filter(is_loaded=True).count(),
            'model_stats': {}
        }
        
        for model in models:
            stats = self.get_model_stats(model.name)
            overview['model_stats'][model.name] = stats
        
        return overview


class TextAnalysisValidator:
    """Validate text analysis inputs and outputs"""
    
    @staticmethod
    def validate_text_input(text: str, max_length: int = 10000) -> str:
        """Validate text input for analysis"""
        if not text or not isinstance(text, str):
            raise ValidationError(_("Text input is required and must be a string"))
        
        text = text.strip()
        if not text:
            raise ValidationError(_("Text input cannot be empty"))
        
        if len(text) > max_length:
            raise ValidationError(_(f"Text input too long (max {max_length} characters)"))
        
        # Check for suspicious content
        if re.search(r'<script|javascript:|data:', text, re.IGNORECASE):
            raise ValidationError(_("Text contains potentially harmful content"))
        
        return text
    
    @staticmethod
    def validate_model_parameters(parameters: Dict[str, Any], model_type: str) -> Dict[str, Any]:
        """Validate model parameters"""
        if not isinstance(parameters, dict):
            raise ValidationError(_("Parameters must be a dictionary"))
        
        validated_params = {}
        
        # Common parameters
        if 'confidence_threshold' in parameters:
            threshold = parameters['confidence_threshold']
            if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
                raise ValidationError(_("Confidence threshold must be between 0 and 1"))
            validated_params['confidence_threshold'] = float(threshold)
        
        if 'max_length' in parameters:
            max_len = parameters['max_length']
            if not isinstance(max_len, int) or max_len <= 0:
                raise ValidationError(_("Max length must be a positive integer"))
            validated_params['max_length'] = max_len
        
        # Model-specific parameters
        if model_type == 'sentiment':
            if 'return_emotions' in parameters:
                validated_params['return_emotions'] = bool(parameters['return_emotions'])
            if 'return_keywords' in parameters:
                validated_params['return_keywords'] = bool(parameters['return_keywords'])
        
        elif model_type == 'ner':
            if 'entity_types' in parameters:
                entity_types = parameters['entity_types']
                if isinstance(entity_types, list):
                    validated_params['entity_types'] = entity_types
            if 'merge_entities' in parameters:
                validated_params['merge_entities'] = bool(parameters['merge_entities'])
        
        elif model_type == 'classification':
            if 'top_k' in parameters:
                top_k = parameters['top_k']
                if isinstance(top_k, int) and top_k > 0:
                    validated_params['top_k'] = top_k
        
        return validated_params
    
    @staticmethod
    def validate_analysis_result(result: Dict[str, Any], model_type: str) -> bool:
        """Validate analysis result structure"""
        if not isinstance(result, dict):
            return False
        
        # Common validations
        if 'confidence' in result:
            confidence = result['confidence']
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                return False
        
        # Model-specific validations
        if model_type == 'sentiment':
            required_fields = ['sentiment']
            if not all(field in result for field in required_fields):
                return False
            
            if result['sentiment'] not in ['positive', 'negative', 'neutral']:
                return False
        
        elif model_type == 'ner':
            if 'entities' not in result or not isinstance(result['entities'], list):
                return False
            
            for entity in result['entities']:
                if not isinstance(entity, dict):
                    return False
                required_fields = ['text', 'label', 'start', 'end']
                if not all(field in entity for field in required_fields):
                    return False
        
        elif model_type == 'classification':
            required_fields = ['predicted_class']
            if not all(field in result for field in required_fields):
                return False
        
        return True


class CacheManager:
    """Manage caching for NLP operations"""
    
    def __init__(self, default_timeout: int = 3600):
        self.default_timeout = default_timeout
    
    def generate_cache_key(self, text: str, model_name: str, parameters: Dict[str, Any] = None) -> str:
        """Generate cache key for text analysis"""
        # Create a hash of the input
        content = f"{text}:{model_name}"
        if parameters:
            content += f":{json.dumps(parameters, sort_keys=True)}"
        
        return f"nlp_analysis:{hashlib.md5(content.encode()).hexdigest()}"
    
    def get_cached_result(self, text: str, model_name: str, parameters: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        cache_key = self.generate_cache_key(text, model_name, parameters)
        cached_data = cache.get(cache_key)
        if cached_data and isinstance(cached_data, dict) and 'result' in cached_data:
            return cached_data
        return cached_data
    
    def cache_result(self, text: str, model_name: str, result: Dict[str, Any], 
                    parameters: Dict[str, Any] = None, timeout: int = None) -> None:
        """Cache analysis result"""
        cache_key = self.generate_cache_key(text, model_name, parameters)
        cache_timeout = timeout or self.default_timeout
        
        # Add metadata to cached result
        cached_data = {
            'result': result,
            'cached_at': timezone.now().isoformat(),
            'model_name': model_name
        }
        
        cache.set(cache_key, cached_data, timeout=cache_timeout)
    
    def invalidate_model_cache(self, model_name: str) -> int:
        """Invalidate all cached results for a model"""
        # This is a simplified implementation
        # In production, you might want to use cache versioning
        pattern = f"nlp_analysis:*{model_name}*"
        
        # Note: This requires Redis or a cache backend that supports pattern deletion
        try:
            if hasattr(cache, 'delete_pattern'):
                return cache.delete_pattern(pattern)
            else:
                logger.warning("Cache backend doesn't support pattern deletion")
                return 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache for model {model_name}: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if hasattr(cache, 'get_stats'):
                return cache.get_stats()
            else:
                return {'message': 'Cache statistics not available'}
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {'error': str(e)}


class BatchProcessor:
    """Process multiple texts in batches"""
    
    def __init__(self, batch_size: int = 10, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
    
    def create_batches(self, texts: List[str]) -> List[List[str]]:
        """Split texts into batches"""
        batches = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    def estimate_processing_time(self, num_texts: int, avg_time_per_text: float = 0.5) -> float:
        """Estimate total processing time"""
        num_batches = (num_texts + self.batch_size - 1) // self.batch_size
        time_per_batch = self.batch_size * avg_time_per_text
        total_time = num_batches * time_per_batch / self.max_workers
        return total_time
    
    def validate_batch_request(self, texts: List[str], max_texts: int = 1000) -> None:
        """Validate batch processing request"""
        if not texts or not isinstance(texts, list):
            raise ValidationError(_("Texts must be a non-empty list"))
        
        if len(texts) > max_texts:
            raise ValidationError(_(f"Too many texts (max {max_texts})"))
        
        for i, text in enumerate(texts):
            try:
                TextAnalysisValidator.validate_text_input(text)
            except ValidationError as e:
                raise ValidationError(_(f"Text {i+1}: {str(e)}"))


class ErrorHandler:
    """Handle and categorize NLP processing errors"""
    
    ERROR_CATEGORIES = {
        'input_validation': 'Input validation error',
        'model_loading': 'Model loading error',
        'processing': 'Text processing error',
        'memory': 'Memory error',
        'timeout': 'Processing timeout',
        'unknown': 'Unknown error'
    }
    
    @classmethod
    def categorize_error(cls, error: Exception) -> str:
        """Categorize error type"""
        error_str = str(error).lower()
        
        if 'validation' in error_str or 'invalid' in error_str:
            return 'input_validation'
        elif 'memory' in error_str or 'out of memory' in error_str:
            return 'memory'
        elif 'timeout' in error_str or 'time out' in error_str:
            return 'timeout'
        elif 'model' in error_str and ('load' in error_str or 'not found' in error_str):
            return 'model_loading'
        elif any(keyword in error_str for keyword in ['process', 'predict', 'analyze']):
            return 'processing'
        else:
            return 'unknown'
    
    @classmethod
    def format_error_response(cls, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format error response"""
        category = cls.categorize_error(error)
        
        response = {
            'error': True,
            'category': category,
            'message': cls.ERROR_CATEGORIES.get(category, 'Unknown error'),
            'detail': str(error),
            'timestamp': timezone.now().isoformat()
        }
        
        if context:
            response['context'] = context
        
        return response
    
    @classmethod
    def log_error(cls, error: Exception, context: Dict[str, Any] = None, level: str = 'error'):
        """Log error with context"""
        category = cls.categorize_error(error)
        
        log_data = {
            'category': category,
            'error': str(error),
            'context': context or {}
        }
        
        if level == 'critical':
            logger.critical(f"Critical NLP error: {json.dumps(log_data)}")
        elif level == 'error':
            logger.error(f"NLP error: {json.dumps(log_data)}")
        elif level == 'warning':
            logger.warning(f"NLP warning: {json.dumps(log_data)}")
        else:
            logger.info(f"NLP info: {json.dumps(log_data)}")


# Utility functions
def get_text_language(text: str) -> str:
    """Detect text language (simplified for Indonesian)"""
    # Simple Indonesian language detection
    indonesian_words = {
        'dan', 'atau', 'yang', 'ini', 'itu', 'dengan', 'untuk', 'dari', 'ke', 'di',
        'pada', 'dalam', 'oleh', 'karena', 'sehingga', 'tetapi', 'namun', 'jika',
        'kalau', 'ketika', 'saat', 'sebelum', 'sesudah', 'setelah', 'selama'
    }
    
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 'unknown'
    
    indonesian_count = sum(1 for word in words if word in indonesian_words)
    indonesian_ratio = indonesian_count / len(words)
    
    if indonesian_ratio > 0.1:  # At least 10% Indonesian words
        return 'indonesian'
    else:
        return 'other'


def format_processing_time(seconds: float) -> str:
    """Format processing time in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity using word overlap"""
    processor = IndonesianTextProcessor()
    
    words1 = set(processor.tokenize_words(processor.clean_text(text1)))
    words2 = set(processor.tokenize_words(processor.clean_text(text2)))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


def extract_text_features(text: str) -> Dict[str, Any]:
    """Extract various features from text"""
    processor = IndonesianTextProcessor()
    
    # Basic features
    char_count = len(text)
    word_count = len(processor.tokenize_words(text))
    sentence_count = len(processor.tokenize_sentences(text))
    
    # Advanced features
    readability = processor.calculate_readability(text)
    keywords = processor.extract_keywords(text, top_k=5)
    
    # Character-level features
    uppercase_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
    digit_ratio = sum(1 for c in text if c.isdigit()) / len(text) if text else 0
    punctuation_ratio = sum(1 for c in text if c in string.punctuation) / len(text) if text else 0
    
    return {
        'char_count': char_count,
        'word_count': word_count,
        'sentence_count': sentence_count,
        'avg_word_length': char_count / word_count if word_count > 0 else 0,
        'avg_sentence_length': word_count / sentence_count if sentence_count > 0 else 0,
        'uppercase_ratio': uppercase_ratio,
        'digit_ratio': digit_ratio,
        'punctuation_ratio': punctuation_ratio,
        'readability_score': readability['score'],
        'readability_level': readability['level'],
        'top_keywords': [kw[0] for kw in keywords],
        'language': get_text_language(text)
    }


# Initialize global instances
class ModelManager:
    """Manages Indonesian NLP models"""
    
    def __init__(self):
        self.models = {}
        self.model_configs = {}
        self.performance_tracker = ModelPerformanceTracker()
    
    def load_model(self, model_name: str, model_path: str = None) -> bool:
        """Load a model"""
        try:
            # Placeholder for model loading logic
            self.models[model_name] = {
                'loaded': True,
                'path': model_path,
                'loaded_at': timezone.now()
            }
            logger.info(f"Model {model_name} loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            return False
    
    def get_model(self, model_name: str):
        """Get a loaded model"""
        return self.models.get(model_name)
    
    def is_model_loaded(self, model_name: str) -> bool:
        """Check if model is loaded"""
        return model_name in self.models and self.models[model_name].get('loaded', False)
    
    def unload_model(self, model_name: str) -> bool:
        """Unload a model"""
        if model_name in self.models:
            del self.models[model_name]
            logger.info(f"Model {model_name} unloaded")
            return True
        return False
    
    def get_loaded_models(self) -> List[str]:
        """Get list of loaded models"""
        return list(self.models.keys())
    
    @classmethod
    def initialize_default_models(cls):
        """Initialize default NLP models"""
        try:
            from .models import NLPModel
            
            # Create default sentiment analysis model
            if not NLPModel.objects.filter(name='default_sentiment', model_type='sentiment').exists():
                NLPModel.objects.create(
                    name='default_sentiment',
                    description='Default Indonesian sentiment analysis model',
                    model_type='sentiment',
                    framework='nltk',
                    model_path='vader_lexicon',
                    config={'language': 'indonesian'},
                    is_active=True
                )
                logger.info("Created default sentiment analysis model")
            
            # Create default NER model
            if not NLPModel.objects.filter(name='default_ner', model_type='ner').exists():
                NLPModel.objects.create(
                    name='default_ner',
                    description='Default Indonesian named entity recognition model',
                    model_type='ner',
                    framework='spacy',
                    model_path='id_core_news_sm',
                    config={'language': 'indonesian'},
                    is_active=True
                )
                logger.info("Created default NER model")
                
        except Exception as e:
            logger.error(f"Failed to initialize default models: {str(e)}")


text_processor = IndonesianTextProcessor()
performance_tracker = ModelPerformanceTracker()
cache_manager = CacheManager()
batch_processor = BatchProcessor()
model_manager = ModelManager()