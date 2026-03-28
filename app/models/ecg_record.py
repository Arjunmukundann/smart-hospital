"""
ECG Record Model - ECG analysis results
"""

from datetime import datetime
from app.extensions import db
import json


class ECGPatient(db.Model):
    """ECG Patient record (can be linked to hospital Patient or standalone)"""
    __tablename__ = 'ecg_patients'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to hospital patient (optional)
    hospital_patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    
    # If standalone ECG patient
    name = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    
    # Who uploaded
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ecg_results = db.relationship('ECGResult', backref='ecg_patient', 
                                  lazy='dynamic', cascade='all, delete-orphan')
    uploader = db.relationship('User', backref='ecg_uploads')
    hospital_patient = db.relationship('Patient', backref='ecg_records')
    
    def __repr__(self):
        return f'<ECGPatient {self.name}>'


class ECGResult(db.Model):
    """ECG Analysis Result"""
    __tablename__ = 'ecg_results'
    
    id = db.Column(db.Integer, primary_key=True)
    ecg_patient_id = db.Column(db.Integer, db.ForeignKey('ecg_patients.id'), nullable=False)
    
    # File info
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    
    # Predictions (JSON)
    predictions = db.Column(db.Text, nullable=True)
    
    # Summary results
    risk_level = db.Column(db.String(20), nullable=True)  # NORMAL, LOW, MODERATE, HIGH, UNKNOWN
    confidence = db.Column(db.Float, nullable=True)
    
    # Beat statistics
    total_beats = db.Column(db.Integer, default=0)
    normal_beats = db.Column(db.Integer, default=0)
    ventricular_beats = db.Column(db.Integer, default=0)
    supraventricular_beats = db.Column(db.Integer, default=0)
    fusion_beats = db.Column(db.Integer, default=0)
    unknown_beats = db.Column(db.Integer, default=0)
    
    # Analysis metadata
    duration_seconds = db.Column(db.Float, default=0)
    sampling_rate = db.Column(db.Integer, default=360)
    
    # Message/diagnosis
    message = db.Column(db.Text, nullable=True)
    
    # Timestamps
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_predictions(self):
        """Get predictions as dict"""
        if self.predictions:
            try:
                return json.loads(self.predictions)
            except:
                return {}
        return {}
    
    def get_class_distribution(self):
        """Get beat class distribution"""
        return {
            'N': self.normal_beats,
            'V': self.ventricular_beats,
            'S': self.supraventricular_beats,
            'F': self.fusion_beats,
            'Q': self.unknown_beats
        }
    
    def get_percentages(self):
        """Get beat percentages"""
        total = self.total_beats or 1
        return {
            'N': round(self.normal_beats / total * 100, 1),
            'V': round(self.ventricular_beats / total * 100, 1),
            'S': round(self.supraventricular_beats / total * 100, 1),
            'F': round(self.fusion_beats / total * 100, 1),
            'Q': round(self.unknown_beats / total * 100, 1)
        }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'patient_name': self.ecg_patient.name if self.ecg_patient else 'Unknown',
            'patient_age': self.ecg_patient.age if self.ecg_patient else 0,
            'patient_gender': self.ecg_patient.gender if self.ecg_patient else '',
            'file_name': self.file_name,
            'risk_level': self.risk_level,
            'confidence': round(self.confidence * 100, 1) if self.confidence else 0,
            'total_beats': self.total_beats,
            'class_distribution': self.get_class_distribution(),
            'percentages': self.get_percentages(),
            'message': self.message,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None
        }
    
    def __repr__(self):
        return f'<ECGResult {self.id} - {self.risk_level}>'