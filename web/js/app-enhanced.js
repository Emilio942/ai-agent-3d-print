/**
 * Enhanced Main Application JavaScript
 * AI Agent 3D Print System - Mobile PWA Enhanced
 */

class AI3DPrintApp {
    constructor() {
        this.wsClient = null;
        this.isOnline = navigator.onLine;
        this.installPrompt = null;
        this.isInstalled = false;
        this.jobs = new Map();
        this.batches = new Map();
        this.notificationPermission = 'default';
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing AI 3D Print System...');
        
        // Check if running as PWA
        this.checkPWAStatus();
        
        // Initialize core systems
        this.setupEventListeners();
        this.setupServiceWorker();
        this.setupNotifications();
        this.setupWebSocket();
        this.setupPWAInstallPrompt();
        this.setupOfflineHandling();
        
        // Initialize UI
        this.initializeUI();
        
        // Load initial data
        await this.loadInitialData();
        
        console.log('✅ AI 3D Print System initialized');
    }
    
    checkPWAStatus() {
        // Check if app is installed
        this.isInstalled = window.matchMedia('(display-mode: standalone)').matches ||
                          window.navigator.standalone ||
                          document.referrer.includes('android-app://');
        
        if (this.isInstalled) {
            console.log('📱 Running as installed PWA');
            document.body.classList.add('pwa-installed');
        }
    }
    
    setupEventListeners() {
        // Network status
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.handleOnlineStatus();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.handleOfflineStatus();
        });
        
        // PWA install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.installPrompt = e;
            this.showPWAInstallPrompt();
        });
        
        // PWA installed
        window.addEventListener('appinstalled', () => {
            this.isInstalled = true;
            this.hidePWAInstallPrompt();
            this.showNotification('App Installed!', 'AI 3D Print System is now installed on your device', 'success');
        });
        
        // Form submissions
        const printForm = document.getElementById('printRequestForm');
        if (printForm) {
            printForm.addEventListener('submit', (e) => this.handlePrintRequest(e));
        }
        
        // Visibility changes for mobile optimization
        document.addEventListener('visibilitychange', () => {
            this.handleVisibilityChange();
        });
        
        // Touch gestures for mobile
        this.setupTouchGestures();
    }
    
    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/web/sw.js')
                .then(registration => {
                    console.log('✅ Service Worker registered:', registration.scope);
                    
                    // Listen for updates
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                this.showUpdateAvailable();
                            }
                        });
                    });
                })
                .catch(error => {
                    console.error('❌ Service Worker registration failed:', error);
                });
        }
    }
    
    setupNotifications() {
        if ('Notification' in window) {
            this.notificationPermission = Notification.permission;
            
            if (this.notificationPermission === 'default') {
                // Request permission after user interaction
                setTimeout(() => {
                    this.requestNotificationPermission();
                }, 3000);
            }
        }
    }
    
    async requestNotificationPermission() {
        try {
            const permission = await Notification.requestPermission();
            this.notificationPermission = permission;
            
            if (permission === 'granted') {
                this.showNotification('Notifications Enabled!', 'You will receive updates about your print jobs', 'success');
            }
        } catch (error) {
            console.error('❌ Notification permission request failed:', error);
        }
    }
    
    setupWebSocket() {
        if (typeof WebSocketClient !== 'undefined') {
            this.wsClient = new WebSocketClient();
            
            // Subscribe to relevant topics when connected
            this.wsClient.on('connected', () => {
                this.wsClient.subscribe('workflow_updates');
                this.wsClient.subscribe('print_updates');
                this.wsClient.subscribe('batch_updates');
                this.wsClient.subscribe('metrics_updates');
            });
        }
    }
    
    showNotification(title, message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${title} - ${message}`);
    }
    
    // Placeholder methods for functionality
    setupPWAInstallPrompt() {}
    setupOfflineHandling() {}
    setupTouchGestures() {}
    initializeUI() {}
    async loadInitialData() {}
    handleOnlineStatus() {}
    handleOfflineStatus() {}
    handleVisibilityChange() {}
    async handlePrintRequest(e) {}
    updateConnectionStatus() {}
    showUpdateAvailable() {}
}\n    \n    setupNotifications() {\n        if ('Notification' in window) {\n            this.notificationPermission = Notification.permission;\n            \n            if (this.notificationPermission === 'default') {\n                // Request permission after user interaction\n                setTimeout(() => {\n                    this.requestNotificationPermission();\n                }, 3000);\n            }\n        }\n    }\n    \n    async requestNotificationPermission() {\n        try {\n            const permission = await Notification.requestPermission();\n            this.notificationPermission = permission;\n            \n            if (permission === 'granted') {\n                this.showNotification('Notifications Enabled!', 'You\\'ll receive updates about your print jobs', 'success');\n            }\n        } catch (error) {\n            console.error('❌ Notification permission request failed:', error);\n        }\n    }\n    \n    setupWebSocket() {\n        this.wsClient = new WebSocketClient();\n        \n        // Subscribe to relevant topics\n        this.wsClient.on('connected', () => {\n            this.wsClient.subscribe('workflow_updates');\n            this.wsClient.subscribe('print_updates');\n            this.wsClient.subscribe('batch_updates');\n            this.wsClient.subscribe('metrics_updates');\n        });\n        \n        // Handle workflow progress\n        this.wsClient.on('workflow_progress', (data) => {\n            this.updateJobProgress(data.job_id, data.progress, data.stage);\n        });\n        \n        // Handle print status updates\n        this.wsClient.on('print_started', (data) => {\n            this.handlePrintStarted(data);\n        });\n        \n        this.wsClient.on('print_completed', (data) => {\n            this.handlePrintCompleted(data);\n        });\n        \n        this.wsClient.on('print_error', (data) => {\n            this.handlePrintError(data);\n        });\n        \n        // Handle metrics updates\n        this.wsClient.on('real_time_metrics', (data) => {\n            this.updateMetricsDisplay(data);\n        });\n    }\n    \n    setupPWAInstallPrompt() {\n        // Create install prompt element\n        const promptHTML = `\n            <div id=\"pwa-install-prompt\" class=\"pwa-install-prompt\">\n                <div class=\"pwa-install-icon\">📱</div>\n                <div class=\"pwa-install-content\">\n                    <div class=\"pwa-install-title\">Install AI 3D Print</div>\n                    <div class=\"pwa-install-description\">Get the app for easier access and offline features</div>\n                </div>\n                <div class=\"pwa-install-actions\">\n                    <button class=\"pwa-install-btn\" id=\"pwa-dismiss\">Not Now</button>\n                    <button class=\"pwa-install-btn primary\" id=\"pwa-install\">Install</button>\n                </div>\n            </div>\n        `;\n        \n        document.body.insertAdjacentHTML('beforeend', promptHTML);\n        \n        // Add event listeners\n        document.getElementById('pwa-install').addEventListener('click', () => {\n            this.installPWA();\n        });\n        \n        document.getElementById('pwa-dismiss').addEventListener('click', () => {\n            this.hidePWAInstallPrompt();\n        });\n    }\n    \n    showPWAInstallPrompt() {\n        if (this.isInstalled) return;\n        \n        const prompt = document.getElementById('pwa-install-prompt');\n        if (prompt) {\n            setTimeout(() => {\n                prompt.classList.add('show');\n            }, 5000); // Show after 5 seconds\n        }\n    }\n    \n    hidePWAInstallPrompt() {\n        const prompt = document.getElementById('pwa-install-prompt');\n        if (prompt) {\n            prompt.classList.remove('show');\n        }\n    }\n    \n    async installPWA() {\n        if (this.installPrompt) {\n            this.installPrompt.prompt();\n            const { outcome } = await this.installPrompt.userChoice;\n            \n            if (outcome === 'accepted') {\n                console.log('✅ PWA installation accepted');\n            } else {\n                console.log('❌ PWA installation declined');\n            }\n            \n            this.installPrompt = null;\n            this.hidePWAInstallPrompt();\n        }\n    }\n    \n    setupOfflineHandling() {\n        // Setup background sync for offline actions\n        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {\n            console.log('✅ Background sync available');\n        }\n        \n        // Handle offline form submissions\n        this.setupOfflineQueue();\n    }\n    \n    setupOfflineQueue() {\n        this.offlineQueue = [];\n        \n        // Process queue when online\n        window.addEventListener('online', () => {\n            this.processOfflineQueue();\n        });\n    }\n    \n    async processOfflineQueue() {\n        while (this.offlineQueue.length > 0) {\n            const action = this.offlineQueue.shift();\n            try {\n                await this.executeAction(action);\n                console.log('✅ Offline action processed:', action.type);\n            } catch (error) {\n                console.error('❌ Failed to process offline action:', error);\n                // Re-queue if failed\n                this.offlineQueue.unshift(action);\n                break;\n            }\n        }\n    }\n    \n    setupTouchGestures() {\n        let startY = 0;\n        let startX = 0;\n        \n        document.addEventListener('touchstart', (e) => {\n            startY = e.touches[0].clientY;\n            startX = e.touches[0].clientX;\n        }, { passive: true });\n        \n        document.addEventListener('touchend', (e) => {\n            const endY = e.changedTouches[0].clientY;\n            const endX = e.changedTouches[0].clientX;\n            const diffY = startY - endY;\n            const diffX = startX - endX;\n            \n            // Pull to refresh gesture\n            if (diffY < -100 && Math.abs(diffX) < 50 && window.scrollY === 0) {\n                this.handlePullToRefresh();\n            }\n        }, { passive: true });\n    }\n    \n    handlePullToRefresh() {\n        console.log('🔄 Pull to refresh triggered');\n        this.showNotification('Refreshing...', 'Updating data', 'info');\n        this.loadInitialData();\n    }\n    \n    initializeUI() {\n        // Initialize progress indicators\n        this.updateConnectionStatus();\n        \n        // Setup quick actions\n        this.setupQuickActions();\n        \n        // Initialize metrics display\n        this.initializeMetricsDisplay();\n        \n        // Setup search functionality\n        this.setupSearch();\n    }\n    \n    setupQuickActions() {\n        // Handle URL parameters for quick actions\n        const urlParams = new URLSearchParams(window.location.search);\n        const action = urlParams.get('action');\n        \n        switch (action) {\n            case 'quick-print':\n                this.focusPrintForm();\n                break;\n            case 'history':\n                this.showHistoryTab();\n                break;\n            case 'status':\n                this.showStatusTab();\n                break;\n        }\n    }\n    \n    focusPrintForm() {\n        const textarea = document.getElementById('userRequest');\n        if (textarea) {\n            textarea.focus();\n            textarea.placeholder = 'Quick print: What would you like to 3D print?';\n        }\n    }\n    \n    initializeMetricsDisplay() {\n        // Create metrics container if it doesn't exist\n        const container = document.getElementById('metrics-container');\n        if (!container) {\n            const metricsHTML = `\n                <div id=\"metrics-container\" class=\"metrics-container\">\n                    <div class=\"metric-card\">\n                        <div class=\"metric-header\">\n                            <div class=\"metric-title\">CPU Usage</div>\n                            <div class=\"metric-icon cpu\">🖥️</div>\n                        </div>\n                        <div class=\"metric-value\" id=\"cpu-usage\">--</div>\n                        <div class=\"metric-description\">System processing power</div>\n                    </div>\n                    <div class=\"metric-card\">\n                        <div class=\"metric-header\">\n                            <div class=\"metric-title\">Memory Usage</div>\n                            <div class=\"metric-icon memory\">💾</div>\n                        </div>\n                        <div class=\"metric-value\" id=\"memory-usage\">--</div>\n                        <div class=\"metric-description\">RAM utilization</div>\n                    </div>\n                    <div class=\"metric-card\">\n                        <div class=\"metric-header\">\n                            <div class=\"metric-title\">Active Connections</div>\n                            <div class=\"metric-icon connections\">🔗</div>\n                        </div>\n                        <div class=\"metric-value\" id=\"active-connections\">--</div>\n                        <div class=\"metric-description\">Connected clients</div>\n                    </div>\n                </div>\n            `;\n            \n            const main = document.querySelector('.main .container');\n            if (main) {\n                main.insertAdjacentHTML('beforeend', metricsHTML);\n            }\n        }\n    }\n    \n    setupSearch() {\n        // Add search functionality for jobs and history\n        const searchInput = document.getElementById('search-input');\n        if (searchInput) {\n            searchInput.addEventListener('input', (e) => {\n                this.filterContent(e.target.value);\n            });\n        }\n    }\n    \n    async loadInitialData() {\n        try {\n            // Load system health\n            await this.loadSystemHealth();\n            \n            // Load recent jobs\n            await this.loadRecentJobs();\n            \n            // Load metrics\n            await this.loadMetrics();\n            \n        } catch (error) {\n            console.error('❌ Failed to load initial data:', error);\n            if (!this.isOnline) {\n                this.showNotification('Offline Mode', 'Some features may be limited', 'warning');\n            }\n        }\n    }\n    \n    async loadSystemHealth() {\n        try {\n            const response = await fetch('/api/health');\n            const data = await response.json();\n            \n            if (data.status === 'healthy') {\n                this.updateConnectionStatus('healthy', 'System Healthy');\n            } else {\n                this.updateConnectionStatus('warning', 'System Issues');\n            }\n        } catch (error) {\n            this.updateConnectionStatus('error', 'Connection Error');\n        }\n    }\n    \n    async loadRecentJobs() {\n        try {\n            const response = await fetch('/api/jobs/recent');\n            if (response.ok) {\n                const jobs = await response.json();\n                this.displayRecentJobs(jobs);\n            }\n        } catch (error) {\n            console.error('❌ Failed to load recent jobs:', error);\n        }\n    }\n    \n    async loadMetrics() {\n        try {\n            const response = await fetch('/api/metrics');\n            if (response.ok) {\n                const metrics = await response.json();\n                this.updateMetricsDisplay(metrics);\n            }\n        } catch (error) {\n            console.error('❌ Failed to load metrics:', error);\n        }\n    }\n    \n    // Event Handlers\n    async handlePrintRequest(e) {\n        e.preventDefault();\n        \n        const formData = new FormData(e.target);\n        const request = formData.get('userRequest');\n        \n        if (!request.trim()) {\n            this.showNotification('Error', 'Please enter a print request', 'error');\n            return;\n        }\n        \n        if (!this.isOnline) {\n            // Queue for offline processing\n            this.queueOfflineAction({\n                type: 'print_request',\n                data: { request },\n                timestamp: Date.now()\n            });\n            this.showNotification('Queued Offline', 'Your request will be processed when online', 'info');\n            return;\n        }\n        \n        try {\n            const submitButton = e.target.querySelector('button[type=\"submit\"]');\n            const originalText = submitButton.textContent;\n            \n            submitButton.textContent = 'Processing...';\n            submitButton.disabled = true;\n            \n            const response = await fetch('/api/print-request', {\n                method: 'POST',\n                headers: {\n                    'Content-Type': 'application/json'\n                },\n                body: JSON.stringify({ request })\n            });\n            \n            const result = await response.json();\n            \n            if (result.success) {\n                this.showNotification('Print Job Started!', `Job ID: ${result.job_id}`, 'success');\n                this.addJobToList(result);\n                e.target.reset();\n            } else {\n                this.showNotification('Error', result.error || 'Failed to start print job', 'error');\n            }\n            \n            submitButton.textContent = originalText;\n            submitButton.disabled = false;\n            \n        } catch (error) {\n            console.error('❌ Print request failed:', error);\n            this.showNotification('Error', 'Failed to submit print request', 'error');\n        }\n    }\n    \n    handleOnlineStatus() {\n        this.showNotification('Back Online!', 'Connection restored', 'success');\n        this.updateConnectionStatus('connected', 'Connected');\n        this.processOfflineQueue();\n    }\n    \n    handleOfflineStatus() {\n        this.showNotification('Gone Offline', 'Some features will be limited', 'warning');\n        this.updateConnectionStatus('offline', 'Offline');\n    }\n    \n    handleVisibilityChange() {\n        if (document.hidden) {\n            // Page hidden - reduce activity\n            console.log('📱 App backgrounded');\n        } else {\n            // Page visible - resume activity\n            console.log('📱 App foregrounded');\n            this.loadMetrics(); // Refresh data\n        }\n    }\n    \n    // Job Management\n    addJobToList(jobData) {\n        this.jobs.set(jobData.job_id, jobData);\n        this.updateJobsList();\n    }\n    \n    updateJobProgress(jobId, progress, stage) {\n        const job = this.jobs.get(jobId);\n        if (job) {\n            job.progress = progress;\n            job.stage = stage;\n            this.updateJobDisplay(job);\n        }\n    }\n    \n    updateJobDisplay(job) {\n        // Update job progress in UI\n        const jobElement = document.querySelector(`[data-job-id=\"${job.job_id}\"]`);\n        if (jobElement) {\n            const progressBar = jobElement.querySelector('.progress-bar');\n            const stageText = jobElement.querySelector('.current-stage');\n            \n            if (progressBar) {\n                progressBar.style.width = `${job.progress}%`;\n            }\n            \n            if (stageText) {\n                stageText.textContent = job.stage || 'Processing';\n            }\n        }\n    }\n    \n    // Utility Methods\n    queueOfflineAction(action) {\n        this.offlineQueue.push(action);\n        \n        // Store in localStorage for persistence\n        try {\n            localStorage.setItem('offlineQueue', JSON.stringify(this.offlineQueue));\n        } catch (error) {\n            console.error('❌ Failed to store offline queue:', error);\n        }\n    }\n    \n    showNotification(title, message, type = 'info') {\n        // Use WebSocket client's notification system\n        if (this.wsClient) {\n            this.wsClient.showNotification(title, message, type);\n        }\n    }\n    \n    updateConnectionStatus(status, text) {\n        const statusIndicator = document.getElementById('statusIndicator');\n        const statusText = document.getElementById('statusText');\n        \n        if (statusIndicator) {\n            statusIndicator.className = `status-indicator status-${status}`;\n        }\n        \n        if (statusText) {\n            statusText.textContent = text;\n        }\n    }\n    \n    updateMetricsDisplay(metrics) {\n        if (this.wsClient) {\n            this.wsClient.updateSystemMetrics(metrics);\n        }\n    }\n    \n    showUpdateAvailable() {\n        this.showNotification(\n            'Update Available',\n            'A new version is available. Refresh to update.',\n            'info'\n        );\n    }\n}\n\n// Initialize the application when DOM is loaded\nif (document.readyState === 'loading') {\n    document.addEventListener('DOMContentLoaded', () => {\n        window.app = new AI3DPrintApp();\n    });\n} else {\n    window.app = new AI3DPrintApp();\n}\n\n// Export for debugging\nwindow.AI3DPrintApp = AI3DPrintApp;
