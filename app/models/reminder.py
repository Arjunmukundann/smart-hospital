"""
Reminder Models - Settings and Logs for medicine reminders
"""

from datetime import datetime
from app import db


class ReminderSetting(db.Model):
    """Patient-specific reminder settings"""
    __tablename__ = 'reminder_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, unique=True)
    
    # Notification preferences
    email_enabled = db.Column(db.Boolean, default=True)
    sms_enabled = db.Column(db.Boolean, default=False)
    push_enabled = db.Column(db.Boolean, default=False)
    
    # Contact information for reminders
    reminder_email = db.Column(db.String(120))
    reminder_phone = db.Column(db.String(20))
    
    # Custom timing preferences
    morning_time = db.Column(db.String(10), default='08:00')
    afternoon_time = db.Column(db.String(10), default='13:00')
    evening_time = db.Column(db.String(10), default='18:00')
    night_time = db.Column(db.String(10), default='21:00')
    
    # Minutes before scheduled time to send reminder
    reminder_advance_minutes = db.Column(db.Integer, default=30)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    patient = db.relationship('Patient', backref=db.backref('reminder_settings', uselist=False))
    
    def get_time_for_timing(self, timing: str) -> str:
        """Get the scheduled time for a specific timing"""
        timing_map = {
            'morning': self.morning_time,
            'afternoon': self.afternoon_time,
            'evening': self.evening_time,
            'night': self.night_time
        }
        return timing_map.get(timing.lower(), '08:00')
    
    def __repr__(self):
        return f'<ReminderSetting Patient:{self.patient_id}>'


class ReminderLog(db.Model):
    """Log of sent reminders"""
    __tablename__ = 'reminder_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Reminder details
    reminder_type = db.Column(db.String(20))  # 'email', 'sms', 'push'
    timing = db.Column(db.String(20))  # 'morning', 'afternoon', 'evening', 'night'
    
    # Content
    medicines_included = db.Column(db.Text)  # JSON string of medicine names
    recipient = db.Column(db.String(120))  # Email or phone number
    
    # Status
    status = db.Column(db.String(20), default='pending')  # 'pending', 'sent', 'failed', 'delivered'
    error_message = db.Column(db.Text)
    
    # Timestamps
    scheduled_time = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    patient = db.relationship('Patient', backref='reminder_logs')
    
    def __repr__(self):
        return f'<ReminderLog {self.id} - {self.status}>'


class GlobalReminderSettings(db.Model):
    """System-wide reminder settings (managed by admin)"""
    __tablename__ = 'global_reminder_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(50), unique=True, nullable=False)
    setting_value = db.Column(db.String(255))
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    @classmethod
    def get_setting(cls, key: str, default=None):
        """Get a setting value"""
        setting = cls.query.filter_by(setting_key=key).first()
        return setting.setting_value if setting else default
    
    @classmethod
    def set_setting(cls, key: str, value: str, user_id: int = None):
        """Set a setting value"""
        setting = cls.query.filter_by(setting_key=key).first()
        if setting:
            setting.setting_value = value
            setting.updated_by = user_id
        else:
            setting = cls(setting_key=key, setting_value=value, updated_by=user_id)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<GlobalSetting {self.setting_key}={self.setting_value}>'