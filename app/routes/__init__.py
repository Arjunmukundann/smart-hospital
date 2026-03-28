"""
Smart Hospital Platform - Routes
"""

from app.routes.auth import auth_bp
from app.routes.doctor import doctor_bp
from app.routes.patient import patient_bp
from app.routes.admin import admin_bp
from app.routes.api import api_bp

__all__ = ['auth_bp', 'doctor_bp', 'patient_bp', 'admin_bp', 'api_bp']