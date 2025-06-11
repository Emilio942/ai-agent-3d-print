"""
API endpoints for 3D Print Preview System

This module provides REST API endpoints for the 3D print preview functionality
including STL visualization, G-code analysis, and layer preview generation.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path
import tempfile
import io
import base64
import json
from typing import Optional

from core.print_preview import PrintPreviewManager
from core.logger import get_logger

# Define ValidationError for this module
class ValidationError(Exception):
    """Validation error for preview operations"""
    pass

logger = get_logger(__name__)

# Create router for preview API
router = APIRouter(prefix="/api/preview", tags=["preview"])

# Initialize preview manager
preview_manager = PrintPreviewManager()

# Allowed file extensions
ALLOWED_STL_EXTENSIONS = {'.stl', '.STL'}
ALLOWED_GCODE_EXTENSIONS = {'.gcode', '.g', '.nc', '.GCODE', '.G', '.NC'}

def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file has allowed extension"""
    return Path(filename).suffix in allowed_extensions

@router.get("/capabilities")
async def get_preview_capabilities():
    """Get information about preview system capabilities"""
    try:
        capabilities = preview_manager.get_preview_capabilities()
        
        return {
            'success': True,
            'data': capabilities
        }
        
    except Exception as e:
        logger.error(f"Error getting preview capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stl/upload")
async def upload_stl_preview(file: UploadFile = File(...)):
    """Upload STL file and generate preview"""
    try:
        # Validate file type
        if not allowed_file(file.filename, ALLOWED_STL_EXTENSIONS):
            raise ValidationError("Invalid file type. Only STL files are allowed.")
        
        # Save file temporarily
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / file.filename
        
        # Read and save file content
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        try:
            # Generate preview
            preview_data = preview_manager.generate_stl_preview(temp_file)
            
            # Save preview data
            preview_filename = f"stl_preview_{Path(file.filename).stem}"
            saved_path = preview_manager.save_preview_data(preview_data, preview_filename)
            
            return {
                'success': True,
                'data': {
                    'preview_data': preview_data,
                    'preview_id': preview_filename,
                    'file_info': preview_data.get('file_info', {})
                }
            }
            
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()
        
    except ValidationError as e:
        logger.warning(f"STL upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error processing STL upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/stl/analyze")
async def analyze_stl_data(content: str, filename: Optional[str] = None):
    """Analyze STL data sent as base64 encoded content"""
    try:
        if not content:
            raise ValidationError("No STL content provided")
        
        # Decode base64 content
        try:
            stl_content = base64.b64decode(content)
        except Exception:
            raise ValidationError("Invalid base64 encoded content")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as temp_file:
            temp_file.write(stl_content)
            temp_path = Path(temp_file.name)
        
        try:
            # Generate preview
            preview_data = preview_manager.generate_stl_preview(temp_path)
            
            # Optional: Save preview data if filename provided
            preview_id = None
            if filename:
                preview_filename = f"stl_preview_{Path(filename).stem}"
                preview_manager.save_preview_data(preview_data, preview_filename)
                preview_id = preview_filename
            
            return {
                'success': True,
                'data': {
                    'preview_data': preview_data,
                    'preview_id': preview_id
                }
            }
            
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
        
    except ValidationError as e:
        logger.warning(f"STL analysis validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error analyzing STL data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/gcode/upload")
async def upload_gcode_preview(file: UploadFile = File(...)):
    """Upload G-code file and generate layer preview"""
    try:
        # Validate file type
        if not allowed_file(file.filename, ALLOWED_GCODE_EXTENSIONS):
            raise ValidationError("Invalid file type. Only G-code files are allowed.")
        
        # Read G-code content
        content = await file.read()
        gcode_content = content.decode('utf-8')
        
        # Generate preview
        preview_data = preview_manager.generate_gcode_preview(gcode_content)
        
        # Save preview data
        preview_filename = f"gcode_preview_{Path(file.filename).stem}"
        saved_path = preview_manager.save_preview_data(preview_data, preview_filename)
        
        return {
            'success': True,
            'data': {
                'preview_data': preview_data,
                'preview_id': preview_filename,
                'file_info': {
                    'filename': file.filename,
                    'size': len(gcode_content)
                }
            }
        }
        
    except ValidationError as e:
        logger.warning(f"G-code upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error processing G-code upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/gcode/analyze")
async def analyze_gcode_content(content: str, filename: Optional[str] = None):
    """Analyze G-code content sent as text"""
    try:
        if not content:
            raise ValidationError("No G-code content provided")
        
        # Generate preview
        preview_data = preview_manager.generate_gcode_preview(content)
        
        # Optional: Save preview data if filename provided
        preview_id = None
        if filename:
            preview_filename = f"gcode_preview_{Path(filename).stem}"
            preview_manager.save_preview_data(preview_data, preview_filename)
            preview_id = preview_filename
        
        return {
            'success': True,
            'data': {
                'preview_data': preview_data,
                'preview_id': preview_id
            }
        }
        
    except ValidationError as e:
        logger.warning(f"G-code analysis validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error analyzing G-code content: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/preview/{preview_id}")
async def get_preview_data(preview_id: str):
    """Get previously saved preview data"""
    try:
        # Load preview data
        preview_data = preview_manager.load_preview_data(preview_id)
        
        return {
            'success': True,
            'data': preview_data
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Preview not found")
        
    except Exception as e:
        logger.error(f"Error loading preview data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/preview/{preview_id}/layer/{layer_number}")
async def get_layer_info(preview_id: str, layer_number: int):
    """Get detailed information about a specific layer"""
    try:
        # Load preview data
        preview_data = preview_manager.load_preview_data(preview_id)
        
        # Check if it's a G-code preview with layer data
        if 'layer_preview' not in preview_data:
            raise ValidationError("Preview does not contain layer data")
        
        layers = preview_data['layer_preview']['layers']
        
        # Find the specified layer
        layer_info = None
        for layer in layers:
            if layer['layer_number'] == layer_number:
                layer_info = layer
                break
        
        if not layer_info:
            raise ValidationError(f"Layer {layer_number} not found")
        
        return {
            'success': True,
            'data': layer_info
        }
        
    except ValidationError as e:
        logger.warning(f"Layer info validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Preview not found")
        
    except Exception as e:
        logger.error(f"Error getting layer info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/preview/{preview_id}/analysis")
async def get_print_analysis(preview_id: str):
    """Get print analysis data for a preview"""
    try:
        # Load preview data
        preview_data = preview_manager.load_preview_data(preview_id)
        
        # Extract analysis data
        analysis_data = {}
        
        if 'print_analysis' in preview_data:
            analysis_data = preview_data['print_analysis']
        elif 'statistics' in preview_data:
            # STL preview statistics
            analysis_data = preview_data['statistics']
        
        return {
            'success': True,
            'data': analysis_data
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Preview not found")
        
    except Exception as e:
        logger.error(f"Error getting print analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/preview/{preview_id}/export/{format}")
async def export_preview(preview_id: str, format: str):
    """Export preview data in various formats"""
    try:
        # Load preview data
        preview_data = preview_manager.load_preview_data(preview_id)
        
        if format == 'json':
            # Return JSON data as file download
            json_content = json.dumps(preview_data, indent=2)
            
            return StreamingResponse(
                io.BytesIO(json_content.encode()),
                media_type='application/json',
                headers={'Content-Disposition': f'attachment; filename="{preview_id}.json"'}
            )
            
        elif format == 'summary':
            # Generate summary report
            summary = generate_preview_summary(preview_data)
            
            return {
                'success': True,
                'data': summary
            }
            
        else:
            raise ValidationError(f"Unsupported export format: {format}")
        
    except ValidationError as e:
        logger.warning(f"Export validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Preview not found")
        
    except Exception as e:
        logger.error(f"Error exporting preview: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def generate_preview_summary(preview_data: dict) -> dict:
    """Generate a human-readable summary of preview data"""
    summary = {
        'type': 'unknown',
        'key_metrics': {},
        'recommendations': []
    }
    
    # Detect preview type and extract key information
    if 'geometry' in preview_data:
        # STL preview
        summary['type'] = 'STL'
        stats = preview_data.get('statistics', {})
        
        summary['key_metrics'] = {
            'triangle_count': stats.get('triangle_count', 0),
            'vertex_count': stats.get('vertex_count', 0),
            'dimensions': stats.get('bounds', {})
        }
        
        # Add recommendations
        triangle_count = stats.get('triangle_count', 0)
        if triangle_count > 100000:
            summary['recommendations'].append(
                "High triangle count detected. Consider simplifying the model for faster processing."
            )
        
    elif 'layer_preview' in preview_data:
        # G-code preview
        summary['type'] = 'G-code'
        analysis = preview_data.get('print_analysis', {})
        
        summary['key_metrics'] = {
            'total_layers': analysis.get('total_layers', 0),
            'estimated_time': analysis.get('estimated_print_time', 0),
            'material_usage': analysis.get('material_usage', {}),
            'quality_score': analysis.get('print_quality_score', 0)
        }
        
        # Add recommendations based on analysis
        quality_score = analysis.get('print_quality_score', 0)
        if quality_score < 70:
            summary['recommendations'].append(
                "Print quality score is below optimal. Check settings and potential issues."
            )
        
        estimated_time = analysis.get('estimated_print_time', 0)
        if estimated_time > 24:  # More than 24 hours
            summary['recommendations'].append(
                "Very long print time detected. Consider optimizing settings or splitting the print."
            )
    
    return summary

@router.get("/health")
async def health_check():
    """Health check endpoint for preview service"""
    try:
        # Test basic functionality
        capabilities = preview_manager.get_preview_capabilities()
        
        return {
            'success': True,
            'status': 'healthy',
            'capabilities': capabilities
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
