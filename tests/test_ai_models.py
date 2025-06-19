"""
Tests for Multi-AI Model System

This module contains comprehensive tests for the AI model abstraction layer,
including all supported backends and fallback mechanisms.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_models import (
    AIModelManager, AIModelConfig, AIModelType, AIResponse,
    BaseAIModel, SpacyTransformersModel, OpenAIModel, 
    AnthropicModel, LocalLlamaModel
)


class TestAIResponse:
    """Test AIResponse data structure."""
    
    def test_ai_response_creation(self):
        """Test creating AIResponse instance."""
        response = AIResponse(
            content="Analysis completed",
            confidence=0.85,
            model_used="gpt-3.5-turbo",
            processing_time=1.2,
            token_usage={"input": 50, "output": 30}
        )
        
        assert response.content == "Analysis completed"
        assert response.confidence == 0.85
        assert response.model_used == "gpt-3.5-turbo"
        assert response.processing_time == 1.2
        assert response.token_usage["input"] == 50
    
    def test_ai_response_defaults(self):
        """Test AIResponse with minimal required fields."""
        response = AIResponse(
            content="Basic response",
            confidence=0.0,
            model_used="unknown",
            processing_time=0.0
        )
        
        assert response.content == "Basic response"
        assert response.confidence == 0.0
        assert response.model_used == "unknown"
        assert response.processing_time == 0.0
        assert response.token_usage is None
        assert response.error is None


class TestAIModelConfig:
    """Test AI model configuration."""
    
    def test_config_creation(self):
        """Test creating AI model configuration."""
        config = AIModelConfig(
            model_type=AIModelType.OPENAI_GPT,
            api_key="test-key",
            model_name="gpt-4",
            max_tokens=2000,
            temperature=0.8
        )
        
        assert config.model_type == AIModelType.OPENAI_GPT
        assert config.api_key == "test-key"
        assert config.model_name == "gpt-4"
        assert config.max_tokens == 2000
        assert config.temperature == 0.8
    
    def test_config_defaults(self):
        """Test configuration default values."""
        config = AIModelConfig(
            model_type=AIModelType.SPACY_TRANSFORMERS
        )
        
        assert config.model_type == AIModelType.SPACY_TRANSFORMERS
        assert config.api_key is None
        assert config.api_base is None
        assert config.max_tokens == 1000
        assert config.temperature == 0.7
        assert config.timeout == 30
        assert config.additional_params == {}


class TestSpacyTransformersModel:
    """Test SpaCy+Transformers model implementation."""
    
    @pytest.fixture
    def spacy_model(self):
        """Create SpaCy model for testing."""
        config = AIModelConfig(
            model_type=AIModelType.SPACY_TRANSFORMERS,
            model_name="spacy_transformers",
            enabled=True
        )
        return SpacyTransformersModel(config)
    
    def test_spacy_model_initialization(self, spacy_model):
        """Test SpaCy model initialization."""
        assert spacy_model.model_type == AIModelType.SPACY_TRANSFORMERS
        assert spacy_model.config.model_name == "spacy_transformers"
        assert spacy_model.config.enabled is True
    
    def test_spacy_model_validation(self, spacy_model):
        """Test SpaCy model connection validation."""
        # This should always pass for SpaCy model
        assert spacy_model.validate_connection() is True
    
    @patch('spacy.load')
    def test_spacy_model_analysis(self, mock_spacy_load, spacy_model):
        """Test SpaCy model analysis."""
        # Mock spaCy model
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.ents = []
        mock_nlp.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp
        
        response = spacy_model.analyze_request(
            request_text="Create a small cube",
            context={},
            analysis_depth="standard"
        )
        
        assert isinstance(response, AIResponse)
        assert response.model_used == "spacy_transformers"


class TestOpenAIModel:
    """Test OpenAI GPT model implementation."""
    
    @pytest.fixture
    def openai_config(self):
        """Create OpenAI configuration."""
        return AIModelConfig(
            model_type=AIModelType.OPENAI_GPT,
            model_name="gpt-3.5-turbo",
            api_key="test-api-key",
            enabled=True
        )
    
    @pytest.fixture
    def openai_model(self, openai_config):
        """Create OpenAI model for testing."""
        return OpenAIModel(openai_config)
    
    def test_openai_model_initialization(self, openai_model):
        """Test OpenAI model initialization."""
        assert openai_model.model_type == AIModelType.OPENAI_GPT
        assert openai_model.config.model_name == "gpt-3.5-turbo"
    
    @patch('openai.OpenAI')
    def test_openai_validation_success(self, mock_openai_class, openai_model):
        """Test successful OpenAI validation."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.models.list.return_value = Mock()
        
        assert openai_model.validate_connection() is True
    
    @patch('openai.OpenAI')
    def test_openai_validation_failure(self, mock_openai_class, openai_model):
        """Test OpenAI validation failure."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.models.list.side_effect = Exception("API Error")
        
        assert openai_model.validate_connection() is False
    
    @patch('openai.OpenAI')
    def test_openai_analysis(self, mock_openai_class, openai_model):
        """Test OpenAI model analysis."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        {
            "object_type": "cube",
            "dimensions": {"x": 20.0, "y": 20.0, "z": 20.0},
            "material_type": "pla",
            "confidence": 0.9
        }
        """
        mock_client.chat.completions.create.return_value = mock_response
        
        response = openai_model.analyze_request(
            request_text="Create a small cube",
            context={},
            analysis_depth="standard"
        )
        
        assert isinstance(response, AIResponse)
        assert response.success is True
        assert response.model_used == "gpt-3.5-turbo"


class TestAnthropicModel:
    """Test Anthropic Claude model implementation."""
    
    @pytest.fixture
    def anthropic_config(self):
        """Create Anthropic configuration."""
        return AIModelConfig(
            model_type=AIModelType.ANTHROPIC_CLAUDE,
            model_name="claude-3-sonnet-20240229",
            api_key="test-api-key",
            enabled=True
        )
    
    @pytest.fixture
    def anthropic_model(self, anthropic_config):
        """Create Anthropic model for testing."""
        return AnthropicModel(anthropic_config)
    
    def test_anthropic_model_initialization(self, anthropic_model):
        """Test Anthropic model initialization."""
        assert anthropic_model.model_type == AIModelType.ANTHROPIC_CLAUDE
        assert anthropic_model.config.model_name == "claude-3-sonnet-20240229"
    
    @patch('anthropic.Anthropic')
    def test_anthropic_validation_success(self, mock_anthropic_class, anthropic_model):
        """Test successful Anthropic validation."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock a simple completion to test connection
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "test"
        mock_client.messages.create.return_value = mock_response
        
        assert anthropic_model.validate_connection() is True
    
    @patch('anthropic.Anthropic')
    def test_anthropic_analysis(self, mock_anthropic_class, anthropic_model):
        """Test Anthropic model analysis."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = """
        {
            "object_type": "cube",
            "dimensions": {"x": 20.0, "y": 20.0, "z": 20.0},
            "material_type": "pla",
            "confidence": 0.85
        }
        """
        mock_client.messages.create.return_value = mock_response
        
        response = anthropic_model.analyze_request(
            request_text="Create a small cube",
            context={},
            analysis_depth="standard"
        )
        
        assert isinstance(response, AIResponse)
        assert response.success is True
        assert response.model_used == "claude-3-sonnet-20240229"


class TestLocalLlamaModel:
    """Test Local Llama model implementation."""
    
    @pytest.fixture
    def llama_config(self):
        """Create Local Llama configuration."""
        return AIModelConfig(
            model_type=AIModelType.LOCAL_LLAMA,
            model_name="llama2:7b",
            api_url="http://localhost:11434",
            enabled=True
        )
    
    @pytest.fixture
    def llama_model(self, llama_config):
        """Create Local Llama model for testing."""
        return LocalLlamaModel(llama_config)
    
    def test_llama_model_initialization(self, llama_model):
        """Test Local Llama model initialization."""
        assert llama_model.model_type == AIModelType.LOCAL_LLAMA
        assert llama_model.config.model_name == "llama2:7b"
    
    @patch('requests.get')
    def test_llama_validation_success(self, mock_get, llama_model):
        """Test successful Local Llama validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ollama is running"}
        mock_get.return_value = mock_response
        
        assert llama_model.validate_connection() is True
    
    @patch('requests.post')
    def test_llama_analysis(self, mock_post, llama_model):
        """Test Local Llama model analysis."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": """
            {
                "object_type": "cube",
                "dimensions": {"x": 20.0, "y": 20.0, "z": 20.0},
                "material_type": "pla",
                "confidence": 0.8
            }
            """
        }
        mock_post.return_value = mock_response
        
        response = llama_model.analyze_request(
            request_text="Create a small cube",
            context={},
            analysis_depth="standard"
        )
        
        assert isinstance(response, AIResponse)
        assert response.success is True
        assert response.model_used == "llama2:7b"


class TestAIModelManager:
    """Test AI Model Manager orchestration."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary configuration file."""
        config_content = """
ai_models:
  spacy_transformers:
    type: "spacy_transformers"
    model_name: "spacy_model"
    enabled: true
    priority: 1
  
  openai_gpt:
    type: "openai_gpt"
    model_name: "gpt-3.5-turbo"
    api_key: "test-key"
    enabled: true
    priority: 2
  
  local_llama:
    type: "local_llama"
    model_name: "llama2:7b"
    api_url: "http://localhost:11434"
    enabled: false
    priority: 3

settings:
  enable_fallback: true
  confidence_threshold: 0.5
  timeout: 30
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            yield f.name
        
        os.unlink(f.name)
    
    @pytest.fixture
    def ai_manager(self, temp_config_file):
        """Create AI Model Manager for testing."""
        return AIModelManager(config_path=temp_config_file)
    
    def test_manager_initialization(self, ai_manager):
        """Test AI Model Manager initialization."""
        assert len(ai_manager.models) >= 2  # At least spacy and openai
        assert "spacy_transformers" in ai_manager.models
        assert "openai_gpt" in ai_manager.models
        assert ai_manager.enable_fallback is True
    
    def test_get_available_models(self, ai_manager):
        """Test getting available models."""
        models = ai_manager.get_available_models()
        assert len(models) >= 2
        assert "spacy_transformers" in models
        assert "openai_gpt" in models
    
    def test_set_preferred_model(self, ai_manager):
        """Test setting preferred model."""
        ai_manager.set_preferred_model("openai_gpt")
        assert ai_manager.preferred_model == "openai_gpt"
    
    def test_set_invalid_preferred_model(self, ai_manager):
        """Test setting invalid preferred model."""
        with pytest.raises(ValueError):
            ai_manager.set_preferred_model("invalid_model")
    
    @patch.object(SpacyTransformersModel, 'analyze_request')
    def test_analyze_request_success(self, mock_analyze, ai_manager):
        """Test successful request analysis."""
        mock_response = AIResponse(
            success=True,
            confidence=0.9,
            model_used="spacy_transformers",
            data={"object_type": "cube"}
        )
        mock_analyze.return_value = mock_response
        
        response = ai_manager.analyze_request(
            request_text="Create a cube",
            context={},
            analysis_depth="standard"
        )
        
        assert response.success is True
        assert response.confidence == 0.9
        assert response.model_used == "spacy_transformers"
    
    @patch.object(SpacyTransformersModel, 'analyze_request')
    @patch.object(OpenAIModel, 'analyze_request')
    def test_fallback_mechanism(self, mock_openai_analyze, mock_spacy_analyze, ai_manager):
        """Test fallback mechanism when primary model fails."""
        # First model fails
        mock_spacy_analyze.side_effect = Exception("Model unavailable")
        
        # Second model succeeds
        mock_openai_response = AIResponse(
            success=True,
            confidence=0.8,
            model_used="gpt-3.5-turbo",
            data={"object_type": "cube"}
        )
        mock_openai_analyze.return_value = mock_openai_response
        
        response = ai_manager.analyze_request(
            request_text="Create a cube",
            context={},
            analysis_depth="standard"
        )
        
        assert response.success is True
        assert response.model_used == "gpt-3.5-turbo"


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""
    
    def test_no_models_available(self):
        """Test behavior when no models are available."""
        manager = AIModelManager()
        manager.models = {}  # Clear all models
        
        response = manager.analyze_request(
            request_text="Create a cube",
            context={},
            analysis_depth="standard"
        )
        
        assert response.success is False
        assert "No AI models available" in response.error_message
    
    def test_all_models_fail(self):
        """Test behavior when all models fail."""
        config = AIModelConfig(
            model_type=AIModelType.SPACY_TRANSFORMERS,
            model_name="failing_model",
            enabled=True
        )
        
        with patch.object(SpacyTransformersModel, 'analyze_request') as mock_analyze:
            mock_analyze.side_effect = Exception("All models failed")
            
            manager = AIModelManager()
            manager.models = {"failing_model": SpacyTransformersModel(config)}
            
            response = manager.analyze_request(
                request_text="Create a cube",
                context={},
                analysis_depth="standard"
            )
            
            assert response.success is False
            assert "analysis failed" in response.error_message.lower()
    
    def test_config_file_not_found(self):
        """Test handling missing configuration file."""
        # Should initialize with default SpaCy model
        manager = AIModelManager(config_path="nonexistent_file.yaml")
        assert len(manager.models) >= 1
        assert any(model.model_type == AIModelType.SPACY_TRANSFORMERS 
                  for model in manager.models.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
