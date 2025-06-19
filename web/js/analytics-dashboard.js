/**
 * Analytics Dashboard for AI Agent 3D Print System
 * Handles real-time analytics, charts, and performance monitoring
 */

class AnalyticsDashboard {
    constructor() {
        this.apiUrl = '/api/advanced';
        this.charts = {};
        this.refreshInterval = null;
        this.refreshRate = 30000; // 30 seconds
        
        this.init();
    }
    
    init() {
        this.initElements();
        this.bindEvents();
        this.loadAnalytics();
        this.startAutoRefresh();
    }
    
    initElements() {
        this.overviewContainer = document.getElementById('analyticsOverview');
        this.chartsContainer = document.querySelector('.analytics-charts');
        this.detailsContainer = document.getElementById('analyticsDetails');
        this.refreshBtn = document.getElementById('refreshAnalyticsBtn');
        this.timeRangeSelect = document.getElementById('timeRangeSelect');
        
        // Metric elements
        this.totalPrintsEl = document.getElementById('totalPrints');
        this.successRateEl = document.getElementById('successRate');
        this.activeJobsEl = document.getElementById('activeJobs');
        this.systemHealthEl = document.getElementById('systemHealth');
        
        // Chart elements
        this.activityChartEl = document.getElementById('activityChart');
        this.performanceChartEl = document.getElementById('performanceChart');
    }
    
    bindEvents() {
        this.refreshBtn?.addEventListener('click', () => this.loadAnalytics());
        this.timeRangeSelect?.addEventListener('change', () => this.loadAnalytics());
    }
    
    async loadAnalytics() {
        try {
            this.showLoading();
            
            // Load overview data
            await this.loadOverview();
            
            // Load live metrics
            await this.loadLiveMetrics();
            
            // Load performance data
            await this.loadPerformanceData();
            
            // Load system health
            await this.loadSystemHealth();
            
            this.hideLoading();
        } catch (error) {
            console.error('Error loading analytics:', error);
            this.showError('Failed to load analytics data');
        }
    }
    
    async loadOverview() {
        try {
            const response = await fetch(`${this.apiUrl}/analytics/overview`);
            const result = await response.json();
            
            if (result.success) {
                this.updateOverviewMetrics(result.overview);
            }
        } catch (error) {
            console.error('Error loading overview:', error);
        }
    }
    
    async loadLiveMetrics() {
        try {
            const response = await fetch(`${this.apiUrl}/analytics/metrics/live`);
            const result = await response.json();
            
            if (result.success) {
                this.updateLiveMetrics(result.metrics);
            }
        } catch (error) {
            console.error('Error loading live metrics:', error);
        }
    }
    
    async loadPerformanceData() {
        try {
            const response = await fetch(`${this.apiUrl}/analytics/performance`);
            const result = await response.json();
            
            if (result.success) {
                this.updatePerformanceCharts(result.performance);
            }
        } catch (error) {
            console.error('Error loading performance data:', error);
        }
    }
    
    async loadSystemHealth() {
        try {
            const response = await fetch(`${this.apiUrl}/analytics/health`);
            const result = await response.json();
            
            if (result.success) {
                this.updateSystemHealth(result.health);
            }
        } catch (error) {
            console.error('Error loading system health:', error);
        }
    }
    
    updateOverviewMetrics(overview) {
        // Update metric cards
        if (this.totalPrintsEl) {
            this.totalPrintsEl.textContent = overview.total_prints || '0';
        }
        
        if (this.successRateEl) {
            const rate = overview.success_rate || 0;
            this.successRateEl.textContent = `${(rate * 100).toFixed(1)}%`;
        }
        
        if (this.activeJobsEl) {
            this.activeJobsEl.textContent = overview.active_jobs || '0';
        }
    }
    
    updateLiveMetrics(metrics) {
        // Update activity chart with live data
        this.updateActivityChart(metrics.activity_data || []);
        
        // Update details section
        this.updateDetailsSection(metrics);
    }
    
    updatePerformanceCharts(performance) {
        // Update performance chart
        this.updatePerformanceChart(performance.performance_data || []);
    }
    
    updateSystemHealth(health) {
        if (this.systemHealthEl) {
            const healthScore = health.overall_score || 0;
            this.systemHealthEl.textContent = `${(healthScore * 100).toFixed(0)}%`;
            
            // Update color based on health
            const healthClass = healthScore > 0.8 ? 'healthy' : healthScore > 0.6 ? 'warning' : 'critical';
            this.systemHealthEl.className = `metric-value ${healthClass}`;
        }
    }
    
    updateActivityChart(activityData) {
        if (!this.activityChartEl) return;
        
        const ctx = this.activityChartEl.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.charts.activity) {
            this.charts.activity.destroy();
        }
        
        // Create new chart with Chart.js (if available) or simple canvas drawing
        if (window.Chart) {
            this.charts.activity = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: activityData.map(d => d.timestamp || d.label),
                    datasets: [{
                        label: 'Print Activity',
                        data: activityData.map(d => d.value || d.count),
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        } else {
            // Fallback to simple canvas drawing
            this.drawSimpleChart(ctx, activityData, 'Activity');
        }
    }
    
    updatePerformanceChart(performanceData) {
        if (!this.performanceChartEl) return;
        
        const ctx = this.performanceChartEl.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.charts.performance) {
            this.charts.performance.destroy();
        }
        
        if (window.Chart) {
            this.charts.performance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: performanceData.map(d => d.metric || d.label),
                    datasets: [{
                        label: 'Performance',
                        data: performanceData.map(d => d.value || d.score),
                        backgroundColor: [
                            '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        } else {
            // Fallback to simple canvas drawing
            this.drawSimpleChart(ctx, performanceData, 'Performance');
        }
    }
    
    drawSimpleChart(ctx, data, title) {
        const canvas = ctx.canvas;
        const width = canvas.width;
        const height = canvas.height;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        if (!data || data.length === 0) {
            // Draw "No data" message
            ctx.fillStyle = '#6b7280';
            ctx.font = '16px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No data available', width / 2, height / 2);
            return;
        }
        
        // Simple line chart
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        const maxValue = Math.max(...data.map(d => d.value || d.count || 0));
        const padding = 40;
        const chartWidth = width - 2 * padding;
        const chartHeight = height - 2 * padding;
        
        data.forEach((point, index) => {
            const x = padding + (index * chartWidth) / (data.length - 1);
            const y = height - padding - ((point.value || point.count || 0) * chartHeight) / maxValue;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // Draw title
        ctx.fillStyle = '#374151';
        ctx.font = '14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(title, width / 2, 20);
    }
    
    updateDetailsSection(metrics) {
        if (!this.detailsContainer) return;
        
        const detailsHtml = `
            <div class="analytics-details-content">
                <h3>System Metrics</h3>
                <div class="metrics-grid">
                    <div class="metric-detail">
                        <span class="metric-label">CPU Usage:</span>
                        <span class="metric-value">${metrics.cpu_usage?.toFixed(1) || 'N/A'}%</span>
                    </div>
                    <div class="metric-detail">
                        <span class="metric-label">Memory Usage:</span>
                        <span class="metric-value">${metrics.memory_usage?.toFixed(1) || 'N/A'}%</span>
                    </div>
                    <div class="metric-detail">
                        <span class="metric-label">Queue Length:</span>
                        <span class="metric-value">${metrics.queue_length || 0}</span>
                    </div>
                    <div class="metric-detail">
                        <span class="metric-label">Average Response Time:</span>
                        <span class="metric-value">${metrics.avg_response_time?.toFixed(0) || 'N/A'}ms</span>
                    </div>
                </div>
                
                <h3>Recent Activity</h3>
                <div class="activity-log">
                    ${(metrics.recent_activity || []).map(activity => `
                        <div class="activity-item">
                            <span class="activity-time">${new Date(activity.timestamp).toLocaleTimeString()}</span>
                            <span class="activity-description">${activity.description}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        this.detailsContainer.innerHTML = detailsHtml;
    }
    
    showLoading() {
        // Show loading indicators on metric cards
        const metricValues = document.querySelectorAll('.metric-value');
        metricValues.forEach(el => {
            if (el.textContent !== '--') {
                el.classList.add('loading');
            }
        });
    }
    
    hideLoading() {
        // Hide loading indicators
        const metricValues = document.querySelectorAll('.metric-value');
        metricValues.forEach(el => {
            el.classList.remove('loading');
        });
    }
    
    showError(message) {
        if (this.detailsContainer) {
            this.detailsContainer.innerHTML = `
                <div class="error-message">
                    <span class="error-icon">⚠️</span>
                    <span>${message}</span>
                </div>
            `;
        }
    }
    
    startAutoRefresh() {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Start new refresh interval
        this.refreshInterval = setInterval(() => {
            this.loadAnalytics();
        }, this.refreshRate);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    destroy() {
        this.stopAutoRefresh();
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.analyticsDashboard = new AnalyticsDashboard();
});

// Cleanup when page is unloaded
window.addEventListener('beforeunload', () => {
    if (window.analyticsDashboard) {
        window.analyticsDashboard.destroy();
    }
});
