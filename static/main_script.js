class TelekinesisApp {
    constructor() {
        this.connectionState = 'disconnected';
        this.eventSource = null;
        this.currentRoom = null;
        this.userName = null;
        this.isRoomCreator = false;
        
        this.initializeElements();
        this.attachEventListeners();
        this.startEventStream();
        
        console.log('🚀 Telekinesis initialized');
    }
    
    initializeElements() {
        this.userNameInput = document.getElementById('userNameInput');
        this.roomNameInput = document.getElementById('roomNameInput');
        this.createRoomBtn = document.getElementById('createRoomBtn');
        this.joinRoomBtn = document.getElementById('joinRoomBtn');
        this.copyRoomNameBtn = document.getElementById('copyRoomNameBtn');
        
        this.disconnectBtn = document.getElementById('disconnectBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.sendFileBtn = document.getElementById('sendFileBtn');
        this.sendMessageBtn = document.getElementById('sendMessageBtn');
        
        this.fileInput = document.getElementById('fileInput');
        this.messageInput = document.getElementById('messageInput');
        
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.connectionSection = document.getElementById('connectionSection');
        this.transferSection = document.getElementById('transferSection');
        this.chatSection = document.getElementById('chatSection');
        this.roomStatus = document.getElementById('roomStatus');
        this.currentRoomName = document.getElementById('currentRoomName');
        this.connectionStatus = document.getElementById('connectionStatus');
        this.shareableRoomName = document.getElementById('shareableRoomName');
        this.roomInstructions = document.getElementById('roomInstructions');
        
        this.fileUploadArea = document.getElementById('fileUploadArea');
        this.selectedFile = document.getElementById('selectedFile');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        
        this.progressCard = document.getElementById('progressCard');
        this.progressTitle = document.getElementById('progressTitle');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.progressStatus = document.getElementById('progressStatus');
        
        this.chatMessages = document.getElementById('chatMessages');
        this.receivedFiles = document.getElementById('receivedFiles');
        
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.notification = document.getElementById('notification');
    }
    
    attachEventListeners() {
        this.createRoomBtn.addEventListener('click', () => this.createRoom());
        this.joinRoomBtn.addEventListener('click', () => this.joinRoom());
        this.copyRoomNameBtn.addEventListener('click', () => this.copyRoomName());
        this.disconnectBtn.addEventListener('click', () => this.disconnect());
        this.resetBtn.addEventListener('click', () => this.resetUI());
        
        this.fileUploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileUploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.fileUploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.sendFileBtn.addEventListener('click', () => this.sendFile());
        
        this.sendMessageBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        document.querySelector('.notification-close').addEventListener('click', () => {
            this.hideNotification();
        });
        
        this.roomNameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.createRoom();
        });
    }
    
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(`/api/${endpoint}`, options);
            return await response.json();
        } catch (error) {
            console.error(`API call failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    async apiCallFormData(endpoint, formData) {
        try {
            const response = await fetch(`/api/${endpoint}`, {
                method: 'POST',
                body: formData
            });
            return await response.json();
        } catch (error) {
            console.error(`API call failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    async createRoom() {
        try {
            const userName = this.userNameInput.value.trim();
            const roomName = this.roomNameInput.value.trim();
            
            if (!userName) {
                this.showNotification('Please enter your name', 'warning');
                return;
            }
            
            if (!roomName) {
                this.showNotification('Please enter a room name', 'warning');
                return;
            }
            
            this.userName = userName;
            this.currentRoom = roomName;
            this.isRoomCreator = true;
            
            this.showLoading('Creating room...');
            
            const result = await this.apiCall('create_room', 'POST', {
                room_name: roomName,
                user_name: userName
            });
            
            if (result.status === 'success') {
                this.showRoomStatus(roomName, 'Waiting for peer...');
                this.showNotification(`Room "${roomName}" created successfully`, 'success');
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.hideLoading();
            this.showNotification(`Failed to create room: ${error.message}`, 'error');
        }
    }
    
    async joinRoom() {
        try {
            const userName = this.userNameInput.value.trim();
            const roomName = this.roomNameInput.value.trim();
            
            if (!userName) {
                this.showNotification('Please enter your name', 'warning');
                return;
            }
            
            if (!roomName) {
                this.showNotification('Please enter a room name', 'warning');
                return;
            }
            
            this.userName = userName;
            this.currentRoom = roomName;
            this.isRoomCreator = false;
            
            this.showLoading('Joining room...');
            
            const result = await this.apiCall('join_room', 'POST', {
                room_name: roomName,
                user_name: userName
            });
            
            if (result.status === 'success') {
                this.showRoomStatus(roomName, 'Connecting...');
                this.showNotification(`Joined room "${roomName}"`, 'success');
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.hideLoading();
            this.showNotification(`Failed to join room: ${error.message}`, 'error');
        }
    }
    
    showRoomStatus(roomName, status) {
        this.currentRoomName.textContent = roomName;
        this.connectionStatus.textContent = status;
        this.shareableRoomName.textContent = roomName;
        
        if (this.isRoomCreator) {
            this.roomInstructions.style.display = 'block';
        } else {
            this.roomInstructions.style.display = 'none';
        }
        
        this.roomStatus.style.display = 'block';
        this.hideLoading();
    }
    
    async copyRoomName() {
        try {
            await navigator.clipboard.writeText(this.currentRoom);
            this.showNotification('Room name copied to clipboard!', 'success');
        } catch (error) {
            this.showNotification('Failed to copy room name', 'error');
        }
    }
    
    async disconnect() {
        try {
            const result = await this.apiCall('disconnect', 'POST');
            if (result.status === 'success') {
                this.showNotification('Disconnected', 'info');
                this.resetUI();
            }
        } catch (error) {
            this.showNotification(`Failed to disconnect: ${error.message}`, 'error');
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        this.fileUploadArea.style.borderColor = 'var(--primary-color)';
        this.fileUploadArea.style.backgroundColor = 'var(--bg-tertiary)';
    }
    
    handleDrop(e) {
        e.preventDefault();
        this.fileUploadArea.style.borderColor = '';
        this.fileUploadArea.style.backgroundColor = '';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.selectFile(files[0]);
        }
    }
    
    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.selectFile(files[0]);
        }
    }
    
    selectFile(file) {
        this.selectedFileData = file;
        this.fileName.textContent = file.name;
        this.fileSize.textContent = this.formatFileSize(file.size);
        
        document.querySelector('.upload-placeholder').style.display = 'none';
        this.selectedFile.style.display = 'flex';
    }
    
    async sendFile() {
        try {
            if (!this.selectedFileData) {
                this.showNotification('Please select a file first', 'warning');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', this.selectedFileData);
            
            this.showProgressCard(`Sending ${this.selectedFileData.name}`, true);
            
            const result = await this.apiCallFormData('send_file', formData);
            if (result.status === 'success') {
                this.showNotification(`Sending ${this.selectedFileData.name}`, 'info');
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.hideProgressCard();
            this.showNotification(`Failed to send file: ${error.message}`, 'error');
        }
    }
    
    async sendMessage() {
        try {
            const message = this.messageInput.value.trim();
            if (!message) return;
            
            const result = await this.apiCall('send_message', 'POST', { message });
            if (result.status === 'success') {
                this.addChatMessage(message, 'sent');
                this.messageInput.value = '';
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.showNotification(`Failed to send message: ${error.message}`, 'error');
        }
    }
    
    addChatMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}`;
        
        const icon = type === 'sent' ? 'fa-paper-plane' : 'fa-comment';
        messageDiv.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${this.escapeHtml(message)}</span>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    startEventStream() {
        this.eventSource = new EventSource('/api/events');
        
        this.eventSource.onmessage = (event) => {
            try {
                const eventData = JSON.parse(event.data);
                console.log('📡 SSE Event received:', eventData);
                
                if (eventData.type === 'heartbeat') {
                    return;
                }
                
                this.handleEvent(eventData);
                
            } catch (error) {
                console.error('Error parsing SSE event:', error, event.data);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            this.eventSource.close();
            
            setTimeout(() => {
                console.log('Reconnecting SSE...');
                this.startEventStream();
            }, 3000);
        };
        
        this.eventSource.onopen = () => {
            console.log('✅ SSE connection established');
        };
    }
    
    handleEvent(event) {
        const { type, data } = event;
        
        switch (type) {
            case 'offer_created':
                this.connectionStatus.textContent = 'Room ready - waiting for peer';
                break;
                
            case 'answer_created':
                this.connectionStatus.textContent = 'Connecting...';
                break;
                
            case 'connection_state_changed':
                this.updateConnectionState(data);
                break;
                
            case 'file_received':
                this.hideProgressCard();
                this.addReceivedFile(data.filename, data.path);
                this.showNotification(`File received: ${data.filename}`, 'success');
                break;
                
            case 'message_received':
                this.addChatMessage(data, 'received');
                break;
                
            case 'progress':
                this.updateProgress(data.progress, data.is_sending);
                break;
                
            case 'error':
                this.hideLoading();
                this.hideProgressCard();
                this.showNotification(`Error: ${data}`, 'error');
                break;
        }
    }
    
    updateConnectionState(state) {
        this.connectionState = state;
        
        const statusMap = {
            'disconnected': 'Disconnected',
            'connecting': 'Connecting...',
            'connected': 'Connected',
            'failed': 'Connection Failed',
            'closed': 'Connection Closed'
        };
        
        const statusText = statusMap[state] || state;
        this.statusText.textContent = statusText;
        this.connectionStatus.textContent = statusText;
        
        this.statusIndicator.className = 'status-indicator';
        if (state === 'connected') {
            this.statusIndicator.classList.add('connected');
            this.disconnectBtn.style.display = 'block';
            this.resetBtn.style.display = 'none';
            this.transferSection.style.display = 'block';
            this.chatSection.style.display = 'block';
            this.connectionSection.style.display = 'none';
            this.hideLoading();
        } else if (state === 'connecting') {
            this.statusIndicator.classList.add('connecting');
        } else if (state === 'failed' || state === 'closed') {
            this.disconnectBtn.style.display = 'none';
            this.resetBtn.style.display = 'block';
            if (state === 'failed') {
                this.showNotification('Connection failed', 'error');
            } else if (state === 'closed') {
                this.showNotification('Connection closed by peer', 'warning');
            }
        }
    }
    
    showProgressCard(title, isSending) {
        this.progressTitle.textContent = title;
        this.progressCard.style.display = 'block';
        this.updateProgress(0, isSending);
    }
    
    hideProgressCard() {
        this.progressCard.style.display = 'none';
    }
    
    updateProgress(progress, isSending) {
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = `${Math.round(progress)}%`;
        this.progressStatus.textContent = isSending ? 'Sending...' : 'Receiving...';
        
        if (progress >= 100) {
            setTimeout(() => {
                this.hideProgressCard();
            }, 2000);
        }
    }
    
    addReceivedFile(filename, filepath) {
        const emptyState = this.receivedFiles.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <i class="fas fa-file-download"></i>
            <div class="file-info">
                <div class="name">${this.escapeHtml(filename)}</div>
                <div class="details">Saved to Downloads/Telekinesis • ${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        this.receivedFiles.insertBefore(fileItem, this.receivedFiles.firstChild);
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showLoading(text) {
        document.getElementById('loadingText').textContent = text;
        this.loadingOverlay.style.display = 'flex';
    }
    
    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }
    
    showNotification(message, type = 'info') {
        const iconMap = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle',
            'info': 'fa-info-circle'
        };
        
        const icon = document.querySelector('.notification-icon');
        icon.className = `notification-icon fas ${iconMap[type]}`;
        
        document.querySelector('.notification-text').textContent = message;
        this.notification.className = `notification ${type}`;
        this.notification.style.display = 'block';
        
        setTimeout(() => {
            this.hideNotification();
        }, 5000);
    }
    
    hideNotification() {
        this.notification.style.display = 'none';
    }
    
    resetUI() {
        this.connectionState = 'disconnected';
        this.currentRoom = null;
        this.userName = null;
        this.isRoomCreator = false;
        
        this.transferSection.style.display = 'none';
        this.chatSection.style.display = 'none';
        this.connectionSection.style.display = 'block';
        this.roomStatus.style.display = 'none';
        this.disconnectBtn.style.display = 'none';
        this.resetBtn.style.display = 'none';
        
        this.userNameInput.value = '';
        this.roomNameInput.value = '';
        this.messageInput.value = '';
        this.fileInput.value = '';
        
        document.querySelector('.upload-placeholder').style.display = 'block';
        this.selectedFile.style.display = 'none';
        this.selectedFileData = null;
        
        this.chatMessages.innerHTML = `
            <div class="chat-message system">
                <i class="fas fa-info-circle"></i>
                <span>Connected! You can now send files and messages.</span>
            </div>
        `;
        
        this.hideProgressCard();
        this.updateConnectionState('disconnected');
    }
    
    destroy() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.telekinesisApp = new TelekinesisApp();
});

window.addEventListener('beforeunload', () => {
    if (window.telekinesisApp) {
        window.telekinesisApp.destroy();
    }
});