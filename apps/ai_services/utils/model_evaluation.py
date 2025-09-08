from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ModelEvaluator:
    """
    Utility class for evaluating machine learning models and calculating metrics.
    """
    
    def __init__(self):
        self.metrics = {}
    
    def split_data(self, X, y, test_size=0.2, random_state=42, stratify=None):
        """
        Split data into training and testing sets.
        
        Args:
            X: Features
            y: Target variable
            test_size: Proportion of test set (default: 0.2)
            random_state: Random seed for reproducibility
            stratify: Whether to stratify split based on target variable
        
        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        try:
            return train_test_split(
                X, y, 
                test_size=test_size, 
                random_state=random_state,
                stratify=stratify if stratify is not None else y
            )
        except Exception as e:
            logger.error(f"Error splitting data: {str(e)}")
            return train_test_split(X, y, test_size=test_size, random_state=random_state)
    
    def calculate_classification_metrics(self, y_true, y_pred, average='weighted'):
        """
        Calculate classification metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            average: Averaging method for multi-class ('weighted', 'macro', 'micro')
        
        Returns:
            Dictionary containing accuracy, precision, recall, and F1-score
        """
        try:
            metrics = {
                'accuracy': accuracy_score(y_true, y_pred),
                'precision': precision_score(y_true, y_pred, average=average, zero_division=0),
                'recall': recall_score(y_true, y_pred, average=average, zero_division=0),
                'f1_score': f1_score(y_true, y_pred, average=average, zero_division=0)
            }
            
            # Add detailed classification report
            metrics['classification_report'] = classification_report(
                y_true, y_pred, output_dict=True, zero_division=0
            )
            
            # Add confusion matrix
            metrics['confusion_matrix'] = confusion_matrix(y_true, y_pred).tolist()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating classification metrics: {str(e)}")
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'error': str(e)
            }
    
    def calculate_regression_metrics(self, y_true, y_pred):
        """
        Calculate regression metrics.
        
        Args:
            y_true: True values
            y_pred: Predicted values
        
        Returns:
            Dictionary containing regression metrics
        """
        try:
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            
            metrics = {
                'mse': mean_squared_error(y_true, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
                'mae': mean_absolute_error(y_true, y_pred),
                'r2_score': r2_score(y_true, y_pred)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating regression metrics: {str(e)}")
            return {
                'mse': float('inf'),
                'rmse': float('inf'),
                'mae': float('inf'),
                'r2_score': 0.0,
                'error': str(e)
            }
    
    def evaluate_model_performance(self, model, X_test, y_test, task_type='classification'):
        """
        Evaluate model performance on test data.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels/values
            task_type: 'classification' or 'regression'
        
        Returns:
            Dictionary containing evaluation metrics
        """
        try:
            # Make predictions
            y_pred = model.predict(X_test)
            
            if task_type == 'classification':
                metrics = self.calculate_classification_metrics(y_test, y_pred)
                
                # Add prediction probabilities if available
                if hasattr(model, 'predict_proba'):
                    y_proba = model.predict_proba(X_test)
                    metrics['prediction_probabilities'] = y_proba.tolist()
                    
                    # Calculate AUC-ROC for binary classification
                    if len(np.unique(y_test)) == 2:
                        from sklearn.metrics import roc_auc_score
                        metrics['auc_roc'] = roc_auc_score(y_test, y_proba[:, 1])
                        
            elif task_type == 'regression':
                metrics = self.calculate_regression_metrics(y_test, y_pred)
            
            else:
                raise ValueError(f"Unsupported task type: {task_type}")
            
            # Add general information
            metrics['task_type'] = task_type
            metrics['test_samples'] = len(y_test)
            metrics['predictions'] = y_pred.tolist() if hasattr(y_pred, 'tolist') else list(y_pred)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model performance: {str(e)}")
            return {
                'error': str(e),
                'task_type': task_type,
                'test_samples': len(y_test) if y_test is not None else 0
            }
    
    def cross_validate_model(self, model, X, y, cv=5, scoring=None):
        """
        Perform cross-validation on the model.
        
        Args:
            model: Model to evaluate
            X: Features
            y: Target variable
            cv: Number of cross-validation folds
            scoring: Scoring metric
        
        Returns:
            Dictionary containing cross-validation results
        """
        try:
            from sklearn.model_selection import cross_val_score, cross_validate
            
            if scoring is None:
                scoring = ['accuracy', 'precision_weighted', 'recall_weighted', 'f1_weighted']
            
            cv_results = cross_validate(model, X, y, cv=cv, scoring=scoring, return_train_score=True)
            
            results = {
                'cv_folds': cv,
                'mean_scores': {},
                'std_scores': {},
                'all_scores': {}
            }
            
            for metric in scoring:
                test_key = f'test_{metric}'
                train_key = f'train_{metric}'
                
                if test_key in cv_results:
                    results['mean_scores'][f'{metric}_test'] = np.mean(cv_results[test_key])
                    results['std_scores'][f'{metric}_test'] = np.std(cv_results[test_key])
                    results['all_scores'][f'{metric}_test'] = cv_results[test_key].tolist()
                
                if train_key in cv_results:
                    results['mean_scores'][f'{metric}_train'] = np.mean(cv_results[train_key])
                    results['std_scores'][f'{metric}_train'] = np.std(cv_results[train_key])
                    results['all_scores'][f'{metric}_train'] = cv_results[train_key].tolist()
            
            return results
            
        except Exception as e:
            logger.error(f"Error in cross-validation: {str(e)}")
            return {
                'error': str(e),
                'cv_folds': cv
            }
    
    def generate_evaluation_report(self, training_data_instance, metrics):
        """
        Generate comprehensive evaluation report and save to TrainingData instance.
        
        Args:
            training_data_instance: TrainingData model instance
            metrics: Dictionary containing evaluation metrics
        
        Returns:
            Updated TrainingData instance
        """
        try:
            # Extract main metrics
            accuracy = metrics.get('accuracy')
            precision = metrics.get('precision')
            recall = metrics.get('recall')
            f1 = metrics.get('f1_score')
            
            # Set evaluation metrics
            training_data_instance.set_evaluation_metrics(
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1=f1,
                additional_metrics=metrics
            )
            
            logger.info(f"Evaluation metrics saved for training data: {training_data_instance.id}")
            return training_data_instance
            
        except Exception as e:
            logger.error(f"Error generating evaluation report: {str(e)}")
            return training_data_instance


def evaluate_training_data(training_data_instance, model, X_test, y_test, task_type='classification'):
    """
    Convenience function to evaluate a model and save metrics to TrainingData instance.
    
    Args:
        training_data_instance: TrainingData model instance
        model: Trained model
        X_test: Test features
        y_test: Test labels/values
        task_type: 'classification' or 'regression'
    
    Returns:
        Updated TrainingData instance with evaluation metrics
    """
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_model_performance(model, X_test, y_test, task_type)
    return evaluator.generate_evaluation_report(training_data_instance, metrics)


def calculate_success_ratio(training_data_instance):
    """
    Calculate and return success ratio for a training data instance.
    
    Args:
        training_data_instance: TrainingData model instance
    
    Returns:
        Float representing success ratio (0.0 to 1.0) or None if not available
    """
    return training_data_instance.get_success_ratio()