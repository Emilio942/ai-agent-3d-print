"""
Image Processing Agent - Convert Images to 3D Models

This agent handles the conversion of 2D images to 3D printable models using
computer vision techniques including edge detection, contour extraction,
depth estimation, and 3D reconstruction.

Features:
- Image preprocessing and validation
- Edge detection and contour extraction
- 2D to 3D extrusion with customizable parameters
- Depth estimation using MiDaS/DPT models for volumetric 3D reconstruction
- Integration with CAD Agent for final model generation
- Support for various image formats (PNG, JPG, GIF)
"""

import cv2
import numpy as np
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image
import io
import base64
from datetime import datetime

# Depth estimation imports
try:
    import torch
    import torchvision.transforms as transforms
    from transformers import AutoImageProcessor, AutoModel
    import open3d as o3d
    DEPTH_ESTIMATION_AVAILABLE = True
except ImportError:
    DEPTH_ESTIMATION_AVAILABLE = False
    print("Warning: Depth estimation dependencies not available")

from core.base_agent import BaseAgent
from core.logger import get_logger
from core.exceptions import ValidationError, WorkflowError

class ImageProcessingAgent(BaseAgent):
    """Agent responsible for converting images to 3D models"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ImageProcessingAgent", config)
        self.logger = get_logger(__name__)
        
        # Default processing parameters
        self.default_params = {
            'max_image_size': (800, 800),
            'blur_kernel_size': 5,
            'canny_threshold1': 50,
            'canny_threshold2': 150,
            'min_contour_area': 100,
            'default_extrusion_height': 5.0,  # mm
            'base_thickness': 1.0,  # mm
            'scale_factor': 0.1,  # mm per pixel
            'smoothing_iterations': 2,
            # Enhanced CV parameters for Aufgabe 6
            'use_adaptive_threshold': True,
            'use_morphological_ops': True,
            'edge_detection_method': 'canny',  # 'canny', 'sobel', 'laplacian', 'auto'
            'enable_shape_recognition': True,
            'enable_multi_object_detection': True,
            'min_shape_confidence': 0.7,
            'morphology_kernel_size': 5,
            'adaptive_threshold_block_size': 11,
            'adaptive_threshold_c': 2,
            'enable_histogram_equalization': True,
            'enable_denoising': True,
            'contour_approximation_epsilon': 0.02,
            # Aufgabe 7: Depth Estimation parameters
            'enable_depth_estimation': True,
            'depth_model': 'dpt-large',  # 'dpt-large', 'dpt-hybrid', 'midas-v2'
            'depth_max_size': 384,  # Maximum input size for depth estimation
            'depth_threshold': 0.1,  # Minimum depth value for reconstruction
            'point_cloud_downsample': 0.005,  # Downsample factor for point cloud
            'mesh_reconstruction_method': 'delaunay',  # 'delaunay', 'poisson', 'alpha_shape'
            'enable_depth_smoothing': True,
            'depth_smoothing_sigma': 1.0,
            'min_depth_points': 1000,  # Minimum points for 3D reconstruction
            'depth_scale_factor': 10.0,  # Scale factor for depth values (mm)
            'use_depth_for_extrusion': False  # Whether to use depth for extrusion height
        }
        
        # Initialize depth estimation model
        self.depth_model = None
        self.depth_processor = None
        if DEPTH_ESTIMATION_AVAILABLE and self.default_params['enable_depth_estimation']:
            self._initialize_depth_model()
    
    def _initialize_depth_model(self):
        """Initialize depth estimation model (MiDaS/DPT)"""
        try:
            model_name = self.default_params['depth_model']
            
            if model_name == 'dpt-large':
                model_id = "Intel/dpt-large"
            elif model_name == 'dpt-hybrid':
                model_id = "Intel/dpt-hybrid-midas"
            elif model_name == 'midas-v2':
                model_id = "Intel/midas-v2"
            else:
                model_id = "Intel/dpt-large"  # Default
            
            self.logger.info(f"Loading depth estimation model: {model_id}")
            
            # Load the image processor and model
            self.depth_processor = AutoImageProcessor.from_pretrained(model_id)
            self.depth_model = AutoModel.from_pretrained(model_id)
            
            # Set to evaluation mode
            self.depth_model.eval()
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.depth_model = self.depth_model.cuda()
                self.logger.info("Depth model loaded on GPU")
            else:
                self.logger.info("Depth model loaded on CPU")
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize depth model: {e}")
            self.depth_model = None
            self.depth_processor = None

    async def process_image_to_3d(self, image_data: bytes, image_filename: str, 
                                 processing_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main method to convert an image to 3D model data
        
        Args:
            image_data: Raw image bytes
            image_filename: Original filename for reference
            processing_params: Custom processing parameters
            
        Returns:
            Dictionary containing 3D model data and metadata
        """
        try:
            self.logger.info(f"Starting image processing for: {image_filename}")
            
            # Merge parameters
            params = {**self.default_params, **(processing_params or {})}
            
            # Step 1: Load and preprocess image
            image_array = self._load_and_preprocess_image(image_data, params)
            
            # Step 2: Extract contours (traditional method)
            contours = self._extract_contours(image_array, params)
            
            # Step 3: Depth estimation (Aufgabe 7)
            depth_data = None
            if params.get('enable_depth_estimation', True) and self.depth_model is not None:
                depth_data = await self._estimate_depth(image_data, params)
            
            # Step 4: Generate 3D geometry (enhanced with depth if available)
            geometry_data = self._generate_3d_geometry(contours, image_array.shape, params, depth_data)
            
            # Step 5: Create mesh data for CAD Agent
            mesh_specification = self._create_mesh_specification(geometry_data, params)
            
            result = {
                'success': True,
                'processing_time': datetime.now().isoformat(),
                'original_image': {
                    'filename': image_filename,
                    'dimensions': image_array.shape[:2],
                    'processed_size': image_array.shape
                },
                'contours_found': len(contours),
                'geometry_data': geometry_data,
                'mesh_specification': mesh_specification,
                'processing_params': params,
                'depth_data': depth_data,  # Aufgabe 7: Include depth estimation results
                'processing_method': 'enhanced_cv_with_depth' if depth_data else 'enhanced_cv_pipeline',
                'cad_agent_input': {
                    'operation': 'create_from_contours',
                    'contours': geometry_data['contours_3d'],
                    'base_thickness': params['base_thickness'],
                    'extrusion_height': params['default_extrusion_height'],
                    'depth_data': depth_data  # Pass depth data to CAD agent
                }
            }
            
            self.logger.info(f"Image processing completed successfully. Found {len(contours)} contours.")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing image {image_filename}: {str(e)}")
            raise WorkflowError(f"Image processing failed: {str(e)}")
    
    def _load_and_preprocess_image(self, image_data: bytes, params: Dict[str, Any]) -> np.ndarray:
        """Load image from bytes and preprocess for advanced edge detection"""
        try:
            # Convert bytes to PIL Image
            image_pil = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')
            
            # Resize if too large
            max_size = params['max_image_size']
            if image_pil.size[0] > max_size[0] or image_pil.size[1] > max_size[1]:
                image_pil.thumbnail(max_size, Image.Resampling.LANCZOS)
                self.logger.info(f"Resized image to {image_pil.size}")
            
            # Convert to numpy array
            image_array = np.array(image_pil)
            
            # Convert to grayscale for edge detection
            if len(image_array.shape) == 3:
                image_gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                image_gray = image_array
            
            # Enhanced preprocessing for Aufgabe 6
            processed_image = self._apply_advanced_preprocessing(image_gray, params)
            
            return processed_image
            
        except Exception as e:
            raise ValidationError(f"Failed to load/preprocess image: {str(e)}")
    
    def _apply_advanced_preprocessing(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply advanced preprocessing techniques for better computer vision results"""
        try:
            processed = image.copy()
            
            # Step 1: Histogram equalization for better contrast
            if params.get('enable_histogram_equalization', True):
                processed = cv2.equalizeHist(processed)
                self.logger.debug("Applied histogram equalization")
            
            # Step 2: Denoising
            if params.get('enable_denoising', True):
                processed = cv2.fastNlMeansDenoising(processed, h=10, templateWindowSize=7, searchWindowSize=21)
                self.logger.debug("Applied denoising filter")
            
            # Step 3: Gaussian blur to reduce noise
            if params['blur_kernel_size'] > 1:
                processed = cv2.GaussianBlur(
                    processed, 
                    (params['blur_kernel_size'], params['blur_kernel_size']), 
                    0
                )
                self.logger.debug(f"Applied Gaussian blur with kernel size {params['blur_kernel_size']}")
            
            # Step 4: Morphological operations for better shape detection
            if params.get('use_morphological_ops', True):
                kernel_size = params.get('morphology_kernel_size', 5)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
                
                # Opening operation to remove noise
                processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
                # Closing operation to fill gaps
                processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
                self.logger.debug("Applied morphological operations")
            
            return processed
            
        except Exception as e:
            self.logger.warning(f"Advanced preprocessing failed, using basic preprocessing: {e}")
            # Fallback to basic preprocessing
            if params['blur_kernel_size'] > 1:
                return cv2.GaussianBlur(
                    image, 
                    (params['blur_kernel_size'], params['blur_kernel_size']), 
                    0
                )
            return image
    
    def _extract_contours(self, image: np.ndarray, params: Dict[str, Any]) -> List[np.ndarray]:
        """Extract contours using advanced edge detection and shape recognition"""
        try:
            # Apply advanced edge detection
            edges = self._apply_advanced_edge_detection(image, params)
            
            # Find contours with hierarchy for nested shape detection
            contours, hierarchy = cv2.findContours(
                edges, 
                cv2.RETR_TREE,  # Get hierarchy for nested shapes
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Advanced contour filtering and analysis
            filtered_contours = self._filter_and_analyze_contours(
                contours, hierarchy, params
            )
            
            # Shape recognition if enabled
            if params.get('enable_shape_recognition', True):
                filtered_contours = self._apply_shape_recognition(filtered_contours, params)
            
            # Multi-object detection if enabled
            if params.get('enable_multi_object_detection', True):
                filtered_contours = self._separate_overlapping_objects(filtered_contours, params)
            
            # Sort by area (largest first) and apply final filtering
            filtered_contours.sort(key=lambda x: x.get('area', cv2.contourArea(x.get('contour', []))), reverse=True)
            
            # Return enhanced data if shape recognition is enabled, otherwise maintain backward compatibility
            if params.get('enable_shape_recognition', True) or params.get('enable_multi_object_detection', True):
                # Return enhanced contour data with shape information
                self.logger.info(f"Advanced contour extraction: {len(filtered_contours)} objects detected with enhanced data")
                return filtered_contours
            else:
                # Extract just the contours for backward compatibility
                result_contours = []
                for item in filtered_contours:
                    if isinstance(item, dict) and 'contour' in item:
                        result_contours.append(item['contour'])
                    else:
                        result_contours.append(item)
                
                self.logger.info(f"Basic contour extraction: {len(result_contours)} objects detected")
                return result_contours
            
        except Exception as e:
            self.logger.warning(f"Advanced contour extraction failed, using fallback: {e}")
            return self._extract_contours_fallback(image, params)
    
    def _apply_advanced_edge_detection(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply advanced edge detection methods"""
        try:
            method = params.get('edge_detection_method', 'canny')
            
            if method == 'auto':
                # Automatically select best method based on image characteristics
                method = self._select_optimal_edge_method(image)
            
            if method == 'canny':
                # Standard Canny edge detection
                edges = cv2.Canny(
                    image,
                    params['canny_threshold1'],
                    params['canny_threshold2']
                )
            
            elif method == 'adaptive_canny':
                # Adaptive Canny with automatic threshold selection
                median = np.median(image)
                lower = int(max(0, 0.7 * median))
                upper = int(min(255, 1.3 * median))
                edges = cv2.Canny(image, lower, upper)
            
            elif method == 'sobel':
                # Sobel edge detection
                grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
                edges = np.sqrt(grad_x**2 + grad_y**2)
                edges = np.uint8(edges / edges.max() * 255)
                _, edges = cv2.threshold(edges, 50, 255, cv2.THRESH_BINARY)
            
            elif method == 'laplacian':
                # Laplacian edge detection
                laplacian = cv2.Laplacian(image, cv2.CV_64F)
                edges = np.uint8(np.absolute(laplacian))
                _, edges = cv2.threshold(edges, 50, 255, cv2.THRESH_BINARY)
            
            else:
                # Default to Canny
                edges = cv2.Canny(
                    image,
                    params['canny_threshold1'],
                    params['canny_threshold2']
                )
            
            # Apply adaptive thresholding if enabled
            if params.get('use_adaptive_threshold', True):
                # Combine with adaptive threshold for better results
                adaptive = cv2.adaptiveThreshold(
                    image,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    params.get('adaptive_threshold_block_size', 11),
                    params.get('adaptive_threshold_c', 2)
                )
                # Combine edges
                edges = cv2.bitwise_or(edges, 255 - adaptive)
            
            self.logger.debug(f"Applied edge detection method: {method}")
            return edges
            
        except Exception as e:
            self.logger.warning(f"Advanced edge detection failed: {e}")
            # Fallback to basic Canny
            return cv2.Canny(
                image,
                params['canny_threshold1'],
                params['canny_threshold2']
            )
    
    def _select_optimal_edge_method(self, image: np.ndarray) -> str:
        """Automatically select the best edge detection method for the image"""
        try:
            # Analyze image characteristics
            mean_intensity = np.mean(image)
            std_intensity = np.std(image)
            contrast = std_intensity / mean_intensity if mean_intensity > 0 else 0
            
            # Select method based on image characteristics
            if contrast > 0.5:
                return 'canny'  # High contrast images work well with Canny
            elif contrast > 0.3:
                return 'adaptive_canny'  # Medium contrast benefits from adaptive thresholds
            else:
                return 'sobel'  # Low contrast images may work better with Sobel
            
        except Exception:
            return 'canny'  # Default fallback
    
    def _filter_and_analyze_contours(self, contours: List[np.ndarray], 
                                   hierarchy: np.ndarray, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Advanced contour filtering with hierarchy analysis"""
        try:
            min_area = params['min_contour_area']
            filtered_contours = []
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                
                # Skip tiny contours
                if area < min_area:
                    continue
                
                # Analyze contour properties
                perimeter = cv2.arcLength(contour, True)
                
                # Calculate shape metrics
                circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                
                # Approximate contour to reduce complexity
                epsilon = params.get('contour_approximation_epsilon', 0.02) * perimeter
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 1
                
                # Get hierarchy information
                hierarchy_info = None
                if hierarchy is not None and i < len(hierarchy[0]):
                    hierarchy_info = hierarchy[0][i]  # [next, previous, first_child, parent]
                
                contour_data = {
                    'contour': contour,
                    'area': area,
                    'perimeter': perimeter,
                    'circularity': circularity,
                    'aspect_ratio': aspect_ratio,
                    'approximated': approx,
                    'vertex_count': len(approx),
                    'bounding_box': (x, y, w, h),
                    'hierarchy': hierarchy_info,
                    'confidence': self._calculate_contour_confidence(contour, area, perimeter)
                }
                
                filtered_contours.append(contour_data)
            
            self.logger.debug(f"Filtered contours: {len(filtered_contours)} from {len(contours)}")
            return filtered_contours
            
        except Exception as e:
            self.logger.warning(f"Contour analysis failed: {e}")
            # Fallback to simple filtering
            return [{'contour': c, 'area': cv2.contourArea(c)} 
                   for c in contours if cv2.contourArea(c) > min_area]
    
    def _calculate_contour_confidence(self, contour: np.ndarray, area: float, perimeter: float) -> float:
        """Calculate confidence score for contour detection quality"""
        try:
            # Base confidence starts at 0.5
            confidence = 0.5
            
            # Boost confidence for reasonable size objects
            if 500 < area < 50000:
                confidence += 0.2
            
            # Boost confidence for good perimeter/area ratio
            if perimeter > 0:
                shape_factor = 4 * np.pi * area / (perimeter * perimeter)
                if 0.1 < shape_factor < 1.2:  # Reasonable shape factor
                    confidence += 0.2
            
            # Boost confidence for smooth contours
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity = area / hull_area
                if solidity > 0.7:  # Solid shape
                    confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception:
            return 0.5  # Default confidence
    
    def _generate_3d_geometry(self, contours: List[np.ndarray], image_shape: Tuple[int, int], 
                             params: Dict[str, Any], depth_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert 2D contours to 3D geometry data with enhanced shape information"""
        try:
            height, width = image_shape
            scale = params['scale_factor']
            extrusion_height = params['default_extrusion_height']
            base_thickness = params['base_thickness']
            
            # Convert image coordinates to 3D coordinates
            # Image origin (0,0) is top-left, 3D origin (0,0,0) is center-bottom
            contours_3d = []
            
            for contour in contours:
                # Handle both enhanced contour data (dict) and simple contours (numpy array)
                if isinstance(contour, dict):
                    # Enhanced contour data from advanced processing
                    contour_array = contour['contour']
                    shape_info = contour  # Contains shape recognition data
                else:
                    # Simple contour array
                    contour_array = contour
                    shape_info = {}
                
                # Simplify contour to reduce complexity
                epsilon = params.get('contour_approximation_epsilon', 0.02) * cv2.arcLength(contour_array, True)
                simplified = cv2.approxPolyDP(contour_array, epsilon, True)
                
                # Convert to 3D coordinates
                contour_3d = []
                for point in simplified:
                    x, y = point[0]
                    
                    # Convert image coordinates to 3D coordinates
                    # Center the object and flip Y axis
                    x_3d = (x - width/2) * scale
                    y_3d = (height/2 - y) * scale
                    
                    contour_3d.append([x_3d, y_3d])
                
                # Create enhanced contour data
                contour_data = {
                    'points': contour_3d,
                    'area': cv2.contourArea(contour_array) * (scale ** 2),
                    'perimeter': cv2.arcLength(contour_array, True) * scale,
                    'simplified_points': len(simplified)
                }
                
                # Add shape recognition data if available
                if shape_info:
                    contour_data.update({
                        'shape_type': shape_info.get('shape_type', 'unknown'),
                        'shape_confidence': shape_info.get('shape_confidence', 0.0),
                        'is_recognized_shape': shape_info.get('is_recognized_shape', False),
                        'circularity': shape_info.get('circularity', 0.0),
                        'aspect_ratio': shape_info.get('aspect_ratio', 1.0),
                        'vertex_count': shape_info.get('vertex_count', len(simplified)),
                        'detection_confidence': shape_info.get('confidence', 0.5),
                        'bounding_box_mm': [
                            coord * scale for coord in shape_info.get('bounding_box', [0, 0, 0, 0])
                        ] if 'bounding_box' in shape_info else None
                    })
                
                contours_3d.append(contour_data)
            
            # Calculate overall dimensions
            all_points = []
            for contour_data in contours_3d:
                all_points.extend(contour_data['points'])
            
            if all_points:
                x_coords = [p[0] for p in all_points]
                y_coords = [p[1] for p in all_points]
                
                bounds = {
                    'x_min': min(x_coords), 'x_max': max(x_coords),
                    'y_min': min(y_coords), 'y_max': max(y_coords),
                    'width': max(x_coords) - min(x_coords),
                    'height': max(y_coords) - min(y_coords)
                }
            else:
                bounds = {'x_min': 0, 'x_max': 0, 'y_min': 0, 'y_max': 0, 'width': 0, 'height': 0}
            
            # Enhanced geometry analysis
            shape_summary = self._analyze_detected_shapes(contours_3d)
            
            # Enhanced extrusion height using depth data if available
            enhanced_extrusion_height = extrusion_height
            if depth_data and params.get('use_depth_for_extrusion', False):
                depth_stats = depth_data.get('depth_stats', {})
                if depth_stats.get('mean', 0) > 0:
                    enhanced_extrusion_height = max(depth_stats['mean'], extrusion_height)
            
            geometry_data = {
                'contours_3d': contours_3d,
                'bounds_2d': bounds,
                'extrusion_height': enhanced_extrusion_height,
                'base_thickness': base_thickness,
                'scale_factor': scale,
                'total_contours': len(contours_3d),
                'estimated_volume': self._estimate_volume(contours_3d, enhanced_extrusion_height, base_thickness),
                'shape_analysis': shape_summary,
                'processing_method': 'enhanced_cv_with_depth' if depth_data else 'enhanced_cv_pipeline',
                # Aufgabe 7: Include depth-based reconstruction data
                'depth_reconstruction': depth_data,
                'has_depth_data': depth_data is not None,
                'reconstruction_method': 'depth_based' if depth_data else 'contour_extrusion'
            }
            
            return geometry_data
            
        except Exception as e:
            raise WorkflowError(f"Enhanced 3D geometry generation failed: {str(e)}")
    
    def _analyze_detected_shapes(self, contours_3d: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the collection of detected shapes"""
        try:
            shape_counts = {}
            total_area = 0
            recognized_shapes = 0
            high_confidence_shapes = 0
            
            for contour_data in contours_3d:
                shape_type = contour_data.get('shape_type', 'unknown')
                shape_confidence = contour_data.get('shape_confidence', 0.0)
                area = contour_data.get('area', 0)
                
                # Count shape types
                shape_counts[shape_type] = shape_counts.get(shape_type, 0) + 1
                total_area += area
                
                # Count recognition success
                if shape_type != 'unknown':
                    recognized_shapes += 1
                    
                if shape_confidence > 0.7:
                    high_confidence_shapes += 1
            
            return {
                'shape_distribution': shape_counts,
                'total_area_mm2': total_area,
                'recognition_rate': recognized_shapes / len(contours_3d) if contours_3d else 0,
                'high_confidence_rate': high_confidence_shapes / len(contours_3d) if contours_3d else 0,
                'complexity_score': len(shape_counts) + (total_area / 1000),  # Rough complexity metric
                'dominant_shape': max(shape_counts.items(), key=lambda x: x[1])[0] if shape_counts else 'none'
            }
            
        except Exception as e:
            self.logger.warning(f"Shape analysis failed: {e}")
            return {
                'shape_distribution': {},
                'total_area_mm2': 0,
                'recognition_rate': 0,
                'high_confidence_rate': 0,
                'complexity_score': 1,
                'dominant_shape': 'unknown'
            }
    
    def _create_mesh_specification(self, geometry_data: Dict[str, Any], 
                                  params: Dict[str, Any]) -> Dict[str, Any]:
        """Create mesh specification for CAD Agent"""
        try:
            # Create specification that CAD Agent can understand
            mesh_spec = {
                'type': 'extruded_contours',
                'contours': geometry_data['contours_3d'],
                'extrusion_height': geometry_data['extrusion_height'],
                'base_thickness': geometry_data['base_thickness'],
                'bounds': geometry_data['bounds_2d'],
                'material_properties': {
                    'volume_mm3': geometry_data['estimated_volume'],
                    'surface_area_estimate': self._estimate_surface_area(geometry_data),
                    'print_complexity': self._assess_print_complexity(geometry_data)
                },
                'generation_method': 'image_processing',
                'generation_timestamp': datetime.now().isoformat()
            }
            
            return mesh_spec
            
        except Exception as e:
            raise WorkflowError(f"Mesh specification creation failed: {str(e)}")
    
    def _estimate_volume(self, contours_3d: List[Dict[str, Any]], 
                        extrusion_height: float, base_thickness: float) -> float:
        """Estimate the volume of the 3D object"""
        try:
            total_area = 0.0
            for contour_data in contours_3d:
                total_area += contour_data['area']
            
            # Volume = base area × (extrusion height + base thickness)
            volume = total_area * (extrusion_height + base_thickness)
            
            return max(volume, 0.1)  # Minimum volume for printability
            
        except Exception as e:
            self.logger.warning(f"Volume estimation failed: {e}")
            return 1.0  # Default volume
    
    def _estimate_surface_area(self, geometry_data: Dict[str, Any]) -> float:
        """Estimate surface area for material calculations"""
        try:
            contours = geometry_data['contours_3d']
            height = geometry_data['extrusion_height'] + geometry_data['base_thickness']
            
            total_area = 0.0
            total_perimeter = 0.0
            
            for contour_data in contours:
                # Top and bottom faces
                total_area += contour_data['area'] * 2
                # Side walls
                total_area += contour_data['perimeter'] * height
                total_perimeter += contour_data['perimeter']
            
            return max(total_area, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Surface area estimation failed: {e}")
            return 10.0  # Default surface area
    
    def _assess_print_complexity(self, geometry_data: Dict[str, Any]) -> str:
        """Assess the complexity of the print job"""
        try:
            contour_count = len(geometry_data['contours_3d'])
            total_points = sum(len(c['points']) for c in geometry_data['contours_3d'])
            bounds = geometry_data['bounds_2d']
            aspect_ratio = bounds['width'] / bounds['height'] if bounds['height'] > 0 else 1.0
            
            # Complexity scoring
            complexity_score = 0
            if contour_count > 10:
                complexity_score += 2
            elif contour_count > 5:
                complexity_score += 1
                
            if total_points > 200:
                complexity_score += 2
            elif total_points > 100:
                complexity_score += 1
                
            if aspect_ratio > 3.0 or aspect_ratio < 0.33:
                complexity_score += 1
            
            if complexity_score >= 4:
                return 'high'
            elif complexity_score >= 2:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            self.logger.warning(f"Complexity assessment failed: {e}")
            return 'medium'
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats"""
        return ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']
    
    def validate_image(self, image_data: bytes, filename: str) -> Dict[str, Any]:
        """Validate uploaded image"""
        try:
            # Check file extension
            file_ext = Path(filename).suffix.lower().lstrip('.')
            if file_ext not in self.get_supported_formats():
                raise ValidationError(f"Unsupported image format: {file_ext}")
            
            # Try to load image
            image_pil = Image.open(io.BytesIO(image_data))
            
            # Check image size
            max_dimension = max(self.default_params['max_image_size'])
            if max(image_pil.size) > max_dimension * 2:
                raise ValidationError(f"Image too large. Max dimension: {max_dimension * 2}px")
            
            # Check image mode
            if image_pil.mode not in ['RGB', 'RGBA', 'L', 'P']:
                raise ValidationError(f"Unsupported image mode: {image_pil.mode}")
            
            return {
                'valid': True,
                'format': file_ext,
                'dimensions': image_pil.size,
                'mode': image_pil.mode,
                'estimated_processing_time': self._estimate_processing_time(image_pil.size)
            }
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Image validation failed: {str(e)}")
    
    def _estimate_processing_time(self, image_size: Tuple[int, int]) -> str:
        """Estimate processing time based on image size"""
        pixel_count = image_size[0] * image_size[1]
        
        if pixel_count > 500000:
            return "2-4 minutes"
        elif pixel_count > 200000:
            return "1-2 minutes"
        elif pixel_count > 50000:
            return "30-60 seconds"
        else:
            return "10-30 seconds"
    
    async def _estimate_depth(self, image_data: bytes, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Estimate depth map from image using MiDaS/DPT model
        
        Args:
            image_data: Raw image bytes
            params: Processing parameters
            
        Returns:
            Dictionary containing depth map and 3D reconstruction data
        """
        try:
            if self.depth_model is None or self.depth_processor is None:
                self.logger.warning("Depth estimation model not available")
                return None
            
            self.logger.info("Starting depth estimation...")
            
            # Load and preprocess image for depth estimation
            image_pil = Image.open(io.BytesIO(image_data))
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')
            
            # Resize for depth model (maintain aspect ratio)
            max_size = params.get('depth_max_size', 384)
            original_size = image_pil.size
            
            # Calculate new size maintaining aspect ratio
            if image_pil.size[0] > image_pil.size[1]:
                new_width = max_size
                new_height = int((max_size * image_pil.size[1]) / image_pil.size[0])
            else:
                new_height = max_size
                new_width = int((max_size * image_pil.size[0]) / image_pil.size[1])
            
            image_resized = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Process image through depth model
            inputs = self.depth_processor(images=image_resized, return_tensors="pt")
            
            # Move to same device as model
            if torch.cuda.is_available() and next(self.depth_model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Generate depth map
            with torch.no_grad():
                outputs = self.depth_model(**inputs)
                
                # Handle different output formats from different models
                if hasattr(outputs, 'predicted_depth'):
                    depth_map = outputs.predicted_depth
                elif hasattr(outputs, 'depth'):
                    depth_map = outputs.depth
                elif hasattr(outputs, 'prediction'):
                    depth_map = outputs.prediction
                elif hasattr(outputs, 'last_hidden_state'):
                    # For DPT models, the depth is often in last_hidden_state
                    depth_map = outputs.last_hidden_state
                elif isinstance(outputs, (list, tuple)):
                    # Try to get the first output
                    depth_map = outputs[0]
                else:
                    # Try to get the tensor directly
                    depth_map = outputs
                
                # Ensure we have a tensor and handle the shape properly
                if hasattr(depth_map, 'squeeze'):
                    depth_map = depth_map.squeeze()
                elif isinstance(depth_map, dict):
                    # If it's still a dict, try common keys
                    for key in ['predicted_depth', 'depth', 'prediction', 'logits']:
                        if key in depth_map:
                            depth_map = depth_map[key]
                            if hasattr(depth_map, 'squeeze'):
                                depth_map = depth_map.squeeze()
                            break
                    else:
                        # Fallback: take the first tensor value
                        depth_map = next(iter(depth_map.values()))
                        if hasattr(depth_map, 'squeeze'):
                            depth_map = depth_map.squeeze()
            
            # Convert to numpy and resize back to original image size
            depth_numpy = depth_map.cpu().numpy() if hasattr(depth_map, 'cpu') else depth_map
            
            # Ensure it's a 2D array
            if depth_numpy.ndim > 2:
                depth_numpy = depth_numpy.squeeze()
                
            # Resize depth map to original image size
            depth_resized = cv2.resize(depth_numpy, original_size, interpolation=cv2.INTER_LINEAR)
            
            # Normalize and apply scaling
            depth_normalized = self._normalize_depth_map(depth_resized, params)
            
            # Generate point cloud from depth map
            point_cloud_data = self._depth_to_point_cloud(
                depth_normalized, original_size, params
            )
            
            # Generate 3D mesh from point cloud
            mesh_data = await self._point_cloud_to_mesh(point_cloud_data, params)
            
            depth_result = {
                'depth_map': depth_normalized,
                'depth_map_shape': depth_normalized.shape,
                'original_image_size': original_size,
                'point_cloud': point_cloud_data,
                'mesh_data': mesh_data,
                'model_used': params.get('depth_model', 'dpt-large'),
                'processing_time': datetime.now().isoformat(),
                'depth_stats': self._analyze_depth_map(depth_normalized)
            }
            
            self.logger.info(f"Depth estimation completed. Generated {len(point_cloud_data['points'])} 3D points")
            return depth_result
            
        except Exception as e:
            self.logger.error(f"Depth estimation failed: {e}")
            return None
    
    def _normalize_depth_map(self, depth_map: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Normalize and scale depth map"""
        try:
            # Remove outliers (values too far from median)
            median_depth = np.median(depth_map)
            std_depth = np.std(depth_map)
            
            # Clip extreme values
            depth_clipped = np.clip(
                depth_map, 
                median_depth - 3 * std_depth, 
                median_depth + 3 * std_depth
            )
            
            # Normalize to 0-1 range
            depth_min = depth_clipped.min()
            depth_max = depth_clipped.max()
            
            if depth_max > depth_min:
                depth_normalized = (depth_clipped - depth_min) / (depth_max - depth_min)
            else:
                depth_normalized = depth_clipped
            
            # Apply threshold
            threshold = params.get('depth_threshold', 0.1)
            depth_normalized[depth_normalized < threshold] = 0
            
            # Apply smoothing if enabled
            if params.get('enable_depth_smoothing', True):
                sigma = params.get('depth_smoothing_sigma', 1.0)
                from scipy import ndimage
                depth_normalized = ndimage.gaussian_filter(depth_normalized, sigma=sigma)
            
            # Scale to physical units (mm)
            scale_factor = params.get('depth_scale_factor', 10.0)
            depth_scaled = depth_normalized * scale_factor
            
            return depth_scaled
            
        except Exception as e:
            self.logger.warning(f"Depth normalization failed: {e}")
            return depth_map
    
    def _depth_to_point_cloud(self, depth_map: np.ndarray, image_size: Tuple[int, int], 
                             params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert depth map to 3D point cloud"""
        try:
            height, width = depth_map.shape
            
            # Create coordinate grids
            x, y = np.meshgrid(np.arange(width), np.arange(height))
            
            # Convert to physical coordinates (centered)
            scale = params.get('scale_factor', 0.1)
            x_3d = (x - width/2) * scale
            y_3d = (height/2 - y) * scale  # Flip Y axis
            z_3d = depth_map
            
            # Create mask for valid depth values
            valid_mask = z_3d > 0
            
            # Extract valid points
            points_3d = np.column_stack([
                x_3d[valid_mask],
                y_3d[valid_mask], 
                z_3d[valid_mask]
            ])
            
            # Downsample if too many points
            downsample_factor = params.get('point_cloud_downsample', 0.005)
            if len(points_3d) > 1/downsample_factor:
                # Random sampling
                num_points = int(len(points_3d) * downsample_factor)
                indices = np.random.choice(len(points_3d), num_points, replace=False)
                points_3d = points_3d[indices]
            
            # Filter points within reasonable bounds
            bounds = self._calculate_point_cloud_bounds(points_3d)
            
            point_cloud_data = {
                'points': points_3d.tolist(),
                'num_points': len(points_3d),
                'bounds': bounds,
                'colors': None,  # Could add color information if needed
                'normals': None  # Could compute normals if needed
            }
            
            return point_cloud_data
            
        except Exception as e:
            self.logger.warning(f"Point cloud generation failed: {e}")
            return {'points': [], 'num_points': 0, 'bounds': {}}
    
    async def _point_cloud_to_mesh(self, point_cloud_data: Dict[str, Any], 
                                  params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert point cloud to triangle mesh"""
        try:
            if not DEPTH_ESTIMATION_AVAILABLE:
                return None
                
            points = np.array(point_cloud_data['points'])
            
            if len(points) < params.get('min_depth_points', 1000):
                self.logger.warning(f"Too few points for mesh reconstruction: {len(points)}")
                return None
            
            method = params.get('mesh_reconstruction_method', 'delaunay')
            
            if method == 'delaunay':
                mesh_data = self._delaunay_reconstruction(points)
            elif method == 'alpha_shape':
                mesh_data = self._alpha_shape_reconstruction(points, params)
            elif method == 'poisson' and hasattr(o3d.geometry, 'PointCloud'):
                mesh_data = self._poisson_reconstruction(points, params)
            else:
                # Fallback to Delaunay
                mesh_data = self._delaunay_reconstruction(points)
            
            return mesh_data
            
        except Exception as e:
            self.logger.warning(f"Mesh reconstruction failed: {e}")
            return None
    
    def _delaunay_reconstruction(self, points: np.ndarray) -> Dict[str, Any]:
        """Simple Delaunay triangulation for mesh reconstruction"""
        try:
            from scipy.spatial import Delaunay
            
            # Use only X,Y coordinates for 2D triangulation
            points_2d = points[:, :2]
            
            # Perform Delaunay triangulation
            tri = Delaunay(points_2d)
            
            # Create 3D vertices using original Z coordinates
            vertices = points
            faces = tri.simplices
            
            # Filter out degenerate triangles
            valid_faces = []
            for face in faces:
                if len(np.unique(face)) == 3:  # Ensure 3 unique vertices
                    valid_faces.append(face)
            
            mesh_data = {
                'vertices': vertices.tolist(),
                'faces': valid_faces,
                'method': 'delaunay',
                'vertex_count': len(vertices),
                'face_count': len(valid_faces)
            }
            
            return mesh_data
            
        except Exception as e:
            self.logger.warning(f"Delaunay reconstruction failed: {e}")
            return {'vertices': [], 'faces': [], 'method': 'delaunay'}
    
    def _alpha_shape_reconstruction(self, points: np.ndarray, params: Dict[str, Any]) -> Dict[str, Any]:
        """Alpha shape reconstruction for more detailed mesh"""
        try:
            # This is a simplified alpha shape implementation
            # In practice, you might want to use a more sophisticated library
            from scipy.spatial import Delaunay
            
            # For now, fall back to Delaunay with filtering
            return self._delaunay_reconstruction(points)
            
        except Exception as e:
            self.logger.warning(f"Alpha shape reconstruction failed: {e}")
            return {'vertices': [], 'faces': [], 'method': 'alpha_shape'}
    
    def _poisson_reconstruction(self, points: np.ndarray, params: Dict[str, Any]) -> Dict[str, Any]:
        """Poisson surface reconstruction using Open3D"""
        try:
            # Create Open3D point cloud
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            
            # Estimate normals
            pcd.estimate_normals()
            
            # Poisson reconstruction
            mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)
            
            # Convert to our format
            vertices = np.asarray(mesh.vertices)
            faces = np.asarray(mesh.triangles)
            
            mesh_data = {
                'vertices': vertices.tolist(),
                'faces': faces.tolist(),
                'method': 'poisson',
                'vertex_count': len(vertices),
                'face_count': len(faces)
            }
            
            return mesh_data
            
        except Exception as e:
            self.logger.warning(f"Poisson reconstruction failed: {e}")
            return {'vertices': [], 'faces': [], 'method': 'poisson'}
    
    def _calculate_point_cloud_bounds(self, points: np.ndarray) -> Dict[str, float]:
        """Calculate bounding box for point cloud"""
        try:
            if len(points) == 0:
                return {'x_min': 0, 'x_max': 0, 'y_min': 0, 'y_max': 0, 'z_min': 0, 'z_max': 0}
            
            return {
                'x_min': float(points[:, 0].min()),
                'x_max': float(points[:, 0].max()),
                'y_min': float(points[:, 1].min()),
                'y_max': float(points[:, 1].max()),
                'z_min': float(points[:, 2].min()),
                'z_max': float(points[:, 2].max())
            }
            
        except Exception:
            return {'x_min': 0, 'x_max': 0, 'y_min': 0, 'y_max': 0, 'z_min': 0, 'z_max': 0}
    
    def _analyze_depth_map(self, depth_map: np.ndarray) -> Dict[str, float]:
        """Analyze depth map statistics"""
        try:
            valid_depths = depth_map[depth_map > 0]
            
            if len(valid_depths) == 0:
                return {'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0, 'coverage': 0}
            
            return {
                'mean': float(np.mean(valid_depths)),
                'median': float(np.median(valid_depths)),
                'std': float(np.std(valid_depths)),
                'min': float(np.min(valid_depths)),
                'max': float(np.max(valid_depths)),
                'coverage': float(len(valid_depths) / depth_map.size)
            }
            
        except Exception:
            return {'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0, 'coverage': 0}
    
    async def execute_task(self, task_data: Dict[str, Any]) -> Any:
        """
        Execute image processing task.
        
        Args:
            task_data: Dictionary containing task parameters
            
        Returns:
            Task execution result
        """
        try:
            operation = task_data.get('operation', 'process_image')
            
            if operation == 'process_image':
                image_data = task_data.get('image_data')
                image_filename = task_data.get('image_filename', 'image.png')
                processing_params = task_data.get('processing_params', {})
                
                if not image_data:
                    raise ValidationError("No image data provided")
                
                result = await self.process_image_to_3d(image_data, image_filename, processing_params)
                return result
                
            elif operation == 'validate_image':
                image_data = task_data.get('image_data')
                image_filename = task_data.get('image_filename', 'image.png')
                
                if not image_data:
                    raise ValidationError("No image data provided")
                
                return self.validate_image(image_data, image_filename)
                
            else:
                raise ValidationError(f"Unknown image processing operation: {operation}")
                
        except Exception as e:
            self.logger.error(f"Image processing task failed: {e}")
            raise

    def _apply_shape_recognition(self, contour_data_list: List[Dict[str, Any]], 
                                   params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply shape recognition to classify detected objects"""
        try:
            min_confidence = params.get('min_shape_confidence', 0.7)
            
            for contour_data in contour_data_list:
                contour = contour_data['contour']
                approx = contour_data['approximated']
                
                # Classify shape based on geometry
                shape_type, shape_confidence = self._classify_shape(contour, approx, contour_data)
                
                contour_data['shape_type'] = shape_type
                contour_data['shape_confidence'] = shape_confidence
                contour_data['is_recognized_shape'] = shape_confidence >= min_confidence
                
                # Add shape-specific properties
                if shape_type == 'circle':
                    center, radius = cv2.minEnclosingCircle(contour)
                    contour_data['circle_center'] = center
                    contour_data['circle_radius'] = radius
                elif shape_type == 'rectangle':
                    rect = cv2.minAreaRect(contour)
                    contour_data['rectangle'] = rect
                elif shape_type == 'triangle':
                    # Triangle properties already in approximated points
                    pass
            
            self.logger.debug("Applied shape recognition to contours")
            return contour_data_list
            
        except Exception as e:
            self.logger.warning(f"Shape recognition failed: {e}")
            return contour_data_list
    
    def _classify_shape(self, contour: np.ndarray, approx: np.ndarray, 
                       contour_data: Dict[str, Any]) -> Tuple[str, float]:
        """Classify the shape of a contour"""
        try:
            vertex_count = len(approx)
            area = contour_data['area']
            circularity = contour_data['circularity']
            aspect_ratio = contour_data['aspect_ratio']
            
            # Circle detection
            if circularity > 0.7 and 0.8 < aspect_ratio < 1.2:
                return 'circle', min(circularity, 0.95)
            
            # Triangle detection
            if vertex_count == 3 and circularity > 0.5:
                return 'triangle', 0.85
            
            # Rectangle/Square detection
            if vertex_count == 4:
                # Check if angles are approximately 90 degrees
                rect_confidence = self._calculate_rectangle_confidence(approx)
                if rect_confidence > 0.7:
                    if 0.8 < aspect_ratio < 1.2:
                        return 'square', rect_confidence
                    else:
                        return 'rectangle', rect_confidence
            
            # Pentagon detection
            if vertex_count == 5 and circularity > 0.6:
                return 'pentagon', 0.75
            
            # Hexagon detection
            if vertex_count == 6 and circularity > 0.7:
                return 'hexagon', 0.8
            
            # General polygon
            if 3 <= vertex_count <= 12:
                return f'polygon_{vertex_count}', 0.6
            
            # Complex/irregular shape
            return 'irregular', 0.5
            
        except Exception:
            return 'unknown', 0.3
    
    def _calculate_rectangle_confidence(self, approx: np.ndarray) -> float:
        """Calculate confidence that a 4-vertex shape is a rectangle"""
        try:
            if len(approx) != 4:
                return 0.0
            
            # Calculate angles between consecutive edges
            points = approx.reshape(4, 2)
            angles = []
            
            for i in range(4):
                p1 = points[i]
                p2 = points[(i + 1) % 4]
                p3 = points[(i + 2) % 4]
                
                # Calculate vectors
                v1 = p1 - p2
                v2 = p3 - p2
                
                # Calculate angle
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                cos_angle = np.clip(cos_angle, -1, 1)
                angle = np.arccos(cos_angle)
                angles.append(angle)
            
            # Check how close angles are to 90 degrees (π/2)
            target_angle = np.pi / 2
            angle_errors = [abs(angle - target_angle) for angle in angles]
            max_error = max(angle_errors)
            
            # Convert error to confidence (smaller error = higher confidence)
            confidence = 1.0 - (max_error / (np.pi / 4))  # Normalize by 45 degrees
            return max(0.0, confidence)
            
        except Exception:
            return 0.0
    
    def _separate_overlapping_objects(self, contour_data_list: List[Dict[str, Any]], 
                                    params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect and separate overlapping objects using advanced techniques"""
        try:
            # Create a mask from all contours
            if not contour_data_list:
                return contour_data_list
            
            # Get image dimensions from bounding boxes
            all_boxes = [data['bounding_box'] for data in contour_data_list]
            max_x = max(box[0] + box[2] for box in all_boxes)
            max_y = max(box[1] + box[3] for box in all_boxes)
            
            # Create binary mask
            mask = np.zeros((max_y + 10, max_x + 10), dtype=np.uint8)
            
            for contour_data in contour_data_list:
                cv2.fillPoly(mask, [contour_data['contour']], 255)
            
            # Apply distance transform
            dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
            
            # Find local maxima (peaks) which indicate object centers
            local_maxima = self._find_local_maxima(dist_transform)
            
            # If multiple peaks found, try to separate objects
            if len(local_maxima) > len(contour_data_list):
                self.logger.debug(f"Found {len(local_maxima)} potential objects in {len(contour_data_list)} contours")
                
                # Apply watershed segmentation
                separated_contours = self._apply_watershed_segmentation(
                    mask, local_maxima, contour_data_list
                )
                
                if separated_contours:
                    return separated_contours
            
            return contour_data_list
            
        except Exception as e:
            self.logger.warning(f"Object separation failed: {e}")
            return contour_data_list
    
    def _find_local_maxima(self, dist_transform: np.ndarray, 
                          min_distance: int = 20) -> List[Tuple[int, int]]:
        """Find local maxima in distance transform"""
        try:
            from scipy import ndimage
            from scipy.ndimage import maximum_filter
            
            # Apply maximum filter to find local maxima
            local_max = maximum_filter(dist_transform, size=min_distance) == dist_transform
            
            # Remove maxima that are too small
            threshold = 0.3 * dist_transform.max()
            local_max = local_max & (dist_transform > threshold)
            
            # Get coordinates of maxima
            coords = np.where(local_max)
            maxima = list(zip(coords[1], coords[0]))  # Convert to (x, y) format
            
            return maxima
            
        except Exception as e:
            self.logger.warning(f"Local maxima detection failed: {e}")
            return []
    
    def _apply_watershed_segmentation(self, mask: np.ndarray, peaks: List[Tuple[int, int]], 
                                    original_contours: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply watershed segmentation to separate overlapping objects"""
        try:
            from scipy import ndimage
            
            # Create markers for watershed
            markers = np.zeros(mask.shape, dtype=np.int32)
            
            for i, (x, y) in enumerate(peaks):
                if 0 <= x < mask.shape[1] and 0 <= y < mask.shape[0]:
                    markers[y, x] = i + 1
            
            # Apply watershed
            distance = ndimage.distance_transform_edt(mask)
            labels = cv2.watershed(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), markers)
            
            # Extract new contours from segmented regions
            new_contours = []
            
            for label in range(1, len(peaks) + 1):
                region_mask = (labels == label).astype(np.uint8) * 255
                
                # Find contours in this region
                region_contours, _ = cv2.findContours(
                    region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                
                for contour in region_contours:
                    area = cv2.contourArea(contour)
                    if area > 100:  # Minimum area threshold
                        # Create contour data similar to original format
                        perimeter = cv2.arcLength(contour, True)
                        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                        
                        contour_data = {
                            'contour': contour,
                            'area': area,
                            'perimeter': perimeter,
                            'circularity': circularity,
                            'confidence': 0.7,  # Lower confidence for separated objects
                            'separated_object': True
                        }
                        
                        new_contours.append(contour_data)
            
            return new_contours if new_contours else original_contours
            
        except Exception as e:
            self.logger.warning(f"Watershed segmentation failed: {e}")
            return original_contours
    
    def _extract_contours_fallback(self, image: np.ndarray, params: Dict[str, Any]) -> List[np.ndarray]:
        """Fallback method for contour extraction if advanced methods fail"""
        try:
            # Basic Canny edge detection
            edges = cv2.Canny(
                image,
                params['canny_threshold1'],
                params['canny_threshold2']
            )
            
            # Find contours
            contours, _ = cv2.findContours(
                edges, 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Filter contours by area
            min_area = params['min_contour_area']
            filtered_contours = [
                contour for contour in contours 
                if cv2.contourArea(contour) > min_area
            ]
            
            # Sort by area (largest first)
            filtered_contours.sort(key=cv2.contourArea, reverse=True)
            
            self.logger.info(f"Fallback contour extraction: {len(filtered_contours)} contours found")
            
            return filtered_contours
            
        except Exception as e:
            self.logger.error(f"Fallback contour extraction failed: {e}")
            return []
    
    # Note: Duplicate execute_task method removed - already defined above at line 1171
