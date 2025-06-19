/**
 * Voice Control Interface for AI Agent 3D Print System
 * Handles voice command recognition and processing
 */

class VoiceControlManager {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.apiUrl = '/api/advanced';
        this.commandHistory = [];
        
        this.init();
    }
    
    init() {
        this.initElements();
        this.initSpeechRecognition();
        this.bindEvents();
        this.loadCommandHistory();
        this.checkVoiceStatus();
    }
    
    initElements() {
        this.startBtn = document.getElementById('startVoiceBtn');
        this.stopBtn = document.getElementById('stopVoiceBtn');
        this.testBtn = document.getElementById('testCommandBtn');
        this.textCommandInput = document.getElementById('textCommand');
        this.voiceStatus = document.getElementById('voiceStatus');
        this.voiceIndicator = document.getElementById('voiceIndicator');
        this.voiceStatusText = document.getElementById('voiceStatusText');
        this.voiceResults = document.getElementById('voiceResults');
        this.voiceHistory = document.getElementById('voiceHistory');
    }
    
    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                this.updateStatus(true);
                this.showResult('Listening...', 'info');
            };
            
            this.recognition.onresult = (event) => {
                const command = event.results[event.results.length - 1][0].transcript;
                this.processVoiceCommand(command);
            };
            
            this.recognition.onerror = (event) => {
                this.showResult(`Recognition error: ${event.error}`, 'error');
                this.updateStatus(false);
            };
            
            this.recognition.onend = () => {
                if (this.isListening) {
                    // Restart recognition if we should be listening
                    setTimeout(() => this.recognition.start(), 100);
                } else {
                    this.updateStatus(false);
                }
            };
        } else {
            this.showResult('Speech recognition not supported in this browser', 'error');
        }
    }
    
    bindEvents() {
        this.startBtn?.addEventListener('click', () => this.startListening());
        this.stopBtn?.addEventListener('click', () => this.stopListening());
        this.testBtn?.addEventListener('click', () => this.testCommand());
        
        this.textCommandInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.testCommand();
            }
        });
    }
    
    async startListening() {
        try {
            if (this.recognition) {
                this.isListening = true;
                this.recognition.start();
                
                // Also notify the backend
                const response = await fetch(`${this.apiUrl}/voice/start`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to start voice control on server');
                }
            }
        } catch (error) {
            console.error('Error starting voice control:', error);
            this.showResult(`Failed to start: ${error.message}`, 'error');
            this.updateStatus(false);
        }
    }
    
    async stopListening() {
        try {
            this.isListening = false;
            
            if (this.recognition) {
                this.recognition.stop();
            }
            
            // Notify the backend
            const response = await fetch(`${this.apiUrl}/voice/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to stop voice control on server');
            }
            
            this.updateStatus(false);
            this.showResult('Voice control stopped', 'info');
        } catch (error) {
            console.error('Error stopping voice control:', error);
            this.showResult(`Failed to stop: ${error.message}`, 'error');
        }
    }
    
    async testCommand() {
        const command = this.textCommandInput?.value?.trim();
        if (!command) {
            this.showResult('Please enter a command to test', 'warning');
            return;
        }
        
        await this.processTextCommand(command);
        this.textCommandInput.value = '';
    }
    
    async processVoiceCommand(command) {
        this.showResult(`Recognized: "${command}"`, 'info');
        
        try {
            const response = await fetch(`${this.apiUrl}/voice/command`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text_command: command,
                    confidence_threshold: 0.7
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.displayCommandResult(result.command);
                this.addToHistory(command, result.command);
            } else {
                this.showResult('Failed to process command', 'error');
            }
        } catch (error) {
            console.error('Error processing voice command:', error);
            this.showResult(`Processing error: ${error.message}`, 'error');
        }
    }
    
    async processTextCommand(command) {
        this.showResult(`Testing: "${command}"`, 'info');
        
        try {
            const response = await fetch(`${this.apiUrl}/voice/command`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text_command: command,
                    confidence_threshold: 0.5
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.displayCommandResult(result.command);
                this.addToHistory(command, result.command);
            } else {
                this.showResult('Failed to process command', 'error');
            }
        } catch (error) {
            console.error('Error processing text command:', error);
            this.showResult(`Processing error: ${error.message}`, 'error');
        }
    }
    
    displayCommandResult(command) {
        const resultHtml = `
            <div class="command-result">
                <strong>Intent:</strong> ${command.intent}<br>
                <strong>Confidence:</strong> ${(command.confidence * 100).toFixed(1)}%<br>
                <strong>Parameters:</strong> ${JSON.stringify(command.parameters, null, 2)}<br>
                <strong>Action:</strong> ${command.recognized_text}
            </div>
        `;
        this.showResult(resultHtml, 'success');
    }
    
    addToHistory(originalCommand, processedCommand) {
        const historyItem = {
            command: originalCommand,
            intent: processedCommand.intent,
            confidence: processedCommand.confidence,
            timestamp: new Date().toISOString()
        };
        
        this.commandHistory.unshift(historyItem);
        if (this.commandHistory.length > 10) {
            this.commandHistory.pop();
        }
        
        this.updateHistoryDisplay();
    }
    
    updateHistoryDisplay() {
        if (!this.voiceHistory) return;
        
        const historyHtml = this.commandHistory.map(item => `
            <div class="history-item">
                <div class="history-command">"${item.command}"</div>
                <div class="history-details">
                    Intent: ${item.intent} | 
                    Confidence: ${(item.confidence * 100).toFixed(1)}% | 
                    ${new Date(item.timestamp).toLocaleTimeString()}
                </div>
            </div>
        `).join('');
        
        this.voiceHistory.innerHTML = historyHtml || '<div class="no-history">No commands yet</div>';
    }
    
    showResult(message, type = 'info') {
        if (!this.voiceResults) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const resultElement = document.createElement('div');
        resultElement.className = `result-item result-${type}`;
        resultElement.innerHTML = `
            <span class="result-time">[${timestamp}]</span>
            <span class="result-message">${message}</span>
        `;
        
        this.voiceResults.insertBefore(resultElement, this.voiceResults.firstChild);
        
        // Keep only last 10 results
        while (this.voiceResults.children.length > 10) {
            this.voiceResults.removeChild(this.voiceResults.lastChild);
        }
    }
    
    updateStatus(isActive) {
        this.isListening = isActive;
        
        if (this.voiceIndicator) {
            this.voiceIndicator.className = `status-indicator ${isActive ? 'active' : 'inactive'}`;
        }
        
        if (this.voiceStatusText) {
            this.voiceStatusText.textContent = isActive ? 'Voice control active' : 'Voice control inactive';
        }
        
        if (this.startBtn) {
            this.startBtn.disabled = isActive;
        }
        
        if (this.stopBtn) {
            this.stopBtn.disabled = !isActive;
        }
    }
    
    async checkVoiceStatus() {
        try {
            const response = await fetch(`${this.apiUrl}/voice/status`);
            const result = await response.json();
            
            if (result.success) {
                this.updateStatus(result.status.is_listening);
            }
        } catch (error) {
            console.error('Error checking voice status:', error);
        }
    }
    
    async loadCommandHistory() {
        try {
            const response = await fetch(`${this.apiUrl}/voice/commands`);
            const result = await response.json();
            
            if (result.success) {
                this.commandHistory = result.commands.slice(0, 10);
                this.updateHistoryDisplay();
            }
        } catch (error) {
            console.error('Error loading command history:', error);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.voiceControlManager = new VoiceControlManager();
});
