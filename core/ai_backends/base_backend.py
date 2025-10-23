#!/usr/bin/env python3
"""
Base Interface for AI 3D Generation Backends
AI Agent 3D Print System

This module defines the abstract base class that all AI 3D generation backends
must implement. This allows easy swapping between different AI models/services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
import trimesh

from core.logger import get_logger


class BaseAI3DBackend(ABC):
    """
    Abstract base class for AI 3D generation backends.
    
    All AI backends (local models, cloud APIs, etc.) must implement this interface.
    This enables easy switching between different AI providers without changing
    the rest of the application code.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI backend.
        
        Args:
            config: Backend-specific configuration
        """
        self.config = config or {}
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.is_initialized = False
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the AI backend (load models, connect to APIs, etc.).
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def image_to_3d(self, 
                         image_path: str, 
                         params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert a 2D image to a 3D model.
        
        Args:
            image_path: Path to input image
            params: Generation parameters (depth_scale, extrusion_height, etc.)
            
        Returns:
            Dict with:
                - mesh: trimesh.Trimesh object
                - metadata: dict with generation info
                - success: bool
        """
        pass
    
    @abstractmethod
    async def text_to_3d(self, 
                        prompt: str, 
                        params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a 3D model from text description.
        
        Args:
            prompt: Text description of desired 3D model
            params: Generation parameters (style, quality, size, etc.)
            
        Returns:
            Dict with:
                - mesh: trimesh.Trimesh object
                - metadata: dict with generation info
                - success: bool
        """
        pass
    
    @abstractmethod
    async def enhance_mesh(self, 
                          mesh: trimesh.Trimesh, 
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enhance/optimize an existing 3D mesh using AI.
        
        Args:
            mesh: Input mesh to enhance
            params: Enhancement parameters (smoothing, detail_level, etc.)
            
        Returns:
            Dict with:
                - mesh: Enhanced trimesh.Trimesh object
                - metadata: dict with enhancement info
                - success: bool
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get backend capabilities and limitations.
        
        Returns:
            Dict with:
                - supports_image_to_3d: bool
                - supports_text_to_3d: bool
                - supports_mesh_enhancement: bool
                - max_resolution: tuple (width, height)
                - supported_formats: list of str
                - cost_info: dict (if applicable)
        """
        pass
    
    @abstractmethod
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get backend identification and version info.
        
        Returns:
            Dict with:
                - name: str (backend name)
                - version: str
                - provider: str (local, openai, replicate, etc.)
                - description: str
        """
        pass
    
    def validate_params(self, params: Dict[str, Any], operation: str) -> bool:
        """
        Validate parameters for a specific operation.
        
        Args:
            params: Parameters to validate
            operation: Operation type (image_to_3d, text_to_3d, enhance_mesh)
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        # Base implementation - can be overridden
        if not isinstance(params, dict):
            raise ValueError("Parameters must be a dictionary")
        return True
    
    async def cleanup(self):
        """
        Cleanup resources (close connections, free memory, etc.).
        Override in subclass if needed.
        """
        self.logger.info(f"Cleaning up {self.__class__.__name__}")
        self.is_initialized = False
