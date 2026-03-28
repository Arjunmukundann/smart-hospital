"""
Chatbot Routes - AI-powered hospital assistant
"""

from datetime import datetime
import uuid
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db
from app.models.chat_log import ChatLog, ChatbotFAQ
from app.services.chatbot_service import ChatbotService
from flask_wtf.csrf import CSRFProtect
from app.extensions import csrf

chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.route('/widget')
def widget():
    """Render chatbot widget (can be embedded)"""
    return render_template('chatbot/widget.html')


@chatbot_bp.route('/fullscreen')
def fullscreen():
    """Full page chatbot interface"""
    return render_template('chatbot/fullscreen.html')

@csrf.exempt 
@chatbot_bp.route('/message', methods=['POST'])
def process_message():
    """Process user message and return bot response"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    message = data.get('message', '').strip()
    session_id = data.get('session_id') or str(uuid.uuid4())
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Get user if logged in
    user = current_user if current_user.is_authenticated else None
    
    # Process message with chatbot service
    chatbot = ChatbotService()
    response = chatbot.process_message(message, user)
    
    # Log the conversation
    try:
        log = ChatLog(
            session_id=session_id,
            user_id=current_user.id if current_user.is_authenticated else None,
            user_message=message,
            bot_response=response.get('message', ''),
            intent=response.get('type', 'unknown'),
            confidence=response.get('confidence')
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # Don't fail the request if logging fails
        print(f"Error logging chat: {e}")
    
    return jsonify({
        'session_id': session_id,
        'response': response
    })


@chatbot_bp.route('/history/<session_id>')
def chat_history(session_id):
    """Get chat history for a session"""
    logs = ChatLog.query.filter_by(session_id=session_id).order_by(
        ChatLog.created_at.asc()
    ).all()
    
    history = []
    for log in logs:
        history.append({
            'user_message': log.user_message,
            'bot_response': log.bot_response,
            'timestamp': log.created_at.isoformat()
        })
    
    return jsonify({'history': history})


@chatbot_bp.route('/suggestions')
def get_suggestions():
    """Get suggested questions"""
    suggestions = [
        "Tell me about the hospital",
        "What are the hospital timings?",
        "Find a doctor",
        "How do I book an appointment?",
        "What departments are available?",
        "Show me available doctors",
        "What insurance do you accept?",
        "Emergency contact number"
    ]
    
    # Add personalized suggestions if logged in
    if current_user.is_authenticated:
        if current_user.is_patient():
            suggestions = [
                "Show my upcoming appointments",
                "View my prescriptions",
                "Book a new appointment"
            ] + suggestions[:5]
        elif current_user.is_doctor():
            suggestions = [
                "Show my today's schedule",
                "How many patients do I have?"
            ] + suggestions[:5]
    
    return jsonify({'suggestions': suggestions})


@chatbot_bp.route('/faqs')
def get_faqs():
    """Get frequently asked questions"""
    faqs = ChatbotFAQ.query.filter_by(is_active=True).order_by(
        ChatbotFAQ.view_count.desc()
    ).limit(10).all()
    
    return jsonify({
        'faqs': [{
            'id': faq.id,
            'question': faq.question,
            'answer': faq.answer,
            'category': faq.category
        } for faq in faqs]
    })


@chatbot_bp.route('/faq/<int:faq_id>')
def get_faq(faq_id):
    """Get specific FAQ and increment view count"""
    faq = ChatbotFAQ.query.get_or_404(faq_id)
    faq.view_count += 1
    db.session.commit()
    
    return jsonify({
        'question': faq.question,
        'answer': faq.answer,
        'category': faq.category
    })


@chatbot_bp.route('/faq/<int:faq_id>/helpful', methods=['POST'])
def mark_helpful(faq_id):
    """Mark FAQ as helpful"""
    faq = ChatbotFAQ.query.get_or_404(faq_id)
    faq.helpful_count += 1
    db.session.commit()
    
    return jsonify({'success': True})


@chatbot_bp.route('/doctor/<int:doctor_id>')
def get_doctor_info(doctor_id):
    """Get detailed doctor information for chatbot"""
    chatbot = ChatbotService()
    from app.models import User
    
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first()
    if not doctor:
        return jsonify({'error': 'Doctor not found'}), 404
    
    info = chatbot.get_doctor_details(doctor)
    return jsonify(info)


@chatbot_bp.route('/departments')
def get_departments():
    """Get list of departments"""
    chatbot = ChatbotService()
    departments = chatbot.get_departments()
    return jsonify({'departments': departments})


@chatbot_bp.route('/doctors')
def get_doctors():
    """Get list of doctors (optionally filtered)"""
    specialty = request.args.get('specialty', '')
    department = request.args.get('department', '')
    
    chatbot = ChatbotService()
    doctors = chatbot.get_doctors(specialty=specialty, department=department)
    
    return jsonify({'doctors': doctors})