"""
Smart Hospital Platform - Application Factory
"""

from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_mail import Mail
from dotenv import load_dotenv
from app.extensions import db, login_manager, csrf, migrate, socketio, mail
from datetime import datetime





def create_app(config_class=None):
    """Application Factory Pattern"""
    load_dotenv() 
    app = Flask(__name__)
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # Load configuration
    if config_class is None:
        from app.config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading',logger=True,engineio_logger=True)  # Add CSRF protection and enable logging
    
    from app.services.video_service import register_socket_events
    register_socket_events(socketio)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader callback
    from app.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.doctor import doctor_bp
    from app.routes.patient import patient_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    
    # NEW: Register new blueprints
    from app.routes.pharmacy import pharmacy_bp
    from app.routes.appointment import appointment_bp
    from app.routes.video_call import video_bp
    from app.routes.chatbot import chatbot_bp
    # Add to your blueprints registration
    from app.routes.meal import meal_bp
    from app.routes.ecg import ecg_bp
    app.register_blueprint(meal_bp, url_prefix='/meal')
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # NEW: Register new blueprints
    app.register_blueprint(pharmacy_bp, url_prefix='/pharmacy')
    app.register_blueprint(appointment_bp, url_prefix='/appointment')
    app.register_blueprint(video_bp, url_prefix='/video')
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
    app.register_blueprint(ecg_bp, url_prefix='/ecg')
    # Register error handlers
    register_error_handlers(app)
    
    # Create upload directories
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'reports'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'prescriptions'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pictures'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'signatures'), exist_ok=True)
    
    try:

    # Initialize reminder service
        from app.services.reminder_service import reminder_service
        reminder_service.init_app(app)
    except Exception as e:    
    # Register socket events
        from app.services.video_service import register_socket_events
        register_socket_events(socketio)

    try:
        from app.services.ecg_service import ecg_service
        ecg_service.init_app(app)
    except Exception as e:
        print(f"⚠️ ECG service initialization failed: {e}")
        
    return app


def register_error_handlers(app):
    """Register custom error handlers"""
    from flask import render_template
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403