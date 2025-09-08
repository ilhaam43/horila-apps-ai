import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from .models import ModelTrainingSession, TrainingData, AIModelRegistry
from .utils.model_evaluation import ModelEvaluator
from .slm_service import SLMService
from .preprocessing import DataPreprocessor, create_preprocessing_pipeline
from .exceptions import TrainingError
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TrainingManager:
    """
    Manages AI model training sessions and workflows
    """
    
    def __init__(self):
        self.slm_service = SLMService()
        self.evaluator = ModelEvaluator()
        self.training_sessions = {}
        
    def create_training_session(self, 
                              model_name: str,
                              training_config: Dict[str, Any],
                              training_data_ids: List[int] = None) -> ModelTrainingSession:
        """
        Create a new training session
        """
        try:
            session = ModelTrainingSession.objects.create(
                model_name=model_name,
                training_config=training_config,
                status='pending',
                created_at=timezone.now()
            )
            
            if training_data_ids:
                training_data = TrainingData.objects.filter(id__in=training_data_ids)
                session.training_data.set(training_data)
            
            logger.info(f"Created training session {session.id} for model {model_name}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create training session: {str(e)}")
            raise TrainingError(f"Failed to create training session: {str(e)}")
    
    def start_training(self, session_id: int) -> bool:
        """
        Start training for a specific session
        """
        try:
            session = ModelTrainingSession.objects.get(id=session_id)
            session.status = 'training'
            session.training_started_at = timezone.now()
            session.save()
            
            # Get training data
            training_data = list(session.training_data.all())
            if not training_data:
                raise TrainingError("No training data available")
            
            # Prepare training data with preprocessing
            X_train, y_train, preprocessor = self._prepare_training_data(training_data)
            
            # Save preprocessor to session
            preprocessor.save_to_session(session)
            
            # Start training process
            training_results = self._execute_training(
                session.model_name,
                X_train,
                y_train,
                session.training_config,
                preprocessor
            )
            
            # Update session with results
            session.training_completed_at = timezone.now()
            session.model_path = training_results.get('model_path')
            session.training_metrics = training_results.get('metrics', {})
            session.status = 'completed'
            session.save()
            
            # Register model if training successful
            if training_results.get('success', False):
                self._register_trained_model(session)
            
            logger.info(f"Training completed for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Training failed for session {session_id}: {str(e)}")
            session = ModelTrainingSession.objects.get(id=session_id)
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
            return False
    
    def _prepare_training_data(self, training_data: List[TrainingData]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data for model training with preprocessing
        """
        try:
            # Collect raw data
            raw_data = []
            targets = []
            
            for data in training_data:
                if data.input_data and data.expected_output:
                    raw_data.append(data.input_data)
                    targets.append(data.expected_output)
            
            if not raw_data:
                raise TrainingError("No valid training data found")
            
            # Convert to DataFrame for preprocessing
            df = pd.DataFrame(raw_data)
            
            # Create and fit preprocessing pipeline
            preprocessor = create_preprocessing_pipeline()
            
            # Fit and transform the data
            X_processed, _ = preprocessor.fit_transform(df)
            y_processed = np.array(targets)
            
            logger.info(f"Preprocessed {len(raw_data)} samples into {X_processed.shape} feature matrix")
            
            return X_processed, y_processed, preprocessor
            
        except Exception as e:
            logger.error(f"Error preparing training data: {str(e)}")
            raise TrainingError(f"Failed to prepare training data: {str(e)}")
    
    def _execute_training(self, 
                         model_name: str,
                         X_train: np.ndarray,
                         y_train: np.ndarray,
                         config: Dict[str, Any],
                         preprocessor: DataPreprocessor) -> Dict[str, Any]:
        """
        Execute the actual training process
        """
        try:
            # Create model directory
            model_dir = os.path.join(settings.MEDIA_ROOT, 'ai_models', model_name)
            os.makedirs(model_dir, exist_ok=True)
            
            # Training configuration
            epochs = config.get('epochs', 10)
            batch_size = config.get('batch_size', 32)
            learning_rate = config.get('learning_rate', 0.001)
            
            # Simulate training process (replace with actual training logic)
            training_metrics = {
                'accuracy': 0.85,
                'loss': 0.15,
                'precision': 0.83,
                'recall': 0.87,
                'f1_score': 0.85,
                'epochs_completed': epochs,
                'training_time': 120.5
            }
            
            # Save model (placeholder)
            model_path = os.path.join(model_dir, f"{model_name}_model.pkl")
            
            # Create a placeholder model file
            model_info = {
                'model_name': model_name,
                'training_date': datetime.now().isoformat(),
                'metrics': training_metrics,
                'config': config
            }
            
            with open(model_path, 'w') as f:
                json.dump(model_info, f, indent=2)
            
            return {
                'success': True,
                'model_path': model_path,
                'metrics': training_metrics
            }
            
        except Exception as e:
            logger.error(f"Training execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _register_trained_model(self, session: ModelTrainingSession):
        """
        Register the trained model in the registry
        """
        try:
            registry_entry = AIModelRegistry.objects.create(
                model_name=session.model_name,
                model_type='custom_trained',
                model_path=session.model_path,
                model_config=session.training_config,
                performance_metrics=session.training_metrics,
                is_active=True,
                created_at=timezone.now()
            )
            
            session.registry_entry = registry_entry
            session.save()
            
            logger.info(f"Registered trained model {session.model_name} in registry")
            
        except Exception as e:
            logger.error(f"Failed to register model: {str(e)}")
    
    def get_training_status(self, session_id: int) -> Dict[str, Any]:
        """
        Get training status for a session
        """
        try:
            session = ModelTrainingSession.objects.get(id=session_id)
            return {
                'session_id': session.id,
                'model_name': session.model_name,
                'status': session.status,
                'progress': self._calculate_progress(session),
                'metrics': session.training_metrics or {},
                'error_message': session.error_message,
                'created_at': session.created_at,
                'training_started_at': session.training_started_at,
                'training_completed_at': session.training_completed_at
            }
        except ModelTrainingSession.DoesNotExist:
            return {'error': 'Training session not found'}
    
    def _calculate_progress(self, session: ModelTrainingSession) -> float:
        """
        Calculate training progress percentage
        """
        if session.status == 'pending':
            return 0.0
        elif session.status == 'training':
            # Simulate progress based on time elapsed
            if session.training_started_at:
                elapsed = (timezone.now() - session.training_started_at).total_seconds()
                # Assume training takes about 5 minutes
                progress = min(elapsed / 300.0, 0.95) * 100
                return progress
            return 10.0
        elif session.status == 'completed':
            return 100.0
        elif session.status == 'failed':
            return 0.0
        return 0.0
    
    def list_training_sessions(self, 
                             model_name: str = None,
                             status: str = None) -> List[Dict[str, Any]]:
        """
        List training sessions with optional filters
        """
        queryset = ModelTrainingSession.objects.all()
        
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        if status:
            queryset = queryset.filter(status=status)
        
        sessions = []
        for session in queryset.order_by('-created_at'):
            sessions.append({
                'id': session.id,
                'model_name': session.model_name,
                'status': session.status,
                'created_at': session.created_at,
                'training_started_at': session.training_started_at,
                'training_completed_at': session.training_completed_at,
                'metrics': session.training_metrics or {}
            })
        
        return sessions
    
    def delete_training_session(self, session_id: int) -> bool:
        """
        Delete a training session and cleanup associated files
        """
        try:
            session = ModelTrainingSession.objects.get(id=session_id)
            
            # Cleanup model files
            if session.model_path and os.path.exists(session.model_path):
                os.remove(session.model_path)
            
            # Remove registry entry if exists
            if hasattr(session, 'registry_entry') and session.registry_entry:
                session.registry_entry.delete()
            
            session.delete()
            logger.info(f"Deleted training session {session_id}")
            return True
            
        except ModelTrainingSession.DoesNotExist:
            logger.warning(f"Training session {session_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to delete training session {session_id}: {str(e)}")
            return False

# Global training manager instance
training_manager = TrainingManager()