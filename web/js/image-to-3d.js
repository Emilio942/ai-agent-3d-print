/**
 * Image to 3D Conversion functionality
 * AI Agent 3D Print System
 */

class ImageTo3DManager {
    constructor() {
        this.currentFile = null;
        this.convertedModels = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadConvertedModels();
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // File upload
        const fileInput = document.getElementById('imageUpload');
        const uploadArea = document.getElementById('fileUploadArea');
        const convertButton = document.getElementById('convertButton');

        fileInput.addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files[0]);
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelection(files[0]);
            }
        });

        // Form submission
        document.getElementById('imageToModelForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.convertImageTo3D();
        });
    }

    switchTab(tabId) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabId).classList.add('active');

        // Initialize 3D viewer if switching to that tab
        if (tabId === '3d-viewer' && window.Viewer3DManager) {
            window.Viewer3DManager.init();
        }
    }

    handleFileSelection(file) {
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.showNotification('Please select a valid image file', 'error');
            return;
        }

        this.currentFile = file;
        this.showImagePreview(file);
        document.getElementById('convertButton').disabled = false;
    }

    showImagePreview(file) {
        const preview = document.getElementById('imagePreview');
        const reader = new FileReader();

        reader.onload = (e) => {
            preview.innerHTML = `
                <img src="${e.target.result}" alt="Preview" class="preview-image">
                <div class="preview-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${this.formatFileSize(file.size)}</span>
                </div>
                <button type="button" class="remove-image" onclick="imageToModelManager.removeImage()">×</button>
            `;
            preview.style.display = 'block';
        };

        reader.readAsDataURL(file);
    }

    removeImage() {
        this.currentFile = null;
        document.getElementById('imagePreview').style.display = 'none';
        document.getElementById('imageUpload').value = '';
        document.getElementById('convertButton').disabled = true;
    }

    async convertImageTo3D() {
        if (!this.currentFile) {
            this.showNotification('Please select an image first', 'error');
            return;
        }

        const convertButton = document.getElementById('convertButton');
        const originalText = convertButton.querySelector('.btn-text').textContent;
        
        try {
            // Update button state
            convertButton.disabled = true;
            convertButton.querySelector('.btn-text').textContent = 'Converting...';

            // Prepare form data
            const formData = new FormData();
            formData.append('file', this.currentFile);
            formData.append('style', document.getElementById('conversionStyle').value);
            formData.append('quality', document.getElementById('conversionQuality').value);
            formData.append('format', document.getElementById('outputFormat').value);

            // Show progress notification
            this.showNotification('Converting image to 3D model...', 'info');

            // Make API request
            const response = await fetch('/api/advanced/image-to-3d/convert', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Image converted successfully!', 'success');
                this.addConvertedModel(result);
                this.loadConvertedModels();
                this.removeImage();
            } else {
                throw new Error(result.detail || 'Conversion failed');
            }

        } catch (error) {
            console.error('Conversion error:', error);
            this.showNotification(`Conversion failed: ${error.message}`, 'error');
        } finally {
            // Reset button state
            convertButton.disabled = false;
            convertButton.querySelector('.btn-text').textContent = originalText;
        }
    }

    async loadConvertedModels() {
        try {
            const response = await fetch('/api/advanced/image-to-3d/models');
            const result = await response.json();

            if (result.success) {
                this.convertedModels = result.models;
                this.displayConvertedModels();
            }
        } catch (error) {
            console.error('Failed to load converted models:', error);
        }
    }

    displayConvertedModels() {
        const modelsContainer = document.getElementById('convertedModels');
        const modelsGrid = document.getElementById('modelsGrid');

        if (this.convertedModels.length === 0) {
            modelsContainer.style.display = 'none';
            return;
        }

        modelsContainer.style.display = 'block';
        modelsGrid.innerHTML = this.convertedModels.map(model => `
            <div class="model-card" data-model-id="${model.model_id}">
                <div class="model-preview">
                    ${model.preview_url ? 
                        `<img src="${model.preview_url}" alt="Model preview">` : 
                        '<div class="no-preview">📦</div>'
                    }
                </div>
                <div class="model-info">
                    <h4>${model.original_filename}</h4>
                    <p class="model-details">
                        Format: ${model.metadata.format?.toUpperCase()}<br>
                        Style: ${model.metadata.style}<br>
                        Created: ${this.formatDate(model.created_at)}
                    </p>
                    <div class="model-actions">
                        <button class="btn btn-sm btn-primary" onclick="imageToModelManager.printModel('${model.model_id}')">
                            Print
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="imageToModelManager.viewModel('${model.model_id}')">
                            View 3D
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="imageToModelManager.deleteModel('${model.model_id}')">
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    addConvertedModel(modelData) {
        this.convertedModels.unshift(modelData);
        this.displayConvertedModels();
    }

    async printModel(modelId) {
        try {
            const response = await fetch(`/api/advanced/image-to-3d/models/${modelId}/print`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    priority: 'normal'
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(`Print job created: ${result.job_id}`, 'success');
            } else {
                throw new Error(result.detail || 'Failed to create print job');
            }
        } catch (error) {
            console.error('Print error:', error);
            this.showNotification(`Print failed: ${error.message}`, 'error');
        }
    }

    async viewModel(modelId) {
        try {
            const response = await fetch(`/api/advanced/image-to-3d/models/${modelId}`);
            const result = await response.json();

            if (result.success && window.Viewer3DManager) {
                // Switch to 3D viewer tab
                this.switchTab('3d-viewer');
                
                // Load the model in the 3D viewer
                await window.Viewer3DManager.loadModel(result.model.model_path);
                
                this.showNotification('Model loaded in 3D viewer', 'success');
            } else {
                throw new Error('Failed to load model details');
            }
        } catch (error) {
            console.error('View error:', error);
            this.showNotification(`Failed to view model: ${error.message}`, 'error');
        }
    }

    async deleteModel(modelId) {
        if (!confirm('Are you sure you want to delete this model?')) {
            return;
        }

        try {
            const response = await fetch(`/api/advanced/image-to-3d/models/${modelId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Model deleted successfully', 'success');
                this.convertedModels = this.convertedModels.filter(m => m.model_id !== modelId);
                this.displayConvertedModels();
            } else {
                throw new Error(result.detail || 'Failed to delete model');
            }
        } catch (error) {
            console.error('Delete error:', error);
            this.showNotification(`Delete failed: ${error.message}`, 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Use the existing notification system
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }
}

// Initialize the image-to-3D manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.imageToModelManager = new ImageTo3DManager();
});
