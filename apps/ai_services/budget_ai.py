import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import logging

from .base import BaseAIService, MLModelMixin
from .config import AIConfig
from .exceptions import PredictionError, ModelLoadError, ValidationError
from .performance_optimizer import (
    cache_prediction, 
    cache_model_load, 
    monitor_ai_performance,
    optimize_ai_service
)
from budget.models import BudgetPlan, BudgetCategory, Expense, ExpenseType
from employee.models import Employee

logger = logging.getLogger(__name__)

@optimize_ai_service
class BudgetAIService(BaseAIService, MLModelMixin):
    """
    AI Service untuk Budget Control System dengan prediksi real-time dan anomaly detection.
    """
    
    def __init__(self):
        config = AIConfig.get_config('budget')
        super().__init__(config['MODEL_NAME'], '1.0')
        self.config = config
        self.scaler = StandardScaler()
        self.anomaly_detector = None
        self.feature_names = config['FEATURES']
        self.prediction_horizon = config['PREDICTION_HORIZON_DAYS']
        self.anomaly_threshold = config['ANOMALY_THRESHOLD']
        
    @cache_model_load
    def load_model(self) -> None:
        """
        Load budget prediction model dan anomaly detector.
        """
        try:
            model_path = AIConfig.get_model_path(self.model_name)
            
            # Load main prediction model
            try:
                self.model = joblib.load(f"{model_path}/budget_predictor.pkl")
                self.scaler = joblib.load(f"{model_path}/budget_scaler.pkl")
                logger.info("Loaded existing budget prediction model")
            except FileNotFoundError:
                logger.info("No existing model found, training new model")
                self._train_model()
            
            # Load anomaly detector
            try:
                self.anomaly_detector = joblib.load(f"{model_path}/anomaly_detector.pkl")
            except FileNotFoundError:
                logger.info("Training new anomaly detector")
                self._train_anomaly_detector()
            
            self.is_loaded = True
            logger.info(f"Budget AI model loaded successfully")
            
        except Exception as e:
            raise ModelLoadError(self.model_name, str(e))
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data untuk budget prediction.
        """
        if not isinstance(input_data, dict):
            return False
        
        required_fields = ['department_id', 'budget_category', 'time_period']
        
        for field in required_fields:
            if field not in input_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate department_id
        if not isinstance(input_data['department_id'], (int, str)):
            return False
        
        # Validate budget_category
        if not isinstance(input_data['budget_category'], str):
            return False
        
        # Validate time_period
        if not isinstance(input_data['time_period'], (str, datetime)):
            return False
        
        return True
    
    @cache_prediction
    @monitor_ai_performance
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make budget prediction dengan confidence score dan recommendations.
        """
        try:
            # Extract features
            features = self._extract_features(input_data)
            
            # Scale features
            features_scaled = self.scaler.transform([features])
            
            # Make prediction
            prediction = self.model.predict(features_scaled)[0]
            
            # Calculate confidence (using prediction variance from ensemble)
            if hasattr(self.model, 'estimators_'):
                predictions = [estimator.predict(features_scaled)[0] for estimator in self.model.estimators_]
                confidence = 1.0 - (np.std(predictions) / np.mean(predictions))
                confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            else:
                confidence = 0.8  # Default confidence
            
            # Detect anomalies
            anomaly_score = self._detect_anomaly(features)
            is_anomaly = anomaly_score < -self.anomaly_threshold
            
            # Generate recommendations
            recommendations = self._generate_recommendations(input_data, prediction, anomaly_score)
            
            # Calculate budget utilization alerts
            alerts = self._calculate_alerts(input_data, prediction)
            
            return {
                'predicted_amount': round(prediction, 2),
                'confidence_score': round(confidence, 4),
                'anomaly_score': round(anomaly_score, 4),
                'is_anomaly': is_anomaly,
                'recommendations': recommendations,
                'alerts': alerts,
                'feature_importance': self.get_feature_importance(),
                'prediction_horizon_days': self.prediction_horizon
            }
            
        except Exception as e:
            raise PredictionError(f"Budget prediction failed: {str(e)}", self.model_name, input_data)
    
    def _extract_features(self, input_data: Dict[str, Any]) -> List[float]:
        """
        Extract features dari input data untuk model prediction.
        """
        features = []
        
        try:
            # Department ID (encoded)
            dept_id = int(input_data['department_id']) if input_data['department_id'] else 0
            features.append(dept_id)
            
            # Budget category (encoded)
            category_mapping = {
                'operational': 1, 'capital': 2, 'personnel': 3, 
                'marketing': 4, 'research': 5, 'other': 0
            }
            category = category_mapping.get(input_data['budget_category'].lower(), 0)
            features.append(category)
            
            # Historical spending (last 3 months average)
            historical_spending = self._get_historical_spending(
                input_data['department_id'], 
                input_data['budget_category']
            )
            features.append(historical_spending)
            
            # Employee count in department
            employee_count = self._get_employee_count(input_data['department_id'])
            features.append(employee_count)
            
            # Project count (active projects in department)
            project_count = self._get_project_count(input_data['department_id'])
            features.append(project_count)
            
            # Seasonal factor (month-based)
            current_month = datetime.now().month
            seasonal_factor = np.sin(2 * np.pi * current_month / 12)
            features.append(seasonal_factor)
            
            # Economic indicator (simplified - could be more sophisticated)
            economic_indicator = self._get_economic_indicator()
            features.append(economic_indicator)
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            # Return default features if extraction fails
            return [0.0] * len(self.feature_names)
    
    def _get_historical_spending(self, department_id: int, category: str) -> float:
        """
        Get historical spending untuk department dan category.
        """
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)  # Last 3 months
            
            # Query budget plans for historical data
            historical_budgets = BudgetPlan.objects.filter(
                created_by__employee_work_info__department_id=department_id,
                category__name__icontains=category,
                created_at__range=[start_date, end_date]
            ).aggregate(avg_amount=Avg('allocated_amount'))['avg_amount']
            
            return float(historical_budgets or 0.0)
            
        except Exception as e:
            logger.warning(f"Could not get historical spending: {str(e)}")
            return 0.0
    
    def _get_employee_count(self, department_id: int) -> int:
        """
        Get jumlah employee di department.
        """
        try:
            return Employee.objects.filter(
                employee_work_info__department_id=department_id,
                is_active=True
            ).count()
        except Exception as e:
            logger.warning(f"Could not get employee count: {str(e)}")
            return 0
    
    def _get_project_count(self, department_id: int) -> int:
        """
        Get jumlah active projects di department.
        """
        try:
            # Simplified - in real implementation, query actual project model
            # For now, return a reasonable estimate based on employee count
            employee_count = self._get_employee_count(department_id)
            return max(1, employee_count // 5)  # Assume 1 project per 5 employees
        except Exception as e:
            logger.warning(f"Could not get project count: {str(e)}")
            return 1
    
    def _get_economic_indicator(self) -> float:
        """
        Get economic indicator (simplified).
        """
        # Simplified economic indicator - in production, use real economic data
        current_month = datetime.now().month
        # Simulate economic cycles
        return 1.0 + 0.1 * np.sin(2 * np.pi * current_month / 12)
    
    def _train_model(self) -> None:
        """
        Train budget prediction model menggunakan historical data.
        """
        try:
            # Get training data
            X, y = self._prepare_training_data()
            
            if len(X) < self.config['MIN_HISTORICAL_DATA_POINTS']:
                logger.warning(f"Insufficient training data ({len(X)} points), using default model")
                self.model = RandomForestRegressor(n_estimators=100, random_state=42)
                # Train with synthetic data
                X, y = self._generate_synthetic_data()
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            
            logger.info(f"Model trained - MAE: {mae:.2f}, RMSE: {rmse:.2f}")
            
            # Save model
            model_path = AIConfig.get_model_path(self.model_name)
            import os
            os.makedirs(model_path, exist_ok=True)
            
            joblib.dump(self.model, f"{model_path}/budget_predictor.pkl")
            joblib.dump(self.scaler, f"{model_path}/budget_scaler.pkl")
            
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            # Fallback to simple model
            self.model = RandomForestRegressor(n_estimators=10, random_state=42)
            X, y = self._generate_synthetic_data()
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data dari historical budget records.
        """
        try:
            # Get historical budget data
            budgets = BudgetPlan.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=365)
            ).select_related('created_by__employee_work_info__department')
            
            X, y = [], []
            
            for budget in budgets:
                # Extract features for each budget record
                input_data = {
                    'department_id': budget.created_by.employee_work_info.department_id if budget.created_by and hasattr(budget.created_by, 'employee_work_info') and budget.created_by.employee_work_info.department_id else 0,
                    'budget_category': 'operational',  # Default category
                    'time_period': budget.created_at
                }
                
                features = self._extract_features(input_data)
                target = float(budget.allocated_amount or 0)
                
                if target > 0:  # Only include valid budget amounts
                    X.append(features)
                    y.append(target)
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"Training data preparation failed: {str(e)}")
            return np.array([]), np.array([])
    
    def _generate_synthetic_data(self, n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data jika historical data tidak cukup.
        """
        np.random.seed(42)
        
        X = []
        y = []
        
        for _ in range(n_samples):
            # Generate synthetic features
            dept_id = np.random.randint(1, 20)
            category = np.random.randint(0, 6)
            historical_spending = np.random.uniform(10000, 500000)
            employee_count = np.random.randint(5, 100)
            project_count = np.random.randint(1, 20)
            seasonal_factor = np.random.uniform(-1, 1)
            economic_indicator = np.random.uniform(0.8, 1.2)
            
            features = [dept_id, category, historical_spending, employee_count, 
                       project_count, seasonal_factor, economic_indicator]
            
            # Generate target based on features (with some realistic relationships)
            target = (
                historical_spending * 1.1 +  # Base on historical
                employee_count * 5000 +      # Employee factor
                project_count * 10000 +      # Project factor
                np.random.normal(0, 10000)   # Random noise
            )
            target = max(0, target)  # Ensure positive
            
            X.append(features)
            y.append(target)
        
        return np.array(X), np.array(y)
    
    def _train_anomaly_detector(self) -> None:
        """
        Train anomaly detection model.
        """
        try:
            # Get training data for anomaly detection
            X, _ = self._prepare_training_data()
            
            if len(X) < 50:  # Minimum data for anomaly detection
                X, _ = self._generate_synthetic_data(500)
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Train isolation forest
            self.anomaly_detector = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42
            )
            
            self.anomaly_detector.fit(X_scaled)
            
            # Save model
            model_path = AIConfig.get_model_path(self.model_name)
            joblib.dump(self.anomaly_detector, f"{model_path}/anomaly_detector.pkl")
            
            logger.info("Anomaly detector trained successfully")
            
        except Exception as e:
            logger.error(f"Anomaly detector training failed: {str(e)}")
            # Fallback to simple anomaly detector
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
    
    def _detect_anomaly(self, features: List[float]) -> float:
        """
        Detect anomaly dalam budget prediction.
        """
        try:
            if self.anomaly_detector is None:
                return 0.0
            
            features_scaled = self.scaler.transform([features])
            anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
            
            return anomaly_score
            
        except Exception as e:
            logger.warning(f"Anomaly detection failed: {str(e)}")
            return 0.0
    
    def _generate_recommendations(self, input_data: Dict[str, Any], 
                                prediction: float, anomaly_score: float) -> List[str]:
        """
        Generate budget recommendations berdasarkan prediction dan anomaly score.
        """
        recommendations = []
        
        try:
            # Historical comparison
            historical_avg = self._get_historical_spending(
                input_data['department_id'], 
                input_data['budget_category']
            )
            
            if historical_avg > 0:
                change_percent = ((prediction - historical_avg) / historical_avg) * 100
                
                if change_percent > 20:
                    recommendations.append(
                        f"Prediksi anggaran {change_percent:.1f}% lebih tinggi dari rata-rata historis. "
                        "Pertimbangkan untuk review kebutuhan anggaran."
                    )
                elif change_percent < -20:
                    recommendations.append(
                        f"Prediksi anggaran {abs(change_percent):.1f}% lebih rendah dari rata-rata historis. "
                        "Mungkin ada peluang untuk optimasi atau realokasi."
                    )
            
            # Anomaly-based recommendations
            if anomaly_score < -self.anomaly_threshold:
                recommendations.append(
                    "Terdeteksi pola anggaran yang tidak biasa. "
                    "Disarankan untuk melakukan review mendalam terhadap kebutuhan anggaran."
                )
            
            # Seasonal recommendations
            current_month = datetime.now().month
            if current_month in [12, 1, 2]:  # End/start of year
                recommendations.append(
                    "Periode akhir/awal tahun - pertimbangkan penyesuaian anggaran "
                    "untuk perencanaan tahunan."
                )
            
            # Budget size recommendations
            if prediction > 1000000:  # Large budget
                recommendations.append(
                    "Anggaran besar terdeteksi. Pastikan ada approval dan monitoring ketat."
                )
            elif prediction < 10000:  # Small budget
                recommendations.append(
                    "Anggaran kecil - pertimbangkan untuk menggabungkan dengan kategori lain "
                    "untuk efisiensi administrasi."
                )
            
            return recommendations
            
        except Exception as e:
            logger.warning(f"Recommendation generation failed: {str(e)}")
            return ["Tidak dapat menggenerate rekomendasi saat ini."]
    
    def _calculate_alerts(self, input_data: Dict[str, Any], prediction: float) -> List[Dict[str, Any]]:
        """
        Calculate budget utilization alerts.
        """
        alerts = []
        
        try:
            # Get current budget allocation
            current_budget = self._get_current_budget_allocation(
                input_data['department_id'], 
                input_data['budget_category']
            )
            
            if current_budget > 0:
                utilization = prediction / current_budget
                
                alert_thresholds = self.config['ALERT_THRESHOLDS']
                
                if utilization >= alert_thresholds['high']:
                    alerts.append({
                        'level': 'high',
                        'message': f"Peringatan: Utilisasi anggaran mencapai {utilization*100:.1f}%",
                        'utilization': utilization,
                        'threshold': alert_thresholds['high']
                    })
                elif utilization >= alert_thresholds['medium']:
                    alerts.append({
                        'level': 'medium',
                        'message': f"Perhatian: Utilisasi anggaran mencapai {utilization*100:.1f}%",
                        'utilization': utilization,
                        'threshold': alert_thresholds['medium']
                    })
                elif utilization >= alert_thresholds['low']:
                    alerts.append({
                        'level': 'low',
                        'message': f"Info: Utilisasi anggaran mencapai {utilization*100:.1f}%",
                        'utilization': utilization,
                        'threshold': alert_thresholds['low']
                    })
            
            return alerts
            
        except Exception as e:
            logger.warning(f"Alert calculation failed: {str(e)}")
            return []
    
    def _get_current_budget_allocation(self, department_id: int, category: str) -> float:
        """
        Get current budget allocation untuk department dan category.
        """
        try:
            current_year = datetime.now().year
            
            budget_allocation = BudgetPlan.objects.filter(
                created_by__employee_work_info__department_id=department_id,
                category__name__icontains=category,
                created_at__year=current_year
            ).aggregate(total=Sum('allocated_amount'))['total']
            
            return float(budget_allocation or 0.0)
            
        except Exception as e:
            logger.warning(f"Could not get current budget allocation: {str(e)}")
            return 0.0
    
    @cache_prediction
    @monitor_ai_performance
    def get_budget_analytics(self, department_id: int = None, 
                           time_range: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive budget analytics.
        """
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=time_range)
            
            # Base query
            query = BudgetPlan.objects.filter(
                created_at__range=[start_date, end_date]
            )
            
            if department_id:
                query = query.filter(created_by__employee_work_info__department_id=department_id)
            
            # Calculate analytics
            analytics = {
                'total_budget': query.aggregate(total=Sum('allocated_amount'))['total'] or 0,
                'average_budget': query.aggregate(avg=Avg('allocated_amount'))['avg'] or 0,
                'budget_count': query.count(),
                'department_breakdown': {},
                'category_breakdown': {},
                'trend_analysis': self._calculate_trend_analysis(department_id, time_range),
                'anomaly_summary': self._get_anomaly_summary(department_id, time_range)
            }
            
            # Department breakdown
            dept_breakdown = query.values('created_by__employee_work_info__department_id').annotate(
                total=Sum('allocated_amount'),
                count=Count('id')
            )
            
            for item in dept_breakdown:
                dept_id = item['created_by__employee_work_info__department_id'] or 'Unknown'
                analytics['department_breakdown'][str(dept_id)] = {
                    'total': item['total'],
                    'count': item['count'],
                    'average': item['total'] / item['count'] if item['count'] > 0 else 0
                }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Budget analytics calculation failed: {str(e)}")
            return {
                'error': str(e),
                'total_budget': 0,
                'average_budget': 0,
                'budget_count': 0
            }
    
    def _calculate_trend_analysis(self, department_id: int = None, 
                                time_range: int = 30) -> Dict[str, Any]:
        """
        Calculate budget trend analysis.
        """
        try:
            # Get data for trend analysis
            end_date = timezone.now()
            start_date = end_date - timedelta(days=time_range * 2)  # Double range for comparison
            
            query = BudgetPlan.objects.filter(
                created_at__range=[start_date, end_date]
            )
            
            if department_id:
                query = query.filter(created_by__employee_work_info__department_id=department_id)
            
            # Split into two periods
            mid_date = start_date + timedelta(days=time_range)
            
            period1_total = query.filter(
                created_at__range=[start_date, mid_date]
            ).aggregate(total=Sum('allocated_amount'))['total'] or 0
            
            period2_total = query.filter(
                created_at__range=[mid_date, end_date]
            ).aggregate(total=Sum('allocated_amount'))['total'] or 0
            
            # Calculate trend
            if period1_total > 0:
                trend_percent = ((period2_total - period1_total) / period1_total) * 100
            else:
                trend_percent = 0
            
            trend_direction = 'increasing' if trend_percent > 5 else 'decreasing' if trend_percent < -5 else 'stable'
            
            return {
                'trend_percent': round(trend_percent, 2),
                'trend_direction': trend_direction,
                'period1_total': period1_total,
                'period2_total': period2_total
            }
            
        except Exception as e:
            logger.warning(f"Trend analysis failed: {str(e)}")
            return {
                'trend_percent': 0,
                'trend_direction': 'unknown',
                'error': str(e)
            }
    
    def _get_anomaly_summary(self, department_id: int = None, 
                           time_range: int = 30) -> Dict[str, Any]:
        """
        Get summary of budget anomalies.
        """
        try:
            if not self.anomaly_detector:
                return {'anomaly_count': 0, 'message': 'Anomaly detector not available'}
            
            # Get recent budget data
            end_date = timezone.now()
            start_date = end_date - timedelta(days=time_range)
            
            query = BudgetPlan.objects.filter(
                created_at__range=[start_date, end_date]
            )
            
            if department_id:
                query = query.filter(created_by__employee_work_info__department_id=department_id)
            
            anomaly_count = 0
            total_checked = 0
            
            for budget in query:
                input_data = {
                    'department_id': budget.created_by.employee_work_info.department_id if budget.created_by and hasattr(budget.created_by, 'employee_work_info') and budget.created_by.employee_work_info.department_id else 0,
                    'budget_category': 'operational',
                    'time_period': budget.created_at
                }
                
                features = self._extract_features(input_data)
                anomaly_score = self._detect_anomaly(features)
                
                if anomaly_score < -self.anomaly_threshold:
                    anomaly_count += 1
                
                total_checked += 1
            
            anomaly_rate = (anomaly_count / total_checked * 100) if total_checked > 0 else 0
            
            return {
                'anomaly_count': anomaly_count,
                'total_checked': total_checked,
                'anomaly_rate': round(anomaly_rate, 2),
                'threshold': self.anomaly_threshold
            }
            
        except Exception as e:
            logger.warning(f"Anomaly summary failed: {str(e)}")
            return {
                'anomaly_count': 0,
                'error': str(e)
            }