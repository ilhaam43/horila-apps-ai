from django.apps import AppConfig


class OllamaIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ollama_integration'
    verbose_name = 'Ollama AI Integration'
    
    def ready(self):
        import ollama_integration.signals