"""
Security and Performance API Endpoints

This module provides API endpoints for monitoring and managing security 
and performance features of the AI Agent 3D Print System.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from datetime import datetime

from core.security import audit_logger, rate_limiter, input_sanitizer, mfa_manager
from core.performance import cache, resource_manager, performance_monitor
from core.logger import get_logger

logger = get_logger(__name__)

# Create router for security and performance endpoints
security_performance_router = APIRouter(prefix="/api/security-performance", tags=["Security & Performance"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SecurityStatusResponse(BaseModel):
    """Security status response model"""
    status: str = Field(..., description="Overall security status")
    threat_level: str = Field(..., description="Current threat level")
    active_violations: int = Field(..., description="Number of active security violations")
    rate_limit_status: Dict[str, Any] = Field(..., description="Rate limiting status")
    audit_log_entries: int = Field(..., description="Number of audit log entries")
    mfa_enabled_users: int = Field(..., description="Number of users with MFA enabled")


class PerformanceStatusResponse(BaseModel):
    """Performance status response model"""
    status: str = Field(..., description="Overall performance status")
    response_time_avg: float = Field(..., description="Average response time in seconds")
    memory_usage: float = Field(..., description="Current memory usage percentage")
    cpu_usage: float = Field(..., description="Current CPU usage percentage")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    active_connections: int = Field(..., description="Number of active connections")
    resource_availability: Dict[str, Any] = Field(..., description="Resource availability status")


class CacheStatsResponse(BaseModel):
    """Cache statistics response model"""
    hit_rate: float = Field(..., description="Cache hit rate")
    hits: int = Field(..., description="Number of cache hits")
    misses: int = Field(..., description="Number of cache misses")
    evictions: int = Field(..., description="Number of cache evictions")
    total_size_mb: float = Field(..., description="Total cache size in MB")
    entry_count: int = Field(..., description="Number of cache entries")
    max_size_mb: float = Field(..., description="Maximum cache size in MB")


class SecurityEventRequest(BaseModel):
    """Security event request model"""
    event_type: str = Field(..., description="Type of security event")
    user_id: Optional[str] = Field(None, description="User ID associated with event")
    ip_address: Optional[str] = Field(None, description="IP address associated with event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event details")


class MFASetupResponse(BaseModel):
    """MFA setup response model"""
    secret: str = Field(..., description="TOTP secret for MFA setup")
    qr_code: str = Field(..., description="QR code data URL for MFA setup")
    backup_codes: list = Field(..., description="Backup codes for MFA")


# =============================================================================
# SECURITY ENDPOINTS
# =============================================================================

@security_performance_router.get("/security/status", response_model=SecurityStatusResponse)
async def get_security_status():
    """Get current security status and metrics"""
    try:
        # Get rate limiting status
        rate_limit_status = {
            "global_active": len(rate_limiter.request_history.get('global', [])),
            "user_limits_active": len(rate_limiter.request_history.get('users', {})),
            "ip_limits_active": len(rate_limiter.request_history.get('ips', {})),
            "violations": len(rate_limiter.violation_penalties)
        }
        
        # Get audit log stats
        audit_stats = await audit_logger.get_statistics()
        
        # Determine overall security status
        status = "healthy"
        threat_level = "LOW"
        
        if rate_limit_status["violations"] > 10:
            status = "warning"
            threat_level = "MEDIUM"
        
        if rate_limit_status["violations"] > 50:
            status = "critical"
            threat_level = "HIGH"
        
        return SecurityStatusResponse(
            status=status,
            threat_level=threat_level,
            active_violations=rate_limit_status["violations"],
            rate_limit_status=rate_limit_status,
            audit_log_entries=audit_stats.get('total_events', 0),
            mfa_enabled_users=len(mfa_manager.user_secrets)
        )
        
    except Exception as e:
        logger.error(f"Error getting security status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security status"
        )


@security_performance_router.get("/security/audit-log")
async def get_audit_log(
    limit: int = Query(100, description="Maximum number of entries to return"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    event_type: Optional[str] = Query(None, description="Filter by event type")
):
    """Get security audit log entries"""
    try:
        filters = {}
        if threat_level:
            filters['threat_level'] = threat_level
        if event_type:
            filters['event_type'] = event_type
        
        events = await audit_logger.get_events(limit=limit, filters=filters)
        
        return {
            "events": events,
            "total_count": len(events),
            "filters_applied": filters
        }
        
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log"
        )


@security_performance_router.post("/security/mfa/setup/{user_id}", response_model=MFASetupResponse)
async def setup_mfa(user_id: str):
    """Setup multi-factor authentication for a user"""
    try:
        # Generate TOTP secret
        secret = mfa_manager.generate_secret(user_id)
        
        # Generate QR code
        qr_code = mfa_manager.generate_qr_code(user_id)
        
        # Generate backup codes
        backup_codes = mfa_manager.generate_backup_codes(user_id)
        
        logger.info(f"MFA setup initiated for user: {user_id}")
        
        return MFASetupResponse(
            secret=secret,
            qr_code=qr_code,
            backup_codes=backup_codes
        )
        
    except Exception as e:
        logger.error(f"Error setting up MFA for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup MFA"
        )


@security_performance_router.post("/security/mfa/verify/{user_id}")
async def verify_mfa(user_id: str, token: str = Query(..., description="TOTP token to verify")):
    """Verify MFA token for a user"""
    try:
        is_valid = mfa_manager.verify_totp(user_id, token)
        
        if is_valid:
            logger.info(f"MFA verification successful for user: {user_id}")
            return {"verified": True, "message": "MFA token verified successfully"}
        else:
            logger.warning(f"MFA verification failed for user: {user_id}")
            return {"verified": False, "message": "Invalid MFA token"}
            
    except Exception as e:
        logger.error(f"Error verifying MFA for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA token"
        )


# =============================================================================
# PERFORMANCE ENDPOINTS
# =============================================================================

@security_performance_router.get("/performance/status", response_model=PerformanceStatusResponse)
async def get_performance_status():
    """Get current performance status and metrics"""
    try:
        # Get performance summary for last 60 minutes
        performance_summary = performance_monitor.get_performance_summary(minutes=60)
        
        # Get resource stats
        resource_stats = resource_manager.get_resource_stats()
        
        # Get cache stats
        cache_stats = cache.get_stats()
        
        # Determine overall performance status
        status = "healthy"
        avg_response_time = performance_summary.get('averages', {}).get('response_time', 0)
        memory_usage = resource_stats.get('current', {}).get('memory_percent', 0)
        cpu_usage = resource_stats.get('current', {}).get('cpu_percent', 0)
        
        if avg_response_time > 1.0 or memory_usage > 80 or cpu_usage > 80:
            status = "warning"
        
        if avg_response_time > 2.0 or memory_usage > 90 or cpu_usage > 90:
            status = "critical"
        
        return PerformanceStatusResponse(
            status=status,
            response_time_avg=avg_response_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            cache_hit_rate=cache_stats.get('hit_rate', 0) * 100,
            active_connections=resource_stats.get('active_jobs', 0),
            resource_availability=resource_stats
        )
        
    except Exception as e:
        logger.error(f"Error getting performance status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance status"
        )


@security_performance_router.get("/performance/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = cache.get_stats()
        return CacheStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@security_performance_router.post("/performance/cache/clear")
async def clear_cache():
    """Clear all cache entries"""
    try:
        await cache.clear()
        logger.info("Cache cleared successfully")
        return {"message": "Cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@security_performance_router.get("/performance/metrics")
async def get_performance_metrics(
    minutes: int = Query(60, description="Time period in minutes for metrics")
):
    """Get detailed performance metrics"""
    try:
        summary = performance_monitor.get_performance_summary(minutes=minutes)
        return summary
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@security_performance_router.get("/performance/resource-usage")
async def get_resource_usage():
    """Get current resource usage statistics"""
    try:
        stats = resource_manager.get_resource_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting resource usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource usage"
        )


# =============================================================================
# COMBINED STATUS ENDPOINT
# =============================================================================

@security_performance_router.get("/status")
async def get_overall_status():
    """Get combined security and performance status"""
    try:
        # Get security status
        security_response = await get_security_status()
        
        # Get performance status
        performance_response = await get_performance_status()
        
        # Determine overall status
        overall_status = "healthy"
        
        if (security_response.status == "warning" or 
            performance_response.status == "warning"):
            overall_status = "warning"
        
        if (security_response.status == "critical" or 
            performance_response.status == "critical"):
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "security": security_response.dict(),
            "performance": performance_response.dict(),
            "summary": {
                "threat_level": security_response.threat_level,
                "response_time": performance_response.response_time_avg,
                "memory_usage": performance_response.memory_usage,
                "cache_hit_rate": performance_response.cache_hit_rate
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting overall status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve overall status"
        )
