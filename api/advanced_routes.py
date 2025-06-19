"""
API endpoints for AI-Enhanced Design and Historical Data Systems

This module provides REST API endpoints for AI-enhanced design analysis,
optimization suggestions, historical data tracking, and learning insights.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import uuid
from datetime import datetime

from core.ai_design_enhancer import AIDesignEnhancer, DesignAnalysisResult
from core.historical_data_system import (
    HistoricalDataSystem, PrintJob, PrintStatus, FailureType
)
from core.print_preview import PrintPreviewManager
from core.logger import get_logger
from core.advanced_features import BatchProcessor, PrintHistory, AdvancedConfigManager, DEFAULT_PROFILES
from core.ai_image_to_3d import AIImageTo3DConverter
from core.voice_control import VoiceControlManager, VoiceCommand
from core.analytics_dashboard import AnalyticsDashboard, MetricType
from core.template_library import TemplateLibrary, TemplateCategory, PrintDifficulty

logger = get_logger(__name__)

# Create router for advanced features API
router = APIRouter(prefix="/api/advanced", tags=["advanced"])

# Initialize systems
ai_enhancer = AIDesignEnhancer()
historical_system = HistoricalDataSystem()
preview_manager = PrintPreviewManager()

# Initialize additional advanced features
print_history = PrintHistory()
config_manager = AdvancedConfigManager()
# BatchProcessor will be initialized when needed with orchestrator

# Initialize AI image-to-3D converter
ai_converter = AIImageTo3DConverter()

# Initialize new systems
voice_control = VoiceControlManager()
analytics_dashboard = AnalyticsDashboard()
template_library = TemplateLibrary()

# Initialize default profiles
for profile_name, profile_config in DEFAULT_PROFILES.items():
    config_manager.create_profile(profile_name, profile_config)

# Pydantic models for request/response
class PrintJobRequest(BaseModel):
    job_id: str
    user_id: str
    design_name: str
    design_file_path: Optional[str] = None
    material_type: str
    layer_height: float = Field(gt=0, le=1.0)
    infill_percentage: int = Field(ge=0, le=100)
    print_speed: int = Field(gt=0, le=300)
    nozzle_temperature: int = Field(ge=150, le=300)
    bed_temperature: int = Field(ge=0, le=150)
    support_enabled: bool = False
    estimated_duration: float = Field(gt=0)

class PrintResultRequest(BaseModel):
    job_id: str
    status: str  # completed, failed, cancelled
    success_rating: Optional[int] = Field(None, ge=1, le=10)
    failure_type: Optional[str] = None
    failure_description: Optional[str] = None
    surface_quality: Optional[int] = Field(None, ge=1, le=10)
    dimensional_accuracy: Optional[int] = Field(None, ge=1, le=10)
    structural_integrity: Optional[int] = Field(None, ge=1, le=10)
    filament_used: Optional[float] = Field(None, ge=0)
    energy_consumed: Optional[float] = Field(None, ge=0)
    user_notes: Optional[str] = None
    would_print_again: Optional[bool] = None
    actual_duration: Optional[float] = Field(None, gt=0)

class OptimizationFeedbackRequest(BaseModel):
    design_id: str
    suggestion_id: str
    implemented: bool
    feedback_score: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None

class BatchRequest(BaseModel):
    requests: List[str]
    settings: Optional[Dict[str, Any]] = None

class BatchResponse(BaseModel):
    batch_id: str
    status: str
    total_requests: int
    completed: int
    failed: int
    success_rate: float

class TemplateRequest(BaseModel):
    category: str
    name: str
    customizations: Optional[Dict[str, Any]] = None

class ProfileRequest(BaseModel):
    name: str
    config: Dict[str, Any]

class HistoryStats(BaseModel):
    total_prints: int
    success_rate: float
    recent_prints: List[Dict[str, Any]]
    popular_requests: List[Dict[str, Any]]

# Voice Control Endpoints
class VoiceCommandRequest(BaseModel):
    audio_data: Optional[str] = None  # Base64 encoded audio
    text_command: Optional[str] = None  # Text version of command
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

# Analytics Dashboard Endpoints
class AnalyticsQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metric_names: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None

# Template Library Endpoints
class TemplateSearchRequest(BaseModel):
    category: Optional[str] = None
    difficulty: Optional[str] = None
    search_term: Optional[str] = None
    tags: Optional[List[str]] = None

class TemplateCustomizationRequest(BaseModel):
    template_id: str
    parameters: Dict[str, Any]
    target_format: str = Field(default="stl", pattern="^(stl|obj|ply)$")

# Global batch processor (will be initialized when needed)
batch_processor: Optional[BatchProcessor] = None

def get_batch_processor():
    """Get or create batch processor instance."""
    global batch_processor
    if batch_processor is None:
        from main import WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator()
        batch_processor = BatchProcessor(orchestrator)
    return batch_processor

# AI Design Enhancement Endpoints
@router.post("/design/analyze")
async def analyze_design(file: UploadFile = File(...), design_id: Optional[str] = None):
    """Analyze design file with AI enhancement system"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.stl'):
            raise HTTPException(status_code=400, detail="Only STL files are supported")
        
        # Generate design ID if not provided
        if not design_id:
            design_id = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save file temporarily
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / file.filename
        
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        try:
            # Parse STL geometry
            from core.print_preview import STLParser
            parser = STLParser()
            geometry_data = parser.parse_stl_file(temp_file)
            
            # Perform AI analysis
            analysis_result = ai_enhancer.analyze_design(design_id, geometry_data)
            
            return {
                'success': True,
                'data': {
                    'design_id': design_id,
                    'analysis_result': {
                        'metrics': analysis_result.metrics.__dict__,
                        'suggestions': [s.__dict__ for s in analysis_result.suggestions],
                        'failure_predictions': analysis_result.failure_predictions,
                        'recommended_materials': analysis_result.recommended_materials,
                        'recommended_settings': analysis_result.recommended_settings,
                        'overall_score': analysis_result.overall_score,
                        'improvement_potential': analysis_result.improvement_potential
                    }
                }
            }
            
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()
        
    except Exception as e:
        logger.error(f"Error analyzing design: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/design/analysis/{design_id}")
async def get_design_analysis(design_id: str):
    """Get existing design analysis"""
    try:
        history = ai_enhancer.get_analysis_history(design_id)
        
        if not history:
            raise HTTPException(status_code=404, detail="Design analysis not found")
        
        return {
            'success': True,
            'data': history[0]  # Most recent analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving design analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/design/feedback")
async def submit_optimization_feedback(feedback: OptimizationFeedbackRequest):
    """Submit feedback on optimization suggestions"""
    try:
        ai_enhancer.update_suggestion_feedback(
            design_id=feedback.design_id,
            suggestion_id=feedback.suggestion_id,
            implemented=feedback.implemented,
            feedback_score=feedback.feedback_score,
            notes=feedback.notes
        )
        
        return {
            'success': True,
            'message': 'Feedback submitted successfully'
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/design/insights")
async def get_design_insights():
    """Get insights from all analyzed designs"""
    try:
        insights = ai_enhancer.get_design_insights()
        
        return {
            'success': True,
            'data': insights
        }
        
    except Exception as e:
        logger.error(f"Error getting design insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/design/retrain")
async def retrain_ai_models():
    """Retrain AI models with accumulated feedback"""
    try:
        ai_enhancer.retrain_models()
        
        return {
            'success': True,
            'message': 'AI models retrained successfully'
        }
        
    except Exception as e:
        logger.error(f"Error retraining models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Historical Data System Endpoints
@router.post("/history/job/start")
async def start_print_job(job: PrintJobRequest):
    """Record the start of a new print job"""
    try:
        print_job = PrintJob(
            job_id=job.job_id,
            user_id=job.user_id,
            design_name=job.design_name,
            design_file_path=job.design_file_path,
            material_type=job.material_type,
            layer_height=job.layer_height,
            infill_percentage=job.infill_percentage,
            print_speed=job.print_speed,
            nozzle_temperature=job.nozzle_temperature,
            bed_temperature=job.bed_temperature,
            support_enabled=job.support_enabled,
            start_time=datetime.now(),
            end_time=None,
            estimated_duration=job.estimated_duration,
            actual_duration=None,
            status=PrintStatus.IN_PROGRESS,
            success_rating=None,
            failure_type=None,
            failure_description=None,
            surface_quality=None,
            dimensional_accuracy=None,
            structural_integrity=None,
            filament_used=None,
            estimated_filament=None,
            energy_consumed=None,
            user_notes=None,
            would_print_again=None,
            design_complexity=None,
            printability_score=None,
            ai_suggestions_count=None,
            ai_suggestions_implemented=None
        )
        
        success = historical_system.add_print_result(print_job)
        
        if success:
            return {
                'success': True,
                'message': 'Print job started and recorded',
                'job_id': job.job_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to record print job")
        
    except Exception as e:
        logger.error(f"Error starting print job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/history/job/complete")
async def complete_print_job(result: PrintResultRequest):
    """Record the completion of a print job"""
    try:
        # Get existing job
        existing_job = historical_system.data_manager.get_print_job(result.job_id)
        
        if not existing_job:
            raise HTTPException(status_code=404, detail="Print job not found")
        
        # Update job with completion data
        existing_job.end_time = datetime.now()
        existing_job.actual_duration = result.actual_duration
        existing_job.status = PrintStatus(result.status)
        existing_job.success_rating = result.success_rating
        existing_job.failure_type = FailureType(result.failure_type) if result.failure_type else None
        existing_job.failure_description = result.failure_description
        existing_job.surface_quality = result.surface_quality
        existing_job.dimensional_accuracy = result.dimensional_accuracy
        existing_job.structural_integrity = result.structural_integrity
        existing_job.filament_used = result.filament_used
        existing_job.energy_consumed = result.energy_consumed
        existing_job.user_notes = result.user_notes
        existing_job.would_print_again = result.would_print_again
        
        success = historical_system.add_print_result(existing_job)
        
        if success:
            return {
                'success': True,
                'message': 'Print job completed and recorded'
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update print job")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing print job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/user/{user_id}")
async def get_user_history(user_id: str, limit: int = Query(50, ge=1, le=200)):
    """Get print history for a specific user"""
    try:
        history = historical_system.data_manager.get_user_print_history(user_id, limit)
        
        # Convert to serializable format
        history_data = []
        for job in history:
            job_dict = job.__dict__.copy()
            # Convert datetime objects to ISO strings
            if job_dict['start_time']:
                job_dict['start_time'] = job_dict['start_time'].isoformat()
            if job_dict['end_time']:
                job_dict['end_time'] = job_dict['end_time'].isoformat()
            # Convert enums to strings
            if job_dict['status']:
                job_dict['status'] = job_dict['status'].value
            if job_dict['failure_type']:
                job_dict['failure_type'] = job_dict['failure_type'].value
            
            history_data.append(job_dict)
        
        return {
            'success': True,
            'data': {
                'user_id': user_id,
                'total_jobs': len(history_data),
                'jobs': history_data
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/statistics")
async def get_print_statistics(
    user_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get print statistics for a user or globally"""
    try:
        stats = historical_system.data_manager.get_print_statistics(user_id, days)
        
        return {
            'success': True,
            'data': stats
        }
        
    except Exception as e:
        logger.error(f"Error getting print statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/insights/{user_id}")
async def get_user_insights(user_id: str):
    """Get comprehensive insights for a user"""
    try:
        insights = historical_system.get_user_insights(user_id)
        
        return {
            'success': True,
            'data': insights
        }
        
    except Exception as e:
        logger.error(f"Error getting user insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/performance")
async def get_system_performance(days: int = Query(30, ge=1, le=365)):
    """Get system-wide performance analytics"""
    try:
        performance = historical_system.get_system_performance(days)
        
        return {
            'success': True,
            'data': performance
        }
        
    except Exception as e:
        logger.error(f"Error getting system performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/learning")
async def get_learning_insights():
    """Get insights about the learning system effectiveness"""
    try:
        insights = historical_system.get_learning_insights()
        
        return {
            'success': True,
            'data': insights
        }
        
    except Exception as e:
        logger.error(f"Error getting learning insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/failures")
async def get_failure_analysis(days: int = Query(90, ge=1, le=365)):
    """Get detailed failure pattern analysis"""
    try:
        analysis = historical_system.learning_engine.analyze_failure_patterns(days)
        
        return {
            'success': True,
            'data': analysis
        }
        
    except Exception as e:
        logger.error(f"Error getting failure analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Combined Analysis Endpoints
@router.post("/analyze/complete")
async def complete_design_analysis(
    file: UploadFile = File(...),
    design_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Perform complete design analysis with both preview and AI enhancement"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.stl'):
            raise HTTPException(status_code=400, detail="Only STL files are supported")
        
        # Generate design ID if not provided
        if not design_id:
            design_id = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save file temporarily
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / file.filename
        
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        try:
            # Generate 3D preview
            preview_data = preview_manager.generate_stl_preview(temp_file)
            
            # Perform AI analysis
            analysis_result = ai_enhancer.analyze_design(design_id, preview_data)
            
            # Get user preferences if user_id provided
            user_insights = None
            if user_id:
                user_insights = historical_system.get_user_insights(user_id)
            
            return {
                'success': True,
                'data': {
                    'design_id': design_id,
                    'preview_data': preview_data,
                    'ai_analysis': {
                        'metrics': analysis_result.metrics.__dict__,
                        'suggestions': [s.__dict__ for s in analysis_result.suggestions],
                        'failure_predictions': analysis_result.failure_predictions,
                        'recommended_materials': analysis_result.recommended_materials,
                        'recommended_settings': analysis_result.recommended_settings,
                        'overall_score': analysis_result.overall_score,
                        'improvement_potential': analysis_result.improvement_potential
                    },
                    'user_insights': user_insights
                }
            }
            
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()
        
    except Exception as e:
        logger.error(f"Error in complete design analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capabilities")
async def get_advanced_capabilities():
    """Get information about all advanced system capabilities"""
    try:
        ai_capabilities = ai_enhancer.get_enhancement_capabilities()
        historical_capabilities = historical_system.get_historical_capabilities()
        preview_capabilities = preview_manager.get_preview_capabilities()
        
        return {
            'success': True,
            'data': {
                'ai_design_enhancement': ai_capabilities,
                'historical_data_system': historical_capabilities,
                '3d_preview_system': preview_capabilities,
                'integrated_features': [
                    'Complete design analysis workflow',
                    'User-specific optimization suggestions',
                    'Learning from print outcomes',
                    'Continuous improvement tracking',
                    'Multi-dimensional analytics'
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check_advanced():
    """Health check for advanced features systems"""
    try:
        # Test each system
        systems_status = {
            'ai_design_enhancer': 'healthy',
            'historical_data_system': 'healthy',
            'preview_system': 'healthy'
        }
        
        # Test database connections
        try:
            historical_system.data_manager.get_print_statistics(days=1)
        except Exception:
            systems_status['historical_data_system'] = 'degraded'
        
        try:
            ai_enhancer.get_design_insights()
        except Exception:
            systems_status['ai_design_enhancer'] = 'degraded'
        
        overall_status = 'healthy' if all(status == 'healthy' for status in systems_status.values()) else 'degraded'
        
        return {
            'success': True,
            'status': overall_status,
            'systems': systems_status,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Batch Processing and Template-Based Printing Endpoints
@router.post("/batch/process")
async def process_batch_requests(batch: BatchRequest):
    """Process a batch of print requests"""
    try:
        processor = get_batch_processor()
        batch_id = processor.start_batch_processing(batch.requests, batch.settings)
        
        return {
            'success': True,
            'data': {
                'batch_id': batch_id,
                'status': 'processing'
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing batch requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get the status of a batch processing job"""
    try:
        processor = get_batch_processor()
        status = processor.get_batch_status(batch_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        return {
            'success': True,
            'data': status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/template/create")
async def create_print_template(template: TemplateRequest):
    """Create a new print template"""
    try:
        template_id = config_manager.create_template(template.category, template.name, template.customizations)
        
        return {
            'success': True,
            'data': {
                'template_id': template_id,
                'message': 'Template created successfully'
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/template/{template_id}")
async def get_template(template_id: str):
    """Get details of a specific print template"""
    try:
        template = config_manager.get_template(template_id)
        
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            'success': True,
            'data': template
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/template/{template_id}")
async def update_template(template_id: str, updates: TemplateRequest):
    """Update an existing print template"""
    try:
        success = config_manager.update_template(template_id, updates.customizations)
        
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            'success': True,
            'message': 'Template updated successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/template/{template_id}")
async def delete_template(template_id: str):
    """Delete a print template"""
    try:
        success = config_manager.delete_template(template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            'success': True,
            'message': 'Template deleted successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/stats/{user_id}")
async def get_history_statistics(user_id: str):
    """Get statistics about a user's print history"""
    try:
        stats = historical_system.get_user_history_statistics(user_id)
        
        return {
            'success': True,
            'data': stats
        }
        
    except Exception as e:
        logger.error(f"Error getting history statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New Batch Processing and Template Endpoints

@router.post("/batch", response_model=BatchResponse)
async def submit_batch_request(
    batch_request: BatchRequest,
    background_tasks: BackgroundTasks
):
    """Submit multiple print requests for batch processing."""
    try:
        processor = get_batch_processor()
        
        # Start batch processing in background
        async def process_batch_async():
            try:
                await processor.orchestrator.initialize()
                result = await processor.process_batch(
                    batch_request.requests,
                    batch_request.settings
                )
                
                # Add each successful print to history
                for print_result in result["results"]:
                    if print_result.get("success"):
                        print_history.add_print(print_result)
                        
                logger.info(f"✅ Batch processing completed: {result['batch_id']}")
                
            except Exception as e:
                logger.error(f"❌ Batch processing failed: {e}")
            finally:
                await processor.orchestrator.shutdown()
        
        # Start background task
        background_tasks.add_task(process_batch_async)
        
        # Return immediate response
        return BatchResponse(
            batch_id="pending",
            status="started",
            total_requests=len(batch_request.requests),
            completed=0,
            failed=0,
            success_rate=0.0
        )
        
    except Exception as e:
        logger.error(f"Failed to start batch processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_templates():
    """List all available print templates."""
    try:
        processor = get_batch_processor()
        return processor.list_templates()
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/template-print")
async def print_from_template(
    template_request: TemplateRequest,
    background_tasks: BackgroundTasks
):
    """Create a print job from a template."""
    try:
        processor = get_batch_processor()
        
        async def process_template_print():
            try:
                await processor.orchestrator.initialize()
                result = await processor.quick_print_from_template(
                    template_request.category,
                    template_request.name,
                    template_request.customizations
                )
                
                if result.get("success"):
                    print_history.add_print(result)
                    
                logger.info(f"✅ Template print completed: {template_request.category}/{template_request.name}")
                
            except Exception as e:
                logger.error(f"❌ Template print failed: {e}")
            finally:
                await processor.orchestrator.shutdown()
        
        background_tasks.add_task(process_template_print)
        
        return {"status": "started", "template": f"{template_request.category}/{template_request.name}"}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start template print: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/print-history", response_model=HistoryStats)
async def get_print_history_stats(limit: int = 10):
    """Get print history and statistics."""
    try:
        return HistoryStats(
            total_prints=len(print_history.history),
            success_rate=print_history.get_success_rate(),
            recent_prints=print_history.get_recent_prints(limit),
            popular_requests=print_history.get_popular_requests()
        )
    except Exception as e:
        logger.error(f"Failed to get print history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-examples")
async def get_quick_examples():
    """Get example batch requests for testing."""
    return {
        "basic_shapes": [
            "Print a 2cm cube",
            "Print a 3cm sphere", 
            "Print a cylinder 4cm tall and 2cm diameter"
        ],
        "household_items": [
            "Print a phone stand",
            "Print a cable organizer",
            "Print a wall hook"
        ],
        "educational": [
            "Print a gear set for learning mechanics",
            "Print a molecule model of water",
            "Print puzzle pieces for a brain teaser"
        ]
    }

# AI Image-to-3D Conversion Endpoints
@router.post("/image-to-3d/convert")
async def convert_image_to_3d(
    file: UploadFile = File(...),
    style: str = Query("realistic", description="3D conversion style"),
    quality: str = Query("medium", description="Output quality: low, medium, high"),
    format: str = Query("stl", description="Output format: stl, obj, ply")
):
    """Convert an uploaded image to a 3D model using AI"""
    try:
        logger.info(f"🖼️ Processing image-to-3D conversion: {file.filename}")
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Convert image to 3D model
        result = await ai_converter.convert_image_to_3d(
            image_data=image_data,
            filename=file.filename,
            style=style,
            quality=quality,
            output_format=format
        )
        
        if result['success']:
            logger.info(f"✅ Image-to-3D conversion completed: {result['model_path']}")
            return JSONResponse({
                "success": True,
                "model_id": result['model_id'],
                "model_path": result['model_path'],
                "preview_url": result['preview_url'],
                "metadata": result['metadata'],
                "processing_time": result['processing_time']
            })
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Conversion failed'))
            
    except Exception as e:
        logger.error(f"❌ Image-to-3D conversion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")

@router.get("/image-to-3d/models")
async def list_converted_models():
    """List all converted 3D models from images"""
    try:
        models = await ai_converter.list_converted_models()
        return JSONResponse({
            "success": True,
            "models": models,
            "count": len(models)
        })
    except Exception as e:
        logger.error(f"❌ Failed to list converted models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image-to-3d/models/{model_id}")
async def get_converted_model(model_id: str):
    """Get details of a specific converted 3D model"""
    try:
        model = await ai_converter.get_model_details(model_id)
        if model:
            return JSONResponse({
                "success": True,
                "model": model
            })
        else:
            raise HTTPException(status_code=404, detail="Model not found")
    except Exception as e:
        logger.error(f"❌ Failed to get model details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/image-to-3d/models/{model_id}")
async def delete_converted_model(model_id: str):
    """Delete a converted 3D model"""
    try:
        success = await ai_converter.delete_model(model_id)
        if success:
            return JSONResponse({
                "success": True,
                "message": "Model deleted successfully"
            })
        else:
            raise HTTPException(status_code=404, detail="Model not found")
    except Exception as e:
        logger.error(f"❌ Failed to delete model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/image-to-3d/models/{model_id}/print")
async def print_converted_model(model_id: str, request_data: Dict[str, Any]):
    """Submit a converted 3D model for printing"""
    try:
        model = await ai_converter.get_model_details(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Create print job for the converted model
        job_data = {
            "user_request": f"Print converted 3D model: {model['original_filename']}",
            "model_path": model['model_path'],
            "priority": request_data.get('priority', 'normal'),
            "source": "image_to_3d_conversion",
            "model_id": model_id
        }
        
        # Create a simple print job directly
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "user_request": job_data["user_request"],
            "model_path": job_data["model_path"],
            "priority": job_data["priority"],
            "source": job_data["source"],
            "model_id": model_id,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
        # Store in print history
        print_history.add_job(job)
        
        return JSONResponse({
            "success": True,
            "job_id": job['id'],
            "message": "Print job created for converted model"
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to create print job for converted model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Voice Control Endpoints
@router.get("/voice/status")
async def get_voice_control_status():
    """Get the current status of voice control system"""
    try:
        status = await voice_control.get_status()
        return JSONResponse({
            "success": True,
            "status": status
        })
    except Exception as e:
        logger.error(f"❌ Failed to get voice control status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/start")
async def start_voice_control():
    """Start voice recognition"""
    try:
        success = await voice_control.start_listening()
        return JSONResponse({
            "success": success,
            "message": "Voice control started" if success else "Failed to start voice control"
        })
    except Exception as e:
        logger.error(f"❌ Failed to start voice control: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/stop")
async def stop_voice_control():
    """Stop voice recognition"""
    try:
        success = await voice_control.stop_listening()
        return JSONResponse({
            "success": success,
            "message": "Voice control stopped" if success else "Failed to stop voice control"
        })
    except Exception as e:
        logger.error(f"❌ Failed to stop voice control: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/command")
async def process_voice_command(request: VoiceCommandRequest):
    """Process a voice command (audio or text)"""
    try:
        if request.text_command:
            # Process text command
            command = await voice_control.process_text_command(
                request.text_command, 
                request.confidence_threshold
            )
        elif request.audio_data:
            # Process audio command
            command = await voice_control.process_audio_command(
                request.audio_data, 
                request.confidence_threshold
            )
        else:
            raise HTTPException(status_code=400, detail="Either text_command or audio_data must be provided")
        
        return JSONResponse({
            "success": True,
            "command": {
                "intent": command.intent,
                "parameters": command.parameters,
                "confidence": command.confidence,
                "recognized_text": command.command
            }
        })
    except Exception as e:
        logger.error(f"❌ Failed to process voice command: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice/commands")
async def get_voice_command_history():
    """Get recent voice command history"""
    try:
        history = await voice_control.get_command_history()
        return JSONResponse({
            "success": True,
            "commands": [
                {
                    "command": cmd.command,
                    "intent": cmd.intent,
                    "parameters": cmd.parameters,
                    "confidence": cmd.confidence,
                    "timestamp": cmd.timestamp.isoformat()
                }
                for cmd in history
            ]
        })
    except Exception as e:
        logger.error(f"❌ Failed to get voice command history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Dashboard Endpoints
@router.get("/analytics/overview")
async def get_analytics_overview():
    """Get comprehensive analytics overview"""
    try:
        overview = await analytics_dashboard.get_overview()
        return JSONResponse({
            "success": True,
            "overview": overview
        })
    except Exception as e:
        logger.error(f"❌ Failed to get analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analytics/query")
async def query_analytics(request: AnalyticsQuery):
    """Query analytics data with filters"""
    try:
        data = await analytics_dashboard.query_metrics(
            start_date=request.start_date,
            end_date=request.end_date,
            metric_names=request.metric_names,
            tags=request.tags
        )
        return JSONResponse({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"❌ Failed to query analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/metrics/live")
async def get_live_metrics():
    """Get real-time system metrics"""
    try:
        metrics = await analytics_dashboard.get_live_metrics()
        return JSONResponse({
            "success": True,
            "metrics": metrics
        })
    except Exception as e:
        logger.error(f"❌ Failed to get live metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/performance")
async def get_performance_analytics():
    """Get performance analytics and insights"""
    try:
        performance = await analytics_dashboard.get_performance_insights()
        return JSONResponse({
            "success": True,
            "performance": performance
        })
    except Exception as e:
        logger.error(f"❌ Failed to get performance analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/health")
async def get_system_health():
    """Get system health metrics"""
    try:
        health = await analytics_dashboard.get_system_health()
        return JSONResponse({
            "success": True,
            "health": health
        })
    except Exception as e:
        logger.error(f"❌ Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template Library Endpoints
@router.get("/templates")
async def list_templates():
    """List all available templates"""
    try:
        templates = await template_library.list_templates()
        return JSONResponse({
            "success": True,
            "templates": templates,
            "count": len(templates)
        })
    except Exception as e:
        logger.error(f"❌ Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/search")
async def search_templates(request: TemplateSearchRequest):
    """Search templates with filters"""
    try:
        templates = await template_library.search_templates(
            category=request.category,
            difficulty=request.difficulty,
            search_term=request.search_term,
            tags=request.tags
        )
        return JSONResponse({
            "success": True,
            "templates": templates,
            "count": len(templates)
        })
    except Exception as e:
        logger.error(f"❌ Failed to search templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/categories")
async def get_template_categories():
    """Get all template categories"""
    try:
        categories = await template_library.get_categories()
        return JSONResponse({
            "success": True,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"❌ Failed to get template categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}")
async def get_template_details(template_id: str):
    """Get detailed information about a specific template"""
    try:
        template = await template_library.get_template(template_id)
        if template:
            return JSONResponse({
                "success": True,
                "template": template
            })
        else:
            raise HTTPException(status_code=404, detail="Template not found")
    except Exception as e:
        logger.error(f"❌ Failed to get template details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/{template_id}/customize")
async def customize_template(template_id: str, request: TemplateCustomizationRequest):
    """Customize a template with user parameters"""
    try:
        result = await template_library.customize_template(
            template_id=template_id,
            parameters=request.parameters,
            target_format=request.target_format
        )
        return JSONResponse({
            "success": True,
            "customized_model": result
        })
    except Exception as e:
        logger.error(f"❌ Failed to customize template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/{template_id}/print")
async def print_template(template_id: str, request_data: Dict[str, Any]):
    """Submit a template for printing (with optional customizations)"""
    try:
        template = await template_library.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Apply customizations if provided
        model_path = template['model_path']
        if request_data.get('parameters'):
            customization_result = await template_library.customize_template(
                template_id=template_id,
                parameters=request_data['parameters'],
                target_format="stl"
            )
            model_path = customization_result['model_path']
        
        # Create print job for the template
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "user_request": f"Print template: {template['name']}",
            "model_path": model_path,
            "priority": request_data.get('priority', 'normal'),
            "source": "template_library",
            "template_id": template_id,
            "status": "created",
            "created_at": datetime.now().isoformat()
        }
        
        # Store in print history
        print_history.add_job(job)
        
        return JSONResponse({
            "success": True,
            "job_id": job['id'],
            "message": "Print job created for template"
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to create print job for template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}/preview")
async def preview_template(template_id: str):
    """Generate a preview of a template"""
    try:
        preview = await template_library.generate_preview(template_id)
        return JSONResponse({
            "success": True,
            "preview": preview
        })
    except Exception as e:
        logger.error(f"❌ Failed to generate template preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
