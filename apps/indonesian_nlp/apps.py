from django.apps import AppConfig


class IndonesianNlpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'indonesian_nlp'
    verbose_name = 'Indonesian NLP Integration'
    
    def ready(self):
        """Initialize the Indonesian NLP application"""
        import sys
        
        # Skip initialization during migrations
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
            
        try:
            # Import signals
            from . import signals
            
            # Initialize NLP models on startup
            from django.db import connection
            from django.db.utils import OperationalError
            
            # Check if tables exist before accessing models
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='indonesian_nlp_nlpmodel';")
                    if cursor.fetchone():
                        from .models import NLPModel
                        from .utils import ModelManager
                        
                        # Load default models if they don't exist
                        if not NLPModel.objects.filter(is_active=True).exists():
                            ModelManager.initialize_default_models()
            except OperationalError:
                # Tables don't exist yet, skip initialization
                pass
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize Indonesian NLP: {str(e)}")