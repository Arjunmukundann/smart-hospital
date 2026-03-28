"""
Meal Analyzer Routes - Check food-medicine interactions
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Patient, Prescription, PrescriptionMedicine
from app.services.meal_analyzer import MealAnalyzer

meal_bp = Blueprint('meal', __name__)


@meal_bp.route('/analyzer', methods=['GET', 'POST'])
@login_required
def analyzer():
    """Meal analyzer page"""
    # Get patient's current medicines
    patient = None
    current_medicines = []
    
    if current_user.is_patient():
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if patient:
            # Get active prescriptions
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
        
        # Combine medicines
        all_medicines = list(medicines_input)
        if custom_medicines:
            all_medicines.extend([m.strip() for m in custom_medicines.split(',') if m.strip()])
        
        if not meal_text:
            flash('Please describe your meal.', 'error')
        elif not all_medicines:
            flash('Please select or enter at least one medicine.', 'error')
        else:
            # Analyze meal
            meal_analyzer = MealAnalyzer()
            result = meal_analyzer.analyze_meal(meal_text, all_medicines)
    
    return render_template('meal/analyzer.html',
                          patient=patient,
                          current_medicines=current_medicines,
                          result=result,
                          meal_text=meal_text)


@meal_bp.route('/api/analyze', methods=['POST'])
@login_required
def api_analyze():
    """API endpoint for meal analysis"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    meal_text = data.get('meal', '').strip()
    medicines = data.get('medicines', [])
    
    if not meal_text:
        return jsonify({'error': 'Meal description is required'}), 400
    
    if not medicines:
        return jsonify({'error': 'At least one medicine is required'}), 400
    
    analyzer = MealAnalyzer()
    result = analyzer.analyze_meal(meal_text, medicines)
    
    return jsonify(result)


@meal_bp.route('/api/food-info/<food_name>')
@login_required
def api_food_info(food_name):
    """Get information about a food item"""
    analyzer = MealAnalyzer()
    categories = analyzer.categorize_food(food_name)
    
    return jsonify({
        'food': food_name,
        'categories': categories
    })