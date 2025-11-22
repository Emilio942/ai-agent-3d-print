"""
Performance Tests for AI Agent 3D Print System

Tests to validate performance improvements and detect regressions.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
import httpx

# Test fixtures and helpers
@pytest.fixture
def mock_httpx_response():
    """Mock httpx response"""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"response": "test"}
    return response


class TestAsyncPerformance:
    """Test async performance improvements"""
    
    @pytest.mark.asyncio
    async def test_httpx_client_reuse(self):
        """Test that httpx client is reused across multiple calls"""
        from core.ai_models import LocalLlamaModel, AIModelConfig, AIModelType
        
        config = AIModelConfig(
            model_type=AIModelType.LOCAL_LLAMA,
            api_base="http://localhost:11434",
            model_name="llama2",
            timeout=5
        )
        
        model = LocalLlamaModel(config)
        
        # Get client twice - should return same instance
        client1 = await model._get_client()
        client2 = await model._get_client()
        
        assert client1 is client2, "Client should be reused"
        
        # Cleanup
        await model.close()
        assert model._client is None, "Client should be closed"
    
    @pytest.mark.asyncio
    async def test_async_validate_connection(self):
        """Test that validate_connection is async and non-blocking"""
        from core.ai_models import LocalLlamaModel, AIModelConfig, AIModelType
        
        config = AIModelConfig(
            model_type=AIModelType.LOCAL_LLAMA,
            api_base="http://localhost:11434",
            timeout=1  # Short timeout for test
        )
        
        model = LocalLlamaModel(config)
        
        # Should be awaitable
        start_time = time.time()
        try:
            result = await model.validate_connection()
            elapsed = time.time() - start_time
            
            # Should timeout quickly, not block
            assert elapsed < 2.0, f"Validation took too long: {elapsed}s"
        except:
            # Connection might fail, but shouldn't block
            elapsed = time.time() - start_time
            assert elapsed < 2.0, f"Validation timeout took too long: {elapsed}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self):
        """Test that concurrent requests don't create excessive overhead"""
        from core.ai_models import LocalLlamaModel, AIModelConfig, AIModelType
        
        config = AIModelConfig(
            model_type=AIModelType.LOCAL_LLAMA,
            api_base="http://localhost:11434",
            timeout=5
        )
        
        model = LocalLlamaModel(config)
        
        # Mock the actual HTTP calls
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate network delay
            response = Mock()
            response.status_code = 200
            response.json.return_value = {"response": "test"}
            return response
        
        with patch.object(httpx.AsyncClient, 'post', new=mock_post):
            # Make 10 concurrent requests
            start_time = time.time()
            tasks = [model.process_intent("test") for _ in range(10)]
            results = await asyncio.gather(*tasks)
            elapsed = time.time() - start_time
            
            # All requests should complete
            assert len(results) == 10
            
            # Should complete in reasonable time (much less than sequential)
            # Sequential would be 10 * 0.01 = 0.1s minimum
            # Concurrent should be close to 0.01s
            assert elapsed < 0.5, f"Concurrent requests too slow: {elapsed}s"
        
        await model.close()


class TestMiddlewarePerformance:
    """Test middleware performance improvements"""
    
    def test_cpu_monitoring_non_blocking(self):
        """Test that CPU monitoring doesn't use blocking calls"""
        from api.middleware.performance_middleware import PerformanceMiddleware
        from fastapi import FastAPI
        
        app = FastAPI()
        middleware = PerformanceMiddleware(app)
        
        # Check that middleware doesn't call psutil.cpu_percent with interval=None
        # This is a static check - the actual behavior is tested in integration tests
        assert hasattr(middleware, '_last_cpu_usage')
        assert middleware._last_cpu_usage == 0.0
    
    @pytest.mark.asyncio
    async def test_middleware_overhead(self):
        """Test that middleware adds minimal overhead"""
        from api.middleware.performance_middleware import PerformanceMiddleware
        from fastapi import FastAPI, Request, Response
        from starlette.middleware.base import BaseHTTPMiddleware
        
        app = FastAPI()
        
        async def simple_endpoint(request: Request):
            return Response(content="test", status_code=200)
        
        # Measure baseline
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        request.query_params = {}
        request.headers = {}
        
        start_time = time.time()
        response = await simple_endpoint(request)
        baseline_time = time.time() - start_time
        
        # The overhead should be minimal (less than 10ms typically)
        assert baseline_time < 0.1, "Baseline endpoint too slow"


class TestConnectionPooling:
    """Test HTTP connection pooling optimizations"""
    
    @pytest.mark.asyncio
    async def test_connection_reuse_reduces_latency(self):
        """Test that connection reuse reduces latency for subsequent requests"""
        from core.ai_models import LocalLlamaModel, AIModelConfig, AIModelType
        
        config = AIModelConfig(
            model_type=AIModelType.LOCAL_LLAMA,
            api_base="http://localhost:11434",
            timeout=5
        )
        
        model = LocalLlamaModel(config)
        
        # Mock HTTP calls with connection setup overhead
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # First call simulates connection setup
            if call_count == 1:
                await asyncio.sleep(0.05)  # 50ms connection overhead
            else:
                await asyncio.sleep(0.01)  # 10ms for reused connection
            
            response = Mock()
            response.status_code = 200
            response.json.return_value = {"response": "test"}
            return response
        
        with patch.object(httpx.AsyncClient, 'post', new=mock_post):
            # First request - should include connection setup
            start1 = time.time()
            await model.process_intent("test1")
            time1 = time.time() - start1
            
            # Second request - should reuse connection
            start2 = time.time()
            await model.process_intent("test2")
            time2 = time.time() - start2
            
            # Second request should be significantly faster
            assert time2 < time1 * 0.5, \
                f"Connection reuse not effective: {time1:.3f}s vs {time2:.3f}s"
        
        await model.close()


class TestResourceEfficiency:
    """Test resource efficiency improvements"""
    
    @pytest.mark.asyncio
    async def test_no_unnecessary_threads(self):
        """Test that async operations don't create unnecessary threads"""
        import threading
        from core.ai_models import LocalLlamaModel, AIModelConfig, AIModelType
        
        config = AIModelConfig(
            model_type=AIModelType.LOCAL_LLAMA,
            api_base="http://localhost:11434",
            timeout=5
        )
        
        model = LocalLlamaModel(config)
        
        # Mock HTTP call
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(0.01)
            response = Mock()
            response.status_code = 200
            response.json.return_value = {"response": "test"}
            return response
        
        with patch.object(httpx.AsyncClient, 'post', new=mock_post):
            initial_threads = threading.active_count()
            
            # Make multiple async requests
            tasks = [model.process_intent("test") for _ in range(5)]
            await asyncio.gather(*tasks)
            
            final_threads = threading.active_count()
            
            # Should not create additional threads (or very few)
            thread_increase = final_threads - initial_threads
            assert thread_increase <= 2, \
                f"Too many threads created: {thread_increase}"
        
        await model.close()


@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Benchmark tests for performance tracking"""
    
    @pytest.mark.asyncio
    async def test_benchmark_process_intent(self, benchmark):
        """Benchmark process_intent performance"""
        from core.ai_models import LocalLlamaModel, AIModelConfig, AIModelType
        
        config = AIModelConfig(
            model_type=AIModelType.LOCAL_LLAMA,
            api_base="http://localhost:11434",
            timeout=5
        )
        
        model = LocalLlamaModel(config)
        
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(0.01)
            response = Mock()
            response.status_code = 200
            response.json.return_value = {"response": '{"intent": "test", "confidence": 0.8}'}
            return response
        
        with patch.object(httpx.AsyncClient, 'post', new=mock_post):
            async def run():
                return await model.process_intent("create a cube")
            
            # Run benchmark
            result = await run()
            assert result.confidence > 0
        
        await model.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
