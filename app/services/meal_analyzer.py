"""
Meal Analyzer Service - Check food-medicine interactions
"""

import re
from typing import Dict, List

class MealAnalyzer:
    """Service for analyzing meal safety with medications"""
    
    # Food categories for better matching
    FOOD_CATEGORIES = {
        'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'paneer', 'curd', 
                  'ice cream', 'ghee', 'cottage cheese'],
        'citrus': ['orange', 'lemon', 'lime', 'grapefruit', 'tangerine', 'citrus'],
        'leafy_greens': ['spinach', 'kale', 'lettuce', 'cabbage', 'broccoli', 
                         'brussels sprouts', 'collard', 'chard', 'methi', 'palak'],
        'alcohol': ['beer', 'wine', 'whiskey', 'vodka', 'rum', 'alcohol', 'liquor',
                    'cocktail', 'champagne', 'brandy'],
        'caffeine': ['coffee', 'tea', 'energy drink', 'cola', 'espresso', 'latte',
                     'cappuccino', 'green tea', 'black tea'],
        'high_protein': ['meat', 'chicken', 'fish', 'egg', 'protein shake', 'beans',
                         'lentils', 'dal', 'paneer', 'tofu', 'mutton', 'beef', 'pork'],
        'fermented': ['kimchi', 'sauerkraut', 'pickles', 'soy sauce', 'miso', 
                      'aged cheese', 'wine', 'beer', 'idli', 'dosa'],
        'high_fiber': ['oats', 'whole wheat', 'bran', 'beans', 'vegetables', 
                       'brown rice', 'quinoa', 'chia seeds'],
        'high_potassium': ['banana', 'potato', 'tomato', 'orange juice', 'coconut water',
                           'spinach', 'sweet potato', 'avocado'],
        'tyramine_rich': ['aged cheese', 'red wine', 'soy sauce', 'sauerkraut', 
                          'processed meats', 'fermented foods']
    }
    
    # Medicine-food interactions database
    MEDICINE_FOOD_INTERACTIONS = {
        'warfarin': {
            'avoid': ['leafy_greens', 'alcohol'],
            'foods': ['spinach', 'kale', 'broccoli', 'alcohol'],
            'severity': 'high',
            'description': 'Vitamin K in green vegetables can reduce Warfarin effectiveness. Alcohol increases bleeding risk.',
            'recommendation': 'Maintain consistent vitamin K intake. Avoid or limit alcohol.'
        },
        'metformin': {
            'avoid': ['alcohol'],
            'foods': ['alcohol', 'beer', 'wine'],
            'severity': 'high',
            'description': 'Alcohol increases the risk of lactic acidosis with Metformin.',
            'recommendation': 'Avoid alcohol completely while on this medication.'
        },
        'simvastatin': {
            'avoid': ['citrus'],
            'foods': ['grapefruit', 'grapefruit juice'],
            'severity': 'high',
            'description': 'Grapefruit significantly increases Simvastatin levels, risking muscle damage.',
            'recommendation': 'Avoid grapefruit and grapefruit juice entirely.'
        },
        'atorvastatin': {
            'avoid': ['citrus'],
            'foods': ['grapefruit'],
            'severity': 'medium',
            'description': 'Grapefruit may increase medication levels.',
            'recommendation': 'Limit grapefruit consumption.'
        },
        'ciprofloxacin': {
            'avoid': ['dairy', 'caffeine'],
            'foods': ['milk', 'cheese', 'yogurt', 'coffee'],
            'severity': 'medium',
            'description': 'Dairy products reduce antibiotic absorption. Caffeine effects may be enhanced.',
            'recommendation': 'Take medication 2 hours before or 6 hours after dairy products.'
        },
        'tetracycline': {
            'avoid': ['dairy'],
            'foods': ['milk', 'cheese', 'yogurt', 'antacids'],
            'severity': 'high',
            'description': 'Calcium in dairy significantly reduces antibiotic absorption.',
            'recommendation': 'Take on empty stomach, 1 hour before or 2 hours after meals.'
        },
        'levothyroxine': {
            'avoid': ['caffeine', 'high_fiber'],
            'foods': ['coffee', 'soy', 'high-fiber foods', 'calcium supplements'],
            'severity': 'medium',
            'description': 'These foods can reduce thyroid medication absorption.',
            'recommendation': 'Take medication on empty stomach, 30-60 minutes before breakfast.'
        },
        'lisinopril': {
            'avoid': ['high_potassium'],
            'foods': ['banana', 'potato', 'orange juice', 'salt substitutes'],
            'severity': 'medium',
            'description': 'This medication increases potassium levels. High potassium foods may cause hyperkalemia.',
            'recommendation': 'Moderate intake of potassium-rich foods.'
        },
        'mao inhibitor': {
            'avoid': ['tyramine_rich', 'fermented'],
            'foods': ['aged cheese', 'red wine', 'soy sauce', 'processed meats'],
            'severity': 'critical',
            'description': 'Tyramine-rich foods can cause dangerous blood pressure spikes.',
            'recommendation': 'Strictly avoid these foods. This is a medical emergency risk.'
        },
        'aspirin': {
            'avoid': ['alcohol'],
            'foods': ['alcohol'],
            'severity': 'medium',
            'description': 'Alcohol increases risk of stomach bleeding with Aspirin.',
            'recommendation': 'Avoid or limit alcohol consumption.'
        },
        'ibuprofen': {
            'avoid': ['alcohol'],
            'foods': ['alcohol'],
            'severity': 'medium',
            'description': 'Alcohol increases risk of stomach irritation and bleeding.',
            'recommendation': 'Avoid alcohol. Take with food to reduce stomach upset.'
        },
        'amlodipine': {
            'avoid': ['citrus'],
            'foods': ['grapefruit'],
            'severity': 'medium',
            'description': 'Grapefruit may increase medication levels.',
            'recommendation': 'Limit grapefruit consumption.'
        },
        'digoxin': {
            'avoid': ['high_fiber'],
            'foods': ['bran', 'high-fiber cereals'],
            'severity': 'medium',
            'description': 'High fiber can reduce Digoxin absorption.',
            'recommendation': 'Take medication separately from high-fiber meals.'
        }
    }
    
    def __init__(self):
        pass
    
    def extract_foods(self, meal_text: str) -> List[str]:
        """Extract individual food items from meal description"""
        # Clean and split the text
        meal_lower = meal_text.lower()
        
        # Remove common connecting words
        connectors = ['and', 'with', 'plus', 'also', 'including', 'along with', 
                      'served with', 'topped with', 'containing']
        for connector in connectors:
            meal_lower = meal_lower.replace(connector, ',')
        
        # Split by common separators
        foods = re.split(r'[,;.\n]+', meal_lower)
        
        # Clean each food item
        cleaned_foods = []
        for food in foods:
            food = food.strip()
            if food and len(food) > 1:
                cleaned_foods.append(food)
        
        return cleaned_foods
    
    def categorize_food(self, food: str) -> List[str]:
        """Categorize a food item"""
        categories = []
        food_lower = food.lower()
        
        for category, items in self.FOOD_CATEGORIES.items():
            for item in items:
                if item in food_lower or food_lower in item:
                    categories.append(category)
                    break
        
        return categories
    
    def analyze_meal(self, meal_text: str, medicines: List[str]) -> Dict:
        """Analyze meal safety with patient's medications"""
        
        # Extract foods from meal description
        foods = self.extract_foods(meal_text)
        
        # Categorize foods
        food_categories = set()
        identified_foods = []
        for food in foods:
            cats = self.categorize_food(food)
            food_categories.update(cats)
            identified_foods.append({
                'name': food,
                'categories': cats
            })
        
        # Check interactions
        warnings = []
        safe_items = []
        
        for medicine in medicines:
            medicine_lower = medicine.lower().strip()
            
            # Find medicine in interaction database
            interaction = None
            for med_key, data in self.MEDICINE_FOOD_INTERACTIONS.items():
                if med_key in medicine_lower or medicine_lower in med_key:
                    interaction = data
                    break
            
            if not interaction:
                continue
            
            # Check for problematic foods
            for food in foods:
                food_lower = food.lower()
                
                # Direct food match
                for problem_food in interaction['foods']:
                    if problem_food in food_lower or food_lower in problem_food:
                        warnings.append({
                            'medicine': medicine,
                            'food': food,
                            'severity': interaction['severity'],
                            'description': interaction['description'],
                            'recommendation': interaction['recommendation']
                        })
                        break
                
                # Category match
                food_cats = self.categorize_food(food)
                for cat in food_cats:
                    if cat in interaction.get('avoid', []):
                        warnings.append({
                            'medicine': medicine,
                            'food': food,
                            'category': cat,
                            'severity': interaction['severity'],
                            'description': interaction['description'],
                            'recommendation': interaction['recommendation']
                        })
        
        # Determine overall safety
        is_safe = len(warnings) == 0
        has_critical = any(w['severity'] == 'critical' for w in warnings)
        has_high = any(w['severity'] == 'high' for w in warnings)
        
        return {
            'is_safe': is_safe,
            'identified_foods': identified_foods,
            'warnings': warnings,
            'summary': {
                'total_foods': len(foods),
                'total_warnings': len(warnings),
                'has_critical': has_critical,
                'has_high': has_high
            },
            'message': self._generate_message(is_safe, warnings)
        }
    
    def _generate_message(self, is_safe: bool, warnings: List[Dict]) -> str:
        """Generate user-friendly message"""
        if is_safe:
            return "✅ Your meal appears safe with your current medications. Enjoy your meal!"
        
        critical_count = sum(1 for w in warnings if w['severity'] == 'critical')
        high_count = sum(1 for w in warnings if w['severity'] == 'high')
        
        if critical_count > 0:
            return f"🚨 CRITICAL WARNING: {critical_count} dangerous interaction(s) detected! Please avoid these foods."
        elif high_count > 0:
            return f"⚠️ WARNING: {high_count} significant interaction(s) found. Please review and modify your meal."
        else:
            return f"⚡ CAUTION: {len(warnings)} potential interaction(s) detected. Review the recommendations."