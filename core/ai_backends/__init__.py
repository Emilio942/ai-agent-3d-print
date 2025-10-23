"""AI 3D Generation Backends Package"""

from .base_backend import BaseAI3DBackend
from .backend_registry import AI3DBackendRegistry

# Import backends to trigger @register_backend decorators
from . import local_depth_backend
from . import mock_cloud_backend

__all__ = ['BaseAI3DBackend', 'AI3DBackendRegistry']
