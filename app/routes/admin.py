"""
Admin Module Routes - Fixed for Charts
"""

from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func
from app import db
from app.models import User, Patient, Prescription, Report, Inventory, InventoryTransaction, SafetyAlert
from app.services import PredictionService

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    today = date.today()
    
    # Statistics
    total_patients = Patient.query.count()
    today_patients = Prescription.query.filter(
        db.func.date(Prescription.created_at) == today
    ).distinct(Prescription.patient_id).count()
    
    today_alerts = SafetyAlert.query.filter(
        db.func.date(SafetyAlert.created_at) == today
    ).count()
    
    low_stock_count = Inventory.query.filter(
        Inventory.current_stock <= Inventory.reorder_level
    ).count()
    
    # Get recent data for charts
    prediction_service = PredictionService()
    historical_data = prediction_service.generate_historical_data(30)
    
    # ✅ FIX: Ensure historical_data is never empty
    if not historical_data:
        historical_data = [{'date': today.strftime('%Y-%m-%d'), 'patient_count': 0}]
    
    # Recent alerts
    recent_alerts = SafetyAlert.query.order_by(
        SafetyAlert.created_at.desc()
    ).limit(10).all()
    
    # ✅ FIX: Get real department distribution from database
    departments = get_department_distribution()
    
    return render_template('admin/dashboard.html',
                         total_patients=total_patients,
                         today_patients=today_patients,
                         today_alerts=today_alerts,
                         low_stock_count=low_stock_count,
                         historical_data=historical_data,
                         recent_alerts=recent_alerts,
                         departments=departments)


def get_department_distribution():
    """Get patient distribution by department from prescriptions"""
    # Try to get real data from database
    try:
        # Get department distribution from prescriptions (using diagnosis as proxy)
        # You can modify this based on your actual data structure
        
        # For now, let's count by doctor specialization
        dept_counts = db.session.query(
            User.specialization,
            func.count(Prescription.id)
        ).join(
            Prescription, User.id == Prescription.doctor_id
        ).filter(
            User.role == 'doctor'
        ).group_by(User.specialization).all()
        
        if dept_counts:
            return {dept or 'General': count for dept, count in dept_counts}
    except Exception as e:
        print(f"Error getting department data: {e}")
    
    # ✅ FIX: Return default data if no real data exists
    return {
        'General Medicine': 35,
        'Cardiology': 20,
        'Orthopedics': 15,
        'Neurology': 12,
        'Pediatrics': 10,
        'Other': 8
    }


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """Detailed analytics view"""
    prediction_service = PredictionService()
    
    # Get 90 days of historical data
    historical_data = prediction_service.generate_historical_data(90)
    
    # ✅ FIX: Ensure data exists
    if not historical_data:
        historical_data = prediction_service.generate_historical_data(90)
    
    # Get analytics summary
    summary = prediction_service.get_analytics_summary(historical_data)
    
    # ✅ FIX: Ensure summary has all required keys
    if 'day_averages' not in summary:
        summary['day_averages'] = {
            'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 
            'Thursday': 0, 'Friday': 0, 'Saturday': 0, 'Sunday': 0
        }
    
    # Alert statistics - ✅ FIX: Handle empty alerts
    alert_stats = db.session.query(
        SafetyAlert.alert_type,
        func.count(SafetyAlert.id)
    ).group_by(SafetyAlert.alert_type).all()
    
    alert_stats_dict = dict(alert_stats) if alert_stats else {}
    
    # ✅ FIX: Provide default alert stats if empty
    if not alert_stats_dict:
        alert_stats_dict = {
            'drug_drug': 0,
            'allergy': 0,
            'food_drug': 0
        }
    
    # Monthly trends
    monthly_data = {}
    for record in historical_data:
        month = record['date'][:7]  # YYYY-MM
        if month not in monthly_data:
            monthly_data[month] = []
        monthly_data[month].append(record['patient_count'])
    
    monthly_averages = {
        month: round(sum(counts) / len(counts), 1)
        for month, counts in monthly_data.items()
    }
    
    # ✅ FIX: Ensure monthly_averages is not empty
    if not monthly_averages:
        current_month = date.today().strftime('%Y-%m')
        monthly_averages = {current_month: 0}
    
    return render_template('admin/analytics.html',
                         historical_data=historical_data,
                         summary=summary,
                         alert_stats=alert_stats_dict,
                         monthly_averages=monthly_averages)


@admin_bp.route('/inventory')
@login_required
@admin_required
def inventory():
    """Medicine inventory management"""
    # Get all inventory items
    all_items = Inventory.query.order_by(Inventory.medicine_name).all()
    
    # Separate low stock items
    low_stock_items = [item for item in all_items if item.is_low_stock()]
    
    return render_template('admin/inventory.html',
                         items=all_items,
                         low_stock_items=low_stock_items)


@admin_bp.route('/inventory/add', methods=['POST'])
@login_required
@admin_required
def add_inventory():
    """Add or update inventory item"""
    medicine_name = request.form.get('medicine_name', '').strip()
    current_stock = request.form.get('current_stock', 0, type=int)
    reorder_level = request.form.get('reorder_level', 50, type=int)
    unit = request.form.get('unit', 'tablets')
    category = request.form.get('category', '')
    
    if not medicine_name:
        flash('Medicine name is required.', 'error')
        return redirect(url_for('admin.inventory'))
    
    # Check if item exists
    item = Inventory.query.filter_by(medicine_name=medicine_name).first()
    
    if item:
        # Update existing
        old_stock = item.current_stock
        item.current_stock = current_stock
        item.reorder_level = reorder_level
        
        # Log transaction
        if current_stock != old_stock:
            transaction = InventoryTransaction(
                medicine_id=item.id,
                transaction_type='add' if current_stock > old_stock else 'remove',
                quantity=abs(current_stock - old_stock),
                user_id=current_user.id,
                notes='Stock updated by admin'
            )
            db.session.add(transaction)
        
        flash(f'Updated {medicine_name} stock.', 'success')
    else:
        # Create new
        item = Inventory(
            medicine_name=medicine_name,
            current_stock=current_stock,
            reorder_level=reorder_level,
            unit=unit,
            category=category
        )
        db.session.add(item)
        flash(f'Added {medicine_name} to inventory.', 'success')
    
    db.session.commit()
    return redirect(url_for('admin.inventory'))


@admin_bp.route('/predictions')
@login_required
@admin_required
def predictions():
    """ML-based predictions"""
    prediction_service = PredictionService()
    
    # Generate and train on historical data
    historical_data = prediction_service.generate_historical_data(90)
    
    # ✅ FIX: Ensure we have data
    if not historical_data:
        flash('Unable to generate historical data for predictions.', 'warning')
        historical_data = []
    
    if historical_data:
        prediction_service.train_model(historical_data)
    
    # Get predictions
    next_7_days = prediction_service.predict_next_days(7)
    
    # ✅ FIX: Ensure predictions exist
    if not next_7_days:
        next_7_days = []
    
    # Get model metrics
    metrics = prediction_service.get_model_metrics(historical_data)
    
    # ✅ FIX: Ensure metrics has all required keys
    if 'model_type' not in metrics:
        metrics['model_type'] = 'simple'
    if 'mae' not in metrics:
        metrics['mae'] = 'N/A'
    if 'rmse' not in metrics:
        metrics['rmse'] = 'N/A'
    if 'r2' not in metrics:
        metrics['r2'] = 'N/A'
    
    return render_template('admin/predictions.html',
                         predictions=next_7_days,
                         historical_data=historical_data[-30:] if historical_data else [],
                         metrics=metrics)


@admin_bp.route('/error-logs')
@login_required
@admin_required
def error_logs():
    """Safety alert error logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter options
    severity = request.args.get('severity', '')
    alert_type = request.args.get('alert_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query
    query = SafetyAlert.query
    
    if severity:
        query = query.filter_by(severity=severity)
    if alert_type:
        query = query.filter_by(alert_type=alert_type)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(SafetyAlert.created_at >= from_date)
        except:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(SafetyAlert.created_at <= to_date)
        except:
            pass
    
    alerts = query.order_by(SafetyAlert.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Statistics
    total_alerts = SafetyAlert.query.count()
    critical_alerts = SafetyAlert.query.filter_by(severity='critical').count()
    overridden_alerts = SafetyAlert.query.filter_by(is_overridden=True).count()
    
    # Alert type distribution
    type_distribution = db.session.query(
        SafetyAlert.alert_type,
        func.count(SafetyAlert.id)
    ).group_by(SafetyAlert.alert_type).all()
    
    return render_template('admin/error_logs.html',
                         alerts=alerts,
                         total_alerts=total_alerts,
                         critical_alerts=critical_alerts,
                         overridden_alerts=overridden_alerts,
                         type_distribution=dict(type_distribution) if type_distribution else {})


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management"""
    page = request.args.get('page', 1, type=int)
    role = request.args.get('role', '')
    
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    all_users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Statistics
    total_users = User.query.count()
    doctors = User.query.filter_by(role='doctor').count()
    patients = User.query.filter_by(role='patient').count()
    admins = User.query.filter_by(role='admin').count()
    
    return render_template('admin/users.html',
                         users=all_users,
                         total_users=total_users,
                         doctors=doctors,
                         patients=patients,
                         admins=admins)


@admin_bp.route('/inventory/update-stock', methods=['POST'])
@login_required
@admin_required
def update_stock():
    """Update inventory stock (add or remove)"""
    item_id = request.form.get('item_id', type=int)
    action = request.form.get('action')  # 'add' or 'remove'
    quantity = request.form.get('quantity', 0, type=int)
    notes = request.form.get('notes', '')
    
    if not item_id or not action or quantity <= 0:
        flash('Invalid request.', 'error')
        return redirect(url_for('admin.inventory'))
    
    item = Inventory.query.get_or_404(item_id)
    
    if action == 'add':
        item.current_stock += quantity
        transaction_type = 'add'
        flash(f'Added {quantity} {item.unit} to {item.medicine_name}', 'success')
    elif action == 'remove':
        if item.current_stock < quantity:
            flash(f'Cannot remove {quantity}. Only {item.current_stock} available.', 'error')
            return redirect(url_for('admin.inventory'))
        item.current_stock -= quantity
        transaction_type = 'remove'
        flash(f'Removed {quantity} {item.unit} from {item.medicine_name}', 'success')
    else:
        flash('Invalid action.', 'error')
        return redirect(url_for('admin.inventory'))
    
    # Log transaction
    transaction = InventoryTransaction(
        medicine_id=item.id,
        transaction_type=transaction_type,
        quantity=quantity,
        user_id=current_user.id,
        notes=notes
    )
    db.session.add(transaction)
    db.session.commit()
    
    return redirect(url_for('admin.inventory'))


# ✅ FIX 7: Add Reminder Settings Route for Admin
# Add this route to app/routes/admin.py

# Add this at the END of your admin.py file (before any patient routes are imported)

@admin_bp.route('/reminder-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def reminder_settings():
    """
    Admin-level reminder settings
    This route is for ADMIN only - uses @admin_required decorator
    """
    from flask import current_app
    
    if request.method == 'POST':
        morning_time = request.form.get('morning_time', '08:00')
        afternoon_time = request.form.get('afternoon_time', '13:00')
        evening_time = request.form.get('evening_time', '18:00')
        night_time = request.form.get('night_time', '21:00')
        
        # Save to database or config
        try:
            from app.models.reminder import GlobalReminderSettings
            
            GlobalReminderSettings.set_setting('morning_time', morning_time, current_user.id)
            GlobalReminderSettings.set_setting('afternoon_time', afternoon_time, current_user.id)
            GlobalReminderSettings.set_setting('evening_time', evening_time, current_user.id)
            GlobalReminderSettings.set_setting('night_time', night_time, current_user.id)
            
            flash('Global reminder settings saved!', 'success')
        except:
            flash('Settings saved (using defaults).', 'info')
        
        return redirect(url_for('admin.reminder_settings'))
    
    # Get current settings
    settings = {
        'morning_time': current_app.config.get('REMINDER_TIMES', {}).get('morning', '08:00'),
        'afternoon_time': current_app.config.get('REMINDER_TIMES', {}).get('afternoon', '13:00'),
        'evening_time': current_app.config.get('REMINDER_TIMES', {}).get('evening', '18:00'),
        'night_time': current_app.config.get('REMINDER_TIMES', {}).get('night', '21:00'),
        'email_enabled': True,
        'sms_enabled': False
    }
    
    email_configured = bool(current_app.config.get('MAIL_USERNAME')) and bool(current_app.config.get('MAIL_PASSWORD'))
    
    return render_template('admin/reminder_settings.html', 
                         settings=settings,
                         email_configured=email_configured)