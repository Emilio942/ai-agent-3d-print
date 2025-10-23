#!/usr/bin/env python3
"""
AI 3D Backend Manager
AI Agent 3D Print System

Central manager for AI 3D generation backends. Handles backend selection,
configuration, and switching between different AI providers.
"""

import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import trimesh

from core.logger import get_logger
from core.ai_backends.base_backend import BaseAI3DBackend
from core.ai_backends.backend_registry import AI3DBackendRegistry


class AI3DBackendManager:
    """
    Manager for AI 3D generation backends.
    
    Features:
    - Load backends from configuration
    - Switch between backends dynamically
    - Fallback to alternative backends on failure
    - Cache backend instances
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the backend manager.
        
        Args:
            config_path: Path to ai_backends.yaml config file
        """
        self.logger = get_logger(f"{__name__}.AI3DBackendManager")
        
        # Load configuration
        if config_path is None:
            # core/ai_backends/ -> root/config/
            config_path = Path(__file__).parent.parent.parent / "config" / "ai_backends.yaml"
        
        self.config = self._load_config(config_path)
        self.registry = AI3DBackendRegistry()
        
        # Active and fallback backends
        self.active_backend: Optional[BaseAI3DBackend] = None
        self.fallback_backend: Optional[BaseAI3DBackend] = None
        
        # Backend cache
        self._backend_instances: Dict[str, BaseAI3DBackend] = {}
        
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"✅ Loaded AI backend config from: {config_path}")
            return config
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load config: {e}. Using defaults.")
            return {
                'ai_3d_backend': {
                    'active': 'local_depth',
                    'fallback': 'local_depth',
                    'backends': {}
                }
            }
    
    async def initialize(self):
        """
        Initialize the backend manager.
        
        - Auto-discover backends
        - Load active and fallback backends
        - Initialize backends
        """
        try:
            self.logger.info("🔧 Initializing AI 3D Backend Manager...")
            
            # Auto-discover backends
            if self.config.get('auto_discovery', {}).get('enabled', True):
                self.registry.auto_discover_backends()
            
            # Get active backend name from config
            active_name = self.config['ai_3d_backend']['active']
            fallback_name = self.config['ai_3d_backend'].get('fallback', 'local_depth')
            
            # Load active backend
            self.active_backend = await self._get_or_create_backend(active_name)
            
            # Load fallback backend (if different)
            if fallback_name != active_name:
                self.fallback_backend = await self._get_or_create_backend(fallback_name)
            
            self.logger.info(f"✅ Active backend: {active_name}")
            if self.fallback_backend:
                self.logger.info(f"✅ Fallback backend: {fallback_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize: {e}")
            return False
    
    async def _get_or_create_backend(self, backend_name: str) -> BaseAI3DBackend:
        """Get backend instance from cache or create new one"""
        if backend_name in self._backend_instances:
            return self._backend_instances[backend_name]
        
        # Get backend configuration
        backend_configs = self.config['ai_3d_backend'].get('backends', {})
        backend_config = backend_configs.get(backend_name, {}).get('config', {})
        
        # Create backend instance
        backend = self.registry.get_backend(backend_name, config=backend_config)
        
        # Initialize backend
        success = await backend.initialize()
        if not success:
            raise RuntimeError(f"Failed to initialize backend: {backend_name}")
        
        # Cache instance
        self._backend_instances[backend_name] = backend
        
        return backend
    
    async def switch_backend(self, backend_name: str) -> bool:
        """
        Switch to a different backend.
        
        Args:
            backend_name: Name of backend to switch to
            
        Returns:
            True if switch successful
        """
        try:
            self.logger.info(f"🔄 Switching to backend: {backend_name}")
            
            new_backend = await self._get_or_create_backend(backend_name)
            self.active_backend = new_backend
            
            self.logger.info(f"✅ Switched to: {backend_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to switch backend: {e}")
            return False
    
    async def image_to_3d(self, 
                         image_path: str, 
                         params: Optional[Dict[str, Any]] = None,
                         use_fallback_on_error: bool = True) -> Dict[str, Any]:
        """
        Convert image to 3D using active backend.
        
        Args:
            image_path: Path to input image
            params: Generation parameters
            use_fallback_on_error: Try fallback backend if primary fails
            
        Returns:
            Result dict with mesh, metadata, success
        """
        try:
            # Try primary backend
            result = await self.active_backend.image_to_3d(image_path, params)
            
            if result['success']:
                return result
            
            # Try fallback if enabled
            if use_fallback_on_error and self.fallback_backend:
                self.logger.warning("⚠️ Primary backend failed, trying fallback...")
                result = await self.fallback_backend.image_to_3d(image_path, params)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Image to 3D failed: {e}")
            return {
                'mesh': None,
                'metadata': {'error': str(e)},
                'success': False
            }
    
    async def text_to_3d(self, 
                        prompt: str, 
                        params: Optional[Dict[str, Any]] = None,
                        use_fallback_on_error: bool = True) -> Dict[str, Any]:
        """
        Generate 3D from text using active backend.
        
        Args:
            prompt: Text description
            params: Generation parameters
            use_fallback_on_error: Try fallback backend if primary fails
            
        Returns:
            Result dict with mesh, metadata, success
        """
        try:
            # Try primary backend
            result = await self.active_backend.text_to_3d(prompt, params)
            
            if result['success']:
                return result
            
            # Try fallback if enabled
            if use_fallback_on_error and self.fallback_backend:
                self.logger.warning("⚠️ Primary backend failed, trying fallback...")
                result = await self.fallback_backend.text_to_3d(prompt, params)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Text to 3D failed: {e}")
            return {
                'mesh': None,
                'metadata': {'error': str(e)},
                'success': False
            }
    
    async def enhance_mesh(self, 
                          mesh: trimesh.Trimesh, 
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enhance mesh using active backend.
        
        Args:
            mesh: Input mesh
            params: Enhancement parameters
            
        Returns:
            Result dict with enhanced mesh, metadata, success
        """
        try:
            result = await self.active_backend.enhance_mesh(mesh, params)
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Mesh enhancement failed: {e}")
            return {
                'mesh': mesh,  # Return original on failure
                'metadata': {'error': str(e)},
                'success': False
            }
    
    def get_active_backend_info(self) -> Dict[str, Any]:
        """Get info about currently active backend"""
        if self.active_backend:
            return self.active_backend.get_backend_info()
        return {}
    
    def get_active_backend_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of active backend"""
        if self.active_backend:
            return self.active_backend.get_capabilities()
        return {}
    
    def list_available_backends(self) -> Dict[str, Dict[str, Any]]:
        """List all available backends"""
        return self.registry.list_backends()
    
    async def cleanup(self):
        """Cleanup all backend instances"""
        self.logger.info("🧹 Cleaning up backend instances...")
        for backend in self._backend_instances.values():
            await backend.cleanup()
        self._backend_instances.clear()


# Singleton instance
_manager_instance: Optional[AI3DBackendManager] = None


def get_ai_backend_manager(config_path: Optional[str] = None) -> AI3DBackendManager:
    """
    Get singleton instance of AI3DBackendManager.
    
    Args:
        config_path: Path to config file (only used on first call)
        
    Returns:
        AI3DBackendManager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = AI3DBackendManager(config_path)
    return _manager_instance
