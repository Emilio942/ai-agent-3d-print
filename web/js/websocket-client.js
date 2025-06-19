/**
 * Real-time WebSocket Client for AI Agent 3D Print System
 * Enhanced with mobile support, offline handling, and real-time updates
 */

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.heartbeatInterval = null;
        this.subscriptions = new Set();
        this.messageHandlers = new Map();
        this.isOnline = navigator.onLine;
        
        this.setupEventHandlers();
        this.connect();
    }
    
    setupEventHandlers() {
        // Network status monitoring
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.showConnectionStatus('online', 'Connected');
            this.connect();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showConnectionStatus('offline', 'Offline');
        });
        
        // Page visibility for mobile optimization
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseConnection();
            } else {
                this.resumeConnection();
            }
        });
    }
    
    connect() {
        if (!this.isOnline) {
            this.showConnectionStatus('offline', 'Offline');
            return;
        }
        
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/connect`;
            
            this.ws = new WebSocket(wsUrl);
            this.setupWebSocketHandlers();
            
            this.showConnectionStatus('connecting', 'Connecting...');
            
        } catch (error) {
            console.error('❌ WebSocket connection failed:', error);
            this.handleConnectionError();
        }
    }
    
    setupWebSocketHandlers() {
        this.ws.onopen = () => {
            console.log('🔌 WebSocket connected');
            this.reconnectAttempts = 0;
            this.showConnectionStatus('connected', 'Connected');
            this.startHeartbeat();
            
            // Resubscribe to topics
            this.subscriptions.forEach(topic => {
                this.subscribe(topic);
            });
            
            // Trigger connection event
            this.emit('connected');
        };
        
        this.ws.onclose = (event) => {
            console.log('🔌 WebSocket disconnected:', event.code);
            this.stopHeartbeat();
            this.showConnectionStatus('disconnected', 'Disconnected');
            
            if (!event.wasClean && this.isOnline) {
                this.scheduleReconnect();
            }
            
            this.emit('disconnected', { code: event.code });
        };
        
        this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.handleConnectionError();
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('❌ Failed to parse WebSocket message:', error);
            }
        };
    }
    
    handleMessage(message) {
        const { type, data, timestamp } = message;
        
        // Handle system messages
        switch (type) {
            case 'heartbeat':
                // Heartbeat response - no action needed
                break;
                
            case 'user_connect':
                console.log('✅ Successfully connected to server');
                break;
                
            case 'workflow_progress':
                this.handleWorkflowProgress(data);
                break;
                
            case 'print_started':
            case 'print_progress':
            case 'print_completed':
            case 'print_error':
                this.handlePrintUpdate(type, data);
                break;
                
            case 'batch_progress':
                this.handleBatchProgress(data);
                break;
                
            case 'system_alert':
            case 'performance_warning':
                this.handleSystemAlert(data);
                break;
                
            case 'real_time_metrics':
                this.handleMetricsUpdate(data);
                break;
                
            case 'analytics_update':
                this.handleAnalyticsUpdate(data);
                break;
                
            default:
                console.log('📨 Received message:', type, data);
        }
        
        // Trigger message handlers
        if (this.messageHandlers.has(type)) {
            this.messageHandlers.get(type).forEach(handler => {
                try {
                    handler(data, timestamp);
                } catch (error) {
                    console.error('❌ Message handler error:', error);
                }
            });
        }
    }
    
    handleWorkflowProgress(data) {
        const { job_id, stage, progress, details } = data;
        
        // Update progress UI
        this.updateProgressBar(job_id, progress, stage);
        
        // Show stage-specific updates
        this.showStageUpdate(stage, details);
        
        // Mobile haptic feedback
        if ('vibrate' in navigator && progress === 100) {
            navigator.vibrate([200, 100, 200]);
        }
    }
    
    handlePrintUpdate(type, data) {
        const { job_id, status, details } = data;
        
        switch (type) {
            case 'print_started':
                this.showNotification('Print Started', `Job ${job_id} has begun printing`);
                this.updateJobStatus(job_id, 'printing');
                break;
                
            case 'print_progress':
                this.updatePrintProgress(job_id, details.progress || 0);
                break;
                
            case 'print_completed':
                this.showNotification('Print Complete!', `Job ${job_id} finished successfully`);
                this.updateJobStatus(job_id, 'completed');
                if ('vibrate' in navigator) {
                    navigator.vibrate([500, 200, 500, 200, 500]);
                }
                break;
                
            case 'print_error':
                this.showNotification('Print Error', `Job ${job_id}: ${details.error || 'Unknown error'}`);
                this.updateJobStatus(job_id, 'error');
                break;
        }
    }
    
    handleBatchProgress(data) {
        const { batch_id, progress } = data;
        this.updateBatchProgress(batch_id, progress);
        
        if (progress.completed === progress.total_requests) {
            this.showNotification('Batch Complete', `All ${progress.total_requests} jobs finished`);
        }
    }
    
    handleSystemAlert(data) {
        const { level, message, details } = data;
        
        switch (level) {
            case 'critical':
                this.showAlert('Critical System Alert', message, 'error');
                break;
            case 'warning':
                this.showAlert('System Warning', message, 'warning');
                break;
            case 'info':
                this.showAlert('System Info', message, 'info');
                break;
        }
    }
    
    handleMetricsUpdate(data) {
        this.updateSystemMetrics(data);
    }
    
    handleAnalyticsUpdate(data) {
        this.updateAnalyticsDashboard(data);
    }
    
    // UI Update Methods
    updateProgressBar(jobId, progress, stage) {
        const progressBar = document.querySelector(`[data-job-id="${jobId}"] .progress-bar`);
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
        }
        
        const stageText = document.querySelector(`[data-job-id="${jobId}"] .current-stage`);
        if (stageText) {
            stageText.textContent = stage;
        }
    }
    
    updateJobStatus(jobId, status) {
        const statusElements = document.querySelectorAll(`[data-job-id="${jobId}"] .status`);
        statusElements.forEach(el => {
            el.textContent = status;
            el.className = `status status-${status}`;
        });
    }
    
    updatePrintProgress(jobId, progress) {
        const progressElements = document.querySelectorAll(`[data-job-id="${jobId}"] .print-progress`);
        progressElements.forEach(el => {
            el.textContent = `${Math.round(progress)}%`;
        });
    }
    
    updateBatchProgress(batchId, progress) {
        const batchElement = document.querySelector(`[data-batch-id="${batchId}"]`);
        if (batchElement) {
            const progressText = batchElement.querySelector('.batch-progress');
            if (progressText) {
                progressText.textContent = `${progress.completed}/${progress.total_requests} completed`;
            }
        }
    }
    
    updateSystemMetrics(metrics) {
        // Update CPU usage
        const cpuElement = document.getElementById('cpu-usage');
        if (cpuElement) {
            cpuElement.textContent = `${Math.round(metrics.cpu_usage)}%`;
        }
        
        // Update memory usage
        const memoryElement = document.getElementById('memory-usage');
        if (memoryElement) {
            memoryElement.textContent = `${Math.round(metrics.memory_usage)}%`;
        }
        
        // Update active connections
        const connectionsElement = document.getElementById('active-connections');
        if (connectionsElement) {
            connectionsElement.textContent = metrics.active_connections || 0;
        }
    }
    
    updateAnalyticsDashboard(data) {
        // Update analytics charts and data
        if (window.analytics && typeof window.analytics.updateCharts === 'function') {
            window.analytics.updateCharts(data);
        }
    }
    
    showStageUpdate(stage, details) {
        const notification = document.createElement('div');
        notification.className = 'stage-notification';
        notification.innerHTML = `
            <div class="stage-icon">⚙️</div>
            <div class="stage-text">
                <strong>${stage}</strong>
                ${details.message || ''}
            </div>
        `;
        
        // Add to notification area
        const notificationArea = document.getElementById('notifications');
        if (notificationArea) {
            notificationArea.appendChild(notification);
            
            // Auto-remove after 3 seconds
            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    }
    
    showNotification(title, message, type = 'info') {
        // Try native notifications first
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '/web/assets/icons/icon-192.png',
                badge: '/web/assets/icons/badge.png',
                tag: 'ai-3d-print'
            });
        }
        
        // Fallback to in-app notification
        this.showInAppNotification(title, message, type);
    }
    
    showInAppNotification(title, message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-icon">${this.getNotificationIcon(type)}</div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close">&times;</button>
        `;
        
        // Add click to close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        // Add to notification container
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            document.body.appendChild(container);
        }
        
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    showAlert(title, message, type) {
        this.showNotification(title, message, type);
    }
    
    getNotificationIcon(type) {
        const icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        };
        return icons[type] || icons.info;
    }
    
    showConnectionStatus(status, text) {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (statusIndicator) {
            statusIndicator.className = `status-indicator status-${status}`;
        }
        
        if (statusText) {
            statusText.textContent = text;
        }
    }
    
    // WebSocket control methods
    send(type, data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                type,
                data,
                timestamp: new Date().toISOString()
            };
            this.ws.send(JSON.stringify(message));
            return true;
        }
        return false;
    }
    
    subscribe(topic) {
        this.subscriptions.add(topic);
        this.send('subscribe', { topic });
    }
    
    unsubscribe(topic) {
        this.subscriptions.delete(topic);
        this.send('unsubscribe', { topic });
    }
    
    on(messageType, handler) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, new Set());
        }
        this.messageHandlers.get(messageType).add(handler);
    }
    
    off(messageType, handler) {
        if (this.messageHandlers.has(messageType)) {
            this.messageHandlers.get(messageType).delete(handler);
        }
    }
    
    emit(eventType, data = null) {
        const event = new CustomEvent(`ws:${eventType}`, { detail: data });
        window.dispatchEvent(event);
    }
    
    // Connection management
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            this.send('heartbeat', { timestamp: Date.now() });
        }, 30000); // Every 30 seconds
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            console.log('❌ Max reconnection attempts reached');
            this.showConnectionStatus('failed', 'Connection failed');
        }
    }
    
    handleConnectionError() {
        this.showConnectionStatus('error', 'Connection error');
        this.scheduleReconnect();
    }
    
    pauseConnection() {
        // Reduce heartbeat frequency when page is hidden (mobile optimization)
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = setInterval(() => {
                this.send('heartbeat', { timestamp: Date.now() });
            }, 60000); // Every 60 seconds when hidden
        }
    }
    
    resumeConnection() {
        // Resume normal heartbeat when page is visible
        this.stopHeartbeat();
        this.startHeartbeat();
    }
    
    disconnect() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    // Utility methods
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
    
    getConnectionState() {
        if (!this.ws) return 'disconnected';
        
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING: return 'connecting';
            case WebSocket.OPEN: return 'connected';
            case WebSocket.CLOSING: return 'closing';
            case WebSocket.CLOSED: return 'disconnected';
            default: return 'unknown';
        }
    }
}

// Export for use in other modules
window.WebSocketClient = WebSocketClient;
