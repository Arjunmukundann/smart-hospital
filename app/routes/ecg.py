"""
ECG Routes - ECG Arrhythmia Detection in Admin Module
"""

import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps

from app.extensions import db
from app.models.ecg_record import ECGPatient, ECGResult
from app.services.ecg_service import ecg_service

ecg_bp = Blueprint('ecg', __name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required for ECG detection.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    """Check if file is allowed"""
    ALLOWED_EXTENSIONS = {'csv', 'txt', 'dat'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== MAIN ECG ROUTES ====================

@ecg_bp.route('/')
@login_required
@admin_required
def index():
    """ECG Detection Dashboard"""
    # Check if models are loaded
    models_loaded = ecg_service.models_loaded
    
    # Get recent results
    recent_results = ECGResult.query.order_by(
        ECGResult.analysis_date.desc()
    ).limit(10).all()
    
    # Statistics
    total_tests = ECGResult.query.count()
    risk_counts = {
        'normal': ECGResult.query.filter_by(risk_level='NORMAL').count(),
        'low': ECGResult.query.filter_by(risk_level='LOW').count(),
        'moderate': ECGResult.query.filter_by(risk_level='MODERATE').count(),
        'high': ECGResult.query.filter_by(risk_level='HIGH').count(),
        'unknown': ECGResult.query.filter_by(risk_level='UNKNOWN').count()
    }
    
    return render_template('admin/ecg_detection.html',
                         models_loaded=models_loaded,
                         recent_results=recent_results,
                         total_tests=total_tests,
                         risk_counts=risk_counts)


@ecg_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload():
    """Upload and analyze ECG file"""
    if not ecg_service.models_loaded:
        flash('ECG models not loaded. Please check server configuration.', 'error')
        return redirect(url_for('ecg.index'))
    
    if request.method == 'POST':
        # Get form data
        patient_name = request.form.get('patient_name', '').strip()
        patient_age = request.form.get('patient_age', '')
        patient_gender = request.form.get('patient_gender', '')
        hospital_patient_id = request.form.get('hospital_patient_id', type=int)
        
        # Validate
        if not patient_name or not patient_age or not patient_gender:
            flash('All patient fields are required.', 'error')
            return render_template('admin/ecg_upload.html')
        
        if 'ecg_file' not in request.files:
            flash('No ECG file uploaded.', 'error')
            return render_template('admin/ecg_upload.html')
        
        file = request.files['ecg_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return render_template('admin/ecg_upload.html')
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload CSV, TXT, or DAT file.', 'error')
            return render_template('admin/ecg_upload.html')
        
        try:
            # Create ECG patient record
            ecg_patient = ECGPatient(
                hospital_patient_id=hospital_patient_id,
                name=patient_name,
                age=int(patient_age),
                gender=patient_gender,
                uploaded_by=current_user.id
            )
            db.session.add(ecg_patient)
            db.session.flush()
            
            # Save file
            filename = secure_filename(f"ecg_{ecg_patient.id}_{int(datetime.now().timestamp())}.csv")
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'ecg')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            print(f"\n{'='*60}")
            print(f"📤 Processing ECG Upload")
            print(f"{'='*60}")
            print(f"Patient: {patient_name}, Age: {patient_age}, Gender: {patient_gender}")
            print(f"File: {filename}")
            
            # Read ECG data
            ecg_data = ecg_service.read_ecg_file(filepath)
            
            if len(ecg_data) < 360:
                db.session.rollback()
                flash(f'ECG file too short: {len(ecg_data)} samples (need at least 360).', 'error')
                return render_template('admin/ecg_upload.html')
            
            # Analyze
            result = ecg_service.analyze_ecg(ecg_data)
            
            if not result.get('success'):
                db.session.rollback()
                flash(result.get('error', 'Analysis failed.'), 'error')
                return render_template('admin/ecg_upload.html')
            
            # Save result
            stats = result.get('statistics', {})
            class_dist = stats.get('class_distribution', {})
            
            ecg_result = ECGResult(
                ecg_patient_id=ecg_patient.id,
                file_name=filename,
                file_path=filepath,
                predictions=json.dumps({
                    'predictions': result.get('predictions', []),
                    'waveform_data': result.get('waveform_data', [])
                }),
                risk_level=result.get('risk_level', 'UNKNOWN'),
                confidence=result.get('confidence', 0),
                total_beats=stats.get('total_beats', 0),
                normal_beats=class_dist.get('N', 0),
                ventricular_beats=class_dist.get('V', 0),
                supraventricular_beats=class_dist.get('S', 0),
                fusion_beats=class_dist.get('F', 0),
                unknown_beats=class_dist.get('Q', 0),
                duration_seconds=stats.get('duration_seconds', 0),
                sampling_rate=stats.get('sampling_rate', 360),
                message=result.get('message', '')
            )
            
            db.session.add(ecg_result)
            db.session.commit()
            
            flash(f'ECG analyzed successfully! {result.get("message", "")}', 'success')
            return redirect(url_for('ecg.view_result', result_id=ecg_result.id))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error analyzing ECG: {str(e)[:200]}', 'error')
            return render_template('admin/ecg_upload.html')
    
    # GET - Get hospital patients for dropdown
    from app.models import Patient
    hospital_patients = Patient.query.order_by(Patient.full_name).limit(100).all()
    
    return render_template('admin/ecg_upload.html', hospital_patients=hospital_patients)


@ecg_bp.route('/result/<int:result_id>')
@login_required
@admin_required
def view_result(result_id):
    """View ECG analysis result"""
    result = ECGResult.query.get_or_404(result_id)
    
    # Get predictions data
    pred_data = result.get_predictions()
    waveform_data = pred_data.get('waveform_data', [])
    beat_predictions = pred_data.get('predictions', [])
    
    return render_template('admin/ecg_result.html',
                         result=result,
                         waveform_data=waveform_data,
                         beat_predictions=beat_predictions)


@ecg_bp.route('/results')
@login_required
@admin_required
def all_results():
    """View all ECG results"""
    page = request.args.get('page', 1, type=int)
    risk_filter = request.args.get('risk', '')
    
    query = ECGResult.query
    
    if risk_filter:
        query = query.filter_by(risk_level=risk_filter.upper())
    
    results = query.order_by(ECGResult.analysis_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/ecg_results.html',
                         results=results,
                         risk_filter=risk_filter)


@ecg_bp.route('/result/<int:result_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_result(result_id):
    """Delete ECG result"""
    result = ECGResult.query.get_or_404(result_id)
    
    # Delete file if exists
    if result.file_path and os.path.exists(result.file_path):
        try:
            os.remove(result.file_path)
        except:
            pass
    
    db.session.delete(result)
    db.session.commit()
    
    flash('ECG result deleted.', 'success')
    return redirect(url_for('ecg.all_results'))


# ==================== API ENDPOINTS ====================

@ecg_bp.route('/api/analyze', methods=['POST'])
@login_required
def api_analyze():
    """API endpoint for ECG analysis"""
    if not ecg_service.models_loaded:
        return jsonify({'success': False, 'error': 'Models not loaded'}), 500
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        # Save temp file
        filename = secure_filename(f"temp_ecg_{int(datetime.now().timestamp())}.csv")
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'ecg', 'temp')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Read and analyze
        ecg_data = ecg_service.read_ecg_file(filepath)
        
        if len(ecg_data) < 360:
            os.remove(filepath)
            return jsonify({'success': False, 'error': 'ECG too short'}), 400
        
        result = ecg_service.analyze_ecg(ecg_data)
        
        # Clean up
        os.remove(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ecg_bp.route('/api/status')
@login_required
def api_status():
    """Check ECG service status"""
    return jsonify({
        'models_loaded': ecg_service.models_loaded,
        'model_path': ecg_service.model_path
    })