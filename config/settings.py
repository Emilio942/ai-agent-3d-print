"""
Configuration Management for AI Agent 3D Print System

This module provides configuration loading and management functionality.
It loads settings from the YAML configuration file and provides
type-safe access to configuration values.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from settings.yaml file with environment-specific overrides.
    
    Args:
        config_path: Optional path to config file. If not provided,
                    uses the default settings.yaml path.
    
    Returns:
        Dictionary containing all configuration settings with environment overrides
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    if config_path is None:
        # Default path relative to this file
        config_path = Path(__file__).parent / "settings.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        # Load base configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Load environment-specific overrides
        environment = os.getenv('APP_ENVIRONMENT', config.get('app', {}).get('environment', 'development'))
        env_config_path = Path(__file__).parent / f"{environment}.yaml"
        
        if env_config_path.exists():
            with open(env_config_path, 'r', encoding='utf-8') as f:
                env_config = yaml.safe_load(f)
                if env_config:
                    config = _deep_merge_configs(config, env_config)
        
        # Override with environment variables if they exist
        config = _apply_environment_overrides(config)
        
        return config
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file {config_path}: {e}")


def _deep_merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two configuration dictionaries.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def _apply_environment_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply environment variable overrides to configuration.
    
    This function checks for common environment variables and
    overrides the corresponding configuration values.
    """
    # API configuration overrides
    if os.getenv('API_HOST'):
        config.setdefault('api', {})['host'] = os.getenv('API_HOST')
    
    if os.getenv('API_PORT'):
        config.setdefault('api', {})['port'] = int(os.getenv('API_PORT'))
    
    # App configuration overrides
    if os.getenv('APP_DEBUG'):
        config.setdefault('app', {})['debug'] = os.getenv('APP_DEBUG').lower() == 'true'
    
    if os.getenv('APP_ENVIRONMENT'):
        config.setdefault('app', {})['environment'] = os.getenv('APP_ENVIRONMENT')
    
    # Database configuration overrides
    if os.getenv('DATABASE_URL'):
        config.setdefault('database', {})['url'] = os.getenv('DATABASE_URL')
    
    # Redis configuration overrides
    if os.getenv('REDIS_URL'):
        config.setdefault('job_queue', {})['redis_url'] = os.getenv('REDIS_URL')
    
    # Printer configuration overrides
    if os.getenv('PRINTER_PORT'):
        config.setdefault('agents', {}).setdefault('printer', {}).setdefault('serial', {})['port'] = os.getenv('PRINTER_PORT')
    
    # Slicer configuration overrides
    if os.getenv('SLICER_PATH'):
        config.setdefault('agents', {}).setdefault('slicer', {}).setdefault('prusaslicer', {})['executable_path'] = os.getenv('SLICER_PATH')
    
    return config


def get_api_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get API-specific configuration.
    
    Args:
        config: Optional pre-loaded config. If not provided, loads from file.
        
    Returns:
        Dictionary containing API configuration
    """
    if config is None:
        config = load_config()
    
    return config.get('api', {
        'host': 'localhost',
        'port': 8000,
        'workers': 1,
        'reload': True,
        'cors_origins': ['http://localhost:3000', 'http://localhost:8080'],
        'cors_methods': ['GET', 'POST', 'PUT', 'DELETE']
    })


def get_websocket_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get WebSocket-specific configuration.
    
    Args:
        config: Optional pre-loaded config. If not provided, loads from file.
        
    Returns:
        Dictionary containing WebSocket configuration
    """
    if config is None:
        config = load_config()
    
    return config.get('websocket', {
        'heartbeat_interval': 30,
        'max_connections': 100,
        'message_size_limit': 1048576
    })


def get_agent_config(agent_name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get configuration for a specific agent.
    
    Args:
        agent_name: Name of the agent (research, cad, slicer, printer)
        config: Optional pre-loaded config. If not provided, loads from file.
        
    Returns:
        Dictionary containing agent-specific configuration
    """
    if config is None:
        config = load_config()
    
    agents_config = config.get('agents', {})
    return agents_config.get(agent_name, {})


def is_production() -> bool:
    """
    Check if the system is running in production mode.
    
    Returns:
        True if in production mode, False otherwise
    """
    config = load_config()
    environment = config.get('app', {}).get('environment', 'development')
    return environment == 'production'


def is_development() -> bool:
    """
    Check if the system is running in development mode.
    
    Returns:
        True if in development mode, False otherwise
    """
    return not is_production()
