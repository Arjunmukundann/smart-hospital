"""
Insurance Routes - Insurance management endpoints
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import Patient
from app.models.insurance import InsuranceProvider, PatientInsurance, InsuranceClaim
from app.services.insurance_service import InsuranceService

insurance_bp = Blueprint('insurance', __name__, url_prefix='/insurance')


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ============ ADMIN ROUTES ============

@insurance_bp.route('/admin/providers')
@login_required
@admin_required
def admin_providers():
    """Manage insurance providers"""
    providers = InsuranceProvider.query.order_by(InsuranceProvider.name).all()
    return render_template('admin/insurance_providers.html', providers=providers)


@insurance_bp.route('/admin/providers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_provider():
    """Add new insurance provider"""
    if request.method == 'POST':
        provider = InsuranceProvider(
            name=request.form.get('name', '').strip(),
            code=request.form.get('code', '').strip().upper(),
            contact_phone=request.form.get('contact_phone', ''),
            contact_email=request.form.get('contact_email', ''),
            website=request.form.get('website', ''),
            is_active=request.form.get('is_active') == 'on'
        )
        
        db.session.add(provider)
        db.session.commit()
        
        flash('Insurance provider added successfully!', 'success')
        return redirect(url_for('insurance.admin_providers'))
    
    return render_template('admin/add_insurance_provider.html')


@insurance_bp.route('/admin/claims')
@login_required
@admin_required
def admin_claims():
    """View all insurance claims"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = InsuranceClaim.query
    
    if status:
        query = query.filter_by(status=status)
    
    claims = query.order_by(InsuranceClaim.submitted_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Statistics
    pending_count = InsuranceClaim.query.filter_by(status='submitted').count()
    total_claimed = db.session.query(
        db.func.sum(InsuranceClaim.claimed_amount)
    ).scalar() or 0
    total_approved = db.session.query(
        db.func.sum(InsuranceClaim.approved_amount)
    ).filter(InsuranceClaim.status == 'approved').scalar() or 0
    
    return render_template('admin/insurance_claims.html',
                         claims=claims,
                         status=status,
                         pending_count=pending_count,
                         total_claimed=total_claimed,
                         total_approved=total_approved)


@insurance_bp.route('/admin/claims/<int:claim_id>/process', methods=['POST'])
@login_required
@admin_required
def process_claim(claim_id):
    """Process an insurance claim"""
    action = request.form.get('action')
    
    if action == 'approve':
        approved_amount = float(request.form.get('approved_amount', 0))
        success, message = InsuranceService.process_claim(
            claim_id,
            approved_amount=approved_amount,
            status='approved',
            processed_by=current_user.id
        )
    else:
        rejection_reason = request.form.get('rejection_reason', '')
        success, message = InsuranceService.process_claim(
            claim_id,
            status='rejected',
            rejection_reason=rejection_reason,
            processed_by=current_user.id
        )
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('insurance.admin_claims'))


# ============ VERIFICATION ROUTES ============

@insurance_bp.route('/verify/<int:policy_id>', methods=['POST'])
@login_required
def verify_policy(policy_id):
    """Verify insurance policy"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    success, message = InsuranceService.verify_insurance(policy_id, current_user.id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400


@insurance_bp.route('/check-coverage', methods=['POST'])
@login_required
def check_coverage():
    """Check insurance coverage for a service"""
    policy_id = request.json.get('policy_id')
    service_type = request.json.get('service_type')
    amount = float(request.json.get('amount', 0))
    
    coverage = InsuranceService.check_coverage(policy_id, service_type, amount)
    return jsonify(coverage)


# ============ API ROUTES ============

@insurance_bp.route('/api/providers')
@login_required
def api_providers():
    """Get list of insurance providers"""
    providers = InsuranceProvider.query.filter_by(is_active=True).all()
    return jsonify([p.to_dict() for p in providers])


@insurance_bp.route('/api/patient/<int:patient_id>/insurance')
@login_required
def api_patient_insurance(patient_id):
    """Get patient's insurance summary"""
    summary = InsuranceService.get_patient_insurance_summary(patient_id)
    return jsonify(summary)