"""
Prediction Service - ML-based patient inflow prediction
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random

class PredictionService:
    """Service for predicting patient inflow and analytics"""
    
    def __init__(self):
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize prediction model"""
        try:
            from sklearn.linear_model import LinearRegression
            from sklearn.ensemble import RandomForestRegressor
            self.model_type = 'random_forest'
            self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        except ImportError:
            self.model = None
            self.model_type = 'simple'
    
    def generate_historical_data(self, days: int = 90) -> List[Dict]:
        """Generate simulated historical patient data"""
        data = []
        base_date = datetime.now() - timedelta(days=days)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            
            # Base patient count with weekly pattern
            day_of_week = date.weekday()
            
            # Monday-Friday: higher, Sat-Sun: lower
            if day_of_week < 5:
                base_count = random.randint(80, 120)
            else:
                base_count = random.randint(40, 70)
            
            # Add seasonal variation
            month = date.month
            if month in [1, 2, 12]:  # Winter
                base_count = int(base_count * 1.2)
            elif month in [6, 7, 8]:  # Summer
                base_count = int(base_count * 1.1)
            
            # Add some random noise
            patient_count = base_count + random.randint(-10, 10)
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'day_of_week': day_of_week,
                'month': month,
                'patient_count': max(patient_count, 20),
                'emergency_count': random.randint(5, 25),
                'icu_occupancy': random.randint(40, 95),
                'opd_count': random.randint(50, 150)
            })
        
        return data
    
    def prepare_features(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for model training"""
        X = []
        y = []
        
        for record in data:
            features = [
                record['day_of_week'],
                record['month'],
                1 if record['day_of_week'] < 5 else 0,  # is_weekday
            ]
            X.append(features)
            y.append(record['patient_count'])
        
        return np.array(X), np.array(y)
    
    def train_model(self, data: List[Dict]):
        """Train the prediction model"""
        if self.model is None:
            return False
        
        X, y = self.prepare_features(data)
        self.model.fit(X, y)
        return True
    
    def predict_next_days(self, days: int = 7) -> List[Dict]:
        """Predict patient inflow for next N days"""
        predictions = []
        today = datetime.now()
        
        for i in range(1, days + 1):
            future_date = today + timedelta(days=i)
            day_of_week = future_date.weekday()
            month = future_date.month
            
            if self.model is not None:
                try:
                    features = np.array([[day_of_week, month, 1 if day_of_week < 5 else 0]])
                    predicted_count = int(self.model.predict(features)[0])
                except Exception:
                    predicted_count = self._simple_prediction(day_of_week, month)
            else:
                predicted_count = self._simple_prediction(day_of_week, month)
            
            # Calculate confidence interval (simplified)
            lower_bound = int(predicted_count * 0.85)
            upper_bound = int(predicted_count * 1.15)
            
            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'day_name': future_date.strftime('%A'),
                'predicted_count': predicted_count,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound,
                'confidence': 85
            })
        
        return predictions
    
    def _simple_prediction(self, day_of_week: int, month: int) -> int:
        """Simple rule-based prediction when ML model is unavailable"""
        # Base prediction
        if day_of_week < 5:
            base = 100
        else:
            base = 55
        
        # Seasonal adjustment
        if month in [1, 2, 12]:
            base = int(base * 1.2)
        elif month in [6, 7, 8]:
            base = int(base * 1.1)
        
        # Add some variance
        return base + random.randint(-5, 5)
    
    def get_model_metrics(self, data: List[Dict]) -> Dict:
        """Calculate model performance metrics"""
        if self.model is None or len(data) < 10:
            return {
                'mae': 'N/A',
                'rmse': 'N/A',
                'r2': 'N/A',
                'model_type': self.model_type
            }
        
        try:
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
            
            # Use last 20% as test data
            split_idx = int(len(data) * 0.8)
            train_data = data[:split_idx]
            test_data = data[split_idx:]
            
            # Train on training data
            X_train, y_train = self.prepare_features(train_data)
            X_test, y_test = self.prepare_features(test_data)
            
            self.model.fit(X_train, y_train)
            y_pred = self.model.predict(X_test)
            
            return {
                'mae': round(mean_absolute_error(y_test, y_pred), 2),
                'rmse': round(np.sqrt(mean_squared_error(y_test, y_pred)), 2),
                'r2': round(r2_score(y_test, y_pred), 3),
                'model_type': self.model_type
            }
        except Exception as e:
            return {
                'mae': 'Error',
                'rmse': 'Error',
                'r2': 'Error',
                'model_type': self.model_type,
                'error': str(e)
            }
    
    def get_analytics_summary(self, data: List[Dict]) -> Dict:
        """Generate analytics summary from historical data"""
        if not data:
            return {}
        
        patient_counts = [d['patient_count'] for d in data]
        emergency_counts = [d['emergency_count'] for d in data]
        
        # Calculate averages by day of week
        day_averages = {}
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                     'Friday', 'Saturday', 'Sunday']
        for i in range(7):
            day_data = [d['patient_count'] for d in data if d['day_of_week'] == i]
            day_averages[day_names[i]] = round(np.mean(day_data), 1) if day_data else 0
        
        # Find busiest day
        busiest_day = max(day_averages, key=day_averages.get)
        
        return {
            'total_patients': sum(patient_counts),
            'average_daily': round(np.mean(patient_counts), 1),
            'max_daily': max(patient_counts),
            'min_daily': min(patient_counts),
            'total_emergency': sum(emergency_counts),
            'average_emergency': round(np.mean(emergency_counts), 1),
            'day_averages': day_averages,
            'busiest_day': busiest_day,
            'trend': 'stable'  # Simplified trend analysis
        }