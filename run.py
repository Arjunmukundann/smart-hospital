#!/usr/bin/env python3
"""
Smart Hospital Platform - Main Entry Point
"""

from app import create_app, db
from app.extensions import socketio
from app.models import (
    User, Patient, Prescription, PrescriptionMedicine, Report, 
    Inventory, SafetyAlert, ReminderSetting, ReminderLog,
    Appointment, TimeSlot, VideoSession, Feedback,
    InsuranceProvider, PatientInsurance, InsuranceClaim,
    DoctorReferral, PharmacyBill, PharmacyBillItem,
    ChatLog, ChatbotFAQ, DoctorAvailability
)

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Make database models available in flask shell"""
    return {
        'db': db,
        'User': User,
        'Patient': Patient,
        'Prescription': Prescription,
        'PrescriptionMedicine': PrescriptionMedicine,
        'Report': Report,
        'Inventory': Inventory,
        'SafetyAlert': SafetyAlert,
        'ReminderSetting': ReminderSetting,
        'ReminderLog': ReminderLog,
        'Appointment': Appointment,
        'TimeSlot': TimeSlot,
        'VideoSession': VideoSession,
        'Feedback': Feedback,
        'InsuranceProvider': InsuranceProvider,
        'PatientInsurance': PatientInsurance,
        'InsuranceClaim': InsuranceClaim,
        'DoctorReferral': DoctorReferral,
        'PharmacyBill': PharmacyBill,
        'PharmacyBillItem': PharmacyBillItem,
        'ChatLog': ChatLog,
        'ChatbotFAQ': ChatbotFAQ,
        'DoctorAvailability': DoctorAvailability
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")
    
    # Initialize scheduler for reminders
    if app.config.get('REMINDER_ENABLED', True):
        try:
            from app.services.scheduler import init_scheduler
            init_scheduler(app)
        except Exception as e:
            print(f"⚠️ Scheduler initialization failed: {e}")
    
    print("\n" + "="*60)
    print("🏥 Smart Hospital Platform Starting...")
    print("📍 Access at: http://127.0.0.1:5000")
    print("🔌 WebSocket enabled for video consultations")
    print("="*60 + "\n")
    
    # Use socketio.run instead of app.run for WebSocket support
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)