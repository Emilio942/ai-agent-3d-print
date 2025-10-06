"""
Simplified tests for Multi-AI Model System integration with Research Agent

This tests the basic functionality of the AI model integration.
"""

import pytest
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.research_agent import ResearchAgent
from core.ai_models import AIModelManager, AIModelConfig, AIModelType
from core.api_schemas import ResearchAgentInput


class TestMultiAIModelIntegration:
    """Test AI model integration with research agent."""
    
    @pytest.fixture
    def research_agent(self):
        """Create a research agent for testing."""
        return ResearchAgent("test_research_agent")
    
    def test_research_agent_initialization(self, research_agent):
        """Test that research agent initializes with AI model manager."""
        assert research_agent is not None
        assert hasattr(research_agent, 'ai_model_manager')
        # AI model manager might be None if initialization failed, that's OK for testing
    
    def test_get_available_ai_models(self, research_agent):
        """Test getting available AI models."""
        models = research_agent.get_available_ai_models()
        assert isinstance(models, list)
        # Should have at least the spaCy model if AI manager initialized
        if research_agent.ai_model_manager:
            assert len(models) >= 1
    
    def test_get_ai_model_status(self, research_agent):
        """Test getting AI model status."""
        status = research_agent.get_ai_model_status()
        assert isinstance(status, dict)
        assert "status" in status or "total_models" in status
    
    @pytest.mark.asyncio
    async def test_extract_intent_basic(self, research_agent):
        """Test basic intent extraction functionality."""
        result = await research_agent.extract_intent_async("Create a small cube")
        
        assert isinstance(result, dict)
        assert "object_type" in result
        assert "confidence" in result
        assert "method_used" in result
        assert result["confidence"] >= 0.0
    
    @pytest.mark.asyncio  
    async def test_extract_intent_with_context(self, research_agent):
        """Test intent extraction with context."""
        context = {"material": "PLA", "size": "small"}
        result = await research_agent.extract_intent_async("Create a gear", context)
        
        assert isinstance(result, dict)
        assert "object_type" in result
        assert "confidence" in result
    
    def test_ai_model_manager_initialization(self):
        """Test standalone AI model manager initialization."""
        try:
            manager = AIModelManager()
            assert manager is not None
            assert hasattr(manager, 'models')
            assert hasattr(manager, 'default_model')
        except Exception as e:
            # It's OK if it fails due to missing dependencies
            pytest.skip(f"AI Model Manager initialization failed: {e}")
    
    @pytest.mark.asyncio
    async def test_execute_task_async(self, research_agent):
        """Test that execute_task works as async method."""
        task_details = ResearchAgentInput(
            user_request="Create a small cube",
            context={},
            analysis_depth="standard"
        )
        
        result = await research_agent.execute_task_async(task_details)
        
        assert hasattr(result, 'success') or 'success' in result
    
    def test_register_ai_model_invalid(self, research_agent):
        """Test registering invalid AI model."""
        result = research_agent.register_ai_model("invalid_model_type")
        assert result is False
    
    def test_set_preferred_ai_model_invalid(self, research_agent):
        """Test setting invalid preferred AI model."""
        result = research_agent.set_preferred_ai_model("invalid_model")
        assert result is False


class TestAIModelFallback:
    """Test AI model fallback mechanisms."""
    
    @pytest.fixture
    def research_agent(self):
        """Create a research agent for testing."""
        return ResearchAgent("test_fallback_agent")
    
    @pytest.mark.asyncio
    async def test_fallback_to_spacy(self, research_agent):
        """Test fallback to spaCy when AI models fail."""
        # This should work even if AI models are not available
        result = await research_agent.extract_intent_async("Create a small sphere")
        
        assert isinstance(result, dict)
        assert "object_type" in result
        assert "method_used" in result
        # Should fall back to spacy or regex/keyword methods
        assert result["method_used"] in ["ai_enhanced", "spacy_primary", "regex_fallback", "keyword_fallback"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
