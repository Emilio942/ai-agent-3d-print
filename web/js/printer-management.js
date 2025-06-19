/**
 * Printer Management JavaScript Module
 * Handles printer discovery, connection, and status monitoring
 */

class PrinterManager {
    constructor() {
        this.discoveredPrinters = [];
        this.connectedPrinters = [];
        this.isDiscovering = false;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Discover Printers Button
        const discoverBtn = document.getElementById('discoverPrintersBtn');
        if (discoverBtn) {
            discoverBtn.addEventListener('click', () => this.discoverPrinters());
        }
    }
    
    async discoverPrinters() {
        if (this.isDiscovering) return;
        
        this.isDiscovering = true;
        const discoverBtn = document.getElementById('discoverPrintersBtn');
        const statusDiv = document.getElementById('discoveryStatus');
        
        // Update UI
        discoverBtn.disabled = true;
        discoverBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Discovering...</span>';
        statusDiv.innerHTML = '<p class="status-message">🔍 Scanning for connected 3D printers...</p>';
        
        try {
            const response = await fetch('/api/printer/discover');
            
            if (!response.ok) {
                throw new Error(`Discovery failed: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Update discovered printers
            this.discoveredPrinters = result.discovered_printers;
            
            // Update UI with results
            this.updateDiscoveryResults(result);
            
        } catch (error) {
            console.error('Printer discovery error:', error);
            statusDiv.innerHTML = `<p class="error-message">❌ Discovery failed: ${error.message}</p>`;
        } finally {
            // Reset button
            this.isDiscovering = false;
            discoverBtn.disabled = false;
            discoverBtn.innerHTML = '<span class="btn-icon">🔍</span><span class="btn-text">Scan for Printers</span>';
        }
    }
    
    updateDiscoveryResults(result) {
        const statusDiv = document.getElementById('discoveryStatus');
        const printersDiv = document.getElementById('discoveredPrinters');
        
        // Update status message
        const scanTime = result.scan_time_seconds;
        const printerCount = result.total_found;
        
        statusDiv.innerHTML = `
            <p class="success-message">
                ✅ Discovery completed in ${scanTime}s - Found ${printerCount} printer(s)
            </p>
        `;
        
        // Clear previous results
        printersDiv.innerHTML = '';
        
        if (printerCount === 0) {
            printersDiv.innerHTML = `
                <div class="no-printers-found">
                    <p>🔌 No 3D printers found.</p>
                    <p>Make sure your printer is:</p>
                    <ul>
                        <li>Connected via USB</li>
                        <li>Powered on</li>
                        <li>Using a working USB cable</li>
                        <li>Using proper drivers (if needed)</li>
                    </ul>
                </div>
            `;
            return;
        }
        
        // Create printer cards
        result.discovered_printers.forEach(printer => {
            this.createPrinterCard(printer, printersDiv);
        });
    }
    
    createPrinterCard(printer, container) {
        const card = document.createElement('div');
        card.className = 'printer-card';
        card.dataset.port = printer.port;
        
        const buildVolumeStr = printer.build_volume.join(' × ') + ' mm';
        const statusClass = printer.is_connected ? 'connected' : 'available';
        const statusIcon = printer.is_connected ? '🟢' : '🔵';
        const statusText = printer.is_connected ? 'Connected' : 'Available';
        
        card.innerHTML = `
            <div class="printer-card-header">
                <h4 class="printer-name">${printer.name}</h4>
                <span class="printer-status ${statusClass}">
                    ${statusIcon} ${statusText}
                </span>
            </div>
            <div class="printer-details">
                <div class="detail-row">
                    <span class="detail-label">Port:</span>
                    <span class="detail-value">${printer.port}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Brand:</span>
                    <span class="detail-value">${printer.brand}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Firmware:</span>
                    <span class="detail-value">${printer.firmware_type}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Build Volume:</span>
                    <span class="detail-value">${buildVolumeStr}</span>
                </div>
                ${printer.profile_name ? `
                <div class="detail-row">
                    <span class="detail-label">Profile:</span>
                    <span class="detail-value">${printer.profile_name}</span>
                </div>
                ` : ''}
            </div>
            <div class="printer-actions">
                ${printer.is_connected ? `
                    <button class="btn btn-secondary" onclick="printerManager.disconnectPrinter('${printer.port}')">
                        Disconnect
                    </button>
                    <button class="btn btn-info" onclick="printerManager.checkPrinterStatus('${printer.port}')">
                        Check Status
                    </button>
                ` : `
                    <button class="btn btn-primary" onclick="printerManager.connectPrinter('${printer.port}')">
                        Connect
                    </button>
                `}
            </div>
        `;
        
        container.appendChild(card);
    }
    
    async connectPrinter(port) {
        try {
            const encodedPort = encodeURIComponent(port);
            const response = await fetch(`/api/printer/${encodedPort}/connect`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`Connection failed: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Show success message
            this.showNotification(`✅ ${result.message}`, 'success');
            
            // Refresh printer list
            await this.discoverPrinters();
            
        } catch (error) {
            console.error('Connection error:', error);
            this.showNotification(`❌ Failed to connect: ${error.message}`, 'error');
        }
    }
    
    async disconnectPrinter(port) {
        try {
            const encodedPort = encodeURIComponent(port);
            const response = await fetch(`/api/printer/${encodedPort}/disconnect`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`Disconnection failed: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Show success message
            this.showNotification(`✅ ${result.message}`, 'success');
            
            // Refresh printer list
            await this.discoverPrinters();
            
        } catch (error) {
            console.error('Disconnection error:', error);
            this.showNotification(`❌ Failed to disconnect: ${error.message}`, 'error');
        }
    }
    
    async checkPrinterStatus(port) {
        try {
            const encodedPort = encodeURIComponent(port);
            const response = await fetch(`/api/printer/${encodedPort}/status`);
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.status} ${response.statusText}`);
            }
            
            const status = await response.json();
            
            // Show status in a modal or update UI
            this.showPrinterStatus(port, status);
            
        } catch (error) {
            console.error('Status check error:', error);
            this.showNotification(`❌ Failed to check status: ${error.message}`, 'error');
        }
    }
    
    showPrinterStatus(port, status) {
        let statusMessage = `📊 Printer Status for ${port}:\\n\\n`;
        statusMessage += `Status: ${status.status}\\n`;
        statusMessage += `Is Printing: ${status.is_printing ? 'Yes' : 'No'}\\n`;
        statusMessage += `Progress: ${status.progress}%\\n`;
        
        if (Object.keys(status.temperature).length > 0) {
            statusMessage += `\\nTemperatures:\\n`;
            for (const [sensor, temp] of Object.entries(status.temperature)) {
                statusMessage += `  ${sensor}: ${temp}°C\\n`;
            }
        }
        
        if (Object.keys(status.position).length > 0) {
            statusMessage += `\\nPosition:\\n`;
            for (const [axis, pos] of Object.entries(status.position)) {
                statusMessage += `  ${axis}: ${pos}mm\\n`;
            }
        }
        
        alert(statusMessage);
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize printer manager when DOM is loaded
let printerManager;

document.addEventListener('DOMContentLoaded', () => {
    printerManager = new PrinterManager();
});

// Export for external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PrinterManager;
}
