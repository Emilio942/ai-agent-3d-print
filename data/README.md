# Data Directory

This directory contains temporary and output files for the AI Agent 3D Print System.

## Directory Structure

### `temp/`
Temporary files during processing:
- Intermediate CAD files
- Temporary STL exports
- Processing status files
- Cache files

### `output/`
Final output files:
- Generated STL files
- Sliced G-code files
- Print reports
- Quality control reports

## File Management

### Automatic Cleanup
- Temporary files older than 7 days are automatically removed
- Maximum storage limit: 1GB
- Configurable retention policies per file type

### File Naming Convention
```
{timestamp}_{job_id}_{file_type}.{extension}

Examples:
20250610_143022_abc123_model.stl
20250610_143022_abc123_gcode.gcode
20250610_143022_abc123_report.json
```

### Supported File Types

#### Input Files
- `.txt` - Text descriptions for 3D objects

#### Intermediate Files
- `.step` - CAD interchange format
- `.iges` - Alternative CAD format
- `.obj` - 3D mesh format

#### Output Files
- `.stl` - 3D printing format
- `.gcode` - Printer instruction format
- `.json` - Reports and metadata

## Storage Considerations

### Development
- Local filesystem storage
- Regular cleanup to prevent disk overflow
- Backup not required for temporary data

### Production
- Consider cloud storage for output files
- Regular backup of important generated models
- Monitor disk usage and implement alerts

## Security

- Files are created with restricted permissions
- No executable permissions on generated files
- Input validation to prevent path traversal attacks
- File type validation to prevent malicious uploads
