# Core Module

This directory contains base classes and common functions used throughout the AI Agent 3D Print System.

## Structure

- `base_agent.py` - Abstract base class for all agents
- `logger.py` - Centralized logging configuration
- `exceptions.py` - Custom exception classes
- `schemas.py` - Pydantic models for data validation
- `job_queue.py` - Priority-based job queue implementation
- `config_manager.py` - Configuration management utilities
- `utils.py` - Common utility functions

## Key Components

### BaseAgent
Abstract base class that provides:
- Standard task execution interface
- Error handling and retry mechanisms
- Input validation
- Logging integration

### Job Queue
Priority-based message queue with:
- Job prioritization (LOW, NORMAL, HIGH, CRITICAL)
- Status tracking (PENDING, RUNNING, COMPLETED, FAILED)
- Optional Redis backend for persistence

### Schemas
Pydantic models for:
- Task requests and responses
- Agent communication protocols
- Configuration validation
