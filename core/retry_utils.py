"""
Retry Utilities - Exponential Backoff Decorator

This module provides retry logic with exponential backoff for handling
transient failures in network requests, API calls, and other unreliable operations.

Key Features:
- Automatic retry with configurable attempts
- Exponential backoff (1s → 2s → 4s → 8s...)
- Support for both sync and async functions
- Custom exception filtering
- Detailed logging of retry attempts

Example Usage:
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def fetch_data(url: str) -> dict:
        response = await httpx.get(url)
        return response.json()
"""

import asyncio
import time
import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type, Any

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Decorator for automatic retry with exponential backoff.
    
    This implements a smart retry strategy:
    - Attempt 1 fails → Wait base_delay seconds
    - Attempt 2 fails → Wait base_delay * exponential_base seconds
    - Attempt 3 fails → Wait base_delay * exponential_base^2 seconds
    - etc.
    
    Why exponential backoff?
    - Prevents overwhelming servers during outages
    - Gives time for transient issues to resolve
    - Industry standard for retry logic (AWS, Google Cloud, etc.)
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        exponential_base: Multiplier for exponential growth (default: 2.0)
        exceptions: Tuple of exception types to retry on (default: all exceptions)
        on_retry: Optional callback function(exception, attempt, delay)
        
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        async def unreliable_api_call():
            response = await httpx.get("https://api.example.com/data")
            return response.json()
            
        # Retry timeline:
        # - Attempt 1 @ 0s: Fails (timeout)
        # - Wait 1s
        # - Attempt 2 @ 1s: Fails (connection error)
        # - Wait 2s
        # - Attempt 3 @ 3s: Success! ✅
    """
    
    def decorator(func: Callable) -> Callable:
        # Detect if function is async or sync
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                        
                    except Exception as e:
                        last_exception = e
                        
                        # Check if this exception should be retried
                        if exceptions and not isinstance(e, exceptions):
                            logger.error(f"Non-retryable exception in {func.__name__}: {type(e).__name__}: {str(e)}")
                            raise
                        
                        # Last attempt - don't wait, just raise
                        if attempt == max_retries - 1:
                            logger.error(f"❌ All {max_retries} retry attempts failed for {func.__name__}")
                            raise
                        
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        
                        logger.warning(
                            f"⚠️ Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: "
                            f"{type(e).__name__}: {str(e)} - Retrying in {delay:.1f}s..."
                        )
                        
                        # Call optional retry callback
                        if on_retry:
                            on_retry(e, attempt + 1, delay)
                        
                        await asyncio.sleep(delay)
                
                # Should never reach here, but just in case
                if last_exception:
                    raise last_exception
                    
            return async_wrapper
            
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                        
                    except Exception as e:
                        last_exception = e
                        
                        # Check if this exception should be retried
                        if exceptions and not isinstance(e, exceptions):
                            logger.error(f"Non-retryable exception in {func.__name__}: {type(e).__name__}: {str(e)}")
                            raise
                        
                        # Last attempt - don't wait, just raise
                        if attempt == max_retries - 1:
                            logger.error(f"❌ All {max_retries} retry attempts failed for {func.__name__}")
                            raise
                        
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        
                        logger.warning(
                            f"⚠️ Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: "
                            f"{type(e).__name__}: {str(e)} - Retrying in {delay:.1f}s..."
                        )
                        
                        # Call optional retry callback
                        if on_retry:
                            on_retry(e, attempt + 1, delay)
                        
                        time.sleep(delay)
                
                # Should never reach here, but just in case
                if last_exception:
                    raise last_exception
                    
            return sync_wrapper
            
    return decorator


def retry_with_fallback(
    max_retries: int = 3,
    base_delay: float = 1.0,
    fallback_func: Optional[Callable] = None,
    fallback_on_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator with retry logic AND fallback to alternative method.
    
    This is perfect for situations like:
    - Primary: PrusaSlicer → Fallback: Cura
    - Primary: FreeCAD → Fallback: Trimesh
    - Primary: Real Printer → Fallback: Mock Printer
    
    Args:
        max_retries: Maximum retry attempts for primary function
        base_delay: Initial delay between retries
        fallback_func: Alternative function to try if all retries fail
        fallback_on_exceptions: Only use fallback for these exceptions
        
    Example:
        def fallback_slicer(stl_file, settings):
            return mock_slice(stl_file, settings)
        
        @retry_with_fallback(max_retries=2, fallback_func=fallback_slicer)
        async def slice_with_prusaslicer(stl_file, settings):
            return await run_prusaslicer(stl_file, settings)
            
        # If PrusaSlicer fails 2 times → automatically uses mock_slice()
    """
    
    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                # Try primary function with retries
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        # Check if we should use fallback for this exception
                        if fallback_on_exceptions and not isinstance(e, fallback_on_exceptions):
                            raise
                        
                        if attempt < max_retries - 1:
                            delay = min(base_delay * (2 ** attempt), 60.0)
                            logger.warning(
                                f"⚠️ {func.__name__} attempt {attempt + 1}/{max_retries} failed: "
                                f"{type(e).__name__} - Retrying in {delay:.1f}s..."
                            )
                            await asyncio.sleep(delay)
                
                # All retries failed - try fallback if available
                if fallback_func:
                    logger.warning(
                        f"🔄 All retries failed for {func.__name__}, "
                        f"trying fallback: {fallback_func.__name__}"
                    )
                    try:
                        if asyncio.iscoroutinefunction(fallback_func):
                            return await fallback_func(*args, **kwargs)
                        else:
                            return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"❌ Fallback also failed: {fallback_error}")
                        raise
                
                # No fallback available - raise original exception
                if last_exception:
                    raise last_exception
                    
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        if fallback_on_exceptions and not isinstance(e, fallback_on_exceptions):
                            raise
                        
                        if attempt < max_retries - 1:
                            delay = min(base_delay * (2 ** attempt), 60.0)
                            logger.warning(
                                f"⚠️ {func.__name__} attempt {attempt + 1}/{max_retries} failed: "
                                f"{type(e).__name__} - Retrying in {delay:.1f}s..."
                            )
                            time.sleep(delay)
                
                if fallback_func:
                    logger.warning(
                        f"🔄 All retries failed for {func.__name__}, "
                        f"trying fallback: {fallback_func.__name__}"
                    )
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"❌ Fallback also failed: {fallback_error}")
                        raise
                
                if last_exception:
                    raise last_exception
                    
            return sync_wrapper
            
    return decorator


class CircuitBreaker:
    """
    Circuit Breaker pattern for preventing cascading failures.
    
    States:
    - CLOSED: Normal operation, requests flow through
    - OPEN: Too many failures, block all requests
    - HALF_OPEN: Testing if service recovered
    
    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        async def call_api():
            if breaker.is_open():
                raise Exception("Circuit breaker is OPEN")
            
            try:
                result = await make_request()
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_attempts: int = 1
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (OPEN → HALF_OPEN)
            half_open_attempts: Number of successful attempts needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def is_open(self) -> bool:
        """Check if circuit breaker is OPEN (blocking requests)."""
        if self.state == "OPEN":
            # Check if timeout expired → move to HALF_OPEN
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.timeout:
                self.state = "HALF_OPEN"
                self.logger.info("🔄 Circuit breaker: OPEN → HALF_OPEN (testing recovery)")
                return False
            return True
        return False
    
    def record_success(self) -> None:
        """Record successful request."""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.half_open_attempts:
                self.state = "CLOSED"
                self.failure_count = 0
                self.success_count = 0
                self.logger.info("✅ Circuit breaker: HALF_OPEN → CLOSED (service recovered)")
        else:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                self.state = "OPEN"
                self.logger.warning(f"🚨 Circuit breaker: CLOSED → OPEN ({self.failure_count} failures)")
        
        if self.state == "HALF_OPEN":
            # Failed during recovery test → go back to OPEN
            self.state = "OPEN"
            self.success_count = 0
            self.logger.warning("🚨 Circuit breaker: HALF_OPEN → OPEN (recovery failed)")
