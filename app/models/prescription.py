"""
Prescription Model - With Digital Signature and Referral Support
"""

from datetime import datetime
from app import db

class Prescription(db.Model):
    """Prescription created by doctor for patient"""
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    # Prescription Details
    diagnosis = db.Column(db.Text, nullable=False)
    symptoms = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='active')  # 'active', 'completed', 'cancelled', 'dispensed'
    
    # Safety Check Results
    safety_checked = db.Column(db.Boolean, default=False)
    safety_overridden = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.Text)
    
    # OCR Source (if from handwritten)
    ocr_source = db.Column(db.String(255))
    
    # ========== NEW: Digital Signature ==========
    is_signed = db.Column(db.Boolean, default=False)
    signature_image = db.Column(db.String(255), nullable=True)
    signed_at = db.Column(db.DateTime, nullable=True)
    signature_hash = db.Column(db.String(256), nullable=True)  # For verification
    
    # ========== NEW: Referral Support ==========
    is_referral = db.Column(db.Boolean, default=False)
    referred_to_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    referral_reason = db.Column(db.Text, nullable=True)
    referral_urgency = db.Column(db.String(20), default='normal')  # normal, urgent, emergency
    referral_status = db.Column(db.String(20), default='pending')  # pending, accepted, completed, declined
    referral_notes = db.Column(db.Text, nullable=True)
    
    # ========== NEW: Pharmacy/Dispensing ==========
    dispensed_at = db.Column(db.DateTime, nullable=True)
    dispensed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    pharmacy_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    valid_until = db.Column(db.Date)
    
    # Relationships
    medicines = db.relationship('PrescriptionMedicine', backref='prescription',
                               lazy='dynamic', cascade='all, delete-orphan')
    alerts = db.relationship('SafetyAlert', backref='prescription',
                            lazy='dynamic', cascade='all, delete-orphan')
    
    # NEW: Referral relationship
    referred_doctor = db.relationship('User', foreign_keys=[referred_to_doctor_id],
                                      backref='referrals_for_me')
    dispensing_pharmacist = db.relationship('User', foreign_keys=[dispensed_by],
                                           backref='prescriptions_dispensed')
    
    @staticmethod
    def generate_prescription_id():
        """Generate unique prescription ID"""
        today = datetime.now().strftime('%Y%m%d')
        last_prescription = Prescription.query.filter(
            Prescription.prescription_id.like(f'RX{today}%')
        ).order_by(Prescription.id.desc()).first()
        
        if last_prescription:
            last_num = int(last_prescription.prescription_id[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'RX{today}{new_num:04d}'
    
    def get_medicines_list(self):
        """Return list of medicine details"""
        return [
            {
                'id': m.id,
                'name': m.medicine_name,
                'dosage': m.dosage,
                'frequency': m.frequency,
                'duration': m.duration,
                'timing': m.timing,
                'instructions': m.instructions,
                'quantity': m.quantity,
                'is_dispensed': m.is_dispensed
            }
            for m in self.medicines.all()
        ]
    
    @property
    def signature_url(self):
        """Return URL for signature image"""
        if self.signature_image:
            return f"/static/uploads/signatures/{self.signature_image}"
        return None
    
    def can_be_dispensed(self):
        """Check if prescription can be dispensed"""
        return self.is_signed and self.status == 'active'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'prescription_id': self.prescription_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'doctor_name': self.doctor.full_name if self.doctor else None,
            'diagnosis': self.diagnosis,
            'is_signed': self.is_signed,
            'status': self.status,
            'is_referral': self.is_referral,
            'referred_to': self.referred_doctor.full_name if self.referred_doctor else None,
            'medicines': self.get_medicines_list(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Prescription {self.prescription_id}>'


class PrescriptionMedicine(db.Model):
    """Medicine in a prescription"""
    __tablename__ = 'prescription_medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    
    # Medicine Details
    medicine_name = db.Column(db.String(100), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=True)  # Link to inventory
    dosage = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    timing = db.Column(db.String(100))
    
    # NEW: Quantity for pharmacy
    quantity = db.Column(db.Integer, default=0)
    
    # Timing specifics
    morning = db.Column(db.Boolean, default=False)
    afternoon = db.Column(db.Boolean, default=False)
    evening = db.Column(db.Boolean, default=False)
    night = db.Column(db.Boolean, default=False)
    
    # Additional instructions
    instructions = db.Column(db.Text)
    
    # NEW: Dispensing tracking
    is_dispensed = db.Column(db.Boolean, default=False)
    dispensed_quantity = db.Column(db.Integer, default=0)
    
    # Relationship to inventory
    inventory_item = db.relationship('Inventory', backref='prescription_items')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'medicine_name': self.medicine_name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'timing': self.timing,
            'quantity': self.quantity,
            'instructions': self.instructions,
            'is_dispensed': self.is_dispensed
        }
    
    def __repr__(self):
        return f'<Medicine {self.medicine_name} - {self.dosage}>'