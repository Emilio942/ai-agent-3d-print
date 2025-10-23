"""
Unit Tests for Retry Logic with Exponential Backoff

Tests the new retry_with_backoff decorator to ensure:
- Automatic retry on failures
- Exponential backoff delays work correctly
- Maximum retry attempts are respected
- Success after retries is handled
- Final failure after max retries raises exception
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from core.retry_utils import retry_with_backoff, CircuitBreaker


class TestRetryWithBackoff:
    """Test suite for retry decorator functionality"""
    
    def test_sync_function_success_first_try(self):
        """Test that successful function doesn't retry"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def sync_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = sync_function()
        
        assert result == "success"
        assert call_count == 1  # Should only be called once
        
    def test_sync_function_retry_then_success(self):
        """Test that function retries on failure then succeeds"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def sync_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = sync_function()
        
        assert result == "success"
        assert call_count == 3  # Should be called 3 times
        
    def test_sync_function_max_retries_exceeded(self):
        """Test that function raises after max retries"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def sync_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Permanent failure")
        
        with pytest.raises(ConnectionError):
            sync_function()
        
        assert call_count == 3  # Should try max_retries times
        
    @pytest.mark.asyncio
    async def test_async_function_success_first_try(self):
        """Test async function success without retry"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        async def async_function():
            nonlocal call_count
            call_count += 1
            return "async success"
        
        result = await async_function()
        
        assert result == "async success"
        assert call_count == 1
        
    @pytest.mark.asyncio
    async def test_async_function_retry_then_success(self):
        """Test async function retries and succeeds"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        async def async_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return "async success after retry"
        
        result = await async_function()
        
        assert result == "async success after retry"
        assert call_count == 2
        
    @pytest.mark.asyncio
    async def test_async_function_max_retries_exceeded(self):
        """Test async function fails after max retries"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        async def async_function():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Permanent timeout")
        
        with pytest.raises(TimeoutError):
            await async_function()
        
        assert call_count == 3
        
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff delays increase correctly"""
        call_times = []
        
        @retry_with_backoff(max_retries=3, base_delay=0.1, exponential_base=2.0)
        def sync_function():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("Retry")
            return "success"
        
        result = sync_function()
        
        assert result == "success"
        assert len(call_times) == 3
        
        # Check delays (approximately)
        # Delay 1: 0.1s
        # Delay 2: 0.2s
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        # Allow some tolerance
        assert 0.05 < delay1 < 0.15  # ~0.1s
        assert 0.15 < delay2 < 0.25  # ~0.2s
        
    def test_exception_filtering(self):
        """Test that only specified exceptions are retried"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1, exceptions=(ConnectionError,))
        def sync_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Should not retry this")
            return "success"
        
        # ValueError should not be retried
        with pytest.raises(ValueError):
            sync_function()
        
        assert call_count == 1  # Only called once
        
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        call_times = []
        
        @retry_with_backoff(max_retries=5, base_delay=1.0, max_delay=2.0, exponential_base=2.0)
        def sync_function():
            call_times.append(time.time())
            if len(call_times) < 5:
                raise Exception("Retry")
            return "success"
        
        result = sync_function()
        
        assert result == "success"
        
        # Check that delays are capped
        # Delay 3 and 4 should be capped at 2.0s
        delay3 = call_times[3] - call_times[2]
        delay4 = call_times[4] - call_times[3]
        
        assert delay3 < 2.5  # Should be capped at ~2.0s
        assert delay4 < 2.5


class TestCircuitBreaker:
    """Test suite for CircuitBreaker pattern"""
    
    def test_circuit_breaker_closed_initially(self):
        """Test that circuit breaker starts in CLOSED state"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
        
        assert breaker.state == "CLOSED"
        assert not breaker.is_open()
        
    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
        
        # Record failures
        breaker.record_failure()
        assert breaker.state == "CLOSED"
        
        breaker.record_failure()
        assert breaker.state == "CLOSED"
        
        breaker.record_failure()
        assert breaker.state == "OPEN"
        assert breaker.is_open()
        
    def test_circuit_breaker_resets_on_success(self):
        """Test that success resets failure count"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
        
        # Record some failures
        breaker.record_failure()
        breaker.record_failure()
        
        # Record success
        breaker.record_success()
        
        # Failure count should be reset
        assert breaker.failure_count == 0
        
    def test_circuit_breaker_half_open_after_timeout(self):
        """Test that circuit breaker moves to HALF_OPEN after timeout"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.5)
        
        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        
        # Wait for timeout
        time.sleep(0.6)
        
        # Should transition to HALF_OPEN
        is_open = breaker.is_open()
        assert not is_open
        assert breaker.state == "HALF_OPEN"
        
    def test_circuit_breaker_closes_after_half_open_success(self):
        """Test that circuit breaker closes after successful HALF_OPEN test"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.5, half_open_attempts=1)
        
        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        
        # Wait and transition to HALF_OPEN
        time.sleep(0.6)
        breaker.is_open()  # Triggers transition
        
        # Record success in HALF_OPEN
        breaker.record_success()
        
        # Should be CLOSED now
        assert breaker.state == "CLOSED"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
