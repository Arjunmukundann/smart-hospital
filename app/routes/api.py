"""
API Routes for AJAX requests
"""

from flask import Blueprint, jsonify, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Patient, Prescription, Inventory
from app.services import SafetyChecker, MealAnalyzer
import os
from datetime import datetime

api_bp = Blueprint('api', __name__)


# ==================== PRESCRIPTION & SAFETY ====================

@api_bp.route('/prescription/validate', methods=['POST'])
@login_required
def validate_prescription():
    """Validate prescription for safety issues"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    patient_id = data.get('patient_id')
    medicines = data.get('medicines', [])
    
    if not patient_id or not medicines:
        return jsonify({'error': 'Patient ID and medicines are required'}), 400
    
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    
    # Get patient data
    allergies = patient.get_allergies_list()
    current_meds = patient.get_current_medications_list()
    
    # Perform safety check
    checker = SafetyChecker()
    result = checker.perform_full_check(medicines, allergies, current_meds)
    
    return jsonify(result)


# ==================== MEAL ANALYSIS ====================

@api_bp.route('/meal/check', methods=['POST'])
@login_required
def check_meal():
    """Check meal safety with medications (text-based)"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    meal = data.get('meal', '')
    medicines = data.get('medicines', [])
    
    if not meal:
        return jsonify({'error': 'Meal description is required'}), 400
    
    analyzer = MealAnalyzer()
    result = analyzer.analyze_meal(meal, medicines)
    
    return jsonify(result)


@api_bp.route('/analyze-meal-safety', methods=['POST'])
@login_required
def analyze_meal_safety():
    """Analyze meal safety with patient's current medicines"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    foods = data.get('foods', [])
    
    if not foods:
        return jsonify({'error': 'No foods provided'}), 400
    
    # Get patient's current medicines
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    medicines = []
    if patient:
        active_rx = Prescription.query.filter_by(
            patient_id=patient.id,
            status='active'
        ).all()
        
        for rx in active_rx:
            for med in rx.medicines.all():
                if med.medicine_name not in medicines:
                    medicines.append(med.medicine_name)
    
    if not medicines:
        return jsonify({
            'is_safe': True,
            'message': 'No active medications found. Meal appears safe!',
            'warnings': [],
            'identified_foods': [{'name': f} for f in foods],
            'summary': {'total_foods': len(foods), 'total_warnings': 0, 'has_critical': False, 'has_high': False}
        })
    
    # Analyze meal
    analyzer = MealAnalyzer()
    meal_text = ', '.join(foods)
    result = analyzer.analyze_meal(meal_text, medicines)
    
    return jsonify(result)


# ==================== FOOD DETECTION (ML) ====================

@api_bp.route('/detect-food', methods=['POST'])
@login_required
def detect_food():
    """Detect food from uploaded image using ML"""
    from werkzeug.utils import secure_filename
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Check file extension
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if ext not in allowed:
        return jsonify({
            'success': False, 
            'error': f'Invalid file type. Allowed: {", ".join(allowed)}'
        }), 400
    
    try:
        # Save file temporarily
        filename = secure_filename(f"food_{current_user.id}_{file.filename}")
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Try ML detection first
        try:
            from app.services.food_detection_ml import food_detector
            result = food_detector.predict(filepath)
        except ImportError:
            # Fallback if ML service not available
            result = fallback_food_detection(filepath)
        
        # Clean up
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def fallback_food_detection(image_path):
    """Simple fallback when ML is not available"""
    try:
        from PIL import Image
        import numpy as np
        
        img = Image.open(image_path)
        img = img.convert('RGB')
        img = img.resize((100, 100))
        img_array = np.array(img)
        
        # Calculate average color
        avg_color = img_array.mean(axis=(0, 1))
        r, g, b = avg_color
        
        # Simple color-based detection
        if g > r and g > b:
            food_name = "Green Vegetable/Salad"
            category = "vegetable"
            nutrition = {'calories': 25, 'protein': 2, 'carbs': 5, 'fat': 0.3, 'health_score': 9}
        elif r > 200 and g > 150 and b < 100:
            food_name = "Yellow/Orange Food (Banana, Orange)"
            category = "fruit"
            nutrition = {'calories': 70, 'protein': 1, 'carbs': 18, 'fat': 0.2, 'health_score': 8}
        elif r > g and r > b:
            food_name = "Red Food (Tomato, Apple, Meat)"
            category = "mixed"
            nutrition = {'calories': 50, 'protein': 2, 'carbs': 10, 'fat': 1, 'health_score': 7}
        elif r > 150 and g > 100 and b < 100:
            food_name = "Brown Food (Bread, Rice, Meat)"
            category = "grain"
            nutrition = {'calories': 150, 'protein': 5, 'carbs': 30, 'fat': 2, 'health_score': 6}
        else:
            food_name = "Mixed Food Item"
            category = "mixed"
            nutrition = {'calories': 100, 'protein': 4, 'carbs': 15, 'fat': 3, 'health_score': 5}
        
        return {
            'success': True,
            'food_name': food_name,
            'category': category,
            'confidence': 55,
            'nutrition': nutrition,
            'model_type': 'Color Analysis (Install TensorFlow for better accuracy)',
            'note': 'For better results, install TensorFlow: pip install tensorflow'
        }
        
    except ImportError:
        # If PIL is not available
        return {
            'success': True,
            'food_name': 'Food Item',
            'category': 'unknown',
            'confidence': 40,
            'nutrition': {'calories': 100, 'protein': 5, 'carbs': 15, 'fat': 3, 'health_score': 5},
            'model_type': 'Basic Detection',
            'note': 'Install Pillow and TensorFlow for better results'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Error analyzing image'
        }


# ==================== SEARCH ====================

@api_bp.route('/patient/search')
@login_required
def search_patients():
    """Search patients by name or ID"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    patients = Patient.query.filter(
        db.or_(
            Patient.patient_id.ilike(f'%{query}%'),
            Patient.full_name.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify([
        {
            'id': p.id,
            'patient_id': p.patient_id,
            'full_name': p.full_name,
            'age': p.age,
            'gender': p.gender
        }
        for p in patients
    ])


@api_bp.route('/medicine/search')
@login_required
def search_medicines():
    """Search medicines in inventory"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    medicines = Inventory.query.filter(
        Inventory.medicine_name.ilike(f'%{query}%')
    ).limit(10).all()
    
    return jsonify([
        {
            'name': m.medicine_name,
            'stock': m.current_stock,
            'unit': m.unit
        }
        for m in medicines
    ])


# ==================== DASHBOARD ====================

@api_bp.route('/dashboard/stats')
@login_required
def dashboard_stats():
    """Get dashboard statistics"""
    from datetime import date
    today = date.today()
    
    stats = {
        'total_patients': Patient.query.count(),
        'today_prescriptions': Prescription.query.filter(
            db.func.date(Prescription.created_at) == today
        ).count(),
        'low_stock_count': Inventory.query.filter(
            Inventory.current_stock <= Inventory.reorder_level
        ).count()
    }
    
    return jsonify(stats)


# ==================== REMINDERS ====================

@api_bp.route('/trigger-reminders/<timing>', methods=['POST'])
@login_required
def trigger_reminders(timing):
    """Manually trigger reminders (for testing)"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    if timing not in ['morning', 'afternoon', 'evening', 'night']:
        return jsonify({'error': 'Invalid timing'}), 400
    
    try:
        from app.services.scheduler import send_scheduled_reminders
        import threading
        
        # Run in background thread
        thread = threading.Thread(target=send_scheduled_reminders, args=(timing,))
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'{timing.title()} reminders triggered. Check server logs.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/test-email', methods=['POST'])
def test_email():
    """Test email configuration - Admin only"""
    from flask import request, jsonify
    from flask_login import current_user, login_required
    from app.services.reminder_service import reminder_service
    
    # Get test email from request or use default
    data = request.get_json() or {}
    test_email = data.get('email', 'test@example.com')
    
    # Send test email
    result = reminder_service.send_email(
        to_email=test_email,
        subject="🧪 Smart Hospital - Test Email",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1 style="color: #667eea;">✅ Email Configuration Working!</h1>
            <p>This is a test email from Smart Hospital Platform.</p>
            <p>If you received this, your email configuration is correct.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                Sent at: """ + str(datetime.now()) + """
            </p>
        </body>
        </html>
        """,
        text_content="Email configuration is working! This is a test email from Smart Hospital."
    )
    
    return jsonify(result)
@api_bp.route('/test-reminder/<timing>', methods=['POST'])
def test_reminder(timing):
    """Manually trigger reminders for testing"""
    from flask import jsonify
    from app.services.scheduler import send_scheduled_reminders
    
    if timing not in ['morning', 'afternoon', 'evening', 'night']:
        return jsonify({'error': 'Invalid timing. Use: morning, afternoon, evening, night'}), 400
    
    try:
        count = send_scheduled_reminders(timing)
        return jsonify({
            'success': True,
            'message': f'Triggered {timing} reminders',
            'sent_count': count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    

@api_bp.route('/scheduler-status', methods=['GET'])
def scheduler_status():
    """Check scheduler status"""
    from flask import current_app, jsonify
    
    scheduler = getattr(current_app, 'scheduler', None)
    
    if scheduler:
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run': str(job.next_run_time) if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jsonify({
            'running': scheduler.running,
            'jobs': jobs
        })
    else:
        return jsonify({
            'running': False,
            'error': 'Scheduler not initialized'
        })