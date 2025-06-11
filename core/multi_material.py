"""
Multi-Material Support System for AI Agent 3D Print System

This module provides comprehensive multi-material and multi-color 3D printing
capabilities including material management, compatibility checking, and 
multi-tool G-code generation.

Features:
- Material profile management with properties and compatibility
- Multi-color/multi-material design specification
- Automatic tool change G-code generation
- Material compatibility validation
- Print optimization for multiple materials
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import sqlite3
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)

class MaterialType(Enum):
    """Material type classification"""
    PLA = "PLA"
    ABS = "ABS"  
    PETG = "PETG"
    TPU = "TPU"
    PVA = "PVA"  # Water soluble support material
    HIPS = "HIPS"
    WOOD_FILL = "WOOD_FILL"
    METAL_FILL = "METAL_FILL"
    CARBON_FIBER = "CARBON_FIBER"
    CUSTOM = "CUSTOM"

class PrintQuality(Enum):
    """Print quality levels"""
    DRAFT = "draft"
    NORMAL = "normal"
    HIGH = "high"
    ULTRA = "ultra"

@dataclass
class MaterialProperties:
    """Material properties for printing optimization"""
    # Temperature settings
    nozzle_temp: int
    bed_temp: int
    chamber_temp: Optional[int] = None
    
    # Physical properties
    density: float  # g/cm³
    diameter: float = 1.75  # mm
    
    # Print settings
    print_speed: int = 50  # mm/s
    retraction_distance: float = 6.5  # mm
    retraction_speed: int = 25  # mm/s
    
    # Advanced properties
    requires_enclosure: bool = False
    requires_heated_bed: bool = True
    supports_overhang: bool = True
    water_soluble: bool = False
    
    # Color and appearance
    color: str = "natural"
    transparency: float = 0.0  # 0.0 = opaque, 1.0 = transparent
    surface_finish: str = "matte"  # matte, glossy, textured
    
    # Compatibility notes
    compatibility_notes: Optional[str] = None
    special_requirements: List[str] = None

    def __post_init__(self):
        if self.special_requirements is None:
            self.special_requirements = []

@dataclass
class Material:
    """Complete material definition"""
    id: str
    name: str
    type: MaterialType
    brand: str
    properties: MaterialProperties
    description: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'brand': self.brand,
            'properties': asdict(self.properties),
            'description': self.description,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Material':
        """Create from dictionary"""
        properties_data = data['properties']
        properties = MaterialProperties(**properties_data)
        
        return cls(
            id=data['id'],
            name=data['name'],
            type=MaterialType(data['type']),
            brand=data['brand'],
            properties=properties,
            description=data.get('description'),
            created_at=data.get('created_at')
        )

class MaterialDatabase:
    """Material database management"""
    
    def __init__(self, db_path: str = "data/materials.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._populate_default_materials()
    
    def _init_database(self):
        """Initialize the materials database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material_compatibility (
                    material1_id TEXT,
                    material2_id TEXT,
                    compatible BOOLEAN,
                    notes TEXT,
                    PRIMARY KEY (material1_id, material2_id),
                    FOREIGN KEY (material1_id) REFERENCES materials (id),
                    FOREIGN KEY (material2_id) REFERENCES materials (id)
                )
            ''')
            conn.commit()
    
    def add_material(self, material: Material) -> bool:
        """Add a new material to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO materials (id, name, type, brand, properties, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    material.id,
                    material.name,
                    material.type.value,
                    material.brand,
                    json.dumps(asdict(material.properties)),
                    material.description
                ))
                conn.commit()
                logger.info(f"Added material: {material.name} ({material.id})")
                return True
        except Exception as e:
            logger.error(f"Failed to add material {material.id}: {e}")
            return False
    
    def get_material(self, material_id: str) -> Optional[Material]:
        """Get material by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, type, brand, properties, description, created_at
                    FROM materials WHERE id = ?
                ''', (material_id,))
                
                row = cursor.fetchone()
                if row:
                    id, name, type_str, brand, properties_json, description, created_at = row
                    properties = MaterialProperties(**json.loads(properties_json))
                    
                    return Material(
                        id=id,
                        name=name,
                        type=MaterialType(type_str),
                        brand=brand,
                        properties=properties,
                        description=description,
                        created_at=created_at
                    )
        except Exception as e:
            logger.error(f"Failed to get material {material_id}: {e}")
        return None
    
    def list_materials(self, material_type: Optional[MaterialType] = None) -> List[Material]:
        """List all materials or by type"""
        materials = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if material_type:
                    cursor.execute('''
                        SELECT id, name, type, brand, properties, description, created_at
                        FROM materials WHERE type = ?
                        ORDER BY name
                    ''', (material_type.value,))
                else:
                    cursor.execute('''
                        SELECT id, name, type, brand, properties, description, created_at
                        FROM materials ORDER BY name
                    ''')
                
                for row in cursor.fetchall():
                    id, name, type_str, brand, properties_json, description, created_at = row
                    properties = MaterialProperties(**json.loads(properties_json))
                    
                    material = Material(
                        id=id,
                        name=name,
                        type=MaterialType(type_str),
                        brand=brand,
                        properties=properties,
                        description=description,
                        created_at=created_at
                    )
                    materials.append(material)
                    
        except Exception as e:
            logger.error(f"Failed to list materials: {e}")
        
        return materials
    
    def check_compatibility(self, material1_id: str, material2_id: str) -> Tuple[bool, str]:
        """Check if two materials are compatible for multi-material printing"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT compatible, notes FROM material_compatibility
                    WHERE (material1_id = ? AND material2_id = ?)
                       OR (material1_id = ? AND material2_id = ?)
                ''', (material1_id, material2_id, material2_id, material1_id))
                
                row = cursor.fetchone()
                if row:
                    return row[0], row[1] or "Compatibility data available"
                
                # If no explicit compatibility data, check basic compatibility
                material1 = self.get_material(material1_id)
                material2 = self.get_material(material2_id)
                
                if material1 and material2:
                    return self._check_basic_compatibility(material1, material2)
                
        except Exception as e:
            logger.error(f"Failed to check compatibility: {e}")
        
        return False, "Unable to determine compatibility"
    
    def _check_basic_compatibility(self, material1: Material, material2: Material) -> Tuple[bool, str]:
        """Basic compatibility checking based on material properties"""
        # Temperature compatibility (within 20°C)
        temp_diff = abs(material1.properties.nozzle_temp - material2.properties.nozzle_temp)
        if temp_diff > 20:
            return False, f"Temperature incompatible: {temp_diff}°C difference"
        
        # Bed temperature compatibility  
        bed_temp_diff = abs(material1.properties.bed_temp - material2.properties.bed_temp)
        if bed_temp_diff > 15:
            return False, f"Bed temperature incompatible: {bed_temp_diff}°C difference"
        
        # Special material combinations
        if material1.properties.water_soluble or material2.properties.water_soluble:
            return True, "Water-soluble support material - good combination"
        
        # Same type materials are usually compatible
        if material1.type == material2.type:
            return True, "Same material type - compatible"
        
        # Known compatible combinations
        compatible_pairs = [
            (MaterialType.PLA, MaterialType.PVA),
            (MaterialType.ABS, MaterialType.HIPS),
            (MaterialType.PETG, MaterialType.PLA),
        ]
        
        material_pair = (material1.type, material2.type)
        reverse_pair = (material2.type, material1.type)
        
        if material_pair in compatible_pairs or reverse_pair in compatible_pairs:
            return True, "Known compatible material combination"
        
        return True, "Likely compatible - test recommended"
    
    def _populate_default_materials(self):
        """Populate database with default material profiles"""
        default_materials = [
            Material(
                id="pla_standard",
                name="Standard PLA",
                type=MaterialType.PLA,
                brand="Generic",
                properties=MaterialProperties(
                    nozzle_temp=210,
                    bed_temp=60,
                    density=1.24,
                    print_speed=60,
                    retraction_distance=6.5,
                    retraction_speed=25,
                    requires_enclosure=False,
                    requires_heated_bed=True,
                    color="natural"
                ),
                description="Standard PLA filament for general purpose printing"
            ),
            Material(
                id="abs_standard",
                name="Standard ABS",
                type=MaterialType.ABS,
                brand="Generic",
                properties=MaterialProperties(
                    nozzle_temp=250,
                    bed_temp=100,
                    chamber_temp=60,
                    density=1.04,
                    print_speed=50,
                    retraction_distance=4.0,
                    retraction_speed=30,
                    requires_enclosure=True,
                    requires_heated_bed=True,
                    color="natural"
                ),
                description="Standard ABS filament for durable prints"
            ),
            Material(
                id="pva_support",
                name="PVA Support Material",
                type=MaterialType.PVA,
                brand="Generic",
                properties=MaterialProperties(
                    nozzle_temp=215,
                    bed_temp=60,
                    density=1.23,
                    print_speed=30,
                    retraction_distance=7.0,
                    retraction_speed=20,
                    requires_enclosure=False,
                    requires_heated_bed=True,
                    water_soluble=True,
                    color="natural",
                    special_requirements=["Store in dry environment", "Use with PLA or PETG"]
                ),
                description="Water-soluble support material for complex geometries"
            ),
            Material(
                id="petg_clear",
                name="Clear PETG",
                type=MaterialType.PETG,
                brand="Generic",
                properties=MaterialProperties(
                    nozzle_temp=230,
                    bed_temp=80,
                    density=1.27,
                    print_speed=45,
                    retraction_distance=5.0,
                    retraction_speed=35,
                    requires_enclosure=False,
                    requires_heated_bed=True,
                    transparency=0.8,
                    surface_finish="glossy",
                    color="clear"
                ),
                description="Crystal clear PETG for transparent parts"
            ),
            Material(
                id="tpu_flexible",
                name="Flexible TPU",
                type=MaterialType.TPU,
                brand="Generic",
                properties=MaterialProperties(
                    nozzle_temp=220,
                    bed_temp=50,
                    density=1.20,
                    print_speed=20,
                    retraction_distance=2.0,
                    retraction_speed=15,
                    requires_enclosure=False,
                    requires_heated_bed=False,
                    supports_overhang=False,
                    color="natural",
                    special_requirements=["Print slowly", "Reduce retraction", "Direct drive extruder recommended"]
                ),
                description="Flexible TPU for gaskets and flexible parts"
            )
        ]
        
        # Check if materials already exist
        existing_materials = self.list_materials()
        existing_ids = {mat.id for mat in existing_materials}
        
        for material in default_materials:
            if material.id not in existing_ids:
                self.add_material(material)

class MultiMaterialManager:
    """Multi-material printing management system"""
    
    def __init__(self):
        self.material_db = MaterialDatabase()
        self.logger = get_logger(__name__)
    
    def validate_material_combination(self, material_ids: List[str]) -> Tuple[bool, List[str]]:
        """Validate a combination of materials for multi-material printing"""
        if len(material_ids) < 2:
            return True, ["Single material - no compatibility issues"]
        
        issues = []
        all_compatible = True
        
        # Check pairwise compatibility
        for i in range(len(material_ids)):
            for j in range(i + 1, len(material_ids)):
                compatible, note = self.material_db.check_compatibility(
                    material_ids[i], material_ids[j]
                )
                if not compatible:
                    all_compatible = False
                    material1 = self.material_db.get_material(material_ids[i])
                    material2 = self.material_db.get_material(material_ids[j])
                    issues.append(f"{material1.name} + {material2.name}: {note}")
                else:
                    self.logger.info(f"Materials {material_ids[i]} + {material_ids[j]}: {note}")
        
        if all_compatible:
            issues.append("All materials are compatible for multi-material printing")
        
        return all_compatible, issues
    
    def generate_tool_change_gcode(self, 
                                  from_material_id: str, 
                                  to_material_id: str,
                                  layer_height: float = 0.2) -> str:
        """Generate G-code for tool change between materials"""
        from_material = self.material_db.get_material(from_material_id)
        to_material = self.material_db.get_material(to_material_id)
        
        if not from_material or not to_material:
            raise ValueError("Invalid material IDs provided")
        
        gcode_lines = []
        
        # Tool change sequence
        gcode_lines.extend([
            "; Tool change sequence",
            f"; From: {from_material.name} to {to_material.name}",
            "",
            "; Retract current material",
            "G1 E-15 F3600  ; Retract filament",
            "",
            "; Move to purge area",
            "G1 X250 Y10 F9000  ; Move to purge area",
            "G1 Z+5 F3000  ; Lift nozzle",
            "",
            f"; Heat nozzle for new material",
            f"M104 S{to_material.properties.nozzle_temp}  ; Set nozzle temperature",
            f"M109 S{to_material.properties.nozzle_temp}  ; Wait for temperature",
            "",
        ])
        
        # Material-specific purge sequence
        if from_material.type != to_material.type:
            purge_amount = 50  # mm of filament
            if to_material.type == MaterialType.PVA:
                purge_amount = 30  # Less purge for support material
            elif from_material.type == MaterialType.ABS and to_material.type == MaterialType.PLA:
                purge_amount = 80  # More purge when going from high to low temp
            
            gcode_lines.extend([
                "; Purge sequence for material change",
                f"G1 E{purge_amount} F300  ; Purge old material",
                "G1 E-5 F3600  ; Small retraction",
                "",
                "; Clean nozzle (move across purge area)",
                "G1 X240 Y20 F3000",
                "G1 X250 Y20 F3000",
                "G1 X240 Y30 F3000",
                "",
            ])
        else:
            # Same material type, minimal purge
            gcode_lines.extend([
                "; Minimal purge for same material type",
                "G1 E10 F300  ; Small purge",
                "",
            ])
        
        # Prime nozzle for new material
        gcode_lines.extend([
            "; Prime nozzle with new material",
            "G1 E10 F300  ; Prime nozzle",
            "G1 E-2 F3600  ; Small retraction",
            "",
            "; Resume printing position",
            "G1 Z-5 F3000  ; Lower nozzle to previous height",
            "; End tool change sequence",
            ""
        ])
        
        return "\n".join(gcode_lines)
    
    def optimize_print_sequence(self, 
                               design_parts: List[Dict[str, Any]], 
                               materials: List[str]) -> Dict[str, Any]:
        """Optimize print sequence for multi-material objects"""
        optimization_plan = {
            "sequence": [],
            "tool_changes": 0,
            "estimated_time_increase": 0,
            "recommendations": []
        }
        
        # Simple optimization: group by material to minimize tool changes
        material_groups = {}
        for part in design_parts:
            material_id = part.get('material_id', materials[0])
            if material_id not in material_groups:
                material_groups[material_id] = []
            material_groups[material_id].append(part)
        
        # Create printing sequence
        current_material = None
        for material_id, parts in material_groups.items():
            if current_material and current_material != material_id:
                optimization_plan["tool_changes"] += 1
                optimization_plan["estimated_time_increase"] += 2  # 2 minutes per tool change
            
            optimization_plan["sequence"].append({
                "material_id": material_id,
                "material_name": self.material_db.get_material(material_id).name,
                "parts": len(parts),
                "layer_ranges": [p.get('layer_range', [0, 100]) for p in parts]
            })
            current_material = material_id
        
        # Add recommendations
        if optimization_plan["tool_changes"] > 5:
            optimization_plan["recommendations"].append(
                "Consider reducing material variety to minimize tool changes"
            )
        
        if len(materials) > 3:
            optimization_plan["recommendations"].append(
                "Multi-material prints with >3 materials may require longer print times"
            )
        
        # Check for support material optimization
        support_materials = [m for m in materials 
                           if self.material_db.get_material(m).properties.water_soluble]
        if support_materials:
            optimization_plan["recommendations"].append(
                "Water-soluble support material detected - excellent for complex geometries"
            )
        
        return optimization_plan
    
    def get_material_suggestions(self, design_requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get material suggestions based on design requirements"""
        suggestions = []
        
        # Analyze requirements
        requires_flexibility = design_requirements.get('flexible', False)
        requires_transparency = design_requirements.get('transparent', False)
        requires_strength = design_requirements.get('high_strength', False)
        requires_supports = design_requirements.get('complex_geometry', False)
        color_requirements = design_requirements.get('colors', [])
        
        # Get relevant materials
        all_materials = self.material_db.list_materials()
        
        for material in all_materials:
            score = 0
            reasons = []
            
            # Match requirements
            if requires_flexibility and material.type == MaterialType.TPU:
                score += 10
                reasons.append("Excellent flexibility")
            
            if requires_transparency and material.properties.transparency > 0.5:
                score += 8
                reasons.append("Good transparency")
            
            if requires_strength and material.type in [MaterialType.ABS, MaterialType.PETG]:
                score += 7
                reasons.append("High strength and durability")
            
            if requires_supports and material.properties.water_soluble:
                score += 9
                reasons.append("Water-soluble support material")
            
            # Color matching
            if color_requirements and material.properties.color in color_requirements:
                score += 5
                reasons.append(f"Matches required color: {material.properties.color}")
            
            # General usability
            if not material.properties.requires_enclosure:
                score += 2
                reasons.append("Easy to print")
            
            if score > 0:
                suggestions.append({
                    "material": material,
                    "score": score,
                    "reasons": reasons,
                    "compatibility_notes": material.properties.compatibility_notes or ""
                })
        
        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:10]  # Return top 10 suggestions

# Global instance
multi_material_manager = MultiMaterialManager()

def get_multi_material_manager() -> MultiMaterialManager:
    """Get the global multi-material manager instance"""
    return multi_material_manager
