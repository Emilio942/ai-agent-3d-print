#!/usr/bin/env python3
"""
Advanced Analytics Dashboard for AI Agent 3D Print System

This module provides comprehensive real-time analytics, monitoring,
and business intelligence capabilities for the 3D printing system.
"""

import asyncio
import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import statistics
from dataclasses import dataclass, asdict
from enum import Enum

from core.logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics tracked by the analytics system"""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Represents a single metric measurement"""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat()
        }


class MetricsCollector:
    """Collects and stores system metrics in memory"""
    
    def __init__(self, db_path: str = "data/analytics.db"):
        self.logger = get_logger(f"{__name__}.MetricsCollector")
        self.db_path = db_path  # Store as instance variable
        # Use simple in-memory storage
        self.metrics_store: List[Dict[str, Any]] = []
        self.max_metrics = 1000  # Limit memory usage
        
    async def record_metric(self, metric: Metric):
        """Record a single metric in memory"""
        try:
            metric_dict = {
                "name": metric.name,
                "value": metric.value,
                "type": metric.metric_type.value,
                "tags": metric.tags,
                "timestamp": metric.timestamp.isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            self.metrics_store.append(metric_dict)
            
            # Keep only recent metrics
            if len(self.metrics_store) > self.max_metrics:
                self.metrics_store = self.metrics_store[-self.max_metrics:]
                
        except Exception as e:
            self.logger.error(f"❌ Failed to record metric {metric.name}: {e}")
    
    async def record_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Record a counter metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            tags=tags or {},
            timestamp=datetime.now()
        )
        await self.record_metric(metric)
    
    async def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            tags=tags or {},
            timestamp=datetime.now()
        )
        await self.record_metric(metric)
    
    async def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timer metric"""
        metric = Metric(
            name=name,
            value=duration_ms,
            metric_type=MetricType.TIMER,
            tags=tags or {},
            timestamp=datetime.now()
        )
        await self.record_metric(metric)
    
    async def get_metrics(self, 
                         name: str = None,
                         start_time: datetime = None,
                         end_time: datetime = None,
                         limit: int = 1000) -> List[Metric]:
        """Retrieve metrics from memory store"""
        try:
            filtered_metrics = []
            
            for metric_dict in self.metrics_store:
                # Filter by name if specified
                if name and metric_dict.get("name") != name:
                    continue
                
                # Parse timestamp for filtering
                metric_timestamp = datetime.fromisoformat(metric_dict["timestamp"])
                
                # Filter by start_time if specified
                if start_time and metric_timestamp < start_time:
                    continue
                
                # Filter by end_time if specified  
                if end_time and metric_timestamp > end_time:
                    continue
                
                # Convert back to Metric object
                metric = Metric(
                    name=metric_dict["name"],
                    value=metric_dict["value"],
                    metric_type=MetricType(metric_dict["type"]),
                    tags=metric_dict["tags"],
                    timestamp=metric_timestamp
                )
                filtered_metrics.append(metric)
            
            # Sort by timestamp descending and limit
            filtered_metrics.sort(key=lambda x: x.timestamp, reverse=True)
            return filtered_metrics[:limit]
                
        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve metrics: {e}")
            return []


class AnalyticsDashboard:
    """Advanced analytics dashboard for the 3D printing system"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.AnalyticsDashboard")
        self.metrics_collector = MetricsCollector()
        self.start_time = datetime.now()
        
        # System metrics tracking
        self.print_jobs_total = 0
        self.print_jobs_success = 0
        self.print_jobs_failed = 0
        self.image_conversions_total = 0
        self.voice_commands_total = 0
        self.api_requests_total = 0
        
    async def record_print_job_started(self, job_id: str, user_request: str):
        """Record when a print job starts"""
        await self.metrics_collector.record_counter(
            "print_jobs_started", 
            tags={
                "job_id": job_id,
                "request_type": "text" if user_request else "image"
            }
        )
        self.print_jobs_total += 1
    
    async def record_print_job_completed(self, job_id: str, success: bool, duration_ms: float):
        """Record when a print job completes"""
        status = "success" if success else "failed"
        
        await self.metrics_collector.record_counter(
            f"print_jobs_{status}",
            tags={"job_id": job_id}
        )
        
        await self.metrics_collector.record_timer(
            "print_job_duration",
            duration_ms,
            tags={"job_id": job_id, "status": status}
        )
        
        if success:
            self.print_jobs_success += 1
        else:
            self.print_jobs_failed += 1
    
    async def record_image_conversion(self, 
                                    conversion_time_ms: float, 
                                    file_size_bytes: int,
                                    format: str,
                                    style: str):
        """Record image-to-3D conversion metrics"""
        await self.metrics_collector.record_timer(
            "image_conversion_duration",
            conversion_time_ms,
            tags={"format": format, "style": style}
        )
        
        await self.metrics_collector.record_gauge(
            "image_conversion_file_size",
            file_size_bytes,
            tags={"format": format}
        )
        
        await self.metrics_collector.record_counter(
            "image_conversions_total",
            tags={"format": format, "style": style}
        )
        
        self.image_conversions_total += 1
    
    async def record_voice_command(self, intent: str, success: bool, confidence: float):
        """Record voice command metrics"""
        status = "success" if success else "failed"
        
        await self.metrics_collector.record_counter(
            f"voice_commands_{status}",
            tags={"intent": intent}
        )
        
        await self.metrics_collector.record_gauge(
            "voice_command_confidence",
            confidence,
            tags={"intent": intent, "status": status}
        )
        
        self.voice_commands_total += 1
    
    async def record_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Record API request metrics"""
        await self.metrics_collector.record_counter(
            "api_requests_total",
            tags={
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code)
            }
        )
        
        await self.metrics_collector.record_timer(
            "api_request_duration",
            duration_ms,
            tags={
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code)
            }
        )
        
        self.api_requests_total += 1
    
    async def record_system_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a general system metric"""
        await self.metrics_collector.record_gauge(name, value, tags)
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get a comprehensive dashboard summary"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)
        
        try:
            # Get recent metrics
            recent_metrics = await self.metrics_collector.get_metrics(
                start_time=last_24h,
                limit=10000
            )
            
            # Calculate key performance indicators
            kpis = await self._calculate_kpis(recent_metrics, last_24h, now)
            
            # Generate charts data
            charts = await self._generate_charts_data(recent_metrics, last_24h, now)
            
            # System health
            health = await self._assess_system_health(recent_metrics)
            
            return {
                "timestamp": now.isoformat(),
                "uptime_hours": (now - self.start_time).total_seconds() / 3600,
                "kpis": kpis,
                "charts": charts,
                "health": health,
                "recent_activity": await self._get_recent_activity(),
                "alerts": await self._check_alerts(recent_metrics)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate dashboard summary: {e}")
            return {"error": str(e)}
    
    async def _calculate_kpis(self, metrics: List[Metric], start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate key performance indicators"""
        
        # Print job metrics
        print_jobs_started = len([m for m in metrics if m.name == "print_jobs_started"])
        print_jobs_success = len([m for m in metrics if m.name == "print_jobs_success"])
        print_jobs_failed = len([m for m in metrics if m.name == "print_jobs_failed"])
        
        success_rate = (print_jobs_success / max(print_jobs_started, 1)) * 100
        
        # Image conversion metrics
        image_conversions = len([m for m in metrics if m.name == "image_conversions_total"])
        
        # Voice command metrics
        voice_commands = len([m for m in metrics if m.name.startswith("voice_commands_")])
        voice_success = len([m for m in metrics if m.name == "voice_commands_success"])
        voice_success_rate = (voice_success / max(voice_commands, 1)) * 100
        
        # API metrics
        api_requests = len([m for m in metrics if m.name == "api_requests_total"])
        
        # Performance metrics
        conversion_times = [m.value for m in metrics if m.name == "image_conversion_duration"]
        avg_conversion_time = statistics.mean(conversion_times) if conversion_times else 0
        
        api_times = [m.value for m in metrics if m.name == "api_request_duration"]
        avg_api_time = statistics.mean(api_times) if api_times else 0
        
        return {
            "print_jobs": {
                "total": print_jobs_started,
                "success": print_jobs_success,
                "failed": print_jobs_failed,
                "success_rate": round(success_rate, 1)
            },
            "conversions": {
                "total": image_conversions,
                "avg_time_ms": round(avg_conversion_time, 1)
            },
            "voice_commands": {
                "total": voice_commands,
                "success_rate": round(voice_success_rate, 1)
            },
            "api": {
                "total_requests": api_requests,
                "avg_response_time_ms": round(avg_api_time, 1)
            }
        }
    
    async def _generate_charts_data(self, metrics: List[Metric], start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate data for dashboard charts"""
        
        # Time series data for last 24 hours (hourly buckets)
        hours = []
        current = start_time.replace(minute=0, second=0, microsecond=0)
        
        while current <= end_time:
            hours.append(current)
            current += timedelta(hours=1)
        
        # Print jobs over time
        print_jobs_chart = []
        for hour in hours:
            hour_end = hour + timedelta(hours=1)
            hour_jobs = len([
                m for m in metrics 
                if m.name == "print_jobs_started" and hour <= m.timestamp < hour_end
            ])
            print_jobs_chart.append({
                "time": hour.strftime("%H:00"),
                "value": hour_jobs
            })
        
        # Conversion times histogram
        conversion_times = [m.value for m in metrics if m.name == "image_conversion_duration"]
        conversion_histogram = self._create_histogram(conversion_times, bins=10)
        
        # Success rate pie chart
        success_pie = [
            {"label": "Success", "value": self.print_jobs_success},
            {"label": "Failed", "value": self.print_jobs_failed}
        ]
        
        return {
            "print_jobs_timeline": print_jobs_chart,
            "conversion_time_histogram": conversion_histogram,
            "success_rate_pie": success_pie,
            "activity_heatmap": await self._generate_activity_heatmap(metrics)
        }
    
    def _create_histogram(self, values: List[float], bins: int = 10) -> List[Dict[str, Any]]:
        """Create histogram data from values"""
        if not values:
            return []
        
        min_val, max_val = min(values), max(values)
        bin_size = (max_val - min_val) / bins
        
        histogram = []
        for i in range(bins):
            bin_start = min_val + i * bin_size
            bin_end = bin_start + bin_size
            count = len([v for v in values if bin_start <= v < bin_end])
            
            histogram.append({
                "range": f"{bin_start:.1f}-{bin_end:.1f}",
                "count": count
            })
        
        return histogram
    
    async def _generate_activity_heatmap(self, metrics: List[Metric]) -> List[Dict[str, Any]]:
        """Generate activity heatmap data"""
        activity = {}
        
        for metric in metrics:
            hour = metric.timestamp.hour
            day = metric.timestamp.strftime("%A")
            
            key = f"{day}_{hour}"
            activity[key] = activity.get(key, 0) + 1
        
        heatmap = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day in days:
            for hour in range(24):
                key = f"{day}_{hour}"
                heatmap.append({
                    "day": day,
                    "hour": hour,
                    "activity": activity.get(key, 0)
                })
        
        return heatmap
    
    async def _assess_system_health(self, metrics: List[Metric]) -> Dict[str, Any]:
        """Assess overall system health"""
        
        # Calculate health score based on various factors
        health_score = 100
        issues = []
        
        # Check error rates
        total_jobs = len([m for m in metrics if m.name == "print_jobs_started"])
        failed_jobs = len([m for m in metrics if m.name == "print_jobs_failed"])
        
        if total_jobs > 0:
            error_rate = (failed_jobs / total_jobs) * 100
            if error_rate > 10:
                health_score -= 20
                issues.append(f"High error rate: {error_rate:.1f}%")
        
        # Check API response times
        api_times = [m.value for m in metrics if m.name == "api_request_duration"]
        if api_times:
            avg_response_time = statistics.mean(api_times)
            if avg_response_time > 1000:  # More than 1 second
                health_score -= 15
                issues.append(f"Slow API responses: {avg_response_time:.0f}ms avg")
        
        # Check conversion times
        conversion_times = [m.value for m in metrics if m.name == "image_conversion_duration"]
        if conversion_times:
            avg_conversion_time = statistics.mean(conversion_times)
            if avg_conversion_time > 5000:  # More than 5 seconds
                health_score -= 10
                issues.append(f"Slow conversions: {avg_conversion_time:.0f}ms avg")
        
        # Determine overall status
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 60:
            status = "fair"
        else:
            status = "poor"
        
        return {
            "score": max(0, health_score),
            "status": status,
            "issues": issues,
            "last_check": datetime.now().isoformat()
        }
    
    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent system activity"""
        recent_metrics = await self.metrics_collector.get_metrics(limit=20)
        
        activity = []
        for metric in recent_metrics[:10]:  # Last 10 activities
            activity.append({
                "timestamp": metric.timestamp.isoformat(),
                "type": metric.name,
                "value": metric.value,
                "tags": metric.tags
            })
        
        return activity
    
    async def _check_alerts(self, metrics: List[Metric]) -> List[Dict[str, Any]]:
        """Check for system alerts"""
        alerts = []
        
        # Check for high error rates in last hour
        last_hour = datetime.now() - timedelta(hours=1)
        recent_metrics = [m for m in metrics if m.timestamp >= last_hour]
        
        failed_jobs = len([m for m in recent_metrics if m.name == "print_jobs_failed"])
        if failed_jobs > 3:
            alerts.append({
                "level": "warning",
                "message": f"{failed_jobs} print jobs failed in the last hour",
                "timestamp": datetime.now().isoformat()
            })
        
        # Check for slow API responses
        api_times = [m.value for m in recent_metrics if m.name == "api_request_duration"]
        if api_times and statistics.mean(api_times) > 2000:
            alerts.append({
                "level": "warning",
                "message": "API response times are slower than normal",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
    
    async def get_overview(self) -> Dict[str, Any]:
        """Get comprehensive analytics overview"""
        return await self.get_dashboard_summary()
    
    async def get_live_metrics(self) -> Dict[str, Any]:
        """Get real-time system metrics"""
        try:
            # Get recent metrics from the last hour
            last_hour = datetime.now() - timedelta(hours=1)
            recent_metrics = await self.metrics_collector.get_metrics(
                start_time=last_hour,
                limit=100
            )
            
            # Process live metrics
            live_data = {
                "timestamp": datetime.now().isoformat(),
                "active_jobs": self.print_jobs_total - self.print_jobs_success - self.print_jobs_failed,
                "total_jobs": self.print_jobs_total,
                "success_rate": (self.print_jobs_success / max(1, self.print_jobs_total)) * 100,
                "api_requests_per_minute": len([m for m in recent_metrics if m.name == "api_requests_total" and m.timestamp >= datetime.now() - timedelta(minutes=1)]),
                "average_conversion_time": 0,
                "system_load": {
                    "cpu_usage": 45.2,  # Mock data - could be replaced with actual system metrics
                    "memory_usage": 62.8,
                    "disk_usage": 23.1
                }
            }
            
            # Calculate average conversion time
            conversion_times = [m.value for m in recent_metrics if m.name == "image_conversion_duration"]
            if conversion_times:
                live_data["average_conversion_time"] = statistics.mean(conversion_times)
            
            return live_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get live metrics: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": "Failed to retrieve live metrics",
                "active_jobs": 0,
                "total_jobs": 0,
                "success_rate": 0,
                "api_requests_per_minute": 0,
                "average_conversion_time": 0,
                "system_load": {
                    "cpu_usage": 0,
                    "memory_usage": 0,
                    "disk_usage": 0
                }
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            # Get recent metrics for health assessment
            last_24h = datetime.now() - timedelta(hours=24)
            recent_metrics = await self.metrics_collector.get_metrics(
                start_time=last_24h,
                limit=1000
            )
            
            # Assess system health
            health_data = await self._assess_system_health(recent_metrics)
            
            # Add additional health indicators
            health_data.update({
                "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
                "total_print_jobs": self.print_jobs_total,
                "successful_jobs": self.print_jobs_success,
                "failed_jobs": self.print_jobs_failed,
                "image_conversions": self.image_conversions_total,
                "voice_commands": self.voice_commands_total,
                "api_requests": self.api_requests_total,
                "alerts": await self._check_alerts(recent_metrics)
            })
            
            return health_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get system health: {e}")
            return {
                "score": 0,
                "status": "error",
                "issues": ["Failed to retrieve system health data"],
                "last_check": datetime.now().isoformat(),
                "uptime_hours": 0,
                "total_print_jobs": 0,
                "successful_jobs": 0,
                "failed_jobs": 0,
                "image_conversions": 0,
                "voice_commands": 0,
                "api_requests": 0,
                "alerts": []
            }
