from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.core.management.color import no_style
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class AiServicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_services'
    verbose_name = 'AI Services'
    
    def ready(self):
        """Called when Django starts."""
        # Import signal handlers
        from . import signals
        
        # Connect post-migrate signal
        post_migrate.connect(self.create_default_data, sender=self)
        
        # Initialize AI services on startup
        self.initialize_ai_services()
    
    def create_default_data(self, sender, **kwargs):
        """Create default data after migrations."""
        try:
            from .models import AIModelRegistry
            
            # Create default AI model entries
            default_models = [
                {
                    'name': 'budget_predictor_v1',
                    'service_type': 'budget_ai',
                    'model_type': 'regression',
                    'version': '1.0.0',
                    'model_path': 'ai_models/budget/predictor_v1.pkl',
                    'config': {
                        'algorithm': 'RandomForestRegressor',
                        'features': ['amount', 'category', 'department', 'month'],
                        'target': 'predicted_amount'
                    },
                    'is_active': True
                },
                {
                    'name': 'budget_anomaly_detector_v1',
                    'service_type': 'budget_ai',
                    'model_type': 'anomaly_detection',
                    'version': '1.0.0',
                    'model_path': 'ai_models/budget/anomaly_detector_v1.pkl',
                    'config': {
                        'algorithm': 'IsolationForest',
                        'contamination': 0.1,
                        'features': ['amount', 'category', 'department']
                    },
                    'is_active': True
                },
                {
                    'name': 'knowledge_embedder_v1',
                    'service_type': 'knowledge_ai',
                    'model_type': 'embedding',
                    'version': '1.0.0',
                    'model_path': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'config': {
                        'model_type': 'sentence_transformer',
                        'embedding_dim': 384,
                        'max_seq_length': 512
                    },
                    'is_active': True
                },
                {
                    'name': 'indonesian_sentiment_v1',
                    'service_type': 'indonesian_nlp',
                    'model_type': 'classification',
                    'version': '1.0.0',
                    'model_path': 'indobenchmark/indobert-base-p1',
                    'config': {
                        'model_type': 'transformer',
                        'num_labels': 3,
                        'labels': ['negative', 'neutral', 'positive']
                    },
                    'is_active': True
                },
                {
                    'name': 'document_classifier_v1',
                    'service_type': 'document_classifier',
                    'model_type': 'classification',
                    'version': '1.0.0',
                    'model_path': 'ai_models/document/classifier_v1.pkl',
                    'config': {
                        'categories': [
                            'resume', 'job_description', 'contract', 'policy',
                            'report', 'invoice', 'other'
                        ],
                        'methods': ['transformer', 'embedding', 'ml_traditional', 'rule_based']
                    },
                    'is_active': True
                },
                {
                    'name': 'search_embedder_v1',
                    'service_type': 'intelligent_search',
                    'model_type': 'embedding',
                    'version': '1.0.0',
                    'model_path': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                    'config': {
                        'model_type': 'sentence_transformer',
                        'embedding_dim': 384,
                        'search_models': [
                            'employee.Employee',
                            'recruitment.JobPosition',
                            'budget.BudgetPlan',
                            'ai_services.KnowledgeBase'
                        ]
                    },
                    'is_active': True
                }
            ]
            
            for model_data in default_models:
                AIModelRegistry.objects.get_or_create(
                    name=model_data['name'],
                    version=model_data['version'],
                    defaults=model_data
                )
            
            logger.info("Default AI models created successfully")
            
        except Exception as e:
            logger.error(f"Error creating default AI models: {str(e)}")
    
    def initialize_ai_services(self):
        """Initialize AI services on startup."""
        try:
            # This will be called when Django starts
            # We can initialize AI services here if needed
            logger.info("AI Services app initialized successfully")
            
            # Create necessary directories
            import os
            from django.conf import settings
            
            ai_models_dir = os.path.join(settings.MEDIA_ROOT, 'ai_models')
            subdirs = ['budget', 'knowledge', 'nlp', 'document', 'search', 'rag']
            
            for subdir in subdirs:
                dir_path = os.path.join(ai_models_dir, subdir)
                os.makedirs(dir_path, exist_ok=True)
            
            logger.info("AI models directories created")
            
        except Exception as e:
            logger.error(f"Error initializing AI services: {str(e)}")
    
    def create_database_indexes(self):
        """Create additional database indexes for performance."""
        try:
            style = no_style()
            
            # Custom indexes for better performance
            custom_indexes = [
                # AI Predictions indexes
                "CREATE INDEX IF NOT EXISTS idx_ai_predictions_model_created "
                "ON ai_predictions(model_id, created_at DESC);",
                
                "CREATE INDEX IF NOT EXISTS idx_ai_predictions_confidence "
                "ON ai_predictions(confidence_score DESC) WHERE confidence_score IS NOT NULL;",
                
                # Knowledge Base indexes
                "CREATE INDEX IF NOT EXISTS idx_knowledge_base_content_search "
                "ON knowledge_base USING gin(to_tsvector('english', content));",
                
                "CREATE INDEX IF NOT EXISTS idx_knowledge_base_tags "
                "ON knowledge_base USING gin(tags);",
                
                # Document Classification indexes
                "CREATE INDEX IF NOT EXISTS idx_document_class_category_confidence "
                "ON document_classifications(predicted_category, confidence_score DESC);",
                
                # Search Query indexes
                "CREATE INDEX IF NOT EXISTS idx_search_query_text_search "
                "ON search_queries USING gin(to_tsvector('english', query_text));",
                
                # NLP Analysis indexes
                "CREATE INDEX IF NOT EXISTS idx_nlp_analysis_sentiment "
                "ON nlp_analyses(sentiment_label, sentiment_score DESC) "
                "WHERE sentiment_score IS NOT NULL;",
                
                # AI Service Logs indexes
                "CREATE INDEX IF NOT EXISTS idx_ai_logs_service_level_time "
                "ON ai_service_logs(service_type, log_level, created_at DESC);",
                
                # Workflow Execution indexes
                "CREATE INDEX IF NOT EXISTS idx_workflow_exec_type_status "
                "ON workflow_executions(workflow_type, n8n_status, created_at DESC);"
            ]
            
            with connection.cursor() as cursor:
                for index_sql in custom_indexes:
                    try:
                        cursor.execute(index_sql)
                        logger.info(f"Created index: {index_sql[:50]}...")
                    except Exception as e:
                        logger.warning(f"Could not create index: {str(e)}")
            
            logger.info("Custom database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database indexes: {str(e)}")