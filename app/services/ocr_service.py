"""
OCR Service - Extract text from images and PDFs
"""

import os
import re
from typing import Dict, List, Optional, Tuple

class OCRService:
    """Service for OCR processing of prescriptions and reports"""
    
    def __init__(self):
        self.reader = None
        self._initialize_ocr()
    
    def _initialize_ocr(self):
        """Initialize EasyOCR reader"""
        try:
            import easyocr
            self.reader = easyocr.Reader(['en'], gpu=False)
        except Exception as e:
            print(f"Warning: Could not initialize EasyOCR: {e}")
            self.reader = None
    
    def extract_from_image(self, image_path: str) -> str:
        """Extract text from an image file"""
        if self.reader is None:
            return self._fallback_extraction(image_path)
        
        try:
            results = self.reader.readtext(image_path)
            text = ' '.join([result[1] for result in results])
            return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def extract_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file"""
        try:
            import PyPDF2
            
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            print(f"PDF Extraction Error: {e}")
            return ""
    
    def _fallback_extraction(self, image_path: str) -> str:
        """Fallback text extraction when OCR is not available"""
        # Return sample text for demonstration
        return "Sample extracted text - OCR not available"
    
    def parse_prescription(self, text: str) -> Dict:
        """Parse extracted text to identify prescription components"""
        result = {
            'medicines': [],
            'diagnosis': '',
            'instructions': '',
            'raw_text': text
        }
        
        # Common medicine patterns
        medicine_patterns = [
            r'(\w+)\s*(\d+\s*mg|\d+\s*ml)',
            r'Tab\.?\s*(\w+)',
            r'Cap\.?\s*(\w+)',
            r'Syrup\.?\s*(\w+)'
        ]
        
        # Common dosage patterns
        dosage_patterns = [
            r'(\d+)\s*times?\s*(?:a\s*)?day',
            r'(once|twice|thrice)\s*daily',
            r'(\d+)\s*-\s*(\d+)\s*-\s*(\d+)',  # Morning-Afternoon-Night
            r'morning|evening|night|before\s*meal|after\s*meal'
        ]
        
        # Duration patterns
        duration_patterns = [
            r'for\s*(\d+)\s*days?',
            r'(\d+)\s*weeks?',
            r'(\d+)\s*months?'
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to identify medicines
            for pattern in medicine_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    medicine = {
                        'name': matches[0] if isinstance(matches[0], str) else matches[0][0],
                        'dosage': '',
                        'frequency': '',
                        'duration': ''
                    }
                    
                    # Extract dosage
                    for dp in dosage_patterns:
                        dm = re.search(dp, line, re.IGNORECASE)
                        if dm:
                            medicine['frequency'] = dm.group()
                            break
                    
                    # Extract duration
                    for drp in duration_patterns:
                        drm = re.search(drp, line, re.IGNORECASE)
                        if drm:
                            medicine['duration'] = drm.group()
                            break
                    
                    result['medicines'].append(medicine)
        
        return result
    
    def extract_medical_values(self, text: str) -> List[Dict]:
        """Extract medical test values from report text"""
        values = []
        
        # Common medical test patterns
        patterns = {
            'Hemoglobin': r'(?:Hemoglobin|Hb|HGB)\s*[:\-]?\s*(\d+\.?\d*)\s*(g/dL|g%)?',
            'Blood Glucose': r'(?:Blood\s*Glucose|Glucose|Sugar)\s*[:\-]?\s*(\d+\.?\d*)\s*(mg/dL)?',
            'Blood Pressure': r'(?:BP|Blood\s*Pressure)\s*[:\-]?\s*(\d+)/(\d+)',
            'Cholesterol': r'(?:Cholesterol|Total\s*Cholesterol)\s*[:\-]?\s*(\d+\.?\d*)',
            'Creatinine': r'(?:Creatinine|Creat)\s*[:\-]?\s*(\d+\.?\d*)',
            'WBC': r'(?:WBC|White\s*Blood\s*Cell)\s*[:\-]?\s*(\d+\.?\d*)',
            'RBC': r'(?:RBC|Red\s*Blood\s*Cell)\s*[:\-]?\s*(\d+\.?\d*)',
            'Platelets': r'(?:Platelets|PLT)\s*[:\-]?\s*(\d+)',
        }
        
        for test_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                values.append({
                    'test_name': test_name,
                    'value': match.group(1),
                    'unit': match.group(2) if len(match.groups()) > 1 else ''
                })
        
        return values