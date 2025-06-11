"""
Health Monitoring System for AI Agent 3D Print System

This module provides comprehensive health monitoring capabilities for all
system components including agents, services, and infrastructure.
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from enum import Enum

from config.settings import load_config
from core.logger import get_logger


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a system component."""
    name: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class SystemMetrics:
    """System-wide metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    load_average: float
    uptime_seconds: float
    network_connections: int
    active_threads: int


class HealthMonitor:
    """
    Comprehensive health monitoring for all system components.
    """
    
    def __init__(self):
        self.config = load_config()
        self.logger = get_logger("health_monitor")
        self.components: Dict[str, ComponentHealth] = {}
        self.system_start_time = datetime.now()
        self._monitoring_active = False
        
    def register_component(self, name: str) -> None:
        """Register a component for health monitoring."""
        self.components[name] = ComponentHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            last_check=datetime.now(),
            response_time_ms=0.0
        )
        self.logger.info(f"Registered component for monitoring: {name}")
    
    async def check_component_health(self, name: str, health_check_func=None) -> ComponentHealth:
        """
        Check health of a specific component.
        
        Args:
            name: Component name
            health_check_func: Optional custom health check function
            
        Returns:
            ComponentHealth object with current status
        """
        start_time = time.time()
        
        try:
            if health_check_func:
                # Use custom health check function
                is_healthy = await health_check_func()
                status = HealthStatus.HEALTHY if is_healthy else HealthStatus.DEGRADED
                error_message = None
            else:
                # Default health check based on component type
                status, error_message = await self._default_health_check(name)
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            health = ComponentHealth(
                name=name,
                status=status,
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_message=error_message
            )
            
            self.components[name] = health
            return health
            
        except Exception as e:
            self.logger.error(f"Health check failed for {name}: {e}")
            error_health = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
            self.components[name] = error_health
            return error_health
    
    async def _default_health_check(self, name: str) -> tuple[HealthStatus, Optional[str]]:
        """Default health check implementation for different components."""
        
        if name == "database":
            return await self._check_database_health()
        elif name == "redis":
            return await self._check_redis_health()
        elif name == "file_system":
            return await self._check_file_system_health()
        elif name.endswith("_agent"):
            return await self._check_agent_health(name)
        elif name == "api":
            return await self._check_api_health()
        else:
            return HealthStatus.UNKNOWN, f"No health check defined for {name}"
    
    async def _check_database_health(self) -> tuple[HealthStatus, Optional[str]]:
        """Check database connectivity and performance."""
        try:
            db_config = self.config.get('database', {})
            db_url = db_config.get('url', '')
            
            if db_url.startswith('sqlite'):
                # Check SQLite file accessibility
                if ':///' in db_url:
                    db_path = Path(db_url.split(':///', 1)[1])
                    if db_path.parent.exists():
                        return HealthStatus.HEALTHY, None
                    else:
                        return HealthStatus.UNHEALTHY, "Database directory not accessible"
                        
            elif db_url.startswith('postgresql'):
                # For PostgreSQL, we'd need actual connection check
                # This is a simplified check
                return HealthStatus.HEALTHY, None
                
            return HealthStatus.UNKNOWN, "Unsupported database type"
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Database check failed: {e}"
    
    async def _check_redis_health(self) -> tuple[HealthStatus, Optional[str]]:
        """Check Redis connectivity and performance."""
        try:
            # This would require actual Redis connection in production
            # For now, we check if Redis configuration is valid
            cache_config = self.config.get('cache', {})
            if cache_config.get('type') == 'redis':
                redis_url = cache_config.get('redis_url')
                if redis_url:
                    return HealthStatus.HEALTHY, None
                else:
                    return HealthStatus.DEGRADED, "Redis URL not configured"
            else:
                return HealthStatus.HEALTHY, "Redis not in use"
                
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Redis check failed: {e}"
    
    async def _check_file_system_health(self) -> tuple[HealthStatus, Optional[str]]:
        """Check file system health and disk space."""
        try:
            # Check critical directories
            critical_dirs = ['logs', 'data', 'config']
            for dir_name in critical_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    return HealthStatus.DEGRADED, f"Critical directory missing: {dir_name}"
                    
            # Check disk space
            disk_usage = psutil.disk_usage('.')
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            if usage_percent > 95:
                return HealthStatus.UNHEALTHY, f"Disk space critical: {usage_percent:.1f}% used"
            elif usage_percent > 80:
                return HealthStatus.DEGRADED, f"Disk space warning: {usage_percent:.1f}% used"
            else:
                return HealthStatus.HEALTHY, None
                
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"File system check failed: {e}"
    
    async def _check_agent_health(self, agent_name: str) -> tuple[HealthStatus, Optional[str]]:
        """Check agent health status."""
        try:
            # In a full implementation, this would check if agents are responsive
            # For now, we check configuration and basic availability
            agent_config = self.config.get('agents', {}).get(agent_name.replace('_agent', ''), {})
            
            if not agent_config.get('enabled', True):
                return HealthStatus.DEGRADED, f"Agent {agent_name} is disabled"
            
            # Check if agent is in mock mode
            if agent_config.get('mock_mode', False):
                return HealthStatus.HEALTHY, f"Agent {agent_name} running in mock mode"
            else:
                return HealthStatus.HEALTHY, None
                
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Agent {agent_name} check failed: {e}"
    
    async def _check_api_health(self) -> tuple[HealthStatus, Optional[str]]:
        """Check API server health."""
        try:
            # Check if API configuration is valid
            api_config = self.config.get('api', {})
            required_fields = ['host', 'port']
            
            for field in required_fields:
                if not api_config.get(field):
                    return HealthStatus.DEGRADED, f"API configuration missing: {field}"
            
            return HealthStatus.HEALTHY, None
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"API check failed: {e}"
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            
            # Load average (Unix systems)
            try:
                load_avg = psutil.getloadavg()[0]
            except AttributeError:
                load_avg = 0.0  # Windows doesn't have load average
            
            # Uptime
            uptime = (datetime.now() - self.system_start_time).total_seconds()
            
            # Network connections
            net_connections = len(psutil.net_connections())
            
            # Active threads
            process = psutil.Process()
            active_threads = process.num_threads()
            
            return SystemMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory_percent,
                disk_usage_percent=disk_percent,
                load_average=load_avg,
                uptime_seconds=uptime,
                network_connections=net_connections,
                active_threads=active_threads
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return SystemMetrics(
                cpu_usage_percent=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
                load_average=0.0,
                uptime_seconds=0.0,
                network_connections=0,
                active_threads=0
            )
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        # Check all registered components
        component_checks = []
        for component_name in self.components.keys():
            component_checks.append(self.check_component_health(component_name))
        
        if component_checks:
            await asyncio.gather(*component_checks, return_exceptions=True)
        
        # Determine overall status
        statuses = [comp.status for comp in self.components.values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        # Get system metrics
        system_metrics = self.get_system_metrics()
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "system_metrics": asdict(system_metrics),
            "components": {name: asdict(comp) for name, comp in self.components.items()},
            "uptime_seconds": system_metrics.uptime_seconds
        }
    
    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start continuous health monitoring."""
        self.logger.info(f"Starting health monitoring with {interval_seconds}s interval")
        self._monitoring_active = True
        
        while self._monitoring_active:
            try:
                health_report = await self.get_overall_health()
                
                # Log health status
                overall_status = health_report["overall_status"]
                if overall_status == HealthStatus.UNHEALTHY:
                    self.logger.error(f"System health: {overall_status}")
                elif overall_status == HealthStatus.DEGRADED:
                    self.logger.warning(f"System health: {overall_status}")
                else:
                    self.logger.info(f"System health: {overall_status}")
                
                # Check for alerts
                await self._check_alerts(health_report)
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    async def _check_alerts(self, health_report: Dict[str, Any]) -> None:
        """Check if any alerts should be triggered."""
        monitoring_config = self.config.get('monitoring', {})
        alerting_config = monitoring_config.get('alerting', {})
        
        if not alerting_config.get('enabled', False):
            return
        
        thresholds = alerting_config.get('thresholds', {})
        metrics = health_report["system_metrics"]
        
        alerts = []
        
        # Check CPU usage
        if metrics["cpu_usage_percent"] > thresholds.get("cpu_usage", 85):
            alerts.append(f"High CPU usage: {metrics['cpu_usage_percent']:.1f}%")
        
        # Check memory usage
        if metrics["memory_usage_percent"] > thresholds.get("memory_usage", 80):
            alerts.append(f"High memory usage: {metrics['memory_usage_percent']:.1f}%")
        
        # Check disk usage
        if metrics["disk_usage_percent"] > thresholds.get("disk_usage", 90):
            alerts.append(f"High disk usage: {metrics['disk_usage_percent']:.1f}%")
        
        # Check component health
        unhealthy_components = [
            name for name, comp in health_report["components"].items()
            if comp["status"] == HealthStatus.UNHEALTHY
        ]
        
        if unhealthy_components:
            alerts.append(f"Unhealthy components: {', '.join(unhealthy_components)}")
        
        # Send alerts if any
        if alerts:
            await self._send_alerts(alerts)
    
    async def _send_alerts(self, alerts: List[str]) -> None:
        """Send alerts via configured channels."""
        self.logger.warning(f"ALERTS: {'; '.join(alerts)}")
        
        # In production, this would send alerts via:
        # - Webhook
        # - Email
        # - Slack/Discord
        # - SMS
        # etc.
    
    def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        self.logger.info("Stopping health monitoring")
        self._monitoring_active = False


# Global health monitor instance
health_monitor = HealthMonitor()


async def setup_default_monitoring() -> None:
    """Setup default health monitoring for common components."""
    # Register default components
    health_monitor.register_component("api")
    health_monitor.register_component("database")
    health_monitor.register_component("redis")
    health_monitor.register_component("file_system")
    health_monitor.register_component("research_agent")
    health_monitor.register_component("cad_agent")
    health_monitor.register_component("slicer_agent")
    health_monitor.register_component("printer_agent")
    
    # Perform initial health check
    await health_monitor.get_overall_health()
