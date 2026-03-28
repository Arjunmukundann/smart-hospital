"""
Insurance Service - Insurance verification and claims management
"""

from datetime import datetime, date
from flask import current_app
from app import db
from app.models.insurance import InsuranceProvider, PatientInsurance, InsuranceClaim

class InsuranceService:
    """Service for insurance operations"""
    
    @staticmethod
    def verify_insurance(policy_id, user_id=None):
        """
        Verify insurance policy
        
        Args:
            policy_id: PatientInsurance ID
            user_id: User performing verification
            
        Returns:
            tuple: (success, message)
        """
        policy = PatientInsurance.query.get(policy_id)
        if not policy:
            return False, "Policy not found"
        
        # Check expiry
        if policy.expiry_date < date.today():
            policy.verification_status = 'expired'
            db.session.commit()
            return False, "Policy has expired"
        
        # Check if effective
        if policy.effective_date > date.today():
            return False, "Policy not yet effective"
        
        # In a real system, this would call the insurance provider's API
        # For now, we'll auto-verify
        policy.is_verified = True
        policy.verified_at = datetime.utcnow()
        policy.verified_by = user_id
        policy.verification_status = 'verified'
        
        db.session.commit()
        
        return True, "Insurance verified successfully"
    
    @staticmethod
    def check_coverage(policy_id, service_type, amount):
        """
        Check if a service is covered and calculate coverage
        
        Args:
            policy_id: PatientInsurance ID
            service_type: Type of service (consultation, medication, etc.)
            amount: Total amount
            
        Returns:
            dict: Coverage details
        """
        policy = PatientInsurance.query.get(policy_id)
        if not policy:
            return {
                'is_covered': False,
                'message': 'Policy not found',
                'covered_amount': 0,
                'patient_responsibility': amount
            }
        
        if not policy.is_valid:
            return {
                'is_covered': False,
                'message': 'Policy is not valid or verified',
                'covered_amount': 0,
                'patient_responsibility': amount
            }
        
        # Calculate coverage
        remaining_deductible = policy.remaining_deductible
        
        # Apply deductible first
        amount_after_deductible = max(0, amount - remaining_deductible)
        
        # Calculate coverage percentage
        coverage_percentage = policy.coverage_percentage / 100
        covered_amount = amount_after_deductible * coverage_percentage
        
        # Check max coverage limit
        if policy.max_coverage and covered_amount > policy.max_coverage:
            covered_amount = policy.max_coverage
        
        # Apply copay
        copay = policy.copay_amount or 0
        patient_responsibility = amount - covered_amount + copay
        
        return {
            'is_covered': True,
            'coverage_percentage': policy.coverage_percentage,
            'deductible_applied': min(remaining_deductible, amount),
            'covered_amount': round(covered_amount, 2),
            'copay': copay,
            'patient_responsibility': round(max(0, patient_responsibility), 2)
        }
    
    @staticmethod
    def create_claim(policy_id, patient_id, claim_type, total_amount, 
                    appointment_id=None, bill_id=None, notes=None):
        """
        Create an insurance claim
        
        Args:
            policy_id: PatientInsurance ID
            patient_id: Patient ID
            claim_type: Type of claim
            total_amount: Total bill amount
            appointment_id: Related appointment (optional)
            bill_id: Related bill (optional)
            notes: Additional notes
            
        Returns:
            InsuranceClaim or None
        """
        policy = PatientInsurance.query.get(policy_id)
        if not policy or not policy.is_valid:
            return None
        
        # Calculate coverage
        coverage = InsuranceService.check_coverage(policy_id, claim_type, total_amount)
        
        claim = InsuranceClaim(
            claim_number=InsuranceClaim.generate_claim_number(),
            policy_id=policy_id,
            patient_id=patient_id,
            appointment_id=appointment_id,
            bill_id=bill_id,
            claim_type=claim_type,
            total_amount=total_amount,
            claimed_amount=coverage['covered_amount'],
            status='submitted',
            notes=notes
        )
        
        db.session.add(claim)
        db.session.commit()
        
        return claim
    
    @staticmethod
    def process_claim(claim_id, approved_amount=None, status='approved', 
                     rejection_reason=None, processed_by=None):
        """
        Process an insurance claim (approve/reject)
        
        Args:
            claim_id: InsuranceClaim ID
            approved_amount: Amount approved (for approval)
            status: 'approved' or 'rejected'
            rejection_reason: Reason for rejection
            processed_by: User processing the claim
            
        Returns:
            tuple: (success, message)
        """
        claim = InsuranceClaim.query.get(claim_id)
        if not claim:
            return False, "Claim not found"
        
        if claim.status not in ['submitted', 'processing']:
            return False, f"Claim cannot be processed (current status: {claim.status})"
        
        claim.processed_at = datetime.utcnow()
        
        if status == 'approved':
            claim.status = 'approved'
            claim.approved_amount = approved_amount or claim.claimed_amount
            claim.patient_responsibility = claim.total_amount - claim.approved_amount
            
            # Update deductible met on policy
            policy = claim.policy
            if policy:
                policy.deductible_met = min(
                    policy.deductible,
                    policy.deductible_met + claim.approved_amount
                )
        else:
            claim.status = 'rejected'
            claim.rejection_reason = rejection_reason
            claim.approved_amount = 0
            claim.patient_responsibility = claim.total_amount
        
        db.session.commit()
        
        return True, f"Claim {status}"
    
    @staticmethod
    def get_patient_insurance_summary(patient_id):
        """
        Get summary of patient's insurance
        
        Args:
            patient_id: Patient ID
            
        Returns:
            dict: Insurance summary
        """
        policies = PatientInsurance.query.filter_by(
            patient_id=patient_id,
            is_active=True
        ).all()
        
        if not policies:
            return {
                'has_insurance': False,
                'policies': [],
                'primary_policy': None
            }
        
        primary = next((p for p in policies if p.is_primary), policies[0])
        
        return {
            'has_insurance': True,
            'policies': [p.to_dict() for p in policies],
            'primary_policy': primary.to_dict() if primary else None,
            'total_policies': len(policies)
        }
    
    @staticmethod
    def get_providers():
        """Get all active insurance providers"""
        return InsuranceProvider.query.filter_by(is_active=True).all()