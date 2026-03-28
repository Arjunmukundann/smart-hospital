"""
Reminder Service - Email and SMS notifications for medicine reminders
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, time
from typing import List, Dict, Optional
import requests
import logging
from flask import current_app, render_template_string

logger = logging.getLogger('reminder_service')

class ReminderService:
    """Service for sending medicine reminders via Email and SMS"""
    
    def __init__(self, app=None):
        self.app = app
        self.email_configured = False
        self.sms_configured = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Check email configuration
        mail_user = app.config.get('MAIL_USERNAME')
        mail_pass = app.config.get('MAIL_PASSWORD')
        
        if mail_user and mail_pass:
            self.email_configured = True
            logger.info(f"✅ Email configured for: {mail_user}")
            print(f"✅ Email reminders configured for: {mail_user}")
        else:
            logger.warning("⚠️ Email not configured")
            print("⚠️ Email not configured - add MAIL_USERNAME and MAIL_PASSWORD to .env")
            if not mail_user:
                print("   Missing: MAIL_USERNAME")
            if not mail_pass:
                print("   Missing: MAIL_PASSWORD")
        
        # Check SMS configuration
        if app.config.get('TWILIO_ACCOUNT_SID') and app.config.get('TWILIO_AUTH_TOKEN'):
            self.sms_configured = True
            self.sms_provider = 'twilio'
            print("✅ SMS reminders configured (Twilio)")
        elif app.config.get('FAST2SMS_API_KEY'):
            self.sms_configured = True
            self.sms_provider = 'fast2sms'
            print("✅ SMS reminders configured (Fast2SMS)")
        else:
            print("⚠️ SMS not configured - add Twilio or Fast2SMS credentials to .env")
    
    # ==================== EMAIL METHODS ====================
    
    def send_email(self, to_email: str, subject: str, html_content: str, 
                   text_content: str = None) -> Dict:
        """Send an email"""
        if not self.email_configured:
            return {'success': False, 'error': 'Email not configured. Check MAIL_USERNAME and MAIL_PASSWORD in .env'}
        
        try:
            # Get config - handle both app context and stored app
            if self.app:
                config = self.app.config
            else:
                from flask import current_app
                config = current_app.config
            
            # Validate required config
            mail_server = config.get('MAIL_SERVER', 'smtp.gmail.com')
            mail_port = config.get('MAIL_PORT', 587)
            mail_username = config.get('MAIL_USERNAME')
            mail_password = config.get('MAIL_PASSWORD')
            mail_sender = config.get('MAIL_DEFAULT_SENDER') or mail_username
            
            if not all([mail_username, mail_password]):
                return {'success': False, 'error': 'Email credentials not configured'}
            
            logger.info(f"📧 Sending email to {to_email} via {mail_server}:{mail_port}")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = mail_sender
            msg['To'] = to_email
            
            # Add plain text version
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML version
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect and send
            logger.info(f"🔌 Connecting to {mail_server}:{mail_port}...")
            
            if config.get('MAIL_USE_SSL'):
                server = smtplib.SMTP_SSL(mail_server, mail_port)
            else:
                server = smtplib.SMTP(mail_server, mail_port)
                if config.get('MAIL_USE_TLS', True):
                    server.starttls()
            
            logger.info(f"🔐 Logging in as {mail_username}...")
            server.login(mail_username, mail_password)
            
            logger.info(f"📤 Sending email...")
            server.sendmail(mail_sender, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            return {'success': True, 'message': 'Email sent successfully'}
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Authentication failed. For Gmail, use App Password. Error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Email error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': error_msg}
    
    def send_medicine_reminder_email(self, to_email: str, patient_name: str,
                                     medicines: List[Dict], timing: str) -> Dict:
        """Send medicine reminder email"""
        
        subject = f"⏰ Medicine Reminder - {timing.title()} Dose"
        
        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .header .emoji {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                .content {{
                    padding: 30px;
                }}
                .greeting {{
                    font-size: 18px;
                    color: #333;
                    margin-bottom: 20px;
                }}
                .timing-badge {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}
                .medicine-card {{
                    background: #f8f9fa;
                    border-left: 4px solid #667eea;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 0 8px 8px 0;
                }}
                .medicine-name {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 5px;
                }}
                .medicine-details {{
                    color: #666;
                    font-size: 14px;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="emoji">💊</div>
                    <h1>Medicine Reminder</h1>
                </div>
                <div class="content">
                    <p class="greeting">Hello <strong>{patient_name}</strong>! 👋</p>
                    
                    <div class="timing-badge">
                        {"☀️" if timing == "morning" else "🍽️" if timing == "afternoon" else "🌅" if timing == "evening" else "🌙"} 
                        {timing.title()} Medicines
                    </div>
                    
                    <p>It's time to take your medicines:</p>
                    
                    {"".join([f'''
                    <div class="medicine-card">
                        <div class="medicine-name">💊 {med['name']}</div>
                        <div class="medicine-details">
                            <strong>Dosage:</strong> {med.get('dosage', 'As prescribed')} | 
                            <strong>Take:</strong> {med.get('timing', 'As directed')}
                        </div>
                    </div>
                    ''' for med in medicines])}
                    
                </div>
                <div class="footer">
                    <p>This is an automated reminder from <strong>Smart Hospital</strong></p>
                </div>
            </div>
        </body>
        </html>
    
        """
        
        # Plain text version
        text_content = f"""
        Medicine Reminder - {timing.title()} Dose
        
        Hello {patient_name}!
        
        It's time to take your {timing} medicines:
        
        {chr(10).join([f"• {med['name']} - {med.get('dosage', 'As prescribed')}" for med in medicines])}
        
        Please take your medicines on time for better health!
        
        - Smart Hospital Platform
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    # ==================== SMS METHODS ====================
    
    def send_sms(self, to_phone: str, message: str) -> Dict:
        """Send an SMS"""
        if not self.sms_configured:
            return {'success': False, 'error': 'SMS not configured'}
        
        # Clean phone number
        to_phone = self._clean_phone_number(to_phone)
        
        if self.sms_provider == 'twilio':
            return self._send_sms_twilio(to_phone, message)
        elif self.sms_provider == 'fast2sms':
            return self._send_sms_fast2sms(to_phone, message)
        else:
            return {'success': False, 'error': 'No SMS provider configured'}
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number"""
        # Remove spaces, dashes, and other characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Add country code if not present (assuming India +91)
        if len(phone) == 10:
            phone = '91' + phone
        
        return phone
    
    def _send_sms_twilio(self, to_phone: str, message: str) -> Dict:
        """Send SMS using Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(
                current_app.config['TWILIO_ACCOUNT_SID'],
                current_app.config['TWILIO_AUTH_TOKEN']
            )
            
            # Ensure phone has + prefix
            if not to_phone.startswith('+'):
                to_phone = '+' + to_phone
            
            sms = client.messages.create(
                body=message,
                from_=current_app.config['TWILIO_PHONE_NUMBER'],
                to=to_phone
            )
            
            return {
                'success': True,
                'message': 'SMS sent successfully',
                'sid': sms.sid
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _send_sms_fast2sms(self, to_phone: str, message: str) -> Dict:
        """Send SMS using Fast2SMS (India)"""
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            
            # Remove country code for Fast2SMS
            if to_phone.startswith('91'):
                to_phone = to_phone[2:]
            
            payload = {
                "route": "q",  # Quick SMS
                "message": message,
                "language": "english",
                "flash": 0,
                "numbers": to_phone
            }
            
            headers = {
                "authorization": current_app.config['FAST2SMS_API_KEY'],
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            
            if result.get('return'):
                return {'success': True, 'message': 'SMS sent successfully'}
            else:
                return {'success': False, 'error': result.get('message', 'Unknown error')}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_medicine_reminder_sms(self, to_phone: str, patient_name: str,
                                   medicines: List[Dict], timing: str) -> Dict:
        """Send medicine reminder SMS"""
        
        # Create short message (SMS has character limits)
        timing_emoji = {
            'morning': '☀️',
            'afternoon': '🍽️',
            'evening': '🌅',
            'night': '🌙'
        }
        
        medicine_list = ', '.join([m['name'] for m in medicines[:3]])
        if len(medicines) > 3:
            medicine_list += f' +{len(medicines) - 3} more'
        
        message = f"""
🏥 Smart Hospital Reminder

Hi {patient_name}!

{timing_emoji.get(timing, '⏰')} Time for your {timing} medicines:
💊 {medicine_list}

Take care of your health! 🌟
        """.strip()
        
        return self.send_sms(to_phone, message)


# Create singleton instance
reminder_service = ReminderService()