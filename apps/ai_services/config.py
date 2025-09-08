import os
from typing import Dict, Any, Optional
from django.conf import settings

class AIConfig:
    """
    Configuration class untuk AI services.
    Mengelola semua konfigurasi terkait AI models dan services.
    """
    
    # Default configurations
    DEFAULT_CONFIG = {
        'CACHE_TIMEOUT': 3600,  # 1 hour
        'MAX_RETRIES': 3,
        'REQUEST_TIMEOUT': 30,  # seconds
        'BATCH_SIZE': 32,
        'MODEL_PATH': '/models',
        'VECTOR_DIMENSION': 1536,  # OpenAI embedding dimension
        'MAX_TOKENS': 4096,
        'TEMPERATURE': 0.7,
        'TOP_P': 0.9,
    }
    
    # Budget AI Configuration
    BUDGET_AI_CONFIG = {
        'MODEL_NAME': 'budget_predictor_v1',
        'PREDICTION_HORIZON_DAYS': 90,
        'ANOMALY_THRESHOLD': 0.15,  # 15% deviation
        'MIN_HISTORICAL_DATA_POINTS': 30,
        'FEATURES': [
            'department_id',
            'budget_category',
            'historical_spending',
            'employee_count',
            'project_count',
            'seasonal_factor',
            'economic_indicator'
        ],
        'ALERT_THRESHOLDS': {
            'low': 0.8,    # 80% of budget
            'medium': 0.9,  # 90% of budget
            'high': 0.95   # 95% of budget
        }
    }
    
    # Knowledge AI Configuration
    KNOWLEDGE_AI_CONFIG = {
        'MODEL_NAME': 'knowledge_assistant_v1',
        'EMBEDDING_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
        'LLM_MODEL': 'ollama/llama2',
        'VECTOR_DB_URL': os.getenv('VECTOR_DB_URL', 'http://localhost:6333'),
        'COLLECTION_NAME': 'horilla_knowledge',
        'SIMILARITY_THRESHOLD': 0.7,
        'MAX_CONTEXT_LENGTH': 4000,
        'CHUNK_SIZE': 500,
        'CHUNK_OVERLAP': 50,
        'SUPPORTED_FORMATS': ['.pdf', '.docx', '.txt', '.md', '.html']
    }
    
    # Small Language Model Configuration
    SLM_CONFIG = {
        'TEXT_GENERATION_MODEL': 'gpt2',
        'QA_MODEL': 't5-small',
        'SUMMARIZATION_MODEL': 't5-small',
        'INDONESIAN_MODEL': 'gpt2',  # Can be replaced with Indonesian-specific model
        'EMBEDDING_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
        'MAX_RESPONSE_LENGTH': 300,
        'MAX_CONTEXT_LENGTH': 2000,
        'USE_INDONESIAN': True,
        'CACHE_ENABLED': True,
        'CACHE_TTL': 3600,  # 1 hour
        'SIMILARITY_THRESHOLD': 0.3,
        'DEVICE': 'cpu',  # Use 'cuda' if GPU available
        'MODEL_CACHE_DIR': './models/slm_cache'
    }
    
    # Indonesian NLP Configuration
    INDONESIAN_NLP_CONFIG = {
        'MODEL_NAME': 'indonesian_nlp_v1',
        'BERT_MODEL': 'indolem/indobert-base-uncased',
        'SENTIMENT_MODEL': 'indonesian-sentiment-analysis',
        'NER_MODEL': 'indonesian-ner',
        'LANGUAGE_DETECTION_THRESHOLD': 0.8,
        'SENTIMENT_LABELS': ['negative', 'neutral', 'positive'],
        'NER_LABELS': ['PERSON', 'ORGANIZATION', 'LOCATION', 'DATE', 'MONEY'],
        'MAX_TEXT_LENGTH': 5000,
        'BATCH_PROCESSING_SIZE': 16
    }
    
    # RAG + N8N Configuration
    RAG_N8N_CONFIG = {
        'MODEL_NAME': 'rag_n8n_integration_v1',
        'N8N_WEBHOOK_URL': os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook'),
        'N8N_API_KEY': os.getenv('N8N_API_KEY', ''),
        'RAG_MODEL': 'rag_recruitment_v1',
        'WORKFLOW_TEMPLATES': {
            'candidate_screening': 'candidate_screening_workflow',
            'interview_scheduling': 'interview_scheduling_workflow',
            'onboarding': 'onboarding_workflow',
            'performance_review': 'performance_review_workflow'
        },
        'AUTO_TRIGGER_THRESHOLD': 0.85
    }
    
    # Document Classification Configuration
    DOCUMENT_AI_CONFIG = {
        'MODEL_NAME': 'document_classifier_v1',
        'CLASSIFICATION_MODEL': 'document-classification-bert',
        'OCR_ENGINE': 'tesseract',
        'SUPPORTED_FORMATS': ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.docx'],
        'MAX_FILE_SIZE_MB': 50,
        'DOCUMENT_CATEGORIES': [
            'contract',
            'resume',
            'invoice',
            'policy',
            'report',
            'certificate',
            'application',
            'other'
        ],
        'CONFIDENCE_THRESHOLD': 0.75,
        'BATCH_PROCESSING': True
    }
    
    # Intelligent Search Configuration
    SEARCH_AI_CONFIG = {
        'MODEL_NAME': 'intelligent_search_v1',
        'SEARCH_ENGINE': 'elasticsearch',
        'EMBEDDING_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
        'ELASTICSEARCH_URL': os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200'),
        'INDEX_NAME': 'horilla_search',
        'SEMANTIC_WEIGHT': 0.7,  # Weight for semantic search
        'KEYWORD_WEIGHT': 0.3,   # Weight for keyword search
        'MAX_RESULTS': 50,
        'SEARCH_TIMEOUT': 10,  # seconds
        'RERANK_TOP_K': 20,
        'SUPPORTED_ENTITIES': [
            'employees',
            'documents',
            'policies',
            'projects',
            'budgets',
            'leaves',
            'payrolls'
        ]
    }
    
    @classmethod
    def get_config(cls, service_name: str) -> Dict[str, Any]:
        """
        Get configuration for specific AI service.
        """
        config_map = {
            'budget': cls.BUDGET_AI_CONFIG,
            'knowledge': cls.KNOWLEDGE_AI_CONFIG,
            'indonesian_nlp': cls.INDONESIAN_NLP_CONFIG,
            'rag_n8n': cls.RAG_N8N_CONFIG,
            'document': cls.DOCUMENT_AI_CONFIG,
            'search': cls.SEARCH_AI_CONFIG
        }
        
        service_config = config_map.get(service_name, {})
        
        # Merge with default config
        merged_config = {**cls.DEFAULT_CONFIG, **service_config}
        
        # Override with Django settings if available
        django_config_key = f'AI_{service_name.upper()}_CONFIG'
        if hasattr(settings, django_config_key):
            django_config = getattr(settings, django_config_key)
            merged_config.update(django_config)
        
        return merged_config
    
    @classmethod
    def get_model_path(cls, model_name: str) -> str:
        """
        Get full path to model file.
        """
        base_path = cls.DEFAULT_CONFIG['MODEL_PATH']
        if hasattr(settings, 'AI_MODEL_PATH'):
            base_path = settings.AI_MODEL_PATH
        
        return os.path.join(base_path, model_name)
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> bool:
        """
        Validate AI service configuration.
        """
        required_keys = ['MODEL_NAME']
        
        for key in required_keys:
            if key not in config:
                return False
        
        # Validate numeric values
        numeric_keys = ['CACHE_TIMEOUT', 'MAX_RETRIES', 'REQUEST_TIMEOUT']
        for key in numeric_keys:
            if key in config and not isinstance(config[key], (int, float)):
                return False
        
        return True
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """
        Get database configuration for AI services.
        """
        return {
            'VECTOR_DB': {
                'ENGINE': os.getenv('VECTOR_DB_ENGINE', 'pinecone'),
                'URL': os.getenv('VECTOR_DB_URL', 'http://localhost:6333'),
                'API_KEY': os.getenv('VECTOR_DB_API_KEY', ''),
                'DIMENSION': cls.DEFAULT_CONFIG['VECTOR_DIMENSION']
            },
            'CACHE_DB': {
                'ENGINE': 'redis',
                'URL': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
                'TIMEOUT': cls.DEFAULT_CONFIG['CACHE_TIMEOUT']
            },
            'SEARCH_DB': {
                'ENGINE': 'elasticsearch',
                'URL': os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200'),
                'INDEX_PREFIX': 'horilla_ai_'
            }
        }
    
    @classmethod
    def get_security_config(cls) -> Dict[str, Any]:
        """
        Get security configuration for AI services.
        """
        return {
            'ENCRYPTION_KEY': os.getenv('AI_ENCRYPTION_KEY', ''),
            'API_RATE_LIMIT': {
                'REQUESTS_PER_MINUTE': 100,
                'REQUESTS_PER_HOUR': 1000,
                'REQUESTS_PER_DAY': 10000
            },
            'INPUT_VALIDATION': {
                'MAX_TEXT_LENGTH': 10000,
                'MAX_FILE_SIZE_MB': 50,
                'ALLOWED_FILE_TYPES': ['.pdf', '.docx', '.txt', '.jpg', '.png']
            },
            'OUTPUT_FILTERING': {
                'ENABLE_CONTENT_FILTER': True,
                'BLOCKED_KEYWORDS': [],
                'SANITIZE_OUTPUT': True
            }
        }
    
    @classmethod
    def get_monitoring_config(cls) -> Dict[str, Any]:
        """
        Get monitoring and logging configuration.
        """
        return {
            'LOGGING': {
                'LEVEL': os.getenv('AI_LOG_LEVEL', 'INFO'),
                'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'FILE_PATH': '/logs/ai_services.log',
                'MAX_FILE_SIZE_MB': 100,
                'BACKUP_COUNT': 5
            },
            'METRICS': {
                'ENABLE_PROMETHEUS': True,
                'METRICS_PORT': 8000,
                'COLLECT_SYSTEM_METRICS': True,
                'COLLECT_MODEL_METRICS': True
            },
            'HEALTH_CHECK': {
                'INTERVAL_SECONDS': 60,
                'TIMEOUT_SECONDS': 10,
                'FAILURE_THRESHOLD': 3
            }
        }