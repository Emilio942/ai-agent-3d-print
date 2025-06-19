"""
Enhanced Image Processing API Routes

This module provides advanced image processing endpoints with:
- Multiple processing modes
- Real-time preview generation
- Batch processing capabilities
- Quality assessment and optimization
- Advanced parameter controls
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any, Union
from uuid import uuid4
import asyncio
from datetime import datetime
import io
import base64

import sys
import os
import importlib.util

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.logger import get_logger
from core.parent_agent import ParentAgent
from core.api_schemas import Workflow, WorkflowState

# Import advanced image processor with explicit path resolution
advanced_processor_path = os.path.join(project_root, "agents", "advanced_image_processor.py")
spec = importlib.util.spec_from_file_location("advanced_image_processor", advanced_processor_path)
advanced_processor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(advanced_processor_module)

AdvancedImageProcessor = advanced_processor_module.AdvancedImageProcessor
ProcessingMode = advanced_processor_module.ProcessingMode

from api.main import get_parent_agent, app_state

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v2", tags=["Advanced Image Processing"])

# Pydantic models for API
class ImageProcessingRequest(BaseModel):
    """Advanced image processing request parameters"""
    processing_mode: str = Field(default=ProcessingMode.CONTOUR, 
                                description="Processing mode: contour, depth, surface, multi_object, heightmap")
    edge_detection_method: str = Field(default="canny", 
                                     description="Edge detection: canny, sobel, laplacian, adaptive")
    depth_estimation_method: str = Field(default="gradient", 
                                       description="Depth estimation: gradient, laplacian, sobel")
    extrusion_height: float = Field(default=5.0, ge=0.1, le=50.0, 
                                  description="Extrusion height in mm")
    base_thickness: float = Field(default=1.0, ge=0.1, le=10.0, 
                                description="Base thickness in mm")
    scale_factor: float = Field(default=0.1, ge=0.01, le=1.0, 
                              description="Scale factor (mm per pixel)")
    min_contour_area: int = Field(default=100, ge=10, le=10000, 
                                description="Minimum contour area threshold")
    blur_kernel_size: int = Field(default=5, ge=1, le=15, 
                                description="Gaussian blur kernel size (odd numbers)")
    enable_preview: bool = Field(default=True, 
                               description="Generate preview images")
    enhance_contrast: bool = Field(default=True, 
                                 description="Enhance image contrast")
    auto_levels: bool = Field(default=True, 
                            description="Apply auto-levels adjustment")
    noise_reduction_strength: int = Field(default=1, ge=0, le=2, 
                                        description="Noise reduction: 0=none, 1=light, 2=heavy")
    quality_level: str = Field(default="standard", 
                             description="Processing quality: draft, standard, high, ultra")
    
    @validator('blur_kernel_size')
    def blur_kernel_must_be_odd(cls, v):
        if v % 2 == 0:
            raise ValueError('Blur kernel size must be odd')
        return v

class ImageProcessingPreview(BaseModel):
    """Preview response model"""
    preview_id: str
    original_thumbnail: str
    edge_preview: Optional[str] = None
    processing_preview: Optional[str] = None
    metadata: Dict[str, Any]
    processing_time: str

class ImageProcessingResult(BaseModel):
    """Complete processing result model"""
    job_id: str
    success: bool
    processing_mode: str
    preview_data: Optional[Dict[str, Any]] = None
    geometry_data: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    processing_params: Dict[str, Any]
    created_at: str
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None

class BatchProcessingRequest(BaseModel):
    """Batch processing request"""
    processing_params: ImageProcessingRequest
    auto_combine: bool = Field(default=False, description="Automatically combine results")
    naming_pattern: str = Field(default="batch_{index}", description="Naming pattern for results")

# Global advanced processor instance - will be initialized lazily
advanced_processor = None

def get_advanced_processor():
    """Get or create advanced image processor instance"""
    global advanced_processor
    if advanced_processor is None:
        advanced_processor = AdvancedImageProcessor()
    return advanced_processor

@router.post("/image/preview", response_model=ImageProcessingPreview)
async def generate_image_preview(
    image: UploadFile = File(..., description="Image file for preview"),
    processing_params: str = Form(default="{}", description="JSON processing parameters"),
):
    """
    Generate preview of image processing without full 3D conversion
    Fast preview endpoint for UI feedback
    """
    try:
        start_time = datetime.now()
        
        # Validate image file
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Please upload an image file"
            )
        
        # Parse processing parameters
        import json
        try:
            params_dict = json.loads(processing_params) if processing_params != "{}" else {}
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in processing_params"
            )
        
        # Read image data
        image_data = await image.read()
        
        # Set preview-only parameters
        preview_params = {
            **params_dict,
            'enable_caching': True,
            'preview_resolution': (400, 400),
            'generate_preview_only': True
        }
        
        # Generate preview using advanced processor
        result = await get_advanced_processor().process_image_advanced(
            image_data, image.filename, preview_params
        )
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        preview_id = str(uuid4())
        
        return ImageProcessingPreview(
            preview_id=preview_id,
            original_thumbnail=result['preview_data'].get('original_thumbnail', ''),
            edge_preview=result['preview_data'].get('edge_preview', ''),
            processing_preview=result['preview_data'].get('processing_preview', ''),
            metadata={
                'filename': image.filename,
                'file_size': len(image_data),
                'processing_mode': preview_params.get('processing_mode', 'contour'),
                'dimensions': result['original_image']['dimensions'],
                'processing_time_ms': processing_time
            },
            processing_time=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate image preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )

async def get_parent_agent_optional() -> Optional[ParentAgent]:
    """Get the ParentAgent instance, returning None if not available."""
    return app_state.get("parent_agent")

@router.post("/image/process-advanced", response_model=ImageProcessingResult)
async def process_image_advanced(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Image file to process"),
    processing_mode: str = Form(default=ProcessingMode.CONTOUR),
    edge_detection_method: str = Form(default="canny"),
    depth_estimation_method: str = Form(default="gradient"),
    extrusion_height: float = Form(default=5.0),
    base_thickness: float = Form(default=1.0),
    scale_factor: float = Form(default=0.1),
    min_contour_area: int = Form(default=100),
    blur_kernel_size: int = Form(default=5),
    enable_preview: bool = Form(default=True),
    enhance_contrast: bool = Form(default=True),
    auto_levels: bool = Form(default=True),
    noise_reduction_strength: int = Form(default=1),
    quality_level: str = Form(default="standard"),
    user_id: Optional[str] = Form(None),
    parent_agent: Optional[ParentAgent] = Depends(get_parent_agent_optional)
):
    """
    Advanced image processing with multiple modes and enhanced features
    Full processing endpoint that creates complete 3D models
    """
    try:
        start_time = datetime.now()
        
        # Validate image file
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Please upload an image file"
            )
        
        # Validate parameters
        if processing_mode not in [ProcessingMode.CONTOUR, ProcessingMode.DEPTH, 
                                  ProcessingMode.SURFACE, ProcessingMode.MULTI_OBJECT, 
                                  ProcessingMode.HEIGHTMAP]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid processing mode: {processing_mode}"
            )
        
        if blur_kernel_size % 2 == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Blur kernel size must be odd"
            )
        
        # Create processing parameters
        processing_params = {
            'processing_mode': processing_mode,
            'edge_detection_method': edge_detection_method,
            'depth_estimation_method': depth_estimation_method,
            'default_extrusion_height': extrusion_height,
            'base_thickness': base_thickness,
            'scale_factor': scale_factor,
            'min_contour_area': min_contour_area,
            'blur_kernel_size': blur_kernel_size,
            'enable_preview': enable_preview,
            'enhance_contrast': enhance_contrast,
            'auto_levels': auto_levels,
            'noise_reduction_strength': noise_reduction_strength,
            'quality_level': quality_level,
            'enable_caching': True
        }
        
        # Read image data
        image_data = await image.read()
        
        # Generate job ID
        job_id = str(uuid4())
        
        logger.info(f"Starting advanced image processing: {job_id} for '{image.filename}' with mode '{processing_mode}'")
        
        # Process image using advanced processor
        result = await get_advanced_processor().process_image_advanced(
            image_data, image.filename, processing_params
        )
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create workflow for 3D model generation if successful and parent agent is available
        if result['success'] and parent_agent is not None:
            workflow = Workflow(
                workflow_id=job_id,
                user_request=f"Advanced processing of '{image.filename}' using {processing_mode} mode",
                user_id=user_id or "anonymous",
                state=WorkflowState.PENDING,
                metadata={
                    "input_type": "advanced_image",
                    "image_filename": image.filename,
                    "image_content_type": image.content_type,
                    "processing_mode": processing_mode,
                    "advanced_processing": True,
                    "api_endpoint": "image/process-advanced",
                    **processing_params
                }
            )
            
            # Store workflow and image data
            app_state["active_workflows"][job_id] = workflow
            app_state["websocket_connections"][job_id] = set()
            workflow.metadata["image_data"] = image_data
            workflow.metadata["processing_result"] = result
            
            # Start background processing for 3D model creation
            background_tasks.add_task(process_advanced_image_workflow, job_id, workflow, parent_agent)
        elif result['success']:
            # Log that advanced workflow creation is not available
            logger.info(f"Advanced image processing completed for {job_id}, but 3D workflow creation is not available (agent system not initialized)")
        
        return ImageProcessingResult(
            job_id=job_id,
            success=result['success'],
            processing_mode=processing_mode,
            preview_data=result.get('preview_data'),
            geometry_data=result.get('geometry_data'),
            quality_metrics=result.get('quality_metrics'),
            processing_params=processing_params,
            created_at=start_time.isoformat(),
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Advanced image processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Advanced processing failed: {str(e)}"
        )

@router.post("/image/batch-process")
async def batch_process_images(
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(..., description="Multiple image files to process"),
    batch_params: str = Form(..., description="JSON batch processing parameters"),
    user_id: Optional[str] = Form(None),
    parent_agent: Optional[ParentAgent] = Depends(get_parent_agent_optional)
):
    """
    Process multiple images in batch with same parameters
    Returns batch job ID for tracking all individual jobs
    """
    try:
        # Parse batch parameters
        import json
        try:
            batch_config = json.loads(batch_params)
            batch_request = BatchProcessingRequest(**batch_config)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid batch parameters: {str(e)}"
            )
        
        if len(images) > 20:  # Limit batch size
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size limited to 20 images"
            )
        
        batch_id = str(uuid4())
        job_ids = []
        
        logger.info(f"Starting batch processing: {batch_id} with {len(images)} images")
        
        # Process each image
        for i, image in enumerate(images):
            # Validate image
            if not image.content_type or not image.content_type.startswith('image/'):
                logger.warning(f"Skipping invalid file: {image.filename}")
                continue
            
            # Generate individual job ID
            job_id = str(uuid4())
            job_ids.append(job_id)
            
            # Create individual workflow
            workflow = Workflow(
                workflow_id=job_id,
                user_request=f"Batch processing #{i+1}: {image.filename}",
                user_id=user_id or "anonymous",
                state=WorkflowState.PENDING,
                metadata={
                    "input_type": "batch_image",
                    "batch_id": batch_id,
                    "batch_index": i,
                    "image_filename": image.filename,
                    "image_content_type": image.content_type,
                    "processing_mode": batch_request.processing_params.processing_mode,
                    "api_endpoint": "image/batch-process",
                    **batch_request.processing_params.dict()
                }
            )
            
            # Store workflow
            app_state["active_workflows"][job_id] = workflow
            app_state["websocket_connections"][job_id] = set()
            
            # Store image data
            image_data = await image.read()
            workflow.metadata["image_data"] = image_data
            
            # Start processing
            background_tasks.add_task(process_advanced_image_workflow, job_id, workflow, parent_agent)
        
        return {
            "batch_id": batch_id,
            "job_ids": job_ids,
            "total_images": len(images),
            "processed_images": len(job_ids),
            "message": f"Started batch processing of {len(job_ids)} images",
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}"
        )

@router.get("/image/processing-modes")
async def get_processing_modes():
    """Get available image processing modes and their descriptions"""
    return {
        "modes": {
            ProcessingMode.CONTOUR: {
                "name": "Contour Extraction",
                "description": "Extract object contours and extrude to 3D",
                "best_for": "Line art, logos, simple shapes",
                "parameters": ["edge_detection_method", "min_contour_area", "blur_kernel_size"]
            },
            ProcessingMode.DEPTH: {
                "name": "Depth-based 3D",
                "description": "Generate 3D model from image depth information",
                "best_for": "Photos with depth, relief patterns",
                "parameters": ["depth_estimation_method", "depth_levels", "height_scale_factor"]
            },
            ProcessingMode.HEIGHTMAP: {
                "name": "Height Map",
                "description": "Convert grayscale to height-based terrain",
                "best_for": "Topographic maps, terrain",
                "parameters": ["height_scale_factor", "smoothing_iterations"]
            },
            ProcessingMode.MULTI_OBJECT: {
                "name": "Multi-Object",
                "description": "Separate and process multiple objects independently",
                "best_for": "Multiple separate objects in one image",
                "parameters": ["min_object_size", "object_merge_distance", "max_objects"]
            },
            ProcessingMode.SURFACE: {
                "name": "Surface Reconstruction",
                "description": "Advanced surface reconstruction from image",
                "best_for": "Complex surfaces, 3D-like images",
                "parameters": ["surface_smoothing", "reconstruction_quality"]
            }
        },
        "edge_detection_methods": {
            "canny": "Canny edge detector (best general purpose)",
            "sobel": "Sobel operator (good for gradients)",
            "laplacian": "Laplacian operator (good for details)",
            "adaptive": "Adaptive threshold (good for varying lighting)"
        },
        "depth_estimation_methods": {
            "gradient": "Gradient-based depth estimation",
            "laplacian": "Laplacian-based depth estimation",
            "sobel": "Sobel-based depth estimation"
        },
        "quality_levels": {
            "draft": "Fast processing, basic quality",
            "standard": "Balanced speed and quality",
            "high": "Higher quality, slower processing",
            "ultra": "Maximum quality, slowest processing"
        }
    }

async def process_advanced_image_workflow(job_id: str, workflow: Workflow, parent_agent: Optional[ParentAgent]):
    """Background task to process advanced image workflow"""
    try:
        logger.info(f"Starting advanced image workflow processing for job {job_id}")
        
        # Update workflow state (use RESEARCH_PHASE instead of RUNNING)
        workflow.state = WorkflowState.RESEARCH_PHASE
        workflow.progress_percentage = 10.0
        
        # Get processing result from metadata (already processed in endpoint)
        processing_result = workflow.metadata.get("processing_result")
        
        if not processing_result:
            # If not already processed, process now
            image_data = workflow.metadata["image_data"]
            processing_params = {k: v for k, v in workflow.metadata.items() 
                               if k.startswith(('processing_mode', 'edge_detection', 'depth_estimation', 
                                              'extrusion_height', 'base_thickness', 'scale_factor',
                                              'min_contour_area', 'blur_kernel_size', 'enhance_contrast',
                                              'auto_levels', 'noise_reduction_strength', 'quality_level'))}
            
            processing_result = await get_advanced_processor().process_image_advanced(
                image_data, workflow.metadata["image_filename"], processing_params
            )
        
        workflow.progress_percentage = 30.0
        
        # Continue with existing CAD workflow if contour mode AND parent agent is available
        if workflow.metadata["processing_mode"] == ProcessingMode.CONTOUR and parent_agent is not None:
            # Use existing image workflow processing
            from api.main import execute_image_cad_step, execute_workflow_step
            
            # Execute CAD step
            workflow.state = WorkflowState.CAD_PHASE
            workflow.progress_percentage = 50.0
            cad_result = await execute_image_cad_step(workflow, parent_agent, job_id)
            
            # Execute slicing step
            workflow.state = WorkflowState.SLICING_PHASE
            workflow.progress_percentage = 70.0
            slicing_result = await execute_workflow_step("slicing", "G-code generation", workflow, parent_agent, job_id)
            
            # Execute printing step  
            workflow.state = WorkflowState.PRINTING_PHASE
            workflow.progress_percentage = 90.0
            printing_result = await execute_workflow_step("printing", "3D printing", workflow, parent_agent, job_id)
            
            workflow.state = WorkflowState.COMPLETED
            workflow.progress_percentage = 100.0
            
        else:
            # For other modes or when parent agent is not available, complete with processing result only
            workflow.metadata["output_data"] = processing_result
            workflow.state = WorkflowState.COMPLETED
            workflow.progress_percentage = 100.0
            if parent_agent is None:
                logger.info(f"Advanced image processing completed for {job_id}, but 3D workflow is unavailable (agent system not initialized)")
            
        logger.info(f"Advanced image workflow {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Advanced image workflow {job_id} failed: {e}")
        workflow.state = WorkflowState.FAILED
        workflow.error_message = str(e)
