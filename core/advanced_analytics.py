"""
Advanced Analytics & Monitoring Dashboard for AI Agent 3D Print System

This module provides comprehensive analytics, monitoring, and dashboard capabilities
including real-time metrics visualization, performance trend analysis, predictive
monitoring, and advanced system insights.

Features:
- Real-time system performance monitoring
- Advanced metrics collection and analysis
- Predictive maintenance alerts
- Historical trend analysis
- Interactive dashboard data preparation
- Alert management system
- Performance optimization recommendations
"""

import asyncio
import json
import time
import statistics
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, deque
import psutil
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from core.logger import get_logger
from core.performance import MultiLevelCache, ResourceManager, PerformanceMonitor

logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """Comprehensive system metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    cache_hit_rate: float
    active_requests: int
    response_time_avg: float
    error_rate: float
    workflow_count: Dict[str, int]
    queue_size: int
    temperature: Optional[float] = None


@dataclass
class Alert:
    """System alert definition"""
    alert_id: str
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'performance', 'security', 'system', 'user'
    title: str
    description: str
    threshold_value: float
    current_value: float
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class PerformanceTrend:
    """Performance trend analysis"""
    metric_name: str
    time_range: str  # '1h', '24h', '7d', '30d'
    trend_direction: str  # 'improving', 'stable', 'degrading'
    change_percentage: float
    prediction_24h: Optional[float]
    confidence_score: float
    data_points: List[Tuple[datetime, float]]


class AdvancedAnalytics:
    """Advanced analytics and monitoring system"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/analytics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = get_logger(f"{__name__}.AdvancedAnalytics")
        
        # Initialize components
        self.cache = MultiLevelCache()
        self.resource_manager = ResourceManager()
        self.performance_monitor = PerformanceMonitor()
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=10000)  # Store last 10k metrics
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, Dict] = {}
        
        # Analytics models
        self.trend_predictor = LinearRegression()
        self.scaler = StandardScaler()
        
        # Initialize database
        self._init_database()
        self._load_alert_rules()
        
        # Start background monitoring
        self._monitoring_active = True
        
    def _init_database(self):
        """Initialize analytics database"""
        try:
            db_path = self.data_dir / "analytics.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        alert_id TEXT PRIMARY KEY,
                        severity TEXT NOT NULL,
                        category TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        threshold_value REAL,
                        current_value REAL,
                        timestamp TEXT NOT NULL,
                        acknowledged BOOLEAN DEFAULT FALSE,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Performance trends table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_trends (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        time_range TEXT NOT NULL,
                        trend_data TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Alert rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alert_rules (
                        rule_id TEXT PRIMARY KEY,
                        metric_name TEXT NOT NULL,
                        threshold_value REAL NOT NULL,
                        operator TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                
            self.logger.info("Analytics database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing analytics database: {e}")
            raise

    def _load_alert_rules(self):
        """Load alert rules from database or create defaults"""
        try:
            db_path = self.data_dir / "analytics.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM alert_rules WHERE enabled = TRUE")
                rules = cursor.fetchall()
                
                if not rules:
                    # Create default alert rules
                    default_rules = [
                        ("cpu_high", "cpu_usage", 90.0, ">", "warning"),
                        ("cpu_critical", "cpu_usage", 95.0, ">", "critical"),
                        ("memory_high", "memory_usage", 85.0, ">", "warning"),
                        ("memory_critical", "memory_usage", 95.0, ">", "critical"),
                        ("disk_high", "disk_usage", 90.0, ">", "warning"),
                        ("response_slow", "response_time_avg", 2000.0, ">", "warning"),
                        ("error_rate_high", "error_rate", 5.0, ">", "warning"),
                        ("cache_low", "cache_hit_rate", 50.0, "<", "info"),
                    ]
                    
                    for rule_id, metric, threshold, operator, severity in default_rules:
                        cursor.execute("""
                            INSERT INTO alert_rules (rule_id, metric_name, threshold_value, operator, severity)
                            VALUES (?, ?, ?, ?, ?)
                        """, (rule_id, metric, threshold, operator, severity))
                        
                        self.alert_rules[rule_id] = {
                            'metric_name': metric,
                            'threshold_value': threshold,
                            'operator': operator,
                            'severity': severity
                        }
                    
                    conn.commit()
                else:
                    # Load existing rules
                    for rule in rules:
                        rule_id, metric_name, threshold, operator, severity, _, _ = rule
                        self.alert_rules[rule_id] = {
                            'metric_name': metric_name,
                            'threshold_value': threshold,
                            'operator': operator,
                            'severity': severity
                        }
                        
            self.logger.info(f"Loaded {len(self.alert_rules)} alert rules")
            
        except Exception as e:
            self.logger.error(f"Error loading alert rules: {e}")

    async def collect_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        try:
            timestamp = datetime.now()
            
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Application metrics
            cache_stats = self.cache.get_stats()
            performance_stats = self.performance_monitor.get_performance_summary(5)  # Last 5 minutes
            
            # Extract performance values with fallbacks
            perf_averages = performance_stats.get('averages', {})
            perf_latest = performance_stats.get('latest', {})
            
            # Network I/O
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Workflow metrics (placeholder - would integrate with actual workflow system)
            workflow_count = {
                'pending': 0,
                'research_phase': 0,
                'cad_phase': 0,
                'slicing_phase': 0,
                'printing_phase': 0,
                'completed': 0,
                'failed': 0
            }
            
            metrics = SystemMetrics(
                timestamp=timestamp,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_io=network_io,
                cache_hit_rate=cache_stats.get('hit_rate', 0) * 100,
                active_requests=perf_latest.get('active_connections', 0),
                response_time_avg=perf_averages.get('response_time', 0) * 1000,  # Convert to ms
                error_rate=perf_averages.get('error_rate', 0) * 100,  # Convert to percentage
                workflow_count=workflow_count,
                queue_size=0  # Would integrate with job queue
            )
            
            # Store metrics
            self.metrics_history.append(metrics)
            await self._store_metrics(metrics)
            
            # Check for alerts
            await self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            raise

    async def _store_metrics(self, metrics: SystemMetrics):
        """Store metrics in database"""
        try:
            db_path = self.data_dir / "analytics.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO system_metrics (timestamp, metrics_json)
                    VALUES (?, ?)
                """, (
                    metrics.timestamp.isoformat(),
                    json.dumps(asdict(metrics), default=str)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error storing metrics: {e}")

    async def _check_alerts(self, metrics: SystemMetrics):
        """Check metrics against alert rules"""
        try:
            for rule_id, rule in self.alert_rules.items():
                metric_name = rule['metric_name']
                threshold = rule['threshold_value']
                operator = rule['operator']
                severity = rule['severity']
                
                # Get current value
                current_value = getattr(metrics, metric_name, 0)
                
                # Check condition
                triggered = False
                if operator == ">":
                    triggered = current_value > threshold
                elif operator == "<":
                    triggered = current_value < threshold
                elif operator == ">=":
                    triggered = current_value >= threshold
                elif operator == "<=":
                    triggered = current_value <= threshold
                    
                if triggered:
                    await self._create_alert(
                        rule_id=rule_id,
                        severity=severity,
                        metric_name=metric_name,
                        threshold=threshold,
                        current_value=current_value,
                        timestamp=metrics.timestamp
                    )
                    
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")

    async def _create_alert(self, rule_id: str, severity: str, metric_name: str, 
                          threshold: float, current_value: float, timestamp: datetime):
        """Create and store alert"""
        try:
            alert_id = f"{rule_id}_{int(timestamp.timestamp())}"
            
            # Check if similar alert exists recently (prevent spam)
            recent_alerts = [a for a in self.alerts 
                           if a.category == metric_name and 
                           (timestamp - a.timestamp).total_seconds() < 300]  # 5 minutes
            
            if recent_alerts:
                return  # Don't create duplicate alerts
            
            alert = Alert(
                alert_id=alert_id,
                severity=severity,
                category="performance",
                title=f"{metric_name.replace('_', ' ').title()} Alert",
                description=f"{metric_name} is {current_value:.2f}, threshold: {threshold:.2f}",
                threshold_value=threshold,
                current_value=current_value,
                timestamp=timestamp
            )
            
            self.alerts.append(alert)
            
            # Store in database
            db_path = self.data_dir / "analytics.db"
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alerts (alert_id, severity, category, title, description,
                                      threshold_value, current_value, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id, alert.severity, alert.category, alert.title,
                    alert.description, alert.threshold_value, alert.current_value,
                    alert.timestamp.isoformat()
                ))
                conn.commit()
            
            self.logger.warning(f"Alert created: {alert.title} - {alert.description}")
            
        except Exception as e:
            self.logger.error(f"Error creating alert: {e}")

    async def analyze_performance_trends(self, metric_name: str, 
                                       time_range: str = "24h") -> PerformanceTrend:
        """Analyze performance trends for a specific metric"""
        try:
            # Get historical data
            data_points = await self._get_historical_data(metric_name, time_range)
            
            if len(data_points) < 10:
                return PerformanceTrend(
                    metric_name=metric_name,
                    time_range=time_range,
                    trend_direction="insufficient_data",
                    change_percentage=0.0,
                    prediction_24h=None,
                    confidence_score=0.0,
                    data_points=data_points
                )
            
            # Extract values and timestamps
            timestamps = [point[0] for point in data_points]
            values = [point[1] for point in data_points]
            
            # Calculate trend
            x = np.array(range(len(values))).reshape(-1, 1)
            y = np.array(values)
            
            self.trend_predictor.fit(x, y)
            slope = self.trend_predictor.coef_[0]
            
            # Determine trend direction
            if abs(slope) < 0.01:
                trend_direction = "stable"
            elif slope > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
                
            # Calculate change percentage
            if len(values) > 1:
                change_percentage = ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else 0
            else:
                change_percentage = 0.0
                
            # Predict next 24h
            next_x = len(values)
            prediction_24h = self.trend_predictor.predict([[next_x]])[0]
            
            # Calculate confidence (R²)
            score = self.trend_predictor.score(x, y)
            confidence_score = max(0.0, min(1.0, score))
            
            return PerformanceTrend(
                metric_name=metric_name,
                time_range=time_range,
                trend_direction=trend_direction,
                change_percentage=change_percentage,
                prediction_24h=prediction_24h,
                confidence_score=confidence_score,
                data_points=data_points
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance trends: {e}")
            return PerformanceTrend(
                metric_name=metric_name,
                time_range=time_range,
                trend_direction="error",
                change_percentage=0.0,
                prediction_24h=None,
                confidence_score=0.0,
                data_points=[]
            )

    async def _get_historical_data(self, metric_name: str, 
                                 time_range: str) -> List[Tuple[datetime, float]]:
        """Get historical data for a metric"""
        try:
            # Convert time range to timedelta
            time_delta_map = {
                "1h": timedelta(hours=1),
                "24h": timedelta(hours=24),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30)
            }
            
            delta = time_delta_map.get(time_range, timedelta(hours=24))
            start_time = datetime.now() - delta
            
            db_path = self.data_dir / "analytics.db"
            data_points = []
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, metrics_json FROM system_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp
                """, (start_time.isoformat(),))
                
                rows = cursor.fetchall()
                
                for timestamp_str, metrics_json in rows:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        metrics_data = json.loads(metrics_json)
                        
                        if metric_name in metrics_data:
                            value = metrics_data[metric_name]
                            data_points.append((timestamp, float(value)))
                            
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
                        
            return data_points
            
        except Exception as e:
            self.logger.error(f"Error getting historical data: {e}")
            return []

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            # Current metrics
            current_metrics = await self.collect_metrics()
            
            # Recent alerts
            recent_alerts = [a for a in self.alerts 
                           if (datetime.now() - a.timestamp).total_seconds() < 86400]  # Last 24h
            
            # Performance trends
            key_metrics = ["cpu_usage", "memory_usage", "response_time_avg", "cache_hit_rate"]
            trends = {}
            
            for metric in key_metrics:
                trends[metric] = await self.analyze_performance_trends(metric, "24h")
            
            # System health score
            health_score = await self._calculate_health_score(current_metrics)
            
            # Recommendations
            recommendations = await self._generate_recommendations(current_metrics, trends)
            
            dashboard_data = {
                "current_metrics": asdict(current_metrics),
                "health_score": health_score,
                "recent_alerts": [asdict(alert) for alert in recent_alerts[:10]],
                "performance_trends": {k: asdict(v) for k, v in trends.items()},
                "recommendations": recommendations,
                "system_status": "healthy" if health_score > 80 else "warning" if health_score > 60 else "critical",
                "last_updated": datetime.now().isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}")
            return {"error": str(e)}

    async def _calculate_health_score(self, metrics: SystemMetrics) -> float:
        """Calculate overall system health score (0-100)"""
        try:
            score = 100.0
            
            # CPU impact (max -30 points)
            if metrics.cpu_usage > 90:
                score -= 30
            elif metrics.cpu_usage > 75:
                score -= 15
            elif metrics.cpu_usage > 60:
                score -= 5
                
            # Memory impact (max -25 points)
            if metrics.memory_usage > 95:
                score -= 25
            elif metrics.memory_usage > 85:
                score -= 15
            elif metrics.memory_usage > 70:
                score -= 5
                
            # Response time impact (max -20 points)
            if metrics.response_time_avg > 2000:
                score -= 20
            elif metrics.response_time_avg > 1000:
                score -= 10
            elif metrics.response_time_avg > 500:
                score -= 5
                
            # Error rate impact (max -15 points)
            if metrics.error_rate > 10:
                score -= 15
            elif metrics.error_rate > 5:
                score -= 8
            elif metrics.error_rate > 1:
                score -= 3
                
            # Cache performance bonus (max +10 points)
            if metrics.cache_hit_rate > 90:
                score += 5
            elif metrics.cache_hit_rate > 80:
                score += 3
                
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating health score: {e}")
            return 50.0

    async def _generate_recommendations(self, metrics: SystemMetrics, 
                                      trends: Dict[str, PerformanceTrend]) -> List[Dict[str, str]]:
        """Generate performance improvement recommendations"""
        try:
            recommendations = []
            
            # CPU recommendations
            if metrics.cpu_usage > 80:
                recommendations.append({
                    "category": "performance",
                    "priority": "high" if metrics.cpu_usage > 90 else "medium",
                    "title": "High CPU Usage",
                    "description": "Consider optimizing CPU-intensive operations or scaling resources"
                })
                
            # Memory recommendations
            if metrics.memory_usage > 85:
                recommendations.append({
                    "category": "performance",
                    "priority": "high" if metrics.memory_usage > 95 else "medium",
                    "title": "High Memory Usage",
                    "description": "Review memory usage patterns and consider garbage collection optimization"
                })
                
            # Cache recommendations
            if metrics.cache_hit_rate < 70:
                recommendations.append({
                    "category": "optimization",
                    "priority": "medium",
                    "title": "Low Cache Hit Rate",
                    "description": "Optimize caching strategy or increase cache size"
                })
                
            # Response time recommendations
            if metrics.response_time_avg > 1000:
                recommendations.append({
                    "category": "performance",
                    "priority": "high",
                    "title": "Slow Response Times",
                    "description": "Investigate and optimize slow endpoints"
                })
                
            # Trend-based recommendations
            cpu_trend = trends.get("cpu_usage")
            if cpu_trend and cpu_trend.trend_direction == "increasing" and cpu_trend.change_percentage > 20:
                recommendations.append({
                    "category": "predictive",
                    "priority": "medium",
                    "title": "Rising CPU Trend",
                    "description": "CPU usage is trending upward, consider proactive optimization"
                })
                
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []

    async def start_monitoring(self, interval: int = 60):
        """Start continuous monitoring"""
        self.logger.info(f"Starting continuous monitoring with {interval}s interval")
        
        while self._monitoring_active:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self._monitoring_active = False
        self.logger.info("Monitoring stopped")

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            # Update in memory
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    break
                    
            # Update in database
            db_path = self.data_dir / "analytics.db"
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alerts SET acknowledged = TRUE WHERE alert_id = ?
                """, (alert_id,))
                conn.commit()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error acknowledging alert: {e}")
            return False

    async def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary"""
        try:
            # Get current metrics
            current_metrics = await self.collect_metrics()
            
            # Get historical summaries
            summary_data = {
                "current_status": {
                    "health_score": await self._calculate_health_score(current_metrics),
                    "cpu_usage": current_metrics.cpu_usage,
                    "memory_usage": current_metrics.memory_usage,
                    "cache_hit_rate": current_metrics.cache_hit_rate,
                    "response_time": current_metrics.response_time_avg
                },
                "24h_summary": await self._get_period_summary("24h"),
                "7d_summary": await self._get_period_summary("7d"),
                "alerts": {
                    "total": len(self.alerts),
                    "unacknowledged": len([a for a in self.alerts if not a.acknowledged]),
                    "critical": len([a for a in self.alerts if a.severity == "critical"]),
                    "recent": [asdict(a) for a in self.alerts[-5:]]
                },
                "recommendations": await self._generate_recommendations(current_metrics, {}),
                "last_updated": datetime.now().isoformat()
            }
            
            return summary_data
            
        except Exception as e:
            self.logger.error(f"Error getting analytics summary: {e}")
            return {"error": str(e)}

    async def _get_period_summary(self, period: str) -> Dict[str, Any]:
        """Get summary for a specific time period"""
        try:
            data_points = await self._get_historical_data("cpu_usage", period)
            
            if not data_points:
                return {"message": "No data available"}
                
            cpu_values = [point[1] for point in data_points]
            
            return {
                "avg_cpu": statistics.mean(cpu_values),
                "max_cpu": max(cpu_values),
                "min_cpu": min(cpu_values),
                "data_points": len(data_points)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting period summary: {e}")
            return {"error": str(e)}
