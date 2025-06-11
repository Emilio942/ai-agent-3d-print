# Configuration Directory

This directory contains all configuration files for the AI Agent 3D Print System.

## Files

### `settings.yaml`
Main configuration file containing:
- Application settings
- Agent configurations
- Database and queue settings
- Security and monitoring options
- Development vs production settings

### Slicer Profiles (Future)
- `slicer_profiles/` - Directory for printer and material profiles
- Pre-configured settings for different printer types
- Material-specific parameters (PLA, PETG, ABS, etc.)

### Environment Configuration
- Support for environment-specific overrides
- Environment variables mapping
- Production security settings

## Configuration Management

The system supports:
- YAML-based configuration
- Environment variable overrides
- Runtime configuration validation
- Hot-reload for development settings

## Usage

Configuration is loaded through the `core.config_manager` module, which provides:
- Type-safe configuration access
- Validation against schemas
- Environment-specific defaults
- Configuration change notifications
