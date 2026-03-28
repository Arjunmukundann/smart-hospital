"""
Appointment Routes - Booking and management
"""

from datetime import datetime, date, time, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Patient, DoctorAvailability
from app.models.appointment import Appointment, TimeSlot
from app.models.video_consultation import VideoSession

appointment_bp = Blueprint('appointment', __name__)


@appointment_bp.route('/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    """Book a new appointment"""
    # Get available doctors
    doctors = User.query.filter_by(role='doctor', is_active=True).all()
    
    # Get patient (for patient users)
    patient = None
    if current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Please complete your patient profile first.', 'warning')
            return redirect(url_for('patient.profile'))
    
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id', type=int)
        patient_id = request.form.get('patient_id', type=int)
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        appointment_type = request.form.get('appointment_type', 'in_person')
        reason = request.form.get('reason', '')
        
        # Validation
        if not all([doctor_id, appointment_date, appointment_time]):
            flash('Please fill in all required fields.', 'error')
            return render_template('appointment/book.html', doctors=doctors, patient=patient)
        
        try:
            apt_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            apt_time = datetime.strptime(appointment_time, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'error')
            return render_template('appointment/book.html', doctors=doctors, patient=patient)
        
        # Check if date is in future
        apt_datetime = datetime.combine(apt_date, apt_time)
        if apt_datetime <= datetime.now():
            flash('Please select a future date and time.', 'error')
            return render_template('appointment/book.html', doctors=doctors, patient=patient)
        
        # Get patient ID
        if current_user.is_patient():
            patient_id = patient.id
        elif not patient_id:
            flash('Please select a patient.', 'error')
            return render_template('appointment/book.html', doctors=doctors, patient=patient)
        
        # Check for existing appointment at same time
        existing = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == apt_date,
            Appointment.appointment_time == apt_time,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).first()
        
        if existing:
            flash('This time slot is already booked. Please choose another time.', 'error')
            return render_template('appointment/book.html', doctors=doctors, patient=patient)
        
        # Get doctor's fee
        doctor = User.query.get(doctor_id)
        if appointment_type == 'video':
            fee = doctor.video_consultation_fee or doctor.consultation_fee or 0
        else:
            fee = doctor.consultation_fee or 0
        
        # Create appointment
        appointment = Appointment(
            appointment_number=Appointment.generate_appointment_number(),
            patient_id=patient_id,
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
            
            # Send notification to doctor
            doctor = User.query.get(doctor_id)
            if doctor and doctor.email:
                NotificationService.send_email(
                    to_email=doctor.email,
                    template_name='new_appointment_request',
                    context={
                        'doctor_name': doctor.full_name,
                        'patient_name': patient.full_name if patient else 'Patient',
                        'appointment_date': apt_date.strftime('%B %d, %Y'),
                        'appointment_time': apt_time.strftime('%I:%M %p'),
                        'appointment_type': 'Video Consultation' if appointment_type == 'video' else 'In-Person',
                        'reason': reason,
                        'appointment_number': appointment.appointment_number
                    }
                )
        except Exception as e:
            print(f"Error sending notification: {e}")
        flash(f'Appointment booked successfully! Appointment #: {appointment.appointment_number}', 'success')
        
        if current_user.is_patient():
            return redirect(url_for('patient.appointments'))
        else:
            return redirect(url_for('appointment.view', appointment_id=appointment.id))
    
    # GET request
    # If doctor is pre-selected
    selected_doctor_id = request.args.get('doctor_id', type=int)
    selected_date = request.args.get('date', '')
    
    return render_template('patient/book_appointment.html',
                         doctors=doctors,
                         patient=patient,
                         selected_doctor_id=selected_doctor_id,
                         selected_date=selected_date)


@appointment_bp.route('/view/<int:appointment_id>')
@login_required
def view(appointment_id):
    """View appointment details"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check access
    if current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient or appointment.patient_id != patient.id:
            flash('Access denied.', 'error')
            return redirect(url_for('patient.dashboard'))
    elif current_user.is_doctor():
        if appointment.doctor_id != current_user.id:
            flash('Access denied.', 'error')
            return redirect(url_for('doctor.dashboard'))
    
    return render_template('appointment/view.html', appointment=appointment)


@appointment_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel(appointment_id):
    """Cancel an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check access
    can_cancel = False
    if current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        can_cancel = patient and appointment.patient_id == patient.id
    elif current_user.is_doctor():
        can_cancel = appointment.doctor_id == current_user.id
    elif current_user.is_admin():
        can_cancel = True
    
    if not can_cancel:
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    if appointment.status in ['completed', 'cancelled']:
        flash('This appointment cannot be cancelled.', 'error')
        return redirect(url_for('appointment.view', appointment_id=appointment_id))
    
    reason = request.form.get('cancellation_reason', 'Cancelled by user')
    
    appointment.status = 'cancelled'
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancellation_reason = reason
    
    db.session.commit()
    
    flash('Appointment cancelled successfully.', 'success')
    
    if current_user.is_patient():
        return redirect(url_for('patient.appointments'))
    elif current_user.is_doctor():
        return redirect(url_for('doctor.appointments'))
    else:
        return redirect(url_for('admin.appointments'))


@appointment_bp.route('/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def reschedule(appointment_id):
    """Reschedule an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if request.method == 'POST':
        new_date = request.form.get('appointment_date')
        new_time = request.form.get('appointment_time')
        
        try:
            apt_date = datetime.strptime(new_date, '%Y-%m-%d').date()
            apt_time = datetime.strptime(new_time, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'error')
            return render_template('appointment/reschedule.html', appointment=appointment)
        
        # Check if new slot is available
        existing = Appointment.query.filter(
            Appointment.id != appointment.id,
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == apt_date,
            Appointment.appointment_time == apt_time,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).first()
        
        if existing:
            flash('This time slot is already booked.', 'error')
            return render_template('appointment/reschedule.html', appointment=appointment)
        
        appointment.appointment_date = apt_date
        appointment.appointment_time = apt_time
        appointment.status = 'scheduled'
        
        db.session.commit()
        
        flash('Appointment rescheduled successfully!', 'success')
        return redirect(url_for('appointment.view', appointment_id=appointment.id))
    
    return render_template('appointment/reschedule.html', appointment=appointment)


@appointment_bp.route('/confirm/<int:appointment_id>', methods=['POST'])
@login_required
def confirm(appointment_id):
    """Confirm an appointment (doctor only)"""
    if not current_user.is_doctor() and not current_user.is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if current_user.is_doctor() and appointment.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.dashboard'))
    
    appointment.status = 'confirmed'
    db.session.commit()
    
    flash('Appointment confirmed.', 'success')
    return redirect(url_for('doctor.appointments'))


@appointment_bp.route('/complete/<int:appointment_id>', methods=['POST'])
@login_required
def complete(appointment_id):
    """Mark appointment as completed"""
    if not current_user.is_doctor():
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor.dashboard'))
    
    appointment.status = 'completed'
    db.session.commit()
    
    flash('Appointment marked as completed.', 'success')
    return redirect(url_for('doctor.appointments'))


# ============ API ENDPOINTS ============

@appointment_bp.route('/api/available-slots')
@login_required
def api_available_slots():
    """Get available time slots for a doctor on a specific date"""
    doctor_id = request.args.get('doctor_id', type=int)
    date_str = request.args.get('date')
    appointment_type = request.args.get('type', 'both')
    
    if not doctor_id or not date_str:
        return jsonify({'error': 'Doctor ID and date required'}), 400
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    if selected_date < date.today():
        return jsonify({'error': 'Cannot book appointments in the past'}), 400
    
    doctor = User.query.get(doctor_id)
    if not doctor or not doctor.is_doctor():
        return jsonify({'error': 'Invalid doctor'}), 400
    
    # Get doctor's availability for this day of week
    day_of_week = selected_date.weekday()  # 0 = Monday
    
    availability = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        day_of_week=day_of_week,
        is_active=True
    ).all()
    
    if not availability:
        # Default availability: 9 AM to 5 PM, 30-minute slots
        availability = [{
            'start_time': time(9, 0),
            'end_time': time(17, 0),
            'slot_duration': 30
        }]
    else:
        availability = [{
            'start_time': a.start_time,
            'end_time': a.end_time,
            'slot_duration': a.slot_duration or 30
        } for a in availability]
    
    # Generate all possible slots
    all_slots = []
    for avail in availability:
        current_time = datetime.combine(selected_date, avail['start_time'])
        end_time = datetime.combine(selected_date, avail['end_time'])
        slot_duration = timedelta(minutes=avail['slot_duration'])
        
        while current_time + slot_duration <= end_time:
            all_slots.append(current_time.time())
            current_time += slot_duration
    
    # Get already booked slots
    booked_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == selected_date,
        Appointment.status.in_(['scheduled', 'confirmed'])
    ).all()
    
    booked_times = [apt.appointment_time for apt in booked_appointments]
    
    # Filter out booked slots and past times (for today)
    available_slots = []
    now = datetime.now()
    
    for slot_time in all_slots:
        if slot_time in booked_times:
            continue
        
        # If today, check if time has passed
        if selected_date == date.today():
            slot_datetime = datetime.combine(selected_date, slot_time)
            if slot_datetime <= now:
                continue
        
        available_slots.append({
            'time': slot_time.strftime('%H:%M'),
            'display': slot_time.strftime('%I:%M %p')
        })
    
    return jsonify({
        'date': date_str,
        'doctor': {
            'id': doctor.id,
            'name': doctor.full_name,
            'specialization': doctor.specialization
        },
        'slots': available_slots
    })


@appointment_bp.route('/api/doctor-schedule/<int:doctor_id>')
@login_required
def api_doctor_schedule(doctor_id):
    """Get doctor's weekly schedule"""
    doctor = User.query.get_or_404(doctor_id)
    
    if not doctor.is_doctor():
        return jsonify({'error': 'Invalid doctor'}), 400
    
    availability = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        is_active=True
    ).all()
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    schedule = []
    
    for avail in availability:
        schedule.append({
            'day': days[avail.day_of_week],
            'day_index': avail.day_of_week,
            'start_time': avail.start_time.strftime('%H:%M'),
            'end_time': avail.end_time.strftime('%H:%M'),
            'slot_duration': avail.slot_duration,
            'consultation_type': avail.consultation_type
        })
    
    return jsonify({
        'doctor': {
            'id': doctor.id,
            'name': doctor.full_name,
            'specialization': doctor.specialization,
            'consultation_fee': doctor.consultation_fee,
            'video_consultation_fee': doctor.video_consultation_fee,
            'is_available_online': doctor.is_available_online
        },
        'schedule': schedule
    })


@appointment_bp.route('/api/upcoming')
@login_required
def api_upcoming_appointments():
    """Get upcoming appointments for current user"""
    if current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            return jsonify([])
        
        appointments = Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.appointment_date >= date.today(),
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(10).all()
    
    elif current_user.is_doctor():
        appointments = Appointment.query.filter(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date >= date.today(),
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(10).all()
    
    else:
        return jsonify([])
    
    return jsonify([apt.to_dict() for apt in appointments])