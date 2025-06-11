"""
Centralized Logging System for AI Agent 3D Print System

This module provides structured logging capabilities with JSON formatting,
separate log files per agent, and configurable log levels.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pythonjsonlogger import jsonlogger


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds timestamp and additional context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        if not log_record.get('timestamp'):
            from datetime import timezone
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        
        # Add module and function information
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add process and thread information
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread


class AgentLogger:
    """Logger class for individual agents with structured JSON logging."""
    
    def __init__(self, agent_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize agent logger.
        
        Args:
            agent_name: Name of the agent (e.g., 'research_agent', 'cad_agent')
            config: Logging configuration dictionary
        """
        self.agent_name = agent_name
        self.config = config or self._load_config()
        self.logger = self._setup_logger()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load logging configuration from settings.yaml."""
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f)
                return full_config.get('logging', {})
        
        # Default configuration if file doesn't exist
        return {
            'level': 'INFO',
            'format': 'json',
            'file_enabled': True,
            'file_path': './logs',
            'file_max_size': '10MB',
            'file_backup_count': 5,
            'console_enabled': True,
            'structured': True
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Set up and configure the logger."""
        logger = logging.getLogger(f"ai_3d_print.{self.agent_name}")
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Set log level
        log_level = getattr(logging, self.config.get('level', 'INFO').upper())
        logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        log_dir = Path(self.config.get('file_path', './logs'))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure log_dir is actually a directory, not a file
        if log_dir.is_file():
            log_dir.unlink()
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up formatters
        if self.config.get('format') == 'json':
            json_formatter = JSONFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s %(module)s %(function)s %(line)s'
            )
            text_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(module)s:%(funcName)s:%(lineno)d]'
            )
        else:
            # Text-only formatting
            text_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(module)s:%(funcName)s:%(lineno)d]'
            )
            json_formatter = text_formatter
        
        # Console handler
        if self.config.get('console_enabled', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(text_formatter)  # Use text format for console
            logger.addHandler(console_handler)
        
        # File handler for agent-specific logs
        if self.config.get('file_enabled', True):
            log_file = log_dir / f"{self.agent_name}.log"
            
            # Parse file size (e.g., "10MB" -> 10485760 bytes)
            max_size_str = self.config.get('file_max_size', '10MB')
            max_size = self._parse_file_size(max_size_str)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_size,
                backupCount=self.config.get('file_backup_count', 5),
                encoding='utf-8'
            )
            file_handler.setFormatter(json_formatter)
            logger.addHandler(file_handler)
        
        # Main application log file
        if self.config.get('file_enabled', True):
            main_log_file = log_dir / "ai_3d_print.log"
            main_handler = logging.handlers.RotatingFileHandler(
                main_log_file,
                maxBytes=self._parse_file_size(self.config.get('file_max_size', '10MB')),
                backupCount=self.config.get('file_backup_count', 5),
                encoding='utf-8'
            )
            main_handler.setFormatter(json_formatter)
            logger.addHandler(main_handler)
        
        # Error-only log file
        if self.config.get('file_enabled', True):
            error_log_file = log_dir / "error.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=self._parse_file_size(self.config.get('file_max_size', '10MB')),
                backupCount=self.config.get('file_backup_count', 5),
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(json_formatter)
            logger.addHandler(error_handler)
        
        return logger
    
    def _parse_file_size(self, size_str: str) -> int:
        """Parse file size string (e.g., '10MB') to bytes."""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        else:
            # Assume bytes
            return int(size_str)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional extra data."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional extra data."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional extra data."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with optional extra data."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with optional extra data."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def _log_with_context(self, level: int, message: str, **kwargs) -> None:
        """Log message with additional context data."""
        extra_data = {
            'agent': self.agent_name,
            **kwargs
        }
        
        # If structured logging is enabled, add extra data to the log record
        if self.config.get('structured', True):
            self.logger.log(level, message, extra=extra_data)
        else:
            # Format extra data as string for non-structured logging
            if kwargs:
                extra_str = " | " + " | ".join([f"{k}={v}" for k, v in kwargs.items()])
                message = message + extra_str
            self.logger.log(level, message)


class LoggerManager:
    """Manager class for creating and managing agent loggers."""
    
    _loggers: Dict[str, AgentLogger] = {}
    _config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_logger(cls, agent_name: str) -> AgentLogger:
        """
        Get or create a logger for the specified agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            AgentLogger instance
        """
        if agent_name not in cls._loggers:
            cls._loggers[agent_name] = AgentLogger(agent_name, cls._config)
        
        return cls._loggers[agent_name]
    
    @classmethod
    def configure(cls, config: Dict[str, Any]) -> None:
        """
        Configure logging for all agents.
        
        Args:
            config: Logging configuration dictionary
        """
        cls._config = config
        
        # Reconfigure existing loggers
        for agent_name in cls._loggers:
            cls._loggers[agent_name] = AgentLogger(agent_name, config)
    
    @classmethod
    def get_agent_names(cls) -> list[str]:
        """Get list of all registered agent names."""
        return list(cls._loggers.keys())


def get_logger(agent_name: str) -> AgentLogger:
    """
    Convenience function to get a logger for an agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        AgentLogger instance
    """
    return LoggerManager.get_logger(agent_name)


def configure_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Configure logging system with optional configuration override.
    
    Args:
        config: Optional logging configuration dictionary
    """
    if config:
        LoggerManager.configure(config)


# Common logger instances for different components
def get_research_logger() -> AgentLogger:
    """Get logger for research agent."""
    return get_logger("research_agent")


def get_cad_logger() -> AgentLogger:
    """Get logger for CAD agent."""
    return get_logger("cad_agent")


def get_slicer_logger() -> AgentLogger:
    """Get logger for slicer agent."""
    return get_logger("slicer_agent")


def get_printer_logger() -> AgentLogger:
    """Get logger for printer agent."""
    return get_logger("printer_agent")


def get_parent_logger() -> AgentLogger:
    """Get logger for parent agent."""
    return get_logger("parent_agent")


def get_api_logger() -> AgentLogger:
    """Get logger for API components."""
    return get_logger("api")


if __name__ == "__main__":
    # Example usage and testing
    print("Testing AI Agent 3D Print Logging System")
    
    # Test different loggers
    research_logger = get_research_logger()
    cad_logger = get_cad_logger()
    
    # Test different log levels with context
    research_logger.info("Starting intent recognition", 
                        user_input="Create a 2cm cube", 
                        confidence=0.95)
    
    research_logger.warning("Low confidence in intent extraction",
                           confidence=0.45,
                           fallback_method="regex_patterns")
    
    cad_logger.debug("Creating primitive geometry",
                     shape="cube",
                     dimensions={"x": 20, "y": 20, "z": 20})
    
    cad_logger.error("CAD operation failed",
                     operation="boolean_union",
                     error_code="GEOMETRY_INVALID")
    
    print("Logging test completed. Check logs/ directory for output files.")
