"""
Pharmacy Model - Pharmacy module with billing
FIXED: Resolved ambiguous foreign key relationships
"""

from datetime import datetime
from app import db

class PharmacyBill(db.Model):
    """Pharmacy billing"""
    __tablename__ = 'pharmacy_bills'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # References
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)
    pharmacist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Amounts
    subtotal = db.Column(db.Float, nullable=False, default=0)
    discount = db.Column(db.Float, default=0)
    discount_reason = db.Column(db.String(200))
    tax = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    
    # Payment
    payment_method = db.Column(db.String(50))  # cash, card, upi, insurance
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, partial, refunded
    amount_paid = db.Column(db.Float, default=0)
    change_given = db.Column(db.Float, default=0)
    
    # Insurance - Store claim ID but don't create bidirectional FK
    insurance_claim_id = db.Column(db.Integer, nullable=True)  # Removed FK to avoid circular reference
    insurance_covered = db.Column(db.Float, default=0)
    
    # Notes
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    # Relationships - Specify foreign_keys explicitly
    patient = db.relationship('Patient', backref='pharmacy_bills', foreign_keys=[patient_id])
    prescription = db.relationship('Prescription', backref='pharmacy_bill', foreign_keys=[prescription_id])
    pharmacist = db.relationship('User', backref='bills_created', foreign_keys=[pharmacist_id])
    items = db.relationship('PharmacyBillItem', backref='bill', cascade='all, delete-orphan')
    
    @staticmethod
    def generate_bill_number():
        """Generate unique bill number"""
        today = datetime.now().strftime('%Y%m%d')
        last_bill = PharmacyBill.query.filter(
            PharmacyBill.bill_number.like(f'PB{today}%')
        ).order_by(PharmacyBill.id.desc()).first()
        
        if last_bill:
            last_num = int(last_bill.bill_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'PB{today}{new_num:04d}'
    
    def calculate_totals(self, tax_rate=0.05):
        """Calculate subtotal, tax, and total"""
        self.subtotal = sum(item.total_price for item in self.items)
        self.tax = round(self.subtotal * tax_rate, 2)
        self.total_amount = round(self.subtotal + self.tax - self.discount, 2)
    
    @property
    def balance_due(self):
        """Calculate remaining balance"""
        return max(0, self.total_amount - self.amount_paid - self.insurance_covered)
    
    @property
    def is_fully_paid(self):
        """Check if bill is fully paid"""
        return self.balance_due <= 0
    
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
            'prescription_id': self.prescription.prescription_id if self.prescription else None,
            'subtotal': self.subtotal,
            'discount': self.discount,
            'tax': self.tax,
            'total_amount': self.total_amount,
            'amount_paid': self.amount_paid,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items]
        }
    
    def __repr__(self):
        return f'<PharmacyBill {self.bill_number}>'


class PharmacyBillItem(db.Model):
    """Individual items in a pharmacy bill"""
    __tablename__ = 'pharmacy_bill_items'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('pharmacy_bills.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    
    medicine_name = db.Column(db.String(200), nullable=False)
    batch_number = db.Column(db.String(50))
    expiry_date = db.Column(db.Date)
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # From prescription (if applicable)
    prescription_medicine_id = db.Column(db.Integer, db.ForeignKey('prescription_medicines.id'), nullable=True)
    
    # Relationships
    medicine = db.relationship('Inventory', backref='pharmacy_bill_items')
    prescription_medicine = db.relationship('PrescriptionMedicine', backref='pharmacy_bill_items')
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_name': self.medicine_name,
            'batch_number': self.batch_number,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price
        }
    
    def __repr__(self):
        return f'<BillItem {self.medicine_name} x{self.quantity}>'