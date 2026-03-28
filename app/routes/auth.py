"""
Authentication Routes - With Patient Linking
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models.user import User
from app.models.patient import Patient

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        # Redirect to appropriate dashboard based on role
        if current_user.is_doctor():
            return redirect(url_for('doctor.dashboard'))
        elif current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_patient():
            # Check if patient has a profile
            patient = Patient.query.filter_by(user_id=current_user.id).first()
            if patient:
                return redirect(url_for('patient.dashboard'))
            else:
                # Try to find and link existing patient by email/phone
                linked = try_link_existing_patient(current_user)
                if linked:
                    flash(f'Welcome! Your account has been linked to existing patient record: {linked.patient_id}', 'success')
                    return redirect(url_for('patient.dashboard'))
                else:
                    # Create new patient profile if none exists
                    new_patient = Patient(
                        user_id=current_user.id,
                        patient_id=Patient.generate_patient_id(),
                        full_name=current_user.full_name,
                        age=0,
                        gender='Not Specified',
                        phone='Not Provided',
                        email=current_user.email,
                        survey_completed=False
                    )
                    db.session.add(new_patient)
                    db.session.commit()
                    flash('Welcome! Please complete your patient profile.', 'info')
                    return redirect(url_for('patient.complete_profile'))
    return render_template('index.html')


def try_link_existing_patient(user):
    """
    Try to find and link an existing patient record to this user.
    Matches by email or phone number.
    """
    # Find patient by email (if user has email)
    if user.email:
        existing_patient = Patient.query.filter(
            Patient.email == user.email,
            Patient.user_id.is_(None)  # Not already linked to another user
        ).first()
        
        if existing_patient:
            existing_patient.user_id = user.id
            db.session.commit()
            return existing_patient
    
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'error')
            return render_template('auth/login.html')
        
        if not user.is_active:
            flash('Your account is deactivated. Please contact administrator.', 'error')
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        user.update_last_login()
        
        flash(f'Welcome back, {user.full_name}!', 'success')
        
        # Redirect based on role
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        # The index route will handle patient linking
        return redirect(url_for('auth.index'))
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with automatic patient linking"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'patient')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        
        # ✅ FIX 1: BLOCK ADMIN REGISTRATION
        if role == 'admin':
            flash('Admin registration is not allowed. Please contact the system administrator.', 'error')
            return render_template('auth/register.html')
        
        # Only allow patient and doctor roles
        if role not in ['patient', 'doctor']:
            flash('Invalid role selected.', 'error')
            return render_template('auth/register.html')
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        
        if not full_name:
            errors.append('Full name is required.')
        
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Check existing users
        if User.query.filter_by(username=username).first():
            errors.append('Username already exists.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered. Please login instead.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        try:
            # Create user
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                role=role
            )
            user.set_password(password)
            
            # Doctor-specific fields
            if role == 'doctor':
                user.specialization = request.form.get('specialization', 'General Medicine')
                user.license_number = request.form.get('license_number', '')
            
            db.session.add(user)
            db.session.commit()  # Commit to get user.id
            
            # For patients, try to link existing patient record OR create new
            if role == 'patient':
                existing_patient = find_existing_patient(email, phone)
                
                if existing_patient:
                    # Link existing patient record to this user
                    existing_patient.user_id = user.id
                    
                    # Update patient info if needed
                    if not existing_patient.email:
                        existing_patient.email = email
                    if phone and (not existing_patient.phone or existing_patient.phone == 'Not Provided'):
                        existing_patient.phone = phone
                    
                    db.session.commit()
                    
                    flash(f'Registration successful! Your account has been linked to existing patient record: {existing_patient.patient_id}', 'success')
                else:
                    # Create new patient profile
                    patient = Patient(
                        user_id=user.id,
                        patient_id=Patient.generate_patient_id(),
                        full_name=full_name,
                        age=int(request.form.get('age', 0)) if request.form.get('age') else 0,
                        gender=request.form.get('gender', 'Not Specified'),
                        phone=phone if phone else 'Not Provided',
                        email=email,
                        survey_completed=False
                    )
                    db.session.add(patient)
                    db.session.commit()
                    
                    flash(f'Registration successful! Your Patient ID is: {patient.patient_id}', 'success')
            else:
                flash(f'{role.capitalize()} registration successful!', 'success')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed. Please try again. Error: {str(e)}', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')
@auth_bp.route('/register/pharmacist', methods=['GET', 'POST'])
def register_pharmacist():
    """Register as pharmacist (should be admin-only in production)"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register_pharmacist'))
        
        user = User(
            email=email,
            full_name=full_name,
            role='pharmacist',
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Pharmacist account created! You can now login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')


def find_existing_patient(email: str, phone: str) -> Patient:
    """
    Find existing patient record by email or phone.
    Only returns patients not already linked to a user.
    """
    
    # First try to find by email
    if email:
        patient = Patient.query.filter(
            db.func.lower(Patient.email) == email.lower(),
            Patient.user_id.is_(None)  # Not already linked
        ).first()
        
        if patient:
            return patient
    
    # Then try to find by phone
    if phone:
        # Clean phone number for comparison
        clean_phone = ''.join(filter(str.isdigit, phone))
        if len(clean_phone) >= 10:
            # Get last 10 digits
            phone_suffix = clean_phone[-10:]
            
            # Find patients with matching phone
            patients = Patient.query.filter(
                Patient.user_id.is_(None),
                Patient.phone.isnot(None),
                Patient.phone != 'Not Provided'
            ).all()
            
            for patient in patients:
                patient_phone_clean = ''.join(filter(str.isdigit, patient.phone or ''))
                if patient_phone_clean[-10:] == phone_suffix:
                    return patient
    
    return None


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.index'))


@auth_bp.route('/check-existing-patient', methods=['POST'])
def check_existing_patient():
    """API endpoint to check if patient record exists"""
    from flask import jsonify
    
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    
    existing = find_existing_patient(email, phone)
    
    if existing:
        return jsonify({
            'exists': True,
            'patient_id': existing.patient_id,
            'name': existing.full_name,
            'message': f'Found existing record: {existing.patient_id} - {existing.full_name}'
        })
    else:
        return jsonify({
            'exists': False,
            'message': 'No existing patient record found. A new record will be created.'
        })