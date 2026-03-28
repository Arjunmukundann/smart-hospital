"""
Chat Log Model - Chatbot conversation logs
"""

from datetime import datetime
from app import db

class ChatLog(db.Model):
    """Chatbot conversation logs"""
    __tablename__ = 'chat_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(100))  # greeting, doctor_info, hospital_info, etc.
    confidence = db.Column(db.Float)  # confidence score if using ML
    
    # Context
    context_data = db.Column(db.Text)  # JSON: any context used
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='chat_logs')
    
    def __repr__(self):
        return f'<ChatLog {self.session_id[:8]}...>'


class ChatbotFAQ(db.Model):
    """Frequently asked questions for chatbot"""
    __tablename__ = 'chatbot_faqs'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # general, doctor, appointment, etc.
    keywords = db.Column(db.Text)  # comma-separated keywords
    
    is_active = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    helpful_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FAQ {self.question[:30]}...>'