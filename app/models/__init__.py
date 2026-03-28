"""
Models Package - Import all models
"""

from app.models.user import User, DoctorAvailability
from app.models.patient import Patient, PatientAllergy, PatientCondition
from app.models.prescription import Prescription, PrescriptionMedicine
from app.models.report import Report
from app.models.inventory import Inventory, InventoryTransaction
from app.models.alert import SafetyAlert
from app.models.reminder import ReminderSetting, ReminderLog

# Check if GlobalReminderSettings exists
try:
    from app.models.reminder import GlobalReminderSettings
except ImportError:
    GlobalReminderSettings = None

# NEW Models
from app.models.appointment import Appointment, TimeSlot
from app.models.video_consultation import VideoSession
from app.models.feedback import Feedback
from app.models.insurance import InsuranceProvider, PatientInsurance, InsuranceClaim
from app.models.referral import DoctorReferral
from app.models.pharmacy import PharmacyBill, PharmacyBillItem
from app.models.chat_log import ChatLog, ChatbotFAQ
from app.models.bill import Bill, BillItem
from app.models.ecg_record import ECGPatient,ECGResult
__all__ = [
    # User & Auth
    'User',
    'DoctorAvailability',
    
    # Patient
    'Patient',
    'PatientAllergy',
    'PatientCondition',
    
    # Prescription
    'Prescription',
    'PrescriptionMedicine',
    
    # Reports
    'Report',
    
    # Inventory
    'Inventory',
    'InventoryTransaction',
    
    # Alerts
    'SafetyAlert',
    
    # Reminders
    'ReminderSetting',
    'ReminderLog',
    'GlobalReminderSettings',
    
    # Appointments
    'Appointment',
    'TimeSlot',
    
    # Video
    'VideoSession',
    
    # Feedback
    'Feedback',
    
    # Insurance
    'InsuranceProvider',
    'PatientInsurance',
    'InsuranceClaim',
    
    # Referral
    'DoctorReferral',
    
    # Pharmacy
    'PharmacyBill',
    'PharmacyBillItem',
    
    # Chatbot
    'ChatLog',
    'ChatbotFAQ',
    
    # General Billing
    'Bill',
    'BillItem'

    'ECGPatient',
    'ECGResult'
]