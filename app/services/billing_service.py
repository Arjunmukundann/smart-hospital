"""
Billing Service - Invoice and payment management
"""

from datetime import datetime
from flask import current_app

class BillingService:
    """Service for billing operations"""
    
    @staticmethod
    def calculate_bill(items, discount=0, tax_rate=None):
        """
        Calculate bill totals
        
        Args:
            items: List of dict with 'quantity' and 'unit_price'
            discount: Discount amount
            tax_rate: Tax rate (default from config)
            
        Returns:
            dict: Bill calculation results
        """
        if tax_rate is None:
            tax_rate = current_app.config.get('TAX_RATE', 0.05)
        
        subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
        tax = round(subtotal * tax_rate, 2)
        discount = min(discount, subtotal)  # Discount can't exceed subtotal
        total = round(subtotal + tax - discount, 2)
        
        return {
            'subtotal': subtotal,
            'tax': tax,
            'tax_rate': tax_rate,
            'discount': discount,
            'total': total
        }
    
    @staticmethod
    def calculate_insurance_coverage(total_amount, policy):
        """
        Calculate insurance coverage
        
        Args:
            total_amount: Total bill amount
            policy: PatientInsurance object
            
        Returns:
            dict: Coverage calculation
        """
        if not policy or not policy.is_valid:
            return {
                'covered_amount': 0,
                'patient_responsibility': total_amount,
                'coverage_percentage': 0
            }
        
        # Check deductible
        remaining_deductible = policy.remaining_deductible
        amount_after_deductible = max(0, total_amount - remaining_deductible)
        
        # Calculate coverage
        coverage_percentage = policy.coverage_percentage / 100
        covered_amount = round(amount_after_deductible * coverage_percentage, 2)
        
        # Check max coverage
        if policy.max_coverage:
            covered_amount = min(covered_amount, policy.max_coverage)
        
        # Add copay
        copay = policy.copay_amount or 0
        
        patient_responsibility = round(total_amount - covered_amount + copay, 2)
        
        return {
            'covered_amount': covered_amount,
            'patient_responsibility': patient_responsibility,
            'coverage_percentage': policy.coverage_percentage,
            'deductible_applied': min(remaining_deductible, total_amount),
            'copay': copay
        }
    
    @staticmethod
    def generate_invoice_number(prefix='INV'):
        """Generate unique invoice number"""
        from app.models.pharmacy import PharmacyBill
        
        today = datetime.now().strftime('%Y%m%d')
        
        # Get last invoice of the day
        last_bill = PharmacyBill.query.filter(
            PharmacyBill.bill_number.like(f'{prefix}{today}%')
        ).order_by(PharmacyBill.id.desc()).first()
        
        if last_bill:
            last_num = int(last_bill.bill_number[-4:])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'{prefix}{today}{new_num:04d}'