from django.apps import AppConfig

class SimplePocAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'simple_poc_app'
    verbose_name = 'Simple POC Application'