"""
Smart Hospital Platform - Configuration
"""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class"""
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-hospital-secret-key-2024'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'hospital.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # WTF Forms
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    # Data files paths
    DATA_FOLDER = os.path.join(basedir, 'static', 'data')
    DRUG_INTERACTIONS_FILE = os.path.join(DATA_FOLDER, 'drug_interactions.csv')
    FOOD_INTERACTIONS_FILE = os.path.join(DATA_FOLDER, 'food_interactions.csv')
    MEDICAL_TERMS_FILE = os.path.join(DATA_FOLDER, 'medical_terms.json')
    HOSPITAL_INFO_FILE = os.path.join(DATA_FOLDER, 'hospital_info.json')

    # ===== EMAIL CONFIGURATION =====
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # ===== REMINDER SETTINGS =====
    REMINDER_ENABLED = True
    REMINDER_TIMES = {
        'morning': '08:00',
        'afternoon': '13:00',
        'evening': '18:00',
        'night': '21:00'
    }
    
    # ===== VIDEO CONSULTATION SETTINGS =====
    VIDEO_CONSULTATION_ENABLED = True
    VIDEO_SESSION_DURATION = 30  # minutes
    
    # ===== PHARMACY SETTINGS =====
    TAX_RATE = 0.05  # 5% tax
    
    # ===== HOSPITAL INFO =====
    HOSPITAL_NAME = os.environ.get('HOSPITAL_NAME', 'Smart Hospital')
    HOSPITAL_ADDRESS = os.environ.get('HOSPITAL_ADDRESS', '123 Medical Center Drive')
    HOSPITAL_PHONE = os.environ.get('HOSPITAL_PHONE', '+1-234-567-8900')
    HOSPITAL_EMAIL = os.environ.get('HOSPITAL_EMAIL', 'info@smarthospital.com')
    # Add to Config class in app/config.py

    # ECG Model Configuration
    ECG_MODEL_PATH = os.path.join(basedir, 'static', 'models', 'ecg')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'