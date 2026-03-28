"""
Referral Model - Doctor-to-Doctor referrals
"""

from datetime import datetime, date, timedelta
from app import db

class DoctorReferral(db.Model):
    """Doctor-to-Doctor referral"""
    __tablename__ = 'doctor_referrals'
    
    id = db.Column(db.Integer, primary_key=True)
    referral_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Doctors involved
    referring_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referred_to_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Patient
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Source prescription (if any)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)
    
    # Referral details
    reason = db.Column(db.Text, nullable=False)
    clinical_summary = db.Column(db.Text)
    clinical_notes = db.Column(db.Text)
    urgency = db.Column(db.String(20), default='normal')  # normal, urgent, emergency
    
    # Referred specialty
    referred_specialty = db.Column(db.String(100))
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, accepted, scheduled, completed, declined
    
    # Response from referred doctor
    accepted_at = db.Column(db.DateTime, nullable=True)
    declined_at = db.Column(db.DateTime, nullable=True)
    decline_reason = db.Column(db.Text, nullable=True)
    
    # Appointment created from referral
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    # Feedback from referred doctor (after consultation)
    consultation_notes = db.Column(db.Text, nullable=True)
    diagnosis_from_referral = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    follow_up_needed = db.Column(db.Boolean, default=False)
    follow_up_instructions = db.Column(db.Text)
    
    # Report back to referring doctor
    report_sent = db.Column(db.Boolean, default=False)
    report_sent_at = db.Column(db.DateTime)
    
    # Validity
    valid_until = db.Column(db.Date, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='referrals')
    prescription = db.relationship('Prescription', backref='referral', foreign_keys=[prescription_id])
    appointment = db.relationship('Appointment', backref='referral', foreign_keys=[appointment_id])
    
    @staticmethod
    def generate_referral_number():
        """Generate unique referral number"""
        today = datetime.now().strftime('%Y%m%d')
        last_ref = DoctorReferral.query.filter(
            DoctorReferral.referral_number.like(f'REF{today}%')
        ).order_by(DoctorReferral.id.desc()).first()
        
        if last_ref:
            last_num = int(last_ref.referral_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'REF{today}{new_num:04d}'
    
    @property
    def is_expired(self):
        """Check if referral is expired"""
        if self.valid_until:
            return self.valid_until < date.today()
        # Default 30 days validity
        return (self.created_at + timedelta(days=30)).date() < date.today()
    
    @property
    def is_active(self):
        """Check if referral is still active"""
        return self.status in ['pending', 'accepted', 'scheduled'] and not self.is_expired
    
    def accept(self):
        """Accept the referral"""
        self.status = 'accepted'
        self.accepted_at = datetime.utcnow()
    
    def decline(self, reason):
        """Decline the referral"""
        self.status = 'declined'
        self.declined_at = datetime.utcnow()
        self.decline_reason = reason
    
    def complete(self, notes, recommendations=None):
        """Mark referral as completed"""
        self.status = 'completed'
        self.consultation_notes = notes
        self.recommendations = recommendations
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'referral_number': self.referral_number,
            'referring_doctor': self.referring_doctor.full_name if self.referring_doctor else None,
            'referring_doctor_specialty': self.referring_doctor.specialization if self.referring_doctor else None,
            'referred_to_doctor': self.referred_to_doctor.full_name if self.referred_to_doctor else None,
            'referred_to_specialty': self.referred_specialty or (
                self.referred_to_doctor.specialization if self.referred_to_doctor else None
            ),
            'patient_name': self.patient.full_name if self.patient else None,
            'patient_id': self.patient.patient_id if self.patient else None,
            'reason': self.reason,
            'urgency': self.urgency,
            'status': self.status,
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<DoctorReferral {self.referral_number}>'