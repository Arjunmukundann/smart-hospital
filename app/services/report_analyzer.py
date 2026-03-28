"""
Report Analyzer Service - AI-powered medical report analysis
Enhanced version with better parsing and analysis
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ReportAnalyzer:
    """Service for analyzing medical reports"""
    
    # Comprehensive normal ranges for common tests
    NORMAL_RANGES = {
        # Complete Blood Count (CBC)
        'hemoglobin': {
            'male': (13.0, 17.0),
            'female': (12.0, 15.5),
            'unit': 'g/dL',
            'aliases': ['hb', 'hgb', 'haemoglobin']
        },
        'wbc': {
            'all': (4000, 11000),
            'unit': '/µL',
            'aliases': ['white blood cell', 'white blood cells', 'leucocyte', 'leukocyte', 'total wbc', 'twbc']
        },
        'rbc': {
            'male': (4.5, 5.5),
            'female': (4.0, 5.0),
            'unit': 'million/µL',
            'aliases': ['red blood cell', 'red blood cells', 'erythrocyte', 'total rbc']
        },
        'platelets': {
            'all': (150000, 400000),
            'unit': '/µL',
            'aliases': ['platelet count', 'plt', 'thrombocyte']
        },
        'pcv': {
            'male': (40, 50),
            'female': (36, 44),
            'unit': '%',
            'aliases': ['hematocrit', 'hct', 'packed cell volume']
        },
        'mcv': {
            'all': (80, 100),
            'unit': 'fL',
            'aliases': ['mean corpuscular volume']
        },
        'mch': {
            'all': (27, 32),
            'unit': 'pg',
            'aliases': ['mean corpuscular hemoglobin']
        },
        'mchc': {
            'all': (32, 36),
            'unit': 'g/dL',
            'aliases': ['mean corpuscular hemoglobin concentration']
        },
        
        # Blood Sugar / Diabetes
        'fasting glucose': {
            'all': (70, 100),
            'unit': 'mg/dL',
            'aliases': ['fasting blood sugar', 'fbs', 'fasting plasma glucose', 'fpg', 'glucose fasting']
        },
        'post prandial glucose': {
            'all': (70, 140),
            'unit': 'mg/dL',
            'aliases': ['pp glucose', 'ppbs', 'post meal glucose', 'glucose pp', '2 hour glucose']
        },
        'random glucose': {
            'all': (70, 140),
            'unit': 'mg/dL',
            'aliases': ['random blood sugar', 'rbs', 'blood sugar random']
        },
        'hba1c': {
            'all': (4.0, 5.6),
            'unit': '%',
            'aliases': ['glycated hemoglobin', 'glycosylated hemoglobin', 'a1c', 'hemoglobin a1c']
        },
        
        # Lipid Profile
        'total cholesterol': {
            'all': (0, 200),
            'unit': 'mg/dL',
            'aliases': ['cholesterol total', 'cholesterol', 'serum cholesterol', 't cholesterol', 'tc']
        },
        'ldl': {
            'all': (0, 100),
            'unit': 'mg/dL',
            'aliases': ['ldl cholesterol', 'ldl-c', 'low density lipoprotein', 'bad cholesterol']
        },
        'hdl': {
            'male': (40, 60),
            'female': (50, 60),
            'unit': 'mg/dL',
            'aliases': ['hdl cholesterol', 'hdl-c', 'high density lipoprotein', 'good cholesterol']
        },
        'vldl': {
            'all': (5, 40),
            'unit': 'mg/dL',
            'aliases': ['vldl cholesterol', 'very low density lipoprotein']
        },
        'triglycerides': {
            'all': (0, 150),
            'unit': 'mg/dL',
            'aliases': ['tg', 'triglyceride', 'trigs']
        },
        
        # Kidney Function (KFT/RFT)
        'creatinine': {
            'male': (0.7, 1.3),
            'female': (0.6, 1.1),
            'unit': 'mg/dL',
            'aliases': ['serum creatinine', 's creatinine', 'creat']
        },
        'urea': {
            'all': (15, 40),
            'unit': 'mg/dL',
            'aliases': ['blood urea', 'serum urea', 'bun']
        },
        'bun': {
            'all': (7, 20),
            'unit': 'mg/dL',
            'aliases': ['blood urea nitrogen']
        },
        'uric acid': {
            'male': (3.5, 7.2),
            'female': (2.5, 6.0),
            'unit': 'mg/dL',
            'aliases': ['serum uric acid', 's uric acid']
        },
        
        # Liver Function (LFT)
        'sgpt': {
            'all': (7, 56),
            'unit': 'U/L',
            'aliases': ['alt', 'alanine transaminase', 'alanine aminotransferase', 'serum glutamic pyruvic transaminase']
        },
        'sgot': {
            'all': (10, 40),
            'unit': 'U/L',
            'aliases': ['ast', 'aspartate transaminase', 'aspartate aminotransferase', 'serum glutamic oxaloacetic transaminase']
        },
        'alp': {
            'all': (44, 147),
            'unit': 'U/L',
            'aliases': ['alkaline phosphatase', 'alk phos', 'alkp']
        },
        'ggt': {
            'all': (9, 48),
            'unit': 'U/L',
            'aliases': ['gamma gt', 'gamma glutamyl transferase', 'ggtp']
        },
        'bilirubin total': {
            'all': (0.1, 1.2),
            'unit': 'mg/dL',
            'aliases': ['total bilirubin', 't bilirubin', 'serum bilirubin', 'tbil']
        },
        'bilirubin direct': {
            'all': (0.0, 0.3),
            'unit': 'mg/dL',
            'aliases': ['direct bilirubin', 'd bilirubin', 'conjugated bilirubin', 'dbil']
        },
        'bilirubin indirect': {
            'all': (0.1, 1.0),
            'unit': 'mg/dL',
            'aliases': ['indirect bilirubin', 'unconjugated bilirubin']
        },
        'albumin': {
            'all': (3.5, 5.0),
            'unit': 'g/dL',
            'aliases': ['serum albumin', 's albumin', 'alb']
        },
        'globulin': {
            'all': (2.0, 3.5),
            'unit': 'g/dL',
            'aliases': ['serum globulin', 's globulin']
        },
        'total protein': {
            'all': (6.0, 8.3),
            'unit': 'g/dL',
            'aliases': ['serum protein', 'protein total', 'tp']
        },
        
        # Thyroid Function (TFT)
        'tsh': {
            'all': (0.4, 4.0),
            'unit': 'mIU/L',
            'aliases': ['thyroid stimulating hormone', 'thyrotropin', 's tsh', 'serum tsh']
        },
        't3': {
            'all': (80, 200),
            'unit': 'ng/dL',
            'aliases': ['total t3', 'triiodothyronine', 'serum t3']
        },
        't4': {
            'all': (5.0, 12.0),
            'unit': 'µg/dL',
            'aliases': ['total t4', 'thyroxine', 'serum t4']
        },
        'free t3': {
            'all': (2.3, 4.2),
            'unit': 'pg/mL',
            'aliases': ['ft3', 'free triiodothyronine']
        },
        'free t4': {
            'all': (0.8, 1.8),
            'unit': 'ng/dL',
            'aliases': ['ft4', 'free thyroxine']
        },
        
        # Vitamins & Minerals
        'vitamin d': {
            'all': (30, 100),
            'unit': 'ng/mL',
            'aliases': ['vit d', '25-oh vitamin d', '25 hydroxy vitamin d', 'vitamin d3', 'cholecalciferol']
        },
        'vitamin b12': {
            'all': (200, 900),
            'unit': 'pg/mL',
            'aliases': ['vit b12', 'cobalamin', 'cyanocobalamin', 'serum b12']
        },
        'folate': {
            'all': (3, 17),
            'unit': 'ng/mL',
            'aliases': ['folic acid', 'serum folate', 'vitamin b9']
        },
        'iron': {
            'male': (60, 170),
            'female': (37, 145),
            'unit': 'µg/dL',
            'aliases': ['serum iron', 's iron', 'fe']
        },
        'ferritin': {
            'male': (30, 400),
            'female': (15, 150),
            'unit': 'ng/mL',
            'aliases': ['serum ferritin', 's ferritin']
        },
        'tibc': {
            'all': (250, 370),
            'unit': 'µg/dL',
            'aliases': ['total iron binding capacity']
        },
        'calcium': {
            'all': (8.6, 10.3),
            'unit': 'mg/dL',
            'aliases': ['serum calcium', 's calcium', 'ca']
        },
        
        # Electrolytes
        'sodium': {
            'all': (136, 145),
            'unit': 'mEq/L',
            'aliases': ['serum sodium', 's sodium', 'na']
        },
        'potassium': {
            'all': (3.5, 5.0),
            'unit': 'mEq/L',
            'aliases': ['serum potassium', 's potassium', 'k']
        },
        'chloride': {
            'all': (98, 106),
            'unit': 'mEq/L',
            'aliases': ['serum chloride', 's chloride', 'cl']
        },
        
        # Cardiac Markers
        'troponin': {
            'all': (0, 0.04),
            'unit': 'ng/mL',
            'aliases': ['troponin i', 'troponin t', 'cardiac troponin', 'trop']
        },
        'ck-mb': {
            'all': (0, 25),
            'unit': 'U/L',
            'aliases': ['creatine kinase mb', 'cpk-mb']
        },
        'bnp': {
            'all': (0, 100),
            'unit': 'pg/mL',
            'aliases': ['b-type natriuretic peptide', 'brain natriuretic peptide']
        },
        
        # Inflammatory Markers
        'crp': {
            'all': (0, 10),
            'unit': 'mg/L',
            'aliases': ['c-reactive protein', 'c reactive protein', 'hs-crp']
        },
        'esr': {
            'male': (0, 15),
            'female': (0, 20),
            'unit': 'mm/hr',
            'aliases': ['erythrocyte sedimentation rate', 'sed rate']
        },
    }
    
    # Medical term simplification
    MEDICAL_TERMS = {
        'hypertension': 'High Blood Pressure',
        'hypotension': 'Low Blood Pressure',
        'hyperglycemia': 'High Blood Sugar',
        'hypoglycemia': 'Low Blood Sugar',
        'hyperlipidemia': 'High Cholesterol',
        'hypothyroidism': 'Underactive Thyroid (TSH is HIGH, T3/T4 are LOW)',
        'hyperthyroidism': 'Overactive Thyroid (TSH is LOW, T3/T4 are HIGH)',
        'anemia': 'Low Red Blood Cells/Hemoglobin',
        'polycythemia': 'High Red Blood Cell Count',
        'leukocytosis': 'High White Blood Cell Count (possible infection)',
        'leukopenia': 'Low White Blood Cell Count',
        'thrombocytopenia': 'Low Platelet Count (bleeding risk)',
        'thrombocytosis': 'High Platelet Count',
        'azotemia': 'High Urea/Creatinine (kidney issue)',
        'hyperuricemia': 'High Uric Acid (gout risk)',
        'hyperbilirubinemia': 'High Bilirubin (jaundice)',
        'hypoalbuminemia': 'Low Albumin (liver/nutrition issue)',
        'hyperkalemia': 'High Potassium (dangerous for heart)',
        'hypokalemia': 'Low Potassium',
        'hypernatremia': 'High Sodium',
        'hyponatremia': 'Low Sodium',
        'hypercalcemia': 'High Calcium',
        'hypocalcemia': 'Low Calcium',
    }
    
    # Condition patterns based on multiple values
    CONDITION_PATTERNS = {
        'diabetes': {
            'indicators': [
                ('fasting glucose', '>', 126),
                ('hba1c', '>', 6.5),
                ('random glucose', '>', 200),
            ],
            'message': 'Values indicate possible Diabetes Mellitus. Recommend further evaluation.'
        },
        'prediabetes': {
            'indicators': [
                ('fasting glucose', 'between', 100, 125),
                ('hba1c', 'between', 5.7, 6.4),
            ],
            'message': 'Values indicate Prediabetes. Lifestyle modifications recommended.'
        },
        'hypothyroidism': {
            'indicators': [
                ('tsh', '>', 4.5),
            ],
            'message': 'Elevated TSH suggests Hypothyroidism (underactive thyroid).'
        },
        'hyperthyroidism': {
            'indicators': [
                ('tsh', '<', 0.4),
            ],
            'message': 'Low TSH suggests Hyperthyroidism (overactive thyroid).'
        },
        'anemia': {
            'indicators': [
                ('hemoglobin', '<', 12),
            ],
            'message': 'Low hemoglobin indicates Anemia. Check iron, B12, and folate levels.'
        },
        'kidney_disease': {
            'indicators': [
                ('creatinine', '>', 1.5),
                ('urea', '>', 50),
            ],
            'message': 'Elevated kidney markers. Recommend nephrology consultation.'
        },
        'liver_disease': {
            'indicators': [
                ('sgpt', '>', 100),
                ('sgot', '>', 100),
            ],
            'message': 'Elevated liver enzymes. Recommend hepatology evaluation.'
        },
        'dyslipidemia': {
            'indicators': [
                ('total cholesterol', '>', 240),
                ('ldl', '>', 160),
                ('triglycerides', '>', 200),
            ],
            'message': 'Abnormal lipid profile. Cardiovascular risk assessment recommended.'
        },
        'vitamin_d_deficiency': {
            'indicators': [
                ('vitamin d', '<', 20),
            ],
            'message': 'Vitamin D deficiency. Supplementation recommended.'
        },
    }
    
    def __init__(self):
        """Initialize the analyzer"""
        pass
    
    def analyze_report(self, extracted_text: str, report_type: str = 'general',
                       gender: str = 'male') -> Dict:
        """
        Main method to analyze a medical report
        
        Args:
            extracted_text: Text extracted from report (via OCR)
            report_type: Type of report (blood_test, thyroid, etc.)
            gender: Patient's gender for gender-specific ranges
            
        Returns:
            Dictionary with analysis results
        """
        
        # Normalize text
        text = self._normalize_text(extracted_text)
        
        # Extract test values
        extracted_values = self._extract_all_values(text)
        
        # Analyze each value
        key_findings = []
        abnormal_values = []
        concern_areas = []
        recommendations = []
        
        for test_name, value_info in extracted_values.items():
            analysis = self._analyze_single_value(
                test_name, 
                value_info['value'], 
                value_info.get('unit', ''),
                gender
            )
            
            if analysis:
                if analysis['status'] == 'normal':
                    key_findings.append(analysis['finding'])
                else:
                    abnormal_values.append(analysis['finding'])
                    if analysis.get('concern'):
                        concern_areas.append(analysis['concern'])
                    if analysis.get('recommendation'):
                        recommendations.append(analysis['recommendation'])
        
        # Check for condition patterns
        condition_findings = self._check_condition_patterns(extracted_values)
        concern_areas.extend(condition_findings)
        
        # Generate summary
        summary = self._generate_summary(
            report_type, 
            key_findings, 
            abnormal_values, 
            concern_areas
        )
        
        return {
            'summary': summary,
            'key_findings': key_findings,
            'abnormal_values': abnormal_values,
            'concern_areas': concern_areas,
            'recommendations': recommendations,
            'extracted_values': extracted_values,
            'raw_text': extracted_text[:1000]  # First 1000 chars for debugging
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better parsing"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace common OCR errors
        text = text.replace('|', 'l')
        text = text.replace('0', 'o').replace('o', '0')  # Context-dependent, simplified
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize units
        text = text.replace('μl', 'µl')
        text = text.replace('ul', 'µl')
        text = text.replace('/cumm', '/µl')
        text = text.replace('/cmm', '/µl')
        text = text.replace('mill/cumm', 'million/µl')
        
        return text
    
    def _extract_all_values(self, text: str) -> Dict:
        """Extract all test values from text"""
        extracted = {}
        
        # For each known test, try to find its value
        for test_name, range_info in self.NORMAL_RANGES.items():
            value = self._find_test_value(text, test_name, range_info.get('aliases', []))
            if value is not None:
                extracted[test_name] = {
                    'value': value,
                    'unit': range_info.get('unit', '')
                }
        
        return extracted
    
    def _find_test_value(self, text: str, test_name: str, aliases: List[str]) -> Optional[float]:
        """Find the value for a specific test"""
        
        # All possible names for this test
        all_names = [test_name] + aliases
        
        for name in all_names:
            # Pattern: test name followed by value
            # Handles: "Hemoglobin : 12.5", "HB - 12.5", "Hb 12.5 g/dl", etc.
            patterns = [
                rf'{re.escape(name)}\s*[:\-=]?\s*(\d+\.?\d*)',
                rf'{re.escape(name)}\s+(\d+\.?\d*)',
                rf'(\d+\.?\d*)\s*[:\-=]?\s*{re.escape(name)}',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        # Basic sanity check
                        if 0 < value < 100000:
                            return value
                    except (ValueError, IndexError):
                        continue
        
        return None
    
    def _analyze_single_value(self, test_name: str, value: float, 
                              unit: str, gender: str) -> Optional[Dict]:
        """Analyze a single test value against normal ranges"""
        
        range_info = self.NORMAL_RANGES.get(test_name)
        if not range_info:
            return None
        
        # Get appropriate range based on gender
        if 'all' in range_info:
            normal_range = range_info['all']
        elif gender.lower() in range_info:
            normal_range = range_info[gender.lower()]
        else:
            normal_range = range_info.get('male', (0, float('inf')))
        
        min_val, max_val = normal_range
        unit_str = range_info.get('unit', unit)
        test_display = test_name.replace('_', ' ').title()
        
        if min_val <= value <= max_val:
            return {
                'status': 'normal',
                'finding': f"✅ {test_display}: {value} {unit_str} (Normal range: {min_val}-{max_val})"
            }
        elif value < min_val:
            severity = 'critical' if value < min_val * 0.7 else 'low'
            concern = self._get_low_value_concern(test_name, value, min_val)
            recommendation = self._get_recommendation(test_name, 'low')
            
            return {
                'status': 'abnormal',
                'finding': f"⬇️ {test_display}: {value} {unit_str} (LOW - Normal: {min_val}-{max_val})",
                'concern': concern,
                'recommendation': recommendation,
                'severity': severity
            }
        else:
            severity = 'critical' if value > max_val * 1.5 else 'high'
            concern = self._get_high_value_concern(test_name, value, max_val)
            recommendation = self._get_recommendation(test_name, 'high')
            
            return {
                'status': 'abnormal',
                'finding': f"⬆️ {test_display}: {value} {unit_str} (HIGH - Normal: {min_val}-{max_val})",
                'concern': concern,
                'recommendation': recommendation,
                'severity': severity
            }
    
    def _get_low_value_concern(self, test_name: str, value: float, min_val: float) -> str:
        """Get concern message for low values"""
        concerns = {
            'hemoglobin': 'Low hemoglobin may indicate anemia. Patient may experience fatigue, weakness, shortness of breath.',
            'wbc': 'Low WBC count may indicate immune system issues or bone marrow problems.',
            'platelets': 'Low platelet count increases bleeding risk. Avoid injuries.',
            'tsh': 'Low TSH with symptoms may indicate hyperthyroidism (overactive thyroid).',
            't3': 'Low T3 may indicate hypothyroidism.',
            't4': 'Low T4 may indicate hypothyroidism.',
            'vitamin d': 'Vitamin D deficiency can affect bone health and immunity.',
            'vitamin b12': 'B12 deficiency can cause anemia and neurological issues.',
            'iron': 'Iron deficiency can cause anemia.',
            'calcium': 'Low calcium can affect bones and muscles.',
            'sodium': 'Low sodium (hyponatremia) can cause confusion, seizures.',
            'potassium': 'Low potassium can cause muscle weakness, cardiac issues.',
            'albumin': 'Low albumin may indicate liver disease or malnutrition.',
            'hdl': 'Low HDL (good cholesterol) increases cardiovascular risk.',
        }
        return concerns.get(test_name, f'Low {test_name.replace("_", " ")} requires medical attention.')
    
    def _get_high_value_concern(self, test_name: str, value: float, max_val: float) -> str:
        """Get concern message for high values"""
        concerns = {
            'hemoglobin': 'High hemoglobin may indicate polycythemia or dehydration.',
            'wbc': 'High WBC count may indicate infection, inflammation, or leukemia.',
            'platelets': 'High platelet count may indicate inflammation or bone marrow disorder.',
            'tsh': 'High TSH indicates hypothyroidism (underactive thyroid). Common symptoms: fatigue, weight gain, cold intolerance.',
            't3': 'High T3 may indicate hyperthyroidism.',
            't4': 'High T4 may indicate hyperthyroidism.',
            'fasting glucose': 'High fasting glucose indicates diabetes or prediabetes.',
            'hba1c': 'High HbA1c indicates poor blood sugar control over past 2-3 months.',
            'total cholesterol': 'High cholesterol increases cardiovascular disease risk.',
            'ldl': 'High LDL (bad cholesterol) increases heart disease and stroke risk.',
            'triglycerides': 'High triglycerides increase cardiovascular risk and can cause pancreatitis.',
            'creatinine': 'High creatinine indicates kidney function impairment.',
            'urea': 'High urea may indicate kidney problems or dehydration.',
            'uric acid': 'High uric acid can cause gout and kidney stones.',
            'sgpt': 'High SGPT/ALT indicates liver cell damage.',
            'sgot': 'High SGOT/AST indicates liver or heart muscle damage.',
            'bilirubin total': 'High bilirubin causes jaundice (yellowing of skin/eyes).',
            'sodium': 'High sodium (hypernatremia) can cause confusion, seizures.',
            'potassium': 'High potassium can cause dangerous heart rhythm problems.',
            'crp': 'High CRP indicates inflammation or infection in the body.',
            'esr': 'High ESR indicates inflammation, infection, or autoimmune disease.',
        }
        return concerns.get(test_name, f'High {test_name.replace("_", " ")} requires medical attention.')
    
    def _get_recommendation(self, test_name: str, direction: str) -> str:
        """Get recommendation for abnormal values"""
        recommendations = {
            ('hemoglobin', 'low'): 'Check iron, B12, and folate levels. Consider iron supplementation if deficient.',
            ('hemoglobin', 'high'): 'Ensure adequate hydration. Rule out polycythemia vera.',
            ('tsh', 'high'): 'Confirm hypothyroidism. May need thyroid hormone replacement therapy (Levothyroxine).',
            ('tsh', 'low'): 'Confirm hyperthyroidism. May need anti-thyroid medications or further evaluation.',
            ('fasting glucose', 'high'): 'Lifestyle modifications, diet control. May need diabetes medication if confirmed.',
            ('hba1c', 'high'): 'Intensive diabetes management. Review diet, exercise, and medications.',
            ('total cholesterol', 'high'): 'Dietary changes, exercise. Consider statin therapy if lifestyle changes insufficient.',
            ('ldl', 'high'): 'Reduce saturated fat intake. Consider statin therapy.',
            ('creatinine', 'high'): 'Nephrology consultation. Ensure adequate hydration. Review nephrotoxic medications.',
            ('sgpt', 'high'): 'Avoid alcohol. Check for viral hepatitis. Review hepatotoxic medications.',
            ('vitamin d', 'low'): 'Vitamin D supplementation (cholecalciferol). Sun exposure recommended.',
            ('vitamin b12', 'low'): 'B12 supplementation (oral or injection depending on cause).',
            ('iron', 'low'): 'Iron supplementation. Check for blood loss sources.',
        }
        
        return recommendations.get((test_name, direction), 
                                  f'Consult doctor for {direction} {test_name.replace("_", " ")}.')
    
    def _check_condition_patterns(self, extracted_values: Dict) -> List[str]:
        """Check for condition patterns based on multiple values"""
        findings = []
        
        for condition, info in self.CONDITION_PATTERNS.items():
            matched = False
            for indicator in info['indicators']:
                test_name = indicator[0]
                operator = indicator[1]
                
                if test_name not in extracted_values:
                    continue
                
                value = extracted_values[test_name]['value']
                
                if operator == '>' and len(indicator) == 3:
                    if value > indicator[2]:
                        matched = True
                        break
                elif operator == '<' and len(indicator) == 3:
                    if value < indicator[2]:
                        matched = True
                        break
                elif operator == 'between' and len(indicator) == 4:
                    if indicator[2] <= value <= indicator[3]:
                        matched = True
                        break
            
            if matched:
                findings.append(f"⚠️ {info['message']}")
        
        return findings
    
    def _generate_summary(self, report_type: str, key_findings: List,
                         abnormal_values: List, concern_areas: List) -> str:
        """Generate human-readable summary"""
        
        report_type_display = report_type.replace('_', ' ').title()
        
        parts = [f"📋 **{report_type_display} Report Analysis**\n"]
        
        total_tests = len(key_findings) + len(abnormal_values)
        
        if total_tests == 0:
            parts.append("⚠️ No test values could be extracted from this report. ")
            parts.append("This may be due to image quality or report format. ")
            parts.append("Please verify the report manually or try re-uploading with better quality.")
        else:
            if abnormal_values:
                parts.append(f"🔴 **{len(abnormal_values)} ABNORMAL** value(s) found out of {total_tests} tests analyzed.\n\n")
            else:
                parts.append(f"✅ All {total_tests} test values are within **NORMAL** ranges.\n\n")
            
            if abnormal_values:
                parts.append("**Abnormal Values:**\n")
                for av in abnormal_values:
                    parts.append(f"• {av}\n")
                parts.append("\n")
            
            if concern_areas:
                parts.append("**Areas of Concern:**\n")
                for ca in concern_areas:
                    parts.append(f"• {ca}\n")
                parts.append("\n")
            
            if key_findings:
                parts.append(f"**Normal Values ({len(key_findings)}):**\n")
                for kf in key_findings[:5]:  # Show first 5
                    parts.append(f"• {kf}\n")
                if len(key_findings) > 5:
                    parts.append(f"• ... and {len(key_findings) - 5} more normal values\n")
        
        return ''.join(parts)
    
    def simplify_medical_terms(self, text: str) -> str:
        """Replace medical jargon with simple explanations"""
        simplified = text
        
        for term, explanation in self.MEDICAL_TERMS.items():
            # Case-insensitive replacement with explanation
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            simplified = pattern.sub(f"{term} ({explanation})", simplified)
        
        return simplified
    
    def analyze_manual_input(self, values: Dict[str, float], gender: str = 'male') -> Dict:
        """
        Analyze manually entered test values
        Useful when OCR doesn't work well
        
        Args:
            values: Dictionary of test_name: value pairs
            gender: Patient's gender
            
        Returns:
            Analysis results
        """
        key_findings = []
        abnormal_values = []
        concern_areas = []
        recommendations = []
        
        for test_name, value in values.items():
            # Normalize test name
            test_name_normalized = test_name.lower().strip().replace(' ', '_')
            
            # Find matching test
            matched_test = None
            for known_test, range_info in self.NORMAL_RANGES.items():
                all_names = [known_test] + range_info.get('aliases', [])
                if test_name_normalized in [n.lower().replace(' ', '_') for n in all_names]:
                    matched_test = known_test
                    break
            
            if matched_test:
                analysis = self._analyze_single_value(
                    matched_test, value, 
                    self.NORMAL_RANGES[matched_test].get('unit', ''),
                    gender
                )
                
                if analysis:
                    if analysis['status'] == 'normal':
                        key_findings.append(analysis['finding'])
                    else:
                        abnormal_values.append(analysis['finding'])
                        if analysis.get('concern'):
                            concern_areas.append(analysis['concern'])
                        if analysis.get('recommendation'):
                            recommendations.append(analysis['recommendation'])
        
        # Check patterns
        extracted_values = {
            k: {'value': v} for k, v in values.items()
        }
        condition_findings = self._check_condition_patterns(extracted_values)
        concern_areas.extend(condition_findings)
        
        summary = self._generate_summary('manual_input', key_findings, abnormal_values, concern_areas)
        
        return {
            'summary': summary,
            'key_findings': key_findings,
            'abnormal_values': abnormal_values,
            'concern_areas': concern_areas,
            'recommendations': recommendations
        }