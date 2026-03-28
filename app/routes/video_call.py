"""
Video Consultation Routes - WebRTC video calls
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Patient
from app.models.appointment import Appointment
from app.models.video_consultation import VideoSession
from app.services.video_service import VideoService

video_bp = Blueprint('video', __name__)


@video_bp.route('/room/<room_id>')
@login_required
def video_room(room_id):
    """Video consultation room"""
    session = VideoSession.query.filter_by(room_id=room_id).first_or_404()
    
    # Verify user is part of this session
    user_type = None
    if current_user.is_doctor():
        if session.doctor_id != current_user.id:
            flash('You are not authorized to join this session.', 'error')
            return redirect(url_for('doctor.dashboard'))
        user_type = 'doctor'
    elif current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient or session.patient_id != patient.id:
            flash('You are not authorized to join this session.', 'error')
            return redirect(url_for('patient.dashboard'))
        user_type = 'patient'
    else:
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    # Check if session can be joined
    if not session.can_join and session.status != 'active':
        flash('This video session is not available right now.', 'warning')
        if user_type == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        return redirect(url_for('patient.dashboard'))
    
    # Generate access token
    token = VideoService.generate_token(room_id, current_user.id, user_type)
    
    # Get appointment details
    appointment = session.appointment
    
    # Get other participant details
    if user_type == 'doctor':
        other_participant = {
            'name': session.patient_rel.full_name if session.patient_rel else 'Patient',
            'type': 'patient'
        }
    else:
        other_participant = {
            'name': session.doctor.full_name if session.doctor else 'Doctor',
            'type': 'doctor'
        }
    
    return render_template('video/room.html',
                         session=session,
                         appointment=appointment,
                         token=token,
                         user_type=user_type,
                         room_id=room_id,
                         other_participant=other_participant)


@video_bp.route('/start/<int:appointment_id>', methods=['POST'])
@login_required
def start_consultation(appointment_id):
    """Start video consultation (doctor initiates)"""
    if not current_user.is_doctor():
        return jsonify({'error': 'Only doctors can start video consultations'}), 403
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Verify this is the doctor's appointment
    if appointment.doctor_id != current_user.id:
        return jsonify({'error': 'This is not your appointment'}), 403
    
    # Check appointment type
    if appointment.appointment_type != 'video':
        return jsonify({'error': 'This is not a video consultation appointment'}), 400
    
    # Check appointment status
    if appointment.status not in ['scheduled', 'confirmed']:
        return jsonify({'error': 'This appointment cannot be started'}), 400
    
    # Check if session already exists
    existing_session = VideoSession.query.filter_by(appointment_id=appointment_id).first()
    if existing_session:
        if existing_session.status == 'ended':
            return jsonify({'error': 'This session has already ended'}), 400
        return jsonify({
            'success': True,
            'room_id': existing_session.room_id,
            'redirect_url': url_for('video.video_room', room_id=existing_session.room_id)
        })
    
    # Create new session
    session = VideoSession(
        room_id=VideoSession.generate_room_id(),
        appointment_id=appointment_id,
        doctor_id=current_user.id,
        patient_id=appointment.patient_id,
        scheduled_at=datetime.combine(appointment.appointment_date, appointment.appointment_time),
        status='waiting'
    )
    
    db.session.add(session)
    
    # Update appointment
    appointment.video_room_id = session.room_id
    appointment.status = 'confirmed'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'room_id': session.room_id,
        'redirect_url': url_for('video.video_room', room_id=session.room_id)
    })


@video_bp.route('/join/<room_id>')
@login_required
def join_consultation(room_id):
    """Join video consultation (patient joins via link)"""
    session = VideoSession.query.filter_by(room_id=room_id).first()
    
    if not session:
        flash('Video session not found.', 'error')
        if current_user.is_patient():
            return redirect(url_for('patient.dashboard'))
        return redirect(url_for('main.index'))
    
    if session.status == 'ended':
        flash('This video session has ended.', 'warning')
        if current_user.is_patient():
            return redirect(url_for('patient.dashboard'))
        return redirect(url_for('main.index'))
    
    return redirect(url_for('video.video_room', room_id=room_id))


@video_bp.route('/end/<room_id>', methods=['POST'])
@login_required
def end_consultation(room_id):
    """End video consultation"""
    session = VideoSession.query.filter_by(room_id=room_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Verify user is part of this session
    is_authorized = False
    if current_user.is_doctor() and session.doctor_id == current_user.id:
        is_authorized = True
    elif current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if patient and session.patient_id == patient.id:
            is_authorized = True
    
    if not is_authorized:
        return jsonify({'error': 'Not authorized'}), 403
    
    # End session
    session.end_session()
    
    # Update appointment
    appointment = session.appointment
    if appointment:
        appointment.status = 'completed'
        appointment.video_call_ended_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Video consultation ended',
        'duration_seconds': session.duration_seconds
    })


@video_bp.route('/session-info/<room_id>')
@login_required
def session_info(room_id):
    """Get video session information"""
    session = VideoSession.query.filter_by(room_id=room_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(session.to_dict())


# ============ API ENDPOINTS FOR WEBRTC ============

@video_bp.route('/api/join/<room_id>', methods=['POST'])
@login_required
def api_join_room(room_id):
    """API endpoint when user joins the room"""
    session = VideoSession.query.filter_by(room_id=room_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    if current_user.is_doctor() and session.doctor_id == current_user.id:
        session.doctor_join()
        if not session.started_at:
            session.start_session()
    elif current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if patient and session.patient_id == patient.id:
            session.patient_join()
            if session.doctor_joined and not session.started_at:
                session.start_session()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'session_status': session.status,
        'doctor_joined': session.doctor_joined,
        'patient_joined': session.patient_joined
    })


@video_bp.route('/api/leave/<room_id>', methods=['POST'])
@login_required
def api_leave_room(room_id):
    """API endpoint when user leaves the room"""
    session = VideoSession.query.filter_by(room_id=room_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # If doctor leaves, end the session
    if current_user.is_doctor() and session.doctor_id == current_user.id:
        session.end_session()
        if session.appointment:
            session.appointment.status = 'completed'
    
    db.session.commit()
    
    return jsonify({'success': True})


@video_bp.route('/api/update-quality/<room_id>', methods=['POST'])
@login_required
def api_update_quality(room_id):
    """Update connection quality metrics"""
    session = VideoSession.query.filter_by(room_id=room_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    quality = request.json.get('quality', 'good')  # good, fair, poor
    
    if current_user.is_doctor() and session.doctor_id == current_user.id:
        session.doctor_connection_quality = quality
    elif current_user.is_patient():
        session.patient_connection_quality = quality
    
    db.session.commit()
    
    return jsonify({'success': True})