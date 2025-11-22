"""
Performance Middleware for FastAPI Application

This module provides performance middleware for the AI Agent 3D Print System,
integrating performance monitoring, caching, and optimization features.
"""

import time
import asyncio
import psutil
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.performance import (
    cache, resource_manager, performance_monitor, compressor
)
from core.logger import get_logger

logger = get_logger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Performance monitoring and optimization middleware"""
    
    def __init__(self, app, enable_compression: bool = True, enable_caching: bool = True):
        super().__init__(app)
        self.enable_compression = enable_compression
        self.enable_caching = enable_caching
        self.request_counter = 0
        self.error_counter = 0
        self._last_cpu_usage = 0.0
        self._cpu_update_task = None
        
        # Start background CPU monitoring
        self._start_cpu_monitoring()
    
    def _start_cpu_monitoring(self):
        """Start background task to monitor CPU usage efficiently"""
        async def update_cpu():
            while True:
                # Update CPU usage every 2 seconds in background
                self._last_cpu_usage = psutil.cpu_percent(interval=1)
                await asyncio.sleep(1)
        
        # Note: This will be started when the app starts up
        # For now, we'll use on-demand measurement with a small interval
        pass
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Main middleware dispatch method"""
        start_time = time.time()
        self.request_counter += 1
        
        # Get initial system stats (removed CPU check to avoid blocking)
        initial_memory = psutil.virtual_memory().percent
        
        try:
            # Check if this is a cacheable GET request
            cache_key = None
            if self.enable_caching and request.method == "GET":
                cache_key = f"response:{request.url.path}:{str(request.query_params)}"
                cached_response = await cache.get(cache_key)
                if cached_response:
                    # Return cached response
                    processing_time = time.time() - start_time
                    logger.info(f"Cache hit for {request.url.path} in {processing_time:.3f}s")
                    
                    response = Response(
                        content=cached_response['content'],
                        status_code=cached_response['status_code'],
                        headers=cached_response['headers']
                    )
                    response.headers["X-Cache"] = "HIT"
                    response.headers["X-Process-Time"] = str(processing_time)
                    return response
            
            # Process request
            response = await call_next(request)
            
            # Calculate performance metrics
            processing_time = time.time() - start_time
            final_memory = psutil.virtual_memory().percent
            # Use cached CPU value to avoid blocking - more efficient
            final_cpu = self._last_cpu_usage if self._last_cpu_usage > 0 else psutil.cpu_percent(interval=0)
            
            # Add performance headers
            response.headers["X-Process-Time"] = str(processing_time)
            response.headers["X-Memory-Usage"] = f"{final_memory:.1f}%"
            response.headers["X-CPU-Usage"] = f"{final_cpu:.1f}%"
            
            # Handle compression
            if self.enable_compression and response.status_code == 200:
                response = await self._maybe_compress_response(request, response)
            
            # Cache successful GET responses (temporarily disabled to avoid middleware conflicts)
            if (False and self.enable_caching and 
                request.method == "GET" and 
                response.status_code == 200 and 
                cache_key):
                
                # Cache response for 5 minutes
                response = await self._cache_response(cache_key, response)
            
            # Record performance metrics
            await self._record_performance_metrics(
                processing_time, final_memory, final_cpu, response.status_code
            )
            
            # Log performance info
            if processing_time > 1.0:  # Log slow requests
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {processing_time:.3f}s"
                )
            else:
                logger.info(
                    f"Request: {request.method} {request.url.path} "
                    f"completed in {processing_time:.3f}s"
                )
            
            return response
            
        except Exception as e:
            self.error_counter += 1
            processing_time = time.time() - start_time
            
            logger.error(f"Performance middleware error: {e}")
            
            # Record error metrics
            await self._record_performance_metrics(
                processing_time, 
                psutil.virtual_memory().percent,
                self._last_cpu_usage if self._last_cpu_usage > 0 else psutil.cpu_percent(interval=0),
                500
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "performance_middleware_error",
                    "message": "An error occurred during performance processing"
                }
            )
    
    async def _maybe_compress_response(self, request: Request, response: Response) -> Response:
        """Compress response if beneficial"""
        try:
            # Check if client accepts gzip
            accept_encoding = request.headers.get("accept-encoding", "")
            if "gzip" not in accept_encoding.lower():
                return response
            
            # Get response content
            content = b""
            async for chunk in response.body_iterator:
                content += chunk
            
            content_type = response.headers.get("content-type", "")
            content_length = len(content)
            
            # Check if compression is beneficial
            if compressor.should_compress(content_type, content_length):
                compressed_content = compressor.compress_content(content)
                compression_ratio = len(compressed_content) / content_length
                
                # Only use compression if it saves significant space
                if compression_ratio < 0.9:  # At least 10% reduction
                    response.headers["content-encoding"] = "gzip"
                    response.headers["content-length"] = str(len(compressed_content))
                    response.headers["X-Compression-Ratio"] = f"{compression_ratio:.2f}"
                    
                    # Create new response with compressed content
                    return Response(
                        content=compressed_content,
                        status_code=response.status_code,
                        headers=response.headers,
                        media_type=response.media_type
                    )
            
            # Return original response if compression not beneficial
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type
            )
            
        except Exception as e:
            logger.error(f"Compression error: {e}")
            return response
    
    async def _cache_response(self, cache_key: str, response: Response):
        """Cache response for future requests"""
        try:
            # Only cache JSON responses to avoid binary content issues
            if response.headers.get("content-type", "").startswith("application/json"):
                # Get response content
                content = b""
                if hasattr(response, 'body_iterator'):
                    async for chunk in response.body_iterator:
                        content += chunk
                else:
                    # Handle already consumed responses
                    return response
                
                # Prepare cache data
                cache_data = {
                    'content': content.decode('utf-8') if content else "",
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                }
                
                # Cache for 5 minutes (300 seconds)
                await cache.set(cache_key, cache_data, ttl=300)
                response.headers["X-Cache"] = "MISS"
                
                # Recreate response with proper content
                return Response(
                    content=content,
                    status_code=response.status_code,
                    headers=response.headers,
                    media_type=response.media_type
                )
            else:
                # Don't cache non-JSON responses
                response.headers["X-Cache"] = "SKIP"
                return response
                
        except Exception as e:
            logger.error(f"Caching error: {e}")
            return response
    
    async def _record_performance_metrics(self, 
                                        processing_time: float,
                                        memory_usage: float,
                                        cpu_usage: float,
                                        status_code: int):
        """Record performance metrics"""
        try:
            # Calculate error rate
            error_rate = self.error_counter / self.request_counter if self.request_counter > 0 else 0
            
            # Get cache stats
            cache_stats = cache.get_stats()
            cache_hit_rate = cache_stats.get('hit_rate', 0)
            
            # Get active connections count
            resource_stats = resource_manager.get_resource_stats()
            active_connections = resource_stats.get('active_jobs', 0)
            
            # Record metrics
            await performance_monitor.record_metrics(
                response_time=processing_time,
                memory_usage=memory_usage / 100.0,  # Convert to fraction
                cpu_usage=cpu_usage / 100.0,  # Convert to fraction
                active_connections=active_connections,
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Error recording performance metrics: {e}")


class ResourceLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing resource limits"""
    
    def __init__(self, app, max_concurrent_requests: int = 100):
        super().__init__(app)
        self.max_concurrent_requests = max_concurrent_requests
        self.active_requests = 0
        self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Enforce resource limits"""
        async with self._lock:
            if self.active_requests >= self.max_concurrent_requests:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "service_unavailable",
                        "message": f"Server is currently handling {self.active_requests} requests. Please try again later.",
                        "max_concurrent_requests": self.max_concurrent_requests
                    }
                )
            
            self.active_requests += 1
        
        try:
            # Check system resources
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            if memory_percent > 90:  # 90% memory usage
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "resource_exhausted",
                        "message": "Server memory usage is too high. Please try again later.",
                        "memory_usage": f"{memory_percent:.1f}%"
                    }
                )
            
            if cpu_percent > 95:  # 95% CPU usage
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "resource_exhausted",
                        "message": "Server CPU usage is too high. Please try again later.",
                        "cpu_usage": f"{cpu_percent:.1f}%"
                    }
                )
            
            # Process request
            response = await call_next(request)
            return response
            
        finally:
            async with self._lock:
                self.active_requests -= 1


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware for setting cache control headers"""
    
    def __init__(self, app):
        super().__init__(app)
        self.cache_policies = {
            '/api/status': 'max-age=60',  # Cache status for 1 minute
            '/health': 'max-age=30',      # Cache health for 30 seconds
            '/api/workflows': 'max-age=300',  # Cache workflow list for 5 minutes
            'static': 'max-age=86400',    # Cache static files for 1 day
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add cache control headers"""
        response = await call_next(request)
        
        # Determine cache policy
        path = request.url.path
        cache_control = None
        
        # Check for exact matches
        if path in self.cache_policies:
            cache_control = self.cache_policies[path]
        else:
            # Check for pattern matches
            for pattern, policy in self.cache_policies.items():
                if pattern in path:
                    cache_control = policy
                    break
        
        # Set cache control header
        if cache_control:
            response.headers["Cache-Control"] = cache_control
        else:
            # Default: no cache for API endpoints
            if path.startswith('/api/'):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
        
        return response
