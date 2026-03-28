"""
ML-based Food Detection Service
Uses image classification to detect food items
"""

import os
import numpy as np
from PIL import Image
from typing import Dict, List, Tuple, Optional
import json

# Try to import ML libraries
try:
    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
    from tensorflow.keras.preprocessing import image as keras_image
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ TensorFlow not installed. Using fallback food detection.")


class FoodDetectionML:
    """Machine Learning based Food Detection"""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.nutrition_db = self._load_nutrition_database()
        
        # Food categories that ImageNet can recognize
        self.food_classes = {
            # Fruits
            'banana': 'fruit', 'orange': 'fruit', 'lemon': 'fruit',
            'fig': 'fruit', 'pineapple': 'fruit', 'strawberry': 'fruit',
            'pomegranate': 'fruit', 'granny_smith': 'fruit',
            
            # Vegetables
            'broccoli': 'vegetable', 'cauliflower': 'vegetable',
            'bell_pepper': 'vegetable', 'cucumber': 'vegetable',
            'mushroom': 'vegetable', 'head_cabbage': 'vegetable',
            
            # Prepared Foods
            'pizza': 'fast_food', 'hamburger': 'fast_food',
            'cheeseburger': 'fast_food', 'hotdog': 'fast_food',
            'french_loaf': 'bread', 'bagel': 'bread',
            'pretzel': 'snack', 'ice_cream': 'dessert',
            'carbonara': 'pasta', 'meat_loaf': 'meat',
            'burrito': 'mexican', 'guacamole': 'dip',
            
            # Beverages
            'espresso': 'beverage', 'cup': 'beverage',
            'red_wine': 'beverage', 'beer_glass': 'beverage',
        }
        
        if ML_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load the pre-trained MobileNetV2 model"""
        try:
            print("Loading MobileNetV2 model...")
            self.model = MobileNetV2(weights='imagenet', include_top=True)
            self.model_loaded = True
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            self.model_loaded = False
    
    def _load_nutrition_database(self) -> Dict:
        """Load nutrition information database"""
        return {
            'banana': {
                'name': 'Banana',
                'calories': 89,
                'protein': 1.1,
                'carbs': 22.8,
                'fat': 0.3,
                'fiber': 2.6,
                'vitamins': ['B6', 'C', 'Potassium'],
                'health_score': 8,
                'category': 'fruit'
            },
            'apple': {
                'name': 'Apple',
                'calories': 52,
                'protein': 0.3,
                'carbs': 14,
                'fat': 0.2,
                'fiber': 2.4,
                'vitamins': ['C', 'K'],
                'health_score': 9,
                'category': 'fruit'
            },
            'orange': {
                'name': 'Orange',
                'calories': 47,
                'protein': 0.9,
                'carbs': 12,
                'fat': 0.1,
                'fiber': 2.4,
                'vitamins': ['C', 'Thiamine'],
                'health_score': 9,
                'category': 'fruit'
            },
            'broccoli': {
                'name': 'Broccoli',
                'calories': 34,
                'protein': 2.8,
                'carbs': 7,
                'fat': 0.4,
                'fiber': 2.6,
                'vitamins': ['C', 'K', 'Folate'],
                'health_score': 10,
                'category': 'vegetable'
            },
            'pizza': {
                'name': 'Pizza',
                'calories': 266,
                'protein': 11,
                'carbs': 33,
                'fat': 10,
                'fiber': 2.3,
                'vitamins': ['Calcium', 'Iron'],
                'health_score': 4,
                'category': 'fast_food'
            },
            'hamburger': {
                'name': 'Hamburger',
                'calories': 295,
                'protein': 17,
                'carbs': 24,
                'fat': 14,
                'fiber': 1.3,
                'vitamins': ['B12', 'Iron'],
                'health_score': 3,
                'category': 'fast_food'
            },
            'rice': {
                'name': 'Rice',
                'calories': 130,
                'protein': 2.7,
                'carbs': 28,
                'fat': 0.3,
                'fiber': 0.4,
                'vitamins': ['Thiamine', 'Niacin'],
                'health_score': 6,
                'category': 'grain'
            },
            'chicken': {
                'name': 'Chicken',
                'calories': 165,
                'protein': 31,
                'carbs': 0,
                'fat': 3.6,
                'fiber': 0,
                'vitamins': ['B6', 'B12', 'Niacin'],
                'health_score': 7,
                'category': 'meat'
            },
            'salad': {
                'name': 'Salad',
                'calories': 20,
                'protein': 1.5,
                'carbs': 3.5,
                'fat': 0.2,
                'fiber': 2,
                'vitamins': ['A', 'C', 'K'],
                'health_score': 10,
                'category': 'vegetable'
            },
            'ice_cream': {
                'name': 'Ice Cream',
                'calories': 207,
                'protein': 3.5,
                'carbs': 24,
                'fat': 11,
                'fiber': 0.7,
                'vitamins': ['Calcium', 'A'],
                'health_score': 2,
                'category': 'dessert'
            },
            'espresso': {
                'name': 'Coffee',
                'calories': 2,
                'protein': 0.1,
                'carbs': 0.4,
                'fat': 0,
                'fiber': 0,
                'vitamins': ['Antioxidants'],
                'health_score': 7,
                'category': 'beverage'
            }
        }
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for model prediction"""
        img = Image.open(image_path)
        img = img.convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)
        return img_array
    
    def predict(self, image_path: str) -> Dict:
        """
        Predict food from image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with prediction results
        """
        if not ML_AVAILABLE or not self.model_loaded:
            return self._fallback_prediction(image_path)
        
        try:
            # Preprocess image
            img_array = self.preprocess_image(image_path)
            
            # Make prediction
            predictions = self.model.predict(img_array, verbose=0)
            decoded = decode_predictions(predictions, top=5)[0]
            
            # Find food-related predictions
            food_results = []
            for pred_id, pred_name, confidence in decoded:
                pred_name_clean = pred_name.lower().replace('_', ' ')
                
                # Check if it's a known food
                for food_key, category in self.food_classes.items():
                    if food_key.replace('_', ' ') in pred_name_clean or pred_name_clean in food_key.replace('_', ' '):
                        nutrition = self.nutrition_db.get(food_key, self._default_nutrition(category))
                        food_results.append({
                            'food_name': nutrition.get('name', pred_name_clean.title()),
                            'category': category,
                            'confidence': float(confidence) * 100,
                            'nutrition': nutrition,
                            'raw_prediction': pred_name
                        })
                        break
            
            if food_results:
                best = food_results[0]
                return {
                    'success': True,
                    'food_name': best['food_name'],
                    'category': best['category'],
                    'confidence': round(best['confidence'], 1),
                    'nutrition': best['nutrition'],
                    'all_predictions': food_results[:3],
                    'model_type': 'MobileNetV2 (Deep Learning)'
                }
            else:
                # No food detected
                return {
                    'success': False,
                    'message': 'Could not identify food in this image',
                    'top_predictions': [
                        {'name': d[1].replace('_', ' ').title(), 'confidence': round(d[2] * 100, 1)}
                        for d in decoded[:3]
                    ],
                    'model_type': 'MobileNetV2 (Deep Learning)'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Error processing image'
            }
    
    def _fallback_prediction(self, image_path: str) -> Dict:
        """Fallback prediction when ML is not available"""
        try:
            img = Image.open(image_path)
            img = img.convert('RGB')
            img = img.resize((100, 100))
            img_array = np.array(img)
            
            # Calculate dominant color
            avg_color = img_array.mean(axis=(0, 1))
            r, g, b = avg_color
            
            # Simple color-based classification
            if g > r and g > b:
                return {
                    'success': True,
                    'food_name': 'Green Vegetable/Fruit',
                    'category': 'vegetable',
                    'confidence': 60,
                    'nutrition': self.nutrition_db.get('broccoli'),
                    'model_type': 'Color Analysis (Fallback)',
                    'note': 'Install TensorFlow for better accuracy'
                }
            elif r > g and r > b:
                return {
                    'success': True,
                    'food_name': 'Red Fruit/Food',
                    'category': 'fruit',
                    'confidence': 55,
                    'nutrition': self.nutrition_db.get('apple'),
                    'model_type': 'Color Analysis (Fallback)',
                    'note': 'Install TensorFlow for better accuracy'
                }
            elif b > r and b > g:
                return {
                    'success': True,
                    'food_name': 'Berry/Beverage',
                    'category': 'fruit',
                    'confidence': 50,
                    'nutrition': self.nutrition_db.get('banana'),
                    'model_type': 'Color Analysis (Fallback)',
                    'note': 'Install TensorFlow for better accuracy'
                }
            else:
                return {
                    'success': True,
                    'food_name': 'General Food Item',
                    'category': 'mixed',
                    'confidence': 45,
                    'nutrition': self.nutrition_db.get('rice'),
                    'model_type': 'Color Analysis (Fallback)',
                    'note': 'Install TensorFlow for better accuracy'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Error processing image'
            }
    
    def _default_nutrition(self, category: str) -> Dict:
        """Get default nutrition for a category"""
        defaults = {
            'fruit': {'name': 'Fruit', 'calories': 60, 'protein': 0.5, 'carbs': 15, 'fat': 0.2, 'health_score': 8},
            'vegetable': {'name': 'Vegetable', 'calories': 30, 'protein': 2, 'carbs': 6, 'fat': 0.3, 'health_score': 9},
            'fast_food': {'name': 'Fast Food', 'calories': 300, 'protein': 12, 'carbs': 35, 'fat': 15, 'health_score': 3},
            'meat': {'name': 'Meat', 'calories': 200, 'protein': 25, 'carbs': 0, 'fat': 10, 'health_score': 6},
            'dessert': {'name': 'Dessert', 'calories': 250, 'protein': 3, 'carbs': 40, 'fat': 12, 'health_score': 2},
            'beverage': {'name': 'Beverage', 'calories': 50, 'protein': 0, 'carbs': 12, 'fat': 0, 'health_score': 5},
        }
        return defaults.get(category, {'name': 'Unknown', 'calories': 100, 'health_score': 5})
    
    def analyze_meal_compatibility(self, foods: List[str], medicines: List[str]) -> Dict:
        """
        Analyze meal compatibility with medicines
        Combines ML food detection with meal analyzer
        """
        from app.services.meal_analyzer import MealAnalyzer
        
        meal_analyzer = MealAnalyzer()
        meal_text = ', '.join(foods)
        
        return meal_analyzer.analyze_meal(meal_text, medicines)


# Singleton instance
food_detector = FoodDetectionML()