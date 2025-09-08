class AIServiceError(Exception):
    """
    Base exception untuk semua AI service errors.
    """
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or 'AI_SERVICE_ERROR'
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        return {
            'error': self.error_code,
            'message': self.message,
            'details': self.details
        }


class ModelNotFoundError(AIServiceError):
    """
    Exception ketika AI model tidak ditemukan atau tidak bisa dimuat.
    """
    def __init__(self, model_name: str, details: dict = None):
        message = f"AI model '{model_name}' not found or could not be loaded"
        super().__init__(message, 'MODEL_NOT_FOUND', details)
        self.model_name = model_name


class PredictionError(AIServiceError):
    """
    Exception ketika terjadi error saat melakukan prediksi.
    """
    def __init__(self, message: str, model_name: str = None, input_data: dict = None):
        details = {}
        if model_name:
            details['model_name'] = model_name
        if input_data:
            details['input_data'] = str(input_data)[:500]  # Limit untuk logging
        
        super().__init__(message, 'PREDICTION_ERROR', details)


class ValidationError(AIServiceError):
    """
    Exception ketika input data tidak valid.
    """
    def __init__(self, message: str, field: str = None, value: str = None):
        details = {}
        if field:
            details['field'] = field
        if value:
            details['value'] = str(value)[:200]
        
        super().__init__(message, 'VALIDATION_ERROR', details)


class ModelLoadError(AIServiceError):
    """
    Exception ketika gagal memuat model.
    """
    def __init__(self, model_name: str, reason: str = None):
        message = f"Failed to load model '{model_name}'"
        if reason:
            message += f": {reason}"
        
        details = {'model_name': model_name}
        if reason:
            details['reason'] = reason
        
        super().__init__(message, 'MODEL_LOAD_ERROR', details)


class ConfigurationError(AIServiceError):
    """
    Exception ketika konfigurasi AI service tidak valid.
    """
    def __init__(self, message: str, config_key: str = None):
        details = {}
        if config_key:
            details['config_key'] = config_key
        
        super().__init__(message, 'CONFIGURATION_ERROR', details)


class ResourceExhaustedError(AIServiceError):
    """
    Exception ketika resource (memory, CPU, etc.) habis.
    """
    def __init__(self, resource_type: str, message: str = None):
        if not message:
            message = f"Resource exhausted: {resource_type}"
        
        details = {'resource_type': resource_type}
        super().__init__(message, 'RESOURCE_EXHAUSTED', details)


class TimeoutError(AIServiceError):
    """
    Exception ketika operasi AI timeout.
    """
    def __init__(self, operation: str, timeout_seconds: int):
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        details = {
            'operation': operation,
            'timeout_seconds': timeout_seconds
        }
        super().__init__(message, 'TIMEOUT_ERROR', details)


class RateLimitError(AIServiceError):
    """
    Exception ketika rate limit terlampaui.
    """
    def __init__(self, limit_type: str, limit_value: int, reset_time: int = None):
        message = f"Rate limit exceeded: {limit_type} ({limit_value})"
        if reset_time:
            message += f". Resets in {reset_time} seconds"
        
        details = {
            'limit_type': limit_type,
            'limit_value': limit_value
        }
        if reset_time:
            details['reset_time'] = reset_time
        
        super().__init__(message, 'RATE_LIMIT_ERROR', details)


class DataProcessingError(AIServiceError):
    """
    Exception ketika terjadi error saat memproses data.
    """
    def __init__(self, message: str, data_type: str = None, processing_step: str = None):
        details = {}
        if data_type:
            details['data_type'] = data_type
        if processing_step:
            details['processing_step'] = processing_step
        
        super().__init__(message, 'DATA_PROCESSING_ERROR', details)


class ExternalServiceError(AIServiceError):
    """
    Exception ketika terjadi error dengan external service (API, database, etc.).
    """
    def __init__(self, service_name: str, message: str, status_code: int = None):
        full_message = f"External service '{service_name}' error: {message}"
        details = {'service_name': service_name}
        if status_code:
            details['status_code'] = status_code
        
        super().__init__(full_message, 'EXTERNAL_SERVICE_ERROR', details)


class SecurityError(AIServiceError):
    """
    Exception untuk security-related errors.
    """
    def __init__(self, message: str, security_type: str = None):
        details = {}
        if security_type:
            details['security_type'] = security_type
        
        super().__init__(message, 'SECURITY_ERROR', details)


class TrainingError(AIServiceError):
    """
    Exception untuk training-related errors.
    """
    def __init__(self, message: str, training_session_id: int = None, model_name: str = None):
        details = {}
        if training_session_id:
            details['training_session_id'] = training_session_id
        if model_name:
            details['model_name'] = model_name
        
        super().__init__(message, 'TRAINING_ERROR', details)


# Utility functions untuk error handling
def handle_ai_exception(func):
    """
    Decorator untuk menangani AI exceptions dengan logging.
    """
    import functools
    import logging
    
    logger = logging.getLogger(__name__)
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AIServiceError as e:
            logger.error(f"AI Service Error in {func.__name__}: {e.to_dict()}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise AIServiceError(f"Unexpected error: {str(e)}")
    
    return wrapper


def create_error_response(exception: AIServiceError, request_id: str = None):
    """
    Create standardized error response untuk API.
    """
    response = {
        'success': False,
        'error': exception.to_dict(),
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
    
    if request_id:
        response['request_id'] = request_id
    
    return response