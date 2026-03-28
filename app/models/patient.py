"""
Patient Model - Patient information and medical survey data
With Insurance Integration
"""

from datetime import datetime
from app import db

class Patient(db.Model):
    """Patient profile with medical survey data"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Basic Information
    patient_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(128), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    blood_group = db.Column(db.String(5))
    date_of_birth = db.Column(db.Date)
    
    # NEW: Profile Picture
    profile_picture = db.Column(db.String(255), default='default_patient.png')
    
    # Contact Information
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    
    # Emergency Contact
    emergency_contact_name = db.Column(db.String(128))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relation = db.Column(db.String(50))
    
    # Medical Survey - Lifestyle
    smoking_status = db.Column(db.String(20))
    alcohol_consumption = db.Column(db.String(20))
    food_preference = db.Column(db.String(20))
    exercise_frequency = db.Column(db.String(20))
    
    # Medical Survey - History
    current_medications = db.Column(db.Text)
    past_surgeries = db.Column(db.Text)
    family_history = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Survey completion status
    survey_completed = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    allergies = db.relationship('PatientAllergy', backref='patient', 
                               lazy='dynamic', cascade='all, delete-orphan')
    conditions = db.relationship('PatientCondition', backref='patient', 
                                lazy='dynamic', cascade='all, delete-orphan')
    prescriptions = db.relationship('Prescription', backref='patient', 
                                   lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='patient', 
                             lazy='dynamic', cascade='all, delete-orphan')
    
    # NEW: Insurance relationship
    insurance_policies = db.relationship('PatientInsurance', back_populates='patient_rel',
                                     lazy='dynamic', cascade='all, delete-orphan')
    
    # NEW: Appointment relationship
    appointments = db.relationship('Appointment', backref='patient',
                                  lazy='dynamic', cascade='all, delete-orphan')
    
    # NEW: Feedback relationship
    feedbacks = db.relationship('Feedback', backref='patient',
                               lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def profile_picture_url(self):
        """Return the URL for the profile picture"""
        if self.profile_picture and self.profile_picture != 'default_patient.png':
            return f"/static/uploads/profile_pictures/{self.profile_picture}"
        return "/static/uploads/profile_pictures/default_patient.png"
    
    def get_allergies_list(self):
        """Return list of allergy names"""
        return [a.allergy_name for a in self.allergies.all()]
    
    def get_conditions_list(self):
        """Return list of condition names"""
        return [c.condition_name for c in self.conditions.all()]
    
    def get_current_medications_list(self):
        """Return list of current medications"""
        if self.current_medications:
            return [m.strip() for m in self.current_medications.split(',')]
        return []
    
    def get_primary_insurance(self):
        """Return primary insurance policy"""
        return self.insurance_policies.filter_by(is_primary=True, is_active=True).first()
    
    def has_active_insurance(self):
        """Check if patient has active insurance"""
        return self.insurance_policies.filter_by(is_active=True).count() > 0
    
    @staticmethod
    def generate_patient_id():
        """Generate unique patient ID"""
        last_patient = Patient.query.order_by(Patient.id.desc()).first()
        if last_patient:
            new_id = last_patient.id + 1
        else:
            new_id = 1
        return f'PT{new_id:06d}'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'full_name': self.full_name,
            'age': self.age,
            'gender': self.gender,
            'blood_group': self.blood_group,
            'phone': self.phone,
            'email': self.email,
            'profile_picture': self.profile_picture_url,
            'has_insurance': self.has_active_insurance()
        }
    
    def __repr__(self):
        return f'<Patient {self.patient_id}: {self.full_name}>'


class PatientAllergy(db.Model):
    """Patient allergies"""
    __tablename__ = 'patient_allergies'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    allergy_name = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), default='unknown')
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Allergy {self.allergy_name}>'


class PatientCondition(db.Model):
    """Patient existing conditions"""
    __tablename__ = 'patient_conditions'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    condition_name = db.Column(db.String(100), nullable=False)
    diagnosed_date = db.Column(db.Date)
    current_status = db.Column(db.String(20), default='active')
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Condition {self.condition_name}>'