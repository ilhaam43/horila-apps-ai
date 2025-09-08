"""init.py"""

from horilla import (
    horilla_apps,
    horilla_context_processors,
    horilla_middlewares,
    horilla_settings,
    rest_conf,
)

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
