#!/usr/bin/env python3
"""
Advanced Features Module for AI Agent 3D Print System

This module adds enhanced capabilities:
- Batch processing of multiple print requests
- Template-based quick prints  
- Print history and analytics
- Advanced configuration management
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from core.logger import get_logger
from config.settings import load_config

logger = get_logger(__name__)


class BatchProcessor:
    """Handle batch processing of multiple print requests."""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.batch_history = []
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined print templates."""
        templates = {
            "basic_shapes": {
                "cube": {"size": "2cm", "infill": "20%", "material": "PLA"},
                "sphere": {"diameter": "3cm", "infill": "15%", "material": "PLA"},
                "cylinder": {"height": "4cm", "diameter": "2cm", "infill": "20%", "material": "PLA"}
            },
            "household": {
                "phone_stand": {"material": "PETG", "infill": "25%", "supports": True},
                "cable_organizer": {"material": "PLA", "infill": "20%", "supports": False},
                "hook": {"material": "ABS", "infill": "30%", "supports": False}
            },
            "educational": {
                "gear_set": {"material": "PLA", "infill": "30%", "supports": True},
                "molecule_model": {"material": "PLA", "infill": "15%", "supports": False},
                "puzzle_piece": {"material": "PETG", "infill": "25%", "supports": False}
            }
        }
        return templates
    
    async def process_batch(self, requests: List[str], batch_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process multiple print requests in batch."""
        batch_id = str(uuid.uuid4())
        batch_result = {
            "batch_id": batch_id,
            "start_time": datetime.now().isoformat(),
            "total_requests": len(requests),
            "completed": 0,
            "failed": 0,
            "results": [],
            "settings": batch_settings or {}
        }
        
        logger.info(f"🔄 Starting batch processing: {batch_id} with {len(requests)} requests")
        
        # Process requests concurrently (limited concurrency to avoid overload)
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        
        async def process_single_request(request: str, index: int):
            async with semaphore:
                try:
                    logger.info(f"📝 Processing request {index + 1}/{len(requests)}: {request}")
                    result = await self.orchestrator.execute_complete_workflow(
                        request, 
                        show_progress=False
                    )
                    result["request_index"] = index
                    result["original_request"] = request
                    batch_result["results"].append(result)
                    
                    if result["success"]:
                        batch_result["completed"] += 1
                        logger.info(f"✅ Request {index + 1} completed successfully")
                    else:
                        batch_result["failed"] += 1
                        logger.warning(f"❌ Request {index + 1} failed: {result.get('error_message', 'Unknown error')}")
                        
                except Exception as e:
                    error_result = {
                        "request_index": index,
                        "original_request": request,
                        "success": False,
                        "error_message": str(e)
                    }
                    batch_result["results"].append(error_result)
                    batch_result["failed"] += 1
                    logger.error(f"❌ Request {index + 1} failed with exception: {e}")
        
        # Start all requests
        tasks = [
            process_single_request(request, i) 
            for i, request in enumerate(requests)
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        batch_result["end_time"] = datetime.now().isoformat()
        batch_result["success_rate"] = batch_result["completed"] / batch_result["total_requests"] * 100
        
        # Store batch history
        self.batch_history.append(batch_result)
        
        logger.info(f"🎉 Batch processing completed: {batch_result['completed']}/{batch_result['total_requests']} successful")
        
        return batch_result
    
    def get_template(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a predefined template."""
        return self.templates.get(category, {}).get(name)
    
    def list_templates(self) -> Dict[str, List[str]]:
        """List all available templates."""
        return {
            category: list(templates.keys())
            for category, templates in self.templates.items()
        }
    
    async def quick_print_from_template(self, category: str, name: str, customizations: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a print request from a template."""
        template = self.get_template(category, name)
        if not template:
            raise ValueError(f"Template not found: {category}/{name}")
        
        # Apply customizations
        if customizations:
            template.update(customizations)
        
        # Convert template to natural language request
        request = self._template_to_request(name, template)
        
        logger.info(f"🎯 Quick print from template: {category}/{name}")
        
        return await self.orchestrator.execute_complete_workflow(request, show_progress=True)
    
    def _template_to_request(self, name: str, template: Dict[str, Any]) -> str:
        """Convert template parameters to natural language request."""
        base_request = f"Print a {name.replace('_', ' ')}"
        
        details = []
        if "size" in template:
            details.append(f"size {template['size']}")
        if "diameter" in template:
            details.append(f"diameter {template['diameter']}")
        if "height" in template:
            details.append(f"height {template['height']}")
        if "material" in template:
            details.append(f"using {template['material']} material")
        if "infill" in template:
            details.append(f"with {template['infill']} infill")
        
        if details:
            base_request += f" with {', '.join(details)}"
        
        return base_request


class PrintHistory:
    """Manage print history and analytics."""
    
    def __init__(self):
        self.history_file = Path("data/print_history.json")
        self.history_file.parent.mkdir(exist_ok=True)
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load print history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load print history: {e}")
        return []
    
    def _save_history(self):
        """Save print history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save print history: {e}")
    
    def add_job(self, job_data: Dict[str, Any]):
        """Add a job to print history."""
        try:
            self.history.append(job_data)
            self._save_history()
            logger.info(f"📝 Added job to print history: {job_data.get('id')}")
        except Exception as e:
            logger.error(f"❌ Failed to add job to history: {e}")

    def add_print(self, workflow_result: Dict[str, Any]):
        """Add a completed print to history."""
        history_entry = {
            "id": workflow_result.get("workflow_id"),
            "request": workflow_result.get("user_request"),
            "timestamp": workflow_result.get("start_time"),
            "success": workflow_result.get("success"),
            "duration": self._calculate_duration(workflow_result),
            "phases": workflow_result.get("phases", {}),
            "files_generated": workflow_result.get("files_generated", [])
        }
        
        self.history.append(history_entry)
        self._save_history()
        
        logger.info(f"📊 Added print to history: {history_entry['request']}")
    
    def _calculate_duration(self, workflow_result: Dict[str, Any]) -> Optional[float]:
        """Calculate print duration in seconds."""
        try:
            start = datetime.fromisoformat(workflow_result.get("start_time", ""))
            end = datetime.fromisoformat(workflow_result.get("end_time", ""))
            return (end - start).total_seconds()
        except:
            return None
    
    def get_recent_prints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent prints."""
        return sorted(self.history, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def get_success_rate(self, days: int = 30) -> float:
        """Calculate success rate over the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        recent_prints = [
            p for p in self.history 
            if datetime.fromisoformat(p["timestamp"]) > cutoff
        ]
        
        if not recent_prints:
            return 0.0
        
        successful = sum(1 for p in recent_prints if p["success"])
        return (successful / len(recent_prints)) * 100
    
    def get_popular_requests(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most popular print requests."""
        request_counts = {}
        for print_job in self.history:
            request = print_job["request"].lower()
            request_counts[request] = request_counts.get(request, 0) + 1
        
        popular = sorted(request_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"request": req, "count": count} for req, count in popular]


class AdvancedConfigManager:
    """Advanced configuration management with profiles."""
    
    def __init__(self):
        self.config_dir = Path("config/profiles")
        self.config_dir.mkdir(exist_ok=True)
        self.base_config = load_config()
    
    def create_profile(self, name: str, config: Dict[str, Any]):
        """Create a new configuration profile."""
        profile_file = self.config_dir / f"{name}.json"
        
        try:
            with open(profile_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"📝 Created configuration profile: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create profile {name}: {e}")
            return False
    
    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a configuration profile."""
        profile_file = self.config_dir / f"{name}.json"
        
        if not profile_file.exists():
            return None
        
        try:
            with open(profile_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load profile {name}: {e}")
            return None
    
    def list_profiles(self) -> List[str]:
        """List all available profiles."""
        return [f.stem for f in self.config_dir.glob("*.json")]
    
    def apply_profile(self, name: str) -> bool:
        """Apply a configuration profile."""
        profile_config = self.load_profile(name)
        if not profile_config:
            return False
        
        # Merge with base config
        merged_config = {**self.base_config, **profile_config}
        
        # Here you would apply the configuration to the system
        # For now, we'll just log it
        logger.info(f"🔧 Applied configuration profile: {name}")
        return True


# Predefined configuration profiles
DEFAULT_PROFILES = {
    "high_quality": {
        "printer": {
            "layer_height": 0.1,
            "infill_percentage": 30,
            "print_speed": 40,
            "temperature": {
                "nozzle": 210,
                "bed": 60
            }
        }
    },
    "fast_draft": {
        "printer": {
            "layer_height": 0.3,
            "infill_percentage": 15,
            "print_speed": 80,
            "temperature": {
                "nozzle": 215,
                "bed": 60
            }
        }
    },
    "strong_functional": {
        "printer": {
            "layer_height": 0.2,
            "infill_percentage": 50,
            "print_speed": 50,
            "temperature": {
                "nozzle": 220,
                "bed": 70
            }
        }
    }
}
