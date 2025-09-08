"""URL configuration for testing Indonesian NLP module."""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/nlp/', include('indonesian_nlp.urls')),
    path('budget/', include('budget.web_urls')),
]