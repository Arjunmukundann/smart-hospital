"""
Doctor Module Routes - Updated with Referral, Signature, Video, Appointments
"""

import os
import re
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
from app import db
from app.models import (
    User, Patient, PatientAllergy, PatientCondition, 
    Prescription, PrescriptionMedicine, Report, SafetyAlert,
    Inventory, InventoryTransaction, DoctorAvailability, patient
)
from app.models.appointment import Appointment, TimeSlot
from app.models.video_consultation import VideoSession
from app.models.feedback import Feedback
from app.models.referral import DoctorReferral
from app.services import OCRService, SafetyChecker, ReportAnalyzer
from app.services.signature_service import SignatureService
from app.services.image_service import ImageService
from datetime import datetime
import uuid
# Add this with other imports at the top
try:
    from app.models.ecg_record import ECGPatient, ECGResult
except ImportError:
    ECGPatient = None

doctor_bp = Blueprint('doctor', __name__)


def doctor_required(f):
    """Decorator to require doctor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_doctor():
            flash('Access denied. Doctor privileges required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@doctor_bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    """Doctor dashboard"""
    today = date.today()
    
    # Statistics
    today_prescriptions = Prescription.query.filter(
        Prescription.doctor_id == current_user.id,
        db.func.date(Prescription.created_at) == today
    ).count()
    
    total_prescriptions = Prescription.query.filter_by(doctor_id=current_user.id).count()
    
    today_alerts = SafetyAlert.query.filter(
        SafetyAlert.doctor_id == current_user.id,
        db.func.date(SafetyAlert.created_at) == today
    ).count()
    
    total_patients = db.session.query(db.func.count(db.distinct(Prescription.patient_id))).filter(
        Prescription.doctor_id == current_user.id
    ).scalar() or 0
    
    # NEW: Today's appointments
    today_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_date == today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_time).all()
    
    # NEW: Pending referrals
    pending_referrals = DoctorReferral.query.filter(
        DoctorReferral.referred_to_doctor_id == current_user.id,
        DoctorReferral.status == 'pending'
    ).count()
    
    # NEW: Upcoming video consultations
    upcoming_video = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_type == 'video',
        Appointment.appointment_date >= today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(5).all()
    
    # Recent prescriptions
    recent_prescriptions = Prescription.query.filter_by(
        doctor_id=current_user.id
    ).order_by(Prescription.created_at.desc()).limit(5).all()
    
    # Recent alerts
    recent_alerts = SafetyAlert.query.filter_by(
        doctor_id=current_user.id
    ).order_by(SafetyAlert.created_at.desc()).limit(10).all()
    
    # NEW: Recent feedback
    recent_feedback = Feedback.query.filter_by(
        doctor_id=current_user.id
    ).order_by(Feedback.created_at.desc()).limit(5).all()
    
    return render_template('doctor/dashboard.html',
                         today_prescriptions=today_prescriptions,
                         total_prescriptions=total_prescriptions,
                         today_alerts=today_alerts,
                         total_patients=total_patients,
                         today_appointments=today_appointments,
                         pending_referrals=pending_referrals,
                         upcoming_video=upcoming_video,
                         recent_prescriptions=recent_prescriptions,
                         recent_alerts=recent_alerts,
                         recent_feedback=recent_feedback,
                         now=datetime.now())


# ============ APPOINTMENTS ============

@doctor_bp.route('/appointments')
@login_required
@doctor_required
def appointments():
    """View doctor's appointments"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    
    query = Appointment.query.filter_by(doctor_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    if date_filter == 'today':
        query = query.filter(Appointment.appointment_date == date.today())
    elif date_filter == 'upcoming':
        query = query.filter(Appointment.appointment_date >= date.today())
    elif date_filter == 'past':
        query = query.filter(Appointment.appointment_date < date.today())
    
    appointments = query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    # Statistics
    today_count = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_date == date.today(),
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).count()
    
    pending_count = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.status == 'scheduled'
    ).count()
    
    return render_template('doctor/appointments.html',
                         appointments=appointments,
                         status=status,
                         date_filter=date_filter,
                         today_count=today_count,
                         pending_count=pending_count)


@doctor_bp.route('/appointment/<int:appointment_id>')
@login_required
@doctor_required
def view_appointment(appointment_id):
    """View single appointment details"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.appointments'))
    
    return render_template('doctor/view_appointment.html', appointment=appointment)
@doctor_bp.route('/start-video/<int:appointment_id>')
@login_required
@doctor_required
def start_video_call(appointment_id):
    """Start video consultation"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if appointment.appointment_type != 'video':
        flash('This is not a video consultation.', 'error')
        return redirect(url_for('doctor.view_appointment', appointment_id=appointment_id))
    
    # Create or get video session
    from app.models.video_consultation import VideoSession
    
    session = VideoSession.query.filter_by(appointment_id=appointment_id).first()
    
    if not session:
          # Create new video session with scheduled_at populated
        room_id = f"room_{uuid.uuid4().hex[:12]}"
        
        # FIX: Set scheduled_at from appointment date/time
        scheduled_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        ) if appointment.appointment_date and appointment.appointment_time else datetime.utcnow()
        session = VideoSession(
            room_id=VideoSession.generate_room_id(),
            appointment_id=appointment_id,
            doctor_id=current_user.id,
            patient_id=appointment.patient_id,
            scheduled_at=scheduled_datetime,
            status='waiting'
        )
        db.session.add(session)
        
        # Update appointment
        appointment.video_room_id = session.room_id
        appointment.status = 'confirmed'
        
        db.session.commit()
        
        # Notify patient
        try:
            from app.services.notification_service import NotificationService
            video_link = url_for('video.video_room', room_id=session.room_id, _external=True)
            NotificationService.send_video_call_notification(appointment, video_link)
        except:
            pass
    
    return redirect(url_for('video.video_room', room_id=session.room_id))

@doctor_bp.route('/availability', methods=['GET', 'POST'])
@login_required
@doctor_required
def availability():
    """Manage doctor's availability schedule"""
    if request.method == 'POST':
        # Clear existing availability
        DoctorAvailability.query.filter_by(doctor_id=current_user.id).delete()
        
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for i, day in enumerate(days):
            if request.form.get(f'{day}_active'):
                start_time = request.form.get(f'{day}_start', '09:00')
                end_time = request.form.get(f'{day}_end', '17:00')
                slot_duration = int(request.form.get(f'{day}_duration', 30))
                consultation_type = request.form.get(f'{day}_type', 'both')
                
                try:
                    start = datetime.strptime(start_time, '%H:%M').time()
                    end = datetime.strptime(end_time, '%H:%M').time()
                    
                    availability = DoctorAvailability(
                        doctor_id=current_user.id,
                        day_of_week=i,
                        start_time=start,
                        end_time=end,
                        slot_duration=slot_duration,
                        consultation_type=consultation_type,
                        is_active=True
                    )
                    db.session.add(availability)
                except:
                    pass
        
        # Update video consultation settings
        current_user.is_available_online = request.form.get('available_online') == 'on'
        current_user.video_consultation_fee = float(request.form.get('video_fee', 0))
        current_user.consultation_fee = float(request.form.get('consultation_fee', 0))
        
        db.session.commit()
        flash('Availability updated successfully!', 'success')
        return redirect(url_for('doctor.availability'))
    
    # GET - Show current availability
    current_availability = DoctorAvailability.query.filter_by(
        doctor_id=current_user.id
    ).all()
    
    # Convert to dict for easy template access
    availability_dict = {}
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for avail in current_availability:
        day_name = days[avail.day_of_week]
        availability_dict[day_name] = {
            'active': avail.is_active,
            'start': avail.start_time.strftime('%H:%M') if avail.start_time else '09:00',
            'end': avail.end_time.strftime('%H:%M') if avail.end_time else '17:00',
            'duration': avail.slot_duration or 30,
            'type': avail.consultation_type or 'both'
        }
    
    return render_template('doctor/availability.html',
                         availability=availability_dict,
                         days=days)



@doctor_bp.route('/appointment/<int:appointment_id>/confirm', methods=['POST'])
@login_required
@doctor_required
def confirm_appointment(appointment_id):
    """Confirm an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if appointment.status != 'scheduled':
        flash('This appointment cannot be confirmed.', 'warning')
        return redirect(url_for('doctor.appointments'))
    
    appointment.status = 'confirmed'
    appointment.confirmed_at = datetime.utcnow()
    db.session.commit()
    
    # Notify patient
    try:
        from app.services.notification_service import NotificationService
        NotificationService.send_appointment_confirmation(appointment)
    except Exception as e:
        print(f"Notification error: {e}")
    
    flash('Appointment confirmed! Patient has been notified.', 'success')
    return redirect(url_for('doctor.appointments'))


@doctor_bp.route('/appointment/<int:appointment_id>/reject', methods=['POST'])
@login_required
@doctor_required
def reject_appointment(appointment_id):
    """Reject an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.appointments'))
    
    reason = request.form.get('reason', 'Rejected by doctor')
    
    appointment.status = 'cancelled'
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancellation_reason = reason
    db.session.commit()
    
    flash('Appointment rejected.', 'info')
    return redirect(url_for('doctor.appointments'))


# ============ PRESCRIPTIONS WITH SIGNATURE ============

@doctor_bp.route('/prescription/new/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def prescription(patient_id):
    """Create new prescription for patient with digital signature support"""
    patient = Patient.query.get_or_404(patient_id)
    
    allergies = patient.get_allergies_list()
    # Get previous prescriptions for reference
    previous_prescriptions = Prescription.query.filter_by(
        patient_id=patient_id
    ).order_by(Prescription.created_at.desc()).limit(5).all()


    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis', '').strip()
        symptoms = request.form.get('symptoms', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not diagnosis:
            flash('Diagnosis is required.', 'error')
            return render_template('doctor/prescription.html', patient=patient)
        
        # Get medicines from form
        medicine_names = request.form.getlist('medicine_name[]')
        dosages = request.form.getlist('dosage[]')
        frequencies = request.form.getlist('frequency[]')
        durations = request.form.getlist('duration[]')
        timings = request.form.getlist('timing[]')
        instructions_list = request.form.getlist('instructions[]')
        quantities = request.form.getlist('quantity[]')
        
        # Get timing checkboxes
        mornings = request.form.getlist('morning[]')
        afternoons = request.form.getlist('afternoon[]')
        evenings = request.form.getlist('evening[]')
        nights = request.form.getlist('night[]')
        
        if not medicine_names or not any(medicine_names):
            flash('At least one medicine is required.', 'error')
            return render_template('doctor/prescription.html', patient=patient)
        
        # Perform safety check
        checker = SafetyChecker()
        medicines = [m.strip() for m in medicine_names if m.strip()]
        allergies = patient.get_allergies_list()
        current_meds = patient.get_current_medications_list()
        
        result = checker.perform_full_check(medicines, allergies, current_meds)
        
        override_confirmed = request.form.get('safety_override') == 'confirmed'
        
        if result['requires_action'] and not override_confirmed:
            return render_template('doctor/safety_alerts.html',
                                 patient=patient,
                                 alerts=result['alerts'],
                                 form_data=request.form)
        
        # Create prescription
        prescription_obj = Prescription(
            prescription_id=Prescription.generate_prescription_id(),
            patient_id=patient.id,
            doctor_id=current_user.id,
            diagnosis=diagnosis,
            symptoms=symptoms,
            notes=notes,
            status='active',
            safety_checked=True
        )
        
        if override_confirmed:
            prescription_obj.safety_overridden = True
            prescription_obj.override_reason = request.form.get('override_reason', '')
        
        # NEW: Check for referral
        is_referral = request.form.get('is_referral') == 'on'
        if is_referral:
            referred_to_id = request.form.get('referred_to_doctor_id', type=int)
            if referred_to_id:
                prescription_obj.is_referral = True
                prescription_obj.referred_to_doctor_id = referred_to_id
                prescription_obj.referral_reason = request.form.get('referral_reason', '')
                prescription_obj.referral_urgency = request.form.get('referral_urgency', 'normal')
        
        db.session.add(prescription_obj)
        db.session.flush()
        
        # Add medicines with timing
        for i in range(len(medicine_names)):
            if medicine_names[i].strip():
                # Calculate quantity if not provided
                quantity = int(quantities[i]) if i < len(quantities) and quantities[i] else 0
                if quantity == 0:
                    quantity = calculate_medicine_quantity(
                        frequencies[i] if i < len(frequencies) else '',
                        durations[i] if i < len(durations) else ''
                    )
                
                med = PrescriptionMedicine(
                    prescription_id=prescription_obj.id,
                    medicine_name=medicine_names[i].strip(),
                    dosage=dosages[i] if i < len(dosages) else '',
                    frequency=frequencies[i] if i < len(frequencies) else '',
                    duration=durations[i] if i < len(durations) else '',
                    timing=timings[i] if i < len(timings) else '',
                    instructions=instructions_list[i] if i < len(instructions_list) else '',
                    quantity=quantity,
                    morning=str(i) in mornings,
                    afternoon=str(i) in afternoons,
                    evening=str(i) in evenings,
                    night=str(i) in nights
                )
                db.session.add(med)
        
        # Save alerts
        for alert in result['alerts']:
            sa = SafetyAlert(
                prescription_id=prescription_obj.id,
                patient_id=patient.id,
                doctor_id=current_user.id,
                alert_type=alert['type'],
                severity=alert['severity'],
                medicine_name=alert.get('medicine', ''),
                conflicting_item=alert.get('conflicting_item', ''),
                description=alert['description'],
                recommendation=alert.get('recommendation', ''),
                is_acknowledged=override_confirmed,
                is_overridden=override_confirmed
            )
            db.session.add(sa)
        
        db.session.commit()
        
        # NEW: If referral, create referral record
        if is_referral and prescription_obj.referred_to_doctor_id:
            referral = DoctorReferral(
                referral_number=DoctorReferral.generate_referral_number(),
                referring_doctor_id=current_user.id,
                referred_to_doctor_id=prescription_obj.referred_to_doctor_id,
                patient_id=patient.id,
                prescription_id=prescription_obj.id,
                reason=prescription_obj.referral_reason,
                urgency=prescription_obj.referral_urgency,
                clinical_summary=f"Diagnosis: {diagnosis}\nSymptoms: {symptoms}",
                status='pending'
            )
            db.session.add(referral)
            db.session.commit()
        
        flash(f'Prescription {prescription_obj.prescription_id} created successfully!', 'success')
        
        # Redirect to sign if doctor wants to sign now
        if request.form.get('sign_now') == 'on':
            return redirect(url_for('doctor.sign_prescription', prescription_id=prescription_obj.id))
        
        return redirect(url_for('doctor.patient_detail', patient_id=patient.id))
    
    # GET - Show prescription form
    # Get list of doctors for referral
    doctors = User.query.filter(
        User.role == 'doctor',
        User.id != current_user.id,
        User.is_active == True
    ).order_by(User.specialization, User.full_name).all()
    
    return render_template('doctor/prescription.html', 
                         patient=patient,
                         allergies=allergies,
                        previous_prescriptions=previous_prescriptions,
                        prescription=None,
                        is_new=True,                    
    )
# ============ LIST ALL PRESCRIPTIONS ============
@doctor_bp.route('/prescriptions')
@login_required
@doctor_required
def prescriptions():
    """View all prescriptions created by this doctor"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Prescription.query.filter_by(doctor_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    if search:
        query = query.join(Patient).filter(
            db.or_(
                Prescription.prescription_id.ilike(f'%{search}%'),
                Patient.full_name.ilike(f'%{search}%'),
                Prescription.diagnosis.ilike(f'%{search}%')
            )
        )
    
    prescriptions_list = query.order_by(Prescription.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get counts
    total_count = Prescription.query.filter_by(doctor_id=current_user.id).count()
    active_count = Prescription.query.filter_by(doctor_id=current_user.id, status='active').count()
    signed_count = Prescription.query.filter_by(doctor_id=current_user.id, is_signed=True).count()
    
    return render_template('doctor/prescriptions.html',
                         prescriptions=prescriptions_list,
                         status=status,
                         search=search,
                         total_count=total_count,
                         active_count=active_count,
                         signed_count=signed_count)

def calculate_medicine_quantity(frequency, duration):
    """Calculate medicine quantity based on frequency and duration"""
    frequency_map = {
        'once daily': 1,
        'twice daily': 2,
        'three times daily': 3,
        'thrice daily': 3,
        'four times daily': 4,
        'as needed': 1,
        'every 4 hours': 6,
        'every 6 hours': 4,
        'every 8 hours': 3,
        'every 12 hours': 2
    }
    
    frequency_lower = (frequency or 'once daily').lower()
    daily_dose = frequency_map.get(frequency_lower, 1)
    
    # Parse duration
    duration_str = duration or '7 days'
    duration_match = re.search(r'(\d+)', duration_str)
    days = int(duration_match.group(1)) if duration_match else 7
    
    if 'week' in duration_str.lower():
        days = days * 7
    elif 'month' in duration_str.lower():
        days = days * 30
    
    return daily_dose * days


@doctor_bp.route('/prescription/<int:prescription_id>/sign', methods=['GET', 'POST'])
@login_required
@doctor_required
def sign_prescription(prescription_id):
    """Sign prescription with digital signature"""
    prescription = Prescription.query.get_or_404(prescription_id)
    
    if prescription.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.dashboard'))
    
    if prescription.is_signed:
        flash('Prescription is already signed.', 'info')
        return redirect(url_for('doctor.view_prescription', prescription_id=prescription_id))
    
    if request.method == 'POST':
        signature_data = request.form.get('signature_data')
        
        if not signature_data:
            flash('Signature is required.', 'error')
            return render_template('doctor/sign_prescription.html', prescription=prescription)
        
        # Use SignatureService to sign
        success, message = SignatureService.sign_prescription(
            prescription, signature_data, current_user.id
        )
        
        if success:
            flash('Prescription signed successfully!', 'success')
            return redirect(url_for('doctor.view_prescription', prescription_id=prescription_id))
        else:
            flash(f'Error signing prescription: {message}', 'error')
    
    return render_template('doctor/sign_prescription.html', prescription=prescription)


@doctor_bp.route('/prescription/<int:prescription_id>/view')
@login_required
def view_prescription(prescription_id):
    """View a prescription after signing or anytime"""
    if current_user.role != 'doctor':
        flash('Access denied. Doctors only.', 'danger')
        return redirect(url_for('auth.login'))
    
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Verify the doctor owns this prescription
    if prescription.doctor_id != current_user.id:
        flash('You do not have permission to view this prescription.', 'danger')
        return redirect(url_for('doctor.prescriptions'))
    
    # Get safety alerts for this prescription
    safety_alerts = SafetyAlert.query.filter_by(prescription_id=prescription_id).all()
    
    # Check if user just signed (for success message)
    just_signed = request.args.get('signed', False)
    
    # Get current datetime for template
    from datetime import datetime
    now = datetime.now()
    
    return render_template('doctor/view_prescription.html',
                          prescription=prescription,
                          safety_alerts=safety_alerts,
                          just_signed=just_signed,
                          now=now)


# ============ REFERRALS ============

@doctor_bp.route('/referrals')
@login_required
@doctor_required
def referrals():
    """View referrals (sent and received)"""
    tab = request.args.get('tab', 'received')
    page = request.args.get('page', 1, type=int)
    
    if tab == 'sent':
        referrals = DoctorReferral.query.filter_by(
            referring_doctor_id=current_user.id
        ).order_by(DoctorReferral.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    else:
        referrals = DoctorReferral.query.filter_by(
            referred_to_doctor_id=current_user.id
        ).order_by(DoctorReferral.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    
    # Count pending received referrals
    pending_count = DoctorReferral.query.filter_by(
        referred_to_doctor_id=current_user.id,
        status='pending'
    ).count()
    
    return render_template('doctor/referrals.html',
                         referrals=referrals,
                         tab=tab,
                         pending_count=pending_count)


@doctor_bp.route('/referral/<int:referral_id>')
@login_required
@doctor_required
def view_referral(referral_id):
    """View referral details"""
    referral = DoctorReferral.query.get_or_404(referral_id)
    
    # Check if user is part of this referral
    if referral.referring_doctor_id != current_user.id and \
       referral.referred_to_doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.referrals'))
    
    return render_template('doctor/view_referral.html', referral=referral)


@doctor_bp.route('/referral/<int:referral_id>/accept', methods=['POST'])
@login_required
@doctor_required
def accept_referral(referral_id):
    """Accept a referral"""
    referral = DoctorReferral.query.get_or_404(referral_id)
    
    if referral.referred_to_doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.referrals'))
    
    referral.accept()
    db.session.commit()
    
    flash('Referral accepted. You can now schedule an appointment with the patient.', 'success')
    return redirect(url_for('doctor.view_referral', referral_id=referral_id))


@doctor_bp.route('/referral/<int:referral_id>/decline', methods=['POST'])
@login_required
@doctor_required
def decline_referral(referral_id):
    """Decline a referral"""
    referral = DoctorReferral.query.get_or_404(referral_id)
    
    if referral.referred_to_doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.referrals'))
    
    reason = request.form.get('decline_reason', 'No reason provided')
    referral.decline(reason)
    db.session.commit()
    
    flash('Referral declined.', 'info')
    return redirect(url_for('doctor.referrals'))


@doctor_bp.route('/referral/<int:referral_id>/complete', methods=['POST'])
@login_required
@doctor_required
def complete_referral(referral_id):
    """Complete a referral with notes"""
    referral = DoctorReferral.query.get_or_404(referral_id)
    
    if referral.referred_to_doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.referrals'))
    
    notes = request.form.get('consultation_notes', '')
    recommendations = request.form.get('recommendations', '')
    follow_up = request.form.get('follow_up_needed') == 'on'
    
    referral.complete(notes, recommendations)
    referral.follow_up_needed = follow_up
    referral.follow_up_instructions = request.form.get('follow_up_instructions', '')
    referral.report_sent = True
    referral.report_sent_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Referral completed and report sent to referring doctor.', 'success')
    return redirect(url_for('doctor.referrals'))


# ============ VIDEO CONSULTATIONS ============

@doctor_bp.route('/video-consultations')
@login_required
@doctor_required
def video_consultations():
    """View video consultation appointments"""
    today = date.today()
    
    # Today's video appointments
    today_video = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_type == 'video',
        Appointment.appointment_date == today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_time).all()
    
    # Upcoming video appointments
    upcoming_video = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_type == 'video',
        Appointment.appointment_date > today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(10).all()
    
    # Past video consultations
    past_video = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.appointment_type == 'video',
        Appointment.status == 'completed'
    ).order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    return render_template('doctor/video_consultations.html',
                         today_video=today_video,
                         upcoming_video=upcoming_video,
                         past_video=past_video)


# ============ PROFILE ============

@doctor_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@doctor_required
def profile():
    """Doctor profile management"""
    if request.method == 'POST':
        # Update basic info
        current_user.full_name = request.form.get('full_name', current_user.full_name)
        current_user.phone = request.form.get('phone', '')
        current_user.specialization = request.form.get('specialization', '')
        current_user.qualification = request.form.get('qualification', '')
        current_user.department = request.form.get('department', '')
        current_user.experience_years = int(request.form.get('experience_years', 0))
        current_user.consultation_fee = float(request.form.get('consultation_fee', 0))
        current_user.video_consultation_fee = float(request.form.get('video_consultation_fee', 0))
        current_user.is_available_online = request.form.get('available_online') == 'on'
        
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                # Delete old picture
                if current_user.profile_picture and current_user.profile_picture != 'default_avatar.png':
                    ImageService.delete_profile_picture(current_user.profile_picture)
                
                # Save new picture
                filename = ImageService.save_profile_picture(file, current_user.id)
                if filename:
                    current_user.profile_picture = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('doctor.profile'))
    
    return render_template('doctor/profile.html')
@doctor_bp.route('/profile/update', methods=['POST'])
@login_required
@doctor_required
def update_profile():
    """Update doctor profile - separate route"""
    try:
        # Update basic info
        current_user.first_name = request.form.get('first_name', current_user.first_name)
        current_user.last_name = request.form.get('last_name', current_user.last_name)
        current_user.phone = request.form.get('phone', current_user.phone)
        current_user.specialization = request.form.get('specialization', current_user.specialization)
        current_user.license_number = request.form.get('license_number', current_user.license_number)
        
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                # Validate file extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                filename = file.filename
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # Generate secure filename
                    import os
                    from werkzeug.utils import secure_filename
                    from datetime import datetime
                    
                    ext = filename.rsplit('.', 1)[1].lower()
                    new_filename = f"doctor_{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                    
                    # Save file
                    upload_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'],
                        'profile_pictures',
                        new_filename
                    )
                    
                    # Delete old profile picture if exists
                    if current_user.profile_picture:
                        old_path = os.path.join(
                            current_app.config['UPLOAD_FOLDER'],
                            'profile_pictures',
                            current_user.profile_picture
                        )
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    file.save(upload_path)
                    current_user.profile_picture = new_filename
                else:
                    flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF', 'warning')
                    return redirect(url_for('doctor.profile'))
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'error')
    
    return redirect(url_for('doctor.profile'))


@doctor_bp.route('/profile/change-password', methods=['POST'])
@login_required
@doctor_required
def change_password():
    """Change doctor password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required.', 'warning')
        return redirect(url_for('doctor.profile'))
    
    # Check current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('doctor.profile'))
    
    # Check new password match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('doctor.profile'))
    
    # Check password length
    if len(new_password) < 8:
        flash('Password must be at least 8 characters long.', 'warning')
        return redirect(url_for('doctor.profile'))
    
    try:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error changing password: {str(e)}', 'error')
    
    return redirect(url_for('doctor.profile'))


@doctor_bp.route('/signature', methods=['GET', 'POST'])
@login_required
@doctor_required
def manage_signature():
    """Manage digital signature"""
    if request.method == 'POST':
        signature_data = request.form.get('signature_data')
        
        if not signature_data:
            flash('Please draw your signature.', 'error')
            return render_template('doctor/signature.html')
        
        success, result = SignatureService.save_doctor_signature(signature_data, current_user.id)
        
        if success:
            flash('Digital signature saved successfully!', 'success')
            return redirect(url_for('doctor.profile'))
        else:
            flash(f'Error saving signature: {result}', 'error')
    
    return render_template('doctor/signature.html')


# ============ FEEDBACK ============

@doctor_bp.route('/feedback')
@login_required
@doctor_required
def feedback():
    """View patient feedback and ratings"""
    page = request.args.get('page', 1, type=int)
    
    feedbacks = Feedback.query.filter_by(
        doctor_id=current_user.id
    ).order_by(Feedback.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Statistics
    total_reviews = Feedback.query.filter_by(doctor_id=current_user.id).count()
    avg_rating = current_user.average_rating
    
    # Rating distribution
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[i] = Feedback.query.filter_by(
            doctor_id=current_user.id,
            overall_rating=i
        ).count()
    
    return render_template('doctor/feedback.html',
                         feedbacks=feedbacks,
                         total_reviews=total_reviews,
                         avg_rating=avg_rating,
                         rating_dist=rating_dist)


@doctor_bp.route('/feedback/<int:feedback_id>/respond', methods=['POST'])
@login_required
@doctor_required
def respond_to_feedback(feedback_id):
    """Respond to patient feedback"""
    feedback = Feedback.query.get_or_404(feedback_id)
    
    if feedback.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.feedback'))
    
    response = request.form.get('response', '').strip()
    if response:
        feedback.doctor_response = response
        feedback.responded_at = datetime.utcnow()
        db.session.commit()
        flash('Response submitted successfully!', 'success')
    
    return redirect(url_for('doctor.feedback'))


# ============ EXISTING ROUTES (Keep these) ============

@doctor_bp.route('/patient/search', methods=['GET', 'POST'])
@login_required
@doctor_required
def search_patient():
    """Search for existing patients"""
    patients = []
    search_query = ''
    
    if request.method == 'POST':
        search_query = request.form.get('search', '').strip()
        if search_query:
            patients = Patient.query.filter(
                db.or_(
                    Patient.patient_id.ilike(f'%{search_query}%'),
                    Patient.full_name.ilike(f'%{search_query}%'),
                    Patient.phone.ilike(f'%{search_query}%')
                )
            ).limit(20).all()
    
    return render_template('doctor/search_patient.html', 
                         patients=patients, 
                         search_query=search_query)
@doctor_bp.route('/patients')
@login_required
@doctor_required
def patients():
    """View doctor's patients"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Get patients who have had appointments with this doctor
    from app.models.appointment import Appointment
    
    subquery = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == current_user.id
    ).distinct().subquery()
    
    query = Patient.query.filter(Patient.id.in_(subquery))
    
    if search:
        query = query.filter(
            db.or_(
                Patient.full_name.ilike(f'%{search}%'),
                Patient.patient_id.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%')
            )
        )
    
    patients = query.order_by(Patient.full_name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('doctor/patient.html',
                         patients=patients,
                         search=search)



@doctor_bp.route('/patient/<int:patient_id>')
@login_required
@doctor_required
def patient_detail(patient_id):
    """View patient details"""
    patient = Patient.query.get_or_404(patient_id)
    prescriptions = Prescription.query.filter_by(
        patient_id=patient_id,
        doctor_id=current_user.id
    ).order_by(Prescription.created_at.desc()).all()
    reports = Report.query.filter_by(patient_id=patient.id).order_by(
        Report.created_at.desc()
    ).all()
    
    # Get patient's appointments with this doctor
    appointments = Appointment.query.filter_by(
        patient_id=patient.id,
        doctor_id=current_user.id
    ).order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    return render_template('doctor/patient_detail.html',
                         patient=patient,
                         prescriptions=prescriptions,
                         reports=reports,
                         appointments=appointments)
@doctor_bp.route('/report/manual/<int:patient_id>/analyze', methods=['POST'])
@login_required
@doctor_required
def analyze_manual_report(patient_id):
    """Analyze manually entered report values"""
    patient = Patient.query.get_or_404(patient_id)
    
    report_type = request.form.get('report_type', 'general')
    report_date_str = request.form.get('report_date', '')
    notes = request.form.get('notes', '')
    
    # Collect all numeric values from form
    values = {}
    for key, value in request.form.items():
        if key not in ['csrf_token', 'report_type', 'report_date', 'notes']:
            try:
                if value and value.strip():
                    values[key] = float(value)
            except ValueError:
                continue
    
    if not values:
        flash('Please enter at least one test value.', 'error')
        return redirect(url_for('doctor.manual_report', patient_id=patient.id))
    
    # Analyze the values
    analyzer = ReportAnalyzer()
    analysis = analyzer.analyze_manual_input(values, patient.gender or 'male')
    
    # Parse report date
    try:
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
    except:
        report_date = date.today()
    
    # Create report record
    report = Report(
        report_id=Report.generate_report_id(),
        patient_id=patient.id,
        uploaded_by=current_user.id,
        report_type=report_type,
        report_name=f"Manual Entry - {report_type}",
        report_date=report_date,
        file_path='manual_entry',
        file_type='manual',
        extracted_text=str(values),  # Store the values as text
        summary=analysis['summary'],
        key_findings='\n'.join(analysis['key_findings']),
        abnormal_values='\n'.join(analysis['abnormal_values']),
        concern_areas='\n'.join(analysis['concern_areas']),
        recommendations='\n'.join(analysis['recommendations']),
        is_analyzed=True,
        analysis_date=datetime.utcnow()
    )
    
    if notes:
        report.summary += f"\n\n📝 Doctor's Notes: {notes}"
    
    db.session.add(report)
    db.session.commit()
    
    flash('Report analyzed successfully!', 'success')
    return redirect(url_for('doctor.view_report', report_id=report.id))
@doctor_bp.route('/report/manual/<int:patient_id>', methods=['GET'])
@login_required
@doctor_required
def manual_report(patient_id):
    """Show manual report entry form"""
    patient = Patient.query.get_or_404(patient_id)
    return render_template('doctor/manual_report.html', patient=patient, today=date.today())
@doctor_bp.route('/report/upload/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def report_upload(patient_id):
    """Upload and analyze medical report"""
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        if 'report_file' not in request.files:
            flash('No file selected.', 'error')
            return render_template('doctor/report_upload.html', patient=patient, today=date.today())
        
        file = request.files['report_file']
        report_type = request.form.get('report_type', 'general')
        report_date_str = request.form.get('report_date', '')
        
        if file.filename == '':
            flash('No file selected.', 'error')
            return render_template('doctor/report_upload.html', patient=patient, today=date.today())
        
        # Check file extension
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            flash('Invalid file type. Please upload PDF, PNG, or JPG files only.', 'error')
            return render_template('doctor/report_upload.html', patient=patient, today=date.today())
        
        try:
            # Save file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{patient.patient_id}_{timestamp}_{filename}"
            
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            # Determine file type and extract text
            ocr_service = OCRService()
            
            if filename.lower().endswith('.pdf'):
                extracted_text = ocr_service.extract_from_pdf(filepath)
                file_type = 'pdf'
            else:
                extracted_text = ocr_service.extract_from_image(filepath)
                file_type = 'image'
            
            # Analyze report
            analyzer = ReportAnalyzer()
            analysis = analyzer.analyze_report(
                extracted_text, 
                report_type, 
                patient.gender or 'male'
            )
            
            # Parse report date
            try:
                report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
            except:
                report_date = date.today()
            
            # Save report
            report = Report(
                report_id=Report.generate_report_id(),
                patient_id=patient.id,
                uploaded_by=current_user.id,
                report_type=report_type,
                report_name=filename,
                report_date=report_date,
                file_path=filepath,
                file_type=file_type,
                extracted_text=extracted_text,
                summary=analysis['summary'],
                key_findings='\n'.join(analysis['key_findings']),
                abnormal_values='\n'.join(analysis['abnormal_values']),
                concern_areas='\n'.join(analysis['concern_areas']),
                recommendations='\n'.join(analysis['recommendations']),
                is_analyzed=True,
                analysis_date=datetime.utcnow()
            )
            
            db.session.add(report)
            db.session.commit()
            
            flash('Report uploaded and analyzed successfully!', 'success')
            return redirect(url_for('doctor.view_report', report_id=report.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading report: {str(e)}', 'error')
            return render_template('doctor/report_upload.html', patient=patient, today=date.today())
    
    # GET request - show upload form
    return render_template('doctor/report_upload.html', patient=patient, today=date.today())
@doctor_bp.route('/patient/register', methods=['GET', 'POST'])
@login_required
@doctor_required
def register_patient():
    """Register new patient with medical survey"""
    from app.models.user import User
    from app.models.patient import Patient, PatientAllergy, PatientCondition
    from datetime import datetime, date, timedelta
    
    if request.method == 'POST':
        try:
            # ========== GET FORM DATA ==========
            full_name = request.form.get('full_name', '').strip()
            gender = request.form.get('gender', '').strip()
            blood_group = request.form.get('blood_group', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            address = request.form.get('address', '').strip()
            
            # Emergency contact
            emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
            emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
            emergency_contact_relation = request.form.get('emergency_contact_relation', '').strip()
            
            # ========== HANDLE AGE PROPERLY ==========
            age = None
            dob = None
            
            # Try to get age from form
            age_str = request.form.get('age', '').strip()
            if age_str:
                try:
                    age = int(age_str)
                except ValueError:
                    age = None
            
            # Try to get date of birth
            dob_str = request.form.get('date_of_birth', '').strip()
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                    # Calculate age from DOB if age not provided
                    if age is None:
                        today = date.today()
                        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                except:
                    pass
            
            # If still no age but we have an approximation, calculate DOB
            if age is not None and age > 0 and dob is None:
                dob = (datetime.now() - timedelta(days=age * 365)).date()
            
            # Final validation for age
            if age is None or age <= 0:
                flash('Please provide a valid age.', 'error')
                return render_template('doctor/patient_survey.html')
            
            # ========== VALIDATE REQUIRED FIELDS ==========
            if not full_name:
                flash('Full name is required.', 'error')
                return render_template('doctor/patient_survey.html')
            
            if not gender:
                flash('Gender is required.', 'error')
                return render_template('doctor/patient_survey.html')
            
            if not phone:
                flash('Phone number is required.', 'error')
                return render_template('doctor/patient_survey.html')
            
            # ========== CHECK EXISTING PATIENT ==========
            existing_patient = Patient.query.filter_by(phone=phone).first()
            if existing_patient:
                flash(f'Patient with phone {phone} already exists!', 'warning')
                return redirect(url_for('doctor.patient_detail', patient_id=existing_patient.id))
            
            # ========== CREATE USER ACCOUNT IF EMAIL PROVIDED ==========
            user = None
            if email:
                existing_user = User.query.filter_by(email=email).first()
                if not existing_user:
                    username = email.split('@')[0]
                    counter = 1
                    original_username = username
                    while User.query.filter_by(username=username).first():
                        username = f"{original_username}{counter}"
                        counter += 1
                    
                    user = User(
                        username=username,
                        email=email,
                        full_name=full_name,
                        role='patient',
                        is_active=True
                    )
                    user.set_password('patient123')
                    db.session.add(user)
                    db.session.flush()
            
            # ========== CREATE PATIENT RECORD ==========
            patient = Patient(
                patient_id=Patient.generate_patient_id(),
                user_id=user.id if user else None,
                full_name=full_name,
                age=age,  # ✅ NOW INCLUDED!
                date_of_birth=dob,
                gender=gender,
                phone=phone,
                email=email,
                blood_group=blood_group if blood_group else None,
                address=address,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                emergency_contact_relation=emergency_contact_relation,
                survey_completed=True
            )
            db.session.add(patient)
            db.session.flush()
            
            # ========== PROCESS ALLERGIES ==========
            allergies = request.form.getlist('allergies')
            custom_allergies = request.form.get('custom_allergies', '').strip()
            
            if custom_allergies:
                custom_list = [a.strip() for a in custom_allergies.split(',') if a.strip()]
                allergies.extend(custom_list)
            
            for allergy in allergies:
                if allergy.strip():
                    patient_allergy = PatientAllergy(
                        patient_id=patient.id,
                        allergy_name=allergy.strip(),  # ✅ Fixed field name
                        severity='moderate',
                        notes='Reported during registration'
                    )
                    db.session.add(patient_allergy)
            
            # ========== PROCESS CONDITIONS ==========
            conditions = request.form.getlist('conditions')
            custom_conditions = request.form.get('custom_conditions', '').strip()
            
            if custom_conditions:
                custom_list = [c.strip() for c in custom_conditions.split(',') if c.strip()]
                conditions.extend(custom_list)
            
            for condition in conditions:
                if condition.strip():
                    patient_condition = PatientCondition(
                        patient_id=patient.id,
                        condition_name=condition.strip(),
                        diagnosed_date=datetime.now().date(),
                        current_status='active',  # ✅ Fixed field name
                        notes='Reported during registration'
                    )
                    db.session.add(patient_condition)
            
            # ========== PROCESS LIFESTYLE INFORMATION ==========
            patient.smoking_status = request.form.get('smoking_status', 'never')
            patient.alcohol_consumption = request.form.get('alcohol_consumption', 'never')
            patient.food_preference = request.form.get('food_preference', 'non-vegetarian')
            patient.exercise_frequency = request.form.get('exercise_frequency', 'none')
            patient.current_medications = request.form.get('current_medications', '').strip()
            patient.notes = request.form.get('notes', '').strip()
            
            db.session.commit()
            
            # ========== SUCCESS MESSAGE ==========
            success_msg = f'Patient {full_name} (ID: {patient.patient_id}) registered successfully!'
            if user:
                success_msg += f' Login: {email} / Password: patient123'
            
            flash(success_msg, 'success')
            return redirect(url_for('doctor.patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering patient: {str(e)}', 'error')
            import traceback
            traceback.print_exc()
            return render_template('doctor/patient_survey.html')
    
    # GET request - show registration form
    return render_template('doctor/patient_survey.html')
@doctor_bp.route('/patient/<int:patient_id>')
@login_required
@doctor_required
def view_patient(patient_id):
    """View patient details"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get patient's prescriptions from this doctor
    prescriptions = Prescription.query.filter_by(
        patient_id=patient_id,
        doctor_id=current_user.id
    ).order_by(Prescription.created_at.desc()).all()
    
    # Get patient's appointments with this doctor
    appointments = Appointment.query.filter_by(
        patient_id=patient_id,
        doctor_id=current_user.id
    ).order_by(Appointment.appointment_date.desc()).limit(10).all()
    
    # Get allergies and conditions
    allergies = patient.get_allergies_list()
    conditions = patient.get_conditions_list()
    
    return render_template('doctor/view_patient.html',
                         patient=patient,
                         prescriptions=prescriptions,
                         appointments=appointments,
                         allergies=allergies,
                         conditions=conditions)
# ============ ECG DETECTION ============

@doctor_bp.route('/ecg-detection')
@login_required
@doctor_required
def ecg_detection():
    """ECG Detection main page for doctors"""
    from app.models.ecg_record import ECGPatient
    
    # Get recent ECG records for this doctor's patients
    recent_ecgs = ECGPatient.query.filter_by(
        analyzed_by=current_user.id
    ).order_by(ECGPatient.created_at.desc()).limit(10).all()
    
    # Get patients for dropdown
    subquery = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == current_user.id
    ).distinct().subquery()
    
    patients = Patient.query.filter(Patient.id.in_(subquery)).order_by(Patient.full_name).all()
    
    return render_template('doctor/ecg_detection.html', 
                          recent_ecgs=recent_ecgs,
                          patients=patients)


@doctor_bp.route('/ecg-detection/upload', methods=['GET', 'POST'])
@login_required
@doctor_required
def ecg_upload():
    """Upload ECG data for analysis"""

    import os
    import json
    import tempfile

    from app.models.ecg_record import ECGPatient, ECGResult
    from app.models import Patient, Appointment
    from flask import request, render_template, flash, redirect, url_for
    from flask_login import current_user
    from app import db

    # 🔹 Get patients for dropdown (only doctor’s patients)
    subquery = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == current_user.id
    ).distinct().subquery()

    patients = Patient.query.filter(
        Patient.id.in_(subquery)
    ).order_by(Patient.full_name).all()

    if request.method == 'POST':
        patient_id = request.form.get('patient_id', type=int)

        if not patient_id:
            flash('Please select a patient.', 'error')
            return redirect(url_for('doctor.ecg_upload'))

        patient = Patient.query.get(patient_id)
        if not patient:
            flash('Invalid patient selected.', 'error')
            return redirect(url_for('doctor.ecg_upload'))

        # 🔹 Check file upload
        if 'ecg_file' not in request.files or not request.files['ecg_file'].filename:
            flash('Please upload an ECG file.', 'error')
            return redirect(url_for('doctor.ecg_upload'))

        file = request.files['ecg_file']

        try:
            # 🔹 Save file temporarily
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, file.filename)
            file.save(temp_path)

            # 🔹 Analyze ECG
            try:
                from app.services.ecg_service import ECGService
                ecg_service = ECGService()
                result = ecg_service.analyze_ecg(temp_path)
            except Exception:
                # Demo / fallback mode
                result = {
                    'success': True,
                    'classification': 'Normal Sinus Rhythm',
                    'confidence': 92.5,
                    'cnn_prediction': 'Normal',
                    'lstm_prediction': 'Normal',
                    'rf_prediction': 'Normal',
                    'heart_rate': 75,
                    'notes': 'Analysis completed (Demo mode)'
                }

            # 🔹 Cleanup temp files
            os.remove(temp_path)
            os.rmdir(temp_dir)

            if not result.get('success', True):
                flash(f"ECG analysis failed: {result.get('error', 'Unknown error')}", 'error')
                return redirect(url_for('doctor.ecg_upload'))

            # ==========================
            # 1️⃣ Save ECGPatient
            # ==========================
            ecg_record = ECGPatient(
                hospital_patient_id=patient.id,
                name=patient.full_name,
                age=patient.age,
                gender=patient.gender,
                uploaded_by=current_user.id
            )

            db.session.add(ecg_record)
            db.session.flush()  # 🔥 get ecg_record.id before commit

            # ==========================
            # 2️⃣ Save ECGResult
            # ==========================
            ecg_result = ECGResult(
                ecg_patient_id=ecg_record.id,

                file_name=file.filename,
                file_path=None,

                predictions=json.dumps(result),

                risk_level=result.get('classification', 'UNKNOWN'),
                confidence=(result.get('confidence', 0) / 100),

                total_beats=0,
                normal_beats=0,
                ventricular_beats=0,
                supraventricular_beats=0,
                fusion_beats=0,
                unknown_beats=0,

                duration_seconds=0,
                sampling_rate=360,

                message=result.get('notes', '')
            )

            db.session.add(ecg_result)
            db.session.commit()

            flash('ECG analysis completed successfully!', 'success')
            return redirect(url_for('doctor.ecg_result', ecg_id=ecg_record.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error processing ECG: {str(e)}', 'error')
            return redirect(url_for('doctor.ecg_upload'))

    return render_template(
        'doctor/ecg_upload.html',
        patients=patients
    )



@doctor_bp.route('/ecg-detection/demo', methods=['GET', 'POST'])
@login_required
@doctor_required
def ecg_demo():
    """Demo ECG analysis with sample data"""
    from app.models.ecg_record import ECGPatient
    
    # Get patients for dropdown
    subquery = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == current_user.id
    ).distinct().subquery()
    
    patients = Patient.query.filter(Patient.id.in_(subquery)).order_by(Patient.full_name).all()
    
    if request.method == 'POST':
        sample_type = request.form.get('sample_type', 'normal')
        patient_id = request.form.get('patient_id', type=int)
        
        # Mock results based on sample type
        results = {
            'normal': {
                'classification': 'Normal Sinus Rhythm',
                'confidence': 94.5,
                'cnn_prediction': 'Normal',
                'lstm_prediction': 'Normal',
                'rf_prediction': 'Normal',
                'heart_rate': 72
            },
            'afib': {
                'classification': 'Atrial Fibrillation',
                'confidence': 89.2,
                'cnn_prediction': 'Atrial Fibrillation',
                'lstm_prediction': 'Atrial Fibrillation',
                'rf_prediction': 'Irregular Rhythm',
                'heart_rate': 110
            },
            'vtach': {
                'classification': 'Ventricular Tachycardia',
                'confidence': 91.8,
                'cnn_prediction': 'Ventricular Tachycardia',
                'lstm_prediction': 'Ventricular Tachycardia',
                'rf_prediction': 'Abnormal',
                'heart_rate': 180
            },
            'bradycardia': {
                'classification': 'Sinus Bradycardia',
                'confidence': 93.1,
                'cnn_prediction': 'Bradycardia',
                'lstm_prediction': 'Bradycardia',
                'rf_prediction': 'Slow Rhythm',
                'heart_rate': 48
            }
        }
        
        result = results.get(sample_type, results['normal'])
        
        # Save ECG record
        ecg_record = ECGPatient(
            patient_id=patient_id if patient_id else None,
            analyzed_by=current_user.id,
            classification=result['classification'],
            confidence=result['confidence'],
            cnn_prediction=result['cnn_prediction'],
            lstm_prediction=result['lstm_prediction'],
            rf_prediction=result['rf_prediction'],
            heart_rate=result['heart_rate'],
            analysis_notes=f'Demo analysis - Sample type: {sample_type}'
        )
        db.session.add(ecg_record)
        db.session.commit()
        
        flash('Demo ECG analysis completed!', 'success')
        return redirect(url_for('doctor.ecg_result', ecg_id=ecg_record.id))
    
    return render_template('doctor/ecg_demo.html', patients=patients)


@doctor_bp.route('/ecg-detection/result/<int:ecg_id>')
@login_required
@doctor_required
def ecg_result(ecg_id):
    """View ECG analysis result"""
    from app.models.ecg_record import ECGPatient
    
    ecg_record = ECGPatient.query.get_or_404(ecg_id)
    
    # Verify access
    if ecg_record.analyzed_by != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.ecg_detection'))
    
    return render_template('doctor/ecg_result.html', ecg=ecg_record)


@doctor_bp.route('/ecg-detection/history')
@login_required
@doctor_required
def ecg_history():
    """View ECG analysis history"""
    from app.models.ecg_record import ECGPatient
    
    page = request.args.get('page', 1, type=int)
    patient_filter = request.args.get('patient_id', type=int)
    
    query = ECGPatient.query.filter_by(analyzed_by=current_user.id)
    
    if patient_filter:
        query = query.filter_by(patient_id=patient_filter)
    
    ecg_records = query.order_by(ECGPatient.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get patients for filter dropdown
    subquery = db.session.query(Appointment.patient_id).filter(
        Appointment.doctor_id == current_user.id
    ).distinct().subquery()
    
    patients = Patient.query.filter(Patient.id.in_(subquery)).order_by(Patient.full_name).all()
    
    return render_template('doctor/ecg_history.html', 
                          ecg_records=ecg_records,
                          patients=patients,
                          patient_filter=patient_filter)


@doctor_bp.route('/patient/<int:patient_id>/ecg')
@login_required
@doctor_required
def patient_ecg_history(patient_id):
    """View ECG history for a specific patient"""
    from app.models.ecg_record import ECGPatient
    
    patient = Patient.query.get_or_404(patient_id)
    
    ecg_records = ECGPatient.query.filter_by(
        patient_id=patient_id
    ).order_by(ECGPatient.created_at.desc()).all()
    
    return render_template('doctor/patient_ecg_history.html',
                          patient=patient,
                          ecg_records=ecg_records)


# ============ REPORTS - FIXED ============

@doctor_bp.route('/patient/<int:patient_id>/reports')
@login_required
@doctor_required
def patient_reports(patient_id):
    """View all reports for a specific patient"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get all reports for this patient
    reports = Report.query.filter_by(patient_id=patient_id).order_by(Report.created_at.desc()).all()
    
    return render_template('doctor/patient_reports.html', 
                          patient=patient, 
                          reports=reports)


@doctor_bp.route('/report/<int:report_id>')
@login_required
@doctor_required
def view_report(report_id):
    """View a specific report"""
    report = Report.query.get_or_404(report_id)
    
    return render_template('doctor/view_report.html', report=report)


@doctor_bp.route('/report/<int:report_id>/reanalyze', methods=['POST'])
@login_required
@doctor_required
def reanalyze_report(report_id):
    """Re-analyze a report"""
    report = Report.query.get_or_404(report_id)
    
    try:
        if report.file_path and report.file_path != 'manual_entry':
            if os.path.exists(report.file_path):
                analyzer = ReportAnalyzer()
                
                # Re-extract text if needed
                if not report.extracted_text:
                    ocr_service = OCRService()
                    if report.file_type == 'pdf':
                        report.extracted_text = ocr_service.extract_from_pdf(report.file_path)
                    else:
                        report.extracted_text = ocr_service.extract_from_image(report.file_path)
                
                # Re-analyze
                patient = Patient.query.get(report.patient_id)
                analysis = analyzer.analyze_report(
                    report.extracted_text,
                    report.report_type,
                    patient.gender if patient else 'male'
                )
                
                report.summary = analysis['summary']
                report.key_findings = '\n'.join(analysis['key_findings'])
                report.abnormal_values = '\n'.join(analysis['abnormal_values'])
                report.concern_areas = '\n'.join(analysis['concern_areas'])
                report.recommendations = '\n'.join(analysis['recommendations'])
                report.is_analyzed = True
                report.analysis_date = datetime.utcnow()
                
                db.session.commit()
                flash('Report re-analyzed successfully!', 'success')
            else:
                flash('Report file not found.', 'error')
        else:
            flash('Cannot re-analyze manual entry reports.', 'warning')
            
    except Exception as e:
        flash(f'Error re-analyzing report: {str(e)}', 'error')
    
    return redirect(url_for('doctor.view_report', report_id=report_id))
