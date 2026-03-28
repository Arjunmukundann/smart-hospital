"""
Scheduler Service - Sends reminders at scheduled times
"""

from datetime import datetime, time
from typing import Optional
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('reminder_scheduler')


def init_scheduler(app):
    """
    Initialize the reminder scheduler with Flask app
    Called from app/__init__.py or run.py
    """
    # Check if scheduler should be enabled
    if not app.config.get('REMINDER_ENABLED', True):
        logger.warning("⚠️ Reminder scheduler is disabled in config")
        return None
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
        
        scheduler = BackgroundScheduler()
        
        # Add event listeners for debugging
        def job_listener(event):
            if event.exception:
                logger.error(f"❌ Job {event.job_id} failed: {event.exception}")
            else:
                logger.info(f"✅ Job {event.job_id} executed successfully")
        
        scheduler.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
        
        # Get reminder times from config
        reminder_times = app.config.get('REMINDER_TIMES', {
            'morning': '08:00',
            'afternoon': '13:00',
            'evening': '18:00',
            'night': '21:00'
        })
        
        # Parse times and schedule jobs
        for timing, time_str in reminder_times.items():
            try:
                hour, minute = map(int, time_str.split(':'))
                scheduler.add_job(
                    func=send_scheduled_reminders_wrapper,
                    args=[app, timing],
                    trigger='cron',
                    hour=hour,
                    minute=minute,
                    id=f'reminder_{timing}',
                    replace_existing=True,
                    misfire_grace_time=3600  # 1 hour grace period
                )
                logger.info(f"✅ Scheduled {timing} reminders at {time_str}")
            except Exception as e:
                logger.error(f"❌ Failed to schedule {timing} reminders: {e}")
        
        # Add a test job that runs every minute (for debugging - remove in production)
        # scheduler.add_job(
        #     func=lambda: logger.info("🔄 Scheduler is alive..."),
        #     trigger='interval',
        #     minutes=1,
        #     id='heartbeat'
        # )
        
        scheduler.start()
        logger.info("✅ Reminder scheduler started successfully")
        
        # Store scheduler in app for later access
        app.scheduler = scheduler
        
        return scheduler
        
    except ImportError:
        logger.error("⚠️ APScheduler not installed. Run: pip install apscheduler")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_scheduled_reminders_wrapper(app, timing):
    """Wrapper to run reminders within app context"""
    logger.info(f"🔔 Triggering {timing} reminders...")
    with app.app_context():
        try:
            count = send_scheduled_reminders(timing)
            logger.info(f"✅ Sent {count} {timing} reminders")
        except Exception as e:
            logger.error(f"❌ Error in {timing} reminders: {e}")
            import traceback
            traceback.print_exc()


def send_scheduled_reminders(timing='morning'):
    """
    Send reminders for a specific timing
    
    Args:
        timing: 'morning', 'afternoon', 'evening', 'night'
    """
    from app import db
    from app.models import Patient, Prescription
    
    logger.info(f"[{datetime.now()}] Starting {timing} reminders...")
    
    try:
        from app.models.reminder import ReminderSetting, ReminderLog
        has_reminder_models = True
        logger.info("✅ Using ReminderSetting model")
    except ImportError:
        has_reminder_models = False
        logger.warning("⚠️ Reminder models not found. Using basic reminder logic.")
    
    sent_count = 0
    failed_count = 0
    
    try:
        if has_reminder_models:
            # Use ReminderSetting model
            settings = ReminderSetting.query.filter_by(is_active=True).all()
            logger.info(f"📋 Found {len(settings)} active reminder settings")
            
            for setting in settings:
                patient = setting.patient
                if not patient:
                    logger.warning(f"⚠️ No patient for setting {setting.id}")
                    continue
                
                logger.info(f"📤 Processing reminders for patient: {patient.full_name}")
                result = send_patient_reminder(patient, timing, setting)
                
                if result:
                    if result.get('success'):
                        sent_count += 1
                        logger.info(f"✅ Sent {result.get('type', 'reminder')} to {patient.full_name}")
                    else:
                        failed_count += 1
                        logger.error(f"❌ Failed for {patient.full_name}: {result.get('error')}")
                    
                    # Log the reminder
                    log = ReminderLog(
                        patient_id=patient.id,
                        reminder_type=result.get('type', 'email'),
                        timing=timing,
                        medicines_included=json.dumps(result.get('medicines', [])),
                        recipient=setting.reminder_email or setting.reminder_phone,
                        status='sent' if result.get('success') else 'failed',
                        error_message=result.get('error'),
                        sent_at=datetime.utcnow() if result.get('success') else None
                    )
                    db.session.add(log)
                else:
                    logger.info(f"⏭️ No medicines for {patient.full_name} at {timing}")
        else:
            # Basic approach without ReminderSetting
            patients = Patient.query.filter(Patient.email.isnot(None)).all()
            logger.info(f"📋 Found {len(patients)} patients with emails")
            
            for patient in patients:
                if patient.email and patient.email != 'Not Provided':
                    logger.info(f"📤 Processing: {patient.full_name} ({patient.email})")
                    result = send_patient_reminder(patient, timing)
                    if result and result.get('success'):
                        sent_count += 1
                        logger.info(f"✅ Sent to {patient.full_name}")
                    elif result:
                        failed_count += 1
                        logger.error(f"❌ Failed: {result.get('error')}")
        
        db.session.commit()
        logger.info(f"[{datetime.now()}] Completed: {sent_count} sent, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"❌ Error sending reminders: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
    
    return sent_count


def send_patient_reminder(patient, timing, setting=None):
    """
    Send reminder to a specific patient
    """
    from app.models import Prescription
    
    logger.info(f"  🔍 Checking prescriptions for patient {patient.id}")
    
    # Get active prescriptions
    prescriptions = Prescription.query.filter_by(
        patient_id=patient.id,
        status='active'
    ).all()
    
    logger.info(f"  📋 Found {len(prescriptions)} active prescriptions")
    
    if not prescriptions:
        return None
    
    # Get medicines for this timing
    medicines_to_remind = []
    
    for rx in prescriptions:
        # Check if medicines relationship exists
        if hasattr(rx, 'medicines'):
            try:
                meds = rx.medicines.all() if hasattr(rx.medicines, 'all') else rx.medicines
            except:
                meds = []
        else:
            logger.warning(f"  ⚠️ Prescription {rx.id} has no medicines relationship")
            continue
        
        for med in meds:
            should_remind = False
            
            # Check timing flags
            if timing == 'morning' and getattr(med, 'morning', False):
                should_remind = True
            elif timing == 'afternoon' and getattr(med, 'afternoon', False):
                should_remind = True
            elif timing == 'evening' and getattr(med, 'evening', False):
                should_remind = True
            elif timing == 'night' and getattr(med, 'night', False):
                should_remind = True
            
            # Fallback: check timing text
            if not should_remind:
                med_timing = getattr(med, 'timing', '') or ''
                if timing.lower() in med_timing.lower():
                    should_remind = True
            
            # Fallback: check frequency
            if not should_remind:
                freq = getattr(med, 'frequency', '') or ''
                freq_lower = freq.lower()
                if 'twice' in freq_lower and timing in ['morning', 'night']:
                    should_remind = True
                elif 'three' in freq_lower and timing in ['morning', 'afternoon', 'night']:
                    should_remind = True
                elif 'four' in freq_lower or 'daily' in freq_lower:
                    should_remind = True
            
            if should_remind:
                med_name = getattr(med, 'medicine_name', None) or getattr(med, 'name', 'Unknown')
                medicines_to_remind.append({
                    'name': med_name,
                    'dosage': getattr(med, 'dosage', 'As prescribed'),
                    'timing': getattr(med, 'timing', 'As directed') or 'As directed',
                    'instructions': getattr(med, 'instructions', '') or ''
                })
    
    logger.info(f"  💊 {len(medicines_to_remind)} medicines to remind for {timing}")
    
    if not medicines_to_remind:
        return None
    
    # Send reminder
    result = {'medicines': [m['name'] for m in medicines_to_remind]}
    
    try:
        from app.services.reminder_service import reminder_service
        
        # Determine email/phone
        if setting:
            email = setting.reminder_email if setting.email_enabled else None
            phone = setting.reminder_phone if setting.sms_enabled else None
        else:
            email = getattr(patient, 'email', None)
            phone = getattr(patient, 'phone', None)
            if phone == 'Not Provided':
                phone = None
        
        logger.info(f"  📧 Email: {email}, 📱 Phone: {phone}")
        
        # Get patient name
        patient_name = getattr(patient, 'full_name', None) or \
                       getattr(patient, 'name', None) or \
                       f"Patient {patient.id}"
        
        # Send email
        if email:
            logger.info(f"  📤 Sending email to {email}...")
            email_result = reminder_service.send_medicine_reminder_email(
                to_email=email,
                patient_name=patient_name,
                medicines=medicines_to_remind,
                timing=timing
            )
            result['success'] = email_result.get('success', False)
            result['error'] = email_result.get('error')
            result['type'] = 'email'
            
            if result['success']:
                logger.info(f"  ✅ Email sent successfully!")
            else:
                logger.error(f"  ❌ Email failed: {result['error']}")
        
        # Send SMS (if email not available or failed)
        elif phone:
            logger.info(f"  📤 Sending SMS to {phone}...")
            sms_result = reminder_service.send_medicine_reminder_sms(
                to_phone=phone,
                patient_name=patient_name,
                medicines=medicines_to_remind,
                timing=timing
            )
            result['success'] = sms_result.get('success', False)
            result['error'] = sms_result.get('error')
            result['type'] = 'sms'
        else:
            result['success'] = False
            result['error'] = 'No email or phone available'
            logger.warning(f"  ⚠️ No contact info for patient")
        
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        logger.error(f"  ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    return result


# Manual trigger function for testing
def trigger_reminder_now(timing='morning'):
    """
    Manually trigger reminders (for testing)
    
    Usage from Flask shell:
        >>> from app.services.scheduler import trigger_reminder_now
        >>> trigger_reminder_now('morning')
    """
    from flask import current_app
    
    try:
        app = current_app._get_current_object()
    except RuntimeError:
        from app import create_app
        app = create_app()
    
    with app.app_context():
        return send_scheduled_reminders(timing)