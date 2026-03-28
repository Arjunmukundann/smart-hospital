"""
User Model - Handles authentication and user management
With Profile Pictures and Digital Signatures
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False)  # 'doctor', 'patient', 'admin', 'pharmacist'
    
    # NEW: Profile Picture
    profile_picture = db.Column(db.String(255), default='default_avatar.png')
    
    # Doctor-specific fields
    specialization = db.Column(db.String(100))
    license_number = db.Column(db.String(50))
    qualification = db.Column(db.String(200))
    experience_years = db.Column(db.Integer, default=0)
    department = db.Column(db.String(100))
    consultation_fee = db.Column(db.Float, default=0)
    
    # NEW: Video consultation settings (for doctors)
    is_available_online = db.Column(db.Boolean, default=True)
    video_consultation_fee = db.Column(db.Float, default=0)
    
    # NEW: Digital Signature (for doctors)
    digital_signature = db.Column(db.String(255), nullable=True)
    signature_verified = db.Column(db.Boolean, default=False)
    
    # NEW: Rating (for doctors)
    average_rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    
    # NEW: Statistics
    total_patients = db.Column(db.Integer, default=0)
    active_patients = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    prescriptions_created = db.relationship('Prescription', 
                                            foreign_keys='Prescription.doctor_id',
                                            backref='doctor', lazy='dynamic')
    patient_profile = db.relationship('Patient', backref='user', uselist=False)
    
    # NEW: Relationships for new features
    appointments_as_doctor = db.relationship('Appointment', 
                                             foreign_keys='Appointment.doctor_id',
                                             backref='doctor_user', lazy='dynamic')
    feedbacks_received = db.relationship('Feedback',
                                         foreign_keys='Feedback.doctor_id',
                                         backref='doctor_user', lazy='dynamic')
    referrals_made = db.relationship('DoctorReferral',
                                     foreign_keys='DoctorReferral.referring_doctor_id',
                                     backref='referring_doctor', lazy='dynamic')
    referrals_received = db.relationship('DoctorReferral',
                                         foreign_keys='DoctorReferral.referred_to_doctor_id',
                                         backref='referred_to_doctor', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def is_doctor(self):
        return self.role == 'doctor'
    
    def is_patient(self):
        return self.role == 'patient'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_pharmacist(self):
        return self.role == 'pharmacist'
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @property
    def profile_picture_url(self):
        """Return the URL for the profile picture"""
        if self.profile_picture and self.profile_picture != 'default_avatar.png':
            return f"/static/uploads/profile_pictures/{self.profile_picture}"
        return "/static/uploads/profile_pictures/default_avatar.png"
    
    @property
    def signature_url(self):
        """Return the URL for the digital signature"""
        if self.digital_signature:
            return f"/static/uploads/signatures/{self.digital_signature}"
        return None
    
    def update_rating(self):
        """Recalculate average rating from feedbacks"""
        from app.models.feedback import Feedback
        feedbacks = Feedback.query.filter_by(doctor_id=self.id, is_approved=True).all()
        if feedbacks:
            total = sum(f.overall_rating for f in feedbacks)
            self.average_rating = round(total / len(feedbacks), 2)
            self.total_reviews = len(feedbacks)
        else:
            self.average_rating = 0.0
            self.total_reviews = 0
    
    def update_patient_stats(self):
        """Update patient statistics"""
        from app.models.prescription import Prescription
        from app.models.appointment import Appointment
        from datetime import timedelta
        
        # Total unique patients
        self.total_patients = db.session.query(
            db.func.count(db.distinct(Prescription.patient_id))
        ).filter(Prescription.doctor_id == self.id).scalar() or 0
        
        # Active patients (with activity in last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        self.active_patients = db.session.query(
            db.func.count(db.distinct(Appointment.patient_id))
        ).filter(
            Appointment.doctor_id == self.id,
            Appointment.created_at >= thirty_days_ago
        ).scalar() or 0
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'profile_picture': self.profile_picture_url,
            'is_active': self.is_active
        }
        
        if self.is_doctor():
            data.update({
                'specialization': self.specialization,
                'department': self.department,
                'qualification': self.qualification,
                'experience_years': self.experience_years,
                'consultation_fee': self.consultation_fee,
                'video_consultation_fee': self.video_consultation_fee,
                'is_available_online': self.is_available_online,
                'average_rating': self.average_rating,
                'total_reviews': self.total_reviews,
                'total_patients': self.total_patients,
                'active_patients': self.active_patients
            })
        
        return data
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class DoctorAvailability(db.Model):
    """Doctor's weekly availability schedule"""
    __tablename__ = 'doctor_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_duration = db.Column(db.Integer, default=30)  # minutes
    is_active = db.Column(db.Boolean, default=True)
    consultation_type = db.Column(db.String(20), default='both')  # in_person, video, both
    
    # Relationship
    doctor = db.relationship('User', backref='availability_schedule')
    
    def __repr__(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return f'<Availability {days[self.day_of_week]} {self.start_time}-{self.end_time}>'