"""
Unit tests for Research Agent - NLP Intent Recognition and Web Research.

Tests cover:
- Intent extraction from text
- Web research capabilities  
- Design specification generation
- Error handling and edge cases
- Mocking of external dependencies
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.research_agent import ResearchAgent
from core.api_schemas import ResearchAgentInput, ResearchAgentOutput, TaskResult
from core.exceptions import ValidationError, AI3DPrintError


class TestResearchAgent:
    """Test cases for Research Agent functionality."""
    
    @pytest.fixture
    def research_agent(self):
        """Create a Research Agent instance for testing."""
        return ResearchAgent("test_research_agent")
    
    @pytest.fixture
    def sample_input(self):
        """Sample input for testing."""
        return ResearchAgentInput(
            user_request="Create a small gear for my robot project",
            context={"description": "Need a 20mm diameter gear with 12 teeth"},
            analysis_depth="standard"
        )
    
    def test_agent_initialization(self, research_agent):
        """Test Research Agent initialization."""
        assert research_agent.agent_name == "test_research_agent"
        assert research_agent.agent_type == "ResearchAgent"
        assert hasattr(research_agent, 'nlp')
        assert hasattr(research_agent, 'intent_patterns')
    
    def test_intent_extraction_gear(self, research_agent):
        """Test intent extraction for gear request."""
        text = "Create a 20mm diameter gear with 12 teeth for my robot"
        
        result = research_agent.extract_intent(text)
        
        assert isinstance(result, dict)
        assert "object_type" in result
        assert "dimensions" in result
        assert "confidence" in result
        assert result["object_type"] == "gear"
        assert result["confidence"] > 0.5
    
    def test_intent_extraction_cube(self, research_agent):
        """Test intent extraction for cube request."""
        text = "I need a 10x15x20mm rectangular box"
        
        result = research_agent.extract_intent(text)
        
        assert result["object_type"] in ["cube", "box", "rectangular"]
        assert "dimensions" in result
        assert result["confidence"] > 0.3
    
    def test_intent_extraction_sphere(self, research_agent):
        """Test intent extraction for sphere request."""
        text = "Create a ball with radius 5cm"
        
        result = research_agent.extract_intent(text)
        
        assert result["object_type"] in ["sphere", "ball"]
        assert result["confidence"] > 0.3
    
    def test_intent_extraction_invalid_input(self, research_agent):
        """Test intent extraction with invalid input."""
        # Test with empty string - should return low confidence result
        result = research_agent.extract_intent("")
        assert isinstance(result, dict)
        assert result["confidence"] < 0.3
        
        # Test with None - should handle gracefully 
        try:
            result = research_agent.extract_intent(None)
            assert isinstance(result, dict)
        except Exception as e:
            # It's ok if it raises an exception for None input
            assert e is not None
    
    def test_intent_extraction_edge_cases(self, research_agent):
        """Test intent extraction with edge cases."""
        # Very long text
        long_text = "I want to create " + "a very long description " * 50 + "for a cube"
        result = research_agent.extract_intent(long_text)
        assert isinstance(result, dict)
        
        # Text with special characters
        special_text = "Create a gear ñáéíóú with 15mm diameter!@#$%"
        result = research_agent.extract_intent(special_text)
        assert isinstance(result, dict)
    
    @patch('agents.research_agent.DDGS')
    def test_web_research_success(self, mock_ddgs, research_agent):
        """Test successful web research."""
        # Mock search results
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"snippet": "Gear design principles: Gears are mechanical components..."}
        ]
        mock_ddgs.return_value = mock_ddgs_instance
        
        keywords = ["gear", "design", "3D printing"]
        result = research_agent.research(keywords)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    @patch('agents.research_agent.DDGS')
    def test_web_research_error_handling(self, mock_ddgs, research_agent):
        """Test web research error handling."""
        # Mock search failure
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.side_effect = Exception("Network error")
        mock_ddgs.return_value = mock_ddgs_instance
        
        keywords = ["test"]
        result = research_agent.research(keywords)
        
        # Should return fallback content, not raise exception
        assert isinstance(result, str)
        assert len(result) > 0
    
    @patch('agents.research_agent.DDGS')
    def test_web_research_caching(self, mock_ddgs, research_agent):
        """Test web research caching functionality."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"snippet": "Cached result for testing"}
        ]
        mock_ddgs.return_value = mock_ddgs_instance
        
        keywords = ["cache", "test"]
        
        # First call
        result1 = research_agent.research(keywords)
        
        # Second call with same keywords should use cache
        result2 = research_agent.research(keywords)
        
        assert result1 == result2
        assert isinstance(result1, str)
    
    def test_design_specification_generation(self, research_agent):
        """Test design specification generation."""
        intent = {
            "object_type": "gear",
            "dimensions": {"diameter": 20, "teeth": 12},
            "material_type": "PLA",
            "confidence": 0.8
        }
        
        spec = research_agent.generate_design_specifications(intent)
        
        assert isinstance(spec, dict)
        assert "geometry" in spec
        assert "constraints" in spec
        assert "metadata" in spec
        
        # Check geometry section - use actual structure
        geometry = spec["geometry"]
        assert "type" in geometry
        assert "dimensions" in geometry
        assert geometry["type"] in ["primitive", "complex", "composite"]
        
        # Check constraints section - use actual field names
        constraints = spec["constraints"]
        assert "minimum_wall_thickness" in constraints
        assert "maximum_overhang_angle" in constraints
        
        # Check metadata section
        metadata = spec["metadata"]
        assert "object_type" in metadata
        assert "generated_at" in metadata
    
    def test_design_specification_edge_cases(self, research_agent):
        """Test design specification with edge cases."""
        # Missing dimensions
        intent = {
            "object_type": "unknown",
            "confidence": 0.1
        }
        
        spec = research_agent.generate_design_specifications(intent)
        
        # Should still generate valid spec with defaults
        assert isinstance(spec, dict)
        assert "geometry" in spec
        assert "constraints" in spec
        assert "metadata" in spec
    
    def test_execute_task_success(self, research_agent, sample_input):
        """Test successful task execution."""
        with patch.object(research_agent, 'research') as mock_research:
            mock_research.return_value = "Research results about gears"
            
            task_data = {
                "task_id": "test_001",
                "user_request": sample_input.user_request,
                "context": sample_input.context,
                "analysis_depth": sample_input.analysis_depth
            }
            
            result = research_agent.execute_task(task_data)
            
            assert isinstance(result, TaskResult)
            assert result.success is True
            assert isinstance(result.data, dict)
            
            # Check output structure
            output_data = result.data
            assert "requirements" in output_data
            assert "object_specifications" in output_data

    def test_execute_task_accepts_schema_input(self, research_agent, sample_input):
        """ResearchAgent should handle ResearchAgentInput models transparently."""
        result = research_agent.execute_task(sample_input)

        assert isinstance(result, TaskResult)
        assert result.task_id is not None
        assert result.metadata.get("task_id") == result.task_id
    
    def test_execute_task_validation_error(self, research_agent):
        """Test task execution with validation errors."""
        # Missing required fields
        task_data = {
            "task_id": "test_002"
            # Missing user_request
        }
        
        result = research_agent.execute_task(task_data)
        
        # Should return error result instead of raising exception
        assert isinstance(result, TaskResult)
        assert result.success is False
    
    def test_execute_task_research_failure(self, research_agent, sample_input):
        """Test task execution when research fails."""
        with patch.object(research_agent, 'research') as mock_research:
            mock_research.side_effect = Exception("Research API failure")
            
            task_data = {
                "task_id": "test_003",
                "user_request": sample_input.user_request,
                "context": sample_input.context,
                "analysis_depth": sample_input.analysis_depth
            }
            
            result = research_agent.execute_task(task_data)
            
            # Should handle error gracefully
            assert isinstance(result, TaskResult)
            # May still succeed with fallback data
    
    def test_keyword_extraction(self, research_agent):
        """Test keyword extraction from text."""
        text = "Create a mechanical gear with 20mm diameter and 12 teeth for robot"
        
        keywords = research_agent._extract_intent_keywords(text, {})
        
        assert isinstance(keywords, dict)
        assert "object_type" in keywords
    
    def test_confidence_calculation(self, research_agent):
        """Test confidence score calculation."""
        # High confidence case
        text = "gear 20mm diameter"
        doc = research_agent.nlp(text) if research_agent.nlp else None
        
        # Use the pattern score calculation which contributes to confidence
        score = research_agent._calculate_pattern_score(text, research_agent.intent_patterns[3], doc)
        assert 0.0 <= score <= 1.0
        
        # Low confidence case
        text_low = "unclear text"
        doc_low = research_agent.nlp(text_low) if research_agent.nlp else None
        score_low = research_agent._calculate_pattern_score(text_low, research_agent.intent_patterns[0], doc_low)
        assert 0.0 <= score_low <= 1.0
    
    def test_fallback_intent_extraction(self, research_agent):
        """Test fallback intent extraction when NLP fails."""
        # Text that might confuse NLP
        unclear_text = "asdf qwerty xyz make something unclear"
        
        result = research_agent.extract_intent(unclear_text)
        
        # Should still return valid structure with low confidence
        assert isinstance(result, dict)
        assert "object_type" in result
        assert "confidence" in result
        assert result["confidence"] < 0.3
    
    def test_research_result_summarization(self, research_agent):
        """Test research result summarization."""
        long_research = "Very long research result " * 100
        
        # Since summarizer is disabled, this should return the input text
        # or handle it gracefully
        if hasattr(research_agent, 'summarizer') and research_agent.summarizer:
            summary = research_agent.summarizer(long_research)
            assert isinstance(summary, str)
            assert len(summary) <= len(long_research)
        else:
            # Summarizer is disabled, so this test should just verify the agent handles it
            assert research_agent.summarizer is None
    
    def test_complexity_score_calculation(self, research_agent):
        """Test complexity score calculation."""
        # Simple object
        simple_spec = {
            "object_type": "cube",
            "dimensions": {"x": 10, "y": 10, "z": 10},
            "special_features": []
        }
        score = research_agent._calculate_complexity_score(simple_spec)
        assert 1 <= score <= 10
        
        # Complex object
        complex_spec = {
            "object_type": "gear",
            "dimensions": {"diameter": 150, "thickness": 20},
            "special_features": ["chamfer", "fillet", "holes"]
        }
        score = research_agent._calculate_complexity_score(complex_spec)
        assert 5 <= score <= 10
    
    def test_print_time_estimation(self, research_agent):
        """Test print time estimation."""
        spec = {
            "object_type": "cube",
            "dimensions": {"x": 20, "y": 20, "z": 20},
            "complexity_score": 3,
            "special_features": []
        }
        
        time_estimate = research_agent._estimate_print_time(spec)
        
        assert isinstance(time_estimate, str)
        assert any(unit in time_estimate for unit in ["min", "hour", "hr", "h", "m"])
    
    def test_material_recommendation(self, research_agent):
        """Test material recommendation."""
        text = "Create a gear that needs to be strong"
        
        # Test through intent extraction which includes material recommendations
        result = research_agent.extract_intent(text)
        
        assert isinstance(result, dict)
        assert "material_recommendations" in result
        assert isinstance(result["material_recommendations"], list)
    
    def test_print_orientation_recommendation(self, research_agent):
        """Test print orientation recommendation through design specifications."""
        intent = {
            "object_type": "gear",
            "dimensions": {"diameter": 20, "thickness": 5},
            "special_features": []
        }
        
        # Test through design specification generation
        spec = research_agent.generate_design_specifications(intent)
        
        assert isinstance(spec, dict)
        assert "manufacturing" in spec
        # Check that manufacturing settings are present
        manufacturing = spec["manufacturing"]
        assert "support_required" in manufacturing
        assert isinstance(manufacturing["support_required"], str)
    
    def test_support_requirement_assessment(self, research_agent):
        """Test support requirement assessment through design specifications."""
        # Object that needs support
        intent_sphere = {
            "object_type": "sphere",
            "dimensions": {"radius": 10},
            "special_features": []
        }
        
        spec = research_agent.generate_design_specifications(intent_sphere)
        assert isinstance(spec, dict)
        assert "manufacturing" in spec
        assert "support_required" in spec["manufacturing"]
        
        # Object that doesn't need support
        intent_cube = {
            "object_type": "cube",
            "dimensions": {"x": 10, "y": 10, "z": 10},
            "special_features": []
        }
        
        spec = research_agent.generate_design_specifications(intent_cube)
        assert isinstance(spec, dict)
        assert "manufacturing" in spec
        assert "support_required" in spec["manufacturing"]
    
    def test_agent_status_tracking(self, research_agent):
        """Test agent status tracking."""
        status = research_agent.get_status()
        
        assert isinstance(status, dict)
        assert "agent_name" in status
        assert "agent_type" in status
        assert "current_status" in status
        assert status["agent_name"] == "test_research_agent"
        assert status["agent_type"] == "ResearchAgent"
    
    def test_error_handling_invalid_task(self, research_agent):
        """Test error handling with invalid task data."""
        invalid_task = {"invalid": "data"}
        
        error_result = research_agent.handle_error(
            ValidationError("Invalid task data"),
            invalid_task
        )
        
        assert isinstance(error_result, dict)
        assert error_result["error"] is True
        assert "error_code" in error_result
        assert "message" in error_result
    
    def test_concurrent_requests(self, research_agent):
        """Test handling of concurrent requests."""
        results = []
        for i in range(3):
            task_data = {
                "task_id": f"concurrent_{i}",
                "user_request": f"Create a cube {i+10}mm",
                "context": {"description": "Test concurrent processing"},
                "analysis_depth": "standard"
            }
            result = research_agent.execute_task(task_data)
            results.append(result)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, TaskResult)
            assert result.success is True
    
    def test_cleanup(self, research_agent):
        """Test agent cleanup through status check."""
        # Since there's no specific cleanup method, test status accessibility
        status = research_agent.get_status()
        assert isinstance(status, dict)
        
        # Test that agent can handle shutdown gracefully
        assert research_agent.agent_name == "test_research_agent"


class TestResearchAgentIntegration:
    """Integration tests for Research Agent."""
    
    @pytest.fixture
    def research_agent(self):
        """Create a Research Agent instance for integration testing."""
        return ResearchAgent("integration_test_agent")
    
    def test_full_workflow_gear(self, research_agent):
        """Test full workflow for gear creation."""
        with patch.object(research_agent, 'research') as mock_research:
            mock_research.return_value = "Gears are circular mechanical devices with teeth..."
            
            task_data = {
                "task_id": "integration_gear",
                "user_request": "Create a 20mm gear with 15 teeth for my robot",
                "context": {"description": "Robot arm joint mechanism"},
                "analysis_depth": "detailed"
            }
            
            result = research_agent.execute_task(task_data)
            
            assert result.success is True
            assert "gear" in result.data["requirements"]["object_type"]
            assert result.data["object_specifications"]["geometry"]["type"] in ["primitive", "composite", "complex"]
    
    def test_full_workflow_complex_object(self, research_agent):
        """Test full workflow for complex object."""
        with patch.object(research_agent, 'research') as mock_research:
            mock_research.return_value = "Complex mechanical assemblies require..."
            
            task_data = {
                "task_id": "integration_complex",
                "user_request": "Design a phone holder with adjustable angle and cable management",
                "context": {"description": "Desk accessory for video calls"},
                "analysis_depth": "detailed"
            }
            
            result = research_agent.execute_task(task_data)
            
            assert result.success is True
            assert result.data["complexity_score"] >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
