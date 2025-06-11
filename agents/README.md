# Agents Module

This directory contains all specialized agents for the AI Agent 3D Print System.

## Agent Types

### Parent Agent (`parent_agent.py`)
- Orchestrates the complete workflow
- Manages agent coordination
- Handles rollback on failures
- Provides progress tracking

### Research Agent (`research_agent.py`)
- NLP intent recognition
- Web research capabilities
- Design specification generation
- Content summarization

### CAD Agent (`cad_agent.py`)
- 3D primitive generation
- Boolean operations
- STL export with quality control
- Geometry validation

### Slicer Agent (`slicer_agent.py`)
- Integration with PrusaSlicer/Cura
- Profile management
- G-code generation
- Print settings optimization

### Printer Agent (`printer_agent.py`)
- Serial communication with 3D printers
- G-code streaming
- Progress monitoring
- Emergency stop functionality

## Agent Communication

All agents follow the BaseAgent interface and communicate through:
- Standardized task requests/responses
- Priority-based job queue
- Event-driven progress updates
- Centralized error handling
