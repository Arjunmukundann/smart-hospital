"""
Report Model - Medical reports and AI analysis
"""

from datetime import datetime
from app import db

class Report(db.Model):
    """Medical reports uploaded for analysis"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Report Details
    report_type = db.Column(db.String(50), nullable=False)  # 'blood_test', 'xray', 'mri', etc.
    report_name = db.Column(db.String(200), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    
    # File Information
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20))  # 'pdf', 'image'
    
    # Extracted Data
    extracted_text = db.Column(db.Text)
    
    # AI Analysis
    summary = db.Column(db.Text)
    key_findings = db.Column(db.Text)
    abnormal_values = db.Column(db.Text)
    concern_areas = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    
    # Status
    is_analyzed = db.Column(db.Boolean, default=False)
    analysis_date = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    uploader = db.relationship('User', backref='uploaded_reports')
    
    @staticmethod
    def generate_report_id():
        """Generate unique report ID"""
        today = datetime.now().strftime('%Y%m%d')
        last_report = Report.query.filter(
            Report.report_id.like(f'RPT{today}%')
        ).order_by(Report.id.desc()).first()
        
        if last_report:
            last_num = int(last_report.report_id[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'RPT{today}{new_num:04d}'
    
    def __repr__(self):
        return f'<Report {self.report_id}: {self.report_type}>'