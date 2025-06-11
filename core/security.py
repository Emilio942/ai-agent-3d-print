"""
Security & Performance Enhancement Module for AI Agent 3D Print System

This module provides advanced security features including:
- Enhanced input sanitization
- SQL injection protection
- XSS protection
- Command injection protection
- Advanced rate limiting
- Security audit logging
"""

import re
import time
import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import pyotp
import qrcode
from io import BytesIO
import base64

from core.exceptions import SecurityViolationError, RateLimitExceededError
from core.logger import get_logger

logger = get_logger(__name__)

class ThreatLevel(Enum):
    """Security threat level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: str
    threat_level: ThreatLevel
    source_ip: str
    user_id: Optional[str]
    endpoint: Optional[str] = None
    payload: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    blocked: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

class InputSanitizer:
    """Advanced input sanitization and validation"""
    
    def __init__(self):
        """Initialize input sanitizer with threat patterns"""
        self.sql_injection_patterns = [
            r"('|(\\'))|(\;)|(\-\-)|(\s+(or|and)\s+.*(=|like))",
            r"(union\s+select|union\s+all\s+select)",
            r"(drop\s+table|truncate\s+table|delete\s+from)",
            r"(exec(\s|\+)+(s|x)p\w+)",
            r"(insert\s+into|update\s+.+\s+set)",
            r"(create\s+(table|database|index|view))",
            r"(alter\s+(table|database|index|view))",
            r"(grant\s+|revoke\s+)",
            r"(information_schema|sysobjects|syscolumns)"
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"javascript:",
            r"vbscript:",
            r"data:text/html",
            r"on\w+\s*=",
            r"<\s*\w+[^>]*on\w+[^>]*>",
            r"expression\s*\(",
            r"url\s*\(",
            r"@import"
        ]
        
        self.command_injection_patterns = [
            r"[;&|`$]",
            r"\.\./",
            r"system\s*\(",
            r"exec\s*\(",
            r"eval\s*\(",
            r"popen\s*\(",
            r"subprocess\s*\.",
            r"os\.(system|popen|exec)",
            r"__(import|eval)__",
            r"getattr\s*\(",
            r"setattr\s*\(",
            r"delattr\s*\(",
            r"globals\s*\(",
            r"locals\s*\(",
            r"vars\s*\(",
            r"dir\s*\("
        ]
        
        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"\\.\\.\\",
            r"/etc/passwd",
            r"/etc/shadow",
            r"c:\\windows\\system32",
            r"..%252f",
            r"..%255c"
        ]
        
        self.threat_scores = {
            'sql_injection': 8,
            'xss': 6,
            'command_injection': 9,
            'path_traversal': 7,
            'suspicious_patterns': 4
        }
    
    def sanitize_input(self, data: str, strict_mode: bool = True) -> Dict[str, Any]:
        """
        Sanitize input data and detect threats
        
        Args:
            data: Input string to sanitize
            strict_mode: If True, apply strict sanitization
            
        Returns:
            Dictionary containing sanitized data and threat assessment
        """
        if not isinstance(data, str):
            data = str(data)
        
        original_data = data
        threat_score = 0
        detected_threats = []
        sanitization_applied = []
        
        # Check for SQL injection
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                detected_threats.append('sql_injection')
                threat_score += self.threat_scores['sql_injection']
                if strict_mode:
                    data = re.sub(pattern, "", data, flags=re.IGNORECASE)
                    sanitization_applied.append('sql_injection_removed')
        
        # Check for XSS
        for pattern in self.xss_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                detected_threats.append('xss')
                threat_score += self.threat_scores['xss']
                if strict_mode:
                    data = re.sub(pattern, "", data, flags=re.IGNORECASE)
                    sanitization_applied.append('xss_removed')
        
        # Check for command injection
        for pattern in self.command_injection_patterns:
            if re.search(pattern, data):
                detected_threats.append('command_injection')
                threat_score += self.threat_scores['command_injection']
                if strict_mode:
                    data = re.sub(pattern, "", data)
                    sanitization_applied.append('command_injection_removed')
        
        # Check for path traversal
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                detected_threats.append('path_traversal')
                threat_score += self.threat_scores['path_traversal']
                if strict_mode:
                    data = re.sub(pattern, "", data, flags=re.IGNORECASE)
                    sanitization_applied.append('path_traversal_removed')
        
        # Determine threat level
        if threat_score >= 15:
            threat_level = ThreatLevel.CRITICAL
        elif threat_score >= 10:
            threat_level = ThreatLevel.HIGH
        elif threat_score >= 5:
            threat_level = ThreatLevel.MEDIUM
        elif threat_score > 0:
            threat_level = ThreatLevel.LOW
        else:
            threat_level = None
        
        # Clean up the sanitized data
        data = data.strip()
        
        return {
            'sanitized_data': data,
            'original_data': original_data,
            'threat_score': threat_score,
            'threat_level': threat_level,
            'detected_threats': list(set(detected_threats)),
            'sanitization_applied': sanitization_applied,
            'is_safe': threat_score == 0
        }
    
    def detect_threats(self, data: str) -> List[str]:
        """
        Detect threats in input data without sanitization
        
        Args:
            data: Input string to analyze
            
        Returns:
            List of detected threat types
        """
        result = self.sanitize_input(data, strict_mode=False)
        return result['detected_threats']


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests: int
    window: int  # seconds
    burst_allowance: int = 0
    progressive_delay: bool = False

class AdvancedRateLimiter:
    """
    Advanced rate limiter with multiple layers and progressive penalties
    """
    
    def __init__(self):
        """Initialize rate limiter with default configurations"""
        self.limits = {
            'global': RateLimitConfig(requests=1000, window=3600, burst_allowance=10),
            'per_user': RateLimitConfig(requests=100, window=3600, burst_allowance=5),
            'per_ip': RateLimitConfig(requests=200, window=3600, burst_allowance=10),
            'endpoints': {
                '/api/print-request': RateLimitConfig(requests=10, window=600, progressive_delay=True),
                '/api/workflows': RateLimitConfig(requests=50, window=3600),
                '/health': RateLimitConfig(requests=100, window=60),
                '/api/status': RateLimitConfig(requests=200, window=3600)
            }
        }
        
        # In-memory storage for rate limiting (in production, use Redis)
        self.request_history = {
            'global': [],
            'users': {},
            'ips': {},
            'endpoints': {}
        }
        
        self.violation_penalties = {}  # Track repeat violators
    
    def _get_current_time(self) -> float:
        """Get current timestamp"""
        return time.time()
    
    def _clean_old_requests(self, requests: List[float], window: int) -> List[float]:
        """Remove requests outside the time window"""
        current_time = self._get_current_time()
        return [req_time for req_time in requests if current_time - req_time < window]
    
    def _apply_progressive_penalty(self, identifier: str) -> float:
        """Apply progressive delay for repeat violators"""
        violations = self.violation_penalties.get(identifier, 0)
        if violations == 0:
            return 0
        
        # Exponential backoff: 1s, 2s, 4s, 8s, etc. (max 60s)
        delay = min(2 ** (violations - 1), 60)
        return delay
    
    async def check_rate_limit(self, 
                             user_id: Optional[str] = None,
                             ip_address: Optional[str] = None,
                             endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if request is within rate limits
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            endpoint: API endpoint being accessed
            
        Returns:
            Dictionary with rate limit status and metadata
        """
        current_time = self._get_current_time()
        violations = []
        delays = []
        
        # Check global rate limit
        self.request_history['global'] = self._clean_old_requests(
            self.request_history['global'], 
            self.limits['global'].window
        )
        
        if len(self.request_history['global']) >= self.limits['global'].requests:
            violations.append('global')
        
        # Check per-user rate limit
        if user_id:
            if user_id not in self.request_history['users']:
                self.request_history['users'][user_id] = []
            
            self.request_history['users'][user_id] = self._clean_old_requests(
                self.request_history['users'][user_id],
                self.limits['per_user'].window
            )
            
            if len(self.request_history['users'][user_id]) >= self.limits['per_user'].requests:
                violations.append('per_user')
                delays.append(self._apply_progressive_penalty(f"user:{user_id}"))
        
        # Check per-IP rate limit
        if ip_address:
            if ip_address not in self.request_history['ips']:
                self.request_history['ips'][ip_address] = []
            
            self.request_history['ips'][ip_address] = self._clean_old_requests(
                self.request_history['ips'][ip_address],
                self.limits['per_ip'].window
            )
            
            if len(self.request_history['ips'][ip_address]) >= self.limits['per_ip'].requests:
                violations.append('per_ip')
                delays.append(self._apply_progressive_penalty(f"ip:{ip_address}"))
        
        # Check endpoint-specific rate limit
        if endpoint and endpoint in self.limits['endpoints']:
            endpoint_key = f"{endpoint}:{user_id or ip_address}"
            if endpoint_key not in self.request_history['endpoints']:
                self.request_history['endpoints'][endpoint_key] = []
            
            self.request_history['endpoints'][endpoint_key] = self._clean_old_requests(
                self.request_history['endpoints'][endpoint_key],
                self.limits['endpoints'][endpoint].window
            )
            
            endpoint_limit = self.limits['endpoints'][endpoint]
            if len(self.request_history['endpoints'][endpoint_key]) >= endpoint_limit.requests:
                violations.append('endpoint')
                if endpoint_limit.progressive_delay:
                    delays.append(self._apply_progressive_penalty(f"endpoint:{endpoint_key}"))
        
        # Determine if request should be allowed
        is_allowed = len(violations) == 0
        max_delay = max(delays) if delays else 0
        
        if not is_allowed:
            # Record violation for progressive penalties
            for violation_type in violations:
                if user_id:
                    key = f"user:{user_id}"
                    self.violation_penalties[key] = self.violation_penalties.get(key, 0) + 1
                if ip_address:
                    key = f"ip:{ip_address}"
                    self.violation_penalties[key] = self.violation_penalties.get(key, 0) + 1
        else:
            # Record successful request
            self.request_history['global'].append(current_time)
            if user_id:
                self.request_history['users'][user_id].append(current_time)
            if ip_address:
                self.request_history['ips'][ip_address].append(current_time)
            if endpoint and endpoint in self.limits['endpoints']:
                endpoint_key = f"{endpoint}:{user_id or ip_address}"
                self.request_history['endpoints'][endpoint_key].append(current_time)
        
        return {
            'allowed': is_allowed,
            'violations': violations,
            'delay_seconds': max_delay,
            'retry_after': current_time + max_delay if max_delay > 0 else None,
            'remaining_requests': self._calculate_remaining_requests(user_id, ip_address, endpoint),
            'reset_time': current_time + max(
                self.limits['global'].window,
                self.limits['per_user'].window if user_id else 0,
                self.limits['per_ip'].window if ip_address else 0
            )
        }
    
    def _calculate_remaining_requests(self, 
                                    user_id: Optional[str],
                                    ip_address: Optional[str],
                                    endpoint: Optional[str]) -> Dict[str, int]:
        """Calculate remaining requests for different limits"""
        remaining = {}
        
        # Global remaining
        remaining['global'] = max(0, self.limits['global'].requests - len(self.request_history['global']))
        
        # User remaining
        if user_id and user_id in self.request_history['users']:
            remaining['user'] = max(0, self.limits['per_user'].requests - len(self.request_history['users'][user_id]))
        
        # IP remaining
        if ip_address and ip_address in self.request_history['ips']:
            remaining['ip'] = max(0, self.limits['per_ip'].requests - len(self.request_history['ips'][ip_address]))
        
        # Endpoint remaining
        if endpoint and endpoint in self.limits['endpoints']:
            endpoint_key = f"{endpoint}:{user_id or ip_address}"
            if endpoint_key in self.request_history['endpoints']:
                remaining['endpoint'] = max(0, 
                    self.limits['endpoints'][endpoint].requests - 
                    len(self.request_history['endpoints'][endpoint_key])
                )
        
        return remaining

class SecurityAuditLogger:
    """Security event audit logger"""
    
    def __init__(self):
        """Initialize security audit logger"""
        self.logger = get_logger("security_audit")
        self.events = []  # In-memory storage (use database in production)
    
    async def log_security_event(self, event: SecurityEvent):
        """Log a security event"""
        event_data = {
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type,
            'threat_level': event.threat_level.value if event.threat_level else None,
            'source_ip': event.source_ip,
            'user_id': event.user_id,
            'payload': event.payload[:1000],  # Limit payload size in logs
            'blocked': event.blocked,
            'details': event.details
        }
        
        # Log to structured logger
        if event.threat_level and event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self.logger.error(f"Security threat detected: {event.event_type}", extra=event_data)
        elif event.threat_level == ThreatLevel.MEDIUM:
            self.logger.warning(f"Security event: {event.event_type}", extra=event_data)
        else:
            self.logger.info(f"Security event: {event.event_type}", extra=event_data)
        
        # Store in memory (replace with database in production)
        self.events.append(event)
        
        # Keep only last 10000 events in memory
        if len(self.events) > 10000:
            self.events = self.events[-10000:]
    
    async def get_security_events(self, 
                                filters: Optional[Dict[str, Any]] = None,
                                limit: int = 100) -> List[SecurityEvent]:
        """Retrieve security events with optional filtering"""
        events = self.events
        
        if filters:
            if 'threat_level' in filters:
                events = [e for e in events if e.threat_level == filters['threat_level']]
            if 'event_type' in filters:
                events = [e for e in events if e.event_type == filters['event_type']]
            if 'source_ip' in filters:
                events = [e for e in events if e.source_ip == filters['source_ip']]
            if 'user_id' in filters:
                events = [e for e in events if e.user_id == filters['user_id']]
            if 'since' in filters:
                events = [e for e in events if e.timestamp >= filters['since']]
        
        return events[-limit:]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get security event statistics"""
        total_events = len(self.events)
        threat_counts = {}
        
        for event in self.events:
            level = event.threat_level.value if event.threat_level else 'UNKNOWN'
            threat_counts[level] = threat_counts.get(level, 0) + 1
        
        return {
            'total_events': total_events,
            'threat_level_counts': threat_counts,
            'recent_events': len([e for e in self.events 
                                if (datetime.now() - e.timestamp).total_seconds() < 3600])
        }
    
    async def get_events(self, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get events in dictionary format for API responses"""
        events = await self.get_security_events(filters, limit)
        
        return [
            {
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'threat_level': event.threat_level.value if event.threat_level else None,
                'source_ip': event.source_ip,
                'user_id': event.user_id,
                'endpoint': event.endpoint,
                'blocked': event.blocked,
                'details': event.details
            }
            for event in events
        ]

class MFAManager:
    """Multi-Factor Authentication Manager"""
    
    def __init__(self):
        """Initialize MFA manager"""
        self.user_secrets = {}  # In production, use secure database
        self.backup_codes = {}  # Store backup codes securely
    
    def generate_secret(self, user_id: str) -> str:
        """Generate a new TOTP secret for user"""
        secret = pyotp.random_base32()
        self.user_secrets[user_id] = secret
        return secret
    
    def generate_qr_code(self, user_id: str, service_name: str = "AI 3D Print System") -> str:
        """Generate QR code for TOTP setup"""
        if user_id not in self.user_secrets:
            raise ValueError("No secret found for user. Generate secret first.")
        
        secret = self.user_secrets[user_id]
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_id,
            issuer_name=service_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_code_data}"
    
    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        if user_id not in self.user_secrets:
            return False
        
        secret = self.user_secrets[user_id]
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self, user_id: str, count: int = 10) -> List[str]:
        """Generate backup codes for user"""
        codes = []
        for _ in range(count):
            code = pyotp.random_base32()[:8]  # 8-character backup codes
            codes.append(code)
        
        self.backup_codes[user_id] = codes
        return codes
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify backup code (single use)"""
        if user_id not in self.backup_codes:
            return False
        
        if code in self.backup_codes[user_id]:
            self.backup_codes[user_id].remove(code)  # Single use
            return True
        
        return False

# Global instances
input_sanitizer = InputSanitizer()
rate_limiter = AdvancedRateLimiter()
audit_logger = SecurityAuditLogger()
mfa_manager = MFAManager()

__all__ = [
    'ThreatLevel',
    'SecurityEvent',
    'InputSanitizer',
    'RateLimitConfig',
    'AdvancedRateLimiter',
    'SecurityAuditLogger',
    'MFAManager',
    'input_sanitizer',
    'rate_limiter',
    'audit_logger',
    'mfa_manager'
]
