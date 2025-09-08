from django.db import models
from django.contrib.auth.models import User

class AIModel(models.Model):
    """Model untuk menyimpan informasi AI models"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    model_type = models.CharField(max_length=50, choices=[
        ('classification', 'Classification'),
        ('regression', 'Regression'),
        ('nlp', 'Natural Language Processing'),
        ('other', 'Other')
    ])
    file_path = models.CharField(max_length=255, blank=True)
    accuracy = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']

class PredictionLog(models.Model):
    """Model untuk menyimpan log prediksi"""
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    input_data = models.JSONField()
    prediction_result = models.JSONField()
    confidence_score = models.FloatField(null=True, blank=True)
    processing_time = models.FloatField(null=True, blank=True)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"Prediction for {self.model.name} at {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']

class TrainingSession(models.Model):
    """Model untuk menyimpan informasi training session"""
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    dataset_info = models.JSONField()
    training_parameters = models.JSONField()
    metrics = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"Training {self.model.name} - {self.status}"
    
    class Meta:
        ordering = ['-started_at']