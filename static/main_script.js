/**
 * Telekinesis - WebRTC P2P File Transfer Frontend
 * Handles all client-side interactions and WebRTC communication
 */

class TelekinesisApp {
    constructor() {
        this.isInitiator = false;
        this.connectionState = 'disconnected';
        this.pollingInterval = null;
        this.currentTransfer = null;
        
        this.initializeElements();
        this.attachEventListeners();
        this.startPolling();
        
        console.log('🚀 Telekinesis initialized');
    }
    
    initializeElements() {
        // Buttons
        this.createOfferBtn = document.getElementById('createOfferBtn');
        this.createAnswerBtn = document.getElementById('createAnswerBtn');
        this.setAnswerBtn = document.getElementById('setAnswerBtn');
        this.disconnectBtn = document.getElementById('disconnectBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.copyBtn = document.getElementById('copyBtn');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.sendFileBtn = document.getElementById('sendFileBtn');
        this.sendMessageBtn = document.getElementById('sendMessageBtn');
        
        // Inputs
        this.offerInput = document.getElementById('offerInput');
        this.answerInput = document.getElementById('answerInput');
        this.offerFileInput = document.getElementById('offerFileInput');
        this.answerFileInput = document.getElementById('answerFileInput');
        this.fileInput = document.getElementById('fileInput');
        this.messageInput = document.getElementById('messageInput');
        
        // Display elements
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.signalingData = document.getElementById('signalingData');
        this.signalingTitle = document.getElementById('signalingTitle');
        this.signalingContent = document.getElementById('signalingContent');
        this.instructionText = document.getElementById('instructionText');
        this.answerSection = document.getElementById('answerSection');
        this.connectionSection = document.getElementById('connectionSection');
        this.transferSection = document.getElementById('transferSection');
        this.receivedSection = document.getElementById('receivedSection');
        
        // File upload
        this.fileUploadArea = document.getElementById('fileUploadArea');
        this.selectedFile = document.getElementById('selectedFile');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        
        // Progress
        this.progressCard = document.getElementById('progressCard');
        this.progressTitle = document.getElementById('progressTitle');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.progressStatus = document.getElementById('progressStatus');
        
        // Chat
        this.chatMessages = document.getElementById('chatMessages');
        this.receivedFiles = document.getElementById('receivedFiles');
        
        // Overlays
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.notification = document.getElementById('notification');
    }
    
    attachEventListeners() {
        // Connection buttons
        this.createOfferBtn.addEventListener('click', () => this.createOffer());
        this.createAnswerBtn.addEventListener('click', () => this.createAnswer());
        this.setAnswerBtn.addEventListener('click', () => this.setAnswer());
        this.disconnectBtn.addEventListener('click', () => this.disconnect());
        this.resetBtn.addEventListener('click', () => this.resetUI());
        
        // Signaling actions
        this.copyBtn.addEventListener('click', () => this.copySignalingData());
        this.downloadBtn.addEventListener('click', () => this.downloadSignalingData());
        
        // File upload
        this.fileUploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileUploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.fileUploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.sendFileBtn.addEventListener('click', () => this.sendFile());
        
        // Chat
        this.sendMessageBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        // File uploads for offer/answer
        this.offerFileInput.addEventListener('change', (e) => this.handleOfferFileUpload(e));
        this.answerFileInput.addEventListener('change', (e) => this.handleAnswerFileUpload(e));
        
        // Notification close
        document.querySelector('.notification-close').addEventListener('click', () => {
            this.hideNotification();
        });
    }
    
    // API Communication
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
    
    // Connection Management
    async createOffer() {
        try {
            this.isInitiator = true;
            this.showLoading('Creating connection offer...');
            
            const result = await this.apiCall('create_offer', 'POST');
            if (result.status === 'success') {
                this.showNotification('Creating offer...', 'info');
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.hideLoading();
            this.showNotification(`Failed to create offer: ${error.message}`, 'error');
        }
    }
    
    async createAnswer() {
        try {
            const offer = this.offerInput.value.trim();
            if (!offer) {
                this.showNotification('Please paste the connection offer', 'warning');
                return;
            }
            
            this.isInitiator = false;
            this.showLoading('Creating connection answer...');
            
            const result = await this.apiCall('create_answer', 'POST', { offer });
            if (result.status === 'success') {
                this.showNotification('Creating answer...', 'info');
                this.offerInput.value = '';
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.hideLoading();
            this.showNotification(`Failed to create answer: ${error.message}`, 'error');
        }
    }
    
    async setAnswer() {
        try {
            const answer = this.answerInput.value.trim();
            if (!answer) {
                this.showNotification('Please paste the connection answer', 'warning');
                return;
            }
            
            this.showLoading('Completing connection...');
            
            const result = await this.apiCall('set_answer', 'POST', { answer });
            if (result.status === 'success') {
                this.showNotification('Completing connection...', 'info');
                this.answerInput.value = '';
                this.hideAnswerSection();
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.hideLoading();
            this.showNotification(`Failed to complete connection: ${error.message}`, 'error');
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
    
    // File Transfer
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
    
    // File upload handlers for offer/answer
    handleOfferFileUpload(e) {
        const file = e.target.files[0];
        if (file && file.type === 'text/plain') {
            const reader = new FileReader();
            reader.onload = (event) => {
                this.offerInput.value = event.target.result;
                this.showNotification('Offer file loaded successfully', 'success');
            };
            reader.readAsText(file);
        } else {
            this.showNotification('Please select a valid text file', 'warning');
        }
        e.target.value = ''; // Reset file input
    }
    
    handleAnswerFileUpload(e) {
        const file = e.target.files[0];
        if (file && file.type === 'text/plain') {
            const reader = new FileReader();
            reader.onload = (event) => {
                this.answerInput.value = event.target.result;
                this.showNotification('Answer file loaded successfully', 'success');
            };
            reader.readAsText(file);
        } else {
            this.showNotification('Please select a valid text file', 'warning');
        }
        e.target.value = ''; // Reset file input
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
    
    // Chat
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
    
    // Event Polling
    startPolling() {
        this.pollingInterval = setInterval(async () => {
            try {
                const events = await this.apiCall('get_events');
                this.handleEvents(events);
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 1000);
    }
    
    handleEvents(events) {
        // Update connection state
        if (events.connection_state !== this.connectionState) {
            this.connectionState = events.connection_state;
            this.updateConnectionState(events.connection_state, events.is_connected);
        }
        
        // Hide loading spinner when connection is established
        if (events.connection_state === 'connected' && events.is_connected) {
            this.hideLoading();
        }
        
        // Handle remote disconnections
        if (events.connection_state === 'closed' || events.connection_state === 'failed' || 
            events.connection_state === 'disconnected') {
            this.hideLoading();
            if (events.connection_state === 'closed') {
                this.showNotification('Remote peer disconnected', 'warning');
            } else if (events.connection_state === 'failed') {
                this.showNotification('Connection failed', 'error');
            }
            // Show reset button for manual UI reset
            this.showResetButton();
        }
        
        // Handle offer created
        if (events.offer) {
            this.hideLoading();
            this.showSignalingData('Connection Offer', events.offer, 
                'Copy this offer and send it to the other person. Wait for them to send you back an answer.');
            this.showAnswerSection();
        }
        
        // Handle answer created
        if (events.answer) {
            this.hideLoading();
            this.showSignalingData('Connection Answer', events.answer, 
                'Copy this answer and send it back to the person who sent you the offer.');
        }
        
        // Handle transfer progress
        if (events.progress) {
            this.updateProgress(events.progress.progress, events.progress.is_sending);
        }
        
        // Handle file received
        if (events.file_received) {
            this.hideProgressCard();
            this.addReceivedFile(events.file_received.filename, events.file_received.path);
            this.showNotification(`File received: ${events.file_received.filename}`, 'success');
        }
        
        // Handle messages
        if (events.message) {
            this.addChatMessage(events.message, 'received');
        }
        
        // Handle errors
        if (events.error) {
            this.hideLoading();
            this.hideProgressCard();
            this.showNotification(`Error: ${events.error}`, 'error');
        }
    }
    
    // UI Updates
    updateConnectionState(state, isConnected) {
        this.statusText.textContent = this.getStatusText(state);
        
        // Update status indicator
        this.statusIndicator.className = 'status-indicator';
        if (isConnected) {
            this.statusIndicator.classList.add('connected');
        } else if (state === 'connecting') {
            this.statusIndicator.classList.add('connecting');
        }
        
        // Show/hide sections based on connection state
        if (isConnected) {
            this.disconnectBtn.style.display = 'block';
            this.hideResetButton();
            this.transferSection.style.display = 'block';
            this.receivedSection.style.display = 'block';
            this.connectionSection.style.display = 'none';
        } else {
            this.disconnectBtn.style.display = 'none';
            this.transferSection.style.display = 'none';
            this.receivedSection.style.display = 'none';
            this.connectionSection.style.display = 'block';
        }
    }
    
    getStatusText(state) {
        const stateMap = {
            'disconnected': 'Disconnected',
            'connecting': 'Connecting...',
            'connected': 'Connected',
            'failed': 'Connection Failed',
            'closed': 'Connection Closed'
        };
        return stateMap[state] || state;
    }
    
    showSignalingData(title, data, instruction) {
        this.signalingTitle.textContent = title;
        this.signalingContent.value = data;
        this.instructionText.textContent = instruction;
        this.signalingData.style.display = 'block';
    }
    
    showAnswerSection() {
        this.answerSection.style.display = 'block';
    }
    
    hideAnswerSection() {
        this.answerSection.style.display = 'none';
    }
    
    showProgressCard(title, isSending) {
        this.progressTitle.textContent = title;
        this.progressCard.style.display = 'block';
        this.updateProgress(0, isSending);
    }
    
    hideProgressCard() {
        this.progressCard.style.display = 'none';
        this.currentTransfer = null;
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
        // Remove empty state if present
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
                <div class="details">Saved to Downloads • ${new Date().toLocaleTimeString()}</div>
            </div>
            <button class="btn btn-outline" onclick="this.openFileLocation('${this.escapeHtml(filepath)}')">
                <i class="fas fa-folder-open"></i> Open Folder
            </button>
        `;
        
        this.receivedFiles.insertBefore(fileItem, this.receivedFiles.firstChild);
    }
    
    openFileLocation(filepath) {
        // This would typically open the file location in the OS file manager
        this.showNotification('File saved to Downloads folder', 'info');
    }
    
    // Utility Functions
    async copySignalingData() {
        try {
            await navigator.clipboard.writeText(this.signalingContent.value);
            this.showNotification('Copied to clipboard!', 'success');
        } catch (error) {
            // Fallback for older browsers
            this.signalingContent.select();
            document.execCommand('copy');
            this.showNotification('Copied to clipboard!', 'success');
        }
    }
    
    downloadSignalingData() {
        const data = this.signalingContent.value;
        const filename = this.isInitiator ? 'connection_offer.txt' : 'connection_answer.txt';
        
        const blob = new Blob([data], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification(`Downloaded ${filename}`, 'success');
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
    
    // Loading and Notifications
    showLoading(text) {
        document.getElementById('loadingText').textContent = text;
        this.loadingOverlay.style.display = 'flex';
    }
    
    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }
    
    showResetButton() {
        this.resetBtn.style.display = 'block';
    }
    
    hideResetButton() {
        this.resetBtn.style.display = 'none';
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
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideNotification();
        }, 5000);
    }
    
    hideNotification() {
        this.notification.style.display = 'none';
    }
    
    resetUI() {
        // Reset connection state
        this.connectionState = 'disconnected';
        this.isInitiator = false;
        
        // Hide sections
        this.transferSection.style.display = 'none';
        this.receivedSection.style.display = 'none';
        this.connectionSection.style.display = 'block';
        this.signalingData.style.display = 'none';
        this.answerSection.style.display = 'none';
        this.disconnectBtn.style.display = 'none';
        this.hideResetButton();
        
        // Reset forms
        this.offerInput.value = '';
        this.answerInput.value = '';
        this.messageInput.value = '';
        this.fileInput.value = '';
        
        // Reset file selection
        document.querySelector('.upload-placeholder').style.display = 'block';
        this.selectedFile.style.display = 'none';
        this.selectedFileData = null;
        
        // Clear chat (except system message)
        this.chatMessages.innerHTML = `
            <div class="chat-message system">
                <i class="fas fa-info-circle"></i>
                <span>Connect with a peer to start transferring files and messages.</span>
            </div>
        `;
        
        // Reset progress
        this.hideProgressCard();
        
        // Update status
        this.updateConnectionState('disconnected', false);
    }
    
    // Cleanup
    destroy() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.telekinesisApp = new TelekinesisApp();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.telekinesisApp) {
        window.telekinesisApp.destroy();
    }
});
