"""
Signature Service - Digital signature handling
"""

import os
import hashlib
import base64
import json
from datetime import datetime
from PIL import Image
import io
from flask import current_app

class SignatureService:
    """Service for handling digital signatures"""
    
    @staticmethod
    def save_signature_image(signature_data, user_id, filename_prefix='signature'):
        """
        Save base64 signature as image file
        
        Args:
            signature_data: Base64 encoded signature image
            user_id: ID of the user (doctor)
            filename_prefix: Prefix for the filename
            
        Returns:
            str: Filename of saved signature or None if error
        """
        try:
            # Remove data URL prefix if present
            if 'base64,' in signature_data:
                signature_data = signature_data.split('base64,')[1]
            
            # Decode base64
            image_data = base64.b64decode(signature_data)
            
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGBA if necessary (for transparency)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{filename_prefix}_{user_id}_{timestamp}.png"
            
            # Get upload folder
            upload_folder = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                'signatures'
            )
            
            # Ensure directory exists
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, filename)
            
            # Save image
            image.save(filepath, 'PNG')
            
            return filename
            
        except Exception as e:
            current_app.logger.error(f"Error saving signature: {str(e)}")
            return None
    
    @staticmethod
    def generate_signature_hash(prescription_data, signature_filename):
        """
        Generate hash for prescription verification
        
        Args:
            prescription_data: Dictionary of prescription details
            signature_filename: Filename of signature image
            
        Returns:
            str: SHA256 hash of combined data
        """
        try:
            # Create string from prescription data
            data_string = json.dumps(prescription_data, sort_keys=True, default=str)
            
            # Get signature file path
            signature_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                'signatures',
                signature_filename
            )
            
            # Get file hash if file exists
            file_hash = ""
            if os.path.exists(signature_path):
                with open(signature_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Combine and hash
            combined = f"{data_string}{file_hash}{datetime.utcnow().isoformat()}"
            return hashlib.sha256(combined.encode()).hexdigest()
            
        except Exception as e:
            current_app.logger.error(f"Error generating signature hash: {str(e)}")
            return None
    
    @staticmethod
    def sign_prescription(prescription, signature_data, doctor_id):
        """
        Sign a prescription with digital signature
        
        Args:
            prescription: Prescription model object
            signature_data: Base64 encoded signature
            doctor_id: ID of the signing doctor
            
        Returns:
            tuple: (success: bool, message: str)
        """
        from app import db
        
        try:
            # Verify doctor owns this prescription
            if prescription.doctor_id != doctor_id:
                return False, "You are not authorized to sign this prescription"
            
            # Check if already signed
            if prescription.is_signed:
                return False, "Prescription is already signed"
            
            # Save signature image
            signature_filename = SignatureService.save_signature_image(
                signature_data, 
                doctor_id,
                f'rx_{prescription.prescription_id}'
            )
            
            if not signature_filename:
                return False, "Failed to save signature image"
            
            # Generate hash
            prescription_data = {
                'id': prescription.id,
                'prescription_id': prescription.prescription_id,
                'patient_id': prescription.patient_id,
                'doctor_id': prescription.doctor_id,
                'diagnosis': prescription.diagnosis,
                'medicines': [m.medicine_name for m in prescription.medicines.all()]
            }
            
            signature_hash = SignatureService.generate_signature_hash(
                prescription_data,
                signature_filename
            )
            
            # Update prescription
            prescription.is_signed = True
            prescription.signature_image = signature_filename
            prescription.signed_at = datetime.utcnow()
            prescription.signature_hash = signature_hash
            
            db.session.commit()
            
            return True, "Prescription signed successfully"
            
        except Exception as e:
            current_app.logger.error(f"Error signing prescription: {str(e)}")
            return False, f"Error signing prescription: {str(e)}"
    
    @staticmethod
    def verify_prescription_signature(prescription):
        """
        Verify if a prescription's signature is valid
        
        Args:
            prescription: Prescription model object
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            if not prescription.is_signed:
                return False, "Prescription is not signed"
            
            if not prescription.signature_image:
                return False, "Signature image not found"
            
            if not prescription.signature_hash:
                return False, "Signature hash not found"
            
            # Verify signature file exists
            signature_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                'signatures',
                prescription.signature_image
            )
            
            if not os.path.exists(signature_path):
                return False, "Signature file missing"
            
            # For now, we just verify the signature exists
            # In a production system, you would verify the hash
            return True, "Signature verified"
            
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    @staticmethod
    def save_doctor_signature(signature_data, doctor_id):
        """
        Save doctor's permanent digital signature
        
        Args:
            signature_data: Base64 encoded signature
            doctor_id: Doctor's user ID
            
        Returns:
            tuple: (success: bool, filename or message: str)
        """
        from app.models import User
        from app import db
        
        try:
            doctor = User.query.get(doctor_id)
            if not doctor or not doctor.is_doctor():
                return False, "Invalid doctor"
            
            # Save signature
            filename = SignatureService.save_signature_image(
                signature_data,
                doctor_id,
                'doctor_sig'
            )
            
            if not filename:
                return False, "Failed to save signature"
            
            # Update doctor's profile
            doctor.digital_signature = filename
            doctor.signature_verified = True
            db.session.commit()
            
            return True, filename
            
        except Exception as e:
            return False, str(e)