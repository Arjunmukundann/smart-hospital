"""
Feedback Model - Ratings and reviews
"""

from datetime import datetime
from app import db

class Feedback(db.Model):
    """Patient feedback and ratings for doctors"""
    __tablename__ = 'feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    # Ratings (1-5 stars)
    overall_rating = db.Column(db.Integer, nullable=False)
    punctuality_rating = db.Column(db.Integer, nullable=True)
    communication_rating = db.Column(db.Integer, nullable=True)
    treatment_rating = db.Column(db.Integer, nullable=True)
    facility_rating = db.Column(db.Integer, nullable=True)
    
    # Feedback content
    title = db.Column(db.String(200), nullable=True)
    review = db.Column(db.Text, nullable=True)
    
    # Options
    would_recommend = db.Column(db.Boolean, default=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # Moderation
    is_approved = db.Column(db.Boolean, default=True)
    is_flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.String(200))
    
    # Doctor response
    doctor_response = db.Column(db.Text, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def update_doctor_rating(doctor_id):
        """Recalculate and update doctor's average rating"""
        from app.models.user import User
        
        feedbacks = Feedback.query.filter_by(
            doctor_id=doctor_id, 
            is_approved=True
        ).all()
        
        doctor = User.query.get(doctor_id)
        if doctor and feedbacks:
            total_rating = sum(f.overall_rating for f in feedbacks)
            doctor.average_rating = round(total_rating / len(feedbacks), 2)
            doctor.total_reviews = len(feedbacks)
            db.session.commit()
    
    @property
    def average_sub_rating(self):
        """Calculate average of sub-ratings"""
        ratings = [r for r in [
            self.punctuality_rating,
            self.communication_rating,
            self.treatment_rating,
            self.facility_rating
        ] if r is not None]
        
        if ratings:
            return round(sum(ratings) / len(ratings), 1)
        return self.overall_rating
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_name': 'Anonymous' if self.is_anonymous else (
                self.patient.full_name if self.patient else 'Unknown'
            ),
            'overall_rating': self.overall_rating,
            'punctuality_rating': self.punctuality_rating,
            'communication_rating': self.communication_rating,
            'treatment_rating': self.treatment_rating,
            'facility_rating': self.facility_rating,
            'title': self.title,
            'review': self.review,
            'would_recommend': self.would_recommend,
            'doctor_response': self.doctor_response,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Feedback {self.id} - Rating: {self.overall_rating}>'