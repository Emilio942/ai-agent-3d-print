"""
Security Middleware for FastAPI Application

This module provides security middleware for the AI Agent 3D Print System,
integrating the security features into the FastAPI application.
"""

import time
import asyncio
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.security import (
    input_sanitizer, rate_limiter, audit_logger, 
    ThreatLevel, SecurityEvent
)
from core.logger import get_logger

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for FastAPI application"""
    
    def __init__(self, app, enable_rate_limiting: bool = True, enable_input_sanitization: bool = True):
        super().__init__(app)
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_input_sanitization = enable_input_sanitization
        
        # Security headers configuration
        self.security_headers = {
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': self._build_csp(),
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'
        }
    
    def _build_csp(self) -> str:
        """Build Content Security Policy header"""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com; "
            "connect-src 'self' ws: wss:; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'"
        )
    
    def _extract_user_info(self, request: Request) -> Dict[str, Optional[str]]:
        """Extract user information from request"""
        # Get IP address (handle proxy forwarding)
        ip_address = request.headers.get("X-Forwarded-For")
        if ip_address:
            ip_address = ip_address.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None
        
        # Extract user ID from authorization header or session
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # In a real implementation, decode JWT to get user_id
            # For now, we'll extract from session or use a placeholder
            user_id = request.headers.get("X-User-ID")
        
        return {
            "user_id": user_id,
            "ip_address": ip_address,
            "endpoint": str(request.url.path)
        }
    
    async def _check_rate_limits(self, request: Request, user_info: Dict[str, Optional[str]]) -> Optional[Response]:
        """Check rate limits and return error response if exceeded"""
        if not self.enable_rate_limiting:
            return None
        
        try:
            rate_limit_result = await rate_limiter.check_rate_limit(
                user_id=user_info["user_id"],
                ip_address=user_info["ip_address"],
                endpoint=user_info["endpoint"]
            )
            
            if not rate_limit_result["allowed"]:
                # Log rate limit violation
                event = SecurityEvent(
                    event_type="rate_limit_exceeded",
                    threat_level=ThreatLevel.MEDIUM,
                    source_ip=user_info["ip_address"],
                    user_id=user_info["user_id"],
                    endpoint=user_info["endpoint"],
                    details={
                        "violations": rate_limit_result["violations"],
                        "delay_seconds": rate_limit_result["delay_seconds"],
                        "remaining_requests": rate_limit_result["remaining_requests"]
                    }
                )
                await audit_logger.log_security_event(event)
                
                # Apply progressive delay if specified
                if rate_limit_result["delay_seconds"] > 0:
                    await asyncio.sleep(min(rate_limit_result["delay_seconds"], 5))  # Max 5s delay
                
                # Return rate limit error response
                headers = {
                    "X-RateLimit-Limit": "100",  # Could be dynamic based on user type
                    "X-RateLimit-Remaining": str(rate_limit_result["remaining_requests"].get("user", 0)),
                    "X-RateLimit-Reset": str(int(rate_limit_result["reset_time"])),
                    "Retry-After": str(int(rate_limit_result["retry_after"])) if rate_limit_result["retry_after"] else "60"
                }
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests. Please try again later.",
                        "violations": rate_limit_result["violations"],
                        "retry_after": rate_limit_result["retry_after"]
                    },
                    headers=headers
                )
            
            # Add rate limit headers to successful requests
            request.state.rate_limit_headers = {
                "X-RateLimit-Limit": "100",  # Could be dynamic
                "X-RateLimit-Remaining": str(rate_limit_result["remaining_requests"].get("user", 100)),
                "X-RateLimit-Reset": str(int(rate_limit_result["reset_time"]))
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            # Don't block request on rate limit check failure
            pass
        
        return None
    
    async def _sanitize_request_data(self, request: Request) -> Optional[Response]:
        """Sanitize request data and check for threats"""
        if not self.enable_input_sanitization:
            return None
        
        try:
            # Check URL path for threats
            url_threats = input_sanitizer.detect_threats(str(request.url.path))
            if url_threats:
                user_info = self._extract_user_info(request)
                event = SecurityEvent(
                    event_type="malicious_request",
                    threat_level=ThreatLevel.HIGH,
                    source_ip=user_info["ip_address"],
                    user_id=user_info["user_id"],
                    endpoint=user_info["endpoint"],
                    details={
                        "threats_detected": url_threats,
                        "request_path": str(request.url.path)
                    }
                )
                await audit_logger.log_security_event(event)
                
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "malicious_request",
                        "message": "Request contains potentially malicious content",
                        "threats_detected": url_threats
                    }
                )
            
            # For POST/PUT requests, check body content
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    # Note: This is a simplified approach. In production,
                    # you'd want to be more careful about reading the body
                    # and ensuring it can be processed downstream
                    body = await request.body()
                    if body:
                        body_str = body.decode("utf-8")
                        body_threats = input_sanitizer.detect_threats(body_str)
                        if body_threats:
                            user_info = self._extract_user_info(request)
                            event = SecurityEvent(
                                event_type="malicious_request_body",
                                threat_level=ThreatLevel.HIGH,
                                source_ip=user_info["ip_address"],
                                user_id=user_info["user_id"],
                                endpoint=user_info["endpoint"],
                                details={
                                    "threats_detected": body_threats,
                                    "content_length": len(body_str)
                                }
                            )
                            await audit_logger.log_security_event(event)
                            
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "error": "malicious_request_body",
                                    "message": "Request body contains potentially malicious content",
                                    "threats_detected": body_threats
                                }
                            )
        
        except Exception as e:
            logger.error(f"Error during input sanitization: {e}")
            # Don't block request on sanitization failure
            pass
        
        return None
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Main middleware dispatch method"""
        start_time = time.time()
        user_info = self._extract_user_info(request)
        
        # Log request start
        logger.info(f"Security middleware processing: {request.method} {request.url.path} from {user_info['ip_address']}")
        
        try:
            # Check rate limits
            rate_limit_response = await self._check_rate_limits(request, user_info)
            if rate_limit_response:
                return rate_limit_response
            
            # Sanitize input
            sanitization_response = await self._sanitize_request_data(request)
            if sanitization_response:
                return sanitization_response
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            for header_name, header_value in self.security_headers.items():
                response.headers[header_name] = header_value
            
            # Add rate limit headers if available
            if hasattr(request.state, 'rate_limit_headers'):
                for header_name, header_value in request.state.rate_limit_headers.items():
                    response.headers[header_name] = header_value
            
            # Add processing time header
            processing_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(processing_time)
            
            # Log successful request
            if response.status_code < 400:
                event = SecurityEvent(
                    event_type="request_processed",
                    threat_level=ThreatLevel.LOW,
                    source_ip=user_info["ip_address"],
                    user_id=user_info["user_id"],
                    endpoint=user_info["endpoint"],
                    details={
                        "status_code": response.status_code,
                        "processing_time": processing_time,
                        "method": request.method
                    }
                )
                await audit_logger.log_security_event(event)
            
            return response
            
        except Exception as e:
            # Log security middleware error
            logger.error(f"Security middleware error: {e}")
            event = SecurityEvent(
                event_type="middleware_error",
                threat_level=ThreatLevel.MEDIUM,
                source_ip=user_info["ip_address"],
                user_id=user_info["user_id"],
                endpoint=user_info["endpoint"],
                details={
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
            )
            await audit_logger.log_security_event(event)
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "security_middleware_error",
                    "message": "An error occurred in security processing"
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware for adding security headers only"""
    
    def __init__(self, app):
        super().__init__(app)
        self.headers = {
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        for header_name, header_value in self.headers.items():
            response.headers[header_name] = header_value
        
        return response
