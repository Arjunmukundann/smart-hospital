"""
Chatbot Service - AI-powered hospital assistant
"""

import os
import json
import re
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import User, Patient
from app.models.appointment import Appointment
from app.models.prescription import Prescription

class ChatbotService:
    """Service for chatbot functionality"""
    
    def __init__(self):
        self.hospital_info = self._load_hospital_info()
        self.intents = self._load_intents()
    
    def _load_hospital_info(self):
        """Load hospital information from JSON file"""
        try:
            info_path = os.path.join(
                current_app.config.get('DATA_FOLDER', ''),
                'hospital_info.json'
            )
            if os.path.exists(info_path):
                with open(info_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading hospital info: {e}")
        
        # Return default info
        return {
            'name': current_app.config.get('HOSPITAL_NAME', 'Smart Hospital'),
            'address': current_app.config.get('HOSPITAL_ADDRESS', '123 Medical Center Drive'),
            'phone': current_app.config.get('HOSPITAL_PHONE', '+1-234-567-8900'),
            'email': current_app.config.get('HOSPITAL_EMAIL', 'info@smarthospital.com'),
            'emergency_phone': '+1-234-567-8911',
            'working_hours': 'Monday - Saturday: 8:00 AM - 8:00 PM\nSunday: Emergency Only',
            'departments': ['General Medicine', 'Cardiology', 'Orthopedics', 'Pediatrics', 'Neurology', 'Dermatology']
        }
    
    def _load_intents(self):
        """Load chatbot intents"""
        return {
            'greeting': {
                'patterns': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
                'response': "Hello! Welcome to {hospital_name}. How can I help you today?"
            },
            'goodbye': {
                'patterns': ['bye', 'goodbye', 'see you', 'thanks', 'thank you'],
                'response': "Thank you for using our service. Take care and stay healthy!"
            },
            'hours': {
                'patterns': ['hours', 'timing', 'open', 'close', 'when'],
                'response': "Our working hours are:\n{working_hours}"
            },
            'location': {
                'patterns': ['address', 'location', 'where', 'directions', 'find you'],
                'response': "We are located at:\n📍 {address}"
            },
            'contact': {
                'patterns': ['phone', 'contact', 'call', 'number', 'reach'],
                'response': "You can reach us at:\n📞 {phone}\n📧 {email}"
            },
            'emergency': {
                'patterns': ['emergency', 'urgent', 'ambulance', '911'],
                'response': "🚨 For emergencies, please call: {emergency_phone}\n\nIf this is a life-threatening emergency, please call 911 immediately."
            }
        }
    
    def process_message(self, message, user=None):
        """
        Process user message and return appropriate response
        
        Args:
            message: User's message text
            user: Current user object (if logged in)
            
        Returns:
            dict: Response with type and message
        """
        message_lower = message.lower().strip()
        
        # Check for specific queries first
        
        # Doctor queries
        if self._contains_any(message_lower, ['doctor', 'dr.', 'specialist', 'physician']):
            return self._handle_doctor_query(message_lower)
        
        # Appointment queries
        if self._contains_any(message_lower, ['appointment', 'book', 'schedule', 'booking']):
            return self._handle_appointment_query(message_lower, user)
        
        # Patient statistics (for doctor users)
        if self._contains_any(message_lower, ['patient count', 'how many patient', 'total patient', 'my patient']):
            if user and user.is_doctor():
                return self._handle_doctor_stats(user)
        
        # Department queries
        if self._contains_any(message_lower, ['department', 'specialty', 'specialization', 'unit']):
            return self._handle_department_query()
        
        # Hospital info queries
        if self._contains_any(message_lower, ['hospital', 'about', 'information', 'info']):
            return self._handle_hospital_info()
        
        # Check against predefined intents
        for intent_name, intent_data in self.intents.items():
            if self._contains_any(message_lower, intent_data['patterns']):
                response = intent_data['response'].format(**self.hospital_info)
                return {
                    'type': 'text',
                    'message': response,
                    'intent': intent_name
                }
        
        # Default response
        return {
            'type': 'text',
            'message': self._get_default_response(),
            'intent': 'unknown',
            'suggestions': self._get_suggestions(user)
        }
    
    def _contains_any(self, text, patterns):
        """Check if text contains any of the patterns"""
        return any(pattern in text for pattern in patterns)
    
    def _handle_doctor_query(self, message):
        """Handle doctor-related queries"""
        # Try to extract doctor name
        name_match = re.search(r'(?:doctor|dr\.?)\s+(\w+)', message, re.IGNORECASE)
        
        if name_match:
            doctor_name = name_match.group(1)
            return self._find_doctor_by_name(doctor_name)
        
        # Check for specialty
        specialties = ['cardiologist', 'orthopedic', 'neurologist', 'pediatric', 'dermatologist', 'general']
        for specialty in specialties:
            if specialty in message:
                return self._find_doctors_by_specialty(specialty)
        
        # Return all doctors
        return self._get_all_doctors()
    
    def _find_doctor_by_name(self, name):
        """Find doctor by name"""
        doctors = User.query.filter(
            User.role == 'doctor',
            User.is_active == True,
            db.or_(
                User.full_name.ilike(f'%{name}%'),
                User.username.ilike(f'%{name}%')
            )
        ).all()
        
        if not doctors:
            return {
                'type': 'text',
                'message': f"Sorry, I couldn't find a doctor named '{name}'. Would you like to see all available doctors?",
                'suggestions': ['Show all doctors', 'Search by specialty']
            }
        
        if len(doctors) == 1:
            return self.get_doctor_details(doctors[0])
        
        return {
            'type': 'doctor_list',
            'message': f"I found {len(doctors)} doctors matching '{name}':",
            'doctors': [self._format_doctor_brief(d) for d in doctors]
        }
    
    def _find_doctors_by_specialty(self, specialty):
        """Find doctors by specialty"""
        doctors = User.query.filter(
            User.role == 'doctor',
            User.is_active == True,
            User.specialization.ilike(f'%{specialty}%')
        ).all()
        
        if not doctors:
            return {
                'type': 'text',
                'message': f"Sorry, we don't have any {specialty} specialists at the moment.",
                'suggestions': ['Show all doctors', 'View departments']
            }
        
        return {
            'type': 'doctor_list',
            'message': f"Here are our {specialty} specialists:",
            'doctors': [self._format_doctor_brief(d) for d in doctors]
        }
    
    def _get_all_doctors(self):
        """Get all active doctors"""
        doctors = User.query.filter_by(role='doctor', is_active=True).limit(10).all()
        
        if not doctors:
            return {
                'type': 'text',
                'message': "Sorry, no doctors are currently available."
            }
        
        return {
            'type': 'doctor_list',
            'message': "Here are our available doctors:",
            'doctors': [self._format_doctor_brief(d) for d in doctors]
        }
    
    def get_doctor_details(self, doctor):
        """Get detailed doctor information"""
        # Get statistics
        total_prescriptions = Prescription.query.filter_by(doctor_id=doctor.id).count()
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_patients = db.session.query(
            db.func.count(db.distinct(Appointment.patient_id))
        ).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.created_at >= thirty_days_ago
        ).scalar() or 0
        
        total_appointments = Appointment.query.filter_by(doctor_id=doctor.id).count()
        completed_appointments = Appointment.query.filter_by(
            doctor_id=doctor.id,
            status='completed'
        ).count()
        
        return {
            'type': 'doctor_profile',
            'message': f"Here's information about Dr. {doctor.full_name}:",
            'doctor': {
                'id': doctor.id,
                'name': doctor.full_name,
                'profile_picture': doctor.profile_picture_url,
                'specialization': doctor.specialization or 'General Medicine',
                'qualification': doctor.qualification or 'MBBS',
                'experience': f"{doctor.experience_years or 0} years",
                'department': doctor.department or 'General',
                'consultation_fee': doctor.consultation_fee or 0,
                'video_consultation_fee': doctor.video_consultation_fee or 0,
                'is_available_online': doctor.is_available_online,
                'rating': doctor.average_rating or 0,
                'total_reviews': doctor.total_reviews or 0,
                'statistics': {
                    'total_patients': total_prescriptions,
                    'active_patients': active_patients,
                    'total_appointments': total_appointments,
                    'completed_consultations': completed_appointments
                }
            }
        }
    
    def _format_doctor_brief(self, doctor):
        """Format doctor info for list display"""
        return {
            'id': doctor.id,
            'name': doctor.full_name,
            'specialization': doctor.specialization or 'General Medicine',
            'rating': doctor.average_rating or 0,
            'profile_picture': doctor.profile_picture_url
        }
    
    def _handle_appointment_query(self, message, user):
        """Handle appointment queries"""
        if user:
            if user.is_patient():
                # Get patient's upcoming appointments
                patient = Patient.query.filter_by(user_id=user.id).first()
                if patient:
                    appointments = Appointment.query.filter(
                        Appointment.patient_id == patient.id,
                        Appointment.appointment_date >= datetime.now().date(),
                        Appointment.status.in_(['scheduled', 'confirmed'])
                    ).order_by(Appointment.appointment_date).limit(5).all()
                    
                    if appointments:
                        return {
                            'type': 'appointment_list',
                            'message': "Here are your upcoming appointments:",
                            'appointments': [apt.to_dict() for apt in appointments],
                            'action': {
                                'type': 'link',
                                'text': 'Book New Appointment',
                                'url': '/appointment/book'
                            }
                        }
            
            elif user.is_doctor():
                # Get doctor's today's appointments
                appointments = Appointment.query.filter(
                    Appointment.doctor_id == user.id,
                    Appointment.appointment_date == datetime.now().date(),
                    Appointment.status.in_(['scheduled', 'confirmed'])
                ).order_by(Appointment.appointment_time).all()
                
                return {
                    'type': 'appointment_list',
                    'message': f"You have {len(appointments)} appointments today:",
                    'appointments': [apt.to_dict() for apt in appointments]
                }
        
        return {
            'type': 'text',
            'message': "To book an appointment:\n\n1. Browse our doctors\n2. Select your preferred doctor\n3. Choose a date and time\n4. Confirm your booking\n\nWould you like me to show you available doctors?",
            'action': {
                'type': 'link',
                'text': 'Book Appointment',
                'url': '/appointment/book'
            },
            'suggestions': ['Show doctors', 'View departments']
        }
    
    def _handle_doctor_stats(self, user):
        """Handle doctor's patient statistics query"""
        total_patients = db.session.query(
            db.func.count(db.distinct(Prescription.patient_id))
        ).filter(Prescription.doctor_id == user.id).scalar() or 0
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_patients = db.session.query(
            db.func.count(db.distinct(Appointment.patient_id))
        ).filter(
            Appointment.doctor_id == user.id,
            Appointment.created_at >= thirty_days_ago
        ).scalar() or 0
        
        today_appointments = Appointment.query.filter(
            Appointment.doctor_id == user.id,
            Appointment.appointment_date == datetime.now().date(),
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count()
        
        return {
            'type': 'statistics',
            'message': "Here are your patient statistics:",
            'stats': {
                'total_patients': total_patients,
                'active_patients': active_patients,
                'today_appointments': today_appointments
            }
        }
    
    def _handle_department_query(self):
        """Handle department queries"""
        departments = self.get_departments()
        
        return {
            'type': 'department_list',
            'message': "Our hospital has the following departments:",
            'departments': departments
        }
    
    def get_departments(self):
        """Get list of departments with doctor count"""
        dept_data = db.session.query(
            User.department,
            db.func.count(User.id).label('doctor_count')
        ).filter(
            User.role == 'doctor',
            User.is_active == True,
            User.department.isnot(None)
        ).group_by(User.department).all()
        
        if dept_data:
            return [{'name': dept, 'doctors': count} for dept, count in dept_data]
        
        # Return default departments if none found
        return [{'name': dept, 'doctors': 0} for dept in self.hospital_info.get('departments', [])]
    
    def get_doctors(self, specialty='', department=''):
        """Get list of doctors optionally filtered"""
        query = User.query.filter_by(role='doctor', is_active=True)
        
        if specialty:
            query = query.filter(User.specialization.ilike(f'%{specialty}%'))
        if department:
            query = query.filter(User.department.ilike(f'%{department}%'))
        
        doctors = query.limit(20).all()
        return [self._format_doctor_brief(d) for d in doctors]
    
    def _handle_hospital_info(self):
        """Handle hospital information query"""
        return {
            'type': 'hospital_info',
            'message': f"Welcome to {self.hospital_info['name']}!",
            'info': {
                'name': self.hospital_info['name'],
                'address': self.hospital_info['address'],
                'phone': self.hospital_info['phone'],
                'email': self.hospital_info.get('email', ''),
                'emergency_phone': self.hospital_info.get('emergency_phone', ''),
                'working_hours': self.hospital_info.get('working_hours', ''),
                'departments': self.hospital_info.get('departments', [])
            }
        }
    
    def _get_default_response(self):
        """Get default response for unrecognized queries"""
        return """I'm not sure I understand. I can help you with:

• 🏥 Hospital information
• 👨‍⚕️ Finding doctors
• 📅 Booking appointments
• 🏢 Department information
• 📞 Contact details
• 🕐 Working hours

What would you like to know?"""
    
    def _get_suggestions(self, user=None):
        """Get contextual suggestions"""
        suggestions = [
            "Find a doctor",
            "Hospital timings",
            "Book appointment",
            "View departments"
        ]
        
        if user:
            if user.is_patient():
                suggestions = ["My appointments", "Find a doctor", "Book appointment"]
            elif user.is_doctor():
                suggestions = ["Today's schedule", "My patient stats"]
        
        return suggestions