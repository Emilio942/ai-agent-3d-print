"""
Research Agent - NLP Intent Recognition with Web Research and Rate Limiting

This module implements the Research Agent for the AI Agent 3D Print System with
robust natural language processing capabilities to extract user intents and
convert them into structured 3D object specifications. Now includes web research
capabilities with DuckDuckGo API integration, caching, and rate limiting.
"""

import re
import json
import spacy
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta

# Web research dependencies
import requests
from duckduckgo_search import DDGS
import diskcache as dc

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from core.api_schemas import TaskResult, ResearchAgentInput, ResearchAgentOutput
from core.logger import AgentLogger
from core.exceptions import ValidationError, SystemResourceError


class ConfidenceLevel(Enum):
    """Confidence levels for intent extraction."""
    VERY_HIGH = 0.9
    HIGH = 0.7
    MEDIUM = 0.5
    LOW = 0.3
    VERY_LOW = 0.1


@dataclass
class IntentPattern:
    """Pattern definition for intent matching."""
    name: str
    keywords: List[str]
    regex_patterns: List[str]
    dimension_patterns: List[str] = field(default_factory=list)
    material_keywords: List[str] = field(default_factory=list)
    confidence_boost: float = 0.1


@dataclass
class RateLimiter:
    """Rate limiter for web requests."""
    max_requests: int = 10
    time_window: int = 60  # seconds
    requests: List[float] = field(default_factory=list)
    
    def can_make_request(self) -> bool:
        """Check if we can make a request within rate limits."""
        current_time = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < self.time_window]
        
        return len(self.requests) < self.max_requests
    
    def record_request(self) -> None:
        """Record a request timestamp."""
        self.requests.append(time.time())


class ResearchAgent(BaseAgent):
    """
    Research Agent with NLP Intent Recognition, Web Research, and Rate Limiting.
    
    Provides robust intent extraction using:
    1. Primary: spaCy NER + Pattern Matching
    2. Fallback: Regex-based extraction
    3. Web research with DuckDuckGo API
    4. Local caching for 24h
    5. Rate limiting: max 10 requests/minute
    """
    
    def __init__(self, agent_id: str = "research_agent", config: Optional[Dict[str, Any]] = None):
        """Initialize Research Agent with NLP and web research capabilities."""
        super().__init__(agent_id, config)
        self.logger = AgentLogger("research_agent")
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.logger.info("Loaded spaCy English model successfully")
        except Exception as e:
            self.logger.error(f"Failed to load spaCy model: {str(e)}")
            self.nlp = None
        
        # Initialize intent patterns
        self._load_intent_patterns()
        
        # Initialize material mappings
        self._load_material_mappings()
        
        # Initialize dimension extraction patterns
        self._load_dimension_patterns()
        
        # Initialize web research components
        self._initialize_web_research()
        
        self.logger.info("Research Agent initialized with NLP and web research capabilities")
    
    def _initialize_web_research(self) -> None:
        """Initialize web research components."""
        try:
            # Initialize cache directory
            cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Initialize cache
            self.cache = dc.Cache(os.path.join(cache_dir, "web_research_cache"))
            
            # Initialize rate limiter
            self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
            
            # Initialize DuckDuckGo search
            self.ddgs = DDGS()
            
            # Disable summarization pipeline due to SSL issues
            self.summarizer = None
            self.logger.info("Summarization disabled to avoid SSL issues")
            
            self.logger.info("Web research components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize web research: {str(e)}")
            self.cache = None
            self.rate_limiter = None
            self.ddgs = None
            self.summarizer = None
    
    def _load_intent_patterns(self) -> None:
        """Load configurable intent patterns."""
        self.intent_patterns = [
            IntentPattern(
                name="cube",
                keywords=["cube", "box", "square", "rectangular", "block"],
                regex_patterns=[
                    r"(?:make|create|print|build).*?(?:a|an)?\s*(?:small|large|medium)?\s*(?:cube|box|square)",
                    r"(?:cube|box|square).*?(?:shaped|object|thing)",
                    r"rectangular\s+(?:box|block|object)"
                ],
                dimension_patterns=[
                    r"(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*(?:x|by|\×)\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*(?:x|by|\×)?\s*(\d+(?:\.\d+)?)",
                    r"(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*cube",
                    r"size\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?"
                ],
                material_keywords=["plastic", "pla", "abs", "petg"],
                confidence_boost=0.2
            ),
            IntentPattern(
                name="cylinder",
                keywords=["cylinder", "tube", "pipe", "round", "circular"],
                regex_patterns=[
                    r"(?:make|create|print|build).*?(?:a|an)?\s*(?:small|large|medium)?\s*(?:cylinder|tube|pipe)",
                    r"(?:cylinder|tube|pipe).*?(?:shaped|object|thing)",
                    r"round\s+(?:tube|pipe|object)"
                ],
                dimension_patterns=[
                    r"diameter\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
                    r"radius\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
                    r"height\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?"
                ],
                material_keywords=["plastic", "pla", "abs", "petg"],
                confidence_boost=0.15
            ),
            IntentPattern(
                name="sphere",
                keywords=["sphere", "ball", "globe", "round", "circular"],
                regex_patterns=[
                    r"(?:make|create|print|build).*?(?:a|an)?\s*(?:small|large|medium)?\s*(?:sphere|ball|globe)",
                    r"(?:sphere|ball|globe).*?(?:shaped|object|thing)",
                    r"round\s+(?:ball|object)"
                ],
                dimension_patterns=[
                    r"diameter\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
                    r"radius\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?"
                ],
                material_keywords=["plastic", "pla", "abs", "petg"],
                confidence_boost=0.15
            ),
            IntentPattern(
                name="phone_case",
                keywords=["phone", "case", "cover", "protection", "mobile"],
                regex_patterns=[
                    r"(?:phone|mobile)\s*(?:case|cover|protection)",
                    r"case\s*for\s*(?:my\s*)?(?:phone|mobile|iphone|android)",
                    r"protective\s*(?:case|cover)"
                ],
                dimension_patterns=[
                    r"(?:iphone|android)\s*(\d+)",
                    r"phone\s*(?:size\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?"
                ],
                material_keywords=["tpu", "flexible", "rubber", "plastic"],
                confidence_boost=0.25
            ),
            IntentPattern(
                name="gear",
                keywords=["gear", "cog", "wheel", "mechanism", "mechanical"],
                regex_patterns=[
                    r"(?:make|create|print|build).*?(?:a|an)?\s*(?:small|large|medium)?\s*(?:gear|cog)",
                    r"(?:gear|cog).*?(?:wheel|mechanism)",
                    r"mechanical\s+(?:gear|part|component)"
                ],
                dimension_patterns=[
                    r"(\d+)\s*(?:teeth|tooth)",
                    r"diameter\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
                    r"module\s*(\d+(?:\.\d+)?)"
                ],
                material_keywords=["pla", "abs", "nylon", "strong"],
                confidence_boost=0.2
            ),
            IntentPattern(
                name="bracket",
                keywords=["bracket", "mount", "holder", "support", "stand"],
                regex_patterns=[
                    r"(?:make|create|print|build).*?(?:a|an)?\s*(?:bracket|mount|holder)",
                    r"(?:bracket|mount|holder)\s*for",
                    r"wall\s*(?:mount|bracket)"
                ],
                dimension_patterns=[
                    r"(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*(?:wide|width)",
                    r"thickness\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?"
                ],
                material_keywords=["abs", "petg", "strong", "durable"],
                confidence_boost=0.15
            )
        ]
        
        self.logger.info(f"Loaded {len(self.intent_patterns)} intent patterns")
    
    def _load_material_mappings(self) -> None:
        """Load material keyword mappings."""
        self.material_mappings = {
            "pla": ["pla", "polylactic", "biodegradable", "easy", "beginner"],
            "abs": ["abs", "acrylonitrile", "strong", "durable", "automotive"],
            "petg": ["petg", "glycol", "clear", "transparent", "food-safe"],
            "tpu": ["tpu", "flexible", "rubber", "soft", "bendable"],
            "nylon": ["nylon", "pa", "engineering", "industrial", "tough"],
            "wood": ["wood", "wooden", "natural", "organic"],
            "metal": ["metal", "metallic", "steel", "aluminum", "brass"]
        }
    
    def _load_dimension_patterns(self) -> None:
        """Load dimension extraction patterns."""
        self.dimension_patterns = [
            # Standard dimensions (x by y by z)
            r"(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*(?:x|by|\×)\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*(?:x|by|\×)?\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            # Single dimension (cube)
            r"(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*(?:cube|cubed)",
            # Width/height/depth specifications
            r"width\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            r"height\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            r"depth\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            r"length\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            # Diameter/radius for round objects
            r"diameter\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            r"radius\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            # General size indicators
            r"size\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?",
            r"(\d+(?:\.\d+)?)\s*(?:cm|mm|inch|in)?\s*(?:in\s*)?(?:size|diameter|width|height)"
        ]
    
    def execute_task(self, task_details: Dict[str, Any]) -> TaskResult:
        """
        Execute intent recognition task with optional web research.
        
        Args:
            task_details: Dictionary containing task parameters
            
        Returns:
            Dictionary with task execution results
        """
        try:
            # Validate input
            self.validate_input(task_details)
            
            # Extract user request
            user_request = task_details.get("user_request", "")
            context = task_details.get("context", {})
            analysis_depth = task_details.get("analysis_depth", "standard")
            enable_web_research = task_details.get("enable_web_research", False)
            
            self.logger.info(f"Starting intent recognition for: {user_request[:100]}...")
            
            # Extract intent using primary method (spaCy + patterns)
            intent_result = self.extract_intent(user_request, context, analysis_depth)
            
            # Perform web research if enabled and confidence is low
            if (enable_web_research and 
                intent_result.get("confidence", 0) < ConfidenceLevel.HIGH.value and
                self.rate_limiter and self.rate_limiter.can_make_request()):
                
                # Generate search queries based on intent
                search_queries = self._generate_search_queries(intent_result, user_request)
                web_research_results = []
                
                for query in search_queries:
                    if self.rate_limiter.can_make_request():
                        self.rate_limiter.record_request()
                        research_summary = self.research(query)
                        # Convert summary to structured format expected by enhancement method
                        web_research_results.append({
                            "query": query,
                            "snippet": research_summary
                        })
                
                # Enhance intent result with web research
                if web_research_results:
                    intent_result = self._enhance_with_web_research(intent_result, web_research_results)
            
            # Generate design specifications
            design_specifications = self.generate_design_specifications(intent_result, analysis_depth)
            
            # Create research output
            research_output = ResearchAgentOutput(
                requirements=intent_result,
                object_specifications=design_specifications,
                material_recommendations=intent_result.get("material_recommendations", []),
                complexity_score=intent_result.get("complexity_score", 5.0),
                feasibility_assessment=intent_result.get("feasibility_assessment", "Feasible with standard 3D printing"),
                recommendations=intent_result.get("recommendations", [])
            )
            
            self.logger.info(f"Intent recognition completed with confidence: {intent_result.get('confidence', 0.0)}")
            
            return TaskResult(
                success=True,
                data=research_output.model_dump(),
                execution_time=None,
                metadata={
                    "confidence": intent_result.get("confidence", 0.0),
                    "method_used": intent_result.get("method_used", "unknown"),
                    "analysis_depth": analysis_depth,
                    "web_research_used": enable_web_research,
                    "design_specifications_generated": True,
                    "specification_version": design_specifications.get("metadata", {}).get("specification_version", "1.0")
                }
            )
            
        except Exception as e:
            self.logger.error(f"Intent recognition failed: {str(e)}")
            return TaskResult(
                success=False,
                error_message=str(e),
                data={}
            )
    
    def research(self, keywords: List[str]) -> str:
        """
        Perform web research with rate limiting and caching.
        
        Args:
            keywords: List of search keywords
            
        Returns:
            Research summary as string
        """
        if isinstance(keywords, str):
            keywords = [keywords]
        
        query = " ".join(keywords)
        cache_key = f"research_{hashlib.md5(query.encode()).hexdigest()}"
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Cache hit for query: {query}")
                return cached_result
        
        # Check rate limiting
        if not self.rate_limiter or not self.rate_limiter.can_make_request():
            self.logger.warning("Rate limit exceeded, skipping web research")
            return "Rate limit exceeded - no web research performed"
        
        try:
            # Record the request
            self.rate_limiter.record_request()
            
            # Perform search
            search_results = self._perform_web_search(query)
            
            # Summarize results
            if search_results and self.summarizer:
                combined_text = " ".join([result.get("snippet", "") for result in search_results])
                if len(combined_text) > 50:  # Only summarize if we have enough text
                    summary_result = self.summarizer(
                        combined_text[:1024],  # Limit input size
                        max_length=150,
                        min_length=30,
                        do_sample=False
                    )
                    summary = summary_result[0]["summary_text"] if summary_result else combined_text[:200]
                else:
                    summary = combined_text
            else:
                summary = f"Found {len(search_results)} results for '{query}'"
            
            # Cache the result for 24 hours
            if self.cache:
                self.cache.set(cache_key, summary, expire=86400)  # 24 hours
            
            self.logger.info(f"Web research completed for query: {query}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Web research failed: {str(e)}")
            return f"Web research failed: {str(e)}"
    
    def _perform_web_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform web search using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
        """
        results = []
        
        if not self.ddgs:
            return results
        
        try:
            self.logger.info(f"Performing web search for: {query}")
            
            # Use the search method directly
            search_results = self.ddgs.text(query, max_results=max_results)
            
            for result in search_results:
                if len(results) >= max_results:
                    break
                
                # Extract relevant information
                title = result.get("title", "")
                body = result.get("body", "")
                href = result.get("href", "")
                
                if title and body:
                    results.append({
                        "title": title,
                        "snippet": body[:300],  # Limit snippet size
                        "url": href
                    })
            
            self.logger.info(f"Found {len(results)} search results")
            
        except Exception as e:
            self.logger.error(f"Web search failed: {str(e)}")
        
        return results
    
    def _generate_search_queries(self, intent_result: Dict[str, Any], user_request: str) -> List[str]:
        """Generate search queries based on intent result."""
        queries = []
        object_type = intent_result.get("object_type", "unknown")
        material = intent_result.get("material_type", "pla")
        
        # Basic search queries
        queries.append(f"3D printing {object_type} {material}")
        queries.append(f"{object_type} 3D print design")
        
        # Add specific queries based on object type
        if object_type == "phone_case":
            queries.append("custom phone case 3D printing tips")
        elif object_type == "gear":
            queries.append("3D printed gear mechanical design")
        elif object_type == "bracket":
            queries.append("functional bracket 3D printing")
        
        return queries[:3]  # Limit to 3 queries to respect rate limits
    
    def _enhance_with_web_research(self, intent_result: Dict[str, Any], web_results: List[Dict[str, str]]) -> Dict[str, Any]:
        """Enhance intent result with web research findings."""
        # Add web research insights to recommendations
        recommendations = intent_result.get("recommendations", [])
        
        # Analyze web results for additional insights
        for result in web_results:
            snippet = result.get("snippet", "").lower()
            
            # Look for material recommendations
            if "material" in snippet:
                if "abs" in snippet and "ABS" not in intent_result.get("material_recommendations", []):
                    recommendations.append("Consider ABS for strength (from web research)")
                elif "tpu" in snippet and "flexible" in snippet:
                    recommendations.append("TPU recommended for flexible parts (from web research)")
            
            # Look for printing tips
            if "support" in snippet:
                recommendations.append("Review support requirements (from web research)")
            if "orientation" in snippet:
                recommendations.append("Print orientation is critical (from web research)")
        
        intent_result["recommendations"] = recommendations
        
        # Slightly boost confidence if web research provides relevant info
        if web_results:
            intent_result["confidence"] = min(intent_result.get("confidence", 0) + 0.1, 1.0)
        
        return intent_result
    
    def generate_design_specifications(self, intent_result: Dict[str, Any], analysis_depth: str = "standard") -> Dict[str, Any]:
        """
        Generate comprehensive 3D design specifications from intent analysis results.
        
        This method transforms research findings into detailed specifications that can be
        used by the CAD Agent to generate accurate 3D models.
        
        Args:
            intent_result: Results from intent recognition analysis
            analysis_depth: Level of detail for specifications
            
        Returns:
            Dict containing comprehensive design specifications
        """
        try:
            self.logger.info("Generating design specifications...")
            
            object_type = intent_result.get("object_type", "unknown")
            dimensions = intent_result.get("dimensions", {})
            material_type = intent_result.get("material_type", "PLA")
            special_features = intent_result.get("special_features", [])
            
            # Create base specifications structure
            specifications = {
                "geometry": self._generate_geometry_specifications(object_type, dimensions, special_features),
                "materials": self._generate_material_specifications(material_type, object_type),
                "manufacturing": self._generate_manufacturing_specifications(material_type, object_type, analysis_depth),
                "constraints": self._generate_design_constraints(object_type, material_type),
                "features": self._generate_feature_specifications(special_features, object_type),
                "metadata": {
                    "object_type": object_type,
                    "specification_version": "1.0",
                    "generated_at": datetime.now().isoformat(),
                    "analysis_depth": analysis_depth
                }
            }
            
            # Add object-specific specifications
            if object_type == "cube":
                specifications.update(self._generate_cube_specifications(dimensions, special_features))
            elif object_type == "cylinder":
                specifications.update(self._generate_cylinder_specifications(dimensions, special_features))
            elif object_type == "sphere":
                specifications.update(self._generate_sphere_specifications(dimensions, special_features))
            elif object_type == "phone_case":
                specifications.update(self._generate_phone_case_specifications(dimensions, special_features))
            elif object_type == "gear":
                specifications.update(self._generate_gear_specifications(dimensions, special_features))
            elif object_type == "bracket":
                specifications.update(self._generate_bracket_specifications(dimensions, special_features))
            
            # Apply design rules and validation
            specifications = self._apply_design_rules(specifications, material_type)
            specifications = self._validate_specifications(specifications)
            
            self.logger.info(f"Design specifications generated for {object_type}")
            return specifications
            
        except Exception as e:
            self.logger.error(f"Failed to generate design specifications: {str(e)}")
            raise ValidationError(f"Design specification generation failed: {str(e)}")
    
    def _generate_geometry_specifications(self, object_type: str, dimensions: Dict[str, float], features: List[str]) -> Dict[str, Any]:
        """Generate basic geometry specifications."""
        geometry = {
            "type": "primitive" if object_type in ["cube", "cylinder", "sphere"] else "complex",
            "primitive_type": object_type if object_type in ["cube", "cylinder", "sphere"] else None,
            "dimensions": self._normalize_dimensions(dimensions, object_type),
            "units": "mm",  # Standard unit for 3D printing
            "coordinate_system": "right_handed",
            "origin": {"x": 0, "y": 0, "z": 0}
        }
        
        # Add feature-specific geometry modifications
        if "hollow" in features:
            geometry["wall_thickness"] = self._calculate_wall_thickness(dimensions, object_type)
            geometry["internal_cavity"] = True
        
        return geometry
    
    def _generate_material_specifications(self, material_type: str, object_type: str) -> Dict[str, Any]:
        """Generate material specifications."""
        material_properties = {
            "PLA": {
                "density": 1.24,  # g/cm³
                "melting_point": 180,  # °C
                "glass_transition": 60,  # °C
                "shrinkage_factor": 0.003,  # 0.3%
                "tensile_strength": 50,  # MPa
                "flexibility": "rigid"
            },
            "ABS": {
                "density": 1.05,
                "melting_point": 230,
                "glass_transition": 105,
                "shrinkage_factor": 0.008,
                "tensile_strength": 40,
                "flexibility": "semi_rigid"
            },
            "TPU": {
                "density": 1.20,
                "melting_point": 200,
                "glass_transition": -40,
                "shrinkage_factor": 0.005,
                "tensile_strength": 35,
                "flexibility": "flexible"
            },
            "PETG": {
                "density": 1.27,
                "melting_point": 245,
                "glass_transition": 85,
                "shrinkage_factor": 0.002,
                "tensile_strength": 50,
                "flexibility": "semi_rigid"
            }
        }
        
        properties = material_properties.get(material_type.upper(), material_properties["PLA"])
        
        return {
            "type": material_type.upper(),
            "properties": properties,
            "suitability_score": self._calculate_material_suitability(material_type, object_type),
            "alternative_materials": self._suggest_alternative_materials(object_type)
        }
    
    def _generate_manufacturing_specifications(self, material_type: str, object_type: str, analysis_depth: str) -> Dict[str, Any]:
        """Generate manufacturing/printing specifications."""
        base_settings = {
            "layer_height": 0.2,  # mm
            "infill_percentage": 20,  # %
            "wall_count": 3,
            "top_bottom_layers": 3,
            "print_speed": 50,  # mm/s
            "support_required": "auto_detect"
        }
        
        # Material-specific adjustments
        material_adjustments = {
            "PLA": {"print_speed": 60, "bed_temperature": 60},
            "ABS": {"print_speed": 45, "bed_temperature": 100, "enclosure_required": True},
            "TPU": {"print_speed": 25, "retraction_distance": 1.0},
            "PETG": {"print_speed": 50, "bed_temperature": 75}
        }
        
        settings = base_settings.copy()
        if material_type.upper() in material_adjustments:
            settings.update(material_adjustments[material_type.upper()])
        
        # Object-specific adjustments
        if object_type == "phone_case":
            settings.update({
                "infill_percentage": 15,  # Lighter for comfort
                "wall_count": 2,  # Thinner walls for flexibility
                "support_required": False
            })
        elif object_type == "gear":
            settings.update({
                "infill_percentage": 100,  # Solid for strength
                "layer_height": 0.15,  # Higher precision
                "wall_count": 4
            })
        elif object_type == "sphere":
            settings["support_required"] = True
        
        # Analysis depth adjustments
        if analysis_depth == "detailed":
            settings.update({
                "layer_height": min(settings["layer_height"], 0.15),
                "infill_percentage": max(settings["infill_percentage"], 25),
                "print_speed": int(settings["print_speed"] * 0.8)  # Slower for quality
            })
        elif analysis_depth == "basic":
            settings.update({
                "layer_height": 0.25,
                "print_speed": int(settings["print_speed"] * 1.2)  # Faster for speed
            })
        
        return settings
    
    def _generate_design_constraints(self, object_type: str, material_type: str) -> Dict[str, Any]:
        """Generate design constraints and limitations."""
        min_wall_thickness = self._get_min_wall_thickness(material_type)
        
        constraints = {
            "minimum_wall_thickness": min_wall_thickness,
            "minimum_feature_size": max(0.4, min_wall_thickness * 0.5),
            "maximum_overhang_angle": 45,  # degrees
            "maximum_bridge_length": 15,  # mm
            "minimum_hole_diameter": 0.5,  # mm
            "draft_angle": 1,  # degrees for vertical walls
            "tolerance": 0.1  # mm
        }
        
        # Object-specific constraints
        if object_type == "gear":
            constraints.update({
                "minimum_tooth_thickness": 1.0,
                "maximum_module": 3.0,
                "minimum_tooth_count": 8
            })
        elif object_type == "phone_case":
            constraints.update({
                "maximum_wall_thickness": 3.0,
                "button_clearance": 0.3,
                "port_clearance": 0.5
            })
        
        return constraints
    
    def _generate_feature_specifications(self, special_features: List[str], object_type: str) -> Dict[str, Any]:
        """Generate specifications for special features."""
        features = {}
        
        if "hollow" in special_features:
            features["hollow"] = {
                "enabled": True,
                "wall_thickness": self._get_min_wall_thickness("PLA") * 2,
                "drainage_holes": True,
                "drainage_hole_diameter": 2.0
            }
        
        if "textured" in special_features:
            features["surface_texture"] = {
                "type": "geometric",
                "pattern": "crosshatch",
                "depth": 0.2,
                "spacing": 1.0
            }
        
        if "flexible" in special_features:
            features["flexibility"] = {
                "material_recommendation": "TPU",
                "wall_thickness_reduction": 0.8,
                "infill_reduction": 0.5
            }
        
        if "support_required" in special_features:
            features["supports"] = {
                "type": "tree",
                "density": 15,
                "interface_layers": 3,
                "overhang_threshold": 45
            }
        
        return features
    
    def _generate_cube_specifications(self, dimensions: Dict[str, float], features: List[str]) -> Dict[str, Any]:
        """Generate cube-specific specifications."""
        # Ensure cube has proper dimensions
        if not dimensions:
            dimensions = {"length": 20, "width": 20, "height": 20}
        
        # If only one dimension provided, make it a cube
        if len(dimensions) == 1:
            dim = list(dimensions.values())[0]
            dimensions = {"length": dim, "width": dim, "height": dim}
        
        return {
            "primitives": [{
                "type": "box",
                "dimensions": {
                    "length": dimensions.get("length", dimensions.get("x", 20)),
                    "width": dimensions.get("width", dimensions.get("y", 20)),
                    "height": dimensions.get("height", dimensions.get("z", 20))
                },
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0}
            }],
            "operations": []
        }
    
    def _generate_cylinder_specifications(self, dimensions: Dict[str, float], features: List[str]) -> Dict[str, Any]:
        """Generate cylinder-specific specifications."""
        diameter = dimensions.get("diameter", dimensions.get("radius", 10) * 2)
        height = dimensions.get("height", dimensions.get("length", 20))
        
        return {
            "primitives": [{
                "type": "cylinder",
                "dimensions": {
                    "diameter": diameter,
                    "height": height
                },
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0}
            }],
            "operations": []
        }
    
    def _generate_sphere_specifications(self, dimensions: Dict[str, float], features: List[str]) -> Dict[str, Any]:
        """Generate sphere-specific specifications."""
        diameter = dimensions.get("diameter", dimensions.get("radius", 10) * 2)
        
        return {
            "primitives": [{
                "type": "sphere",
                "dimensions": {
                    "diameter": diameter
                },
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0}
            }],
            "operations": []
        }
    
    def _generate_phone_case_specifications(self, dimensions: Dict[str, float], features: List[str]) -> Dict[str, Any]:
        """Generate phone case-specific specifications."""
        # Default iPhone dimensions if not specified
        phone_length = dimensions.get("length", 147)  # mm
        phone_width = dimensions.get("width", 71.5)   # mm
        phone_thickness = dimensions.get("thickness", 7.8)  # mm
        
        case_thickness = 2.0  # mm
        lip_height = 1.5  # mm
        
        return {
            "primitives": [
                {
                    "type": "box",
                    "name": "outer_shell",
                    "dimensions": {
                        "length": phone_length + case_thickness * 2,
                        "width": phone_width + case_thickness * 2,
                        "height": phone_thickness + case_thickness + lip_height
                    },
                    "position": {"x": 0, "y": 0, "z": 0}
                },
                {
                    "type": "box",
                    "name": "phone_cavity",
                    "dimensions": {
                        "length": phone_length + 0.3,  # Tolerance
                        "width": phone_width + 0.3,
                        "height": phone_thickness + 0.3
                    },
                    "position": {"x": 0, "y": 0, "z": case_thickness}
                }
            ],
            "operations": [
                {
                    "type": "subtract",
                    "operand1": "outer_shell",
                    "operand2": "phone_cavity"
                }
            ],
            "cutouts": [
                {
                    "type": "camera",
                    "position": {"x": phone_length/2 - 15, "y": phone_width/2 - 15, "z": 0},
                    "dimensions": {"diameter": 12, "depth": case_thickness + 1}
                },
                {
                    "type": "charging_port",
                    "position": {"x": 0, "y": -phone_width/2, "z": case_thickness/2},
                    "dimensions": {"width": 25, "height": 8, "depth": case_thickness + 1}
                }
            ]
        }
    
    def _generate_gear_specifications(self, dimensions: Dict[str, float], features: List[str]) -> Dict[str, Any]:
        """Generate gear-specific specifications."""
        teeth_count = int(dimensions.get("teeth", dimensions.get("tooth_count", 20)))
        module = dimensions.get("module", 2.0)  # Standard module
        thickness = dimensions.get("thickness", dimensions.get("height", 5))
        
        # Calculate gear parameters
        pitch_diameter = teeth_count * module
        outer_diameter = pitch_diameter + 2 * module
        root_diameter = pitch_diameter - 2.5 * module
        
        return {
            "primitives": [
                {
                    "type": "cylinder",
                    "name": "gear_blank",
                    "dimensions": {
                        "diameter": outer_diameter,
                        "height": thickness
                    },
                    "position": {"x": 0, "y": 0, "z": 0}
                }
            ],
            "operations": [],
            "gear_parameters": {
                "teeth_count": teeth_count,
                "module": module,
                "pitch_diameter": pitch_diameter,
                "outer_diameter": outer_diameter,
                "root_diameter": root_diameter,
                "thickness": thickness,
                "pressure_angle": 20,  # Standard pressure angle
                "tooth_profile": "involute"
            }
        }
    
    def _generate_bracket_specifications(self, dimensions: Dict[str, float], features: List[str]) -> Dict[str, Any]:
        """Generate bracket-specific specifications."""
        length = dimensions.get("length", 50)
        width = dimensions.get("width", 30)
        thickness = dimensions.get("thickness", 5)
        hole_diameter = dimensions.get("hole_diameter", 5)
        
        return {
            "primitives": [
                {
                    "type": "box",
                    "name": "bracket_body",
                    "dimensions": {
                        "length": length,
                        "width": width,
                        "height": thickness
                    },
                    "position": {"x": 0, "y": 0, "z": 0}
                }
            ],
            "operations": [],
            "mounting_holes": [
                {
                    "type": "cylinder",
                    "diameter": hole_diameter,
                    "depth": thickness + 1,
                    "position": {"x": length/4, "y": width/4, "z": -0.5}
                },
                {
                    "type": "cylinder", 
                    "diameter": hole_diameter,
                    "depth": thickness + 1,
                    "position": {"x": -length/4, "y": -width/4, "z": -0.5}
                }
            ]
        }
    
    def _normalize_dimensions(self, dimensions: Dict[str, float], object_type: str) -> Dict[str, float]:
        """Normalize dimensions to standard format."""
        normalized = {}
        
        # Convert common dimension names to standard format
        dimension_mapping = {
            "x": "length", "y": "width", "z": "height",
            "w": "width", "h": "height", "l": "length",
            "d": "diameter", "r": "radius"
        }
        
        for key, value in dimensions.items():
            standard_key = dimension_mapping.get(key.lower(), key.lower())
            normalized[standard_key] = float(value)
        
        # Convert radius to diameter if needed
        if "radius" in normalized and "diameter" not in normalized:
            normalized["diameter"] = normalized["radius"] * 2
            del normalized["radius"]
        
        # Ensure minimum dimensions
        min_dimension = 1.0  # mm
        for key in normalized:
            normalized[key] = max(normalized[key], min_dimension)
        
        return normalized
    
    def _calculate_wall_thickness(self, dimensions: Dict[str, float], object_type: str) -> float:
        """Calculate appropriate wall thickness for hollow objects."""
        min_thickness = 1.2  # mm minimum for PLA
        
        # Base thickness on largest dimension
        max_dim = max(dimensions.values()) if dimensions else 20
        
        if max_dim < 10:
            return min_thickness
        elif max_dim < 50:
            return min_thickness * 1.5
        else:
            return min_thickness * 2.0
    
    def _calculate_material_suitability(self, material_type: str, object_type: str) -> float:
        """Calculate how suitable a material is for the object type (0-10)."""
        suitability_matrix = {
            ("PLA", "cube"): 9.0,
            ("PLA", "cylinder"): 9.0,
            ("PLA", "sphere"): 8.0,
            ("PLA", "phone_case"): 6.0,
            ("PLA", "gear"): 7.0,
            ("PLA", "bracket"): 8.0,
            ("ABS", "cube"): 8.0,
            ("ABS", "cylinder"): 8.0,
            ("ABS", "sphere"): 7.0,
            ("ABS", "phone_case"): 7.0,
            ("ABS", "gear"): 9.0,
            ("ABS", "bracket"): 9.0,
            ("TPU", "cube"): 5.0,
            ("TPU", "cylinder"): 5.0,
            ("TPU", "sphere"): 6.0,
            ("TPU", "phone_case"): 10.0,
            ("TPU", "gear"): 3.0,
            ("TPU", "bracket"): 4.0,
        }
        
        return suitability_matrix.get((material_type.upper(), object_type), 5.0)
    
    def _suggest_alternative_materials(self, object_type: str) -> List[str]:
        """Suggest alternative materials for the object type."""
        suggestions = {
            "cube": ["PLA", "ABS", "PETG"],
            "cylinder": ["PLA", "ABS", "PETG"],
            "sphere": ["PLA", "ABS", "PETG"],
            "phone_case": ["TPU", "PETG", "ABS"],
            "gear": ["ABS", "PETG", "Nylon"],
            "bracket": ["ABS", "PETG", "Nylon"]
        }
        
        return suggestions.get(object_type, ["PLA", "ABS"])
    
    def _apply_design_rules(self, specifications: Dict[str, Any], material_type: str) -> Dict[str, Any]:
        """Apply 3D printing design rules and constraints."""
        constraints = specifications.get("constraints", {})
        min_wall = constraints.get("minimum_wall_thickness", 1.2)
        
        # Ensure all dimensions respect minimum constraints
        if "primitives" in specifications:
            for primitive in specifications["primitives"]:
                dims = primitive.get("dimensions", {})
                for key, value in dims.items():
                    if key in ["wall_thickness", "thickness"] and value < min_wall:
                        dims[key] = min_wall
        
        # Add design warnings
        specifications["design_warnings"] = []
        
        # Check for potential issues
        geometry = specifications.get("geometry", {})
        if geometry.get("type") == "complex":
            specifications["design_warnings"].append("Complex geometry may require supports")
        
        return specifications
    
    def _validate_specifications(self, specifications: Dict[str, Any]) -> Dict[str, Any]:
        """Validate design specifications for completeness and correctness."""
        required_sections = ["geometry", "materials", "manufacturing", "constraints"]
        
        for section in required_sections:
            if section not in specifications:
                raise ValidationError(f"Missing required specification section: {section}")
        
        # Validate geometry
        geometry = specifications["geometry"]
        if "dimensions" not in geometry:
            raise ValidationError("Geometry specifications missing dimensions")
        
        # Validate materials
        materials = specifications["materials"]
        if "type" not in materials:
            raise ValidationError("Material specifications missing type")
        
        # Add validation timestamp
        specifications["validation"] = {
            "validated_at": datetime.now().isoformat(),
            "status": "passed",
            "warnings": specifications.get("design_warnings", [])
        }
        
        return specifications

    # [All the existing intent extraction methods remain the same]
    def extract_intent(
        self,
        user_request: str,
        context: Dict[str, Any] = None,
        analysis_depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        Extract intent from user request with fallback strategies.
        
        Args:
            user_request: Natural language description
            context: Additional context information
            analysis_depth: Level of analysis (basic, standard, detailed)
            
        Returns:
            Dictionary with extracted intent information
        """
        context = context or {}
        
        # Try primary method (spaCy NER + Pattern Matching)
        if self.nlp:
            try:
                intent_result = self._extract_intent_spacy(user_request, context, analysis_depth)
                if intent_result["confidence"] >= ConfidenceLevel.MEDIUM.value:
                    intent_result["method_used"] = "spacy_primary"
                    return intent_result
            except Exception as e:
                self.logger.warning(f"spaCy intent extraction failed: {str(e)}")
        
        # Fallback to regex-based extraction
        try:
            intent_result = self._extract_intent_regex(user_request, context, analysis_depth)
            intent_result["method_used"] = "regex_fallback"
            return intent_result
        except Exception as e:
            self.logger.error(f"Regex fallback failed: {str(e)}")
        
        # Final fallback - basic keyword matching
        intent_result = self._extract_intent_keywords(user_request, context)
        intent_result["method_used"] = "keyword_fallback"
        return intent_result
    
    def _extract_intent_spacy(
        self,
        user_request: str,
        context: Dict[str, Any],
        analysis_depth: str
    ) -> Dict[str, Any]:
        """Extract intent using spaCy NER and pattern matching."""
        doc = self.nlp(user_request.lower())
        
        # Initialize result structure
        result = {
            "object_type": "unknown",
            "dimensions": {"x": 20.0, "y": 20.0, "z": 20.0},  # Default 2cm cube
            "material_type": "pla",
            "special_features": [],
            "confidence": 0.0,
            "specifications": {},
            "material_recommendations": ["PLA"],
            "complexity_score": 5.0,
            "feasibility_assessment": "Feasible with standard 3D printing",
            "recommendations": []
        }
        
        # Extract entities using spaCy NER
        entities = {ent.label_: ent.text for ent in doc.ents}
        
        # Find best matching pattern
        best_pattern = None
        best_score = 0.0
        
        for pattern in self.intent_patterns:
            score = self._calculate_pattern_score(user_request, pattern, doc)
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        if best_pattern:
            result["object_type"] = best_pattern.name
            result["confidence"] = min(best_score, 1.0)
            
            # Extract dimensions based on pattern
            dimensions = self._extract_dimensions_spacy(user_request, best_pattern, doc)
            if dimensions:
                result["dimensions"] = dimensions
            
            # Extract material information
            material_info = self._extract_material_spacy(user_request, best_pattern, doc)
            result.update(material_info)
            
            # Extract special features
            features = self._extract_features_spacy(user_request, doc, analysis_depth)
            result["special_features"] = features
            
            # Generate specifications
            result["specifications"] = self._generate_specifications(result, analysis_depth)
            
            # Generate recommendations
            result["recommendations"] = self._generate_recommendations(result, analysis_depth)
            
            # Calculate complexity score
            result["complexity_score"] = self._calculate_complexity_score(result)
            
            # Generate feasibility assessment
            result["feasibility_assessment"] = self._assess_feasibility(result)
        
        return result
    
    def _extract_intent_regex(
        self,
        user_request: str,
        context: Dict[str, Any],
        analysis_depth: str
    ) -> Dict[str, Any]:
        """Extract intent using regex patterns."""
        result = {
            "object_type": "unknown",
            "dimensions": {"x": 20.0, "y": 20.0, "z": 20.0},
            "material_type": "pla",
            "special_features": [],
            "confidence": 0.0,
            "specifications": {},
            "material_recommendations": ["PLA"],
            "complexity_score": 5.0,
            "feasibility_assessment": "Feasible with standard 3D printing",
            "recommendations": []
        }
        
        user_text = user_request.lower()
        best_score = 0.0
        best_pattern = None
        
        # Test each pattern
        for pattern in self.intent_patterns:
            score = 0.0
            
            # Check regex patterns
            for regex_pattern in pattern.regex_patterns:
                if re.search(regex_pattern, user_text):
                    score += 0.3
            
            # Check keywords
            for keyword in pattern.keywords:
                if keyword in user_text:
                    score += 0.2
            
            # Apply confidence boost
            score += pattern.confidence_boost
            
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        if best_pattern:
            result["object_type"] = best_pattern.name
            result["confidence"] = min(best_score, 0.8)  # Cap regex confidence at 0.8
            
            # Extract dimensions using regex
            dimensions = self._extract_dimensions_regex(user_text, best_pattern)
            if dimensions:
                result["dimensions"] = dimensions
            
            # Extract material using regex
            material_info = self._extract_material_regex(user_text, best_pattern)
            result.update(material_info)
            
            # Extract features using regex
            features = self._extract_features_regex(user_text)
            result["special_features"] = features
            
            # Generate additional information
            result["specifications"] = self._generate_specifications(result, analysis_depth)
            result["recommendations"] = self._generate_recommendations(result, analysis_depth)
            result["complexity_score"] = self._calculate_complexity_score(result)
            result["feasibility_assessment"] = self._assess_feasibility(result)
        
        return result
    
    def _extract_intent_keywords(self, user_request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Final fallback using basic keyword matching."""
        result = {
            "object_type": "cube",  # Default to cube
            "dimensions": {"x": 20.0, "y": 20.0, "z": 20.0},
            "material_type": "pla",
            "special_features": [],
            "confidence": ConfidenceLevel.LOW.value,
            "specifications": {},
            "material_recommendations": ["PLA"],
            "complexity_score": 3.0,
            "feasibility_assessment": "Basic object, should be feasible",
            "recommendations": ["Simple geometric shape", "Good for beginners"]
        }
        
        user_text = user_request.lower()
        
        # Basic object type detection
        if any(word in user_text for word in ["cylinder", "tube", "pipe"]):
            result["object_type"] = "cylinder"
        elif any(word in user_text for word in ["sphere", "ball", "globe"]):
            result["object_type"] = "sphere"
        elif any(word in user_text for word in ["phone", "case", "cover"]):
            result["object_type"] = "phone_case"
        elif any(word in user_text for word in ["gear", "cog"]):
            result["object_type"] = "gear"
        elif any(word in user_text for word in ["bracket", "mount", "holder"]):
            result["object_type"] = "bracket"
        
        # Basic dimension extraction
        numbers = re.findall(r'\d+(?:\.\d+)?', user_text)
        if numbers:
            if len(numbers) >= 3:
                result["dimensions"] = {
                    "x": float(numbers[0]),
                    "y": float(numbers[1]),
                    "z": float(numbers[2])
                }
            elif len(numbers) == 1:
                size = float(numbers[0])
                result["dimensions"] = {"x": size, "y": size, "z": size}
        
        return result
    
    def _calculate_pattern_score(
        self,
        user_request: str,
        pattern: IntentPattern,
        doc
    ) -> float:
        """Calculate matching score for a pattern."""
        score = 0.0
        user_text = user_request.lower()
        
        # Check regex patterns
        for regex_pattern in pattern.regex_patterns:
            if re.search(regex_pattern, user_text):
                score += 0.3
        
        # Check keywords
        for keyword in pattern.keywords:
            if keyword in user_text:
                score += 0.25
        
        # Check material keywords
        for material in pattern.material_keywords:
            if material in user_text:
                score += 0.1
        
        # Check spaCy entities
        for token in doc:
            if token.text.lower() in pattern.keywords:
                score += 0.2
        
        # Apply pattern-specific confidence boost
        score += pattern.confidence_boost
        
        return score
    
    def _extract_dimensions_spacy(
        self,
        user_request: str,
        pattern: IntentPattern,
        doc
    ) -> Optional[Dict[str, float]]:
        """Extract dimensions using spaCy analysis."""
        dimensions = {}
        
        # Try pattern-specific dimension patterns first
        for dim_pattern in pattern.dimension_patterns:
            match = re.search(dim_pattern, user_request.lower())
            if match:
                numbers = [float(g) for g in match.groups() if g and g.replace('.', '').isdigit()]
                if len(numbers) >= 3:
                    return {"x": numbers[0], "y": numbers[1], "z": numbers[2]}
                elif len(numbers) == 2:
                    return {"x": numbers[0], "y": numbers[1], "z": numbers[0]}
                elif len(numbers) == 1:
                    return {"x": numbers[0], "y": numbers[0], "z": numbers[0]}
        
        # Try general dimension patterns
        for dim_pattern in self.dimension_patterns:
            match = re.search(dim_pattern, user_request.lower())
            if match:
                numbers = [float(g) for g in match.groups() if g and g.replace('.', '').isdigit()]
                if numbers:
                    if len(numbers) >= 3:
                        return {"x": numbers[0], "y": numbers[1], "z": numbers[2]}
                    elif len(numbers) == 2:
                        return {"x": numbers[0], "y": numbers[1], "z": max(numbers)}
                    elif len(numbers) == 1:
                        size = numbers[0]
                        # Adjust based on object type
                        if pattern.name == "cylinder":
                            return {"x": size, "y": size, "z": size * 2}  # Assume height = 2 * diameter
                        else:
                            return {"x": size, "y": size, "z": size}
        
        return None
    
    def _extract_dimensions_regex(self, user_text: str, pattern: IntentPattern) -> Optional[Dict[str, float]]:
        """Extract dimensions using regex patterns."""
        # Similar to spaCy version but simpler
        for dim_pattern in pattern.dimension_patterns + self.dimension_patterns:
            match = re.search(dim_pattern, user_text)
            if match:
                numbers = [float(g) for g in match.groups() if g and g.replace('.', '').isdigit()]
                if numbers:
                    if len(numbers) >= 3:
                        return {"x": numbers[0], "y": numbers[1], "z": numbers[2]}
                    elif len(numbers) == 2:
                        return {"x": numbers[0], "y": numbers[1], "z": max(numbers)}
                    elif len(numbers) == 1:
                        size = numbers[0]
                        return {"x": size, "y": size, "z": size}
        
        return None
    
    def _extract_material_spacy(
        self,
        user_request: str,
        pattern: IntentPattern,
        doc
    ) -> Dict[str, Any]:
        """Extract material information using spaCy."""
        material_info = {
            "material_type": "pla",
            "material_recommendations": ["PLA"]
        }
        
        user_text = user_request.lower()
        
        # Check for explicit material mentions
        for material, keywords in self.material_mappings.items():
            for keyword in keywords:
                if keyword in user_text:
                    material_info["material_type"] = material.upper()
                    material_info["material_recommendations"] = [material.upper()]
                    return material_info
        
        # Use pattern-specific material recommendations
        if pattern.material_keywords:
            # Find best matching material from pattern
            for pattern_material in pattern.material_keywords:
                for material, keywords in self.material_mappings.items():
                    if pattern_material in keywords:
                        material_info["material_type"] = material.upper()
                        material_info["material_recommendations"] = [material.upper()]
                        break
        
        return material_info
    
    def _extract_material_regex(self, user_text: str, pattern: IntentPattern) -> Dict[str, Any]:
        """Extract material information using regex."""
        return self._extract_material_spacy(user_text, pattern, None)  # Reuse spaCy logic
    
    def _extract_features_spacy(self, user_request: str, doc, analysis_depth: str) -> List[str]:
        """Extract special features using spaCy analysis."""
        features = []
        user_text = user_request.lower()
        
        # Basic feature keywords
        feature_keywords = {
            "hollow": ["hollow", "empty", "cavity"],
            "textured": ["textured", "rough", "pattern", "embossed"],
            "flexible": ["flexible", "bendable", "soft"],
            "transparent": ["transparent", "clear", "see-through"],
            "colored": ["colored", "color", "red", "blue", "green", "black", "white"],
            "threaded": ["threaded", "screw", "bolt"],
            "interlocking": ["interlocking", "connecting", "modular"],
            "functional": ["functional", "working", "moving", "mechanical"],
            "decorative": ["decorative", "ornamental", "artistic"]
        }
        
        for feature, keywords in feature_keywords.items():
            if any(keyword in user_text for keyword in keywords):
                features.append(feature)
        
        # Advanced feature detection for detailed analysis
        if analysis_depth == "detailed":
            # Look for more complex features
            advanced_features = {
                "support_required": ["overhang", "bridge", "cantilever"],
                "multi_part": ["assembly", "parts", "components"],
                "precision_required": ["precise", "accurate", "tight", "tolerance"],
                "large_size": ["large", "big", "huge", "massive"],
                "small_details": ["detail", "fine", "intricate", "complex"]
            }
            
            for feature, keywords in advanced_features.items():
                if any(keyword in user_text for keyword in keywords):
                    features.append(feature)
        
        return features
    
    def _extract_features_regex(self, user_text: str) -> List[str]:
        """Extract features using regex patterns."""
        features = []
        
        # Simple feature detection patterns
        feature_patterns = [
            (r"hollow|empty|cavity", "hollow"),
            (r"textured|rough|pattern", "textured"),
            (r"flexible|bendable|soft", "flexible"),
            (r"transparent|clear", "transparent"),
            (r"threaded|screw", "threaded"),
            (r"functional|working|moving", "functional")
        ]
        
        for pattern, feature in feature_patterns:
            if re.search(pattern, user_text):
                features.append(feature)
        
        return features
    
    def _generate_specifications(self, result: Dict[str, Any], analysis_depth: str) -> Dict[str, Any]:
        """Generate detailed specifications based on extracted intent."""
        specs = {
            "geometry": {
                "type": "primitive" if result["object_type"] in ["cube", "cylinder", "sphere"] else "composite",
                "base_shape": result["object_type"],
                "dimensions": result["dimensions"],
                "modifications": result["special_features"]
            },
            "constraints": {
                "min_wall_thickness": self._get_min_wall_thickness(result["material_type"]),
                "support_needed": self._requires_support(result),
                "print_orientation": self._get_optimal_orientation(result["object_type"])
            },
            "metadata": {
                "complexity_score": result.get("complexity_score", 5),
                "estimated_print_time": self._estimate_print_time(result)
            }
        }
        
        if analysis_depth == "detailed":
            specs["advanced"] = {
                "infill_percentage": self._recommend_infill(result),
                "layer_height": self._recommend_layer_height(result),
                "print_speed": self._recommend_print_speed(result),
                "temperature_settings": self._get_temperature_settings(result["material_type"])
            }
        
        return specs
    
    def _generate_recommendations(self, result: Dict[str, Any], analysis_depth: str) -> List[str]:
        """Generate printing recommendations."""
        recommendations = []
        
        # Basic recommendations
        if result["object_type"] == "cube":
            recommendations.append("Simple rectangular object, ideal for beginners")
        elif result["object_type"] == "cylinder":
            recommendations.append("May require supports depending on orientation")
        elif result["object_type"] == "sphere":
            recommendations.append("Will require supports, consider printing in two halves")
        elif result["object_type"] == "phone_case":
            recommendations.append("Use flexible material like TPU for better protection")
        elif result["object_type"] == "gear":
            recommendations.append("Use strong material like ABS or PETG for mechanical parts")
        
        # Material-specific recommendations
        if result["material_type"].lower() == "pla":
            recommendations.append("PLA is easy to print and biodegradable")
        elif result["material_type"].lower() == "abs":
            recommendations.append("ABS requires heated bed and good ventilation")
        elif result["material_type"].lower() == "tpu":
            recommendations.append("TPU is flexible but requires slower print speeds")
        
        # Feature-specific recommendations
        if "hollow" in result["special_features"]:
            recommendations.append("Consider adding drainage holes for hollow objects")
        if "support_required" in result["special_features"]:
            recommendations.append("Design with minimal overhangs to reduce support needs")
        
        # Size-specific recommendations
        max_dim = max(result["dimensions"].values())
        if max_dim > 100:
            recommendations.append("Large object may require splitting into parts")
        elif max_dim < 5:
            recommendations.append("Very small object may require high-resolution printer")
        
        return recommendations
    
    def _calculate_complexity_score(self, result: Dict[str, Any]) -> float:
        """Calculate complexity score (0-10)."""
        score = 3.0  # Base score
        
        # Object type complexity
        type_complexity = {
            "cube": 1,
            "cylinder": 2,
            "sphere": 3,
            "phone_case": 6,
            "gear": 7,
            "bracket": 5
        }
        score += type_complexity.get(result["object_type"], 5)
        
        # Features add complexity
        score += len(result["special_features"]) * 0.5
        
        # Size complexity
        max_dim = max(result["dimensions"].values())
        if max_dim > 100:
            score += 1
        elif max_dim < 5:
            score += 2
        
        return min(score, 10.0)
    
    def _assess_feasibility(self, result: Dict[str, Any]) -> str:
        """Assess printing feasibility."""
        complexity = result.get("complexity_score", 5)
        
        if complexity <= 3:
            return "Very feasible - simple geometry suitable for any 3D printer"
        elif complexity <= 5:
            return "Feasible with standard 3D printing - may require basic supports"
        elif complexity <= 7:
            return "Moderately complex - requires careful planning and possibly advanced settings"
        else:
            return "Complex object - may require advanced printer capabilities or multi-part design"
    
    def _get_min_wall_thickness(self, material: str) -> float:
        """Get minimum wall thickness for material."""
        thickness_map = {
            "pla": 1.2,
            "abs": 1.5,
            "petg": 1.3,
            "tpu": 2.0,
            "nylon": 1.8
        }
        return thickness_map.get(material.lower(), 1.5)
    
    def _requires_support(self, result: Dict[str, Any]) -> bool:
        """Determine if object requires support material."""
        object_type = result["object_type"]
        features = result["special_features"]
        
        if object_type in ["sphere"]:
            return True
        if "overhang" in features or "bridge" in features:
            return True
        if object_type == "cylinder":
            # Depends on orientation
            return True
        
        return False
    
    def _get_optimal_orientation(self, object_type: str) -> str:
        """Get optimal print orientation."""
        orientation_map = {
            "cube": "any",
            "cylinder": "standing",
            "sphere": "any_with_supports",
            "phone_case": "back_down",
            "gear": "flat",
            "bracket": "minimize_overhangs"
        }
        return orientation_map.get(object_type, "flat")
    
    def _estimate_print_time(self, result: Dict[str, Any]) -> str:
        """Estimate print time based on object properties."""
        dims = result["dimensions"]
        volume = dims["x"] * dims["y"] * dims["z"]
        
        # Basic time estimation (very rough)
        base_time_minutes = volume * 2  # 2 minutes per cubic cm
        
        # Adjust for complexity
        complexity_multiplier = 1 + (result.get("complexity_score", 5) / 10)
        total_minutes = base_time_minutes * complexity_multiplier
        
        if total_minutes < 60:
            return f"{int(total_minutes)} minutes"
        else:
            hours = int(total_minutes / 60)
            minutes = int(total_minutes % 60)
            return f"{hours}h {minutes}m"
    
    def _recommend_infill(self, result: Dict[str, Any]) -> int:
        """Recommend infill percentage."""
        if result["object_type"] in ["gear", "bracket"]:
            return 80  # Functional parts need high infill
        elif "decorative" in result["special_features"]:
            return 15  # Decorative parts can be lighter
        else:
            return 20  # Standard infill
    
    def _recommend_layer_height(self, result: Dict[str, Any]) -> float:
        """Recommend layer height."""
        if "small_details" in result["special_features"]:
            return 0.1  # Fine details need thin layers
        elif max(result["dimensions"].values()) > 50:
            return 0.3  # Large objects can use thicker layers
        else:
            return 0.2  # Standard layer height
    
    def _recommend_print_speed(self, result: Dict[str, Any]) -> int:
        """Recommend print speed in mm/s."""
        if result["material_type"].lower() == "tpu":
            return 25  # Flexible materials need slow speeds
        elif "precision_required" in result["special_features"]:
            return 40  # Precision parts need slower speeds
        else:
            return 60  # Standard speed
    
    def _get_temperature_settings(self, material: str) -> Dict[str, int]:
        """Get temperature settings for material."""
        temp_map = {
            "pla": {"nozzle": 210, "bed": 60},
            "abs": {"nozzle": 240, "bed": 80},
            "petg": {"nozzle": 230, "bed": 70},
            "tpu": {"nozzle": 220, "bed": 50},
            "nylon": {"nozzle": 260, "bed": 90}
        }
        return temp_map.get(material.lower(), {"nozzle": 210, "bed": 60})
    
    def validate_input(self, task_details: Dict[str, Any]) -> bool:
        """Validate research agent input."""
        if not isinstance(task_details, dict):
            raise ValidationError("task_details must be a dictionary")
        
        if "user_request" not in task_details:
            raise ValidationError("user_request is required")
        
        user_request = task_details["user_request"]
        if not isinstance(user_request, str) or not user_request.strip():
            raise ValidationError("user_request must be a non-empty string")
        
        if len(user_request) > 1000:
            raise ValidationError("user_request too long (max 1000 characters)")
        
        analysis_depth = task_details.get("analysis_depth", "standard")
        if analysis_depth not in ["basic", "standard", "detailed"]:
            raise ValidationError("analysis_depth must be 'basic', 'standard', or 'detailed'")
        
        return True


# Utility functions for testing
def create_test_research_agent() -> ResearchAgent:
    """Create a research agent for testing."""
    return ResearchAgent("test_research_agent")


def create_test_intent_request(user_request: str, analysis_depth: str = "standard", enable_web_research: bool = False) -> Dict[str, Any]:
    """Create a test intent recognition request with web research option."""
    return {
        "task_id": f"research_{hash(user_request) % 10000}",
        "user_request": user_request,
        "context": {},
        "analysis_depth": analysis_depth,
        "enable_web_research": enable_web_research
    }
