"""
Notification Service - Email, SMS, and Push notifications
"""

from datetime import datetime
from flask import current_app, render_template_string
from flask_mail import Message
from app import db, mail
import threading

class NotificationService:
    """Service for sending notifications"""
    
    # Email Templates
    EMAIL_TEMPLATES = {
        'appointment_confirmation': {
            'subject': 'Appointment Confirmed - Smart Hospital',
            'template': '''
                <h2>Appointment Confirmed</h2>
                <p>Dear {{ patient_name }},</p>
                <p>Your appointment has been confirmed:</p>
                <ul>
                    <li><strong>Doctor:</strong> Dr. {{ doctor_name }}</li>
                    <li><strong>Date:</strong> {{ appointment_date }}</li>
                    <li><strong>Time:</strong> {{ appointment_time }}</li>
                    <li><strong>Type:</strong> {{ appointment_type }}</li>
                </ul>
                <p>Appointment #: {{ appointment_number }}</p>
                {% if appointment_type == 'video' %}
                <p>You will receive a link to join the video consultation before your appointment.</p>
                {% endif %}
                <p>Thank you for choosing Smart Hospital!</p>
            '''
        },
        # Add to EMAIL_TEMPLATES dictionary in NotificationService class

'new_appointment_request': {
    'subject': '🗓️ New Appointment Request - Smart Hospital',
    'template': '''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center;">
                <h1>🗓️ New Appointment Request</h1>
            </div>
            <div style="padding: 20px; background: #f8f9fa;">
                <p>Dear Dr. <strong>{{ doctor_name }}</strong>,</p>
                <p>You have received a new appointment request:</p>
                
                <div style="background: white; border-left: 4px solid #667eea; padding: 15px; margin: 15px 0;">
                    <p><strong>👤 Patient:</strong> {{ patient_name }}</p>
                    <p><strong>📅 Date:</strong> {{ appointment_date }}</p>
                    <p><strong>🕐 Time:</strong> {{ appointment_time }}</p>
                    <p><strong>📋 Type:</strong> {{ appointment_type }}</p>
                    <p><strong>💬 Reason:</strong> {{ reason }}</p>
                    <p><strong>🔢 Appointment #:</strong> {{ appointment_number }}</p>
                </div>
                
                <p>Please log in to your dashboard to confirm or manage this appointment.</p>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="#" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Appointments
                    </a>
                </div>
            </div>
            <div style="background: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                Smart Hospital Platform
            </div>
        </div>
    '''
},
        'appointment_reminder': {
            'subject': 'Appointment Reminder - Smart Hospital',
            'template': '''
                <h2>Appointment Reminder</h2>
                <p>Dear {{ patient_name }},</p>
                <p>This is a reminder for your upcoming appointment:</p>
                <ul>
                    <li><strong>Doctor:</strong> Dr. {{ doctor_name }}</li>
                    <li><strong>Date:</strong> {{ appointment_date }}</li>
                    <li><strong>Time:</strong> {{ appointment_time }}</li>
                </ul>
                {% if appointment_type == 'video' %}
                <p><a href="{{ video_link }}">Click here to join your video consultation</a></p>
                {% else %}
                <p>Please arrive 15 minutes before your appointment time.</p>
                {% endif %}
            '''
        },
        'prescription_ready': {
            'subject': 'Your Prescription is Ready - Smart Hospital',
            'template': '''
                <h2>Prescription Ready</h2>
                <p>Dear {{ patient_name }},</p>
                <p>Your prescription ({{ prescription_id }}) has been signed and is ready.</p>
                <p>You can collect your medicines from our pharmacy.</p>
                <p>Prescribed by: Dr. {{ doctor_name }}</p>
            '''
        },
        'video_call_starting': {
            'subject': 'Your Video Consultation is Starting - Smart Hospital',
            'template': '''
                <h2>Video Consultation Starting</h2>
                <p>Dear {{ patient_name }},</p>
                <p>Dr. {{ doctor_name }} is ready for your video consultation.</p>
                <p><a href="{{ video_link }}" style="background: #4a90d9; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Join Video Call</a></p>
                <p>If the button doesn't work, copy this link: {{ video_link }}</p>
            '''
        },
        'referral_received': {
            'subject': 'New Patient Referral - Smart Hospital',
            'template': '''
                <h2>New Patient Referral</h2>
                <p>Dear Dr. {{ doctor_name }},</p>
                <p>You have received a new patient referral:</p>
                <ul>
                    <li><strong>Patient:</strong> {{ patient_name }}</li>
                    <li><strong>Referred by:</strong> Dr. {{ referring_doctor }}</li>
                    <li><strong>Reason:</strong> {{ referral_reason }}</li>
                    <li><strong>Urgency:</strong> {{ urgency }}</li>
                </ul>
                <p>Please review and respond to this referral.</p>
            '''
        },
        # Add to EMAIL_TEMPLATES dictionary in NotificationService class
'new_appointment_request': {
    'subject': 'New Appointment Request - Smart Hospital',
    'template': '''
        <h2>New Appointment Request</h2>
        <p>Dear Dr. {{ doctor_name }},</p>
        <p>You have a new appointment request:</p>
        <ul>
            <li><strong>Patient:</strong> {{ patient_name }}</li>
            <li><strong>Date:</strong> {{ appointment_date }}</li>
            <li><strong>Time:</strong> {{ appointment_time }}</li>
            <li><strong>Type:</strong> {{ appointment_type }}</li>
            <li><strong>Reason:</strong> {{ reason }}</li>
        </ul>
        <p>Appointment #: {{ appointment_number }}</p>
        <p>Please login to confirm or reschedule this appointment.</p>
        <p><a href="{{ url_for('doctor.appointments', _external=True) }}" 
              style="background: #4a90d9; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
              View Appointments
        </a></p>
    '''
},


    }
    
    @staticmethod
    def send_email(to_email, template_name, context, async_send=True):
        """
        Send email using template
        
        Args:
            to_email: Recipient email
            template_name: Name of email template
            context: Template context dictionary
            async_send: Send asynchronously
            
        Returns:
            bool: Success status
        """
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.warning("Email not configured, skipping send")
            return False
        
        template_data = NotificationService.EMAIL_TEMPLATES.get(template_name)
        if not template_data:
            current_app.logger.error(f"Email template not found: {template_name}")
            return False
        
        try:
            subject = template_data['subject']
            html_body = render_template_string(template_data['template'], **context)
            
            msg = Message(
                subject=subject,
                recipients=[to_email],
                html=html_body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            if async_send:
                # Send in background thread
                thread = threading.Thread(
                    target=NotificationService._send_async_email,
                    args=(current_app._get_current_object(), msg)
                )
                thread.start()
            else:
                mail.send(msg)
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def _send_async_email(app, msg):
        """Send email in background thread"""
        with app.app_context():
            try:
                mail.send(msg)
            except Exception as e:
                app.logger.error(f"Async email error: {str(e)}")
    
    @staticmethod
    def send_appointment_confirmation(appointment):
        """Send appointment confirmation email"""
        if not appointment.patient or not appointment.patient.email:
            return False
        
        context = {
            'patient_name': appointment.patient.full_name,
            'doctor_name': appointment.doctor_user.full_name if appointment.doctor_user else 'N/A',
            'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
            'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            'appointment_type': 'Video Consultation' if appointment.appointment_type == 'video' else 'In-Person Visit',
            'appointment_number': appointment.appointment_number
        }
        
        return NotificationService.send_email(
            appointment.patient.email,
            'appointment_confirmation',
            context
        )
    
    @staticmethod
    def send_appointment_reminder(appointment, video_link=None):
        """Send appointment reminder email"""
        if not appointment.patient or not appointment.patient.email:
            return False
        
        context = {
            'patient_name': appointment.patient.full_name,
            'doctor_name': appointment.doctor_user.full_name if appointment.doctor_user else 'N/A',
            'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
            'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            'appointment_type': appointment.appointment_type,
            'video_link': video_link
        }
        
        return NotificationService.send_email(
            appointment.patient.email,
            'appointment_reminder',
            context
        )
    
    @staticmethod
    def send_video_call_notification(appointment, video_link):
        """Send video call starting notification"""
        if not appointment.patient or not appointment.patient.email:
            return False
        
        context = {
            'patient_name': appointment.patient.full_name,
            'doctor_name': appointment.doctor_user.full_name if appointment.doctor_user else 'N/A',
            'video_link': video_link
        }
        
        return NotificationService.send_email(
            appointment.patient.email,
            'video_call_starting',
            context
        )
    
    @staticmethod
    def send_prescription_notification(prescription):
        """Send prescription ready notification"""
        if not prescription.patient or not prescription.patient.email:
            return False
        
        context = {
            'patient_name': prescription.patient.full_name,
            'prescription_id': prescription.prescription_id,
            'doctor_name': prescription.doctor.full_name if prescription.doctor else 'N/A'
        }
        
        return NotificationService.send_email(
            prescription.patient.email,
            'prescription_ready',
            context
        )
    
    @staticmethod
    def send_referral_notification(referral):
        """Send referral notification to referred doctor"""
        referred_doctor = referral.referred_to_doctor
        if not referred_doctor or not referred_doctor.email:
            return False
        
        context = {
            'doctor_name': referred_doctor.full_name,
            'patient_name': referral.patient.full_name if referral.patient else 'N/A',
            'referring_doctor': referral.referring_doctor.full_name if referral.referring_doctor else 'N/A',
            'referral_reason': referral.reason,
            'urgency': referral.urgency.title()
        }
        
        return NotificationService.send_email(
            referred_doctor.email,
            'referral_received',
            context
        )
    
    @staticmethod
    def send_sms(phone_number, message):
        """
        Send SMS notification
        
        Args:
            phone_number: Recipient phone number
            message: SMS message text
            
        Returns:
            bool: Success status
        """
        # Placeholder for SMS integration
        # Integrate with Twilio, AWS SNS, or other SMS provider
        current_app.logger.info(f"SMS to {phone_number}: {message}")
        return True
    
    @staticmethod
    def send_push_notification(user_id, title, body, data=None):
        """
        Send push notification
        
        Args:
            user_id: User ID
            title: Notification title
            body: Notification body
            data: Additional data payload
            
        Returns:
            bool: Success status
        """
        # Placeholder for push notification integration
        # Integrate with Firebase Cloud Messaging or similar
        current_app.logger.info(f"Push to user {user_id}: {title} - {body}")
        return True