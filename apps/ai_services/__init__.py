"""AI Services Package for HRIS System.

This package provides comprehensive AI and automation services including:
- Budget Control System with AI predictions
- Knowledge Management with AI Assistant
- Indonesian NLP processing
- RAG + N8N workflow automation
- Document classification
- Intelligent search capabilities

Author: AI Assistant
Version: 1.0.0
Created: 2024
"""

__version__ = '1.0.0'
__author__ = 'AI Assistant'
__email__ = 'ai@hris.com'

# Lazy imports to avoid circular import issues
def get_budget_ai_service():
    """Get BudgetAIService instance (lazy import)."""
    from .budget_ai import BudgetAIService
    return BudgetAIService

def get_knowledge_ai_service():
    """Get KnowledgeAIService instance (lazy import)."""
    from .knowledge_ai import KnowledgeAIService
    return KnowledgeAIService

def get_indonesian_nlp_service():
    """Get IndonesianNLPService instance (lazy import)."""
    from .indonesian_nlp import IndonesianNLPService
    return IndonesianNLPService

def get_rag_n8n_service():
    """Get RAGN8NIntegrationService instance (lazy import)."""
    from .rag_n8n_integration import RAGN8NIntegrationService
    return RAGN8NIntegrationService

def get_document_classifier_service():
    """Get DocumentClassifierService instance (lazy import)."""
    from .document_classifier import DocumentClassifierService
    return DocumentClassifierService

def get_intelligent_search_service():
    """Get IntelligentSearchService instance (lazy import)."""
    from .intelligent_search import IntelligentSearchService
    return IntelligentSearchService

# Import configuration and exceptions (these are safe)
try:
    from .config import AIConfig
    from .exceptions import AIServiceError, ModelNotFoundError, ValidationError
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import AI config/exceptions: {e}")

# Define what gets imported with "from ai_services import *"
__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__email__',
    
    # Main service classes
    'BudgetAIService',
    'KnowledgeAIService',
    'IndonesianNLPService',
    'RAGN8NIntegrationService',
    'DocumentClassifierService',
    'IntelligentSearchService',
    
    # Configuration and exceptions
    'AIConfig',
    'AIServiceError',
    'ModelNotFoundError',
    'ValidationError',
    
    # Utilities
    'extract_text_from_file',
    'clean_text',
    'tokenize_indonesian_text',
    'validate_input_data',
    'calculate_text_similarity',
]

# Package metadata
PACKAGE_INFO = {
    'name': 'ai_services',
    'version': __version__,
    'description': 'AI Services Package for HRIS System',
    'author': __author__,
    'email': __email__,
    'services': [
        'Budget AI',
        'Knowledge AI',
        'Indonesian NLP',
        'RAG + N8N Integration',
        'Document Classifier',
        'Intelligent Search'
    ],
    'features': [
        'Real-time budget predictions',
        'Anomaly detection',
        'Knowledge management with RAG',
        'Indonesian sentiment analysis',
        'Named entity recognition',
        'Document classification',
        'Semantic search',
        'Workflow automation',
        'AI-powered recommendations'
    ]
}

def get_package_info():
    """Get package information.
    
    Returns:
        dict: Package information including version, services, and features
    """
    return PACKAGE_INFO.copy()

def get_available_services():
    """Get list of available AI services.
    
    Returns:
        list: List of available service names
    """
    return PACKAGE_INFO['services'].copy()

def get_service_features():
    """Get list of AI service features.
    
    Returns:
        list: List of available features
    """
    return PACKAGE_INFO['features'].copy()

# Initialize logging for the package
import logging

logger = logging.getLogger(__name__)
logger.info(f"AI Services Package v{__version__} initialized")
logger.info(f"Available services: {', '.join(get_available_services())}")

# Default app configuration
default_app_config = 'ai_services.apps.AiServicesConfig'