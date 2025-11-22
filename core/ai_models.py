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
from typing import Dict, List, Any, Optional, Union, Awaitable
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

import yaml

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
    api_url: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30
    enabled: bool = True
    config_path: Optional[str] = None
    additional_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}

        # Harmonize API base/url aliases for convenience
        if self.api_base and not self.api_url:
            self.api_url = self.api_base
        elif self.api_url and not self.api_base:
            self.api_base = self.api_url


@dataclass
class AIResponse:
    """Standardized response from AI models."""
    content: str = ""
    confidence: float = 0.0
    model_used: str = ""
    processing_time: float = 0.0
    success: bool = False
    data: Optional[Dict[str, Any]] = None
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.error and not self.error_message:
            self.error_message = self.error
        if self.error_message and not self.error:
            self.error = self.error_message


def _run_async(coro: Awaitable[Any]) -> Any:
    """Execute an async coroutine regardless of loop availability."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(loop)
            new_loop.close()

    return asyncio.run(coro)


class BaseAIModel(ABC):
    """Abstract base class for AI model implementations."""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.model_type = config.model_type
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

    def analyze_request(
        self,
        request_text: str,
        context: Optional[Dict[str, Any]] = None,
        analysis_depth: str = "standard"
    ) -> AIResponse:
        """Synchronous helper that wraps :meth:`process_intent`."""

        context = context or {}

        try:
            response = _run_async(self.process_intent(request_text, context))
        except Exception as exc:  # pragma: no cover - catastrophic fallback
            self.logger.error(f"Analyze request failed: {exc}")
            return AIResponse(
                content="",
                confidence=0.0,
                model_used=self.config.model_type.value,
                processing_time=0.0,
                success=False,
                error_message=str(exc)
            )

        if not response.model_used:
            response.model_used = self.config.model_type.value

        if response.error or response.error_message:
            response.success = False
        else:
            response.success = True

        if response.content and response.data is None:
            try:
                response.data = json.loads(response.content)
            except (TypeError, json.JSONDecodeError):
                response.data = {"raw_content": response.content}

        return response


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
                    model_used=self.config.model_type.value,
                    processing_time=processing_time
                )
            else:
                raise Exception("spaCy model not available")
                
        except Exception as e:
            self.logger.error(f"Intent processing failed: {e}")
            return AIResponse(
                content="",
                confidence=0.0,
                model_used=self.config.model_type.value,
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
        self._client_is_async = False
        self.client = None
        self.model_name = self.config.model_name or "gpt-3.5-turbo"
        
    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            import openai
            self.model_name = self.config.model_name or self.model_name or "gpt-3.5-turbo"
            if hasattr(openai, "OpenAI"):
                self.client = openai.OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
                self._client_is_async = False
            else:
                self.client = openai.AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
                self._client_is_async = True
            self.logger.info(f"OpenAI client initialized with model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
            self._client_is_async = False

    def _ensure_client(self) -> bool:
        if not self.client:
            self._initialize_client()
        return self.client is not None
    
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """Process intent using OpenAI GPT."""
        import time
        start_time = time.time()
        
        if not self._ensure_client():
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
            
            if self._client_is_async:
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
            else:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
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

            usage = getattr(response, "usage", None)
            token_usage = None
            if usage:
                token_usage = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None)
                }
                token_usage = {k: v for k, v in token_usage.items() if v is not None} or None
            
            return AIResponse(
                content=content,
                confidence=confidence,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage=token_usage
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
        
        if not self._ensure_client():
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
            
            if self._client_is_async:
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
            else:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
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

            usage = getattr(response, "usage", None)
            token_usage = None
            if usage:
                token_usage = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None)
                }
                token_usage = {k: v for k, v in token_usage.items() if v is not None} or None

            return AIResponse(
                content=content,
                confidence=0.9,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage=token_usage
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
        if not self.config.api_key:
            return False

        if not self._ensure_client():
            return False

        try:
            if self._client_is_async:
                _run_async(self.client.models.list())
            else:
                self.client.models.list()
            return True
        except Exception as e:
            self.logger.error(f"OpenAI connection validation failed: {e}")
            return False


class AnthropicModel(BaseAIModel):
    """Anthropic Claude model implementation."""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._client_is_async = False
        self.client = None
        self.model_name = self.config.model_name or "claude-3-sonnet-20240229"
        
    def _initialize_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            self.model_name = self.config.model_name or self.model_name or "claude-3-sonnet-20240229"
            self.client = None

            if hasattr(anthropic, "Anthropic"):
                try:
                    self.client = anthropic.Anthropic(
                        api_key=self.config.api_key,
                        base_url=self.config.api_base
                    )
                    self._client_is_async = False
                    self.logger.info(
                        f"Anthropic client initialized (sync) with model: {self.model_name}"
                    )
                except Exception as sync_exc:
                    self.logger.debug(
                        f"Sync Anthropic client init failed, trying async: {sync_exc}"
                    )

            if self.client is None and hasattr(anthropic, "AsyncAnthropic"):
                self.client = anthropic.AsyncAnthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
                self._client_is_async = True
                self.logger.info(
                    f"Anthropic client initialized (async) with model: {self.model_name}"
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize Anthropic client: {e}")
            self.client = None
            self._client_is_async = False

    def _ensure_client(self) -> bool:
        if not self.client:
            self._initialize_client()
        return self.client is not None
    
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """Process intent using Anthropic Claude."""
        import time
        start_time = time.time()
        
        if not self._ensure_client():
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
            
            if self._client_is_async:
                response = await self.client.messages.create(
                    model=self.model_name,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_input}
                    ]
                )
            else:
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.model_name,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_input}
                    ]
                )
            
            response_content = getattr(response, "content", None)
            if isinstance(response_content, list) and response_content:
                first_item = response_content[0]
                content = getattr(first_item, "text", "") or getattr(first_item, "value", "")
            else:
                content = getattr(response, "text", "")
            processing_time = time.time() - start_time
            
            # Parse confidence from response
            try:
                parsed_content = json.loads(content)
                confidence = parsed_content.get("confidence", 0.85)
            except:
                confidence = 0.85

            usage = getattr(response, "usage", None)
            token_usage = None
            if usage:
                token_usage = {
                    "input_tokens": getattr(usage, "input_tokens", None),
                    "output_tokens": getattr(usage, "output_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None)
                }
                token_usage = {k: v for k, v in token_usage.items() if v is not None} or None
            
            return AIResponse(
                content=content,
                confidence=confidence,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage=token_usage
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
        
        if not self._ensure_client():
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
            
            if self._client_is_async:
                response = await self.client.messages.create(
                    model=self.model_name,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Enhance this 3D printing research query: {query}"}
                    ]
                )
            else:
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.model_name,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Enhance this 3D printing research query: {query}"}
                    ]
                )
            
            response_content = getattr(response, "content", None)
            if isinstance(response_content, list) and response_content:
                first_item = response_content[0]
                content = getattr(first_item, "text", "") or getattr(first_item, "value", "")
            else:
                content = getattr(response, "text", "")
            processing_time = time.time() - start_time
            
            usage = getattr(response, "usage", None)
            token_usage = None
            if usage:
                token_usage = {
                    "input_tokens": getattr(usage, "input_tokens", None),
                    "output_tokens": getattr(usage, "output_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None)
                }
                token_usage = {k: v for k, v in token_usage.items() if v is not None} or None
            
            return AIResponse(
                content=content,
                confidence=0.9,
                model_used=self.model_name,
                processing_time=processing_time,
                token_usage=token_usage
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
        if not self.config.api_key:
            return False

        if not self._ensure_client():
            return False
        
        try:
            kwargs = {
                "model": self.model_name,
                "max_tokens": 8,
                "temperature": 0,
                "system": "Ping test",
                "messages": [{"role": "user", "content": "Hello"}]
            }

            if not hasattr(self.client, "messages"):
                raise AttributeError("Anthropic client missing 'messages' attribute")

            if self._client_is_async:
                _run_async(self.client.messages.create(**kwargs))
            else:
                self.client.messages.create(**kwargs)

            return True
        except Exception as e:
            self.logger.error(f"Anthropic connection validation failed: {e}")
            return False


class LocalLlamaModel(BaseAIModel):
    """Local Llama model implementation using Ollama or similar."""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.model_name = self.config.model_name or "llama2"
        self.api_base = self.config.api_base or "http://localhost:11434"
        self._client = None
        
    async def _get_client(self):
        """Get or create a reusable httpx client for better connection pooling."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client
    
    async def close(self):
        """Close the httpx client to cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        
    async def process_intent(self, user_input: str, context: Dict[str, Any] = None) -> AIResponse:
        """Process intent using local Llama model."""
        import time
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
            
            client = await self._get_client()
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
                }
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
                    model_used=self.model_name,
                    processing_time=processing_time
                )
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Local Llama processing failed: {e}")
            return AIResponse(
                content="",
                confidence=0.0,
                model_used=self.model_name,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def enhance_research(self, query: str, context: Dict[str, Any] = None) -> AIResponse:
        """Enhance research using local Llama model."""
        import time
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
            
            client = await self._get_client()
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
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("response", query)

                processing_time = time.time() - start_time

                return AIResponse(
                    content=content,
                    confidence=0.8,
                    model_used=self.model_name,
                    processing_time=processing_time
                )
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Local Llama research enhancement failed: {e}")
            return AIResponse(
                content=query,
                confidence=0.5,
                model_used=self.model_name,
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    async def validate_connection(self) -> bool:
        """Validate local Llama connection asynchronously."""
        try:
            import httpx
            # Use a separate client for validation to avoid timeout issues
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get(f"{self.api_base}/")
                    if response.status_code == 200:
                        return True
                except:
                    pass

                # Fallback simple generation check
                response = await client.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": "Hello",
                        "stream": False,
                        "options": {"num_predict": 1}
                    }
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Local Llama connection validation failed: {e}")
            return False


class AIModelManager:
    """Manager for multiple AI model backends."""

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        enable_fallback: bool = True,
        confidence_threshold: float = 0.5
    ):
        self.logger = AgentLogger("ai_model_manager")
        self.models: Dict[str, BaseAIModel] = {}
        self.model_configs: Dict[str, AIModelConfig] = {}
        self.enable_fallback = enable_fallback
        self.confidence_threshold = confidence_threshold
        self.preferred_model: Optional[str] = None
        self.default_model: Optional[str] = None
        self.config_path = str(config_path) if config_path else None
        self.fallback_order: List[str] = []
        self.performance_settings: Dict[str, Any] = {}
        self.analytics_settings: Dict[str, Any] = {}
        self.environment_variables: Dict[str, str] = {}

        if self.config_path:
            self._load_from_config(self.config_path)

        if not self.models:
            self._register_default_spacy()

    # ------------------------------------------------------------------
    # Registration & configuration helpers
    # ------------------------------------------------------------------
    def register_model(self, model_identifier: Union[str, AIModelType], config: AIModelConfig) -> bool:
        """Register an AI model with the manager.

        Args:
            model_identifier: String name or :class:`AIModelType` value.
            config: Configuration object for the model.

        Returns:
            True if the connection validates successfully, False otherwise.
        """

        model_name = self._normalize_model_name(model_identifier) or config.model_type.value

        try:
            model = self._instantiate_model(config)
        except Exception as exc:
            self.logger.error(f"Failed to instantiate model {model_name}: {exc}")
            return False

        self.models[model_name] = model
        self.model_configs[model_name] = config

        if model_name not in self.fallback_order:
            self.fallback_order.append(model_name)

        available = False
        try:
            available = model.validate_connection()
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(f"Validation error for model {model_name}: {exc}")

        if available:
            self.logger.info(f"Successfully registered model: {model_name}")
        else:
            self.logger.warning(f"Model registered but validation failed: {model_name}")

        if not self.default_model and config.enabled:
            self.default_model = model_name

        return available

    def set_default_model(self, model_identifier: Union[str, AIModelType]) -> bool:
        """Set the default AI model used for processing."""
        model_name = self._normalize_model_name(model_identifier)
        if not model_name or model_name not in self.models:
            self.logger.error(f"Cannot set default to unknown model: {model_identifier}")
            return False

        self.default_model = model_name
        self.logger.info(f"Default model set to: {model_name}")
        return True

    def set_preferred_model(self, model_identifier: Union[str, AIModelType]) -> None:
        """Set the preferred model name (raises if unavailable)."""
        model_name = self._normalize_model_name(model_identifier)
        if not model_name or model_name not in self.models:
            raise ValueError(f"Unknown AI model: {model_identifier}")
        self.preferred_model = model_name

    # ------------------------------------------------------------------
    # Analysis & research helpers
    # ------------------------------------------------------------------
    async def process_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_model: Optional[Union[str, AIModelType]] = None
    ) -> AIResponse:
        """Process intent using the preferred model with optional fallback."""

        context = context or {}
        candidates = self._build_candidate_sequence(preferred_model)

        if not candidates:
            return AIResponse(
                content="",
                confidence=0.0,
                model_used="none_available",
                processing_time=0.0,
                success=False,
                error_message="No AI models available"
            )

        last_error: Optional[str] = None

        for name in candidates:
            config = self.model_configs.get(name)
            if config and not config.enabled:
                continue

            model = self.models.get(name)
            if not model:
                continue

            try:
                response = await model.process_intent(user_input, context)
            except Exception as exc:
                last_error = str(exc)
                self.logger.error(f"Intent processing failed for {name}: {exc}")
                if not self.enable_fallback:
                    break
                continue

            if not response.model_used:
                response.model_used = name

            if response.error or response.error_message:
                last_error = response.error_message or response.error
                self.logger.warning(f"Model {name} returned error: {last_error}")
                if not self.enable_fallback:
                    break
                continue

            response.success = response.confidence >= self.confidence_threshold
            if response.success:
                self.logger.info(f"Intent processed successfully with {name}")
                return response

            last_error = f"Low confidence response ({response.confidence:.2f})"
            self.logger.warning(f"Model {name} produced low confidence output")
            if not self.enable_fallback:
                break

        return AIResponse(
            content="",
            confidence=0.0,
            model_used="none_available",
            processing_time=0.0,
            success=False,
            error_message=f"All models failed. Last error: {last_error}"
        )

    async def enhance_research(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_model: Optional[Union[str, AIModelType]] = None
    ) -> AIResponse:
        """Enhance research query using preferred model with fallback."""

        context = context or {}
        candidates = self._build_candidate_sequence(preferred_model)

        if not candidates:
            return AIResponse(
                content=query,
                confidence=0.5,
                model_used="fallback",
                processing_time=0.0,
                success=False,
                error_message="No AI models available"
            )

        last_error: Optional[str] = None

        for name in candidates:
            config = self.model_configs.get(name)
            if config and not config.enabled:
                continue

            model = self.models.get(name)
            if not model:
                continue

            try:
                response = await model.enhance_research(query, context)
            except Exception as exc:
                last_error = str(exc)
                self.logger.error(f"Research enhancement failed for {name}: {exc}")
                if not self.enable_fallback:
                    break
                continue

            if not response.model_used:
                response.model_used = name

            if response.error or response.error_message:
                last_error = response.error_message or response.error
                self.logger.warning(f"Model {name} returned error during research: {last_error}")
                if not self.enable_fallback:
                    break
                continue

            self.logger.info(f"Research enhanced successfully with {name}")
            return response

        return AIResponse(
            content=query,
            confidence=0.5,
            model_used="fallback",
            processing_time=0.0,
            success=False,
            error_message=f"All models failed. Last error: {last_error}"
        )

    def analyze_request(
        self,
        request_text: str,
        context: Optional[Dict[str, Any]] = None,
        analysis_depth: str = "standard",
        preferred_model: Optional[Union[str, AIModelType]] = None
    ) -> AIResponse:
        """Synchronous interface mirroring :meth:`process_intent`."""

        candidates = self._build_candidate_sequence(preferred_model)
        if not candidates:
            return AIResponse(
                content="",
                confidence=0.0,
                model_used="none_available",
                processing_time=0.0,
                success=False,
                error_message="No AI models available"
            )

        last_error: Optional[str] = None
        context = context or {}

        for name in candidates:
            config = self.model_configs.get(name)
            if config and not config.enabled:
                continue

            model = self.models.get(name)
            if not model:
                continue

            try:
                response = model.analyze_request(request_text, context, analysis_depth)
            except Exception as exc:
                last_error = str(exc)
                self.logger.error(f"Analyze request failed for {name}: {exc}")
                if not self.enable_fallback:
                    break
                continue

            if not response.model_used:
                response.model_used = name

            if response.error or response.error_message:
                last_error = response.error_message or response.error
                self.logger.warning(f"Model {name} returned error: {last_error}")
                if not self.enable_fallback:
                    break
                continue

            if response.confidence < self.confidence_threshold:
                last_error = f"Low confidence response ({response.confidence:.2f})"
                self.logger.warning(f"Model {name} produced low confidence output")
                if not self.enable_fallback:
                    break
                continue

            response.success = True
            return response

        return AIResponse(
            content="",
            confidence=0.0,
            model_used="none_available",
            processing_time=0.0,
            success=False,
            error_message=f"AI model analysis failed: {last_error}"
        )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def get_available_models(self) -> List[str]:
        """Return a list of registered (and enabled) model names."""
        return [
            name for name, cfg in self.model_configs.items()
            if cfg.enabled and name in self.models
        ]

    def get_model_stats(self) -> Dict[str, Any]:
        """Return a compact status dictionary used by diagnostics."""
        return {
            "total_models": len(self.models),
            "available_models": self.get_available_models(),
            "preferred_model": self.preferred_model,
            "default_model": self.default_model,
            "fallback_order": list(self.fallback_order),
            "enable_fallback": self.enable_fallback,
            "confidence_threshold": self.confidence_threshold
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_model_name(self, identifier: Optional[Union[str, AIModelType]]) -> Optional[str]:
        if identifier is None:
            return None
        if isinstance(identifier, AIModelType):
            return identifier.value
        if isinstance(identifier, str):
            return identifier
        return None

    def _instantiate_model(self, config: AIModelConfig) -> BaseAIModel:
        model_type = config.model_type
        if model_type == AIModelType.SPACY_TRANSFORMERS:
            return SpacyTransformersModel(config)
        if model_type == AIModelType.OPENAI_GPT:
            return OpenAIModel(config)
        if model_type == AIModelType.ANTHROPIC_CLAUDE:
            return AnthropicModel(config)
        if model_type in (AIModelType.LOCAL_LLAMA, AIModelType.LOCAL_MISTRAL):
            if model_type == AIModelType.LOCAL_MISTRAL and not config.model_name:
                config.model_name = "mistral"
            return LocalLlamaModel(config)
        raise ValueError(f"Unsupported model type: {model_type}")

    def _build_candidate_sequence(self, preferred: Optional[Union[str, AIModelType]]) -> List[str]:
        order: List[str] = []
        preferred_name = self._normalize_model_name(preferred)

        if preferred_name and preferred_name in self.models:
            order.append(preferred_name)

        if self.preferred_model and self.preferred_model not in order and self.preferred_model in self.models:
            order.append(self.preferred_model)

        if self.default_model and self.default_model not in order and self.default_model in self.models:
            order.append(self.default_model)

        for name in self.fallback_order:
            if name in self.models and name not in order:
                order.append(name)

        for name in self.models.keys():
            if name not in order:
                order.append(name)

        return order

    def _load_from_config(self, config_path: Union[str, Path]) -> None:
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except FileNotFoundError:
            self.logger.warning(f"AI model config not found: {config_path}")
            return
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(f"Failed to load AI model config: {exc}")
            return

        ai_section = data.get("ai_models", {})

        models_cfg: Dict[str, Dict[str, Any]]
        fallback_cfg: Dict[str, Any] = {}
        performance_cfg: Dict[str, Any] = {}

        if isinstance(ai_section, dict) and "models" in ai_section:
            models_cfg = ai_section.get("models", {})
            fallback_cfg = ai_section.get("fallback", {}) or {}
            performance_cfg = ai_section.get("performance", {}) or {}
            configured_default = ai_section.get("default_model")
            if configured_default:
                self.default_model = configured_default
        else:
            models_cfg = ai_section or {}
            configured_default = None

        settings = data.get("settings", {})
        self.enable_fallback = fallback_cfg.get("auto_fallback", settings.get("enable_fallback", self.enable_fallback))
        self.confidence_threshold = fallback_cfg.get(
            "min_confidence",
            settings.get("confidence_threshold", self.confidence_threshold)
        )

        self.performance_settings = performance_cfg
        self.analytics_settings = data.get("analytics", {}) or {}

        env_mapping = data.get("environment_variables", {}) or {}
        if isinstance(env_mapping, dict):
            self.environment_variables = {str(k): str(v) for k, v in env_mapping.items()}

        requested_fallback_order = fallback_cfg.get("order", [])
        self.fallback_order = [str(item) for item in requested_fallback_order if isinstance(item, str)]

        ordered_entries = sorted(
            models_cfg.items(),
            key=lambda item: item[1].get("priority", 100)
        )

        def _populate_from_env(model_type: AIModelType, config: AIModelConfig) -> None:
            if not self.environment_variables:
                return

            if model_type == AIModelType.OPENAI_GPT:
                env_key = self.environment_variables.get("openai_api_key")
                if env_key and not config.api_key:
                    config.api_key = os.getenv(env_key) or config.api_key
            elif model_type == AIModelType.ANTHROPIC_CLAUDE:
                env_key = self.environment_variables.get("anthropic_api_key")
                if env_key and not config.api_key:
                    config.api_key = os.getenv(env_key) or config.api_key
            elif model_type in (AIModelType.LOCAL_LLAMA, AIModelType.LOCAL_MISTRAL):
                env_key = self.environment_variables.get("local_api_base")
                if env_key:
                    env_value = os.getenv(env_key)
                    if env_value:
                        config.api_base = env_value
                        config.api_url = env_value

        for name, cfg in ordered_entries:
            model_type_str = cfg.get("type", name)
            try:
                model_type = AIModelType(model_type_str)
            except ValueError:
                self.logger.warning(f"Unknown model type '{model_type_str}' in config; skipping")
                continue

            config = AIModelConfig(
                model_type=model_type,
                api_key=cfg.get("api_key"),
                api_base=cfg.get("api_base"),
                api_url=cfg.get("api_url"),
                model_name=cfg.get("model_name"),
                max_tokens=cfg.get("max_tokens", 1000),
                temperature=cfg.get("temperature", 0.7),
                timeout=cfg.get("timeout", 30),
                enabled=cfg.get("enabled", True),
                config_path=str(config_path),
                additional_params=cfg.get("additional_params") or {}
            )

            _populate_from_env(model_type, config)

            self.model_configs[name] = config

            if config.enabled:
                if name not in self.fallback_order:
                    self.fallback_order.append(name)
                self.register_model(name, config)
            else:
                self.logger.info(f"Model '{name}' disabled in configuration; skipping registration")

        if configured_default and configured_default in self.models:
            self.default_model = configured_default
        elif self.fallback_order:
            self.default_model = self.fallback_order[0]

    def _register_default_spacy(self) -> None:
        config = AIModelConfig(model_type=AIModelType.SPACY_TRANSFORMERS, model_name="en_core_web_sm")
        self.register_model("spacy_transformers", config)
        if not self.fallback_order:
            self.fallback_order.append("spacy_transformers")
        if not self.default_model:
            self.default_model = "spacy_transformers"
