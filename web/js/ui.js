/**
 * UI Components and Utilities
 * Handles DOM manipulation, form handling, and UI state management
 */

class UIManager {
    constructor() {
        this.jobs = new Map(); // Store job data
        this.currentView = 'form'; // 'form' or 'jobs'
        this.notifications = [];
        
        // Initialize UI elements
        this.initializeElements();
        this.setupEventListeners();
    }

    /**
     * Initialize DOM element references
     */
    initializeElements() {
        // Connection status
        this.connectionStatus = document.getElementById('connectionStatus');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        
        // Forms and buttons
        this.printRequestForm = document.getElementById('printRequestForm');
        this.userRequestInput = document.getElementById('userRequest');
        this.prioritySelect = document.getElementById('priority');
        this.submitButton = document.getElementById('submitButton');
        
        // Job list
        this.jobsList = document.getElementById('jobsList');
        this.jobsContainer = document.getElementById('jobsContainer');
        this.loadMoreButton = document.getElementById('loadMoreButton');
        
        // Notifications
        this.notificationContainer = document.getElementById('notificationContainer');
        
        // View toggle
        this.formSection = document.querySelector('.form-section');
        this.jobsSection = document.querySelector('.jobs-section');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Form submission
        if (this.printRequestForm) {
            this.printRequestForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFormSubmit();
            });
        }

        // Load more jobs button
        if (this.loadMoreButton) {
            this.loadMoreButton.addEventListener('click', () => {
                this.loadMoreJobs();
            });
        }

        // Auto-resize textarea
        if (this.userRequestInput) {
            this.userRequestInput.addEventListener('input', () => {
                this.autoResizeTextarea(this.userRequestInput);
            });
        }
    }

    /**
     * Update connection status display
     */
    updateConnectionStatus(status, message = '') {
        if (!this.statusIndicator || !this.statusText) return;

        // Remove existing status classes
        this.statusIndicator.className = 'status-indicator';
        
        // Add new status class
        this.statusIndicator.classList.add(`status-${status}`);
        
        // Update text
        const statusMessages = {
            connected: 'Connected',
            connecting: 'Connecting...',
            disconnected: 'Disconnected',
            error: 'Connection Error'
        };
        
        this.statusText.textContent = message || statusMessages[status] || status;
    }

    /**
     * Handle form submission
     */
    async handleFormSubmit() {
        const userRequest = this.userRequestInput?.value?.trim();
        const priority = this.prioritySelect?.value || 'normal';

        if (!userRequest) {
            this.showNotification('Please enter a description for your 3D print request', 'error');
            return;
        }

        try {
            // Disable form during submission
            this.setFormLoading(true);

            // Submit request via API
            const result = await window.app.api.submitPrintRequest(userRequest, priority);
            
            // Show success notification
            this.showNotification(
                `Print job created successfully! Job ID: ${result.job_id}`,
                'success'
            );

            // Reset form
            this.printRequestForm.reset();
            
            // Add job to tracking
            this.addJobToList(result);
            
            // Subscribe to job updates
            if (window.app.ws.isConnected()) {
                window.app.ws.subscribeToJob(result.job_id);
            }

        } catch (error) {
            console.error('Error submitting print request:', error);
            this.showNotification(
                `Failed to submit print request: ${error.message}`,
                'error'
            );
        } finally {
            this.setFormLoading(false);
        }
    }

    /**
     * Set form loading state
     */
    setFormLoading(loading) {
        if (!this.submitButton) return;

        this.submitButton.disabled = loading;
        this.submitButton.textContent = loading ? 'Submitting...' : 'Submit Print Request';
        
        if (this.userRequestInput) {
            this.userRequestInput.disabled = loading;
        }
        if (this.prioritySelect) {
            this.prioritySelect.disabled = loading;
        }
    }

    /**
     * Add job to the jobs list
     */
    addJobToList(jobData) {
        if (!this.jobsContainer) return;

        this.jobs.set(jobData.job_id, jobData);
        
        const jobElement = this.createJobElement(jobData);
        this.jobsContainer.insertBefore(jobElement, this.jobsContainer.firstChild);
        
        // Show jobs section if hidden
        if (this.jobsSection) {
            this.jobsSection.classList.add('has-jobs');
        }
    }

    /**
     * Create job list element
     */
    createJobElement(jobData) {
        const jobElement = document.createElement('div');
        jobElement.className = 'job-card';
        jobElement.id = `job-${jobData.job_id}`;
        
        jobElement.innerHTML = `
            <div class="job-header">
                <div class="job-id">Job #${jobData.job_id}</div>
                <div class="job-status status-${jobData.status?.toLowerCase() || 'pending'}">
                    ${jobData.status || 'Pending'}
                </div>
            </div>
            <div class="job-description">
                ${this.escapeHtml(jobData.user_request || 'No description')}
            </div>
            <div class="job-meta">
                <span class="job-priority">Priority: ${jobData.priority || 'Normal'}</span>
                <span class="job-created">Created: ${this.formatDate(jobData.created_at)}</span>
            </div>
            <div class="job-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${jobData.progress || 0}%"></div>
                </div>
                <div class="progress-text">${jobData.progress || 0}%</div>
            </div>
            <div class="job-actions">
                <button class="btn btn-secondary btn-sm" onclick="window.app.ui.viewJobDetails('${jobData.job_id}')">
                    View Details
                </button>
                <button class="btn btn-danger btn-sm" onclick="window.app.ui.cancelJob('${jobData.job_id}')">
                    Cancel
                </button>
            </div>
        `;
        
        return jobElement;
    }

    /**
     * Update job in the list
     */
    updateJob(jobData) {
        this.jobs.set(jobData.job_id, { ...this.jobs.get(jobData.job_id), ...jobData });
        
        const jobElement = document.getElementById(`job-${jobData.job_id}`);
        if (!jobElement) {
            this.addJobToList(jobData);
            return;
        }

        // Update status
        const statusElement = jobElement.querySelector('.job-status');
        if (statusElement && jobData.status) {
            statusElement.className = `job-status status-${jobData.status.toLowerCase()}`;
            statusElement.textContent = jobData.status;
        }

        // Update progress
        const progressFill = jobElement.querySelector('.progress-fill');
        const progressText = jobElement.querySelector('.progress-text');
        if (progressFill && progressText && jobData.progress !== undefined) {
            progressFill.style.width = `${jobData.progress}%`;
            progressText.textContent = `${jobData.progress}%`;
        }
    }

    /**
     * Load more jobs from API
     */
    async loadMoreJobs() {
        try {
            const skip = this.jobs.size;
            const workflows = await window.app.api.getWorkflows(skip, 20);
            
            workflows.workflows.forEach(job => {
                if (!this.jobs.has(job.job_id)) {
                    this.addJobToList(job);
                }
            });

            // Hide load more button if no more jobs
            if (workflows.workflows.length < 20) {
                this.loadMoreButton.style.display = 'none';
            }

        } catch (error) {
            console.error('Error loading more jobs:', error);
            this.showNotification('Failed to load more jobs', 'error');
        }
    }

    /**
     * View job details (placeholder)
     */
    viewJobDetails(jobId) {
        const job = this.jobs.get(jobId);
        if (job) {
            // For now, just show an alert. In a real app, this would open a modal or new page
            alert(`Job Details:\n\nID: ${job.job_id}\nStatus: ${job.status}\nRequest: ${job.user_request}`);
        }
    }

    /**
     * Cancel a job
     */
    async cancelJob(jobId) {
        if (!confirm('Are you sure you want to cancel this job?')) {
            return;
        }

        try {
            await window.app.api.cancelWorkflow(jobId);
            this.showNotification('Job cancelled successfully', 'success');
            
            // Update job status
            this.updateJob({ job_id: jobId, status: 'cancelled' });
            
        } catch (error) {
            console.error('Error cancelling job:', error);
            this.showNotification(`Failed to cancel job: ${error.message}`, 'error');
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${this.escapeHtml(message)}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        if (this.notificationContainer) {
            this.notificationContainer.appendChild(notification);
        } else {
            // Fallback: add to body
            document.body.appendChild(notification);
        }

        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, duration);

        this.notifications.push(notification);
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (error) {
            return dateString;
        }
    }

    /**
     * Clear all notifications
     */
    clearNotifications() {
        this.notifications.forEach(notification => {
            if (notification.parentElement) {
                notification.remove();
            }
        });
        this.notifications = [];
    }
}

// Export for use in other modules
window.UIManager = UIManager;
