/**
 * Chatbot JavaScript - Main functionality
 */

class SmartHospitalChatbot {
    constructor(options = {}) {
        this.sessionId = this.getOrCreateSession();
        this.isOpen = false;
        this.isTyping = false;
        this.messageHistory = [];
        
        this.config = {
            endpoint: '/chatbot/message',
            suggestionsEndpoint: '/chatbot/suggestions',
            maxMessages: 100,
            typingDelay: 500,
            ...options
        };
        
        this.init();
    }
    
    init() {
        this.createWidget();
        this.bindEvents();
        this.loadSuggestions();
    }
    
    getOrCreateSession() {
        let session = localStorage.getItem('chatbot_session_id');
        if (!session) {
            session = 'session_' + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('chatbot_session_id', session);
        }
        return session;
    }
    
    createWidget() {
        // Widget is created via HTML template, this method can be used for dynamic creation
        this.widget = document.getElementById('chatbotWidget');
        this.toggle = document.getElementById('chatbotToggle');
        this.window = document.getElementById('chatbotWindow');
        this.messagesContainer = document.getElementById('chatbotMessages');
        this.input = document.getElementById('chatbotInput');
        this.sendBtn = document.getElementById('chatbotSend');
        this.closeBtn = document.getElementById('chatbotClose');
    }
    
    bindEvents() {
        if (this.toggle) {
            this.toggle.addEventListener('click', () => this.toggleChat());
        }
        
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.closeChat());
        }
        
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        if (this.input) {
            this.input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            this.input.addEventListener('input', () => {
                this.sendBtn.disabled = !this.input.value.trim();
            });
        }
        
        // Quick reply buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-reply-btn')) {
                this.handleQuickReply(e.target.dataset.message);
            }
            
            if (e.target.classList.contains('chat-doctor-card') || 
                e.target.closest('.chat-doctor-card')) {
                const card = e.target.classList.contains('chat-doctor-card') ? 
                             e.target : e.target.closest('.chat-doctor-card');
                const doctorId = card.dataset.doctorId;
                if (doctorId) {
                    window.location.href = `/patient/doctor/${doctorId}`;
                }
            }
        });
    }
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }
    
    openChat() {
        this.isOpen = true;
        this.window.style.display = 'flex';
        this.toggle.classList.add('active');
        this.input.focus();
        this.hideBadge();
    }
    
    closeChat() {
        this.isOpen = false;
        this.window.style.display = 'none';
        this.toggle.classList.remove('active');
    }
    
    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message
        this.addMessage(message, 'user');
        this.input.value = '';
        this.sendBtn.disabled = true;
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            const response = await fetch(this.config.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            
            // Simulate typing delay
            await this.delay(this.config.typingDelay);
            
            this.hideTyping();
            
            if (data.response) {
                this.handleBotResponse(data.response);
            }
        } catch (error) {
            console.error('Chatbot error:', error);
            this.hideTyping();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
    }
    
    handleQuickReply(message) {
        this.input.value = message;
        this.sendMessage();
    }
    
    addMessage(content, type, extras = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        if (typeof content === 'string') {
            bubble.innerHTML = `<p>${this.formatMessage(content)}</p>`;
        } else {
            bubble.innerHTML = content;
        }
        
        // Add quick replies if provided
        if (extras.quickReplies && extras.quickReplies.length > 0) {
            const repliesDiv = document.createElement('div');
            repliesDiv.className = 'quick-replies';
            extras.quickReplies.forEach(reply => {
                const btn = document.createElement('button');
                btn.className = 'quick-reply-btn';
                btn.dataset.message = reply;
                btn.textContent = reply;
                repliesDiv.appendChild(btn);
            });
            bubble.appendChild(repliesDiv);
        }
        
        messageDiv.appendChild(bubble);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store in history
        this.messageHistory.push({ content, type, timestamp: new Date() });
        
        // Trim history if needed
        if (this.messageHistory.length > this.config.maxMessages) {
            this.messageHistory.shift();
        }
    }
    
    handleBotResponse(response) {
        let content = '';
        let extras = {};
        
        // Handle message
        if (response.message) {
            content = response.message;
        }
        
        // Handle different response types
        switch (response.type) {
            case 'doctor_list':
                content += this.renderDoctorList(response.doctors);
                break;
                
            case 'doctor_profile':
                content += this.renderDoctorProfile(response.doctor);
                break;
                
            case 'department_list':
                content += this.renderDepartmentList(response.departments);
                break;
                
            case 'appointment_list':
                content += this.renderAppointmentList(response.appointments);
                break;
                
            case 'hospital_info':
                content += this.renderHospitalInfo(response.info);
                break;
                
            case 'statistics':
                content += this.renderStatistics(response.stats);
                break;
        }
        
        // Handle suggestions
        if (response.suggestions) {
            extras.quickReplies = response.suggestions;
        }
        
        // Handle action buttons
        if (response.action) {
            content += this.renderActionButton(response.action);
        }
        
        this.addMessage(content, 'bot', extras);
    }
    
    renderDoctorList(doctors) {
        if (!doctors || doctors.length === 0) return '';
        
        return doctors.map(doc => `
            <div class="chat-doctor-card" data-doctor-id="${doc.id}">
                <img src="${doc.profile_picture || '/static/images/default_avatar.png'}" alt="${doc.name}">
                <div class="chat-doctor-info">
                    <h6>Dr. ${doc.name}</h6>
                    <p>${doc.specialization || 'General Medicine'}</p>
                    <p class="rating">⭐ ${doc.rating || 'New'}</p>
                </div>
            </div>
        `).join('');
    }
    
    renderDoctorProfile(doctor) {
        if (!doctor) return '';
        
        return `
            <div class="chat-doctor-card" data-doctor-id="${doctor.id}">
                <img src="${doctor.profile_picture || '/static/images/default_avatar.png'}" alt="${doctor.name}">
                <div class="chat-doctor-info">
                    <h6>Dr. ${doctor.name}</h6>
                    <p>${doctor.specialization}</p>
                    <p>⭐ ${doctor.rating || 0} (${doctor.total_reviews || 0} reviews)</p>
                    <p>💼 ${doctor.experience}</p>
                    <p>💰 Consultation: ₹${doctor.consultation_fee || 0}</p>
                    ${doctor.is_available_online ? '<span class="badge bg-success">Video Available</span>' : ''}
                </div>
            </div>
        `;
    }
    
    renderDepartmentList(departments) {
        if (!departments || departments.length === 0) return '';
        
        return '<div class="mt-2">' + departments.map(dept => `
            <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                <span>🏥 ${dept.name}</span>
                <span class="badge bg-primary">${dept.doctors || 0} doctors</span>
            </div>
        `).join('') + '</div>';
    }
    
    renderAppointmentList(appointments) {
        if (!appointments || appointments.length === 0) return '';
        
        return appointments.map(apt => `
            <div class="border rounded p-2 mb-2">
                <div class="d-flex justify-content-between">
                    <strong>${apt.doctor_name}</strong>
                    <span class="badge bg-${apt.status === 'confirmed' ? 'success' : 'warning'}">${apt.status}</span>
                </div>
                <small class="text-muted">
                    📅 ${apt.formatted_date} at ${apt.formatted_time}
                </small>
            </div>
        `).join('');
    }
    
    renderHospitalInfo(info) {
        if (!info) return '';
        
        return `
            <div class="mt-2">
                <p><strong>📍 Address:</strong><br>${info.address || 'N/A'}</p>
                <p><strong>📞 Phone:</strong> ${info.phone || 'N/A'}</p>
                <p><strong>🕐 Hours:</strong><br>${(info.working_hours || 'N/A').replace(/\n/g, '<br>')}</p>
            </div>
        `;
    }
    
    renderStatistics(stats) {
        if (!stats) return '';
        
        return `
            <div class="row text-center mt-2">
                ${Object.entries(stats).map(([key, value]) => `
                    <div class="col-6 mb-2">
                        <div class="border rounded p-2">
                            <div class="h4 mb-0">${value}</div>
                            <small class="text-muted">${key.replace(/_/g, ' ')}</small>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    renderActionButton(action) {
        if (action.type === 'link') {
            return `
                <div class="mt-2">
                    <a href="${action.url}" class="btn btn-sm btn-primary">
                        ${action.text} <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
            `;
        }
        return '';
    }
    
    showTyping() {
        this.isTyping = true;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message bot';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        const typing = document.getElementById('typingIndicator');
        if (typing) typing.remove();
    }
    
    showBadge(count = 1) {
        const badge = document.getElementById('chatbotBadge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = 'flex';
        }
    }
    
    hideBadge() {
        const badge = document.getElementById('chatbotBadge');
        if (badge) {
            badge.style.display = 'none';
        }
    }
    
    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }
    
    formatMessage(text) {
        // Convert URLs to links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        text = text.replace(urlRegex, '<a href="$1" target="_blank">$1</a>');
        
        // Convert newlines to <br>
        text = text.replace(/\n/g, '<br>');
        
        return text;
    }
    
    async loadSuggestions() {
        try {
            const response = await fetch(this.config.suggestionsEndpoint);
            const data = await response.json();
            
            if (data.suggestions) {
                // Add initial suggestions as quick replies
                const welcomeMessage = this.messagesContainer.querySelector('.bot-message');
                if (welcomeMessage) {
                    const repliesContainer = welcomeMessage.querySelector('.quick-replies');
                    if (repliesContainer) {
                        repliesContainer.innerHTML = data.suggestions.slice(0, 4).map(s => 
                            `<button class="quick-reply-btn" data-message="${s}">${s}</button>`
                        ).join('');
                    }
                }
            }
        } catch (error) {
            console.error('Error loading suggestions:', error);
        }
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    clearHistory() {
        this.messageHistory = [];
        this.messagesContainer.innerHTML = '';
        this.addWelcomeMessage();
    }
    
    addWelcomeMessage() {
        this.addMessage(
            '👋 Hello! I\'m your Smart Hospital assistant. How can I help you today?',
            'bot',
            {
                quickReplies: ['Find a doctor', 'Hospital timings', 'Book appointment', 'View departments']
            }
        );
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('chatbotWidget')) {
        window.chatbot = new SmartHospitalChatbot();
    }
});