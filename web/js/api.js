/**
 * API Communication Module
 * Handles all REST API calls to the FastAPI backend
 */

class APIClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
        this.timeout = 30000; // 30 seconds
    }

    /**
     * Make HTTP request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            timeout: this.timeout
        };

        const config = { ...defaultOptions, ...options };

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), config.timeout);
            
            const response = await fetch(url, {
                ...config,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new APIError(
                    response.status,
                    errorData.detail || `HTTP ${response.status}`,
                    errorData
                );
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new APIError(408, 'Request timeout');
            }
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError(0, 'Network error', { originalError: error.message });
        }
    }

    /**
     * Submit a new print request
     */
    async submitPrintRequest(userRequest, priority = 'normal') {
        return await this.request('/api/print-request', {
            method: 'POST',
            body: JSON.stringify({
                user_request: userRequest,
                priority: priority
            })
        });
    }

    /**
     * Submit a new print request with image upload
     */
    async submitImagePrintRequest(imageFile, priority = 'normal', extrusionHeight = 5.0, baseThickness = 1.0) {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('priority', priority);
        formData.append('extrusion_height', extrusionHeight.toString());
        formData.append('base_thickness', baseThickness.toString());

        // For FormData, we need to override the default JSON headers
        const url = `${this.baseURL}/api/image-print-request`;
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new APIError(
                    response.status,
                    errorData.detail || `HTTP ${response.status}`,
                    errorData
                );
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new APIError(408, 'Request timeout');
            }
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError(0, 'Network error', { originalError: error.message });
        }
    }

    /**
     * Get job status by ID
     */
    async getJobStatus(jobId) {
        return await this.request(`/api/status/${jobId}`);
    }

    /**
     * Get all workflows with pagination
     */
    async getWorkflows(skip = 0, limit = 50, status = null) {
        const params = new URLSearchParams({
            skip: skip.toString(),
            limit: limit.toString()
        });
        
        if (status) {
            params.append('status', status);
        }

        return await this.request(`/api/workflows?${params}`);
    }

    /**
     * Cancel a workflow
     */
    async cancelWorkflow(jobId) {
        return await this.request(`/api/workflows/${jobId}`, {
            method: 'DELETE'
        });
    }

    /**
     * Get system health status
     */
    async getHealth() {
        return await this.request('/health');
    }

    /**
     * Check if API is reachable
     */
    async ping() {
        try {
            await this.getHealth();
            return true;
        } catch (error) {
            return false;
        }
    }
}

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(status, message, data = {}) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }

    toString() {
        return `APIError ${this.status}: ${this.message}`;
    }
}

// Export for use in other modules
window.APIClient = APIClient;
window.APIError = APIError;
