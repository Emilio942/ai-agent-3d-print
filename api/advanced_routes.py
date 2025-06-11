"""
API endpoints for AI-Enhanced Design and Historical Data Systems

This module provides REST API endpoints for AI-enhanced design analysis,
optimization suggestions, historical data tracking, and learning insights.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
from datetime import datetime

from core.ai_design_enhancer import AIDesignEnhancer, DesignAnalysisResult
from core.historical_data_system import (
    HistoricalDataSystem, PrintJob, PrintStatus, FailureType
)
from core.print_preview import PrintPreviewManager
from core.logger import get_logger

logger = get_logger(__name__)

# Create router for advanced features API
router = APIRouter(prefix="/api/advanced", tags=["advanced"])

# Initialize systems
ai_enhancer = AIDesignEnhancer()
historical_system = HistoricalDataSystem()
preview_manager = PrintPreviewManager()

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
