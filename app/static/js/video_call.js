/**
 * Video Call JavaScript - WebRTC Implementation
 */

class VideoCallManager {
    constructor(options) {
        this.roomId = options.roomId;
        this.userId = options.userId;
        this.userType = options.userType;
        this.token = options.token;
        
        this.localStream = null;
        this.remoteStream = null;
        this.peerConnection = null;
        this.socket = null;
        
        this.isAudioEnabled = true;
        this.isVideoEnabled = true;
        this.isScreenSharing = false;
        this.callStartTime = null;
        this.durationInterval = null;
        
        this.config = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };
        
        this.elements = {
            localVideo: document.getElementById('localVideo'),
            remoteVideo: document.getElementById('remoteVideo'),
            waitingOverlay: document.getElementById('waitingOverlay'),
            videoPlaceholder: document.getElementById('videoPlaceholder'),
            statusIndicator: document.getElementById('statusIndicator'),
            connectionStatus: document.getElementById('connectionStatus'),
            callDuration: document.getElementById('callDuration'),
            chatMessages: document.getElementById('chatMessages'),
            chatInput: document.getElementById('chatInput')
        };
        
        this.init();
    }
    
    async init() {
        try {
            await this.getLocalStream();
            this.initSocket();
            this.bindControlEvents();
            this.updateStatus('connecting', 'Connecting...');
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to access camera/microphone');
        }
    }
    
    async getLocalStream() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            
            this.elements.localVideo.srcObject = this.localStream;
            return this.localStream;
        } catch (error) {
            console.error('Error getting local stream:', error);
            throw error;
        }
    }
    
    initSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Socket connected');
            this.joinRoom();
        });
        
        this.socket.on('joined', (data) => {
            console.log('Joined room:', data);
            this.updateStatus('connecting', 'Waiting for participant...');
        });
        
        this.socket.on('user_joined', async (data) => {
            console.log('User joined:', data);
            this.hideWaiting();
            await this.createPeerConnection();
            await this.createAndSendOffer();
        });
        
        this.socket.on('offer', async (data) => {
            console.log('Received offer');
            this.hideWaiting();
            await this.createPeerConnection();
            await this.handleOffer(data.offer);
        });
        
        this.socket.on('answer', async (data) => {
            console.log('Received answer');
            await this.handleAnswer(data.answer);
        });
        
        this.socket.on('ice_candidate', async (data) => {
            await this.handleIceCandidate(data.candidate);
        });
        
        this.socket.on('user_left', (data) => {
            console.log('User left:', data);
            this.handleUserLeft();
        });
        
        this.socket.on('call_ended', () => {
            this.handleCallEnded();
        });
        
        this.socket.on('chat_message', (data) => {
            this.addChatMessage(data.message, data.sender !== this.userType);
        });
        
        this.socket.on('video_toggled', (data) => {
            this.handleRemoteVideoToggle(data.video_enabled);
        });
        
        this.socket.on('audio_toggled', (data) => {
            this.handleRemoteAudioToggle(data.audio_enabled);
        });
    }
    
    joinRoom() {
        this.socket.emit('join_room', {
            room_id: this.roomId,
            user_id: this.userId,
            user_type: this.userType,
            token: this.token
        });
        
        // Notify server via API
        fetch(`/video/api/join/${this.roomId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }
    
    async createPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.config);
        
        // Add local tracks
        this.localStream.getTracks().forEach(track => {
            this.peerConnection.addTrack(track, this.localStream);
        });
        
        // Handle incoming tracks
        this.peerConnection.ontrack = (event) => {
            console.log('Received remote track');
            this.remoteStream = event.streams[0];
            this.elements.remoteVideo.srcObject = this.remoteStream;
            this.elements.videoPlaceholder.style.display = 'none';
            this.startCallTimer();
            this.updateStatus('connected', 'Connected');
        };
        
        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.socket.emit('ice_candidate', {
                    room_id: this.roomId,
                    candidate: event.candidate,
                    sender_id: this.userId
                });
            }
        };
        
        // Handle connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            const state = this.peerConnection.connectionState;
            console.log('Connection state:', state);
            
            switch (state) {
                case 'connected':
                    this.updateStatus('connected', 'Connected');
                    break;
                case 'disconnected':
                    this.updateStatus('disconnected', 'Connection lost');
                    break;
                case 'failed':
                    this.updateStatus('disconnected', 'Connection failed');
                    this.attemptReconnect();
                    break;
            }
        };
        
        // Handle ICE connection state
        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('ICE state:', this.peerConnection.iceConnectionState);
        };
    }
    
    async createAndSendOffer() {
        try {
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this.socket.emit('offer', {
                room_id: this.roomId,
                offer: offer,
                sender_id: this.userId
            });
        } catch (error) {
            console.error('Error creating offer:', error);
        }
    }
    
    async handleOffer(offer) {
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
            
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);
            
            this.socket.emit('answer', {
                room_id: this.roomId,
                answer: answer,
                sender_id: this.userId
            });
        } catch (error) {
            console.error('Error handling offer:', error);
        }
    }
    
    async handleAnswer(answer) {
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
        } catch (error) {
            console.error('Error handling answer:', error);
        }
    }
    
    async handleIceCandidate(candidate) {
        try {
            if (this.peerConnection && candidate) {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            }
        } catch (error) {
            console.error('Error adding ICE candidate:', error);
        }
    }
    
    bindControlEvents() {
        // Toggle microphone
        document.getElementById('toggleMic')?.addEventListener('click', () => {
            this.toggleAudio();
        });
        
        // Toggle camera
        document.getElementById('toggleCamera')?.addEventListener('click', () => {
            this.toggleVideo();
        });
        
        // Screen share
        document.getElementById('toggleScreenShare')?.addEventListener('click', () => {
            this.toggleScreenShare();
        });
        
        // End call
        document.getElementById('endCall')?.addEventListener('click', () => {
            this.endCall();
        });
        
        // Chat
        document.getElementById('sendMessage')?.addEventListener('click', () => {
            this.sendChatMessage();
        });
        
        this.elements.chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChatMessage();
            }
        });
        
        // Chat panel toggle
        document.getElementById('toggleChat')?.addEventListener('click', () => {
            document.getElementById('chatPanel')?.classList.toggle('open');
        });
        
        // Settings
        document.getElementById('openSettings')?.addEventListener('click', () => {
            this.openSettings();
        });
    }
    
    toggleAudio() {
        if (!this.localStream) return;
        
        this.isAudioEnabled = !this.isAudioEnabled;
        this.localStream.getAudioTracks().forEach(track => {
            track.enabled = this.isAudioEnabled;
        });
        
        const btn = document.getElementById('toggleMic');
        btn.classList.toggle('active', this.isAudioEnabled);
        btn.classList.toggle('inactive', !this.isAudioEnabled);
        btn.innerHTML = this.isAudioEnabled ? 
            '<i class="fas fa-microphone"></i>' : 
            '<i class="fas fa-microphone-slash"></i>';
        
        this.socket.emit('toggle_audio', {
            room_id: this.roomId,
            user_id: this.userId,
            audio_enabled: this.isAudioEnabled
        });
    }
    
    toggleVideo() {
        if (!this.localStream) return;
        
        this.isVideoEnabled = !this.isVideoEnabled;
        this.localStream.getVideoTracks().forEach(track => {
            track.enabled = this.isVideoEnabled;
        });
        
        const btn = document.getElementById('toggleCamera');
        btn.classList.toggle('active', this.isVideoEnabled);
        btn.classList.toggle('inactive', !this.isVideoEnabled);
        btn.innerHTML = this.isVideoEnabled ? 
            '<i class="fas fa-video"></i>' : 
            '<i class="fas fa-video-slash"></i>';
        
        this.socket.emit('toggle_video', {
            room_id: this.roomId,
            user_id: this.userId,
            video_enabled: this.isVideoEnabled
        });
    }
    
    async toggleScreenShare() {
        if (this.isScreenSharing) {
            // Stop screen sharing
            this.stopScreenShare();
        } else {
            // Start screen sharing
            await this.startScreenShare();
        }
    }
    
    async startScreenShare() {
        try {
            const screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
                audio: false
            });
            
            const screenTrack = screenStream.getVideoTracks()[0];
            
            // Replace video track
            const sender = this.peerConnection.getSenders().find(s => 
                s.track && s.track.kind === 'video'
            );
            
            if (sender) {
                await sender.replaceTrack(screenTrack);
            }
            
            this.isScreenSharing = true;
            
            const btn = document.getElementById('toggleScreenShare');
            btn.classList.add('active');
            btn.style.background = '#28a745';
            
            // Handle when user stops sharing via browser UI
            screenTrack.onended = () => {
                this.stopScreenShare();
            };
            
        } catch (error) {
            console.error('Screen share error:', error);
        }
    }
    
    async stopScreenShare() {
        try {
            const videoTrack = this.localStream.getVideoTracks()[0];
            
            const sender = this.peerConnection.getSenders().find(s => 
                s.track && s.track.kind === 'video'
            );
            
            if (sender && videoTrack) {
                await sender.replaceTrack(videoTrack);
            }
            
            this.isScreenSharing = false;
            
            const btn = document.getElementById('toggleScreenShare');
            btn.classList.remove('active');
            btn.style.background = '#6c757d';
            
        } catch (error) {
            console.error('Stop screen share error:', error);
        }
    }
    
    sendChatMessage() {
        const message = this.elements.chatInput?.value.trim();
        if (!message) return;
        
        this.socket.emit('chat_message', {
            room_id: this.roomId,
            message: message,
            sender: this.userType
        });
        
        this.addChatMessage(message, false);
        this.elements.chatInput.value = '';
    }
    
    addChatMessage(message, isReceived) {
        const container = this.elements.chatMessages;
        if (!container) return;
        
        const div = document.createElement('div');
        div.className = `chat-message ${isReceived ? 'received' : 'sent'}`;
        div.innerHTML = `
            <div class="message-bubble">
                <p>${this.escapeHtml(message)}</p>
                <span class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
        `;
        
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }
    
    async endCall() {
        if (!confirm('Are you sure you want to end this call?')) return;
        
        this.socket.emit('end_call', {
            room_id: this.roomId,
            ended_by: this.userType
        });
        
        await fetch(`/video/end/${this.roomId}`, {
            method: 'POST'
        });
        
        this.cleanup();
        this.redirectAfterCall();
    }
    
    handleUserLeft() {
        this.updateStatus('disconnected', 'Participant left');
        this.elements.remoteVideo.srcObject = null;
        this.elements.videoPlaceholder.style.display = 'flex';
    }
    
    handleCallEnded() {
        this.cleanup();
        this.redirectAfterCall();
    }
    
    handleRemoteVideoToggle(enabled) {
        const placeholder = this.elements.videoPlaceholder;
        if (placeholder) {
            placeholder.style.display = enabled ? 'none' : 'flex';
        }
    }
    
    handleRemoteAudioToggle(enabled) {
        // Could show muted indicator
        const indicator = document.getElementById('remoteMutedIndicator');
        if (indicator) {
            indicator.style.display = enabled ? 'none' : 'block';
        }
    }
    
    startCallTimer() {
        if (this.callStartTime) return;
        
        this.callStartTime = new Date();
        
        this.durationInterval = setInterval(() => {
            const elapsed = Math.floor((new Date() - this.callStartTime) / 1000);
            const hours = Math.floor(elapsed / 3600);
            const minutes = Math.floor((elapsed % 3600) / 60);
            const seconds = elapsed % 60;
            
            let display = '';
            if (hours > 0) {
                display = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            } else {
                display = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
            
            if (this.elements.callDuration) {
                this.elements.callDuration.textContent = display;
            }
        }, 1000);
    }
    
    hideWaiting() {
        if (this.elements.waitingOverlay) {
            this.elements.waitingOverlay.classList.add('hidden');
        }
    }
    
    updateStatus(status, text) {
        if (this.elements.statusIndicator) {
            this.elements.statusIndicator.className = `status-indicator status-${status}`;
        }
        if (this.elements.connectionStatus) {
            this.elements.connectionStatus.textContent = text;
        }
    }
    
    showError(message) {
        alert(message);
    }
    
    attemptReconnect() {
        console.log('Attempting to reconnect...');
        // Implement reconnection logic
    }
    
    cleanup() {
        if (this.durationInterval) {
            clearInterval(this.durationInterval);
        }
        
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        
        if (this.socket) {
            this.socket.emit('leave_room', {
                room_id: this.roomId,
                user_id: this.userId,
                user_type: this.userType
            });
        }
    }
    
    redirectAfterCall() {
        const redirectUrl = this.userType === 'doctor' ? 
            '/doctor/video-consultations' : 
            '/patient/appointments';
        window.location.href = redirectUrl;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for global use
window.VideoCallManager = VideoCallManager;