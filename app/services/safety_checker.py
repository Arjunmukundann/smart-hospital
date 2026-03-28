"""
Safety Checker Service - Drug and allergy interaction checks
"""

import os
import json
from typing import Dict, List, Optional
from flask import current_app

class SafetyChecker:
    """Service for checking prescription safety"""
    
    # Common drug-drug interactions
    DRUG_INTERACTIONS = {
        ('warfarin', 'aspirin'): {
            'severity': 'high',
            'description': 'Increased risk of bleeding when used together',
            'recommendation': 'Monitor closely for signs of bleeding; consider alternatives'
        },
        ('metformin', 'alcohol'): {
            'severity': 'high',
            'description': 'Increased risk of lactic acidosis',
            'recommendation': 'Avoid alcohol consumption while on Metformin'
        },
        ('simvastatin', 'erythromycin'): {
            'severity': 'high',
            'description': 'Increased risk of myopathy/rhabdomyolysis',
            'recommendation': 'Avoid combination; use alternative antibiotic'
        },
        ('lisinopril', 'potassium'): {
            'severity': 'medium',
            'description': 'Risk of hyperkalemia',
            'recommendation': 'Monitor potassium levels regularly'
        },
        ('ciprofloxacin', 'antacids'): {
            'severity': 'medium',
            'description': 'Reduced absorption of Ciprofloxacin',
            'recommendation': 'Take Ciprofloxacin 2 hours before antacids'
        },
        ('methotrexate', 'ibuprofen'): {
            'severity': 'high',
            'description': 'Increased Methotrexate toxicity',
            'recommendation': 'Avoid NSAIDs; use Paracetamol instead'
        },
        ('digoxin', 'amiodarone'): {
            'severity': 'high',
            'description': 'Increased Digoxin levels and toxicity',
            'recommendation': 'Reduce Digoxin dose by 50%'
        },
        ('clopidogrel', 'omeprazole'): {
            'severity': 'medium',
            'description': 'Reduced antiplatelet effect of Clopidogrel',
            'recommendation': 'Use alternative PPI like Pantoprazole'
        }
    }
    
    # Common drug-food interactions
    FOOD_INTERACTIONS = {
        'warfarin': {
            'foods': ['spinach', 'kale', 'broccoli', 'green leafy vegetables'],
            'severity': 'medium',
            'description': 'Vitamin K in these foods can reduce Warfarin effectiveness',
            'recommendation': 'Maintain consistent intake of Vitamin K foods'
        },
        'tetracycline': {
            'foods': ['milk', 'dairy', 'cheese', 'yogurt', 'calcium'],
            'severity': 'medium',
            'description': 'Calcium reduces absorption of Tetracycline',
            'recommendation': 'Take medication 2 hours before/after dairy'
        },
        'metformin': {
            'foods': ['alcohol', 'beer', 'wine', 'spirits'],
            'severity': 'high',
            'description': 'Alcohol increases risk of lactic acidosis with Metformin',
            'recommendation': 'Avoid or limit alcohol consumption'
        },
        'ciprofloxacin': {
            'foods': ['milk', 'dairy', 'calcium supplements'],
            'severity': 'medium',
            'description': 'Calcium reduces Ciprofloxacin absorption',
            'recommendation': 'Take 2 hours before or 6 hours after dairy'
        },
        'simvastatin': {
            'foods': ['grapefruit', 'grapefruit juice'],
            'severity': 'high',
            'description': 'Grapefruit increases Simvastatin levels significantly',
            'recommendation': 'Avoid grapefruit entirely'
        },
        'mao inhibitors': {
            'foods': ['aged cheese', 'red wine', 'soy sauce', 'fermented foods'],
            'severity': 'critical',
            'description': 'Tyramine-rich foods can cause hypertensive crisis',
            'recommendation': 'Strictly avoid these foods during treatment'
        },
        'levothyroxine': {
            'foods': ['soy', 'coffee', 'high-fiber foods'],
            'severity': 'medium',
            'description': 'These foods can reduce Levothyroxine absorption',
            'recommendation': 'Take medication on empty stomach, 30-60 min before food'
        }
    }
    
    # Common allergen-medicine mappings
    ALLERGEN_MEDICINE_MAP = {
        'penicillin': ['amoxicillin', 'ampicillin', 'penicillin v', 'penicillin g', 
                       'piperacillin', 'augmentin', 'amoxiclav'],
        'sulfa': ['sulfamethoxazole', 'trimethoprim-sulfamethoxazole', 'bactrim', 
                  'sulfasalazine', 'sulfadiazine'],
        'aspirin': ['aspirin', 'acetylsalicylic acid', 'ecosprin', 'disprin'],
        'ibuprofen': ['ibuprofen', 'brufen', 'advil', 'motrin'],
        'nsaid': ['ibuprofen', 'naproxen', 'diclofenac', 'indomethacin', 
                  'piroxicam', 'celecoxib'],
        'codeine': ['codeine', 'co-codamol', 'morphine', 'tramadol', 'oxycodone'],
        'latex': [],  # No direct medicine, but important for procedures
        'eggs': ['flu vaccine', 'mmr vaccine'],  # Some vaccines
        'shellfish': ['glucosamine'],  # Shellfish-derived supplements
    }
    
    def __init__(self):
        self.load_interaction_data()
    
    def load_interaction_data(self):
        """Load additional interaction data from CSV files"""
        try:
            data_folder = current_app.config.get('DATA_FOLDER', '')
            
            # Load drug interactions from CSV if available
            drug_file = os.path.join(data_folder, 'drug_interactions.csv')
            if os.path.exists(drug_file):
                self._load_drug_interactions_csv(drug_file)
            
            # Load food interactions from CSV if available
            food_file = os.path.join(data_folder, 'food_interactions.csv')
            if os.path.exists(food_file):
                self._load_food_interactions_csv(food_file)
                
        except Exception as e:
            print(f"Warning: Could not load interaction data: {e}")
    
    def _load_drug_interactions_csv(self, filepath: str):
        """Load drug interactions from CSV file"""
        import csv
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    drug1 = row.get('drug1', '').lower().strip()
                    drug2 = row.get('drug2', '').lower().strip()
                    if drug1 and drug2:
                        self.DRUG_INTERACTIONS[(drug1, drug2)] = {
                            'severity': row.get('severity', 'medium'),
                            'description': row.get('description', ''),
                            'recommendation': row.get('recommendation', '')
                        }
        except Exception as e:
            print(f"Error loading drug interactions CSV: {e}")
    
    def _load_food_interactions_csv(self, filepath: str):
        """Load food interactions from CSV file"""
        import csv
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    drug = row.get('drug', '').lower().strip()
                    if drug:
                        foods = [f.strip() for f in row.get('foods', '').split(';')]
                        self.FOOD_INTERACTIONS[drug] = {
                            'foods': foods,
                            'severity': row.get('severity', 'medium'),
                            'description': row.get('description', ''),
                            'recommendation': row.get('recommendation', '')
                        }
        except Exception as e:
            print(f"Error loading food interactions CSV: {e}")
    
    def check_allergies(self, medicines: List[str], patient_allergies: List[str]) -> List[Dict]:
        """Check if any prescribed medicine conflicts with patient allergies"""
        alerts = []
        
        for medicine in medicines:
            medicine_lower = medicine.lower().strip()
            
            for allergy in patient_allergies:
                allergy_lower = allergy.lower().strip()
                
                # Direct match
                if allergy_lower in medicine_lower or medicine_lower in allergy_lower:
                    alerts.append({
                        'type': 'allergy',
                        'severity': 'critical',
                        'medicine': medicine,
                        'conflicting_item': allergy,
                        'description': f'Patient is allergic to {allergy}. {medicine} may cause allergic reaction.',
                        'recommendation': 'Do NOT prescribe. Find alternative medication.'
                    })
                    continue
                
                # Check allergen-medicine mapping
                for allergen, related_medicines in self.ALLERGEN_MEDICINE_MAP.items():
                    if allergy_lower in allergen or allergen in allergy_lower:
                        if medicine_lower in [m.lower() for m in related_medicines]:
                            alerts.append({
                                'type': 'allergy',
                                'severity': 'critical',
                                'medicine': medicine,
                                'conflicting_item': allergy,
                                'description': f'Patient is allergic to {allergy}. {medicine} is contraindicated.',
                                'recommendation': 'Do NOT prescribe. Choose alternative medication.'
                            })
        
        return alerts
    
    def check_drug_interactions(self, medicines: List[str]) -> List[Dict]:
        """Check for drug-drug interactions among prescribed medicines"""
        alerts = []
        medicines_lower = [m.lower().strip() for m in medicines]
        
        # Check each pair of medicines
        for i, med1 in enumerate(medicines_lower):
            for med2 in medicines_lower[i+1:]:
                # Check both orderings
                interaction = None
                for (drug1, drug2), data in self.DRUG_INTERACTIONS.items():
                    if (drug1 in med1 or med1 in drug1) and (drug2 in med2 or med2 in drug2):
                        interaction = data
                        break
                    if (drug2 in med1 or med1 in drug2) and (drug1 in med2 or med2 in drug1):
                        interaction = data
                        break
                
                if interaction:
                    alerts.append({
                        'type': 'drug_drug',
                        'severity': interaction['severity'],
                        'medicine': medicines[medicines_lower.index(med1)],
                        'conflicting_item': medicines[medicines_lower.index(med2)],
                        'description': interaction['description'],
                        'recommendation': interaction['recommendation']
                    })
        
        return alerts
    
    def check_food_interactions(self, medicines: List[str]) -> List[Dict]:
        """Get food interaction warnings for prescribed medicines"""
        alerts = []
        
        for medicine in medicines:
            medicine_lower = medicine.lower().strip()
            
            for drug, data in self.FOOD_INTERACTIONS.items():
                if drug in medicine_lower or medicine_lower in drug:
                    alerts.append({
                        'type': 'drug_food',
                        'severity': data['severity'],
                        'medicine': medicine,
                        'conflicting_item': ', '.join(data['foods']),
                        'description': data['description'],
                        'recommendation': data['recommendation']
                    })
        
        return alerts
    
    def perform_full_check(self, medicines: List[str], patient_allergies: List[str], 
                           current_medications: List[str] = None) -> Dict:
        """Perform comprehensive safety check"""
        all_medicines = medicines.copy()
        if current_medications:
            all_medicines.extend(current_medications)
        
        allergy_alerts = self.check_allergies(medicines, patient_allergies)
        drug_alerts = self.check_drug_interactions(all_medicines)
        food_alerts = self.check_food_interactions(medicines)
        
        all_alerts = allergy_alerts + drug_alerts + food_alerts
        
        # Determine if action is required
        critical_count = sum(1 for a in all_alerts if a['severity'] == 'critical')
        high_count = sum(1 for a in all_alerts if a['severity'] == 'high')
        
        return {
            'alerts': all_alerts,
            'summary': {
                'total_alerts': len(all_alerts),
                'critical': critical_count,
                'high': high_count,
                'medium': sum(1 for a in all_alerts if a['severity'] == 'medium'),
                'low': sum(1 for a in all_alerts if a['severity'] == 'low')
            },
            'requires_action': critical_count > 0 or high_count > 0,
            'can_proceed': critical_count == 0
        }