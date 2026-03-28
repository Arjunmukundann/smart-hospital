"""
Image Service - Profile picture handling
"""

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
from flask import current_app

class ImageService:
    """Service for handling image uploads"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_SIZE = (500, 500)  # Maximum dimensions for profile pictures
    THUMBNAIL_SIZE = (150, 150)
    
    @staticmethod
    def allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ImageService.ALLOWED_EXTENSIONS
    
    @staticmethod
    def save_profile_picture(file, user_id, folder='profile_pictures'):
        """
        Save and process profile picture
        
        Args:
            file: FileStorage object
            user_id: User ID for filename
            folder: Subfolder name
            
        Returns:
            str: Saved filename or None if error
        """
        if not file or not file.filename:
            return None
        
        if not ImageService.allowed_file(file.filename):
            return None
        
        try:
            # Generate unique filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"profile_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Get upload folder
            upload_folder = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                folder
            )
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, filename)
            
            # Open and process image
            image = Image.open(file)
            
            # Convert to RGB if necessary (for PNG with transparency)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize if too large
            image.thumbnail(ImageService.MAX_SIZE, Image.Resampling.LANCZOS)
            
            # Save
            image.save(filepath, quality=85, optimize=True)
            
            return filename
            
        except Exception as e:
            current_app.logger.error(f"Error saving profile picture: {str(e)}")
            return None
    
    @staticmethod
    def delete_profile_picture(filename, folder='profile_pictures'):
        """Delete a profile picture file"""
        if not filename or filename == 'default_avatar.png':
            return True
        
        try:
            filepath = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                folder,
                filename
            )
            
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting profile picture: {str(e)}")
            return False
    
    @staticmethod
    def create_thumbnail(source_path, thumb_path, size=None):
        """Create thumbnail from source image"""
        if size is None:
            size = ImageService.THUMBNAIL_SIZE
        
        try:
            image = Image.open(source_path)
            image.thumbnail(size, Image.Resampling.LANCZOS)
            image.save(thumb_path, quality=80, optimize=True)
            return True
        except Exception as e:
            current_app.logger.error(f"Error creating thumbnail: {str(e)}")
            return False