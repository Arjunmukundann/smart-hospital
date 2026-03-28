"""
Safety Alert Model - Track all safety alerts
"""

from datetime import datetime
from app import db

class SafetyAlert(db.Model):
    """Safety alerts generated during prescription"""
    __tablename__ = 'safety_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Alert Details
    alert_type = db.Column(db.String(50), nullable=False)  # 'allergy', 'drug_drug', 'drug_food'
    severity = db.Column(db.String(20), nullable=False)  # 'critical', 'high', 'medium', 'low'
    
    # Alert Content
    medicine_name = db.Column(db.String(100))
    conflicting_item = db.Column(db.String(100))  # Allergen, drug, or food
    description = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text)
    
    # Status
    is_acknowledged = db.Column(db.Boolean, default=False)
    is_overridden = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    acknowledged_at = db.Column(db.DateTime)
    
    # Relationships
    patient = db.relationship('Patient', backref='safety_alerts')
    doctor = db.relationship('User', backref='generated_alerts')
    
    def __repr__(self):
        return f'<SafetyAlert {self.alert_type}: {self.severity}>'