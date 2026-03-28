#!/usr/bin/env python3
"""
Database Migration Script
Location: smart_hospital/migrate_database.py (same level as run.py)

Run this after adding new models to create/update tables.
Usage: python migrate_database.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate():
    """Create all new tables and add default data"""
    from app import create_app, db
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Starting database migration...")
        print("-" * 50)
        
        # Import all models to ensure they're registered
        try:
            from app.models.user import User, DoctorAvailability
            from app.models.patient import Patient, PatientAllergy, PatientCondition
            from app.models.prescription import Prescription, PrescriptionMedicine
            from app.models.report import Report
            from app.models.inventory import Inventory, InventoryTransaction
            from app.models.alert import SafetyAlert
            from app.models.reminder import ReminderSetting, ReminderLog
        except ImportError as e:
            print(f"⚠️ Warning importing base models: {e}")
        
        # Import new models
        try:
            from app.models.appointment import Appointment, TimeSlot
            print("   ✓ Appointment models loaded")
        except ImportError as e:
            print(f"   ⚠️ Appointment models: {e}")
        
        try:
            from app.models.video_consultation import VideoSession
            print("   ✓ VideoSession model loaded")
        except ImportError as e:
            print(f"   ⚠️ VideoSession model: {e}")
        
        try:
            from app.models.feedback import Feedback
            print("   ✓ Feedback model loaded")
        except ImportError as e:
            print(f"   ⚠️ Feedback model: {e}")
        
        try:
            from app.models.insurance import InsuranceProvider, PatientInsurance, InsuranceClaim
            print("   ✓ Insurance models loaded")
        except ImportError as e:
            print(f"   ⚠️ Insurance models: {e}")
        
        try:
            from app.models.referral import DoctorReferral
            print("   ✓ Referral model loaded")
        except ImportError as e:
            print(f"   ⚠️ Referral model: {e}")
        
        try:
            from app.models.pharmacy import PharmacyBill, PharmacyBillItem
            print("   ✓ Pharmacy models loaded")
        except ImportError as e:
            print(f"   ⚠️ Pharmacy models: {e}")
        
        try:
            from app.models.chat_log import ChatLog, ChatbotFAQ
            print("   ✓ Chatbot models loaded")
        except ImportError as e:
            print(f"   ⚠️ Chatbot models: {e}")
        
        try:
            from app.models.bill import Bill, BillItem
            print("   ✓ Bill models loaded")
        except ImportError as e:
            print(f"   ⚠️ Bill models: {e}")
        
        print("-" * 50)
        
        # Create all tables
        try:
            db.create_all()
            print("✅ All tables created!")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return
        
        # Add default data
        try:
            add_default_data(db)
        except Exception as e:
            print(f"⚠️ Error adding default data: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 50)
        print("✅ Migration completed successfully!")
        print("\nYou can now run: python run.py")


def add_default_data(db):
    """Add default/seed data"""
    print("\n📋 Adding default data...")
    
    # Add default insurance providers
    try:
        from app.models.insurance import InsuranceProvider
        
        if InsuranceProvider.query.count() == 0:
            providers = [
                InsuranceProvider(name="Medicare", code="MEDICARE", 
                                contact_phone="1-800-MEDICARE", is_active=True),
                InsuranceProvider(name="Blue Cross Blue Shield", code="BCBS", 
                                contact_phone="1-800-123-4567", is_active=True),
                InsuranceProvider(name="Aetna", code="AETNA", 
                                contact_phone="1-800-872-3862", is_active=True),
                InsuranceProvider(name="United Healthcare", code="UHC", 
                                contact_phone="1-800-328-5979", is_active=True),
                InsuranceProvider(name="Cigna", code="CIGNA", 
                                contact_phone="1-800-997-1654", is_active=True),
                InsuranceProvider(name="Star Health", code="STAR", 
                                contact_phone="1800-425-2255", is_active=True),
            ]
            
            for provider in providers:
                db.session.add(provider)
            db.session.commit()
            print("   ✅ Added insurance providers")
        else:
            print("   ℹ️ Insurance providers already exist")
    except Exception as e:
        print(f"   ⚠️ Could not add insurance providers: {e}")
    
    # Add default chatbot FAQs
    try:
        from app.models.chat_log import ChatbotFAQ
        
        if ChatbotFAQ.query.count() == 0:
            faqs = [
                ChatbotFAQ(
                    question="What are the hospital visiting hours?",
                    answer="Our visiting hours are from 10:00 AM to 8:00 PM daily.",
                    category="general",
                    keywords="visiting,hours,visit,time"
                ),
                ChatbotFAQ(
                    question="How do I book an appointment?",
                    answer="You can book through our website, mobile app, or by calling +1-234-567-8900.",
                    category="appointment",
                    keywords="book,appointment,schedule"
                ),
                ChatbotFAQ(
                    question="What insurance do you accept?",
                    answer="We accept most major insurance providers including Medicare, BCBS, Aetna, UHC, and Cigna.",
                    category="insurance",
                    keywords="insurance,accept,coverage"
                ),
                ChatbotFAQ(
                    question="Where is the hospital located?",
                    answer="We are at 123 Medical Center Drive, Healthcare City.",
                    category="general",
                    keywords="location,address,where,directions"
                ),
                ChatbotFAQ(
                    question="Do you offer video consultations?",
                    answer="Yes! Many of our doctors offer video consultations.",
                    category="appointment",
                    keywords="video,online,telemedicine,virtual"
                ),
            ]
            
            for faq in faqs:
                db.session.add(faq)
            db.session.commit()
            print("   ✅ Added chatbot FAQs")
        else:
            print("   ℹ️ Chatbot FAQs already exist")
    except Exception as e:
        print(f"   ⚠️ Could not add chatbot FAQs: {e}")
    
    # Create pharmacist user if not exists
    try:
        from app.models.user import User
        
        # Create admin if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@hospital.com',
                full_name='System Administrator',
                role='admin',
                is_active=True
            )
            admin.set_password('######')
            db.session.add(admin)
            print("   ✅ Admin user created")
            print("      Username: admin | Password: ####")
        
        # Create doctor if not exists
        doctor = User.query.filter_by(username='doctor').first()
        if not doctor:
            doctor = User(
                username='doctor',
                email='doctor@hospital.com',
                full_name='Dr. John Smith',
                role='doctor',
                department='Cardiology',
                specialization='Cardiologist',
                is_active=True
            )
            doctor.set_password('######')
            db.session.add(doctor)
            print("   ✅ Doctor user created")
            print("      Username: doctor | Password: ##########")
        
        # Create patient if not exists
        patient_user = User.query.filter_by(username='patient').first()
        if not patient_user:
            patient_user = User(
                username='patient',
                email='patient@hospital.com',
                full_name='Jane Doe',
                role='patient',
                is_active=True
            )
            patient_user.set_password('######')
            db.session.add(patient_user)
            print("   ✅ Patient user created")
            print("      Username: patient | Password: #########")
        
        # Create pharmacist if not exists
        pharmacist = User.query.filter_by(username='pharmacist').first()
        if not pharmacist:
            pharmacist = User(
                username='pharmacist',
                email='pharmacist@hospital.com',
                full_name='Pharmacy Admin',
                role='pharmacist',
                is_active=True
            )
            pharmacist.set_password('#########')
            db.session.add(pharmacist)
            print("   ✅ Pharmacist user created")
            print("      Username: pharmacist | Password: ########3")
        
        db.session.commit()
        
    except Exception as e:
        print(f"   ⚠️ Could not create default users: {e}")
        import traceback
        traceback.print_exc()



def rollback():
    """Rollback - drop all tables (DANGEROUS!)"""
    confirm = input("⚠️ This will DELETE ALL DATA. Type 'DELETE' to confirm: ")
    if confirm == 'DELETE':
        from app import create_app, db
        app = create_app()
        with app.app_context():
            db.drop_all()
            print("All tables dropped!")
    else:
        print("Cancelled.")


def reset_db():
    """Reset database - drop and recreate all tables"""
    confirm = input("⚠️ This will DELETE ALL DATA and recreate tables. Type 'RESET' to confirm: ")
    if confirm == 'RESET':
        from app import create_app, db
        app = create_app()
        with app.app_context():
            print("Dropping all tables...")
            db.drop_all()
            print("Creating all tables...")
            db.create_all()
            print("Adding default data...")
            add_default_data(db)
            print("✅ Database reset complete!")
    else:
        print("Cancelled.")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--rollback':
            rollback()
        elif sys.argv[1] == '--reset':
            reset_db()
        elif sys.argv[1] == '--help':
            print("Usage: python migrate_database.py [option]")
            print("Options:")
            print("  (none)      - Create new tables and add default data")
            print("  --reset     - Drop all tables and recreate (DELETES ALL DATA)")
            print("  --rollback  - Drop all tables (DELETES ALL DATA)")
            print("  --help      - Show this help message")
    else:
        migrate()
