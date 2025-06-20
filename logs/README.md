# Logs Directory

This directory contains log files generated by the AI Agent 3D Print System.

## Log Structure

### Application Logs
- `ai_3d_print.log` - Main application log
- `ai_3d_print.log.1`, `.2`, etc. - Rotated log files

### Agent-Specific Logs
- `research_agent.log` - Research and NLP operations
- `cad_agent.log` - CAD generation and validation
- `slicer_agent.log` - Slicing operations and G-code generation
- `printer_agent.log` - Printer communication and status

### Special Purpose Logs
- `error.log` - Error-level messages only
- `performance.log` - Performance metrics and timing
- `audit.log` - Security and access events

## Log Configuration

### Format
- **Development**: Human-readable text format
- **Production**: Structured JSON format for log aggregation

### Rotation
- Maximum file size: 10MB
- Keep last 5 rotated files
- Automatic cleanup of old logs

### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational messages
- **WARNING**: Warning messages for attention
- **ERROR**: Error conditions that don't stop operation
- **CRITICAL**: Serious errors that may stop operation

## Log Analysis

Logs can be analyzed using:
- Standard text tools (grep, awk, etc.)
- Log aggregation tools (ELK stack, Fluentd)
- Custom analysis scripts

## Security Note

Logs may contain sensitive information. Ensure proper:
- File permissions (readable only by application user)
- Log rotation and cleanup
- Secure storage in production environments
