"""
Video Service - WebRTC and video session management
"""

from datetime import datetime
import jwt
from flask import current_app,request
from flask_socketio import emit, join_room, leave_room

class VideoService:
    """Service for managing video consultations"""
    
    @staticmethod
    def generate_token(room_id, user_id, user_role):
        """Generate JWT token for video room access"""
        import time
        
        payload = {
            'room_id': room_id,
            'user_id': user_id,
            'role': user_role,
            'iat': int(time.time()),
            'exp': int(time.time()) + 7200  # 2 hours expiry
        }
        
        secret_key = current_app.config.get('SECRET_KEY', 'default-secret')
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        """Verify JWT token"""
        try:
            secret_key = current_app.config.get('SECRET_KEY', 'default-secret')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


def register_socket_events(socketio):
    """Register WebSocket events for video calls"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"Client connected: {request.sid if hasattr(request, 'sid') else 'unknown'}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"Client disconnected")
    
    @socketio.on('join_room')
    def handle_join_room(data):
        """Handle user joining a video room"""
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        user_type = data.get('user_type')
        token = data.get('token')
        
        # Verify token
        payload = VideoService.verify_token(token)
        if not payload or payload.get('room_id') != room_id:
            emit('error', {'message': 'Invalid token'})
            return
        
        join_room(room_id)
        
        # Notify others in the room
        emit('user_joined', {
            'user_id': user_id,
            'user_type': user_type
        }, room=room_id, include_self=False)
        
        # Send confirmation to joiner
        emit('joined', {
            'room_id': room_id,
            'message': f'Joined room {room_id}'
        })
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        """Handle user leaving a video room"""
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        user_type = data.get('user_type')
        
        leave_room(room_id)
        
        emit('user_left', {
            'user_id': user_id,
            'user_type': user_type
        }, room=room_id)
    
    @socketio.on('offer')
    def handle_offer(data):
        """Handle WebRTC offer"""
        room_id = data.get('room_id')
        offer = data.get('offer')
        
        emit('offer', {
            'offer': offer,
            'sender_id': data.get('sender_id')
        }, room=room_id, include_self=False)
    
    @socketio.on('answer')
    def handle_answer(data):
        """Handle WebRTC answer"""
        room_id = data.get('room_id')
        answer = data.get('answer')
        
        emit('answer', {
            'answer': answer,
            'sender_id': data.get('sender_id')
        }, room=room_id, include_self=False)
    
    @socketio.on('ice_candidate')
    def handle_ice_candidate(data):
        """Handle ICE candidate exchange"""
        room_id = data.get('room_id')
        candidate = data.get('candidate')
        
        emit('ice_candidate', {
            'candidate': candidate,
            'sender_id': data.get('sender_id')
        }, room=room_id, include_self=False)
    
    @socketio.on('chat_message')
    def handle_chat_message(data):
        """Handle in-call chat messages"""
        room_id = data.get('room_id')
        message = data.get('message')
        sender = data.get('sender')
        
        emit('chat_message', {
            'message': message,
            'sender': sender,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room_id)
    
    @socketio.on('toggle_video')
    def handle_toggle_video(data):
        """Handle video toggle notification"""
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        video_enabled = data.get('video_enabled')
        
        emit('video_toggled', {
            'user_id': user_id,
            'video_enabled': video_enabled
        }, room=room_id, include_self=False)
    
    @socketio.on('toggle_audio')
    def handle_toggle_audio(data):
        """Handle audio toggle notification"""
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        audio_enabled = data.get('audio_enabled')
        
        emit('audio_toggled', {
            'user_id': user_id,
            'audio_enabled': audio_enabled
        }, room=room_id, include_self=False)
    
    @socketio.on('end_call')
    def handle_end_call(data):
        """Handle call ending"""
        room_id = data.get('room_id')
        ended_by = data.get('ended_by')
        
        emit('call_ended', {
            'ended_by': ended_by,
            'message': 'The call has ended'
        }, room=room_id)


# Import request for socket events
try:
    from flask import request
except:
    request = None