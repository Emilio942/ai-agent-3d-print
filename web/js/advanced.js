/**
 * Advanced Features JavaScript for AI Agent 3D Print System
 * Handles batch processing, templates, and print history
 */

class AdvancedFeatures {
    constructor() {
        this.currentTab = 'batch';
        this.batchRequests = [''];
        this.templates = {};
        this.history = {};
        this.selectedTemplate = null;
        
        this.init();
    }
    
    init() {
        this.loadTemplates();
        this.loadHistory();
        this.setupEventListeners();
        this.initializeTabs();
    }
    
    initializeTabs() {
        // Setup tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // Show initial tab
        this.switchTab('batch');
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        this.currentTab = tabName;
        
        // Load data for the current tab
        if (tabName === 'templates' && Object.keys(this.templates).length === 0) {
            this.loadTemplates();
        } else if (tabName === 'history') {
            this.loadHistory();
        }
    }
    
    setupEventListeners() {
        // Batch processing
        const addRequestBtn = document.getElementById('addRequestBtn');
        const submitBatchBtn = document.getElementById('submitBatchBtn');
        
        if (addRequestBtn) {
            addRequestBtn.addEventListener('click', () => this.addBatchRequest());
        }
        
        if (submitBatchBtn) {
            submitBatchBtn.addEventListener('click', () => this.submitBatch());
        }
        
        // Template printing
        const printTemplateBtn = document.getElementById('printTemplateBtn');
        if (printTemplateBtn) {
            printTemplateBtn.addEventListener('click', () => this.printFromTemplate());
        }
        
        // Quick examples
        const quickExamplesBtn = document.getElementById('quickExamplesBtn');
        if (quickExamplesBtn) {
            quickExamplesBtn.addEventListener('click', () => this.loadQuickExamples());
        }
    }
    
    // Batch Processing Methods
    addBatchRequest() {
        this.batchRequests.push('');
        this.renderBatchRequests();
    }
    
    removeBatchRequest(index) {
        if (this.batchRequests.length > 1) {
            this.batchRequests.splice(index, 1);
            this.renderBatchRequests();
        }
    }
    
    updateBatchRequest(index, value) {
        this.batchRequests[index] = value;
    }
    
    renderBatchRequests() {
        const container = document.getElementById('batchRequests');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.batchRequests.forEach((request, index) => {
            const requestDiv = document.createElement('div');
            requestDiv.className = 'batch-request-input';
            
            requestDiv.innerHTML = `
                <input 
                    type="text" 
                    value="${request}" 
                    placeholder="Describe what you want to 3D print..."
                    onchange="advancedFeatures.updateBatchRequest(${index}, this.value)"
                >
                ${this.batchRequests.length > 1 ? `
                    <button 
                        type="button" 
                        class="remove-request-btn"
                        onclick="advancedFeatures.removeBatchRequest(${index})"
                    >
                        ✕
                    </button>
                ` : ''}
            `;
            
            container.appendChild(requestDiv);
        });
    }
    
    async submitBatch() {
        const validRequests = this.batchRequests.filter(req => req.trim());
        
        if (validRequests.length === 0) {
            this.showMessage('Please add at least one print request.', 'error');
            return;
        }
        
        try {
            this.setLoading(true);
            
            const response = await fetch('/api/advanced/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    requests: validRequests,
                    settings: {
                        submitted_at: new Date().toISOString(),
                        source: 'web_interface'
                    }
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showMessage(`Batch processing started! Processing ${result.total_requests} requests.`, 'success');
                this.showBatchProgress(result);
            } else {
                throw new Error('Failed to submit batch request');
            }
        } catch (error) {
            console.error('Batch submission error:', error);
            this.showMessage('Failed to submit batch request. Please try again.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    showBatchProgress(batchInfo) {
        const progressContainer = document.getElementById('batchProgress');
        if (!progressContainer) return;
        
        progressContainer.style.display = 'block';
        progressContainer.innerHTML = `
            <h4>Batch Processing in Progress</h4>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 10%"></div>
            </div>
            <div class="progress-text">
                Processing ${batchInfo.total_requests} requests...
            </div>
        `;
        
        // Simulate progress (in real implementation, this would be WebSocket updates)
        let progress = 10;
        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                this.showMessage('Batch processing completed!', 'success');
                this.loadHistory(); // Refresh history
            }
            
            const progressFill = progressContainer.querySelector('.progress-fill');
            const progressText = progressContainer.querySelector('.progress-text');
            
            if (progressFill) {
                progressFill.style.width = `${progress}%`;
            }
            
            if (progressText) {
                if (progress < 100) {
                    progressText.textContent = `Processing... ${Math.round(progress)}%`;
                } else {
                    progressText.textContent = 'Batch processing completed!';
                }
            }
        }, 2000);
    }
    
    // Template Methods
    async loadTemplates() {
        try {
            const response = await fetch('/api/advanced/templates');
            if (response.ok) {
                this.templates = await response.json();
                this.renderTemplates();
            }
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    }
    
    renderTemplates() {
        const container = document.getElementById('templateCategories');
        if (!container) return;
        
        container.innerHTML = '';
        
        Object.entries(this.templates).forEach(([category, items]) => {
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'template-category';
            
            categoryDiv.innerHTML = `
                <h4>${category.replace('_', ' ').toUpperCase()}</h4>
                <div class="template-items">
                    ${items.map(item => `
                        <div 
                            class="template-item" 
                            onclick="advancedFeatures.selectTemplate('${category}', '${item}')"
                            data-category="${category}"
                            data-name="${item}"
                        >
                            ${item.replace('_', ' ')}
                        </div>
                    `).join('')}
                </div>
            `;
            
            container.appendChild(categoryDiv);
        });
    }
    
    selectTemplate(category, name) {
        // Remove previous selection
        document.querySelectorAll('.template-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Add selection to clicked item
        const item = document.querySelector(`[data-category="${category}"][data-name="${name}"]`);
        if (item) {
            item.classList.add('selected');
        }
        
        this.selectedTemplate = { category, name };
        
        // Enable print button
        const printBtn = document.getElementById('printTemplateBtn');
        if (printBtn) {
            printBtn.disabled = false;
            printBtn.textContent = `Print ${name.replace('_', ' ')}`;
        }
    }
    
    async printFromTemplate() {
        if (!this.selectedTemplate) {
            this.showMessage('Please select a template first.', 'error');
            return;
        }
        
        try {
            this.setLoading(true);
            
            const response = await fetch('/api/advanced/template-print', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    category: this.selectedTemplate.category,
                    name: this.selectedTemplate.name,
                    customizations: {}
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showMessage(`Template print started: ${result.template}`, 'success');
            } else {
                throw new Error('Failed to start template print');
            }
        } catch (error) {
            console.error('Template print error:', error);
            this.showMessage('Failed to start template print. Please try again.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    // History Methods
    async loadHistory() {
        try {
            const response = await fetch('/api/advanced/print-history?limit=10');
            if (response.ok) {
                this.history = await response.json();
                this.renderHistory();
            }
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }
    
    renderHistory() {
        // Render stats
        const statsContainer = document.getElementById('historyStats');
        if (statsContainer && this.history) {
            statsContainer.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${this.history.total_prints}</div>
                    <div class="stat-label">Total Prints</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${Math.round(this.history.success_rate)}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${this.history.popular_requests.length}</div>
                    <div class="stat-label">Popular Items</div>
                </div>
            `;
        }
        
        // Render recent prints
        const recentContainer = document.getElementById('recentPrints');
        if (recentContainer && this.history.recent_prints) {
            recentContainer.innerHTML = `
                <h4>Recent Prints</h4>
                ${this.history.recent_prints.map(print => `
                    <div class="print-item">
                        <span class="print-request">${print.request}</span>
                        <span class="print-status ${print.success ? 'success' : 'failed'}">
                            ${print.success ? 'Success' : 'Failed'}
                        </span>
                    </div>
                `).join('')}
            `;
        }
    }
    
    // Quick Examples
    async loadQuickExamples() {
        try {
            const response = await fetch('/api/advanced/quick-examples');
            if (response.ok) {
                const examples = await response.json();
                this.showQuickExamples(examples);
            }
        } catch (error) {
            console.error('Failed to load quick examples:', error);
        }
    }
    
    showQuickExamples(examples) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Quick Example Batches</h3>
                <div class="example-categories">
                    ${Object.entries(examples).map(([category, requests]) => `
                        <div class="example-category">
                            <h4>${category.replace('_', ' ').toUpperCase()}</h4>
                            <button 
                                onclick="advancedFeatures.loadExampleBatch('${category}', ${JSON.stringify(requests).replace(/"/g, '&quot;')})"
                                class="load-example-btn"
                            >
                                Load Example (${requests.length} items)
                            </button>
                        </div>
                    `).join('')}
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="close-modal-btn">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    loadExampleBatch(category, requests) {
        this.batchRequests = [...requests];
        this.renderBatchRequests();
        this.switchTab('batch');
        
        // Close modal
        const modal = document.querySelector('.modal');
        if (modal) {
            modal.remove();
        }
        
        this.showMessage(`Loaded ${requests.length} example requests for ${category.replace('_', ' ')}`, 'info');
    }
    
    // Utility Methods
    setLoading(loading) {
        const submitBtn = document.getElementById('submitBatchBtn');
        const printBtn = document.getElementById('printTemplateBtn');
        
        if (submitBtn) {
            submitBtn.disabled = loading;
            submitBtn.textContent = loading ? 'Processing...' : 'Submit Batch';
        }
        
        if (printBtn && !loading) {
            printBtn.disabled = !this.selectedTemplate;
        }
    }
    
    showMessage(text, type = 'info') {
        const messageContainer = document.getElementById('messageContainer') || this.createMessageContainer();
        
        const message = document.createElement('div');
        message.className = `message ${type}`;
        message.textContent = text;
        
        messageContainer.appendChild(message);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 5000);
    }
    
    createMessageContainer() {
        const container = document.createElement('div');
        container.id = 'messageContainer';
        container.style.position = 'fixed';
        container.style.top = '1rem';
        container.style.right = '1rem';
        container.style.zIndex = '1000';
        container.style.maxWidth = '400px';
        
        document.body.appendChild(container);
        return container;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.advancedFeatures = new AdvancedFeatures();
});

// Add modal styles
const modalStyles = `
<style>
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    max-width: 500px;
    width: 90%;
    max-height: 70vh;
    overflow-y: auto;
}

.example-categories {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin: 1rem 0;
}

.example-category {
    padding: 1rem;
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
}

.example-category h4 {
    margin: 0 0 0.5rem 0;
    color: #374151;
}

.load-example-btn {
    background: #3b82f6;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.875rem;
}

.load-example-btn:hover {
    background: #2563eb;
}

.close-modal-btn {
    background: #6b7280;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    margin-top: 1rem;
}

.close-modal-btn:hover {
    background: #4b5563;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', modalStyles);
