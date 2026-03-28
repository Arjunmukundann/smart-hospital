"""
Inventory Model - Medicine inventory management
"""

from datetime import datetime
from app import db

class Inventory(db.Model):
    """Medicine inventory tracking"""
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Medicine Details
    medicine_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    generic_name = db.Column(db.String(100))
    category = db.Column(db.String(50))  # 'antibiotic', 'painkiller', 'vitamin', etc.
    manufacturer = db.Column(db.String(100))
    
    # Stock Information
    current_stock = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=50)
    unit = db.Column(db.String(20), default='tablets')  # 'tablets', 'ml', 'capsules'
    unit_price = db.Column(db.Float, default=0.0)
    
    # Expiry tracking
    expiry_date = db.Column(db.Date)
    batch_number = db.Column(db.String(50))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('InventoryTransaction', backref='medicine',
                                  lazy='dynamic', cascade='all, delete-orphan')
    
    def is_low_stock(self):
        """Check if stock is below reorder level"""
        return self.current_stock <= self.reorder_level
    
    def is_out_of_stock(self):
        """Check if medicine is out of stock"""
        return self.current_stock <= 0
    
    def get_stock_status(self):
        """Get stock status as string"""
        if self.current_stock <= 0:
            return 'out_of_stock'
        elif self.current_stock <= self.reorder_level:
            return 'low_stock'
        else:
            return 'in_stock'
    
    def get_stock_percentage(self):
        """Get stock level as percentage"""
        max_stock = max(self.reorder_level * 3, 100)
        return min((self.current_stock / max_stock) * 100, 100)
    
    @classmethod
    def get_available_medicines(cls):
        """Get all medicines that are in stock"""
        return cls.query.filter(
            cls.current_stock > 0,
            cls.is_active == True
        ).order_by(cls.medicine_name).all()
    
    @classmethod
    def get_out_of_stock_medicines(cls):
        """Get all out of stock medicines"""
        return cls.query.filter(
            cls.current_stock <= 0,
            cls.is_active == True
        ).order_by(cls.medicine_name).all()
    
    @classmethod
    def check_medicine_stock(cls, medicine_name, required_quantity=1):
        """
        Check if a medicine is available in required quantity
        Returns: (is_available, medicine_obj, message)
        """
        # Find medicine (case-insensitive partial match)
        medicine = cls.query.filter(
            cls.medicine_name.ilike(f'%{medicine_name}%'),
            cls.is_active == True
        ).first()
        
        if not medicine:
            return True, None, "Medicine not in inventory (external)"
        
        if medicine.current_stock <= 0:
            return False, medicine, f"OUT OF STOCK: {medicine.medicine_name} (0 {medicine.unit} available)"
        
        if medicine.current_stock < required_quantity:
            return False, medicine, f"INSUFFICIENT STOCK: {medicine.medicine_name} (Only {medicine.current_stock} {medicine.unit} available, need {required_quantity})"
        
        return True, medicine, f"Available: {medicine.current_stock} {medicine.unit}"
    
    def __repr__(self):
        return f'<Inventory {self.medicine_name}: {self.current_stock}>'


class InventoryTransaction(db.Model):
    """Inventory transaction log"""
    __tablename__ = 'inventory_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    
    # Transaction Details
    transaction_type = db.Column(db.String(20), nullable=False)  # 'add', 'remove', 'prescribed'
    quantity = db.Column(db.Integer, nullable=False)
    reference_id = db.Column(db.String(50))  # Prescription ID or PO number
    
    # User who made the transaction
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationship
    user = db.relationship('User', backref='inventory_transactions')
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type}: {self.quantity}>'