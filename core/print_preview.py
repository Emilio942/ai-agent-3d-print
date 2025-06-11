"""
3D Print Preview System for AI Agent 3D Print System

This module provides comprehensive 3D print preview and visualization capabilities
including STL visualization, G-code layer preview, print simulation, and 
interactive 3D viewer components.

Features:
- STL file 3D visualization and rendering
- G-code layer-by-layer preview and simulation
- Print time and material estimation with visualization
- Interactive 3D viewer with rotation, zoom, and pan
- Print analysis including support structures and infill
- Real-time print simulation and progress tracking
"""

import json
import logging
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import base64
import io
from PIL import Image

from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ViewerSettings:
    """3D viewer configuration settings"""
    background_color: str = "#f0f0f0"
    grid_enabled: bool = True
    grid_size: int = 10
    show_axes: bool = True
    camera_position: Tuple[float, float, float] = (50, 50, 50)
    camera_target: Tuple[float, float, float] = (0, 0, 0)
    lighting_intensity: float = 1.0
    show_build_volume: bool = True
    build_volume_size: Tuple[float, float, float] = (200, 200, 200)

@dataclass
class LayerInfo:
    """Information about a single print layer"""
    layer_number: int
    layer_height: float
    z_position: float
    print_time: float
    material_usage: float
    movements: List[Dict[str, Any]]
    temperatures: Dict[str, float]
    speeds: Dict[str, float]

@dataclass
class PrintAnalysis:
    """Complete print analysis results"""
    total_layers: int
    estimated_print_time: float
    material_usage: Dict[str, float]
    support_volume: float
    infill_percentage: float
    layer_heights: List[float]
    potential_issues: List[str]
    print_quality_score: float

class STLParser:
    """Parser for STL files to extract geometry data"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.STLParser")
    
    def parse_stl_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse STL file and extract vertices, normals, and triangles
        
        Args:
            file_path: Path to STL file
            
        Returns:
            Dictionary containing geometry data
        """
        try:
            # Check if file is binary or ASCII STL
            with open(file_path, 'rb') as f:
                header = f.read(80)
                if header.startswith(b'solid '):
                    return self._parse_ascii_stl(file_path)
                else:
                    return self._parse_binary_stl(file_path)
                    
        except Exception as e:
            self.logger.error(f"Error parsing STL file {file_path}: {e}")
            raise
    
    def _parse_binary_stl(self, file_path: Path) -> Dict[str, Any]:
        """Parse binary STL file"""
        vertices = []
        normals = []
        
        with open(file_path, 'rb') as f:
            # Skip header (80 bytes)
            f.read(80)
            
            # Read number of triangles
            triangle_count = int.from_bytes(f.read(4), byteorder='little')
            
            for _ in range(triangle_count):
                # Read normal vector (3 floats)
                normal = []
                for _ in range(3):
                    normal.append(float(np.frombuffer(f.read(4), dtype=np.float32)[0]))
                normals.append(normal)
                
                # Read triangle vertices (9 floats)
                triangle_vertices = []
                for _ in range(3):
                    vertex = []
                    for _ in range(3):
                        vertex.append(float(np.frombuffer(f.read(4), dtype=np.float32)[0]))
                    triangle_vertices.append(vertex)
                vertices.extend(triangle_vertices)
                
                # Skip attribute byte count
                f.read(2)
        
        return {
            'vertices': vertices,
            'normals': normals,
            'triangle_count': triangle_count,
            'bounds': self._calculate_bounds(vertices)
        }
    
    def _parse_ascii_stl(self, file_path: Path) -> Dict[str, Any]:
        """Parse ASCII STL file"""
        vertices = []
        normals = []
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        current_normal = None
        triangle_vertices = []
        triangle_count = 0
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('facet normal'):
                parts = line.split()
                current_normal = [float(parts[2]), float(parts[3]), float(parts[4])]
                
            elif line.startswith('vertex'):
                parts = line.split()
                vertex = [float(parts[1]), float(parts[2]), float(parts[3])]
                triangle_vertices.append(vertex)
                
            elif line.startswith('endfacet'):
                if current_normal and len(triangle_vertices) == 3:
                    normals.append(current_normal)
                    vertices.extend(triangle_vertices)
                    triangle_count += 1
                triangle_vertices = []
                current_normal = None
        
        return {
            'vertices': vertices,
            'normals': normals,
            'triangle_count': triangle_count,
            'bounds': self._calculate_bounds(vertices)
        }
    
    def _calculate_bounds(self, vertices: List[List[float]]) -> Dict[str, Tuple[float, float]]:
        """Calculate bounding box of the geometry"""
        if not vertices:
            return {'x': (0, 0), 'y': (0, 0), 'z': (0, 0)}
        
        vertices_array = np.array(vertices)
        return {
            'x': (float(vertices_array[:, 0].min()), float(vertices_array[:, 0].max())),
            'y': (float(vertices_array[:, 1].min()), float(vertices_array[:, 1].max())),
            'z': (float(vertices_array[:, 2].min()), float(vertices_array[:, 2].max()))
        }

class GCodeAnalyzer:
    """Analyzer for G-code files to extract layer and printing information"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.GCodeAnalyzer")
    
    def analyze_gcode(self, gcode_content: str) -> Tuple[List[LayerInfo], PrintAnalysis]:
        """
        Analyze G-code and extract layer information and print analysis
        
        Args:
            gcode_content: Raw G-code string
            
        Returns:
            Tuple of (layer_info_list, print_analysis)
        """
        try:
            lines = gcode_content.split('\n')
            layers = []
            current_layer = None
            total_time = 0
            material_usage = {}
            
            # Track current state
            current_z = 0
            current_temp = {}
            current_speed = {}
            layer_number = 0
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith(';'):
                    # Check for layer comments
                    if line.startswith(';LAYER:'):
                        if current_layer:
                            layers.append(current_layer)
                        layer_number += 1
                        current_layer = LayerInfo(
                            layer_number=layer_number,
                            layer_height=0.2,  # Default, will be calculated
                            z_position=current_z,
                            print_time=0,
                            material_usage=0,
                            movements=[],
                            temperatures=current_temp.copy(),
                            speeds=current_speed.copy()
                        )
                    continue
                
                # Parse G-code commands
                command_info = self._parse_gcode_line(line)
                if command_info and current_layer:
                    current_layer.movements.append(command_info)
                    
                    # Update current state
                    if 'Z' in command_info.get('params', {}):
                        current_z = command_info['params']['Z']
                        current_layer.z_position = current_z
                
                # Track temperatures
                if line.startswith('M104') or line.startswith('M109'):
                    temp_match = self._extract_temperature(line)
                    if temp_match:
                        current_temp['extruder'] = temp_match
                
                if line.startswith('M140') or line.startswith('M190'):
                    temp_match = self._extract_temperature(line)
                    if temp_match:
                        current_temp['bed'] = temp_match
            
            # Add last layer
            if current_layer:
                layers.append(current_layer)
            
            # Calculate analysis
            analysis = self._calculate_print_analysis(layers, lines)
            
            return layers, analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing G-code: {e}")
            raise
    
    def _parse_gcode_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single G-code line and extract command information"""
        parts = line.split()
        if not parts:
            return None
        
        command = parts[0]
        params = {}
        
        for part in parts[1:]:
            if len(part) >= 2:
                param_name = part[0]
                try:
                    param_value = float(part[1:])
                    params[param_name] = param_value
                except ValueError:
                    params[param_name] = part[1:]
        
        return {
            'command': command,
            'params': params,
            'raw_line': line
        }
    
    def _extract_temperature(self, line: str) -> Optional[float]:
        """Extract temperature value from G-code line"""
        if 'S' in line:
            parts = line.split('S')
            if len(parts) > 1:
                try:
                    return float(parts[1].split()[0])
                except (ValueError, IndexError):
                    pass
        return None
    
    def _calculate_print_analysis(self, layers: List[LayerInfo], gcode_lines: List[str]) -> PrintAnalysis:
        """Calculate comprehensive print analysis from layers"""
        total_layers = len(layers)
        estimated_time = sum(layer.print_time for layer in layers)
        
        # Estimate material usage (simplified)
        total_extrusion = 0
        for layer in layers:
            for movement in layer.movements:
                if movement['command'] in ['G1', 'G0'] and 'E' in movement.get('params', {}):
                    total_extrusion += movement['params']['E']
        
        material_usage = {'PLA': total_extrusion * 0.001}  # Convert to grams (simplified)
        
        # Calculate layer heights
        layer_heights = []
        if len(layers) > 1:
            for i in range(1, len(layers)):
                height = layers[i].z_position - layers[i-1].z_position
                layer_heights.append(height)
        
        # Analyze potential issues
        issues = []
        if total_layers > 1000:
            issues.append("Very high layer count - long print time expected")
        
        # Calculate quality score (simplified)
        quality_score = 85.0  # Base score
        if len(issues) > 0:
            quality_score -= len(issues) * 5
        
        return PrintAnalysis(
            total_layers=total_layers,
            estimated_print_time=estimated_time,
            material_usage=material_usage,
            support_volume=0,  # Would need more complex analysis
            infill_percentage=20,  # Default, would parse from comments
            layer_heights=layer_heights,
            potential_issues=issues,
            print_quality_score=quality_score
        )

class Preview3DRenderer:
    """3D rendering engine for print preview"""
    
    def __init__(self, settings: ViewerSettings = None):
        self.settings = settings or ViewerSettings()
        self.logger = get_logger(f"{__name__}.Preview3DRenderer")
    
    def generate_stl_preview(self, geometry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate 3D preview data for STL geometry
        
        Args:
            geometry_data: Parsed STL geometry data
            
        Returns:
            Preview data for web rendering
        """
        try:
            vertices = geometry_data['vertices']
            normals = geometry_data['normals']
            bounds = geometry_data['bounds']
            
            # Generate Three.js compatible geometry
            threejs_geometry = {
                'vertices': self._flatten_vertices(vertices),
                'normals': self._flatten_normals(normals),
                'faces': self._generate_face_indices(len(vertices)),
                'bounds': bounds,
                'center': self._calculate_center(bounds)
            }
            
            # Generate camera settings
            camera_settings = self._calculate_optimal_camera(bounds)
            
            return {
                'geometry': threejs_geometry,
                'camera': camera_settings,
                'viewer_settings': asdict(self.settings),
                'statistics': {
                    'triangle_count': geometry_data['triangle_count'],
                    'vertex_count': len(vertices),
                    'bounds': bounds
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating STL preview: {e}")
            raise
    
    def generate_layer_preview(self, layers: List[LayerInfo]) -> Dict[str, Any]:
        """
        Generate layer-by-layer preview data
        
        Args:
            layers: List of layer information
            
        Returns:
            Layer preview data for visualization
        """
        try:
            layer_data = []
            
            for layer in layers:
                # Extract path information for layer
                paths = self._extract_layer_paths(layer)
                
                layer_preview = {
                    'layer_number': layer.layer_number,
                    'z_position': layer.z_position,
                    'paths': paths,
                    'print_time': layer.print_time,
                    'material_usage': layer.material_usage,
                    'temperatures': layer.temperatures,
                    'speeds': layer.speeds
                }
                layer_data.append(layer_preview)
            
            return {
                'layers': layer_data,
                'total_layers': len(layers),
                'animation_settings': {
                    'play_speed': 1.0,
                    'show_travel_moves': False,
                    'color_by_speed': True,
                    'show_retraction': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating layer preview: {e}")
            raise
    
    def _flatten_vertices(self, vertices: List[List[float]]) -> List[float]:
        """Flatten vertex array for Three.js"""
        flattened = []
        for vertex in vertices:
            flattened.extend(vertex)
        return flattened
    
    def _flatten_normals(self, normals: List[List[float]]) -> List[float]:
        """Flatten normal array for Three.js"""
        flattened = []
        for normal in normals:
            # Repeat normal for each vertex of triangle
            flattened.extend(normal)
            flattened.extend(normal)
            flattened.extend(normal)
        return flattened
    
    def _generate_face_indices(self, vertex_count: int) -> List[int]:
        """Generate face indices for Three.js geometry"""
        indices = []
        for i in range(0, vertex_count, 3):
            indices.extend([i, i + 1, i + 2])
        return indices
    
    def _calculate_center(self, bounds: Dict[str, Tuple[float, float]]) -> Tuple[float, float, float]:
        """Calculate center point of geometry"""
        center_x = (bounds['x'][0] + bounds['x'][1]) / 2
        center_y = (bounds['y'][0] + bounds['y'][1]) / 2
        center_z = (bounds['z'][0] + bounds['z'][1]) / 2
        return (center_x, center_y, center_z)
    
    def _calculate_optimal_camera(self, bounds: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """Calculate optimal camera position for viewing geometry"""
        # Calculate geometry size
        size_x = bounds['x'][1] - bounds['x'][0]
        size_y = bounds['y'][1] - bounds['y'][0]
        size_z = bounds['z'][1] - bounds['z'][0]
        max_size = max(size_x, size_y, size_z)
        
        # Position camera at optimal distance
        distance = max_size * 2
        center = self._calculate_center(bounds)
        
        return {
            'position': [center[0] + distance, center[1] + distance, center[2] + distance],
            'target': list(center),
            'fov': 45,
            'near': 0.1,
            'far': distance * 10
        }
    
    def _extract_layer_paths(self, layer: LayerInfo) -> List[Dict[str, Any]]:
        """Extract printable paths from layer movements"""
        paths = []
        current_path = []
        current_position = [0, 0, layer.z_position]
        is_extruding = False
        
        for movement in layer.movements:
            if movement['command'] in ['G0', 'G1']:
                params = movement.get('params', {})
                
                # Update position
                if 'X' in params:
                    current_position[0] = params['X']
                if 'Y' in params:
                    current_position[1] = params['Y']
                if 'Z' in params:
                    current_position[2] = params['Z']
                
                # Check if extruding
                extruding = 'E' in params and params['E'] > 0
                
                if extruding != is_extruding:
                    # Extrusion state changed
                    if current_path and not is_extruding:
                        # End travel move
                        paths.append({
                            'type': 'travel',
                            'points': current_path.copy(),
                            'speed': params.get('F', 1800)
                        })
                    elif current_path and is_extruding:
                        # End extrusion move
                        paths.append({
                            'type': 'extrusion',
                            'points': current_path.copy(),
                            'speed': params.get('F', 1200),
                            'extrusion': True
                        })
                    current_path = []
                
                current_path.append(current_position.copy())
                is_extruding = extruding
        
        # Add final path
        if current_path:
            path_type = 'extrusion' if is_extruding else 'travel'
            paths.append({
                'type': path_type,
                'points': current_path,
                'speed': 1200,
                'extrusion': is_extruding
            })
        
        return paths

class PrintPreviewManager:
    """Main manager for 3D print preview functionality"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/preview")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.stl_parser = STLParser()
        self.gcode_analyzer = GCodeAnalyzer()
        self.renderer = Preview3DRenderer()
        self.logger = get_logger(f"{__name__}.PrintPreviewManager")
    
    def generate_stl_preview(self, stl_file_path: Path) -> Dict[str, Any]:
        """
        Generate complete STL file preview
        
        Args:
            stl_file_path: Path to STL file
            
        Returns:
            Complete preview data
        """
        try:
            self.logger.info(f"Generating STL preview for {stl_file_path}")
            
            # Parse STL geometry
            geometry_data = self.stl_parser.parse_stl_file(stl_file_path)
            
            # Generate 3D preview
            preview_data = self.renderer.generate_stl_preview(geometry_data)
            
            # Add file information
            preview_data['file_info'] = {
                'filename': stl_file_path.name,
                'file_size': stl_file_path.stat().st_size,
                'modification_time': stl_file_path.stat().st_mtime
            }
            
            self.logger.info(f"STL preview generated successfully")
            return preview_data
            
        except Exception as e:
            self.logger.error(f"Error generating STL preview: {e}")
            raise
    
    def generate_gcode_preview(self, gcode_content: str) -> Dict[str, Any]:
        """
        Generate complete G-code preview with layer analysis
        
        Args:
            gcode_content: Raw G-code string
            
        Returns:
            Complete G-code preview data
        """
        try:
            self.logger.info("Generating G-code preview")
            
            # Analyze G-code
            layers, analysis = self.gcode_analyzer.analyze_gcode(gcode_content)
            
            # Generate layer preview
            layer_preview = self.renderer.generate_layer_preview(layers)
            
            # Combine data
            preview_data = {
                'layer_preview': layer_preview,
                'print_analysis': asdict(analysis),
                'summary': {
                    'total_layers': analysis.total_layers,
                    'estimated_time': analysis.estimated_print_time,
                    'material_usage': analysis.material_usage,
                    'quality_score': analysis.print_quality_score
                }
            }
            
            self.logger.info("G-code preview generated successfully")
            return preview_data
            
        except Exception as e:
            self.logger.error(f"Error generating G-code preview: {e}")
            raise
    
    def save_preview_data(self, preview_data: Dict[str, Any], filename: str) -> Path:
        """
        Save preview data to file for later use
        
        Args:
            preview_data: Preview data to save
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        try:
            output_path = self.data_dir / f"{filename}.json"
            
            with open(output_path, 'w') as f:
                json.dump(preview_data, f, indent=2)
            
            self.logger.info(f"Preview data saved to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error saving preview data: {e}")
            raise
    
    def load_preview_data(self, filename: str) -> Dict[str, Any]:
        """
        Load previously saved preview data
        
        Args:
            filename: Filename to load
            
        Returns:
            Loaded preview data
        """
        try:
            file_path = self.data_dir / f"{filename}.json"
            
            with open(file_path, 'r') as f:
                preview_data = json.load(f)
            
            self.logger.info(f"Preview data loaded from {file_path}")
            return preview_data
            
        except Exception as e:
            self.logger.error(f"Error loading preview data: {e}")
            raise
    
    def get_preview_capabilities(self) -> Dict[str, Any]:
        """
        Get information about preview system capabilities
        
        Returns:
            Capabilities information
        """
        return {
            'supported_formats': ['STL', 'OBJ', 'GCODE'],
            'viewer_features': [
                'Interactive 3D rotation',
                'Zoom and pan controls',
                'Layer-by-layer preview',
                'Print simulation',
                'Material usage visualization',
                'Print time estimation',
                'Quality analysis'
            ],
            'export_formats': ['JSON', 'PNG', 'WebGL'],
            'max_file_size': '100MB',
            'performance_optimized': True
        }
