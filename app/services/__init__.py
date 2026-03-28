"""
Services Package
"""

from app.services.ocr_service import OCRService
from app.services.safety_checker import SafetyChecker
from app.services.report_analyzer import ReportAnalyzer
from app.services.meal_analyzer import MealAnalyzer
from app.services.prediction_service import PredictionService
from app.services.reminder_service import ReminderService

# NEW Services
from app.services.video_service import VideoService
from app.services.signature_service import SignatureService
from app.services.chatbot_service import ChatbotService
from app.services.billing_service import BillingService
from app.services.image_service import ImageService

# PDF Service (optional - requires reportlab)
try:
    from app.services.pdf_service import PDFService
except ImportError:
    PDFService = None

__all__ = [
    'OCRService',
    'SafetyChecker',
    'ReportAnalyzer',
    'MealAnalyzer',
    'PredictionService',
    'ReminderService',
    'VideoService',
    'SignatureService',
    'ChatbotService',
    'BillingService',
    'ImageService',
    'PDFService'
]