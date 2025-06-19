"""
Multi-AI Model Support for AI Agent 3D Print System

This module provides an abstraction layer for multiple AI model backends,
allowing users to choose between OpenAI, Anthropic Claude, local models,
and the existing spaCy/transformers pipeline.
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

# Core imports
from core.logger import AgentLogger


class AIModelType(Enum):
    """Supported AI model types."""
    SPACY_TRANSFORMERS = "spacy_transformers"  # Current default
    OPENAI_GPT = "openai_gpt"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    LOCAL_LLAMA = "local_llama"
    LOCAL_MISTRAL = "local_mistral"


@dataclass
class AIModelConfig:
    """Configuration for AI models."""
    model_type: AIModelType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30
    additional_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}


@dataclass
class AIResponse:
    """Standardized response from AI models."""
    content: str
    confidence: float
    model_used: str
    processing_time: float
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class BaseAIModel(ABC):
    """Abstract base class for AI model implementations."""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.logger = AgentLogger(f"ai_model_{config.model_type.value}")
        
    @abstractmethod
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """
        Process user input for intent recognition.
        
        Args:
            user_input: User's natural language input
            context: Additional context information
            
        Returns:
            AIResponse with extracted intent and confidence
        """
        pass
    
    @abstractmethod
    async def enhance_research(self, query: str, context: Dict[str, Any] = None) -> AIResponse:
        """
        Enhance research queries with AI assistance.
        
        Args:
            query: Research query to enhance
            context: Additional context information
            
        Returns:
            AIResponse with enhanced query and suggestions
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate that the AI model can be reached and is properly configured.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass


class SpacyTransformersModel(BaseAIModel):
    """Current spaCy + transformers implementation."""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize spaCy and transformers models."""
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            self.logger.info("SpaCy model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load spaCy model: {e}")
            self.nlp = None
    
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """Process intent using existing spaCy pipeline."""
        import time
        start_time = time.time()
        
        try:
            # Use existing spaCy-based intent extraction
            # This would integrate with the existing research_agent logic
            confidence = 0.8  # Placeholder - use actual extraction logic
            
            # Extract entities and patterns
            if self.nlp:
                doc = self.nlp(user_input)
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                
                # Basic intent classification
                intent_keywords = {
                    "cube": ["cube", "box", "square", "rectangular"],
                    "cylinder": ["cylinder", "tube", "pipe", "round"],
                    "sphere": ["sphere", "ball", "globe"],
                    "phone_case": ["phone", "case", "cover"],
                    "gear": ["gear", "cog", "mechanical"],
                    "bracket": ["bracket", "mount", "holder"]
                }
                
                detected_intent = "unknown"
                for intent_type, keywords in intent_keywords.items():
                    if any(keyword in user_input.lower() for keyword in keywords):
                        detected_intent = intent_type
                        confidence = 0.9
                        break
                
                result = {
                    "intent": detected_intent,
                    "entities": entities,
                    "confidence": confidence,
                    "source": "spacy_transformers"
                }
                
                processing_time = time.time() - start_time
                
                return AIResponse(
                    content=json.dumps(result),
                    confidence=confidence,
                    model_used="spacy_en_core_web_sm",
                    processing_time=processing_time
                )
            else:
                raise Exception("spaCy model not available")
                
        except Exception as e:
            self.logger.error(f"Intent processing failed: {e}")
            return AIResponse(
                content="",
                confidence=0.0,
                model_used="spacy_transformers",
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def enhance_research(self, query: str, context: Dict[str, Any] = None) -> AIResponse:
        """Enhance research using spaCy analysis."""
        import time
        start_time = time.time()
        
        try:
            if self.nlp:
                doc = self.nlp(query)
                
                # Extract key terms and entities
                key_terms = [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                
                # Create enhanced query
                enhanced_query = f"{query} {' '.join(key_terms[:5])}"
                
                result = {
                    "original_query": query,
                    "enhanced_query": enhanced_query,
                    "key_terms": key_terms,
                    "entities": entities,
                    "suggestions": [
                        f"3D printing {query}",
                        f"{query} design specifications",
                        f"{query} manufacturing requirements"
                    ]
                }
                
                processing_time = time.time() - start_time
                
                return AIResponse(
                    content=json.dumps(result),
                    confidence=0.7,
                    model_used="spacy_en_core_web_sm",
                    processing_time=processing_time
                )
            else:
                raise Exception("spaCy model not available")
                
        except Exception as e:
            self.logger.error(f"Research enhancement failed: {e}")
            return AIResponse(
                content=query,
                confidence=0.5,
                model_used="spacy_transformers",
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    def validate_connection(self) -> bool:
        """Validate spaCy model availability."""
        return self.nlp is not None


class OpenAIModel(BaseAIModel):
    """OpenAI GPT model implementation."""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )
            self.model_name = self.config.model_name or "gpt-3.5-turbo"
            self.logger.info(f"OpenAI client initialized with model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """Process intent using OpenAI GPT."""
        import time
        start_time = time.time()
        
        if not self.client:
            return AIResponse(
                content="",
                confidence=0.0,
                model_used="openai_unavailable",
                processing_time=0.0,
                error="OpenAI client not initialized"
            )
        
        try:
            system_prompt = """You are an expert 3D printing assistant. Analyze user requests and extract:
1. Object type (cube, cylinder, sphere, phone_case, gear, bracket, etc.)
2. Dimensions (if specified)
3. Material preferences
4. Confidence level (0.0-1.0)

Respond with JSON format:
{
    "intent": "object_type",
    "dimensions": {"width": 10, "height": 10, "depth": 10, "unit": "mm"},
    "material": "pla",
    "confidence": 0.95,
    "reasoning": "explanation"
}"""
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            content = response.choices[0].message.content
            processing_time = time.time() - start_time
            
            # Parse confidence from response
            try:
                parsed_content = json.loads(content)
                confidence = parsed_content.get("confidence", 0.8)
            except:
                confidence = 0.8
            
            return AIResponse(
                content=content,
                confidence=confidence,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
            
        except Exception as e:
            self.logger.error(f"OpenAI processing failed: {e}")
            return AIResponse(
                content="",
                confidence=0.0,
                model_used=self.model_name,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def enhance_research(self, query: str, context: Dict[str, Any] = None) -> AIResponse:
        """Enhance research using OpenAI GPT."""
        import time
        start_time = time.time()
        
        if not self.client:
            return AIResponse(
                content=query,
                confidence=0.0,
                model_used="openai_unavailable",
                processing_time=0.0,
                error="OpenAI client not initialized"
            )
        
        try:
            system_prompt = """You are a 3D printing research assistant. Enhance search queries by:
1. Adding relevant technical terms
2. Suggesting alternative search terms
3. Identifying key specifications to research

Respond with JSON format:
{
    "enhanced_query": "improved search query",
    "alternative_terms": ["term1", "term2"],
    "key_specifications": ["spec1", "spec2"],
    "research_suggestions": ["suggestion1", "suggestion2"]
}"""
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Enhance this 3D printing search query: {query}"}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            content = response.choices[0].message.content
            processing_time = time.time() - start_time
            
            return AIResponse(
                content=content,
                confidence=0.9,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
            
        except Exception as e:
            self.logger.error(f"OpenAI research enhancement failed: {e}")
            return AIResponse(
                content=query,
                confidence=0.5,
                model_used=self.model_name,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    def validate_connection(self) -> bool:
        """Validate OpenAI connection."""
        if not self.client or not self.config.api_key:
            return False
        
        try:
            # Simple test request
            import asyncio
            loop = asyncio.new_event_loop() if not asyncio.get_event_loop().is_running() else None
            if loop:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self._test_connection())
                loop.close()
            else:
                result = asyncio.create_task(self._test_connection())
            return result
        except Exception as e:
            self.logger.error(f"OpenAI connection validation failed: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test OpenAI connection."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except:
            return False


class AnthropicModel(BaseAIModel):
    """Anthropic Claude model implementation."""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )
            self.model_name = self.config.model_name or "claude-3-sonnet-20240229"
            self.logger.info(f"Anthropic client initialized with model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Anthropic client: {e}")
            self.client = None
    
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """Process intent using Anthropic Claude."""
        import time
        start_time = time.time()
        
        if not self.client:
            return AIResponse(
                content="",
                confidence=0.0,
                model_used="claude_unavailable",
                processing_time=0.0,
                error="Anthropic client not initialized"
            )
        
        try:
            system_prompt = """You are an expert 3D printing assistant. Analyze user requests and extract detailed specifications for 3D printing.

Extract and structure:
1. Object type (cube, cylinder, sphere, phone_case, gear, bracket, custom)
2. Precise dimensions with units
3. Material recommendations
4. Design complexity assessment
5. Confidence level

Respond only with valid JSON:
{
    "intent": "object_type",
    "dimensions": {"width": 10, "height": 10, "depth": 10, "unit": "mm"},
    "material": "pla",
    "complexity": "simple|medium|complex",
    "confidence": 0.95,
    "reasoning": "brief explanation",
    "print_considerations": ["consideration1", "consideration2"]
}"""
            
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_input}
                ]
            )
            
            content = response.content[0].text
            processing_time = time.time() - start_time
            
            # Parse confidence from response
            try:
                parsed_content = json.loads(content)
                confidence = parsed_content.get("confidence", 0.85)
            except:
                confidence = 0.85
            
            return AIResponse(
                content=content,
                confidence=confidence,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            )
            
        except Exception as e:
            self.logger.error(f"Anthropic processing failed: {e}")
            return AIResponse(
                content="",
                confidence=0.0,
                model_used=self.model_name,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def enhance_research(self, query: str, context: Dict[str, Any] = None) -> AIResponse:
        """Enhance research using Anthropic Claude."""
        import time
        start_time = time.time()
        
        if not self.client:
            return AIResponse(
                content=query,
                confidence=0.0,
                model_used="claude_unavailable",
                processing_time=0.0,
                error="Anthropic client not initialized"
            )
        
        try:
            system_prompt = """You are a comprehensive 3D printing research specialist. Enhance search queries with:

1. Technical terminology specific to 3D printing
2. Material science considerations
3. Manufacturing constraints and requirements
4. Design optimization suggestions
5. Alternative approaches and methodologies

Provide structured research enhancement focusing on practical 3D printing applications.

Respond only with valid JSON:
{
    "enhanced_query": "technically optimized search query",
    "technical_terms": ["term1", "term2", "term3"],
    "material_considerations": ["consideration1", "consideration2"],
    "design_factors": ["factor1", "factor2"],
    "research_directions": ["direction1", "direction2"],
    "confidence": 0.9
}"""
            
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Enhance this 3D printing research query: {query}"}
                ]
            )
            
            content = response.content[0].text
            processing_time = time.time() - start_time
            
            return AIResponse(
                content=content,
                confidence=0.9,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            )
            
        except Exception as e:
            self.logger.error(f"Anthropic research enhancement failed: {e}")
            return AIResponse(
                content=query,
                confidence=0.5,
                model_used=self.model_name,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    def validate_connection(self) -> bool:
        """Validate Anthropic connection."""
        if not self.client or not self.config.api_key:
            return False
        
        try:
            # Simple test request
            import asyncio
            loop = asyncio.new_event_loop() if not asyncio.get_event_loop().is_running() else None
            if loop:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self._test_connection())
                loop.close()
            else:
                result = asyncio.create_task(self._test_connection())
            return result
        except Exception as e:
            self.logger.error(f"Anthropic connection validation failed: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test Anthropic connection."""
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return True
        except:
            return False


class LocalLlamaModel(BaseAIModel):
    """Local Llama model implementation using Ollama or similar."""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.model_name = self.config.model_name or "llama2"
        self.api_base = self.config.api_base or "http://localhost:11434"
        
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """Process intent using local Llama model."""
        import time
        import httpx
        start_time = time.time()
        
        try:
            prompt = f"""<|system|>
You are a 3D printing expert. Analyze this request and extract object specifications.

Respond with JSON:
{{
    "intent": "object_type",
    "dimensions": {{"width": 10, "height": 10, "depth": 10, "unit": "mm"}},
    "material": "pla",
    "confidence": 0.8
}}

<|user|>
{user_input}

<|assistant|>"""
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens
                        }
                    },
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("response", "")
                    
                    # Try to parse confidence
                    try:
                        parsed_content = json.loads(content)
                        confidence = parsed_content.get("confidence", 0.7)
                    except:
                        confidence = 0.7
                    
                    processing_time = time.time() - start_time
                    
                    return AIResponse(
                        content=content,
                        confidence=confidence,
                        model_used=f"llama_{self.model_name}",
                        processing_time=processing_time
                    )
                else:
                    raise Exception(f"Ollama API error: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Local Llama processing failed: {e}")
            return AIResponse(
                content="",
                confidence=0.0,
                model_used=f"llama_{self.model_name}",
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def enhance_research(self, query: str, context: Dict[str, Any] = None) -> AIResponse:
        """Enhance research using local Llama model."""
        import time
        import httpx
        start_time = time.time()
        
        try:
            prompt = f"""<|system|>
You are a 3D printing research assistant. Enhance this search query with technical terms and alternatives.

Respond with JSON:
{{
    "enhanced_query": "improved query",
    "alternatives": ["term1", "term2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}

<|user|>
Enhance this 3D printing search: {query}

<|assistant|>"""
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens
                        }
                    },
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("response", query)
                    
                    processing_time = time.time() - start_time
                    
                    return AIResponse(
                        content=content,
                        confidence=0.8,
                        model_used=f"llama_{self.model_name}",
                        processing_time=processing_time
                    )
                else:
                    raise Exception(f"Ollama API error: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Local Llama research enhancement failed: {e}")
            return AIResponse(
                content=query,
                confidence=0.5,
                model_used=f"llama_{self.model_name}",
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    def validate_connection(self) -> bool:
        """Validate local Llama connection."""
        try:
            import httpx
            with httpx.Client() as client:
                response = client.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": "Hello",
                        "stream": False,
                        "options": {"num_predict": 1}
                    },
                    timeout=5
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Local Llama connection validation failed: {e}")
            return False


class AIModelManager:
    """Manager for multiple AI model backends."""
    
    def __init__(self):
        self.logger = AgentLogger("ai_model_manager")
        self.models: Dict[AIModelType, BaseAIModel] = {}
        self.default_model = AIModelType.SPACY_TRANSFORMERS
        self.fallback_order = [
            AIModelType.SPACY_TRANSFORMERS,
            AIModelType.OPENAI_GPT,
            AIModelType.ANTHROPIC_CLAUDE,
            AIModelType.LOCAL_LLAMA
        ]
        
    def register_model(self, model_type: AIModelType, config: AIModelConfig) -> bool:
        """Register an AI model with the manager."""
        try:
            if model_type == AIModelType.SPACY_TRANSFORMERS:
                model = SpacyTransformersModel(config)
            elif model_type == AIModelType.OPENAI_GPT:
                model = OpenAIModel(config)
            elif model_type == AIModelType.ANTHROPIC_CLAUDE:
                model = AnthropicModel(config)
            elif model_type == AIModelType.LOCAL_LLAMA:
                model = LocalLlamaModel(config)
            elif model_type == AIModelType.LOCAL_MISTRAL:
                # Use LocalLlamaModel with Mistral configuration
                config.model_name = config.model_name or "mistral"
                model = LocalLlamaModel(config)
            else:
                self.logger.error(f"Unsupported model type: {model_type}")
                return False
            
            # Validate connection
            if model.validate_connection():
                self.models[model_type] = model
                self.logger.info(f"Successfully registered model: {model_type.value}")
                return True
            else:
                self.logger.warning(f"Model registered but connection failed: {model_type.value}")
                self.models[model_type] = model  # Still register for fallback
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to register model {model_type.value}: {e}")
            return False
    
    def set_default_model(self, model_type: AIModelType) -> bool:
        """Set the default AI model to use."""
        if model_type in self.models:
            self.default_model = model_type
            self.logger.info(f"Default model set to: {model_type.value}")
            return True
        else:
            self.logger.error(f"Cannot set default to unregistered model: {model_type.value}")
            return False
    
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None, 
                           preferred_model: Optional[AIModelType] = None) -> AIResponse:
        """Process intent using preferred model with fallback."""
        
        # Determine which model to try first
        model_order = []
        if preferred_model and preferred_model in self.models:
            model_order.append(preferred_model)
        
        if self.default_model in self.models and self.default_model not in model_order:
            model_order.append(self.default_model)
        
        # Add fallback models
        for model_type in self.fallback_order:
            if model_type in self.models and model_type not in model_order:
                model_order.append(model_type)
        
        # Try models in order
        last_error = None
        for model_type in model_order:
            try:
                model = self.models[model_type]
                response = await model.process_intent(user_input, context)
                
                if response.error is None and response.confidence > 0.3:
                    self.logger.info(f"Intent processed successfully with {model_type.value}")
                    return response
                else:
                    last_error = response.error or "Low confidence response"
                    self.logger.warning(f"Model {model_type.value} failed: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Error with model {model_type.value}: {e}")
        
        # All models failed
        self.logger.error("All AI models failed for intent processing")
        return AIResponse(
            content="",
            confidence=0.0,
            model_used="none_available",
            processing_time=0.0,
            error=f"All models failed. Last error: {last_error}"
        )
    
    async def enhance_research(self, query: str, context: Dict[str, Any] = None,
                             preferred_model: Optional[AIModelType] = None) -> AIResponse:
        """Enhance research using preferred model with fallback."""
        
        # Determine which model to try first
        model_order = []
        if preferred_model and preferred_model in self.models:
            model_order.append(preferred_model)
        
        if self.default_model in self.models and self.default_model not in model_order:
            model_order.append(self.default_model)
        
        # Add fallback models
        for model_type in self.fallback_order:
            if model_type in self.models and model_type not in model_order:
                model_order.append(model_type)
        
        # Try models in order
        last_error = None
        for model_type in model_order:
            try:
                model = self.models[model_type]
                response = await model.enhance_research(query, context)
                
                if response.error is None:
                    self.logger.info(f"Research enhanced successfully with {model_type.value}")
                    return response
                else:
                    last_error = response.error
                    self.logger.warning(f"Model {model_type.value} failed: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Error with model {model_type.value}: {e}")
        
        # All models failed, return original query
        self.logger.warning("All AI models failed for research enhancement, using original query")
        return AIResponse(
            content=query,
            confidence=0.5,
            model_used="fallback",
            processing_time=0.0,
            error=f"All models failed. Last error: {last_error}"
        )
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models with their status."""
        models_info = []
        for model_type, model in self.models.items():
            models_info.append({
                "type": model_type.value,
                "name": model_type.value.replace("_", " ").title(),
                "available": model.validate_connection(),
                "is_default": model_type == self.default_model
            })
        return models_info
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about model usage and performance."""
        return {
            "total_models": len(self.models),
            "default_model": self.default_model.value,
            "available_models": [mt.value for mt in self.models.keys()],
            "fallback_order": [mt.value for mt in self.fallback_order if mt in self.models]
        }
