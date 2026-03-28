"""
Appointment Model - Appointment booking system
"""

from datetime import datetime, date, time
from app import db

class Appointment(db.Model):
    """Appointment booking between patient and doctor"""
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Appointment Details
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    
    appointment_type = db.Column(db.String(20), nullable=False, default='in_person')  # 'in_person', 'video'
    status = db.Column(db.String(20), default='scheduled')  # scheduled, confirmed, completed, cancelled, no_show
    
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Priority
    priority = db.Column(db.String(20), default='normal')  # normal, urgent, emergency
    
    # Video consultation specific
    video_room_id = db.Column(db.String(100), nullable=True)
    video_call_started_at = db.Column(db.DateTime, nullable=True)
    video_call_ended_at = db.Column(db.DateTime, nullable=True)
    
    # Payment
    fee_amount = db.Column(db.Float, default=0)
    is_paid = db.Column(db.Boolean, default=False)
    payment_method = db.Column(db.String(50))
    payment_id = db.Column(db.String(100), nullable=True)
    
    # Reminders
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_sent_at = db.Column(db.DateTime)
    
    # Check-in
    checked_in_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)
    
    # Relationships
    prescription = db.relationship('Prescription', backref='appointment', uselist=False)
    feedback = db.relationship('Feedback', backref='appointment', uselist=False)
    video_session = db.relationship('VideoSession', backref='appointment', uselist=False)
    
    @staticmethod
    def generate_appointment_number():
        """Generate unique appointment number"""
        today = datetime.now().strftime('%Y%m%d')
        last_apt = Appointment.query.filter(
            Appointment.appointment_number.like(f'APT{today}%')
        ).order_by(Appointment.id.desc()).first()
        
        if last_apt:
            last_num = int(last_apt.appointment_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'APT{today}{new_num:04d}'
    
    @property
    def is_upcoming(self):
        """Check if appointment is in the future"""
        apt_datetime = datetime.combine(self.appointment_date, self.appointment_time)
        return apt_datetime > datetime.now()
    
    @property
    def is_today(self):
        """Check if appointment is today"""
        return self.appointment_date == date.today()
    
    @property
    def formatted_time(self):
        """Return formatted time string"""
        return self.appointment_time.strftime('%I:%M %p')
    
    @property
    def formatted_date(self):
        """Return formatted date string"""
        return self.appointment_date.strftime('%B %d, %Y')
    
    def can_start_video(self):
        """Check if video call can be started"""
        if self.appointment_type != 'video':
            return False
        if self.status not in ['scheduled', 'confirmed']:
            return False
        
        # Allow starting 10 minutes before scheduled time
        apt_datetime = datetime.combine(self.appointment_date, self.appointment_time)
        from datetime import timedelta
        start_window = apt_datetime - timedelta(minutes=10)
        end_window = apt_datetime + timedelta(minutes=self.duration_minutes + 30)
        
        now = datetime.now()
        return start_window <= now <= end_window
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'appointment_number': self.appointment_number,
            'patient_name': self.patient.full_name if self.patient else None,
            'patient_id': self.patient.patient_id if self.patient else None,
            'doctor_name': self.doctor_user.full_name if self.doctor_user else None,
            'doctor_specialization': self.doctor_user.specialization if self.doctor_user else None,
            'date': self.appointment_date.isoformat(),
            'time': self.appointment_time.strftime('%H:%M'),
            'formatted_date': self.formatted_date,
            'formatted_time': self.formatted_time,
            'type': self.appointment_type,
            'status': self.status,
            'priority': self.priority,
            'reason': self.reason,
            'fee_amount': self.fee_amount,
            'is_paid': self.is_paid,
            'video_room_id': self.video_room_id,
            'can_start_video': self.can_start_video()
        }
    
    def __repr__(self):
        return f'<Appointment {self.appointment_number}>'


class TimeSlot(db.Model):
    """Available time slots for appointments"""
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_booked = db.Column(db.Boolean, default=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    slot_type = db.Column(db.String(20), default='both')  # in_person, video, both
    
    # Relationship
    doctor = db.relationship('User', backref='time_slots')
    appointment = db.relationship('Appointment', backref='time_slot')
    
    def __repr__(self):
        return f'<TimeSlot {self.date} {self.start_time}-{self.end_time}>'