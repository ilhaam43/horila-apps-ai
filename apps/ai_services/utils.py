import os
import json
import hashlib
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import base64
import io
from PIL import Image
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# File and Data Processing Utilities
def extract_text_from_file(file_path: str) -> str:
    """Extract text content from various file formats."""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif file_extension == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                logger.warning("PyPDF2 not available, cannot extract PDF text")
                return ""
        
        elif file_extension in ['.doc', '.docx']:
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                logger.warning("python-docx not available, cannot extract Word document text")
                return ""
        
        elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            try:
                import pytesseract
                from PIL import Image
                image = Image.open(file_path)
                text = pytesseract.image_to_string(image)
                return text
            except ImportError:
                logger.warning("pytesseract not available, cannot extract text from image")
                return ""
        
        else:
            logger.warning(f"Unsupported file format: {file_extension}")
            return ""
    
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        return ""

def save_file_to_storage(file_content: bytes, filename: str, subfolder: str = 'ai_uploads') -> str:
    """Save file content to Django storage and return the path."""
    try:
        file_path = f"{subfolder}/{filename}"
        saved_path = default_storage.save(file_path, ContentFile(file_content))
        return saved_path
    except Exception as e:
        logger.error(f"Error saving file {filename}: {str(e)}")
        raise

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get comprehensive file information."""
    try:
        if not os.path.exists(file_path):
            return {'exists': False}
        
        stat = os.stat(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        info = {
            'exists': True,
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'extension': file_extension,
            'created_at': datetime.fromtimestamp(stat.st_ctime),
            'modified_at': datetime.fromtimestamp(stat.st_mtime),
            'is_text': file_extension in ['.txt', '.csv', '.json', '.xml', '.html'],
            'is_document': file_extension in ['.pdf', '.doc', '.docx', '.rtf'],
            'is_image': file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'],
            'is_audio': file_extension in ['.mp3', '.wav', '.flac', '.aac'],
            'is_video': file_extension in ['.mp4', '.avi', '.mov', '.wmv', '.flv']
        }
        
        return info
    
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {str(e)}")
        return {'exists': False, 'error': str(e)}

# Text Processing Utilities
def clean_text(text: str) -> str:
    """Clean and normalize text for AI processing."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters but keep Indonesian characters
    import re
    text = re.sub(r'[^\w\s\u00C0-\u017F\u1E00-\u1EFF]', ' ', text)
    
    # Normalize case
    text = text.lower().strip()
    
    return text

def tokenize_indonesian_text(text: str) -> List[str]:
    """Tokenize Indonesian text with basic preprocessing."""
    try:
        # Try to use NLTK if available
        import nltk
        from nltk.tokenize import word_tokenize
        
        # Download required NLTK data if not present
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        tokens = word_tokenize(text.lower())
        
        # Filter out non-alphabetic tokens
        tokens = [token for token in tokens if token.isalpha() and len(token) > 1]
        
        return tokens
    
    except ImportError:
        # Fallback to simple tokenization
        import re
        tokens = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        return tokens

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text using TF-IDF."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # Tokenize text
        tokens = tokenize_indonesian_text(text)
        if len(tokens) < 3:
            return tokens
        
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=max_keywords,
            stop_words=None,  # We'll handle Indonesian stop words separately
            ngram_range=(1, 2)
        )
        
        # Fit and transform
        tfidf_matrix = vectorizer.fit_transform([' '.join(tokens)])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        
        # Get top keywords
        keyword_scores = list(zip(feature_names, scores))
        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        
        keywords = [kw[0] for kw in keyword_scores[:max_keywords] if kw[1] > 0]
        return keywords
    
    except ImportError:
        # Fallback to simple frequency-based extraction
        tokens = tokenize_indonesian_text(text)
        from collections import Counter
        word_freq = Counter(tokens)
        return [word for word, freq in word_freq.most_common(max_keywords)]

# Caching Utilities
def get_cache_key(service_type: str, operation: str, **kwargs) -> str:
    """Generate a consistent cache key for AI operations."""
    key_parts = [service_type, operation]
    
    # Sort kwargs for consistent key generation
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (dict, list)):
            v = json.dumps(v, sort_keys=True)
        key_parts.append(f"{k}:{v}")
    
    key_string = "|".join(str(part) for part in key_parts)
    
    # Hash the key if it's too long
    if len(key_string) > 200:
        key_string = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"ai_cache:{key_string}"

def cache_ai_result(cache_key: str, result: Any, timeout: int = 3600) -> None:
    """Cache AI operation result."""
    try:
        cache.set(cache_key, result, timeout)
        logger.debug(f"Cached result with key: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache result: {str(e)}")

def get_cached_result(cache_key: str) -> Optional[Any]:
    """Get cached AI operation result."""
    try:
        result = cache.get(cache_key)
        if result is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
        return result
    except Exception as e:
        logger.warning(f"Failed to get cached result: {str(e)}")
        return None

def invalidate_cache_pattern(pattern: str) -> int:
    """Invalidate cache keys matching a pattern."""
    try:
        # This is a simplified version - in production, you might want to use Redis SCAN
        from django.core.cache.backends.base import InvalidCacheBackendError
        
        # For now, we'll just clear the entire cache if pattern matching is not supported
        cache.clear()
        logger.info(f"Cache cleared for pattern: {pattern}")
        return 1
    except Exception as e:
        logger.warning(f"Failed to invalidate cache pattern {pattern}: {str(e)}")
        return 0

# Data Validation Utilities
def validate_input_data(data: Dict[str, Any], required_fields: List[str], 
                       field_types: Optional[Dict[str, type]] = None) -> Tuple[bool, List[str]]:
    """Validate input data for AI services."""
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Field {field} cannot be None")
    
    # Check field types
    if field_types:
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(f"Field {field} must be of type {expected_type.__name__}")
    
    return len(errors) == 0, errors

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    
    # Remove path traversal characters first
    filename = filename.replace('..', '').replace('./', '').replace('\\', '')
    
    # Remove or replace unsafe characters (including forward slashes)
    filename = re.sub(r'[^\w\s._-]', '_', filename)
    
    # Remove leading dots to prevent hidden files
    filename = filename.lstrip('.')
    
    # Remove multiple spaces/underscores
    filename = re.sub(r'[\s_]+', '_', filename)
    
    # Ensure it's not too long
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:90] + ext
    
    # Ensure we have a valid filename
    if not filename or filename.isspace():
        filename = 'sanitized_file'
    
    return filename.strip('_')

# Model Management Utilities
def get_model_path(service_type: str, model_name: str) -> str:
    """Get the file path for a model."""
    models_dir = getattr(settings, 'AI_MODELS_DIR', os.path.join(settings.BASE_DIR, 'ai_models'))
    return os.path.join(models_dir, service_type, f"{model_name}.pkl")

def save_model(model: Any, service_type: str, model_name: str) -> str:
    """Save a trained model to disk."""
    try:
        model_path = get_model_path(service_type, model_name)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        logger.info(f"Model saved: {model_path}")
        return model_path
    
    except Exception as e:
        logger.error(f"Error saving model {service_type}/{model_name}: {str(e)}")
        raise

def load_model(service_type: str, model_name: str) -> Any:
    """Load a trained model from disk."""
    try:
        model_path = get_model_path(service_type, model_name)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        logger.info(f"Model loaded: {model_path}")
        return model
    
    except Exception as e:
        logger.error(f"Error loading model {service_type}/{model_name}: {str(e)}")
        raise

def model_exists(service_type: str, model_name: str) -> bool:
    """Check if a model file exists."""
    model_path = get_model_path(service_type, model_name)
    return os.path.exists(model_path)

# Performance Monitoring Utilities
def measure_execution_time(func):
    """Decorator to measure function execution time."""
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Add execution time to result if it's a dict
            if isinstance(result, dict):
                result['processing_time_ms'] = execution_time
            
            logger.debug(f"Function {func.__name__} executed in {execution_time:.2f}ms")
            return result
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Function {func.__name__} failed after {execution_time:.2f}ms: {str(e)}")
            raise
    
    return wrapper

def log_ai_operation(service_type: str, operation: str, success: bool, 
                    execution_time_ms: float = None, error_message: str = None,
                    extra_data: Dict[str, Any] = None):
    """Log AI operation for monitoring and analytics."""
    try:
        from .models import AIServiceLog
        
        log_level = "INFO" if success else "ERROR"
        message = f"Operation {operation} {'succeeded' if success else 'failed'}"
        
        if error_message:
            message += f": {error_message}"
        
        log_data = extra_data or {}
        if execution_time_ms is not None:
            log_data['execution_time_ms'] = execution_time_ms
        
        AIServiceLog.objects.create(
            service_type=service_type,
            operation=operation,
            log_level=log_level,
            message=message,
            extra_data=log_data
        )
        
    except Exception as e:
        logger.error(f"Failed to log AI operation: {str(e)}")

# Data Conversion Utilities
def numpy_to_json_serializable(obj: Any) -> Any:
    """Convert numpy objects to JSON serializable format."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: numpy_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [numpy_to_json_serializable(item) for item in obj]
    else:
        return obj

def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string."""
    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {str(e)}")
        raise

def decode_base64_to_image(base64_string: str, output_path: str) -> str:
    """Decode base64 string to image file."""
    try:
        image_data = base64.b64decode(base64_string)
        
        with open(output_path, 'wb') as image_file:
            image_file.write(image_data)
        
        return output_path
    except Exception as e:
        logger.error(f"Error decoding base64 image: {str(e)}")
        raise

# Configuration Utilities
def get_ai_config(service_type: str, config_key: str, default_value: Any = None) -> Any:
    """Get AI service configuration value."""
    try:
        from .config import AIConfig
        config = AIConfig()
        service_config = config.get_service_config(service_type)
        return service_config.get(config_key, default_value)
    except Exception as e:
        logger.warning(f"Error getting AI config {service_type}.{config_key}: {str(e)}")
        return default_value

def update_ai_config(service_type: str, config_updates: Dict[str, Any]) -> bool:
    """Update AI service configuration."""
    try:
        # This would typically update a configuration file or database
        # For now, we'll just log the update request
        logger.info(f"Configuration update requested for {service_type}: {config_updates}")
        return True
    except Exception as e:
        logger.error(f"Error updating AI config for {service_type}: {str(e)}")
        return False

# External API Utilities
def make_api_request(url: str, method: str = 'GET', headers: Dict[str, str] = None,
                   data: Dict[str, Any] = None, timeout: int = 30) -> Dict[str, Any]:
    """Make HTTP API request with error handling."""
    try:
        headers = headers or {}
        
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=data, timeout=timeout)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=data, timeout=timeout)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        
        try:
            return response.json()
        except ValueError:
            return {'content': response.text, 'status_code': response.status_code}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {url}: {str(e)}")
        raise

# Security Utilities
def sanitize_user_input(user_input: str, max_length: int = 1000) -> str:
    """Sanitize user input for AI processing."""
    if not isinstance(user_input, str):
        user_input = str(user_input)
    
    # Truncate if too long
    if len(user_input) > max_length:
        user_input = user_input[:max_length]
    
    # Remove potentially dangerous characters
    import re
    user_input = re.sub(r'[<>"\'\/\\]', '', user_input)
    
    # Remove excessive whitespace
    user_input = ' '.join(user_input.split())
    
    return user_input.strip()

def validate_file_upload(file_path: str, allowed_extensions: List[str] = None,
                        max_size_mb: int = 10) -> Tuple[bool, str]:
    """Validate uploaded file for security and size constraints."""
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return False, f"File size ({file_size_mb:.2f}MB) exceeds limit ({max_size_mb}MB)"
        
        # Check file extension
        if allowed_extensions:
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension not in allowed_extensions:
                return False, f"File extension {file_extension} not allowed"
        
        # Basic file content validation (check if it's actually the claimed type)
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                # Validate image file
                with Image.open(file_path) as img:
                    img.verify()
        except Exception:
            return False, "File appears to be corrupted or not a valid image"
        
        return True, "File is valid"
    
    except Exception as e:
        return False, f"Error validating file: {str(e)}"

# Utility Functions for Specific AI Tasks
def prepare_budget_features(budget_data: Dict[str, Any]) -> np.ndarray:
    """Prepare features for budget AI prediction."""
    try:
        # Extract numerical features
        features = []
        
        # Basic budget features
        features.extend([
            float(budget_data.get('current_amount', 0)),
            float(budget_data.get('allocated_amount', 0)),
            float(budget_data.get('spent_amount', 0)),
            int(budget_data.get('days_remaining', 30)),
            int(budget_data.get('department_id', 0)),
            int(budget_data.get('category_id', 0))
        ])
        
        # Historical spending pattern (if available)
        historical_data = budget_data.get('historical_spending', [])
        if historical_data:
            features.extend([
                np.mean(historical_data),
                np.std(historical_data),
                np.max(historical_data),
                np.min(historical_data)
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        return np.array(features).reshape(1, -1)
    
    except Exception as e:
        logger.error(f"Error preparing budget features: {str(e)}")
        raise

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using cosine similarity."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Vectorize texts
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        return float(similarity)
    
    except ImportError:
        # Fallback to simple word overlap
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    except Exception as e:
        logger.error(f"Error calculating text similarity: {str(e)}")
        return 0.0

# Error Handling Utilities
def create_error_response(error_type: str, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        'success': False,
        'error': {
            'type': error_type,
            'message': message,
            'details': details or {},
            'timestamp': timezone.now().isoformat()
        }
    }

def create_success_response(data: Any, message: str = "Operation completed successfully") -> Dict[str, Any]:
    """Create standardized success response."""
    return {
        'success': True,
        'data': data,
        'message': message,
        'timestamp': timezone.now().isoformat()
    }