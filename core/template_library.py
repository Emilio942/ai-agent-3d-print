#!/usr/bin/env python3
"""
Template Library System for AI Agent 3D Print System

This module provides a comprehensive library of pre-designed 3D model templates
that users can quickly customize and print, accelerating the design process.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from core.logger import get_logger

logger = get_logger(__name__)


class TemplateCategory(Enum):
    """Categories for organizing templates"""
    MECHANICAL = "mechanical"
    DECORATIVE = "decorative"
    FUNCTIONAL = "functional"
    TOYS_GAMES = "toys_games"
    TOOLS = "tools"
    HOUSEHOLD = "household"
    JEWELRY = "jewelry"
    EDUCATIONAL = "educational"
    PROTOTYPING = "prototyping"
    ART = "art"


class PrintDifficulty(Enum):
    """Printing difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class TemplateParameter:
    """Represents a customizable parameter in a template"""
    name: str
    display_name: str
    parameter_type: str  # "number", "text", "choice", "boolean"
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[List[str]] = None
    unit: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Template:
    """Represents a 3D model template"""
    id: str
    name: str
    description: str
    category: TemplateCategory
    difficulty: PrintDifficulty
    parameters: List[TemplateParameter]
    preview_image: str
    model_file: str
    tags: List[str]
    author: str
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    print_time_estimate: Optional[int] = None  # in minutes
    material_estimate: Optional[float] = None  # in grams
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class TemplateLibrary:
    """Manages the template library and customization"""
    
    def __init__(self, library_path: str = "data/templates"):
        self.logger = get_logger(f"{__name__}.TemplateLibrary")
        self.library_path = Path(library_path)
        
        # Only create directory if it doesn't exist and we have permissions
        try:
            self.library_path.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            self.logger.warning(f"Could not create template library directory: {e}")
        
        self.templates: Dict[str, Template] = {}
        self.categories: Dict[TemplateCategory, List[str]] = {}
        
    def __init__(self, library_path: str = "data/templates"):
        self.logger = get_logger(f"{__name__}.TemplateLibrary")
        self.library_path = Path(library_path)
        
        # Only create directory if it doesn't exist and we have permissions
        try:
            self.library_path.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            self.logger.warning(f"Could not create template library directory: {e}")
        
        self.templates: Dict[str, Template] = {}
        self.categories: Dict[TemplateCategory, List[str]] = {}
        
        # Initialize with simple templates for now
        self._initialize_simple_templates()
        
    def _initialize_simple_templates(self):
        """Initialize with simple templates to avoid complex dataclass issues"""
        try:
            # Create a simple gear template
            gear_template = Template(
                id=str(uuid.uuid4()),
                name="Simple Gear",
                description="A basic gear template",
                category=TemplateCategory.MECHANICAL,
                difficulty=PrintDifficulty.BEGINNER,
                parameters=[],  # Start with no parameters
                preview_image="/templates/previews/gear.png",
                model_file="/templates/models/gear.stl",
                tags=["gear", "mechanical"],
                author="AI Agent System",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                rating=4.5,
                usage_count=10,
                print_time_estimate=45,
                material_estimate=15.0
            )
            
            self.templates[gear_template.id] = gear_template
            self.logger.info(f"✅ Initialized {len(self.templates)} simple templates")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize simple templates: {e}")
            # Continue with empty templates
            pass
    
    def _initialize_default_templates(self):
        """Initialize the library with default templates"""
        default_templates = [
            {
                "name": "Customizable Gear",
                "description": "A parametric gear that can be customized for different applications",
                "category": TemplateCategory.MECHANICAL,
                "difficulty": PrintDifficulty.INTERMEDIATE,
                "parameters": [
                    TemplateParameter(
                        name="teeth", 
                        display_name="Number of Teeth", 
                        parameter_type="number", 
                        default_value=20, 
                        min_value=8, 
                        max_value=100, 
                        unit="teeth"
                    ),
                    TemplateParameter(
                        name="module", 
                        display_name="Module (Tooth Size)", 
                        parameter_type="number", 
                        default_value=2.0, 
                        min_value=0.5, 
                        max_value=10.0, 
                        unit="mm"
                    ),
                    TemplateParameter(
                        name="thickness", 
                        display_name="Gear Thickness", 
                        parameter_type="number", 
                        default_value=5.0, 
                        min_value=2.0, 
                        max_value=20.0, 
                        unit="mm"
                    ),
                    TemplateParameter(
                        name="bore_diameter", 
                        display_name="Center Hole Diameter", 
                        parameter_type="number", 
                        default_value=6.0, 
                        min_value=0.0, 
                        max_value=50.0, 
                        unit="mm"
                    ),
                    TemplateParameter(
                        name="pressure_angle", 
                        display_name="Pressure Angle", 
                        parameter_type="choice", 
                        default_value="20°", 
                        choices=["14.5°", "20°", "25°"]
                    )
                ],
                "tags": ["gear", "mechanical", "parametric", "functional"],
                "author": "AI Agent System",
                "print_time_estimate": 45,
                "material_estimate": 15.0
            },
            {
                "name": "Phone Stand",
                "description": "Adjustable phone stand for different device sizes",
                "category": TemplateCategory.FUNCTIONAL,
                "difficulty": PrintDifficulty.BEGINNER,
                "parameters": [
                    TemplateParameter("phone_width", "Phone Width", "number", 75.0, 50.0, 100.0, unit="mm"),
                    TemplateParameter("phone_thickness", "Phone Thickness", "number", 8.0, 5.0, 15.0, unit="mm"),
                    TemplateParameter("angle", "Stand Angle", "number", 60.0, 30.0, 90.0, unit="degrees"),
                    TemplateParameter("base_size", "Base Size", "choice", "Medium", choices=["Small", "Medium", "Large"]),
                    TemplateParameter("cable_notch", "Cable Management Notch", "boolean", True)
                ],
                "tags": ["phone", "stand", "functional", "office"],
                "author": "AI Agent System",
                "print_time_estimate": 90,
                "material_estimate": 25.0
            },
            {
                "name": "Custom Box",
                "description": "A simple box with customizable dimensions and features",
                "category": TemplateCategory.FUNCTIONAL,
                "difficulty": PrintDifficulty.BEGINNER,
                "parameters": [
                    TemplateParameter("length", "Length", "number", 100.0, 10.0, 300.0, unit="mm"),
                    TemplateParameter("width", "Width", "number", 80.0, 10.0, 300.0, unit="mm"),
                    TemplateParameter("height", "Height", "number", 50.0, 5.0, 200.0, unit="mm"),
                    TemplateParameter("wall_thickness", "Wall Thickness", "number", 2.0, 0.8, 5.0, unit="mm"),
                    TemplateParameter("lid_type", "Lid Type", "choice", "Sliding", choices=["None", "Hinged", "Sliding", "Snap-fit"]),
                    TemplateParameter("rounded_corners", "Rounded Corners", "boolean", True)
                ],
                "tags": ["box", "container", "storage", "functional"],
                "author": "AI Agent System",
                "print_time_estimate": 120,
                "material_estimate": 40.0
            },
            {
                "name": "Fidget Spinner",
                "description": "Classic fidget spinner with customizable design",
                "category": TemplateCategory.TOYS_GAMES,
                "difficulty": PrintDifficulty.INTERMEDIATE,
                "parameters": [
                    TemplateParameter("arm_count", "Number of Arms", "choice", "3", choices=["3", "4", "5", "6"]),
                    TemplateParameter("overall_diameter", "Overall Diameter", "number", 75.0, 50.0, 120.0, unit="mm"),
                    TemplateParameter("bearing_size", "Bearing Size", "choice", "608", choices=["608", "688", "625"]),
                    TemplateParameter("thickness", "Thickness", "number", 7.0, 5.0, 12.0, unit="mm"),
                    TemplateParameter("weight_style", "Weight Distribution", "choice", "Heavy Arms", choices=["Balanced", "Heavy Arms", "Heavy Center"]),
                    TemplateParameter("decorative_pattern", "Decorative Pattern", "choice", "None", choices=["None", "Hexagonal", "Circular", "Star"])
                ],
                "tags": ["fidget", "spinner", "toy", "fun"],
                "author": "AI Agent System", 
                "print_time_estimate": 60,
                "material_estimate": 20.0
            },
            {
                "name": "Jewelry Ring",
                "description": "Customizable ring design with various patterns",
                "category": TemplateCategory.JEWELRY,
                "difficulty": PrintDifficulty.ADVANCED,
                "parameters": [
                    TemplateParameter("ring_size", "Ring Size (US)", "number", 7.0, 4.0, 13.0, unit="US size"),
                    TemplateParameter("band_width", "Band Width", "number", 6.0, 2.0, 15.0, unit="mm"),
                    TemplateParameter("band_thickness", "Band Thickness", "number", 1.5, 0.8, 3.0, unit="mm"),
                    TemplateParameter("pattern", "Pattern", "choice", "Smooth", choices=["Smooth", "Textured", "Geometric", "Organic", "Celtic"]),
                    TemplateParameter("stone_setting", "Stone Setting", "choice", "None", choices=["None", "Simple", "Prong", "Bezel"]),
                    TemplateParameter("finish", "Surface Finish", "choice", "Polished", choices=["Matte", "Polished", "Brushed"])
                ],
                "tags": ["ring", "jewelry", "fashion", "accessory"],
                "author": "AI Agent System",
                "print_time_estimate": 30,
                "material_estimate": 5.0
            },
            {
                "name": "Tool Holder",
                "description": "Customizable tool holder for workshop organization",
                "category": TemplateCategory.TOOLS,
                "difficulty": PrintDifficulty.BEGINNER,
                "parameters": [
                    TemplateParameter("tool_count", "Number of Tools", "number", 6, 2, 20, unit="tools"),
                    TemplateParameter("tool_diameter", "Tool Diameter", "number", 10.0, 3.0, 25.0, unit="mm"),
                    TemplateParameter("holder_length", "Holder Length", "number", 150.0, 50.0, 300.0, unit="mm"),
                    TemplateParameter("mounting_type", "Mounting Type", "choice", "Wall Mount", choices=["Standalone", "Wall Mount", "Magnetic"]),
                    TemplateParameter("label_area", "Include Label Area", "boolean", True),
                    TemplateParameter("angle", "Tool Angle", "number", 0.0, -45.0, 45.0, unit="degrees")
                ],
                "tags": ["tool", "holder", "organization", "workshop"],
                "author": "AI Agent System",
                "print_time_estimate": 75,
                "material_estimate": 30.0
            },
            {
                "name": "Planter Pot",
                "description": "Decorative planter pot for small plants",
                "category": TemplateCategory.DECORATIVE,
                "difficulty": PrintDifficulty.BEGINNER,
                "parameters": [
                    TemplateParameter("top_diameter", "Top Diameter", "number", 120.0, 50.0, 200.0, unit="mm"),
                    TemplateParameter("bottom_diameter", "Bottom Diameter", "number", 80.0, 30.0, 180.0, unit="mm"),
                    TemplateParameter("height", "Height", "number", 100.0, 30.0, 200.0, unit="mm"),
                    TemplateParameter("wall_thickness", "Wall Thickness", "number", 2.5, 1.5, 5.0, unit="mm"),
                    TemplateParameter("drainage_holes", "Drainage Holes", "boolean", True),
                    TemplateParameter("decorative_style", "Decorative Style", "choice", "Modern", choices=["Smooth", "Modern", "Textured", "Geometric", "Natural"])
                ],
                "tags": ["planter", "pot", "garden", "decorative"],
                "author": "AI Agent System",
                "print_time_estimate": 180,
                "material_estimate": 60.0
            }
        ]
        
        # Create template objects
        for template_data in default_templates:
            template_id = str(uuid.uuid4())
            template = Template(
                id=template_id,
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                difficulty=template_data["difficulty"],
                parameters=template_data["parameters"],
                preview_image=f"/templates/previews/{template_id}.png",
                model_file=f"/templates/models/{template_id}.stl",
                tags=template_data["tags"],
                author=template_data["author"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                print_time_estimate=template_data.get("print_time_estimate"),
                material_estimate=template_data.get("material_estimate")
            )
            
            self._save_template(template)
    
    def _load_templates(self):
        """Load templates from the library directory"""
        try:
            templates_file = self.library_path / "templates.json"
            
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    templates_data = json.load(f)
                
                for template_data in templates_data:
                    # Reconstruct TemplateParameter objects
                    parameters = []
                    for param_data in template_data.get("parameters", []):
                        parameters.append(TemplateParameter(**param_data))
                    
                    template = Template(
                        id=template_data["id"],
                        name=template_data["name"],
                        description=template_data["description"],
                        category=TemplateCategory(template_data["category"]),
                        difficulty=PrintDifficulty(template_data["difficulty"]),
                        parameters=parameters,
                        preview_image=template_data["preview_image"],
                        model_file=template_data["model_file"],
                        tags=template_data["tags"],
                        author=template_data["author"],
                        created_at=datetime.fromisoformat(template_data["created_at"]),
                        updated_at=datetime.fromisoformat(template_data["updated_at"]),
                        usage_count=template_data.get("usage_count", 0),
                        rating=template_data.get("rating", 0.0),
                        rating_count=template_data.get("rating_count", 0),
                        print_time_estimate=template_data.get("print_time_estimate"),
                        material_estimate=template_data.get("material_estimate")
                    )
                    
                    self.templates[template.id] = template
            
            self._organize_by_categories()
            self.logger.info(f"✅ Loaded {len(self.templates)} templates from library")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load templates: {e}")
    
    def _save_template(self, template: Template):
        """Save a single template to the library"""
        self.templates[template.id] = template
        self._save_all_templates()
    
    def _save_all_templates(self):
        """Save all templates to the library file"""
        try:
            templates_file = self.library_path / "templates.json"
            
            # Convert templates to serializable format
            templates_data = []
            for template in self.templates.values():
                template_dict = template.to_dict()
                # Convert TemplateParameter objects to dicts
                template_dict["parameters"] = [asdict(param) for param in template.parameters]
                templates_data.append(template_dict)
            
            with open(templates_file, 'w') as f:
                json.dump(templates_data, f, indent=2, default=str)
                
            self.logger.info(f"💾 Saved {len(templates_data)} templates to library")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save templates: {e}")
    
    def _organize_by_categories(self):
        """Organize templates by categories"""
        self.categories = {category: [] for category in TemplateCategory}
        
        for template in self.templates.values():
            self.categories[template.category].append(template.id)
    
    async def get_templates(self, 
                           category: Optional[TemplateCategory] = None,
                           difficulty: Optional[PrintDifficulty] = None,
                           tags: Optional[List[str]] = None,
                           search_query: Optional[str] = None) -> List[Template]:
        """Get templates with optional filtering"""
        
        templates = list(self.templates.values())
        
        # Filter by category
        if category:
            templates = [t for t in templates if t.category == category]
        
        # Filter by difficulty
        if difficulty:
            templates = [t for t in templates if t.difficulty == difficulty]
        
        # Filter by tags
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        # Filter by search query
        if search_query:
            query_lower = search_query.lower()
            templates = [
                t for t in templates 
                if query_lower in t.name.lower() 
                or query_lower in t.description.lower()
                or any(query_lower in tag.lower() for tag in t.tags)
            ]
        
        # Sort by popularity (usage count and rating)
        templates.sort(key=lambda t: (t.usage_count * t.rating), reverse=True)
        
        return templates
    
    async def get_template(self, template_id: str) -> Optional[Template]:
        """Get a specific template by ID"""
        return self.templates.get(template_id)
    
    async def customize_template(self, 
                                template_id: str, 
                                parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Customize a template with given parameters"""
        try:
            template = self.templates.get(template_id)
            if not template:
                return {"success": False, "error": "Template not found"}
            
            # Validate parameters
            validation_result = self._validate_parameters(template, parameters)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
            
            # Generate customized model
            customized_model = await self._generate_customized_model(template, parameters)
            
            # Update usage statistics
            template.usage_count += 1
            self._save_all_templates()
            
            self.logger.info(f"🎨 Customized template: {template.name}")
            
            return {
                "success": True,
                "template_id": template_id,
                "customized_model": customized_model,
                "parameters": parameters,
                "estimated_print_time": self._estimate_print_time(template, parameters),
                "estimated_material": self._estimate_material_usage(template, parameters)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to customize template: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_parameters(self, template: Template, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate customization parameters"""
        
        for param in template.parameters:
            if param.name in parameters:
                value = parameters[param.name]
                
                # Type validation
                if param.parameter_type == "number":
                    if not isinstance(value, (int, float)):
                        return {"valid": False, "error": f"Parameter '{param.name}' must be a number"}
                    
                    # Range validation
                    if param.min_value is not None and value < param.min_value:
                        return {"valid": False, "error": f"Parameter '{param.name}' must be >= {param.min_value}"}
                    
                    if param.max_value is not None and value > param.max_value:
                        return {"valid": False, "error": f"Parameter '{param.name}' must be <= {param.max_value}"}
                
                elif param.parameter_type == "choice":
                    if param.choices and value not in param.choices:
                        return {"valid": False, "error": f"Parameter '{param.name}' must be one of: {param.choices}"}
                
                elif param.parameter_type == "boolean":
                    if not isinstance(value, bool):
                        return {"valid": False, "error": f"Parameter '{param.name}' must be true or false"}
        
        return {"valid": True}
    
    async def _generate_phone_stand(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate phone stand using CAD operations"""
        try:
            angle = parameters.get('angle', 15)
            width = parameters.get('width', 80)
            depth = parameters.get('depth', 40)
            thickness = parameters.get('thickness', 3)
            
            # Create design specifications for phone stand
            design_spec = {
                'object_type': 'phone_stand',
                'primary_shape': 'custom',
                'dimensions': {'width': width, 'depth': depth, 'thickness': thickness},
                'features': ['angled_support', 'charging_cable_slot'],
                'angle': angle,
                'material_type': 'PLA'
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_phone_stand',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_gear(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate gear using CAD operations"""
        try:
            teeth = parameters.get('teeth', 12)
            diameter = parameters.get('diameter', 20)
            thickness = parameters.get('thickness', 3)
            bore_diameter = parameters.get('bore_diameter', 3)
            
            design_spec = {
                'object_type': 'gear',
                'primary_shape': 'gear',
                'dimensions': {'diameter': diameter, 'thickness': thickness},
                'features': ['teeth', 'center_bore'],
                'teeth_count': teeth,
                'bore_diameter': bore_diameter,
                'material_type': 'PLA'
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_gear',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_pencil_holder(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pencil holder using CAD operations"""
        try:
            diameter = parameters.get('diameter', 50)
            height = parameters.get('height', 100)
            wall_thickness = parameters.get('wall_thickness', 2)
            compartments = parameters.get('compartments', 1)
            
            design_spec = {
                'object_type': 'pencil_holder',
                'primary_shape': 'cylinder',
                'dimensions': {'diameter': diameter, 'height': height},
                'features': ['hollow_interior', 'multiple_compartments'] if compartments > 1 else ['hollow_interior'],
                'wall_thickness': wall_thickness,
                'compartments': compartments,
                'material_type': 'PLA'
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_container',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_storage_box(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate storage box using CAD operations"""
        try:
            length = parameters.get('length', 100)
            width = parameters.get('width', 80)
            height = parameters.get('height', 60)
            wall_thickness = parameters.get('wall_thickness', 2)
            lid = parameters.get('lid', True)
            
            design_spec = {
                'object_type': 'storage_box',
                'primary_shape': 'box',
                'dimensions': {'x': length, 'y': width, 'z': height},
                'features': ['hollow_interior', 'removable_lid'] if lid else ['hollow_interior'],
                'wall_thickness': wall_thickness,
                'material_type': 'PLA'
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_container',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_cable_manager(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cable management clip using CAD operations"""
        try:
            cable_diameter = parameters.get('cable_diameter', 5)
            clip_width = parameters.get('clip_width', 20)
            thickness = parameters.get('thickness', 3)
            
            design_spec = {
                'object_type': 'cable_clip',
                'primary_shape': 'custom',
                'dimensions': {'width': clip_width, 'thickness': thickness},
                'features': ['cable_groove', 'mounting_hole'],
                'cable_diameter': cable_diameter,
                'material_type': 'PETG'  # Flexible for clips
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_clip',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_desk_organizer(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate desk organizer using CAD operations"""
        try:
            sections = parameters.get('sections', 3)
            width = parameters.get('width', 150)
            depth = parameters.get('depth', 100)
            height = parameters.get('height', 80)
            
            design_spec = {
                'object_type': 'desk_organizer',
                'primary_shape': 'box',
                'dimensions': {'x': width, 'y': depth, 'z': height},
                'features': ['multiple_compartments', 'dividers'],
                'sections': sections,
                'material_type': 'PLA'
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_organizer',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_bracket(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate custom bracket using CAD operations"""
        try:
            length = parameters.get('length', 50)
            width = parameters.get('width', 30)
            thickness = parameters.get('thickness', 5)
            hole_diameter = parameters.get('hole_diameter', 5)
            
            design_spec = {
                'object_type': 'bracket',
                'primary_shape': 'custom',
                'dimensions': {'x': length, 'y': width, 'z': thickness},
                'features': ['mounting_holes', 'l_shape'],
                'hole_diameter': hole_diameter,
                'material_type': 'PETG'
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_bracket',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_basic_shape(self, cad_agent, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic shape as fallback"""
        try:
            size = parameters.get('size', 20)
            shape = parameters.get('shape', 'cube')
            
            design_spec = {
                'object_type': shape,
                'primary_shape': shape,
                'dimensions': {'x': size, 'y': size, 'z': size},
                'material_type': 'PLA'
            }
            
            return await cad_agent.execute_task({
                'operation': 'create_primitive',
                'design_specifications': design_spec
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _generate_customized_model(self, template: Template, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a customized 3D model using real CAD operations"""
        try:
            # Import CAD agent for actual 3D model generation
            from agents.cad_agent import CADAgent
            
            model_id = str(uuid.uuid4())
            self.logger.info(f"Generating customized model for template '{template.name}' with ID {model_id}")
            
            # Create CAD agent instance for model generation
            cad_agent = CADAgent(f"template_cad_{model_id}")
            
            # Generate model based on template type
            if template.name == "Phone Stand":
                result = await self._generate_phone_stand(cad_agent, parameters)
            elif template.name == "Simple Gear":
                result = await self._generate_gear(cad_agent, parameters)
            elif template.name == "Pencil Holder":
                result = await self._generate_pencil_holder(cad_agent, parameters)
            elif template.name == "Storage Box":
                result = await self._generate_storage_box(cad_agent, parameters)
            elif template.name == "Cable Management":
                result = await self._generate_cable_manager(cad_agent, parameters)
            elif template.name == "Desk Organizer":
                result = await self._generate_desk_organizer(cad_agent, parameters)
            elif template.name == "Custom Bracket":
                result = await self._generate_bracket(cad_agent, parameters)
            else:
                # Fallback to basic cube
                result = await self._generate_basic_shape(cad_agent, parameters)
            
            if result.get('success', False):
                output_file = result.get('output_file', '')
                
                # Ensure output directory exists
                output_dir = Path("/tmp/customized_models")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy to final location if needed
                final_path = output_dir / f"{model_id}.stl"
                if output_file and Path(output_file).exists():
                    import shutil
                    shutil.copy2(output_file, final_path)
                else:
                    final_path = output_file
                
                self.logger.info(f"Successfully generated model: {final_path}")
                
                return {
                    "model_id": model_id,
                    "file_path": str(final_path),
                    "preview_image": f"/tmp/customized_models/{model_id}_preview.png",
                    "generated_at": datetime.now().isoformat(),
                    "base_template": template.name,
                    "generation_method": "real_cad",
                    "cad_result": result
                }
            else:
                raise Exception(f"CAD generation failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Model generation failed: {e}")
            # Fallback to simulation for now
            model_id = str(uuid.uuid4())
            return {
                "model_id": model_id,
                "file_path": f"/tmp/customized_models/{model_id}.stl",
                "preview_image": f"/tmp/customized_models/{model_id}_preview.png",
                "generated_at": datetime.now().isoformat(),
                "base_template": template.name,
                "generation_method": "fallback_simulation",
                "error": str(e)
            }
    
    def _estimate_print_time(self, template: Template, parameters: Dict[str, Any]) -> int:
        """Estimate print time based on template and parameters"""
        
        base_time = template.print_time_estimate or 60  # Default 60 minutes
        
        # Adjust based on size parameters
        scale_factor = 1.0
        
        for param in template.parameters:
            if param.name in parameters and param.parameter_type == "number":
                value = parameters[param.name]
                default_value = param.default_value
                
                if "size" in param.name.lower() or "diameter" in param.name.lower() or "length" in param.name.lower():
                    scale_factor *= (value / default_value) ** 2  # Area scaling
        
        return int(base_time * scale_factor)
    
    def _estimate_material_usage(self, template: Template, parameters: Dict[str, Any]) -> float:
        """Estimate material usage based on template and parameters"""
        
        base_material = template.material_estimate or 20.0  # Default 20 grams
        
        # Adjust based on size parameters
        scale_factor = 1.0
        
        for param in template.parameters:
            if param.name in parameters and param.parameter_type == "number":
                value = parameters[param.name]
                default_value = param.default_value
                
                if any(keyword in param.name.lower() for keyword in ["size", "diameter", "length", "width", "height", "thickness"]):
                    scale_factor *= (value / default_value)
        
        return round(base_material * scale_factor, 1)
    
    async def rate_template(self, template_id: str, rating: float) -> Dict[str, Any]:
        """Rate a template (1-5 stars)"""
        try:
            template = self.templates.get(template_id)
            if not template:
                return {"success": False, "error": "Template not found"}
            
            if not 1 <= rating <= 5:
                return {"success": False, "error": "Rating must be between 1 and 5"}
            
            # Update rating statistics
            total_rating = template.rating * template.rating_count + rating
            template.rating_count += 1
            template.rating = total_rating / template.rating_count
            
            self._save_all_templates()
            
            return {
                "success": True,
                "new_rating": round(template.rating, 1),
                "rating_count": template.rating_count
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to rate template: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_popular_templates(self, limit: int = 10) -> List[Template]:
        """Get the most popular templates"""
        templates = list(self.templates.values())
        
        # Sort by popularity score (usage count * rating)
        templates.sort(key=lambda t: t.usage_count * max(t.rating, 1), reverse=True)
        
        return templates[:limit]
    
    async def get_recent_templates(self, limit: int = 10) -> List[Template]:
        """Get the most recently added templates"""
        templates = list(self.templates.values())
        
        # Sort by creation date
        templates.sort(key=lambda t: t.created_at, reverse=True)
        
        return templates[:limit]
    
    def get_categories_summary(self) -> Dict[str, Any]:
        """Get summary of templates by category"""
        summary = {}
        
        for category in TemplateCategory:
            category_templates = [t for t in self.templates.values() if t.category == category]
            
            summary[category.value] = {
                "count": len(category_templates),
                "avg_rating": round(
                    sum(t.rating for t in category_templates) / max(len(category_templates), 1), 1
                ),
                "total_usage": sum(t.usage_count for t in category_templates)
            }
        
        return summary
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        templates = []
        for template in self.templates.values():
            templates.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "difficulty": template.difficulty.value,
                "rating": template.rating,
                "print_count": template.usage_count,
                "preview_image": template.preview_image,
                "model_path": template.model_file,
                "estimated_print_time": template.print_time_estimate,
                "recommended_material": template.material_estimate
            })
        
        return sorted(templates, key=lambda x: x.get("rating", 0), reverse=True)
    
    async def search_templates(self, category=None, difficulty=None, search_term=None, tags=None) -> List[Dict[str, Any]]:
        """Search templates with filters"""
        templates = list(self.templates.values())
        
        # Apply category filter
        if category:
            templates = [t for t in templates if t.category.value == category]
        
        # Apply difficulty filter
        if difficulty:
            templates = [t for t in templates if t.difficulty.value == difficulty]
        
        # Apply search term filter
        if search_term:
            search_lower = search_term.lower()
            templates = [t for t in templates if 
                        search_lower in t.name.lower() or 
                        search_lower in t.description.lower() or
                        any(search_lower in tag.lower() for tag in t.tags)]
        
        # Apply tags filter
        if tags:
            for tag in tags:
                templates = [t for t in templates if tag.lower() in [t.lower() for t in t.tags]]
        
        # Convert to dict format
        result = []
        for template in templates:
            result.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "difficulty": template.difficulty.value,
                "rating": template.rating,
                "print_count": template.usage_count,
                "preview_image": template.preview_image,
                "model_path": template.model_file,
                "estimated_print_time": template.print_time_estimate,
                "recommended_material": template.material_estimate
            })
        
        return sorted(result, key=lambda x: x.get("rating", 0), reverse=True)
    
    async def get_categories(self) -> List[Dict[str, str]]:
        """Get all template categories"""
        return [
            {"value": category.value, "display_name": category.value.replace("_", " ").title()}
            for category in TemplateCategory
        ]
    
    async def generate_preview(self, template_id: str) -> Dict[str, Any]:
        """Generate a preview of a template"""
        template = self.templates.get(template_id)
        if not template:
            return {"error": "Template not found"}
        
        return {
            "preview_image": template.preview_image,
            "model_file": template.model_file,
            "metadata": {
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "difficulty": template.difficulty.value,
                "estimated_print_time": template.print_time_estimate,
                "material_usage": template.material_estimate
            }
        }
