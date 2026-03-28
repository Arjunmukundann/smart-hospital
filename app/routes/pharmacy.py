"""
Pharmacy Module Routes - Complete pharmacy management
"""

from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import (
    User, Patient, Prescription, PrescriptionMedicine,
    Inventory, InventoryTransaction
)
from app.models.pharmacy import PharmacyBill, PharmacyBillItem
from app.models.insurance import PatientInsurance, InsuranceClaim
from app.services.billing_service import BillingService
from app.services.pdf_service import PDFService

pharmacy_bp = Blueprint('pharmacy', __name__)


def pharmacist_required(f):
    """Decorator to require pharmacist role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access the pharmacy module.', 'info')
            return redirect(url_for('auth.login'))
        
        # Allow both pharmacist and admin
        if current_user.role not in ['pharmacist', 'admin']:
            flash(f'Access denied. You are logged in as "{current_user.role}". Pharmacist access required.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

@pharmacy_bp.route('/')
def pharmacy_index():
    """Pharmacy module index"""
    if current_user.is_authenticated:
        if current_user.role in ['pharmacist', 'admin']:
            return redirect(url_for('pharmacy.dashboard'))
    
    flash('Please log in as pharmacist to access this module.', 'info')
    return redirect(url_for('auth.login'))

@pharmacy_bp.route('/dashboard')
@login_required
@pharmacist_required
def dashboard():
    """Pharmacy dashboard"""
    from app.models.inventory import Inventory
    from app.models.prescription import Prescription
    from app.models.pharmacy import PharmacyBill
    
    today = date.today()
    
    # Statistics
    try:
        total_medicines = Inventory.query.filter_by(is_active=True).count()
    except:
        total_medicines = 0
    
    try:
        low_stock = Inventory.query.filter(
            Inventory.current_stock <= Inventory.reorder_level,
            Inventory.is_active == True
        ).count()
    except:
        low_stock = 0
    
    try:
        out_of_stock = Inventory.query.filter(
            Inventory.current_stock <= 0,
            Inventory.is_active == True
        ).count()
    except:
        out_of_stock = 0
    
    try:
        expired_medicines = Inventory.query.filter(
            Inventory.expiry_date < today,
            Inventory.is_active == True
        ).count()
    except:
        expired_medicines = 0
    
    try:
        pending_prescriptions = Prescription.query.filter(
            Prescription.status == 'active',
            Prescription.is_signed == True
        ).count()
    except:
        pending_prescriptions = 0
    
    try:
        today_bills = PharmacyBill.query.filter(
            db.func.date(PharmacyBill.created_at) == today
        ).count()
    except:
        today_bills = 0
    
    try:
        today_revenue = db.session.query(
            db.func.sum(PharmacyBill.total_amount)
        ).filter(
            db.func.date(PharmacyBill.created_at) == today,
            PharmacyBill.payment_status == 'paid'
        ).scalar() or 0
    except:
        today_revenue = 0
    
    # Recent data
    try:
        recent_prescriptions = Prescription.query.filter(
            Prescription.status == 'active',
            Prescription.is_signed == True
        ).order_by(Prescription.created_at.desc()).limit(10).all()
    except:
        recent_prescriptions = []
    
    try:
        recent_bills = PharmacyBill.query.order_by(
            PharmacyBill.created_at.desc()
        ).limit(10).all()
    except:
        recent_bills = []
    
    try:
        low_stock_items = Inventory.query.filter(
            Inventory.current_stock <= Inventory.reorder_level,
            Inventory.is_active == True
        ).order_by(Inventory.current_stock.asc()).limit(10).all()
    except:
        low_stock_items = []
    
    return render_template('pharmacy/dashboard.html',
                         total_medicines=total_medicines,
                         low_stock=low_stock,
                         out_of_stock=out_of_stock,
                         expired_medicines=expired_medicines,
                         pending_prescriptions=pending_prescriptions,
                         today_bills=today_bills,
                         today_revenue=today_revenue,
                         recent_prescriptions=recent_prescriptions,
                         recent_bills=recent_bills,
                         low_stock_items=low_stock_items)



@pharmacy_bp.route('/inventory')
@login_required
@pharmacist_required
def inventory():
    """Medicine inventory management"""
    from datetime import date
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    stock_filter = request.args.get('stock', '')
    
    query = Inventory.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Inventory.medicine_name.ilike(f'%{search}%'),
                Inventory.generic_name.ilike(f'%{search}%'),
                Inventory.batch_number.ilike(f'%{search}%')
            )
        )
    
    if category:
        query = query.filter_by(category=category)
    
    if stock_filter == 'low':
        query = query.filter(
            Inventory.current_stock <= Inventory.reorder_level,
            Inventory.current_stock > 0
        )
    elif stock_filter == 'out':
        query = query.filter(Inventory.current_stock <= 0)
    elif stock_filter == 'expired':
        query = query.filter(Inventory.expiry_date < date.today())
    
    medicines = query.order_by(Inventory.medicine_name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique categories
    categories = db.session.query(Inventory.category).distinct().filter(
        Inventory.category.isnot(None),
        Inventory.category != ''
    ).all()
    categories = [c[0] for c in categories]
    
    return render_template('pharmacy/inventory.html',
                         medicines=medicines,
                         categories=categories,
                         search=search,
                         current_category=category,
                         stock_filter=stock_filter,
                         today=date.today())  # ADD THIS!




@pharmacy_bp.route('/medicine/add', methods=['GET', 'POST'])
@login_required
@pharmacist_required
def add_medicine():
    """Add new medicine to inventory"""
    if request.method == 'POST':
        medicine_name = request.form.get('medicine_name', '').strip()
        
        if not medicine_name:
            flash('Medicine name is required.', 'error')
            return render_template('pharmacy/add_medicine.html')
        
        # Check if already exists
        existing = Inventory.query.filter(
            Inventory.medicine_name.ilike(medicine_name)
        ).first()
        
        if existing:
            flash(f'Medicine "{medicine_name}" already exists. Updating stock instead.', 'info')
            return redirect(url_for('pharmacy.edit_medicine', medicine_id=existing.id))
        
        try:
            expiry_date = None
            if request.form.get('expiry_date'):
                expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            
            medicine = Inventory(
                medicine_name=medicine_name,
                generic_name=request.form.get('generic_name', '').strip(),
                category=request.form.get('category', '').strip(),
                manufacturer=request.form.get('manufacturer', '').strip(),
                batch_number=request.form.get('batch_number', '').strip(),
                current_stock=int(request.form.get('current_stock', 0)),
                reorder_level=int(request.form.get('reorder_level', 50)),
                unit=request.form.get('unit', 'tablets'),
                unit_price=float(request.form.get('unit_price', 0)),
                expiry_date=expiry_date,
                is_active=True
            )
            
            db.session.add(medicine)
            db.session.flush()
            
            # Record initial stock transaction
            if medicine.current_stock > 0:
                transaction = InventoryTransaction(
                    medicine_id=medicine.id,
                    transaction_type='add',
                    quantity=medicine.current_stock,
                    reference_id='INITIAL',
                    user_id=current_user.id,
                    notes='Initial stock entry'
                )
                db.session.add(transaction)
            
            db.session.commit()
            flash(f'Medicine "{medicine_name}" added successfully!', 'success')
            return redirect(url_for('pharmacy.inventory'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding medicine: {str(e)}', 'error')
    
    return render_template('pharmacy/add_medicine.html')


@pharmacy_bp.route('/medicine/<int:medicine_id>/edit', methods=['GET', 'POST'])
@login_required
@pharmacist_required
def edit_medicine(medicine_id):
    """Edit medicine details"""
    medicine = Inventory.query.get_or_404(medicine_id)
    
    if request.method == 'POST':
        try:
            medicine.medicine_name = request.form.get('medicine_name', medicine.medicine_name).strip()
            medicine.generic_name = request.form.get('generic_name', '').strip()
            medicine.category = request.form.get('category', '').strip()
            medicine.manufacturer = request.form.get('manufacturer', '').strip()
            medicine.batch_number = request.form.get('batch_number', '').strip()
            medicine.reorder_level = int(request.form.get('reorder_level', 50))
            medicine.unit = request.form.get('unit', 'tablets')
            medicine.unit_price = float(request.form.get('unit_price', 0))
            
            if request.form.get('expiry_date'):
                medicine.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            
            db.session.commit()
            flash('Medicine updated successfully!', 'success')
            return redirect(url_for('pharmacy.inventory'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating medicine: {str(e)}', 'error')
    
    return render_template('pharmacy/edit_medicine.html', medicine=medicine)


@pharmacy_bp.route('/medicine/<int:medicine_id>/stock', methods=['POST'])
@login_required
@pharmacist_required
def update_stock(medicine_id):
    """Update medicine stock (add or remove)"""
    medicine = Inventory.query.get_or_404(medicine_id)
    
    action = request.form.get('action')  # 'add' or 'remove'
    quantity = int(request.form.get('quantity', 0))
    notes = request.form.get('notes', '')
    batch_number = request.form.get('batch_number', '')
    
    if quantity <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Quantity must be positive'}), 400
        flash('Quantity must be positive.', 'error')
        return redirect(url_for('pharmacy.inventory'))
    
    previous_stock = medicine.current_stock
    
    if action == 'add':
        medicine.current_stock += quantity
        if batch_number:
            medicine.batch_number = batch_number
        transaction_type = 'add'
        message = f'Added {quantity} {medicine.unit} to {medicine.medicine_name}'
    elif action == 'remove':
        if medicine.current_stock < quantity:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': f'Insufficient stock. Only {medicine.current_stock} available'}), 400
            flash(f'Insufficient stock. Only {medicine.current_stock} available.', 'error')
            return redirect(url_for('pharmacy.inventory'))
        medicine.current_stock -= quantity
        transaction_type = 'remove'
        message = f'Removed {quantity} {medicine.unit} from {medicine.medicine_name}'
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Invalid action'}), 400
        flash('Invalid action.', 'error')
        return redirect(url_for('pharmacy.inventory'))
    
    # Log transaction
    transaction = InventoryTransaction(
        medicine_id=medicine.id,
        transaction_type=transaction_type,
        quantity=quantity,
        reference_id='MANUAL',
        user_id=current_user.id,
        notes=notes or f'Manual {action} by pharmacist'
    )
    db.session.add(transaction)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': message,
            'new_stock': medicine.current_stock,
            'is_low_stock': medicine.is_low_stock()
        })
    
    flash(message, 'success')
    return redirect(url_for('pharmacy.inventory'))


@pharmacy_bp.route('/prescriptions')
@login_required
@pharmacist_required
def prescriptions():
    """View prescriptions to dispense"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'pending')  # pending, dispensed, all
    search = request.args.get('search', '')
    
    query = Prescription.query.filter(Prescription.is_signed == True)
    
    if status == 'pending':
        query = query.filter(Prescription.status == 'active')
    elif status == 'dispensed':
        query = query.filter(Prescription.status == 'dispensed')
    
    if search:
        query = query.join(Patient).filter(
            db.or_(
                Prescription.prescription_id.ilike(f'%{search}%'),
                Patient.full_name.ilike(f'%{search}%'),
                Patient.patient_id.ilike(f'%{search}%')
            )
        )
    
    prescriptions = query.order_by(Prescription.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('pharmacy/prescription.html',
                         prescriptions=prescriptions,
                         status=status,
                         search=search)


@pharmacy_bp.route('/prescription/<int:prescription_id>')
@login_required
@pharmacist_required
def view_prescription(prescription_id):
    """View prescription details"""
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Check stock availability for each medicine
    stock_status = []
    for med in prescription.medicines.all():
        inventory_item = Inventory.query.filter(
            Inventory.medicine_name.ilike(f'%{med.medicine_name}%')
        ).first()
        
        stock_status.append({
            'medicine': med,
            'inventory': inventory_item,
            'available': inventory_item.current_stock if inventory_item else 0,
            'sufficient': inventory_item and inventory_item.current_stock >= (med.quantity or 1) if inventory_item else False
        })
    
    return render_template('pharmacy/view_prescription.html',
                         prescription=prescription,
                         stock_status=stock_status)


@pharmacy_bp.route('/dispense/<int:prescription_id>', methods=['GET', 'POST'])
@login_required
@pharmacist_required
def dispense_prescription(prescription_id):
    """Dispense medicines for a prescription"""
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Validation
    if not prescription.is_signed:
        flash('Cannot dispense unsigned prescription.', 'error')
        return redirect(url_for('pharmacy.prescriptions'))
    
    if prescription.status == 'dispensed':
        flash('Prescription already dispensed.', 'warning')
        # Find existing bill
        existing_bill = PharmacyBill.query.filter_by(prescription_id=prescription.id).first()
        if existing_bill:
            return redirect(url_for('pharmacy.view_bill', bill_id=existing_bill.id))
        return redirect(url_for('pharmacy.prescriptions'))
    
    # Get patient's insurance
    patient_insurance = None
    if prescription.patient:
        patient_insurance = prescription.patient.insurance_policies.filter_by(
            is_active=True, is_primary=True
        ).first()
    
    if request.method == 'POST':
        try:
            # Create bill
            bill = PharmacyBill(
                bill_number=PharmacyBill.generate_bill_number(),
                patient_id=prescription.patient_id,
                prescription_id=prescription.id,
                pharmacist_id=current_user.id,
                subtotal=0,
                total_amount=0
            )
            db.session.add(bill)
            db.session.flush()
            
            subtotal = 0
            all_dispensed = True
            
            # Process each medicine
            for med in prescription.medicines.all():
                quantity_to_dispense = int(request.form.get(f'quantity_{med.id}', 0))
                
                if quantity_to_dispense <= 0:
                    continue
                
                # Find in inventory
                inventory_item = Inventory.query.filter(
                    Inventory.medicine_name.ilike(f'%{med.medicine_name}%')
                ).first()
                
                if not inventory_item:
                    flash(f'Medicine "{med.medicine_name}" not found in inventory.', 'warning')
                    all_dispensed = False
                    continue
                
                if inventory_item.current_stock < quantity_to_dispense:
                    flash(f'Insufficient stock for {med.medicine_name}. Only {inventory_item.current_stock} available.', 'warning')
                    quantity_to_dispense = inventory_item.current_stock
                    all_dispensed = False
                
                if quantity_to_dispense <= 0:
                    continue
                
                # Calculate price
                unit_price = inventory_item.unit_price or 0
                item_total = quantity_to_dispense * unit_price
                
                # Create bill item
                bill_item = PharmacyBillItem(
                    bill_id=bill.id,
                    medicine_id=inventory_item.id,
                    medicine_name=inventory_item.medicine_name,
                    batch_number=inventory_item.batch_number,
                    expiry_date=inventory_item.expiry_date,
                    quantity=quantity_to_dispense,
                    unit_price=unit_price,
                    total_price=item_total,
                    prescription_medicine_id=med.id
                )
                db.session.add(bill_item)
                
                # Deduct from inventory
                previous_stock = inventory_item.current_stock
                inventory_item.current_stock -= quantity_to_dispense
                
                # Record stock movement
                transaction = InventoryTransaction(
                    medicine_id=inventory_item.id,
                    transaction_type='prescribed',
                    quantity=quantity_to_dispense,
                    reference_id=prescription.prescription_id,
                    user_id=current_user.id,
                    notes=f'Dispensed for {prescription.patient.full_name} ({prescription.patient.patient_id})'
                )
                db.session.add(transaction)
                
                # Update prescription medicine
                med.is_dispensed = True
                med.dispensed_quantity = quantity_to_dispense
                
                subtotal += item_total
            
            # Calculate totals
            from flask import current_app
            tax_rate = current_app.config.get('TAX_RATE', 0.05)
            
            bill.subtotal = round(subtotal, 2)
            bill.tax = round(subtotal * tax_rate, 2)
            
            # Apply discount if any
            discount = float(request.form.get('discount', 0))
            bill.discount = min(discount, bill.subtotal)  # Discount can't exceed subtotal
            bill.discount_reason = request.form.get('discount_reason', '')
            
            bill.total_amount = round(bill.subtotal + bill.tax - bill.discount, 2)
            
            # Handle insurance if applicable
            use_insurance = request.form.get('use_insurance') == 'on'
            if use_insurance and patient_insurance and patient_insurance.is_valid:
                coverage_amount = (bill.total_amount * patient_insurance.coverage_percentage / 100)
                bill.insurance_covered = round(coverage_amount, 2)
                
                # Create insurance claim
                claim = InsuranceClaim(
                    claim_number=InsuranceClaim.generate_claim_number(),
                    policy_id=patient_insurance.id,
                    patient_id=prescription.patient_id,
                    bill_id=bill.id,
                    claim_type='medication',
                    total_amount=bill.total_amount,
                    claimed_amount=bill.insurance_covered,
                    status='submitted'
                )
                db.session.add(claim)
                db.session.flush()
                bill.insurance_claim_id = claim.id
            
            # Update prescription status
            if all_dispensed:
                prescription.status = 'dispensed'
            prescription.dispensed_at = datetime.utcnow()
            prescription.dispensed_by = current_user.id
            prescription.pharmacy_notes = request.form.get('notes', '')
            
            db.session.commit()
            
            flash('Prescription dispensed successfully!', 'success')
            return redirect(url_for('pharmacy.view_bill', bill_id=bill.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error dispensing prescription: {str(e)}', 'error')
    
    # GET - Show dispense form
    # Prepare stock status for each medicine
    medicines_with_stock = []
    for med in prescription.medicines.all():
        inventory_item = Inventory.query.filter(
            Inventory.medicine_name.ilike(f'%{med.medicine_name}%')
        ).first()
        
        medicines_with_stock.append({
            'medicine': med,
            'inventory': inventory_item,
            'available_stock': inventory_item.current_stock if inventory_item else 0,
            'unit_price': inventory_item.unit_price if inventory_item else 0,
            'suggested_quantity': med.quantity or 1
        })
    
    return render_template('pharmacy/dispense.html',
                         prescription=prescription,
                         medicines_with_stock=medicines_with_stock,
                         patient_insurance=patient_insurance)


@pharmacy_bp.route('/bill/<int:bill_id>')
@login_required
@pharmacist_required
def view_bill(bill_id):
    """View pharmacy bill"""
    bill = PharmacyBill.query.get_or_404(bill_id)
    return render_template('pharmacy/billing.html', bill=bill)


@pharmacy_bp.route('/bill/<int:bill_id>/print')
@login_required
@pharmacist_required
def print_bill(bill_id):
    """Print-friendly bill view"""
    bill = PharmacyBill.query.get_or_404(bill_id)
    return render_template('pharmacy/print_bill.html', bill=bill)


@pharmacy_bp.route('/bill/<int:bill_id>/pdf')
@login_required
@pharmacist_required
def download_bill_pdf(bill_id):
    """Generate and download bill as PDF"""
    bill = PharmacyBill.query.get_or_404(bill_id)
    
    try:
        pdf_service = PDFService()
        pdf_content = pdf_service.generate_pharmacy_bill_pdf(bill)
        
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=bill_{bill.bill_number}.pdf'
        return response
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('pharmacy.view_bill', bill_id=bill_id))


@pharmacy_bp.route('/bill/<int:bill_id>/payment', methods=['POST'])
@login_required
@pharmacist_required
def process_payment(bill_id):
    """Process bill payment"""
    bill = PharmacyBill.query.get_or_404(bill_id)
    
    payment_method = request.form.get('payment_method', 'cash')
    amount_received = float(request.form.get('amount_received', 0))
    
    amount_due = bill.total_amount - bill.insurance_covered
    
    if amount_received <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Invalid payment amount'}), 400
        flash('Invalid payment amount.', 'error')
        return redirect(url_for('pharmacy.view_bill', bill_id=bill_id))
    
    bill.payment_method = payment_method
    bill.amount_paid = amount_received
    
    if amount_received >= amount_due:
        bill.payment_status = 'paid'
        bill.paid_at = datetime.utcnow()
        bill.change_given = round(amount_received - amount_due, 2)
    else:
        bill.payment_status = 'partial'
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'payment_status': bill.payment_status,
            'change': bill.change_given,
            'message': 'Payment processed successfully'
        })
    
    flash('Payment processed successfully!', 'success')
    return redirect(url_for('pharmacy.view_bill', bill_id=bill_id))


@pharmacy_bp.route('/bills')
@login_required
@pharmacist_required
def bills():
    """View all pharmacy bills"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('search', '')
    
    query = PharmacyBill.query
    
    if status:
        query = query.filter_by(payment_status=status)
    
    if search:
        query = query.join(Patient).filter(
            db.or_(
                PharmacyBill.bill_number.ilike(f'%{search}%'),
                Patient.full_name.ilike(f'%{search}%'),
                Patient.patient_id.ilike(f'%{search}%')
            )
        )
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(PharmacyBill.created_at >= from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(PharmacyBill.created_at <= to_date)
        except:
            pass
    
    bills = query.order_by(PharmacyBill.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Summary statistics
    total_revenue = db.session.query(
        db.func.sum(PharmacyBill.total_amount)
    ).filter(PharmacyBill.payment_status == 'paid').scalar() or 0
    
    pending_amount = db.session.query(
        db.func.sum(PharmacyBill.total_amount - PharmacyBill.amount_paid)
    ).filter(PharmacyBill.payment_status.in_(['pending', 'partial'])).scalar() or 0
    
    return render_template('pharmacy/bills.html',
                         bills=bills,
                         status=status,
                         date_from=date_from,
                         date_to=date_to,
                         search=search,
                         total_revenue=total_revenue,
                         pending_amount=pending_amount)


@pharmacy_bp.route('/reports')
@login_required
@pharmacist_required
def reports():
    """Pharmacy reports and analytics"""
    # Date range
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
    
    try:
        from_date = datetime.strptime(date_from, '%Y-%m-%d')
        to_date = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except:
        from_date = datetime.now() - timedelta(days=30)
        to_date = datetime.now()
    
    # Sales summary
    sales_data = db.session.query(
        db.func.date(PharmacyBill.created_at).label('date'),
        db.func.count(PharmacyBill.id).label('bill_count'),
        db.func.sum(PharmacyBill.total_amount).label('total_sales')
    ).filter(
        PharmacyBill.created_at >= from_date,
        PharmacyBill.created_at <= to_date,
        PharmacyBill.payment_status == 'paid'
    ).group_by(db.func.date(PharmacyBill.created_at)).all()
    
    # Top selling medicines
    top_medicines = db.session.query(
        PharmacyBillItem.medicine_name,
        db.func.sum(PharmacyBillItem.quantity).label('total_quantity'),
        db.func.sum(PharmacyBillItem.total_price).label('total_revenue')
    ).join(PharmacyBill).filter(
        PharmacyBill.created_at >= from_date,
        PharmacyBill.created_at <= to_date
    ).group_by(PharmacyBillItem.medicine_name).order_by(
        db.func.sum(PharmacyBillItem.quantity).desc()
    ).limit(10).all()
    
    # Stock alerts
    low_stock_items = Inventory.query.filter(
        Inventory.current_stock <= Inventory.reorder_level,
        Inventory.is_active == True
    ).count()
    
    expired_items = Inventory.query.filter(
        Inventory.expiry_date < date.today(),
        Inventory.is_active == True
    ).count()
    
    from datetime import timedelta
    expiring_soon = Inventory.query.filter(
        Inventory.expiry_date <= date.today() + timedelta(days=30),
        Inventory.expiry_date >= date.today(),
        Inventory.is_active == True
    ).count()
    
    return render_template('pharmacy/reports.html',
                         sales_data=sales_data,
                         top_medicines=top_medicines,
                         low_stock_items=low_stock_items,
                         expired_items=expired_items,
                         expiring_soon=expiring_soon,
                         date_from=date_from,
                         date_to=date_to)


# ============ API ENDPOINTS ============

@pharmacy_bp.route('/api/medicines/search')
@login_required
@pharmacist_required
def api_search_medicines():
    """Search medicines for autocomplete"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    medicines = Inventory.query.filter(
        db.or_(
            Inventory.medicine_name.ilike(f'%{query}%'),
            Inventory.generic_name.ilike(f'%{query}%')
        ),
        Inventory.is_active == True
    ).limit(10).all()
    
    return jsonify([{
        'id': m.id,
        'name': m.medicine_name,
        'generic_name': m.generic_name,
        'stock': m.current_stock,
        'unit': m.unit,
        'price': m.unit_price,
        'is_low_stock': m.is_low_stock()
    } for m in medicines])


@pharmacy_bp.route('/api/stock-alerts')
@login_required
@pharmacist_required
def api_stock_alerts():
    """Get stock alerts"""
    low_stock = Inventory.query.filter(
        Inventory.current_stock <= Inventory.reorder_level,
        Inventory.current_stock > 0,
        Inventory.is_active == True
    ).all()
    
    out_of_stock = Inventory.query.filter(
        Inventory.current_stock <= 0,
        Inventory.is_active == True
    ).all()
    
    expired = Inventory.query.filter(
        Inventory.expiry_date < date.today(),
        Inventory.is_active == True
    ).all()
    
    return jsonify({
        'low_stock': [{
            'id': m.id,
            'name': m.medicine_name,
            'stock': m.current_stock,
            'reorder_level': m.reorder_level
        } for m in low_stock],
        'out_of_stock': [{
            'id': m.id,
            'name': m.medicine_name
        } for m in out_of_stock],
        'expired': [{
            'id': m.id,
            'name': m.medicine_name,
            'expiry_date': m.expiry_date.isoformat() if m.expiry_date else None
        } for m in expired]
    })