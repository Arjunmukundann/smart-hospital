"""
Insurance Model - Insurance integration
FIXED: Resolved ambiguous foreign key relationships
"""

from datetime import datetime, date
from app import db

class InsuranceProvider(db.Model):
    """Insurance company/provider"""
    __tablename__ = 'insurance_providers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    logo = db.Column(db.String(255), nullable=True)
    
    # Contact
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    website = db.Column(db.String(255))
    address = db.Column(db.Text)
    
    # API Integration (for automated verification)
    api_endpoint = db.Column(db.String(255), nullable=True)
    api_key = db.Column(db.String(255), nullable=True)
    
    # Coverage details
    coverage_types = db.Column(db.Text)  # JSON: what they cover
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    policies = db.relationship('PatientInsurance', backref='provider', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'logo': self.logo,
            'contact_phone': self.contact_phone,
            'website': self.website
        }
    
    def __repr__(self):
        return f'<InsuranceProvider {self.name}>'


class PatientInsurance(db.Model):
    """Patient's insurance policy details"""
    __tablename__ = 'patient_insurance'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('insurance_providers.id'), nullable=False)
    
    # Policy Details
    policy_number = db.Column(db.String(100), nullable=False)
    group_number = db.Column(db.String(100), nullable=True)
    member_id = db.Column(db.String(100), nullable=False)
    
    # Policy Holder
    policy_holder_name = db.Column(db.String(200), nullable=False)
    relationship_to_patient = db.Column(db.String(50), default='self')  # self, spouse, child, parent
    
    # Coverage
    coverage_type = db.Column(db.String(50))  # individual, family
    plan_type = db.Column(db.String(100))  # HMO, PPO, EPO, etc.
    plan_name = db.Column(db.String(200))
    
    # Validity
    effective_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    
    # Coverage amounts
    coverage_percentage = db.Column(db.Integer, default=80)
    deductible = db.Column(db.Float, default=0)
    deductible_met = db.Column(db.Float, default=0)
    max_coverage = db.Column(db.Float, nullable=True)
    copay_amount = db.Column(db.Float, default=0)
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verification_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected, expired
    verification_notes = db.Column(db.Text)
    
    # Card images
    card_front_image = db.Column(db.String(255))
    card_back_image = db.Column(db.String(255))
    
    is_primary = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - specify foreign_keys explicitly
    patient_rel = db.relationship('Patient', foreign_keys=[patient_id], back_populates='insurance_policies')
    verifier = db.relationship('User', backref='verified_policies', foreign_keys=[verified_by])
    claims = db.relationship('InsuranceClaim', backref='policy', lazy='dynamic',
                            foreign_keys='InsuranceClaim.policy_id')
    
    @property
    def is_expired(self):
        """Check if policy is expired"""
        return self.expiry_date < date.today()
    
    @property
    def is_valid(self):
        """Check if policy is currently valid"""
        today = date.today()
        return (self.is_active and 
                self.effective_date <= today <= self.expiry_date and
                self.verification_status == 'verified')
    
    @property
    def remaining_deductible(self):
        """Calculate remaining deductible"""
        return max(0, self.deductible - self.deductible_met)
    
    def to_dict(self):
        return {
            'id': self.id,
            'provider_name': self.provider.name if self.provider else None,
            'policy_number': self.policy_number,
            'member_id': self.member_id,
            'plan_name': self.plan_name,
            'coverage_percentage': self.coverage_percentage,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_verified': self.is_verified,
            'is_valid': self.is_valid,
            'is_primary': self.is_primary
        }
    
    def __repr__(self):
        return f'<PatientInsurance {self.policy_number}>'


class InsuranceClaim(db.Model):
    """Insurance claims for billing"""
    __tablename__ = 'insurance_claims'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_number = db.Column(db.String(100), unique=True, nullable=False)
    
    # References - NO bidirectional FK to pharmacy_bills
    policy_id = db.Column(db.Integer, db.ForeignKey('patient_insurance.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    # Store pharmacy bill ID without FK to avoid circular reference
    pharmacy_bill_id = db.Column(db.Integer, nullable=True)  # No FK constraint
    
    # General bill reference
    general_bill_id = db.Column(db.Integer, nullable=True)  # No FK constraint
    
    claim_type = db.Column(db.String(50))  # consultation, procedure, medication, lab_test
    
    # Amounts
    total_amount = db.Column(db.Float, nullable=False)
    claimed_amount = db.Column(db.Float, nullable=False)
    approved_amount = db.Column(db.Float, default=0)
    patient_responsibility = db.Column(db.Float, default=0)
    
    # Status
    status = db.Column(db.String(20), default='submitted')  # submitted, processing, approved, rejected, paid
    
    # Dates
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    # Details
    diagnosis_codes = db.Column(db.Text)  # ICD codes
    procedure_codes = db.Column(db.Text)  # CPT codes
    rejection_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - explicit foreign_keys
    patient = db.relationship('Patient', backref='insurance_claims', foreign_keys=[patient_id])
    appointment = db.relationship('Appointment', backref='insurance_claims', foreign_keys=[appointment_id])
    
    @staticmethod
    def generate_claim_number():
        """Generate unique claim number"""
        today = datetime.now().strftime('%Y%m%d')
        last_claim = InsuranceClaim.query.filter(
            InsuranceClaim.claim_number.like(f'CLM{today}%')
        ).order_by(InsuranceClaim.id.desc()).first()
        
        if last_claim:
            last_num = int(last_claim.claim_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'CLM{today}{new_num:04d}'
    
    def get_pharmacy_bill(self):
        """Get associated pharmacy bill if any"""
        if self.pharmacy_bill_id:
            from app.models.pharmacy import PharmacyBill
            return PharmacyBill.query.get(self.pharmacy_bill_id)
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'claim_number': self.claim_number,
            'claim_type': self.claim_type,
            'total_amount': self.total_amount,
            'claimed_amount': self.claimed_amount,
            'approved_amount': self.approved_amount,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None
        }
    
    def __repr__(self):
        return f'<InsuranceClaim {self.claim_number}>'