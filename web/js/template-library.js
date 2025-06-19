/**
 * Template Library Interface for AI Agent 3D Print System
 * Handles template browsing, searching, customization, and printing
 */

class TemplateLibrary {
    constructor() {
        this.apiUrl = '/api/advanced';
        this.templates = [];
        this.selectedTemplate = null;
        this.currentFilters = {
            category: '',
            difficulty: '',
            search: ''
        };
        
        this.init();
    }
    
    init() {
        this.initElements();
        this.bindEvents();
        this.loadTemplates();
        this.loadCategories();
    }
    
    initElements() {
        this.categoryFilter = document.getElementById('categoryFilter');
        this.difficultyFilter = document.getElementById('difficultyFilter');
        this.searchFilter = document.getElementById('searchFilter');
        this.searchBtn = document.getElementById('searchTemplatesBtn');
        this.templateGrid = document.getElementById('templateGrid');
        this.templateDetails = document.getElementById('templateDetails');
    }
    
    bindEvents() {
        this.searchBtn?.addEventListener('click', () => this.searchTemplates());
        this.categoryFilter?.addEventListener('change', () => this.applyFilters());
        this.difficultyFilter?.addEventListener('change', () => this.applyFilters());
        
        this.searchFilter?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchTemplates();
            }
        });
        
        this.searchFilter?.addEventListener('input', () => {
            // Debounced search
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => this.applyFilters(), 500);
        });
    }
    
    async loadTemplates() {
        try {
            this.showLoading();
            
            const response = await fetch(`${this.apiUrl}/templates`);
            const result = await response.json();
            
            if (result.success) {
                this.templates = result.templates;
                this.displayTemplates(this.templates);
            } else {
                this.showError('Failed to load templates');
            }
        } catch (error) {
            console.error('Error loading templates:', error);
            this.showError('Error loading templates');
        }
    }
    
    async loadCategories() {
        try {
            const response = await fetch(`${this.apiUrl}/templates/categories`);
            const result = await response.json();
            
            if (result.success && this.categoryFilter) {
                // Clear existing options except "All Categories"
                while (this.categoryFilter.children.length > 1) {
                    this.categoryFilter.removeChild(this.categoryFilter.lastChild);
                }
                
                // Add category options
                result.categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category.value;
                    option.textContent = category.display_name;
                    this.categoryFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }
    
    async searchTemplates() {
        try {
            this.showLoading();
            
            const searchData = {
                category: this.categoryFilter?.value || null,
                difficulty: this.difficultyFilter?.value || null,
                search_term: this.searchFilter?.value || null
            };
            
            // Remove null values
            Object.keys(searchData).forEach(key => {
                if (searchData[key] === null || searchData[key] === '') {
                    delete searchData[key];
                }
            });
            
            const response = await fetch(`${this.apiUrl}/templates/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(searchData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.templates = result.templates;
                this.displayTemplates(this.templates);
            } else {
                this.showError('Failed to search templates');
            }
        } catch (error) {
            console.error('Error searching templates:', error);
            this.showError('Error searching templates');
        }
    }
    
    applyFilters() {
        // Update current filters
        this.currentFilters.category = this.categoryFilter?.value || '';
        this.currentFilters.difficulty = this.difficultyFilter?.value || '';
        this.currentFilters.search = this.searchFilter?.value || '';
        
        // Search with current filters
        this.searchTemplates();
    }
    
    displayTemplates(templates) {
        if (!this.templateGrid) return;
        
        if (!templates || templates.length === 0) {
            this.templateGrid.innerHTML = `
                <div class="no-templates">
                    <div class="no-templates-icon">📦</div>
                    <div class="no-templates-message">No templates found</div>
                    <div class="no-templates-suggestion">Try adjusting your search filters</div>
                </div>
            `;
            return;
        }
        
        const templatesHtml = templates.map(template => `
            <div class="template-card" data-template-id="${template.id}">
                <div class="template-image">
                    ${template.preview_image ? 
                        `<img src="${template.preview_image}" alt="${template.name}" loading="lazy">` :
                        `<div class="template-placeholder">🔧</div>`
                    }
                </div>
                <div class="template-info">
                    <h3 class="template-name">${template.name}</h3>
                    <p class="template-description">${template.description}</p>
                    <div class="template-meta">
                        <span class="template-category">${this.formatCategory(template.category)}</span>
                        <span class="template-difficulty ${template.difficulty}">${this.formatDifficulty(template.difficulty)}</span>
                    </div>
                    <div class="template-stats">
                        <span class="template-rating">⭐ ${template.rating?.toFixed(1) || 'N/A'}</span>
                        <span class="template-prints">🖨️ ${template.print_count || 0}</span>
                    </div>
                    <div class="template-actions">
                        <button class="btn btn-secondary template-preview-btn" data-template-id="${template.id}">
                            Preview
                        </button>
                        <button class="btn btn-primary template-select-btn" data-template-id="${template.id}">
                            Customize
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        this.templateGrid.innerHTML = templatesHtml;
        
        // Bind events for template cards
        this.bindTemplateEvents();
    }
    
    bindTemplateEvents() {
        // Preview buttons
        const previewBtns = document.querySelectorAll('.template-preview-btn');
        previewBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const templateId = e.target.getAttribute('data-template-id');
                this.previewTemplate(templateId);
            });
        });
        
        // Customize buttons
        const selectBtns = document.querySelectorAll('.template-select-btn');
        selectBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const templateId = e.target.getAttribute('data-template-id');
                this.selectTemplate(templateId);
            });
        });
        
        // Template cards
        const templateCards = document.querySelectorAll('.template-card');
        templateCards.forEach(card => {
            card.addEventListener('click', (e) => {
                // Only select if not clicking on buttons
                if (!e.target.closest('.template-actions')) {
                    const templateId = card.getAttribute('data-template-id');
                    this.selectTemplate(templateId);
                }
            });
        });
    }
    
    async previewTemplate(templateId) {
        try {
            const response = await fetch(`${this.apiUrl}/templates/${templateId}/preview`);
            const result = await response.json();
            
            if (result.success) {
                this.showPreview(result.preview);
            } else {
                this.showNotification('Failed to generate preview', 'error');
            }
        } catch (error) {
            console.error('Error previewing template:', error);
            this.showNotification('Error generating preview', 'error');
        }
    }
    
    async selectTemplate(templateId) {
        try {
            const response = await fetch(`${this.apiUrl}/templates/${templateId}`);
            const result = await response.json();
            
            if (result.success) {
                this.selectedTemplate = result.template;
                this.showTemplateDetails(this.selectedTemplate);
            } else {
                this.showNotification('Failed to load template details', 'error');
            }
        } catch (error) {
            console.error('Error selecting template:', error);
            this.showNotification('Error loading template', 'error');
        }
    }
    
    showTemplateDetails(template) {
        if (!this.templateDetails) return;
        
        const detailsHtml = `
            <div class="template-details-content">
                <div class="template-header">
                    <button class="btn btn-secondary back-btn" id="backToGridBtn">
                        ← Back to Templates
                    </button>
                    <h2>${template.name}</h2>
                </div>
                
                <div class="template-details-body">
                    <div class="template-preview-section">
                        ${template.preview_image ? 
                            `<img src="${template.preview_image}" alt="${template.name}" class="template-detail-image">` :
                            `<div class="template-detail-placeholder">🔧</div>`
                        }
                    </div>
                    
                    <div class="template-info-section">
                        <p class="template-detail-description">${template.description}</p>
                        
                        <div class="template-metadata">
                            <div class="metadata-item">
                                <strong>Category:</strong> ${this.formatCategory(template.category)}
                            </div>
                            <div class="metadata-item">
                                <strong>Difficulty:</strong> ${this.formatDifficulty(template.difficulty)}
                            </div>
                            <div class="metadata-item">
                                <strong>Print Time:</strong> ${template.estimated_print_time || 'N/A'}
                            </div>
                            <div class="metadata-item">
                                <strong>Material:</strong> ${template.recommended_material || 'PLA'}
                            </div>
                        </div>
                        
                        <div class="template-parameters">
                            <h3>Customization Options</h3>
                            <div class="parameters-form" id="parametersForm">
                                ${this.renderParameters(template.parameters || [])}
                            </div>
                        </div>
                        
                        <div class="template-actions-section">
                            <button class="btn btn-secondary" id="previewCustomizedBtn">
                                Preview Customized
                            </button>
                            <button class="btn btn-primary" id="printTemplateBtn">
                                Print Template
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.templateDetails.innerHTML = detailsHtml;
        this.templateDetails.style.display = 'block';
        
        // Bind detail events
        this.bindDetailEvents();
    }
    
    renderParameters(parameters) {
        if (!parameters || parameters.length === 0) {
            return '<p class="no-parameters">This template has no customizable parameters.</p>';
        }
        
        return parameters.map(param => {
            switch (param.parameter_type) {
                case 'number':
                    return `
                        <div class="parameter-group">
                            <label for="param_${param.name}" class="parameter-label">
                                ${param.display_name}:
                            </label>
                            <input type="number" 
                                   id="param_${param.name}" 
                                   name="${param.name}"
                                   value="${param.default_value || param.min_value || 0}"
                                   min="${param.min_value || ''}"
                                   max="${param.max_value || ''}"
                                   step="${param.step || 0.1}"
                                   class="parameter-input">
                            <span class="parameter-unit">${param.unit || ''}</span>
                        </div>
                    `;
                case 'text':
                    return `
                        <div class="parameter-group">
                            <label for="param_${param.name}" class="parameter-label">
                                ${param.display_name}:
                            </label>
                            <input type="text" 
                                   id="param_${param.name}" 
                                   name="${param.name}"
                                   value="${param.default_value || ''}"
                                   class="parameter-input">
                        </div>
                    `;
                case 'choice':
                    return `
                        <div class="parameter-group">
                            <label for="param_${param.name}" class="parameter-label">
                                ${param.display_name}:
                            </label>
                            <select id="param_${param.name}" name="${param.name}" class="parameter-input">
                                ${(param.choices || []).map(choice => `
                                    <option value="${choice}" ${choice === param.default_value ? 'selected' : ''}>
                                        ${choice}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                    `;
                case 'boolean':
                    return `
                        <div class="parameter-group">
                            <label class="parameter-checkbox">
                                <input type="checkbox" 
                                       id="param_${param.name}" 
                                       name="${param.name}"
                                       ${param.default_value ? 'checked' : ''}>
                                ${param.display_name}
                            </label>
                        </div>
                    `;
                default:
                    return '';
            }
        }).join('');
    }
    
    bindDetailEvents() {
        const backBtn = document.getElementById('backToGridBtn');
        const previewBtn = document.getElementById('previewCustomizedBtn');
        const printBtn = document.getElementById('printTemplateBtn');
        
        backBtn?.addEventListener('click', () => this.hideTemplateDetails());
        previewBtn?.addEventListener('click', () => this.previewCustomized());
        printBtn?.addEventListener('click', () => this.printTemplate());
    }
    
    hideTemplateDetails() {
        if (this.templateDetails) {
            this.templateDetails.style.display = 'none';
        }
        this.selectedTemplate = null;
    }
    
    getParameterValues() {
        const form = document.getElementById('parametersForm');
        if (!form) return {};
        
        const parameters = {};
        const inputs = form.querySelectorAll('.parameter-input, input[type="checkbox"]');
        
        inputs.forEach(input => {
            const name = input.name;
            if (name) {
                if (input.type === 'checkbox') {
                    parameters[name] = input.checked;
                } else if (input.type === 'number') {
                    parameters[name] = parseFloat(input.value) || 0;
                } else {
                    parameters[name] = input.value;
                }
            }
        });
        
        return parameters;
    }
    
    async previewCustomized() {
        if (!this.selectedTemplate) return;
        
        try {
            const parameters = this.getParameterValues();
            
            const response = await fetch(`${this.apiUrl}/templates/${this.selectedTemplate.id}/customize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    template_id: this.selectedTemplate.id,
                    parameters: parameters,
                    target_format: 'stl'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Customized model generated successfully!', 'success');
                // You could integrate with the 3D viewer here
                this.showPreview(result.customized_model);
            } else {
                this.showNotification('Failed to customize template', 'error');
            }
        } catch (error) {
            console.error('Error customizing template:', error);
            this.showNotification('Error customizing template', 'error');
        }
    }
    
    async printTemplate() {
        if (!this.selectedTemplate) return;
        
        try {
            const parameters = this.getParameterValues();
            
            const response = await fetch(`${this.apiUrl}/templates/${this.selectedTemplate.id}/print`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    parameters: parameters,
                    priority: 'normal'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`Print job created! Job ID: ${result.job_id}`, 'success');
                this.hideTemplateDetails();
            } else {
                this.showNotification('Failed to create print job', 'error');
            }
        } catch (error) {
            console.error('Error creating print job:', error);
            this.showNotification('Error creating print job', 'error');
        }
    }
    
    showPreview(preview) {
        // This could integrate with the 3D viewer
        console.log('Preview data:', preview);
        this.showNotification('Preview generated (check console for details)', 'info');
    }
    
    formatCategory(category) {
        return category?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Uncategorized';
    }
    
    formatDifficulty(difficulty) {
        return difficulty?.charAt(0).toUpperCase() + difficulty?.slice(1) || 'Unknown';
    }
    
    showLoading() {
        if (this.templateGrid) {
            this.templateGrid.innerHTML = `
                <div class="loading-templates">
                    <div class="loading-spinner"></div>
                    <div class="loading-message">Loading templates...</div>
                </div>
            `;
        }
    }
    
    showError(message) {
        if (this.templateGrid) {
            this.templateGrid.innerHTML = `
                <div class="error-templates">
                    <div class="error-icon">⚠️</div>
                    <div class="error-message">${message}</div>
                    <button class="btn btn-primary retry-btn" onclick="window.templateLibrary.loadTemplates()">
                        Retry
                    </button>
                </div>
            `;
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;
        
        // Add to notification container or body
        const container = document.getElementById('notificationContainer') || document.body;
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
        
        // Manual close
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn?.addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.templateLibrary = new TemplateLibrary();
});
