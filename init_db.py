"""
Initialize Database with Default Data
"""

from datetime import datetime, date
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.patient import Patient, PatientAllergy, PatientCondition

def init_database():
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created!")
        
        # ============ CREATE ADMIN ============
        try:
            if not User.query.filter_by(email='admin@hospital.com').first():
                admin = User()
                admin.username = 'admin'
                admin.email = 'admin@hospital.com'
                admin.full_name = 'System Administrator'
                admin.role = 'admin'
                admin.is_active = True
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ Admin created: admin@hospital.com")
            else:
                print("ℹ️ Admin already exists")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Admin error: {e}")
        
        # ============ CREATE PHARMACIST ============
        try:
            if not User.query.filter_by(email='pharmacist@hospital.com').first():
                pharmacist = User()
                pharmacist.username = 'pharmacist'
                pharmacist.email = 'pharmacist@hospital.com'
                pharmacist.full_name = 'Default Pharmacist'
                pharmacist.role = 'pharmacist'
                pharmacist.phone = '9876543210'
                pharmacist.is_active = True
                pharmacist.set_password('pharmacist123')
                db.session.add(pharmacist)
                db.session.commit()
                print("✅ Pharmacist created: pharmacist@hospital.com")
            else:
                print("ℹ️ Pharmacist already exists")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Pharmacist error: {e}")
        
        # ============ CREATE DOCTOR 1 ============
        try:
            if not User.query.filter_by(email='doctor@hospital.com').first():
                doctor = User()
                doctor.username = 'doctor'
                doctor.email = 'doctor@hospital.com'
                doctor.full_name = 'Dr. John Smith'
                doctor.role = 'doctor'
                doctor.phone = '9876543211'
                doctor.specialization = 'General Medicine'
                doctor.qualification = 'MBBS, MD'
                doctor.experience_years = 10
                doctor.department = 'General'
                doctor.consultation_fee = 500.0
                doctor.video_consultation_fee = 400.0
                doctor.is_available_online = True
                doctor.is_active = True
                doctor.set_password('doctor123')
                db.session.add(doctor)
                db.session.commit()
                print("✅ Doctor created: doctor@hospital.com")
            else:
                print("ℹ️ Doctor already exists")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Doctor error: {e}")
        
        # ============ CREATE DOCTOR 2 ============
        try:
            if not User.query.filter_by(email='doctor2@hospital.com').first():
                doctor2 = User()
                doctor2.username = 'doctor2'
                doctor2.email = 'doctor2@hospital.com'
                doctor2.full_name = 'Dr. Sarah Johnson'
                doctor2.role = 'doctor'
                doctor2.phone = '9876543212'
                doctor2.specialization = 'Cardiology'
                doctor2.qualification = 'MBBS, DM Cardiology'
                doctor2.experience_years = 15
                doctor2.department = 'Cardiology'
                doctor2.consultation_fee = 800.0
                doctor2.video_consultation_fee = 700.0
                doctor2.is_available_online = True
                doctor2.is_active = True
                doctor2.set_password('doctor123')
                db.session.add(doctor2)
                db.session.commit()
                print("✅ Doctor 2 created: doctor2@hospital.com")
            else:
                print("ℹ️ Doctor 2 already exists")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Doctor 2 error: {e}")
        
        # ============ CREATE PATIENT USER 1 ============
        try:
            patient_user = User.query.filter_by(email='patient@hospital.com').first()
            if not patient_user:
                patient_user = User()
                patient_user.username = 'patient'
                patient_user.email = 'patient@hospital.com'
                patient_user.full_name = 'Test Patient'
                patient_user.role = 'patient'
                patient_user.phone = '9876543213'
                patient_user.is_active = True
                patient_user.set_password('patient123')
                db.session.add(patient_user)
                db.session.commit()
                print("✅ Patient user created: patient@hospital.com")
            else:
                print("ℹ️ Patient user already exists")
            
            # Create Patient Profile
            if patient_user and not Patient.query.filter_by(user_id=patient_user.id).first():
                patient_id = Patient.generate_patient_id()
                
                # Create patient with ONLY actual column fields (NOT relationships!)
                patient = Patient()
                patient.user_id = patient_user.id
                patient.patient_id = patient_id
                patient.full_name = 'Test Patient'
                patient.age = 30
                patient.gender = 'Male'
                patient.blood_group = 'O+'
                patient.phone = '9876543213'
                patient.email = 'patient@hospital.com'
                patient.address = '123 Main Street'
                patient.city = 'Mumbai'
                patient.state = 'Maharashtra'
                patient.pincode = '400001'
                patient.emergency_contact_name = 'Emergency Contact'
                patient.emergency_contact_phone = '9876543214'
                patient.emergency_contact_relation = 'Spouse'
                patient.smoking_status = 'never'
                patient.alcohol_consumption = 'never'
                patient.food_preference = 'vegetarian'
                patient.exercise_frequency = 'regular'
                patient.current_medications = ''
                patient.past_surgeries = ''
                patient.family_history = ''
                patient.notes = ''
                patient.survey_completed = True
                
                db.session.add(patient)
                db.session.commit()
                print(f"✅ Patient profile created: {patient_id}")
                
                # Add sample allergy (using the relationship properly)
                allergy = PatientAllergy()
                allergy.patient_id = patient.id
                allergy.allergy_name = 'Penicillin'
                allergy.severity = 'high'
                allergy.notes = 'Causes rash'
                db.session.add(allergy)
                db.session.commit()
                print("✅ Sample allergy added")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Patient error: {e}")
            import traceback
            traceback.print_exc()
        
        # ============ CREATE PATIENT USER 2 ============
        try:
            patient_user2 = User.query.filter_by(email='patient2@hospital.com').first()
            if not patient_user2:
                patient_user2 = User()
                patient_user2.username = 'patient2'
                patient_user2.email = 'patient2@hospital.com'
                patient_user2.full_name = 'Jane Doe'
                patient_user2.role = 'patient'
                patient_user2.phone = '9876543215'
                patient_user2.is_active = True
                patient_user2.set_password('patient123')
                db.session.add(patient_user2)
                db.session.commit()
                print("✅ Patient 2 user created: patient2@hospital.com")
            
            # Create Patient Profile 2
            if patient_user2 and not Patient.query.filter_by(user_id=patient_user2.id).first():
                patient_id2 = Patient.generate_patient_id()
                
                patient2 = Patient()
                patient2.user_id = patient_user2.id
                patient2.patient_id = patient_id2
                patient2.full_name = 'Jane Doe'
                patient2.age = 25
                patient2.gender = 'Female'
                patient2.blood_group = 'A+'
                patient2.phone = '9876543215'
                patient2.email = 'patient2@hospital.com'
                patient2.address = '456 Second Street'
                patient2.city = 'Delhi'
                patient2.state = 'Delhi'
                patient2.pincode = '110001'
                patient2.survey_completed = True
                
                db.session.add(patient2)
                db.session.commit()
                print(f"✅ Patient 2 profile created: {patient_id2}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Patient 2 error: {e}")
        
        # ============ PRINT SUMMARY ============
        print("\n" + "=" * 60)
        print("✅ DATABASE INITIALIZATION COMPLETE!")
        print("=" * 60)
        print("\n📋 LOGIN CREDENTIALS:")
        print("-" * 60)
        print(f"{'Role':<12} | {'Email':<30} | {'Password':<15}")
        print("-" * 60)
        print(f"{'Admin':<12} | {'admin@hospital.com':<30} | {'admin123':<15}")
        print(f"{'Doctor':<12} | {'doctor@hospital.com':<30} | {'doctor123':<15}")
        print(f"{'Doctor 2':<12} | {'doctor2@hospital.com':<30} | {'doctor123':<15}")
        print(f"{'Pharmacist':<12} | {'pharmacist@hospital.com':<30} | {'pharmacist123':<15}")
        print(f"{'Patient':<12} | {'patient@hospital.com':<30} | {'patient123':<15}")
        print(f"{'Patient 2':<12} | {'patient2@hospital.com':<30} | {'patient123':<15}")
        print("-" * 60)
        print("\n🌐 Start the server: python run.py")
        print("📍 Open in browser: http://localhost:5000")
        print("=" * 60)


if __name__ == '__main__':
    init_database()