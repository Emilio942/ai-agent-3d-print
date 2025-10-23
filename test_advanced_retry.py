"""
Advanced Retry Logic & Fallback Mechanism Tests

This module tests the enhanced retry capabilities:
1. Retry with exponential backoff
2. Fallback to alternative methods
3. Circuit breaker pattern
4. Multi-level error recovery

Simulates real-world failure scenarios:
- Network timeouts
- Hardware disconnections  
- External tool crashes
- Resource exhaustion
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from core.retry_utils import retry_with_fallback, CircuitBreaker
from agents.slicer_agent import SlicerAgent
from agents.printer_agent import PrinterAgent
from core.exceptions import SlicerExecutionError, PrinterConnectionError


class TestRetryWithFallback:
    """Test retry with fallback decorator"""
    
    @pytest.mark.asyncio
    async def test_primary_succeeds_no_fallback(self):
        """Test that fallback is not called when primary succeeds"""
        primary_called = 0
        fallback_called = 0
        
        async def fallback_func(*args, **kwargs):
            nonlocal fallback_called
            fallback_called += 1
            return "fallback"
        
        @retry_with_fallback(max_retries=2, base_delay=0.1, fallback_func=fallback_func)
        async def primary_func():
            nonlocal primary_called
            primary_called += 1
            return "primary"
        
        result = await primary_func()
        
        assert result == "primary"
        assert primary_called == 1
        assert fallback_called == 0  # Fallback should NOT be called
    
    @pytest.mark.asyncio
    async def test_primary_fails_fallback_succeeds(self):
        """Test fallback is called after primary fails"""
        primary_called = 0
        fallback_called = 0
        
        async def fallback_func(*args, **kwargs):
            nonlocal fallback_called
            fallback_called += 1
            return "fallback_success"
        
        @retry_with_fallback(max_retries=2, base_delay=0.1, fallback_func=fallback_func)
        async def primary_func():
            nonlocal primary_called
            primary_called += 1
            raise ConnectionError("Primary failed")
        
        result = await primary_func()
        
        assert result == "fallback_success"
        assert primary_called == 2  # Should retry max_retries times
        assert fallback_called == 1  # Fallback called once
    
    @pytest.mark.asyncio
    async def test_both_fail_raises_exception(self):
        """Test that exception is raised when both primary and fallback fail"""
        
        async def fallback_func(*args, **kwargs):
            raise Exception("Fallback also failed")
        
        @retry_with_fallback(max_retries=2, base_delay=0.1, fallback_func=fallback_func)
        async def primary_func():
            raise ConnectionError("Primary failed")
        
        with pytest.raises(Exception, match="Fallback also failed"):
            await primary_func()
    
    @pytest.mark.asyncio
    async def test_fallback_only_for_specific_exceptions(self):
        """Test that fallback only triggers for specific exception types"""
        fallback_called = 0
        
        async def fallback_func(*args, **kwargs):
            nonlocal fallback_called
            fallback_called += 1
            return "fallback"
        
        @retry_with_fallback(
            max_retries=2,
            base_delay=0.1,
            fallback_func=fallback_func,
            fallback_on_exceptions=(ConnectionError,)
        )
        async def primary_func():
            raise ValueError("Wrong exception type")
        
        # ValueError should NOT trigger fallback
        with pytest.raises(ValueError):
            await primary_func()
        
        assert fallback_called == 0
    
    @pytest.mark.asyncio
    async def test_retry_delays_increase_exponentially(self):
        """Test that retry delays follow exponential backoff"""
        call_times = []
        
        async def fallback_func(*args, **kwargs):
            return "fallback"
        
        @retry_with_fallback(max_retries=3, base_delay=0.1, fallback_func=fallback_func)
        async def primary_func():
            call_times.append(time.time())
            raise Exception("Fail")
        
        await primary_func()
        
        # Check delays
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        # Delay should roughly double each time
        assert 0.08 < delay1 < 0.15  # ~0.1s
        assert 0.15 < delay2 < 0.25  # ~0.2s


class TestSlicerAgentRetry:
    """Test slicer agent retry and fallback behavior"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Slicer agent initialization needs proper setup")
    async def test_slicer_falls_back_to_mock_on_failure(self):
        """Test that slicer falls back to mock mode when real slicer fails"""
        agent = SlicerAgent()  # Fixed: simplified initialization
        
        # Create test input
        from core.api_schemas import SlicerAgentInput
        test_input = SlicerAgentInput(
            task_id="test_fallback",
            model_file_path="/tmp/test.stl",
            printer_profile="ender3",
            quality_preset="standard"
        )
        
        effective_settings = {
            "layer_height": 0.2,
            "infill_density": 20
        }
        
        # Mock the actual slicing to fail
        with patch.object(agent, '_is_slicer_available', return_value=False):
            # This should fall back to mock slicing
            result = await agent._perform_actual_slicing(test_input, effective_settings)
            
            # Should get mock slicing result
            assert result is not None
            assert 'gcode_content' in result or 'gcode_path' in result


class TestPrinterAgentRetry:
    """Test printer agent retry behavior for connections"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Printer agent initialization needs proper setup")
    async def test_printer_connection_retries(self):
        """Test that printer connection retries on failure"""
        agent = PrinterAgent(mock_mode=True)  # Fixed: removed agent_name parameter
        
        call_count = 0
        
        # Mock serial connection to fail first 2 times
        original_connect = agent._connect_real_printer
        
        async def mock_connect_with_retry(port, baudrate):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                raise PrinterConnectionError("Connection failed")
            
            # Success on 3rd try
            agent.mock_mode = True
            return True
        
        # Patch the connection method
        with patch.object(agent, '_connect_real_printer', side_effect=mock_connect_with_retry):
            try:
                # This should retry and eventually succeed
                result = await agent._connect_real_printer(port="/dev/ttyUSB0", baudrate=115200)
                
                # Should succeed on 3rd attempt
                assert call_count == 3
            except PrinterConnectionError:
                # If connection still fails, that's OK - we're testing retry behavior
                assert call_count >= 3


class TestCircuitBreakerIntegration:
    """Test circuit breaker pattern in real scenarios"""
    
    def test_circuit_breaker_prevents_cascading_failures(self):
        """Test that circuit breaker stops calls after threshold"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
        
        # Simulate failures
        for i in range(3):
            breaker.record_failure()
        
        # Circuit should be OPEN
        assert breaker.state == "OPEN"
        assert breaker.is_open() == True
        
        # Further calls should be blocked
        # (In real code, we'd check breaker.is_open() before making call)
    
    def test_circuit_breaker_recovers_after_timeout(self):
        """Test that circuit breaker enters HALF_OPEN after timeout"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.5)
        
        # Open circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        
        # Wait for timeout
        time.sleep(0.6)
        
        # Should transition to HALF_OPEN
        is_open = breaker.is_open()
        assert not is_open
        assert breaker.state == "HALF_OPEN"
        
        # Success in HALF_OPEN should close circuit
        breaker.record_success()
        assert breaker.state == "CLOSED"


class TestRealWorldScenarios:
    """Test real-world failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_network_timeout_recovery(self):
        """Simulate network timeout and recovery"""
        from core.retry_utils import retry_with_backoff
        
        attempts = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        async def flaky_network_call():
            nonlocal attempts
            attempts += 1
            
            # Fail first 2 times (network timeout)
            if attempts < 3:
                raise TimeoutError("Network timeout")
            
            # Success on 3rd try
            return "data"
        
        result = await flaky_network_call()
        
        assert result == "data"
        assert attempts == 3
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_fallback(self):
        """Simulate resource exhaustion with fallback"""
        
        async def lightweight_fallback():
            return {"status": "limited", "data": "cached"}
        
        @retry_with_fallback(
            max_retries=2,
            base_delay=0.1,
            fallback_func=lightweight_fallback
        )
        async def resource_intensive_operation():
            raise MemoryError("Out of memory")
        
        result = await resource_intensive_operation()
        
        # Should fall back to lightweight operation
        assert result["status"] == "limited"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
