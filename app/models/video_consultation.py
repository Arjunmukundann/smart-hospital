"""
Video Consultation Model - Video call sessions
"""

from datetime import datetime
import uuid
from app import db

class VideoSession(db.Model):
    """Video consultation session"""
    __tablename__ = 'video_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Session Status
    status = db.Column(db.String(20), default='waiting')  # waiting, active, ended
    
    # Timing
    scheduled_at = db.Column(db.DateTime, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, default=0)
    
    # Participant Status
    doctor_joined = db.Column(db.Boolean, default=False)
    doctor_joined_at = db.Column(db.DateTime)
    patient_joined = db.Column(db.Boolean, default=False)
    patient_joined_at = db.Column(db.DateTime)
    
    # Recording (optional)
    is_recorded = db.Column(db.Boolean, default=False)
    recording_url = db.Column(db.String(255), nullable=True)
    recording_consent = db.Column(db.Boolean, default=False)
    
    # Quality metrics
    doctor_connection_quality = db.Column(db.String(20), nullable=True)
    patient_connection_quality = db.Column(db.String(20), nullable=True)
    
    # Notes
    session_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('User', backref='video_sessions_as_doctor')
    patient_rel = db.relationship('Patient', backref='video_sessions')
    
    @staticmethod
    def generate_room_id():
        """Generate unique room ID"""
        return f"room_{uuid.uuid4().hex[:12]}"
    
    @property
    def is_active(self):
        """Check if session is currently active"""
        return self.status == 'active'
    
    @property
    def can_join(self):
        """Check if session can be joined"""
        if self.status == 'ended':
            return False
        
        # Allow joining 10 minutes before to 60 minutes after scheduled time
        from datetime import timedelta
        now = datetime.utcnow()
        start_window = self.scheduled_at - timedelta(minutes=10)
        end_window = self.scheduled_at + timedelta(minutes=60)
        
        return start_window <= now <= end_window
    
    def start_session(self):
        """Mark session as started"""
        self.status = 'active'
        self.started_at = datetime.utcnow()
    
    def end_session(self):
        """Mark session as ended"""
        self.status = 'ended'
        self.ended_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())
    
    def doctor_join(self):
        """Record doctor joining"""
        self.doctor_joined = True
        self.doctor_joined_at = datetime.utcnow()
    
    def patient_join(self):
        """Record patient joining"""
        self.patient_joined = True
        self.patient_joined_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'appointment_id': self.appointment_id,
            'doctor_name': self.doctor.full_name if self.doctor else None,
            'patient_name': self.patient_rel.full_name if self.patient_rel else None,
            'status': self.status,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': self.duration_seconds,
            'can_join': self.can_join
        }
    
    def __repr__(self):
        return f'<VideoSession {self.room_id}>'