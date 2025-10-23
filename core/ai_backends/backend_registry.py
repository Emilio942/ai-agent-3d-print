#!/usr/bin/env python3
"""
AI 3D Backend Registry System
AI Agent 3D Print System

This module manages registration and selection of different AI 3D generation backends.
Supports dynamic loading and switching between backends via configuration.
"""

from typing import Dict, Type, Optional, Any
from pathlib import Path
import importlib
import inspect

from core.logger import get_logger
from .base_backend import BaseAI3DBackend


class AI3DBackendRegistry:
    """
    Registry for managing AI 3D generation backends.
    
    Allows registering, discovering, and instantiating different AI backends
    for 3D model generation from images, text, or mesh enhancement.
    """
    
    _instance = None
    _backends: Dict[str, Type[BaseAI3DBackend]] = {}
    
    def __new__(cls):
        """Singleton pattern to ensure single registry instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logger = get_logger(f"{__name__}.AI3DBackendRegistry")
        return cls._instance
    
    @classmethod
    def register(cls, name: str, backend_class: Type[BaseAI3DBackend]):
        """
        Register an AI backend.
        
        Args:
            name: Unique identifier for the backend (e.g., 'local_depth', 'openai', 'replicate')
            backend_class: Backend class (must inherit from BaseAI3DBackend)
        """
        if not issubclass(backend_class, BaseAI3DBackend):
            raise TypeError(f"Backend {name} must inherit from BaseAI3DBackend")
        
        cls._backends[name] = backend_class
        logger = get_logger(f"{__name__}.AI3DBackendRegistry")
        logger.info(f"✅ Registered AI backend: {name} ({backend_class.__name__})")
    
    @classmethod
    def unregister(cls, name: str):
        """Unregister an AI backend"""
        if name in cls._backends:
            del cls._backends[name]
            logger = get_logger(f"{__name__}.AI3DBackendRegistry")
            logger.info(f"❌ Unregistered AI backend: {name}")
    
    @classmethod
    def get_backend(cls, name: str, config: Optional[Dict[str, Any]] = None) -> BaseAI3DBackend:
        """
        Get an instance of a registered backend.
        
        Args:
            name: Backend identifier
            config: Backend-specific configuration
            
        Returns:
            Instantiated backend object
            
        Raises:
            KeyError: If backend not found
        """
        if name not in cls._backends:
            available = ", ".join(cls._backends.keys())
            raise KeyError(
                f"Backend '{name}' not found. Available backends: {available}"
            )
        
        backend_class = cls._backends[name]
        return backend_class(config=config)
    
    @classmethod
    def list_backends(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all registered backends with their info.
        
        Returns:
            Dict mapping backend names to their info
        """
        backends_info = {}
        for name, backend_class in cls._backends.items():
            # Try to get info from class (if it has a static method)
            backends_info[name] = {
                "class_name": backend_class.__name__,
                "module": backend_class.__module__,
                "docstring": backend_class.__doc__ or "No description"
            }
        return backends_info
    
    @classmethod
    def auto_discover_backends(cls, backends_dir: Optional[Path] = None):
        """
        Automatically discover and register backends from a directory.
        
        Args:
            backends_dir: Directory to search for backends (defaults to ./ai_backends/)
        """
        logger = get_logger(f"{__name__}.AI3DBackendRegistry")
        
        if backends_dir is None:
            backends_dir = Path(__file__).parent
        
        logger.info(f"🔍 Auto-discovering backends in: {backends_dir}")
        
        # Find all Python files in the directory
        for py_file in backends_dir.glob("*_backend.py"):
            if py_file.name.startswith("base_"):
                continue  # Skip base class
            
            try:
                # Import the module
                module_name = f"core.ai_backends.{py_file.stem}"
                module = importlib.import_module(module_name)
                
                # Find all BaseAI3DBackend subclasses in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseAI3DBackend) and obj is not BaseAI3DBackend:
                        # Auto-register using snake_case version of class name
                        backend_name = cls._class_name_to_backend_name(name)
                        cls.register(backend_name, obj)
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to load backend from {py_file}: {e}")
    
    @staticmethod
    def _class_name_to_backend_name(class_name: str) -> str:
        """Convert ClassName to backend_name format"""
        # Remove 'Backend' suffix if present
        if class_name.endswith('Backend'):
            class_name = class_name[:-7]
        
        # Convert camelCase to snake_case
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        return name


# Convenience function for registration decorator
def register_backend(name: str):
    """
    Decorator to register a backend class.
    
    Usage:
        @register_backend('my_ai')
        class MyAIBackend(BaseAI3DBackend):
            ...
    """
    def decorator(cls):
        AI3DBackendRegistry.register(name, cls)
        return cls
    return decorator
