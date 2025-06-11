/**
 * Main Application Module
 * Coordinates all modules and handles application lifecycle
 */

class App {
    constructor() {
        this.api = null;
        this.ws = null;
        this.ui = null;
        this.config = {
            apiBaseURL: 'http://localhost:8000',
            wsURL: 'ws://localhost:8000/ws/progress',
            autoReconnect: true,
            heartbeatInterval: 30000
        };
        
        this.isInitialized = false;
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            console.log('Initializing AI 3D Print System...');

            // Initialize API client
            this.api = new APIClient(this.config.apiBaseURL);
            
            // Initialize UI manager
            this.ui = new UIManager();
            
            // Initialize WebSocket manager
            this.ws = new WebSocketManager(this.config.wsURL);
            
            // Setup WebSocket event handlers
            this.setupWebSocketHandlers();
            
            // Connect to WebSocket
            await this.ws.connect();
            
            // Check API health
            await this.checkAPIHealth();
            
            // Load initial data
            await this.loadInitialData();
            
            // Setup periodic health checks
            this.setupHealthChecks();
            
            this.isInitialized = true;
            console.log('Application initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.ui?.showNotification(
                'Failed to initialize application. Please refresh the page.',
                'error'
            );
        }
    }

    /**
     * Setup WebSocket event handlers
     */
    setupWebSocketHandlers() {
        this.ws.onConnect = () => {
            console.log('WebSocket connected');
            this.ui.updateConnectionStatus('connected');
            
            // Subscribe to all active jobs
            this.subscribeToActiveJobs();
        };

        this.ws.onDisconnect = (event) => {
            console.log('WebSocket disconnected');
            this.ui.updateConnectionStatus('disconnected');
        };

        this.ws.onError = (error) => {
            console.error('WebSocket error:', error);
            this.ui.updateConnectionStatus('error');
        };

        this.ws.onMessage = (data) => {
            this.handleWebSocketMessage(data);
        };
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleWebSocketMessage(data) {
        console.log('WebSocket message received:', data);

        switch (data.type) {
            case 'job_update':
                this.handleJobUpdate(data);
                break;
                
            case 'workflow_progress':
                this.handleWorkflowProgress(data);
                break;
                
            case 'error':
                this.handleWebSocketError(data);
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    /**
     * Handle job status updates
     */
    handleJobUpdate(data) {
        if (data.job_id) {
            this.ui.updateJob({
                job_id: data.job_id,
                status: data.status,
                progress: data.progress,
                message: data.message,
                updated_at: data.timestamp || new Date().toISOString()
            });

            // Show notification for important status changes
            if (data.status === 'completed') {
                this.ui.showNotification(
                    `Job #${data.job_id} completed successfully!`,
                    'success'
                );
            } else if (data.status === 'failed') {
                this.ui.showNotification(
                    `Job #${data.job_id} failed: ${data.message || 'Unknown error'}`,
                    'error'
                );
            }
        }
    }

    /**
     * Handle workflow progress updates
     */
    handleWorkflowProgress(data) {
        if (data.job_id) {
            this.ui.updateJob({
                job_id: data.job_id,
                progress: data.progress,
                current_step: data.current_step,
                message: data.message
            });
        }
    }

    /**
     * Handle WebSocket errors
     */
    handleWebSocketError(data) {
        console.error('WebSocket error message:', data);
        this.ui.showNotification(
            `Connection error: ${data.message || 'Unknown error'}`,
            'error'
        );
    }

    /**
     * Check API health and update connection status
     */
    async checkAPIHealth() {
        try {
            const health = await this.api.getHealth();
            console.log('API Health:', health);
            
            if (health.status === 'healthy') {
                this.ui.updateConnectionStatus('connected');
            } else {
                this.ui.updateConnectionStatus('error', 'API not healthy');
            }
            
        } catch (error) {
            console.error('API health check failed:', error);
            this.ui.updateConnectionStatus('error', 'API unavailable');
        }
    }

    /**
     * Load initial data (recent jobs)
     */
    async loadInitialData() {
        try {
            const workflows = await this.api.getWorkflows(0, 10);
            
            workflows.workflows.forEach(job => {
                this.ui.addJobToList(job);
            });
            
            console.log(`Loaded ${workflows.workflows.length} initial jobs`);
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.ui.showNotification(
                'Failed to load recent jobs',
                'warning'
            );
        }
    }

    /**
     * Subscribe to all active jobs for real-time updates
     */
    subscribeToActiveJobs() {
        this.ui.jobs.forEach((job, jobId) => {
            if (job.status && !['completed', 'failed', 'cancelled'].includes(job.status.toLowerCase())) {
                this.ws.subscribeToJob(jobId);
            }
        });
    }

    /**
     * Setup periodic health checks
     */
    setupHealthChecks() {
        // Check API health every 30 seconds
        setInterval(async () => {
            if (!this.ws.isConnected()) {
                await this.checkAPIHealth();
            }
        }, 30000);
    }

    /**
     * Cleanup when page is closed
     */
    destroy() {
        if (this.ws) {
            this.ws.disconnect();
        }
        
        console.log('Application destroyed');
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    // Create global app instance
    window.app = new App();
    
    // Initialize application
    await window.app.init();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        window.app.destroy();
    });
});

// Handle page visibility changes (reconnect when tab becomes visible)
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.app && window.app.ws) {
        // Reconnect WebSocket if disconnected
        if (!window.app.ws.isConnected()) {
            setTimeout(() => {
                window.app.ws.connect();
            }, 1000);
        }
    }
});
