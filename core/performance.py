"""
Performance Enhancement Module for AI Agent 3D Print System

This module provides performance optimizations including:
- Multi-level caching system
- Resource management and monitoring
- Database optimization
- Response compression
- Async job processing
"""

import asyncio
import psutil
import time
import hashlib
import pickle
import gzip
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from contextlib import asynccontextmanager

from core.logger import get_logger

logger = get_logger(__name__)


class CacheLevel(Enum):
    """Cache level enumeration"""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"


@dataclass
class CacheEntry:
    """Cache entry data structure"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0


@dataclass
class ResourceLimits:
    """Resource limits configuration"""
    max_memory_per_request: int = 500 * 1024 * 1024  # 500MB
    max_cpu_time: int = 30  # 30 seconds
    max_concurrent_jobs: int = 10
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_connections: int = 1000
    memory_warning_threshold: float = 0.8  # 80%
    cpu_warning_threshold: float = 0.8  # 80%


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    response_time: float
    memory_usage: float
    cpu_usage: float
    active_connections: int
    cache_hit_rate: float
    error_rate: float


class MultiLevelCache:
    """Multi-level caching system with automatic optimization"""
    
    def __init__(self, max_memory_size: int = 100 * 1024 * 1024):  # 100MB default
        self.max_memory_size = max_memory_size
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size': 0
        }
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes"""
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode('utf-8'))
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _evict_lru(self):
        """Evict least recently used items when cache is full"""
        if not self.memory_cache:
            return
        
        # Sort by last accessed time
        sorted_entries = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest 25% of entries
        evict_count = max(1, len(sorted_entries) // 4)
        for i in range(evict_count):
            key, entry = sorted_entries[i]
            self.cache_stats['total_size'] -= entry.size_bytes
            del self.memory_cache[key]
            self.cache_stats['evictions'] += 1
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            
            # Check expiration
            if entry.expires_at and datetime.now() > entry.expires_at:
                await self.delete(key)
                self.cache_stats['misses'] += 1
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self.cache_stats['hits'] += 1
            
            return entry.value
        
        self.cache_stats['misses'] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds"""
        try:
            size_bytes = self._calculate_size(value)
            
            # Check if cache is getting too large
            if self.cache_stats['total_size'] + size_bytes > self.max_memory_size:
                self._evict_lru()
            
            expires_at = None
            if ttl:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes
            )
            
            # Remove old entry if exists
            if key in self.memory_cache:
                self.cache_stats['total_size'] -= self.memory_cache[key].size_bytes
            
            self.memory_cache[key] = entry
            self.cache_stats['total_size'] += size_bytes
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            self.cache_stats['total_size'] -= entry.size_bytes
            del self.memory_cache[key]
            return True
        return False
    
    async def clear(self):
        """Clear all cache entries"""
        self.memory_cache.clear()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size': 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hit_rate': hit_rate,
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'evictions': self.cache_stats['evictions'],
            'total_size_mb': self.cache_stats['total_size'] / (1024 * 1024),
            'entry_count': len(self.memory_cache),
            'max_size_mb': self.max_memory_size / (1024 * 1024)
        }


class ResourceManager:
    """Resource management and monitoring system"""
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.resource_usage_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
    def _get_system_stats(self) -> Dict[str, float]:
        """Get current system resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'active_connections': len(self.active_jobs)
        }
    
    async def check_resource_availability(self, 
                                        resource_type: str,
                                        estimated_memory: int = 0,
                                        estimated_cpu_time: int = 0) -> Dict[str, Any]:
        """Check if resources are available for a new request"""
        system_stats = self._get_system_stats()
        
        availability = {
            'memory_available': True,
            'cpu_available': True,
            'connections_available': True,
            'overall_available': True,
            'warnings': []
        }
        
        # Check memory
        if system_stats['memory_percent'] > self.limits.memory_warning_threshold * 100:
            availability['memory_available'] = False
            availability['warnings'].append(f"High memory usage: {system_stats['memory_percent']:.1f}%")
        
        # Check CPU
        if system_stats['cpu_percent'] > self.limits.cpu_warning_threshold * 100:
            availability['cpu_available'] = False
            availability['warnings'].append(f"High CPU usage: {system_stats['cpu_percent']:.1f}%")
        
        # Check concurrent jobs
        if len(self.active_jobs) >= self.limits.max_concurrent_jobs:
            availability['connections_available'] = False
            availability['warnings'].append(f"Max concurrent jobs reached: {len(self.active_jobs)}")
        
        # Overall availability
        availability['overall_available'] = all([
            availability['memory_available'],
            availability['cpu_available'],
            availability['connections_available']
        ])
        
        return availability
    
    @asynccontextmanager
    async def allocate_resources(self, request_id: str, resource_type: str):
        """Context manager for resource allocation"""
        start_time = time.time()
        
        # Check availability
        availability = await self.check_resource_availability(resource_type)
        if not availability['overall_available']:
            raise ResourceError(f"Resources not available: {availability['warnings']}")
        
        # Allocate resources
        self.active_jobs[request_id] = {
            'resource_type': resource_type,
            'start_time': start_time,
            'allocated_memory': 0,
            'status': 'active'
        }
        
        try:
            logger.info(f"Resources allocated for {request_id}")
            yield
            
        finally:
            # Release resources
            if request_id in self.active_jobs:
                end_time = time.time()
                duration = end_time - start_time
                
                # Log resource usage
                usage_stats = {
                    'request_id': request_id,
                    'resource_type': resource_type,
                    'duration': duration,
                    'timestamp': datetime.now(),
                    **self._get_system_stats()
                }
                
                self.resource_usage_history.append(usage_stats)
                
                # Trim history if too large
                if len(self.resource_usage_history) > self.max_history_size:
                    self.resource_usage_history = self.resource_usage_history[-self.max_history_size:]
                
                del self.active_jobs[request_id]
                logger.info(f"Resources released for {request_id} after {duration:.2f}s")
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics"""
        current_stats = self._get_system_stats()
        
        return {
            'current': current_stats,
            'active_jobs': len(self.active_jobs),
            'limits': {
                'max_concurrent_jobs': self.limits.max_concurrent_jobs,
                'memory_warning_threshold': self.limits.memory_warning_threshold,
                'cpu_warning_threshold': self.limits.cpu_warning_threshold
            },
            'history_count': len(self.resource_usage_history)
        }


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 10000
        self.alert_thresholds = {
            'response_time': 1.0,  # 1 second
            'memory_usage': 0.85,  # 85%
            'cpu_usage': 0.85,  # 85%
            'error_rate': 0.05  # 5%
        }
        self.alerts_enabled = True
    
    async def record_metrics(self, 
                           response_time: float,
                           memory_usage: float,
                           cpu_usage: float,
                           active_connections: int,
                           cache_hit_rate: float,
                           error_rate: float):
        """Record performance metrics"""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            response_time=response_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            active_connections=active_connections,
            cache_hit_rate=cache_hit_rate,
            error_rate=error_rate
        )
        
        self.metrics_history.append(metrics)
        
        # Trim history if too large
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        # Check for alerts
        if self.alerts_enabled:
            await self._check_alerts(metrics)
    
    async def _check_alerts(self, metrics: PerformanceMetrics):
        """Check metrics against alert thresholds"""
        alerts = []
        
        if metrics.response_time > self.alert_thresholds['response_time']:
            alerts.append(f"High response time: {metrics.response_time:.3f}s")
        
        if metrics.memory_usage > self.alert_thresholds['memory_usage']:
            alerts.append(f"High memory usage: {metrics.memory_usage:.1%}")
        
        if metrics.cpu_usage > self.alert_thresholds['cpu_usage']:
            alerts.append(f"High CPU usage: {metrics.cpu_usage:.1%}")
        
        if metrics.error_rate > self.alert_thresholds['error_rate']:
            alerts.append(f"High error rate: {metrics.error_rate:.1%}")
        
        for alert in alerts:
            logger.warning(f"Performance alert: {alert}")
    
    def get_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get performance summary for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {'message': 'No recent metrics available'}
        
        avg_response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics)
        avg_memory_usage = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_cpu_usage = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        
        return {
            'time_period_minutes': minutes,
            'sample_count': len(recent_metrics),
            'averages': {
                'response_time': avg_response_time,
                'memory_usage': avg_memory_usage,
                'cpu_usage': avg_cpu_usage,
                'cache_hit_rate': avg_cache_hit_rate,
                'error_rate': avg_error_rate
            },
            'latest': {
                'response_time': recent_metrics[-1].response_time,
                'memory_usage': recent_metrics[-1].memory_usage,
                'cpu_usage': recent_metrics[-1].cpu_usage,
                'active_connections': recent_metrics[-1].active_connections
            }
        }


class ResponseCompressor:
    """Response compression utility"""
    
    @staticmethod
    def should_compress(content_type: str, content_length: int) -> bool:
        """Determine if response should be compressed"""
        # Compress text-based content types over 1KB
        compressible_types = [
            'application/json',
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'text/plain',
            'application/xml'
        ]
        
        return (
            any(ct in content_type for ct in compressible_types) and
            content_length > 1024  # 1KB threshold
        )
    
    @staticmethod
    def compress_content(content: bytes) -> bytes:
        """Compress content using gzip"""
        return gzip.compress(content)


# Custom exceptions
class ResourceError(Exception):
    """Resource allocation error"""
    pass


class PerformanceError(Exception):
    """Performance-related error"""
    pass


# Global instances
cache = MultiLevelCache()
resource_manager = ResourceManager()
performance_monitor = PerformanceMonitor()
compressor = ResponseCompressor()

# Cache decorator for functions
def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = await cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator


__all__ = [
    'CacheLevel',
    'CacheEntry',
    'ResourceLimits',
    'PerformanceMetrics',
    'MultiLevelCache',
    'ResourceManager',
    'PerformanceMonitor',
    'ResponseCompressor',
    'ResourceError',
    'PerformanceError',
    'cache',
    'resource_manager',
    'performance_monitor',
    'compressor',
    'cached'
]
