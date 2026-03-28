"""
Patient Module Routes - Updated with Appointments, Feedback, Insurance
"""

from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User, Patient, Prescription, Report
from app.models.appointment import Appointment
from app.models.video_consultation import VideoSession
from app.models.feedback import Feedback
from app.models.insurance import PatientInsurance, InsuranceProvider, InsuranceClaim
from app.services.image_service import ImageService

patient_bp = Blueprint('patient', __name__)


def patient_required(f):
    """Decorator to require patient role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_patient():
            flash('Access denied. Patient login required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_patient():
    """Get current patient profile"""
    return Patient.query.filter_by(user_id=current_user.id).first()

@patient_bp.route('/meal-analyzer', methods=['GET', 'POST'])  # BOTH METHODS!
@login_required
@patient_required
def meal_analyzer():
    """Meal analyzer page for patients"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    # Get current medicines
    current_medicines = []
    active_prescriptions = Prescription.query.filter_by(
        patient_id=patient.id,
        status='active'
    ).all()
    
    for rx in active_prescriptions:
        for med in rx.medicines.all():
            if med.medicine_name not in current_medicines:
                current_medicines.append(med.medicine_name)
    
    result = None
    meal_text = ''
    
    if request.method == 'POST':
        meal_text = request.form.get('meal_description', '').strip()
        medicines_input = request.form.getlist('medicines')
        custom_medicines = request.form.get('custom_medicines', '').strip()
        
        all_medicines = list(medicines_input)
        if custom_medicines:
            all_medicines.extend([m.strip() for m in custom_medicines.split(',') if m.strip()])
        
        if not meal_text:
            flash('Please describe your meal.', 'error')
        elif not all_medicines:
            flash('Please select or enter at least one medicine.', 'error')
        else:
            from app.services.meal_analyzer import MealAnalyzer
            analyzer = MealAnalyzer()
            result = analyzer.analyze_meal(meal_text, all_medicines)
    
    return render_template('patient/meal_analyzer.html',
                          patient=patient,
                          current_medicines=current_medicines,
                          result=result,
                          meal_text=meal_text)


@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    """Patient dashboard"""
    patient = get_current_patient()
    
    if not patient:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('patient.complete_profile'))
    
    today = date.today()
    
    # Upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(5).all()
    
    # Today's appointments
    today_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date == today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_time).all()
    
    # Recent prescriptions
    recent_prescriptions = Prescription.query.filter_by(
        patient_id=patient.id
    ).order_by(Prescription.created_at.desc()).limit(5).all()
    
    # Active prescriptions
    active_prescriptions = Prescription.query.filter_by(
        patient_id=patient.id,
        status='active'
    ).order_by(Prescription.created_at.desc()).all() 
    total_reports = Report.query.filter_by(patient_id=patient.id).count()
    
    # Recent reports
    recent_reports = Report.query.filter_by(
        patient_id=patient.id
    ).order_by(Report.created_at.desc()).limit(5).all()
    
    # Video consultations ready to join
    video_ready = []
    for apt in today_appointments:
        if apt.appointment_type == 'video' and apt.can_start_video():
            video_ready.append(apt)
    
    # ========== ADD TODAY'S REMINDERS ==========
    today_reminders = []
    for prescription in active_prescriptions:
        for med in prescription.medicines.all():
            # Parse frequency to determine timing
            frequency = (med.frequency or '').lower()
            dosage = med.dosage or 'As prescribed'
            
            # Determine timing based on frequency
            if 'morning' in frequency or 'breakfast' in frequency:
                timing = 'Morning'
            elif 'afternoon' in frequency or 'lunch' in frequency:
                timing = 'Afternoon'
            elif 'evening' in frequency or 'dinner' in frequency:
                timing = 'Evening'
            elif 'night' in frequency or 'bed' in frequency:
                timing = 'Night'
            else:
                timing = 'As directed'
            
            today_reminders.append({
                'medicine': med.medicine_name,
                'dosage': dosage,
                'timing': timing,
                'frequency': med.frequency or 'As prescribed',
                'prescription_id': prescription.id
            })
    # ========== END TODAY'S REMINDERS ==========
    
    return render_template('patient/dashboard.html',
                         patient=patient,
                         upcoming_appointments=upcoming_appointments,
                         today_appointments=today_appointments,
                         recent_prescriptions=recent_prescriptions,
                         active_prescriptions=active_prescriptions,
                         total_reports=total_reports,
                         recent_reports=recent_reports,
                         video_ready=video_ready,
                         today_reminders=today_reminders) 


# ============ APPOINTMENTS ============

@patient_bp.route('/appointments')
@login_required
@patient_required
def appointments():
    """View patient's appointments"""
    patient = get_current_patient()
    if not patient:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('patient.complete_profile'))
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    time_filter = request.args.get('time', 'upcoming')
    
    query = Appointment.query.filter_by(patient_id=patient.id)
    
    if status:
        query = query.filter_by(status=status)
    
    if time_filter == 'upcoming':
        query = query.filter(Appointment.appointment_date >= date.today())
    elif time_filter == 'past':
        query = query.filter(Appointment.appointment_date < date.today())
    
    appointments = query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('patient/appointments.html',
                         appointments=appointments,
                         status=status,
                         time_filter=time_filter)


@patient_bp.route('/book-appointment', methods=['GET', 'POST'])
@login_required
@patient_required
def book_appointment():
    """Book new appointment"""
    patient = get_current_patient()
    if not patient:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('patient.complete_profile'))
    
    # Get all active doctors
    doctors = User.query.filter_by(role='doctor', is_active=True).all()
    
    # Get specializations for filter
    specializations = db.session.query(User.specialization).filter(
        User.role == 'doctor',
        User.is_active == True,
        User.specialization.isnot(None)
    ).distinct().all()
    specializations = [s[0] for s in specializations if s[0]]
    
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id', type=int)
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        appointment_type = request.form.get('appointment_type', 'in_person')
        reason = request.form.get('reason', '')
        
        if not all([doctor_id, appointment_date, appointment_time]):
            flash('Please fill all required fields.', 'error')
            return render_template('patient/book_appointment.html',
                                 doctors=doctors,
                                 specializations=specializations)
        
        try:
            apt_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            apt_time = datetime.strptime(appointment_time, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'error')
            return render_template('patient/book_appointment.html',
                                 doctors=doctors,
                                 specializations=specializations)
        
        # Validate date is in future
        apt_datetime = datetime.combine(apt_date, apt_time)
        if apt_datetime <= datetime.now():
            flash('Please select a future date and time.', 'error')
            return render_template('patient/book_appointment.html',
                                 doctors=doctors,
                                 specializations=specializations)
        
        # Check slot availability
        existing = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == apt_date,
            Appointment.appointment_time == apt_time,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).first()
        
        if existing:
            flash('This time slot is no longer available.', 'error')
            return render_template('patient/book_appointment.html',
                                 doctors=doctors,
                                 specializations=specializations)
        
        # Get fee
        doctor = User.query.get(doctor_id)
        fee = doctor.video_consultation_fee if appointment_type == 'video' else doctor.consultation_fee
        fee = fee or 0
        
        # Create appointment
        appointment = Appointment(
            appointment_number=Appointment.generate_appointment_number(),
            patient_id=patient.id,
            doctor_id=doctor_id,
            appointment_date=apt_date,
            appointment_time=apt_time,
            appointment_type=appointment_type,
            reason=reason,
            fee_amount=fee,
            status='scheduled'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        try:
            from app.services.notification_service import NotificationService
            
            # Send email to doctor
            if doctor.email:
                NotificationService.send_email(
                    to_email=doctor.email,
                    template_name='new_appointment_request',
                    context={
                        'doctor_name': doctor.full_name,
                        'patient_name': patient.full_name,
                        'appointment_date': apt_date.strftime('%B %d, %Y'),
                        'appointment_time': apt_time.strftime('%I:%M %p'),
                        'appointment_type': 'Video Consultation' if appointment_type == 'video' else 'In-Person Visit',
                        'reason': reason or 'Not specified',
                        'appointment_number': appointment.appointment_number
                    }
                )
                print(f"✅ Notification sent to doctor: {doctor.email}")
        except Exception as e:
            # Don't fail the appointment if notification fails
            print(f"⚠️ Failed to send notification to doctor: {e}")
        # ========== END NOTIFICATION ==========
        
        flash(f'Appointment booked successfully! Confirmation #: {appointment.appointment_number}', 'success')
        return redirect(url_for('patient.view_appointment', appointment_id=appointment.id))
    
    return render_template('patient/book_appointment.html',
                         doctors=doctors,
                         specializations=specializations,
                         patient=patient)


@patient_bp.route('/appointment/<int:appointment_id>')
@login_required
@patient_required
def view_appointment(appointment_id):
    """View appointment details"""
    patient = get_current_patient()
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.appointments'))
    
    # Check if feedback can be given
    can_give_feedback = (
        appointment.status == 'completed' and
        not appointment.feedback
    )
    
    return render_template('patient/view_appointment.html',
                         appointment=appointment,
                         can_give_feedback=can_give_feedback)


@patient_bp.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@patient_required
def cancel_appointment(appointment_id):
    """Cancel appointment"""
    patient = get_current_patient()
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.appointments'))
    
    if appointment.status in ['completed', 'cancelled']:
        flash('This appointment cannot be cancelled.', 'error')
        return redirect(url_for('patient.view_appointment', appointment_id=appointment_id))
    
    # Check if within cancellation window (e.g., 24 hours before)
    apt_datetime = datetime.combine(appointment.appointment_date, appointment.appointment_time)
    if apt_datetime - datetime.now() < timedelta(hours=24):
        flash('Appointments can only be cancelled at least 24 hours in advance.', 'warning')
    
    reason = request.form.get('reason', 'Cancelled by patient')
    
    appointment.status = 'cancelled'
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancellation_reason = reason
    
    db.session.commit()
    
    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('patient.appointments'))


# ============ VIDEO CONSULTATIONS ============

@patient_bp.route('/video-consultations')
@login_required
@patient_required
def video_consultations():
    """View video consultation appointments"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    today = date.today()
    
    # Today's video appointments
    today_video = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_type == 'video',
        Appointment.appointment_date == today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_time).all()
    
    # Upcoming video appointments
    upcoming_video = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_type == 'video',
        Appointment.appointment_date > today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(10).all()
    
    return render_template('patient/video_consultations.html',
                         today_video=today_video,
                         upcoming_video=upcoming_video)


@patient_bp.route('/join-video/<int:appointment_id>')
@login_required
@patient_required
def join_video(appointment_id):
    """Join video consultation"""
    patient = get_current_patient()
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    if appointment.appointment_type != 'video':
        flash('This is not a video consultation.', 'error')
        return redirect(url_for('patient.view_appointment', appointment_id=appointment_id))
    
    # Check if video session exists
    if appointment.video_room_id:
        return redirect(url_for('video.video_room', room_id=appointment.video_room_id))
    
    # Check if doctor has started the session
    session = VideoSession.query.filter_by(appointment_id=appointment_id).first()
    if session:
        return redirect(url_for('video.video_room', room_id=session.room_id))
    
    flash('The doctor has not started the video consultation yet. Please wait.', 'info')
    return redirect(url_for('patient.view_appointment', appointment_id=appointment_id))


# ============ FEEDBACK ============

@patient_bp.route('/feedback/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@patient_required
def give_feedback(appointment_id):
    """Give feedback for an appointment"""
    patient = get_current_patient()
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.appointments'))
    
    if appointment.status != 'completed':
        flash('You can only give feedback for completed appointments.', 'error')
        return redirect(url_for('patient.view_appointment', appointment_id=appointment_id))
    
    if appointment.feedback:
        flash('You have already given feedback for this appointment.', 'info')
        return redirect(url_for('patient.view_appointment', appointment_id=appointment_id))
    
    if request.method == 'POST':
        overall_rating = int(request.form.get('overall_rating', 5))
        
        feedback = Feedback(
            patient_id=patient.id,
            doctor_id=appointment.doctor_id,
            appointment_id=appointment.id,
            overall_rating=overall_rating,
            punctuality_rating=int(request.form.get('punctuality_rating', 0)) or None,
            communication_rating=int(request.form.get('communication_rating', 0)) or None,
            treatment_rating=int(request.form.get('treatment_rating', 0)) or None,
            facility_rating=int(request.form.get('facility_rating', 0)) or None,
            title=request.form.get('title', '').strip(),
            review=request.form.get('review', '').strip(),
            would_recommend=request.form.get('would_recommend') == 'yes',
            is_anonymous=request.form.get('is_anonymous') == 'on'
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        # Update doctor's rating
        Feedback.update_doctor_rating(appointment.doctor_id)
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('patient.view_appointment', appointment_id=appointment_id))
    
    return render_template('patient/give_feedback.html', appointment=appointment)


@patient_bp.route('/my-feedback')
@login_required
@patient_required
def my_feedback():
    """View all feedback given by patient"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    feedbacks = Feedback.query.filter_by(patient_id=patient.id).order_by(
        Feedback.created_at.desc()
    ).all()
    
    return render_template('patient/my_feedback.html', feedbacks=feedbacks)


# ============ INSURANCE ============

@patient_bp.route('/insurance')
@login_required
@patient_required
def insurance():
    """View patient's insurance policies"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    policies = PatientInsurance.query.filter_by(
        patient_id=patient.id
    ).order_by(PatientInsurance.is_primary.desc()).all()
    
    # Get insurance providers for adding new policy
    providers = InsuranceProvider.query.filter_by(is_active=True).all()
    
    return render_template('patient/insurance.html',
                         policies=policies,
                         providers=providers)


@patient_bp.route('/insurance/add', methods=['GET', 'POST'])
@login_required
@patient_required
def add_insurance():
    """Add new insurance policy"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    providers = InsuranceProvider.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        provider_id = request.form.get('provider_id', type=int)
        
        # Check if this provider already exists for patient
        existing = PatientInsurance.query.filter_by(
            patient_id=patient.id,
            provider_id=provider_id,
            is_active=True
        ).first()
        
        if existing:
            flash('You already have an active policy with this provider.', 'warning')
            return render_template('patient/add_insurance.html', providers=providers)
        
        try:
            effective_date = datetime.strptime(request.form['effective_date'], '%Y-%m-%d').date()
            expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
        except:
            flash('Invalid date format.', 'error')
            return render_template('patient/add_insurance.html', providers=providers)
        
        # If this is first policy or set as primary, update others
        is_primary = request.form.get('is_primary') == 'on'
        if is_primary:
            PatientInsurance.query.filter_by(
                patient_id=patient.id, is_primary=True
            ).update({'is_primary': False})
        
        policy = PatientInsurance(
            patient_id=patient.id,
            provider_id=provider_id,
            policy_number=request.form.get('policy_number', '').strip(),
            group_number=request.form.get('group_number', '').strip(),
            member_id=request.form.get('member_id', '').strip(),
            policy_holder_name=request.form.get('policy_holder_name', patient.full_name),
            relationship_to_patient=request.form.get('relationship', 'self'),
            coverage_type=request.form.get('coverage_type', 'individual'),
            plan_type=request.form.get('plan_type', ''),
            plan_name=request.form.get('plan_name', ''),
            effective_date=effective_date,
            expiry_date=expiry_date,
            coverage_percentage=int(request.form.get('coverage_percentage', 80)),
            deductible=float(request.form.get('deductible', 0)),
            copay_amount=float(request.form.get('copay', 0)),
            is_primary=is_primary,
            is_active=True,
            verification_status='pending'
        )
        
        db.session.add(policy)
        db.session.commit()
        
        flash('Insurance policy added successfully!', 'success')
        return redirect(url_for('patient.insurance'))
    
    return render_template('patient/add_insurance.html', providers=providers)


@patient_bp.route('/insurance/<int:policy_id>/remove', methods=['POST'])
@login_required
@patient_required
def remove_insurance(policy_id):
    """Remove/deactivate insurance policy"""
    patient = get_current_patient()
    policy = PatientInsurance.query.get_or_404(policy_id)
    
    if policy.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.insurance'))
    
    policy.is_active = False
    db.session.commit()
    
    flash('Insurance policy removed.', 'success')
    return redirect(url_for('patient.insurance'))


@patient_bp.route('/insurance/claims')
@login_required
@patient_required
def insurance_claims():
    """View insurance claims"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    claims = InsuranceClaim.query.filter_by(
        patient_id=patient.id
    ).order_by(InsuranceClaim.submitted_at.desc()).all()
    
    return render_template('patient/insurance_claims.html', claims=claims)


# ============ PRESCRIPTIONS ============

@patient_bp.route('/prescriptions')
@login_required
@patient_required
def prescriptions():
    """View all prescriptions"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Prescription.query.filter_by(patient_id=patient.id)
    
    if status:
        query = query.filter_by(status=status)
    
    prescriptions = query.order_by(Prescription.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('patient/prescriptions.html',
                         prescriptions=prescriptions,
                         status=status)
@patient_bp.route('/prescription/<int:prescription_id>')
@login_required
@patient_required
def prescription_detail(prescription_id):
    """View single prescription"""
    patient = get_current_patient()
    
    if not patient:
        flash('Patient profile not found.', 'error')
        return render_template('patient/no_profile.html')
    
    prescription = Prescription.query.get_or_404(prescription_id)
    
    if prescription.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.prescriptions'))
    
    return render_template('patient/prescription_detail.html',
                         prescription=prescription)


@patient_bp.route('/prescription/<int:prescription_id>')
@login_required
@patient_required
def view_prescription(prescription_id):
    """View prescription details"""
    patient = get_current_patient()
    prescription = Prescription.query.get_or_404(prescription_id)
    
    if prescription.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.prescriptions'))
    
    return render_template('patient/view_prescription.html', prescription=prescription)


# ============ PROFILE ============

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def profile():
    """Patient profile management"""
    patient = get_current_patient()
    
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    if request.method == 'POST':
        # Update basic info
        patient.full_name = request.form.get('full_name', patient.full_name)
        patient.phone = request.form.get('phone', patient.phone)
        patient.email = request.form.get('email', patient.email)
        patient.address = request.form.get('address', '')
        patient.city = request.form.get('city', '')
        patient.state = request.form.get('state', '')
        patient.pincode = request.form.get('pincode', '')
        patient.blood_group = request.form.get('blood_group', '')
        
        # Update age
        age_str = request.form.get('age', '')
        if age_str:
            try:
                patient.age = int(age_str)
            except:
                pass
        
        # Update date of birth
        dob_str = request.form.get('date_of_birth', '')
        if dob_str:
            try:
                from datetime import datetime
                patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except:
                pass
        
        patient.gender = request.form.get('gender', patient.gender)
        
        # Emergency contact
        patient.emergency_contact_name = request.form.get('emergency_contact_name', '')
        patient.emergency_contact_phone = request.form.get('emergency_contact_phone', '')
        patient.emergency_contact_relation = request.form.get('emergency_contact_relation', '')
        
        # Lifestyle
        patient.smoking_status = request.form.get('smoking_status', 'never')
        patient.alcohol_consumption = request.form.get('alcohol_consumption', 'never')
        patient.food_preference = request.form.get('food_preference', 'non-vegetarian')
        patient.exercise_frequency = request.form.get('exercise_frequency', 'none')
        patient.current_medications = request.form.get('current_medications', '')
        
        # Handle profile picture
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                allowed = {'png', 'jpg', 'jpeg', 'gif'}
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                
                if ext in allowed:
                    import os
                    import uuid
                    from flask import current_app
                    
                    filename = f"patient_{patient.id}_{uuid.uuid4().hex[:8]}.{ext}"
                    upload_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'],
                        'profile_pictures',
                        filename
                    )
                    
                    # Delete old picture
                    if patient.profile_picture and patient.profile_picture != 'default_patient.png':
                        old_path = os.path.join(
                            current_app.config['UPLOAD_FOLDER'],
                            'profile_pictures',
                            patient.profile_picture
                        )
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    file.save(upload_path)
                    patient.profile_picture = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient.profile'))
    
    # Get counts for stats
    from app.models.prescription import Prescription
    from app.models.appointment import Appointment
    from app.models.report import Report
    
    prescriptions_count = Prescription.query.filter_by(patient_id=patient.id).count()
    appointments_count = Appointment.query.filter_by(patient_id=patient.id).count()
    reports_count = Report.query.filter_by(patient_id=patient.id).count()
    
    return render_template('patient/profile.html',
                         patient=patient,
                         prescriptions_count=prescriptions_count,
                         appointments_count=appointments_count,
                         reports_count=reports_count)


@patient_bp.route('/complete-profile', methods=['GET', 'POST'])
@login_required
@patient_required
def complete_profile():
    """Complete patient profile (first time setup)"""
    existing = get_current_patient()
    if existing:
        return redirect(url_for('patient.profile'))
    
    if request.method == 'POST':
        patient = Patient(
            user_id=current_user.id,
            patient_id=Patient.generate_patient_id(),
            full_name=request.form.get('full_name', current_user.full_name),
            age=int(request.form.get('age', 0)),
            gender=request.form.get('gender', ''),
            blood_group=request.form.get('blood_group', ''),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', current_user.email),
            address=request.form.get('address', ''),
            emergency_contact_name=request.form.get('emergency_contact_name', ''),
            emergency_contact_phone=request.form.get('emergency_contact_phone', ''),
            emergency_contact_relation=request.form.get('emergency_contact_relation', ''),
            survey_completed=True
        )
        
        db.session.add(patient)
        db.session.commit()
        
        flash('Profile completed successfully!', 'success')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/complete_profile.html')


# ============ DOCTORS ============

@patient_bp.route('/find-doctors')
@login_required
@patient_required
def find_doctors():
    """Find and browse doctors"""
    specialty = request.args.get('specialty', '')
    department = request.args.get('department', '')
    search = request.args.get('search', '')
    
    query = User.query.filter_by(role='doctor', is_active=True)
    
    if specialty:
        query = query.filter(User.specialization.ilike(f'%{specialty}%'))
    
    if department:
        query = query.filter(User.department.ilike(f'%{department}%'))
    
    if search:
        query = query.filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                User.specialization.ilike(f'%{search}%')
            )
        )
    
    doctors = query.order_by(User.average_rating.desc()).all()
    
    # Get specializations for filter
    specializations = db.session.query(User.specialization).filter(
        User.role == 'doctor',
        User.specialization.isnot(None)
    ).distinct().all()
    specializations = [s[0] for s in specializations if s[0]]
    
    # Get departments for filter
    departments = db.session.query(User.department).filter(
        User.role == 'doctor',
        User.department.isnot(None)
    ).distinct().all()
    departments = [d[0] for d in departments if d[0]]
    
    return render_template('patient/find_doctors.html',
                         doctors=doctors,
                         specializations=specializations,
                         departments=departments,
                         current_specialty=specialty,
                         current_department=department,
                         search=search)


@patient_bp.route('/doctor/<int:doctor_id>')
@login_required
@patient_required
def view_doctor(doctor_id):
    """View doctor profile"""
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first_or_404()
    
    # Get recent reviews
    reviews = Feedback.query.filter_by(
        doctor_id=doctor_id,
        is_approved=True
    ).order_by(Feedback.created_at.desc()).limit(10).all()
    
    return render_template('patient/view_doctor.html',
                         doctor=doctor,
                         reviews=reviews)
# ============ REMINDERS ============
@patient_bp.route('/save-reminder-settings', methods=['POST'])
@login_required
@patient_required
def save_reminder_settings():
    """Save patient reminder settings"""
    patient = get_current_patient()
    
    if not patient:
        flash('Patient profile not found.', 'error')
        return redirect(url_for('patient.reminders'))
    
    try:
        from app.models.reminder import ReminderSetting
        
        # Get or create settings
        settings = ReminderSetting.query.filter_by(patient_id=patient.id).first()
        
        if not settings:
            settings = ReminderSetting(patient_id=patient.id)
            db.session.add(settings)
        
        # Update settings from form
        settings.is_active = request.form.get('enable_reminders') == 'on'
        settings.email_enabled = request.form.get('email_enabled') == 'on'
        settings.reminder_email = request.form.get('reminder_email', '').strip() or patient.email
        settings.morning_time = request.form.get('morning_time', '08:00')
        settings.afternoon_time = request.form.get('afternoon_time', '13:00')
        settings.evening_time = request.form.get('evening_time', '18:00')
        settings.night_time = request.form.get('night_time', '21:00')
        
        db.session.commit()
        flash('Reminder settings saved successfully!', 'success')
        
    except ImportError:
        # ReminderSetting model doesn't exist - just show message
        flash('Reminder settings saved! (Note: Full reminder system requires database migration)', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving settings: {str(e)}', 'error')
    
    return redirect(url_for('patient.reminders'))

@patient_bp.route('/reminders')
@login_required
@patient_required
def reminders():
    """View medication and appointment reminders"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    today = date.today()
    
    # Get upcoming appointments as reminders
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(10).all()
    
    # Get active prescriptions for medication reminders
    active_prescriptions = Prescription.query.filter_by(
        patient_id=patient.id,
        status='active'
    ).all()
    
    return render_template('patient/reminders.html',
                         patient=patient,
                         upcoming_appointments=upcoming_appointments,
                         active_prescriptions=active_prescriptions)


# ============ MEDICAL SUMMARY ============

@patient_bp.route('/medical-summary')
@login_required
@patient_required
def medical_summary():
    """View patient's medical summary"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    # Get all prescriptions
    all_prescriptions = Prescription.query.filter_by(
        patient_id=patient.id
    ).order_by(Prescription.created_at.desc()).all()
    
    # Get all appointments
    all_appointments = Appointment.query.filter_by(
        patient_id=patient.id
    ).order_by(Appointment.appointment_date.desc()).limit(20).all()
    
    # Get all reports
    all_reports = Report.query.filter_by(
        patient_id=patient.id
    ).order_by(Report.created_at.desc()).all()
    
    # Calculate stats
    stats = {
        'total_appointments': Appointment.query.filter_by(patient_id=patient.id).count(),
        'completed_appointments': Appointment.query.filter_by(patient_id=patient.id, status='completed').count(),
        'total_prescriptions': len(all_prescriptions),
        'active_prescriptions': Prescription.query.filter_by(patient_id=patient.id, status='active').count(),
        'total_reports': len(all_reports)
    }
    
    return render_template('patient/medical_summary.html',
                         patient=patient,
                         prescriptions=all_prescriptions,
                         appointments=all_appointments,
                         reports=all_reports,
                         stats=stats)


# ============ REPORTS ============

@patient_bp.route('/reports')
@login_required
@patient_required
def reports():
    """View patient's medical reports"""
    patient = get_current_patient()
    if not patient:
        return redirect(url_for('patient.complete_profile'))
    
    page = request.args.get('page', 1, type=int)
    report_type = request.args.get('type', '')
    
    query = Report.query.filter_by(patient_id=patient.id)
    
    if report_type:
        query = query.filter_by(report_type=report_type)
    
    reports = query.order_by(Report.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get report types for filter
    report_types = db.session.query(Report.report_type).filter_by(
        patient_id=patient.id
    ).distinct().all()
    report_types = [r[0] for r in report_types if r[0]]
    
    return render_template('patient/reports.html',
                         reports=reports,
                         report_types=report_types,
                         current_type=report_type)


@patient_bp.route('/report/<int:report_id>')
@login_required
@patient_required
def view_report(report_id):
    """View a specific report"""
    patient = get_current_patient()
    report = Report.query.get_or_404(report_id)
    
    if report.patient_id != patient.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.reports'))
    
    return render_template('patient/view_report.html', report=report)
@patient_bp.route('/food-detection', methods=['GET', 'POST'])  # Both methods!
@login_required
@patient_required
def food_detection():
    """Detect and analyze food from image"""
    patient = get_current_patient()
    result = None
    
    if request.method == 'POST':
        if 'food_image' not in request.files:
            flash('No image uploaded.', 'error')
            return render_template('patient/food_detection.html', patient=patient)
        
        file = request.files['food_image']
        
        if file.filename == '':
            flash('No image selected.', 'error')
            return render_template('patient/food_detection.html', patient=patient)
        
        if file:
            try:
                # Save the file temporarily
                import os
                from werkzeug.utils import secure_filename
                from flask import current_app
                
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'food_images')
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                
                # Analyze the food image
                from app.services.food_detection_ml import FoodDetectionService
                food_service = FoodDetectionService()
                detected_foods = food_service.detect_food(filepath)
                
                # Get patient's medicines
                current_medicines = []
                active_prescriptions = Prescription.query.filter_by(
                    patient_id=patient.id,
                    status='active'
                ).all()
                
                for rx in active_prescriptions:
                    for med in rx.medicines.all():
                        if med.medicine_name not in current_medicines:
                            current_medicines.append(med.medicine_name)
                
                # Analyze for interactions
                if detected_foods and current_medicines:
                    from app.services.meal_analyzer import MealAnalyzer
                    analyzer = MealAnalyzer()
                    meal_text = ', '.join(detected_foods)
                    result = analyzer.analyze_meal(meal_text, current_medicines)
                    result['detected_foods'] = detected_foods
                else:
                    result = {
                        'detected_foods': detected_foods,
                        'is_safe': True,
                        'message': 'Foods detected but no active medications to check against.',
                        'warnings': []
                    }
                
                # Clean up
                os.remove(filepath)
                
            except Exception as e:
                flash(f'Error analyzing image: {str(e)}', 'error')
                import traceback
                traceback.print_exc()
    
    return render_template('patient/food_detection.html', 
                          patient=patient, 
                          result=result)