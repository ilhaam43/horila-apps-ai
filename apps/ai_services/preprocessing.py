import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
import logging
import json
from datetime import datetime
from django.core.cache import cache
try:
    from .utils import get_cache_key, sanitize_filename
except ImportError:
    # Fallback functions if utils not available
    def get_cache_key(service_type: str, key: str) -> str:
        return f"{service_type}_{key}"
    
    def sanitize_filename(filename: str) -> str:
        import re
        return re.sub(r'[^\w\-_\.]', '_', filename)
from .models import AIModelRegistry, ModelTrainingSession

logger = logging.getLogger(__name__)

class DataPreprocessor:
    """
    Comprehensive data preprocessing pipeline for AI services.
    Handles various data types and ensures consistency across training and inference.
    """
    
    def __init__(self, service_type: str = 'budget_ai'):
        self.service_type = service_type
        self.scalers = {}
        self.encoders = {}
        self.vectorizers = {}
        self.imputers = {}
        self.feature_names = []
        self.preprocessing_config = {}
        
    def fit_transform(self, data: Union[pd.DataFrame, Dict[str, Any]], 
                     target_column: Optional[str] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Fit preprocessing pipeline and transform data.
        
        Args:
            data: Input data as DataFrame or dictionary
            target_column: Name of target column for supervised learning
            
        Returns:
            Tuple of (features, target) as numpy arrays
        """
        try:
            # Convert to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = data.copy()
                
            logger.info(f"Starting preprocessing for {len(df)} samples with {len(df.columns)} features")
            
            # Separate features and target
            if target_column and target_column in df.columns:
                target = df[target_column].values
                features_df = df.drop(columns=[target_column])
            else:
                target = None
                features_df = df
                
            # Store feature names
            self.feature_names = list(features_df.columns)
            
            # Process different data types
            processed_features = []
            
            for column in features_df.columns:
                column_data = features_df[column]
                
                if column_data.dtype == 'object':
                    # Handle text/categorical data
                    processed_col = self._process_categorical_column(column, column_data, fit=True)
                elif pd.api.types.is_numeric_dtype(column_data):
                    # Handle numerical data
                    processed_col = self._process_numerical_column(column, column_data, fit=True)
                else:
                    # Handle other data types
                    processed_col = self._process_other_column(column, column_data, fit=True)
                    
                if processed_col is not None:
                    if len(processed_col.shape) == 1:
                        processed_col = processed_col.reshape(-1, 1)
                    processed_features.append(processed_col)
                    
            # Combine all features
            if processed_features:
                features = np.hstack(processed_features)
            else:
                features = np.array([]).reshape(len(df), 0)
                
            # Save preprocessing configuration
            self._save_preprocessing_config()
            
            logger.info(f"Preprocessing completed. Output shape: {features.shape}")
            return features, target
            
        except Exception as e:
            logger.error(f"Error in fit_transform: {str(e)}")
            raise
            
    def transform(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> np.ndarray:
        """
        Transform new data using fitted preprocessing pipeline.
        
        Args:
            data: Input data to transform
            
        Returns:
            Transformed features as numpy array
        """
        try:
            # Convert to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = data.copy()
                
            # Ensure all expected columns are present
            missing_cols = set(self.feature_names) - set(df.columns)
            if missing_cols:
                logger.warning(f"Missing columns: {missing_cols}. Filling with default values.")
                for col in missing_cols:
                    df[col] = 0  # Default value
                    
            # Reorder columns to match training order
            df = df[self.feature_names]
            
            # Process each column using fitted transformers
            processed_features = []
            
            for column in self.feature_names:
                column_data = df[column]
                
                if column_data.dtype == 'object':
                    processed_col = self._process_categorical_column(column, column_data, fit=False)
                elif pd.api.types.is_numeric_dtype(column_data):
                    processed_col = self._process_numerical_column(column, column_data, fit=False)
                else:
                    processed_col = self._process_other_column(column, column_data, fit=False)
                    
                if processed_col is not None:
                    if len(processed_col.shape) == 1:
                        processed_col = processed_col.reshape(-1, 1)
                    processed_features.append(processed_col)
                    
            # Combine all features
            if processed_features:
                features = np.hstack(processed_features)
            else:
                features = np.array([]).reshape(len(df), 0)
                
            return features
            
        except Exception as e:
            logger.error(f"Error in transform: {str(e)}")
            raise
            
    def _process_numerical_column(self, column_name: str, data: pd.Series, fit: bool = True) -> np.ndarray:
        """
        Process numerical columns with imputation and scaling.
        """
        try:
            # Handle missing values
            if column_name not in self.imputers:
                if fit:
                    self.imputers[column_name] = SimpleImputer(strategy='median')
                    imputed_data = self.imputers[column_name].fit_transform(data.values.reshape(-1, 1))
                else:
                    return data.fillna(0).values  # Fallback if imputer not fitted
            else:
                imputed_data = self.imputers[column_name].transform(data.values.reshape(-1, 1))
                
            # Scale the data
            if column_name not in self.scalers:
                if fit:
                    self.scalers[column_name] = StandardScaler()
                    scaled_data = self.scalers[column_name].fit_transform(imputed_data)
                else:
                    return imputed_data.flatten()  # Fallback if scaler not fitted
            else:
                scaled_data = self.scalers[column_name].transform(imputed_data)
                
            return scaled_data.flatten()
            
        except Exception as e:
            logger.error(f"Error processing numerical column {column_name}: {str(e)}")
            return data.fillna(0).values
            
    def _process_categorical_column(self, column_name: str, data: pd.Series, fit: bool = True) -> np.ndarray:
        """
        Process categorical columns with encoding.
        """
        try:
            # Fill missing values
            data_filled = data.fillna('unknown')
            
            # Check if this looks like text data (long strings)
            avg_length = data_filled.astype(str).str.len().mean()
            
            if avg_length > 50:  # Treat as text data
                return self._process_text_column(column_name, data_filled, fit)
            else:  # Treat as categorical
                if column_name not in self.encoders:
                    if fit:
                        self.encoders[column_name] = LabelEncoder()
                        encoded_data = self.encoders[column_name].fit_transform(data_filled.astype(str))
                    else:
                        return np.zeros(len(data_filled))  # Fallback
                else:
                    # Handle unseen categories
                    try:
                        encoded_data = self.encoders[column_name].transform(data_filled.astype(str))
                    except ValueError:
                        # Handle unseen labels
                        encoded_data = np.zeros(len(data_filled))
                        for i, val in enumerate(data_filled.astype(str)):
                            try:
                                encoded_data[i] = self.encoders[column_name].transform([val])[0]
                            except ValueError:
                                encoded_data[i] = 0  # Default for unseen categories
                                
                return encoded_data
                
        except Exception as e:
            logger.error(f"Error processing categorical column {column_name}: {str(e)}")
            return np.zeros(len(data))
            
    def _process_text_column(self, column_name: str, data: pd.Series, fit: bool = True) -> np.ndarray:
        """
        Process text columns with TF-IDF vectorization.
        """
        try:
            if column_name not in self.vectorizers:
                if fit:
                    self.vectorizers[column_name] = TfidfVectorizer(
                        max_features=100,  # Limit features to prevent explosion
                        stop_words='english',
                        lowercase=True,
                        ngram_range=(1, 2)
                    )
                    vectorized_data = self.vectorizers[column_name].fit_transform(data.astype(str))
                    return vectorized_data.toarray()
                else:
                    return np.zeros((len(data), 100))  # Fallback
            else:
                vectorized_data = self.vectorizers[column_name].transform(data.astype(str))
                return vectorized_data.toarray()
                
        except Exception as e:
            logger.error(f"Error processing text column {column_name}: {str(e)}")
            return np.zeros((len(data), 100))
            
    def _process_other_column(self, column_name: str, data: pd.Series, fit: bool = True) -> np.ndarray:
        """
        Process other data types (datetime, etc.).
        """
        try:
            # Try to convert to datetime
            if data.dtype == 'datetime64[ns]' or 'date' in column_name.lower():
                # Extract useful datetime features
                dt_data = pd.to_datetime(data, errors='coerce')
                features = []
                
                # Year, month, day, hour features
                if not dt_data.isna().all():
                    features.extend([
                        dt_data.dt.year.fillna(2000).values,
                        dt_data.dt.month.fillna(1).values,
                        dt_data.dt.day.fillna(1).values,
                        dt_data.dt.hour.fillna(0).values,
                        dt_data.dt.dayofweek.fillna(0).values
                    ])
                    return np.column_stack(features)
                    
            # Convert to string and treat as categorical
            return self._process_categorical_column(column_name, data.astype(str), fit)
            
        except Exception as e:
            logger.error(f"Error processing other column {column_name}: {str(e)}")
            return np.zeros(len(data))
            
    def _save_preprocessing_config(self):
        """
        Save preprocessing configuration for later use.
        """
        try:
            config = {
                'service_type': self.service_type,
                'feature_names': self.feature_names,
                'scalers_fitted': list(self.scalers.keys()),
                'encoders_fitted': list(self.encoders.keys()),
                'vectorizers_fitted': list(self.vectorizers.keys()),
                'imputers_fitted': list(self.imputers.keys()),
                'created_at': datetime.now().isoformat()
            }
            
            self.preprocessing_config = config
            
            # Cache the configuration
            cache_key = get_cache_key(self.service_type, 'preprocessing_config')
            cache.set(cache_key, config, timeout=3600 * 24)  # 24 hours
            
            logger.info(f"Preprocessing configuration saved for {self.service_type}")
            
        except Exception as e:
            logger.error(f"Error saving preprocessing config: {str(e)}")
            
    def save_to_session(self, session: ModelTrainingSession):
        """
        Save preprocessing pipeline to training session.
        """
        try:
            import pickle
            import base64
            
            # Serialize the preprocessor
            preprocessor_data = {
                'scalers': {k: base64.b64encode(pickle.dumps(v)).decode() for k, v in self.scalers.items()},
                'encoders': {k: base64.b64encode(pickle.dumps(v)).decode() for k, v in self.encoders.items()},
                'vectorizers': {k: base64.b64encode(pickle.dumps(v)).decode() for k, v in self.vectorizers.items()},
                'imputers': {k: base64.b64encode(pickle.dumps(v)).decode() for k, v in self.imputers.items()},
                'feature_names': self.feature_names,
                'service_type': self.service_type
            }
            
            # Save to session config
            current_config = session.get_config()
            current_config['preprocessing'] = preprocessor_data
            session.set_config(current_config)
            session.save()
            
            logger.info(f"Preprocessing pipeline saved to session {session.id}")
            
        except Exception as e:
            logger.error(f"Error saving preprocessor to session: {str(e)}")
            
    @classmethod
    def load_from_session(cls, session: ModelTrainingSession) -> 'DataPreprocessor':
        """
        Load preprocessing pipeline from training session.
        """
        try:
            import pickle
            import base64
            
            config = session.get_config()
            if 'preprocessing' not in config:
                raise ValueError("No preprocessing configuration found in session")
                
            preprocessor_data = config['preprocessing']
            
            # Create new preprocessor instance
            preprocessor = cls(service_type=preprocessor_data.get('service_type', 'budget_ai'))
            
            # Deserialize components
            preprocessor.scalers = {
                k: pickle.loads(base64.b64decode(v.encode()))
                for k, v in preprocessor_data.get('scalers', {}).items()
            }
            preprocessor.encoders = {
                k: pickle.loads(base64.b64decode(v.encode()))
                for k, v in preprocessor_data.get('encoders', {}).items()
            }
            preprocessor.vectorizers = {
                k: pickle.loads(base64.b64decode(v.encode()))
                for k, v in preprocessor_data.get('vectorizers', {}).items()
            }
            preprocessor.imputers = {
                k: pickle.loads(base64.b64decode(v.encode()))
                for k, v in preprocessor_data.get('imputers', {}).items()
            }
            
            preprocessor.feature_names = preprocessor_data.get('feature_names', [])
            
            logger.info(f"Preprocessing pipeline loaded from session {session.id}")
            return preprocessor
            
        except Exception as e:
            logger.error(f"Error loading preprocessor from session: {str(e)}")
            # Return default preprocessor
            return cls()
            
    def get_feature_info(self) -> Dict[str, Any]:
        """
        Get information about processed features.
        """
        return {
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names,
            'numerical_features': len(self.scalers),
            'categorical_features': len(self.encoders),
            'text_features': len(self.vectorizers),
            'service_type': self.service_type
        }


def create_preprocessing_pipeline(service_type: str = 'budget_ai') -> DataPreprocessor:
    """
    Factory function to create preprocessing pipeline.
    """
    return DataPreprocessor(service_type=service_type)


def preprocess_budget_data(data: Dict[str, Any]) -> np.ndarray:
    """
    Convenience function for budget data preprocessing.
    """
    preprocessor = DataPreprocessor(service_type='budget_ai')
    features, _ = preprocessor.fit_transform(data)
    return features


def preprocess_hr_data(data: Dict[str, Any]) -> np.ndarray:
    """
    Convenience function for HR data preprocessing.
    """
    preprocessor = DataPreprocessor(service_type='hr_assistant')
    features, _ = preprocessor.fit_transform(data)
    return features