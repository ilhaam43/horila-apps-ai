from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'knowledge'
    verbose_name = 'Knowledge Management'
    
    def ready(self):
        from django.urls import include, path
        from horilla.horilla_settings import APPS
        from horilla.urls import urlpatterns
        
        # Register the app
        APPS.append('knowledge')
        
        # Add URL patterns (already added in horilla/urls.py but ensuring consistency)
        # urlpatterns.append(
        #     path('knowledge/', include('knowledge.web_urls', namespace='knowledge_web')),
        # )
        
        import knowledge.signals
        super().ready()