"""
Bill Model - General billing (separate from pharmacy bills)
For consultation fees, procedure charges, etc.
FIXED: Resolved ambiguous foreign key relationships
"""

from datetime import datetime
from app import db

class Bill(db.Model):
    """General hospital bill"""
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Patient
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Related entities
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    # Bill type
    bill_type = db.Column(db.String(50), nullable=False)  # consultation, procedure, lab_test, etc.
    
    # Description
    description = db.Column(db.Text)
    
    # Amounts
    subtotal = db.Column(db.Float, nullable=False, default=0)
    discount = db.Column(db.Float, default=0)
    discount_reason = db.Column(db.String(200))
    tax = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    
    # Payment
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, partial, refunded
    amount_paid = db.Column(db.Float, default=0)
    paid_at = db.Column(db.DateTime)
    
    # Insurance - Store ID without FK to avoid circular reference
    insurance_claim_id = db.Column(db.Integer, nullable=True)  # No FK constraint
    insurance_covered = db.Column(db.Float, default=0)
    
    # Created by
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Notes
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - explicit foreign_keys
    patient = db.relationship('Patient', backref='general_bills', foreign_keys=[patient_id])
    appointment = db.relationship('Appointment', backref='general_bills', foreign_keys=[appointment_id])
    creator = db.relationship('User', backref='bills_generated', foreign_keys=[created_by])
    items = db.relationship('BillItem', backref='bill', cascade='all, delete-orphan')
    
    @staticmethod
    def generate_bill_number(prefix='BILL'):
        """Generate unique bill number"""
        today = datetime.now().strftime('%Y%m%d')
        last_bill = Bill.query.filter(
            Bill.bill_number.like(f'{prefix}{today}%')
        ).order_by(Bill.id.desc()).first()
        
        if last_bill:
            last_num = int(last_bill.bill_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'{prefix}{today}{new_num:04d}'
    
    @property
    def balance_due(self):
        """Calculate remaining balance"""
        return max(0, self.total_amount - self.amount_paid - self.insurance_covered)
    
    @property
    def is_fully_paid(self):
        """Check if bill is fully paid"""
        return self.balance_due <= 0
    
    def calculate_totals(self, tax_rate=0.05):
        """Calculate bill totals"""
        self.subtotal = sum(item.total_price for item in self.items)
        self.tax = round(self.subtotal * tax_rate, 2)
        self.total_amount = round(self.subtotal + self.tax - self.discount, 2)
    
    def get_insurance_claim(self):
        """Get associated insurance claim if any"""
        if self.insurance_claim_id:
            from app.models.insurance import InsuranceClaim
            return InsuranceClaim.query.get(self.insurance_claim_id)
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'bill_number': self.bill_number,
            'patient_name': self.patient.full_name if self.patient else None,
            'bill_type': self.bill_type,
            'subtotal': self.subtotal,
            'discount': self.discount,
            'tax': self.tax,
            'total_amount': self.total_amount,
            'amount_paid': self.amount_paid,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Bill {self.bill_number}>'


class BillItem(db.Model):
    """Individual items in a bill"""
    __tablename__ = 'bill_items'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    
    description = db.Column(db.String(255), nullable=False)
    item_type = db.Column(db.String(50))  # consultation, procedure, test, etc.
    
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # Reference to related entity
    reference_type = db.Column(db.String(50))  # appointment, prescription, etc.
    reference_id = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price
        }
    
    def __repr__(self):
        return f'<BillItem {self.description}>'