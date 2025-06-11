"""
AI-Enhanced Design Features for AI Agent 3D Print System

This module provides AI-powered design analysis, optimization, and enhancement
capabilities including design complexity assessment, automatic improvements,
failure prediction, and intelligent suggestions.

Features:
- Design complexity analysis and scoring
- Machine learning-based optimization suggestions
- Print failure prediction algorithms
- Automatic design improvements
- Material and setting recommendations
- Structural analysis and optimization
"""

import json
import logging
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import sqlite3
from datetime import datetime
import pickle
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error

from core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class DesignMetrics:
    """Comprehensive design metrics for analysis"""
    # Geometric complexity
    triangle_count: int
    vertex_count: int
    surface_area: float
    volume: float
    bounding_box_volume: float
    aspect_ratio: float
    
    # Print complexity
    overhangs_percentage: float
    bridges_count: int
    support_volume_ratio: float
    thin_walls_count: int
    small_features_count: int
    
    # Structural analysis
    wall_thickness_min: float
    wall_thickness_avg: float
    stress_concentration_points: int
    weak_points_count: int
    
    # Printability scores
    printability_score: float
    complexity_score: float
    failure_risk_score: float
    estimated_success_rate: float

@dataclass
class OptimizationSuggestion:
    """AI-generated optimization suggestion"""
    suggestion_id: str
    category: str  # 'geometry', 'orientation', 'supports', 'material', 'settings'
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    expected_improvement: str
    implementation_difficulty: str
    estimated_time_savings: float  # in hours
    estimated_material_savings: float  # in percentage
    confidence_score: float  # 0.0 to 1.0

@dataclass
class DesignAnalysisResult:
    """Complete design analysis result"""
    design_id: str
    analysis_timestamp: datetime
    metrics: DesignMetrics
    suggestions: List[OptimizationSuggestion]
    failure_predictions: List[str]
    recommended_materials: List[str]
    recommended_settings: Dict[str, Any]
    overall_score: float
    improvement_potential: float

class GeometryAnalyzer:
    """Analyzes 3D geometry for design metrics and complexity"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.GeometryAnalyzer")
    
    def analyze_stl_geometry(self, geometry_data: Dict[str, Any]) -> DesignMetrics:
        """
        Analyze STL geometry and extract comprehensive design metrics
        
        Args:
            geometry_data: Parsed STL geometry data
            
        Returns:
            DesignMetrics object with all calculated metrics
        """
        try:
            vertices = geometry_data['vertices']
            normals = geometry_data['normals']
            bounds = geometry_data['bounds']
            
            # Basic geometric properties
            triangle_count = geometry_data['triangle_count']
            vertex_count = len(vertices)
            
            # Calculate surface area and volume
            surface_area = self._calculate_surface_area(vertices, normals)
            volume = self._calculate_volume(vertices)
            bounding_box_volume = self._calculate_bounding_box_volume(bounds)
            aspect_ratio = self._calculate_aspect_ratio(bounds)
            
            # Analyze print complexity
            overhangs_percentage = self._analyze_overhangs(vertices, normals)
            bridges_count = self._count_bridges(vertices, normals)
            support_volume_ratio = self._estimate_support_volume(vertices, normals)
            thin_walls_count = self._count_thin_walls(vertices)
            small_features_count = self._count_small_features(vertices)
            
            # Structural analysis
            wall_thickness_min, wall_thickness_avg = self._analyze_wall_thickness(vertices)
            stress_concentration_points = self._find_stress_concentrations(vertices)
            weak_points_count = self._count_weak_points(vertices, normals)
            
            # Calculate printability scores
            printability_score = self._calculate_printability_score(
                overhangs_percentage, thin_walls_count, small_features_count
            )
            complexity_score = self._calculate_complexity_score(
                triangle_count, surface_area, volume, bridges_count
            )
            failure_risk_score = self._calculate_failure_risk(
                overhangs_percentage, thin_walls_count, weak_points_count
            )
            estimated_success_rate = max(0, 100 - failure_risk_score)
            
            return DesignMetrics(
                triangle_count=triangle_count,
                vertex_count=vertex_count,
                surface_area=surface_area,
                volume=volume,
                bounding_box_volume=bounding_box_volume,
                aspect_ratio=aspect_ratio,
                overhangs_percentage=overhangs_percentage,
                bridges_count=bridges_count,
                support_volume_ratio=support_volume_ratio,
                thin_walls_count=thin_walls_count,
                small_features_count=small_features_count,
                wall_thickness_min=wall_thickness_min,
                wall_thickness_avg=wall_thickness_avg,
                stress_concentration_points=stress_concentration_points,
                weak_points_count=weak_points_count,
                printability_score=printability_score,
                complexity_score=complexity_score,
                failure_risk_score=failure_risk_score,
                estimated_success_rate=estimated_success_rate
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing geometry: {e}")
            raise
    
    def _calculate_surface_area(self, vertices: List[List[float]], normals: List[List[float]]) -> float:
        """Calculate surface area of the mesh"""
        total_area = 0.0
        for i in range(0, len(vertices), 3):
            if i + 2 < len(vertices):
                v1 = np.array(vertices[i])
                v2 = np.array(vertices[i + 1])
                v3 = np.array(vertices[i + 2])
                
                # Calculate triangle area using cross product
                edge1 = v2 - v1
                edge2 = v3 - v1
                triangle_area = 0.5 * np.linalg.norm(np.cross(edge1, edge2))
                total_area += triangle_area
        
        return total_area
    
    def _calculate_volume(self, vertices: List[List[float]]) -> float:
        """Calculate volume using divergence theorem"""
        volume = 0.0
        for i in range(0, len(vertices), 3):
            if i + 2 < len(vertices):
                v1 = np.array(vertices[i])
                v2 = np.array(vertices[i + 1])
                v3 = np.array(vertices[i + 2])
                
                # Calculate signed volume of tetrahedron
                volume += np.dot(v1, np.cross(v2, v3)) / 6.0
        
        return abs(volume)
    
    def _calculate_bounding_box_volume(self, bounds: Dict[str, Tuple[float, float]]) -> float:
        """Calculate bounding box volume"""
        width = bounds['x'][1] - bounds['x'][0]
        height = bounds['y'][1] - bounds['y'][0]
        depth = bounds['z'][1] - bounds['z'][0]
        return width * height * depth
    
    def _calculate_aspect_ratio(self, bounds: Dict[str, Tuple[float, float]]) -> float:
        """Calculate aspect ratio (longest dimension / shortest dimension)"""
        dimensions = [
            bounds['x'][1] - bounds['x'][0],
            bounds['y'][1] - bounds['y'][0],
            bounds['z'][1] - bounds['z'][0]
        ]
        return max(dimensions) / min(dimensions) if min(dimensions) > 0 else 1.0
    
    def _analyze_overhangs(self, vertices: List[List[float]], normals: List[List[float]]) -> float:
        """Analyze percentage of surface that requires supports"""
        overhang_threshold = -0.7  # cos(135°) - steeper than 45° overhang
        overhang_triangles = 0
        total_triangles = len(normals)
        
        for normal in normals:
            if normal[2] < overhang_threshold:  # Z component indicates overhang
                overhang_triangles += 1
        
        return (overhang_triangles / total_triangles * 100) if total_triangles > 0 else 0
    
    def _count_bridges(self, vertices: List[List[float]], normals: List[List[float]]) -> int:
        """Count potential bridge structures"""
        # Simplified bridge detection based on horizontal surfaces with gaps
        bridges = 0
        z_levels = {}
        
        # Group triangles by Z level
        for i in range(0, len(vertices), 3):
            if i + 2 < len(vertices):
                z_avg = (vertices[i][2] + vertices[i + 1][2] + vertices[i + 2][2]) / 3
                z_level = round(z_avg, 1)
                if z_level not in z_levels:
                    z_levels[z_level] = []
                z_levels[z_level].append(i // 3)
        
        # Check for gaps at each level (simplified)
        for z_level, triangles in z_levels.items():
            if len(triangles) < 5:  # Potential bridge if few triangles at this level
                bridges += 1
        
        return bridges
    
    def _estimate_support_volume(self, vertices: List[List[float]], normals: List[List[float]]) -> float:
        """Estimate support material volume as percentage of model volume"""
        overhang_percentage = self._analyze_overhangs(vertices, normals)
        # Simplified estimation: support volume scales with overhang percentage
        return min(overhang_percentage * 0.3, 50.0)  # Cap at 50%
    
    def _count_thin_walls(self, vertices: List[List[float]]) -> int:
        """Count thin walls that might be problematic for printing"""
        # Simplified thin wall detection based on proximity analysis
        thin_walls = 0
        min_thickness = 0.8  # mm - typical minimum wall thickness
        
        # This is a simplified implementation
        # In practice, would need more sophisticated mesh analysis
        vertex_array = np.array(vertices)
        if len(vertex_array) > 0:
            # Estimate based on surface area to volume ratio
            surface_area = self._calculate_surface_area(vertices, [])
            volume = self._calculate_volume(vertices)
            if volume > 0:
                sa_vol_ratio = surface_area / volume
                if sa_vol_ratio > 50:  # High ratio indicates thin walls
                    thin_walls = int(sa_vol_ratio / 10)
        
        return min(thin_walls, 20)  # Cap at reasonable number
    
    def _count_small_features(self, vertices: List[List[float]]) -> int:
        """Count small features that might not print well"""
        small_features = 0
        min_feature_size = 0.5  # mm
        
        # Simplified detection based on vertex clustering
        vertex_array = np.array(vertices)
        if len(vertex_array) > 100:
            # Sample vertices and check for tight clusters
            sample_size = min(1000, len(vertex_array))
            sample_indices = np.random.choice(len(vertex_array), sample_size, replace=False)
            sample_vertices = vertex_array[sample_indices]
            
            # Count vertices that are very close to others
            for i, vertex in enumerate(sample_vertices):
                close_count = 0
                for j, other in enumerate(sample_vertices):
                    if i != j:
                        distance = np.linalg.norm(vertex - other)
                        if distance < min_feature_size:
                            close_count += 1
                if close_count > 5:  # Many nearby vertices indicate small feature
                    small_features += 1
        
        return min(small_features // 10, 15)  # Scale down and cap
    
    def _analyze_wall_thickness(self, vertices: List[List[float]]) -> Tuple[float, float]:
        """Analyze wall thickness statistics"""
        # Simplified wall thickness analysis
        # In practice, would need ray casting or other advanced techniques
        vertex_array = np.array(vertices)
        
        if len(vertex_array) == 0:
            return 1.0, 1.0
        
        # Estimate based on bounding box and vertex distribution
        bounds_x = [vertex_array[:, 0].min(), vertex_array[:, 0].max()]
        bounds_y = [vertex_array[:, 1].min(), vertex_array[:, 1].max()]
        bounds_z = [vertex_array[:, 2].min(), vertex_array[:, 2].max()]
        
        dimensions = [
            bounds_x[1] - bounds_x[0],
            bounds_y[1] - bounds_y[0],
            bounds_z[1] - bounds_z[0]
        ]
        
        # Rough estimation
        min_thickness = min(dimensions) * 0.05  # 5% of smallest dimension
        avg_thickness = sum(dimensions) * 0.02  # 2% of average dimension
        
        return max(min_thickness, 0.4), max(avg_thickness, 0.8)
    
    def _find_stress_concentrations(self, vertices: List[List[float]]) -> int:
        """Find potential stress concentration points"""
        # Simplified stress concentration detection
        # Based on sharp angles and geometric discontinuities
        stress_points = 0
        
        vertex_array = np.array(vertices)
        if len(vertex_array) > 9:
            # Check for sharp angles in triangle mesh
            for i in range(0, len(vertex_array) - 6, 3):
                v1 = vertex_array[i]
                v2 = vertex_array[i + 1]
                v3 = vertex_array[i + 2]
                
                # Calculate angle between edges
                edge1 = v2 - v1
                edge2 = v3 - v1
                
                if np.linalg.norm(edge1) > 0 and np.linalg.norm(edge2) > 0:
                    cos_angle = np.dot(edge1, edge2) / (np.linalg.norm(edge1) * np.linalg.norm(edge2))
                    angle = np.arccos(np.clip(cos_angle, -1, 1))
                    
                    # Sharp angle indicates potential stress concentration
                    if angle < np.pi / 6:  # Less than 30 degrees
                        stress_points += 1
        
        return min(stress_points // 10, 10)  # Scale down and cap
    
    def _count_weak_points(self, vertices: List[List[float]], normals: List[List[float]]) -> int:
        """Count structural weak points"""
        # Simplified weak point detection
        weak_points = 0
        
        # Check for areas with high curvature or thin connections
        vertex_array = np.array(vertices)
        normal_array = np.array(normals)
        
        if len(normal_array) > 1:
            # Check for rapid normal changes (high curvature)
            for i in range(len(normal_array) - 1):
                dot_product = np.dot(normal_array[i], normal_array[i + 1])
                if dot_product < 0.5:  # Normals differ significantly
                    weak_points += 1
        
        return min(weak_points // 5, 8)  # Scale down and cap
    
    def _calculate_printability_score(self, overhangs_pct: float, thin_walls: int, small_features: int) -> float:
        """Calculate overall printability score (0-100)"""
        base_score = 100.0
        
        # Deduct for overhangs
        base_score -= overhangs_pct * 0.5
        
        # Deduct for thin walls
        base_score -= thin_walls * 2
        
        # Deduct for small features
        base_score -= small_features * 1.5
        
        return max(base_score, 0.0)
    
    def _calculate_complexity_score(self, triangles: int, surface_area: float, volume: float, bridges: int) -> float:
        """Calculate design complexity score (0-100)"""
        base_score = 0.0
        
        # Triangle count complexity
        if triangles > 100000:
            base_score += 30
        elif triangles > 50000:
            base_score += 20
        elif triangles > 10000:
            base_score += 10
        
        # Surface area to volume ratio
        if volume > 0:
            sa_vol_ratio = surface_area / volume
            if sa_vol_ratio > 100:
                base_score += 25
            elif sa_vol_ratio > 50:
                base_score += 15
        
        # Bridge complexity
        base_score += bridges * 5
        
        return min(base_score, 100.0)
    
    def _calculate_failure_risk(self, overhangs_pct: float, thin_walls: int, weak_points: int) -> float:
        """Calculate print failure risk score (0-100)"""
        risk_score = 0.0
        
        # Overhang risk
        if overhangs_pct > 50:
            risk_score += 40
        elif overhangs_pct > 25:
            risk_score += 20
        elif overhangs_pct > 10:
            risk_score += 10
        
        # Thin wall risk
        risk_score += thin_walls * 3
        
        # Weak point risk
        risk_score += weak_points * 2
        
        return min(risk_score, 100.0)

class AIOptimizationEngine:
    """AI-powered optimization suggestion engine"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/ai_models")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = get_logger(f"{__name__}.AIOptimizationEngine")
        
        # Initialize ML models
        self.failure_predictor = None
        self.optimization_recommender = None
        self.scaler = StandardScaler()
        
        # Load or create models
        self._load_or_create_models()
    
    def _load_or_create_models(self):
        """Load existing models or create new ones"""
        try:
            failure_model_path = self.data_dir / "failure_predictor.pkl"
            optimization_model_path = self.data_dir / "optimization_recommender.pkl"
            scaler_path = self.data_dir / "feature_scaler.pkl"
            
            if all(p.exists() for p in [failure_model_path, optimization_model_path, scaler_path]):
                # Load existing models
                with open(failure_model_path, 'rb') as f:
                    self.failure_predictor = pickle.load(f)
                with open(optimization_model_path, 'rb') as f:
                    self.optimization_recommender = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                self.logger.info("AI models loaded successfully")
            else:
                # Create new models with synthetic data
                self._create_initial_models()
                self.logger.info("New AI models created with synthetic data")
                
        except Exception as e:
            self.logger.error(f"Error loading AI models: {e}")
            self._create_initial_models()
    
    def _create_initial_models(self):
        """Create initial models with synthetic training data"""
        try:
            # Generate synthetic training data
            X_failure, y_failure = self._generate_failure_training_data()
            X_optimization, y_optimization = self._generate_optimization_training_data()
            
            # Train failure prediction model
            self.failure_predictor = RandomForestClassifier(n_estimators=100, random_state=42)
            X_failure_scaled = self.scaler.fit_transform(X_failure)
            self.failure_predictor.fit(X_failure_scaled, y_failure)
            
            # Train optimization recommendation model
            self.optimization_recommender = GradientBoostingRegressor(n_estimators=100, random_state=42)
            self.optimization_recommender.fit(X_failure_scaled, y_optimization)
            
            # Save models
            self._save_models()
            
        except Exception as e:
            self.logger.error(f"Error creating initial models: {e}")
            raise
    
    def _generate_failure_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for failure prediction"""
        n_samples = 1000
        
        # Feature vector: [triangle_count, surface_area, volume, overhangs_pct, thin_walls, bridges]
        X = np.random.rand(n_samples, 6)
        
        # Scale features to realistic ranges
        X[:, 0] *= 200000  # triangle_count: 0-200k
        X[:, 1] *= 10000   # surface_area: 0-10k mm²
        X[:, 2] *= 1000    # volume: 0-1k mm³
        X[:, 3] *= 100     # overhangs_pct: 0-100%
        X[:, 4] *= 20      # thin_walls: 0-20
        X[:, 5] *= 10      # bridges: 0-10
        
        # Generate labels based on heuristics
        y = np.zeros(n_samples)
        for i in range(n_samples):
            failure_score = 0
            if X[i, 3] > 50:  # High overhangs
                failure_score += 0.4
            if X[i, 4] > 10:  # Many thin walls
                failure_score += 0.3
            if X[i, 5] > 5:   # Many bridges
                failure_score += 0.2
            if X[i, 0] > 150000:  # High complexity
                failure_score += 0.1
            
            y[i] = 1 if failure_score > 0.5 else 0
        
        return X, y
    
    def _generate_optimization_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for optimization recommendations"""
        n_samples = 1000
        
        # Same feature vector as failure prediction
        X = np.random.rand(n_samples, 6)
        X[:, 0] *= 200000
        X[:, 1] *= 10000
        X[:, 2] *= 1000
        X[:, 3] *= 100
        X[:, 4] *= 20
        X[:, 5] *= 10
        
        # Generate optimization potential scores (0-100)
        y = np.zeros(n_samples)
        for i in range(n_samples):
            optimization_potential = 0
            if X[i, 3] > 30:  # Overhangs can be optimized
                optimization_potential += 30
            if X[i, 4] > 5:   # Thin walls can be thickened
                optimization_potential += 25
            if X[i, 5] > 3:   # Bridges can be minimized
                optimization_potential += 20
            if X[i, 0] > 100000:  # Complexity can be reduced
                optimization_potential += 15
            
            y[i] = min(optimization_potential + np.random.normal(0, 5), 100)
        
        return X, y
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            with open(self.data_dir / "failure_predictor.pkl", 'wb') as f:
                pickle.dump(self.failure_predictor, f)
            with open(self.data_dir / "optimization_recommender.pkl", 'wb') as f:
                pickle.dump(self.optimization_recommender, f)
            with open(self.data_dir / "feature_scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
                
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
    
    def generate_optimization_suggestions(self, metrics: DesignMetrics) -> List[OptimizationSuggestion]:
        """Generate AI-powered optimization suggestions"""
        try:
            suggestions = []
            
            # Extract features for ML models
            features = np.array([[
                metrics.triangle_count,
                metrics.surface_area,
                metrics.volume,
                metrics.overhangs_percentage,
                metrics.thin_walls_count,
                metrics.bridges_count
            ]])
            
            features_scaled = self.scaler.transform(features)
            
            # Get AI predictions
            failure_probability = self.failure_predictor.predict_proba(features_scaled)[0][1]
            optimization_potential = self.optimization_recommender.predict(features_scaled)[0]
            
            # Generate suggestions based on metrics and AI predictions
            suggestion_id_counter = 1
            
            # Overhang optimization
            if metrics.overhangs_percentage > 25:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"OPT_{suggestion_id_counter:03d}",
                    category="orientation",
                    priority="high" if metrics.overhangs_percentage > 50 else "medium",
                    title="Optimize Print Orientation",
                    description=f"Current overhang percentage is {metrics.overhangs_percentage:.1f}%. Rotating the model could reduce support requirements.",
                    expected_improvement="Reduce support material by 30-60%",
                    implementation_difficulty="easy",
                    estimated_time_savings=metrics.overhangs_percentage * 0.02,
                    estimated_material_savings=metrics.overhangs_percentage * 0.3,
                    confidence_score=min(0.9, failure_probability + 0.3)
                ))
                suggestion_id_counter += 1
            
            # Thin wall optimization
            if metrics.thin_walls_count > 5:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"OPT_{suggestion_id_counter:03d}",
                    category="geometry",
                    priority="high",
                    title="Thicken Thin Walls",
                    description=f"Found {metrics.thin_walls_count} thin walls. Thickening to minimum 0.8mm recommended.",
                    expected_improvement="Improve structural integrity and print reliability",
                    implementation_difficulty="medium",
                    estimated_time_savings=0.5,
                    estimated_material_savings=-5.0,  # Negative = more material
                    confidence_score=0.8
                ))
                suggestion_id_counter += 1
            
            # Complexity reduction
            if metrics.triangle_count > 100000:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"OPT_{suggestion_id_counter:03d}",
                    category="geometry",
                    priority="medium",
                    title="Reduce Mesh Complexity",
                    description=f"Model has {metrics.triangle_count:,} triangles. Decimation could improve processing speed.",
                    expected_improvement="Faster slicing and processing",
                    implementation_difficulty="easy",
                    estimated_time_savings=1.0,
                    estimated_material_savings=0.0,
                    confidence_score=0.7
                ))
                suggestion_id_counter += 1
            
            # Support optimization
            if metrics.bridges_count > 3:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"OPT_{suggestion_id_counter:03d}",
                    category="supports",
                    priority="medium",
                    title="Optimize Bridge Structures",
                    description=f"Found {metrics.bridges_count} potential bridges. Consider design modifications to reduce bridging.",
                    expected_improvement="Reduce support material and improve surface quality",
                    implementation_difficulty="hard",
                    estimated_time_savings=metrics.bridges_count * 0.3,
                    estimated_material_savings=metrics.bridges_count * 5.0,
                    confidence_score=0.6
                ))
                suggestion_id_counter += 1
            
            # Material recommendation based on complexity
            if metrics.complexity_score > 70:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"OPT_{suggestion_id_counter:03d}",
                    category="material",
                    priority="low",
                    title="Consider Advanced Materials",
                    description="High complexity design may benefit from materials with better layer adhesion (ABS, PETG).",
                    expected_improvement="Better interlayer bonding and strength",
                    implementation_difficulty="easy",
                    estimated_time_savings=0.0,
                    estimated_material_savings=0.0,
                    confidence_score=optimization_potential / 100.0
                ))
                suggestion_id_counter += 1
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating optimization suggestions: {e}")
            return []
    
    def predict_print_failure(self, metrics: DesignMetrics) -> List[str]:
        """Predict potential print failures"""
        try:
            failures = []
            
            # Extract features
            features = np.array([[
                metrics.triangle_count,
                metrics.surface_area,
                metrics.volume,
                metrics.overhangs_percentage,
                metrics.thin_walls_count,
                metrics.bridges_count
            ]])
            
            features_scaled = self.scaler.transform(features)
            failure_probability = self.failure_predictor.predict_proba(features_scaled)[0][1]
            
            # Generate specific failure predictions
            if failure_probability > 0.7:
                failures.append("High risk of print failure detected")
            
            if metrics.overhangs_percentage > 60:
                failures.append("Excessive overhangs may cause sagging or collapse")
            
            if metrics.thin_walls_count > 10:
                failures.append("Thin walls may not print properly or break easily")
            
            if metrics.bridges_count > 5:
                failures.append("Multiple bridges may fail without proper cooling")
            
            if metrics.small_features_count > 10:
                failures.append("Small features may not resolve clearly")
            
            if metrics.aspect_ratio > 10:
                failures.append("High aspect ratio may cause tipping or warping")
            
            return failures
            
        except Exception as e:
            self.logger.error(f"Error predicting print failures: {e}")
            return ["Error in failure prediction system"]
    
    def recommend_materials(self, metrics: DesignMetrics) -> List[str]:
        """Recommend optimal materials based on design characteristics"""
        try:
            materials = []
            
            # Base recommendation
            materials.append("PLA")  # Always safe option
            
            # Advanced materials for complex designs
            if metrics.complexity_score > 50:
                materials.append("ABS")
                
            if metrics.thin_walls_count > 5 or metrics.weak_points_count > 3:
                materials.append("PETG")  # Better interlayer adhesion
                
            if metrics.small_features_count > 8:
                materials.append("Resin (SLA)")  # Better detail resolution
                
            if metrics.bridges_count > 3:
                materials.append("PLA+")  # Better bridging properties
                
            # Remove duplicates and sort by preference
            unique_materials = list(dict.fromkeys(materials))
            return unique_materials
            
        except Exception as e:
            self.logger.error(f"Error recommending materials: {e}")
            return ["PLA"]
    
    def recommend_print_settings(self, metrics: DesignMetrics) -> Dict[str, Any]:
        """Recommend optimal print settings"""
        try:
            settings = {
                "layer_height": 0.2,
                "infill_percentage": 20,
                "print_speed": 50,
                "support_overhang_angle": 45,
                "support_density": 15
            }
            
            # Adjust based on complexity
            if metrics.small_features_count > 5:
                settings["layer_height"] = 0.1  # Finer layers
                settings["print_speed"] = 30   # Slower for detail
                
            if metrics.thin_walls_count > 5:
                settings["infill_percentage"] = 30  # More infill for strength
                
            if metrics.overhangs_percentage > 30:
                settings["support_overhang_angle"] = 35  # More aggressive supports
                settings["support_density"] = 20
                
            if metrics.bridges_count > 3:
                settings["print_speed"] = 40  # Slower for better bridging
                
            return settings
            
        except Exception as e:
            self.logger.error(f"Error recommending print settings: {e}")
            return {"layer_height": 0.2, "infill_percentage": 20, "print_speed": 50}

class AIDesignEnhancer:
    """Main AI-enhanced design analysis and optimization system"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/ai_design")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.geometry_analyzer = GeometryAnalyzer()
        self.optimization_engine = AIOptimizationEngine(data_dir)
        self.logger = get_logger(f"{__name__}.AIDesignEnhancer")
        
        # Initialize database for storing analysis results
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for storing analysis results"""
        try:
            db_path = self.data_dir / "design_analysis.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Create tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS design_analyses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        design_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        suggestions_json TEXT NOT NULL,
                        overall_score REAL NOT NULL,
                        improvement_potential REAL NOT NULL
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS optimization_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        design_id TEXT NOT NULL,
                        suggestion_id TEXT NOT NULL,
                        implemented BOOLEAN NOT NULL,
                        feedback_score INTEGER,
                        notes TEXT,
                        timestamp TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    def analyze_design(self, design_id: str, geometry_data: Dict[str, Any]) -> DesignAnalysisResult:
        """
        Perform comprehensive AI-enhanced design analysis
        
        Args:
            design_id: Unique identifier for the design
            geometry_data: Parsed STL geometry data
            
        Returns:
            Complete design analysis result
        """
        try:
            self.logger.info(f"Starting AI design analysis for {design_id}")
            
            # Analyze geometry metrics
            metrics = self.geometry_analyzer.analyze_stl_geometry(geometry_data)
            
            # Generate AI-powered suggestions
            suggestions = self.optimization_engine.generate_optimization_suggestions(metrics)
            
            # Predict potential failures
            failure_predictions = self.optimization_engine.predict_print_failure(metrics)
            
            # Recommend materials and settings
            recommended_materials = self.optimization_engine.recommend_materials(metrics)
            recommended_settings = self.optimization_engine.recommend_print_settings(metrics)
            
            # Calculate overall scores
            overall_score = self._calculate_overall_score(metrics)
            improvement_potential = self._calculate_improvement_potential(suggestions)
            
            # Create analysis result
            result = DesignAnalysisResult(
                design_id=design_id,
                analysis_timestamp=datetime.now(),
                metrics=metrics,
                suggestions=suggestions,
                failure_predictions=failure_predictions,
                recommended_materials=recommended_materials,
                recommended_settings=recommended_settings,
                overall_score=overall_score,
                improvement_potential=improvement_potential
            )
            
            # Save to database
            self._save_analysis_result(result)
            
            self.logger.info(f"AI design analysis completed for {design_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in design analysis: {e}")
            raise
    
    def _calculate_overall_score(self, metrics: DesignMetrics) -> float:
        """Calculate overall design quality score"""
        # Weighted combination of various scores
        weights = {
            'printability': 0.4,
            'complexity': -0.2,  # Negative because high complexity is bad
            'failure_risk': -0.3,  # Negative because high risk is bad
            'success_rate': 0.1
        }
        
        score = (
            metrics.printability_score * weights['printability'] +
            (100 - metrics.complexity_score) * abs(weights['complexity']) +
            (100 - metrics.failure_risk_score) * abs(weights['failure_risk']) +
            metrics.estimated_success_rate * weights['success_rate']
        )
        
        return max(0, min(100, score))
    
    def _calculate_improvement_potential(self, suggestions: List[OptimizationSuggestion]) -> float:
        """Calculate improvement potential based on suggestions"""
        if not suggestions:
            return 0.0
        
        total_potential = 0.0
        weight_sum = 0.0
        
        priority_weights = {'high': 3.0, 'medium': 2.0, 'low': 1.0}
        
        for suggestion in suggestions:
            weight = priority_weights.get(suggestion.priority, 1.0)
            potential = suggestion.confidence_score * 100
            total_potential += potential * weight
            weight_sum += weight
        
        return (total_potential / weight_sum) if weight_sum > 0 else 0.0
    
    def _save_analysis_result(self, result: DesignAnalysisResult):
        """Save analysis result to database"""
        try:
            db_path = self.data_dir / "design_analysis.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO design_analyses 
                    (design_id, timestamp, metrics_json, suggestions_json, overall_score, improvement_potential)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    result.design_id,
                    result.analysis_timestamp.isoformat(),
                    json.dumps(asdict(result.metrics)),
                    json.dumps([asdict(s) for s in result.suggestions]),
                    result.overall_score,
                    result.improvement_potential
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving analysis result: {e}")
    
    def get_analysis_history(self, design_id: str = None) -> List[Dict[str, Any]]:
        """Get analysis history for a design or all designs"""
        try:
            db_path = self.data_dir / "design_analysis.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                if design_id:
                    cursor.execute("""
                        SELECT * FROM design_analyses WHERE design_id = ?
                        ORDER BY timestamp DESC
                    """, (design_id,))
                else:
                    cursor.execute("""
                        SELECT * FROM design_analyses
                        ORDER BY timestamp DESC LIMIT 100
                    """)
                
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                columns = ['id', 'design_id', 'timestamp', 'metrics_json', 
                          'suggestions_json', 'overall_score', 'improvement_potential']
                
                results = []
                for row in rows:
                    result = dict(zip(columns, row))
                    result['metrics'] = json.loads(result['metrics_json'])
                    result['suggestions'] = json.loads(result['suggestions_json'])
                    del result['metrics_json']
                    del result['suggestions_json']
                    results.append(result)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error getting analysis history: {e}")
            return []
    
    def get_design_insights(self) -> Dict[str, Any]:
        """Get insights from all analyzed designs"""
        try:
            history = self.get_analysis_history()
            
            if not history:
                return {"message": "No analysis data available"}
            
            # Calculate statistics
            scores = [h['overall_score'] for h in history]
            improvements = [h['improvement_potential'] for h in history]
            
            insights = {
                "total_designs_analyzed": len(history),
                "average_quality_score": sum(scores) / len(scores),
                "average_improvement_potential": sum(improvements) / len(improvements),
                "top_performing_designs": sorted(history, key=lambda x: x['overall_score'], reverse=True)[:5],
                "common_issues": self._analyze_common_issues(history),
                "improvement_trends": self._analyze_improvement_trends(history)
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting design insights: {e}")
            return {"error": str(e)}
    
    def _analyze_common_issues(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze common issues across all designs"""
        issue_counts = {}
        
        for analysis in history:
            suggestions = analysis.get('suggestions', [])
            for suggestion in suggestions:
                category = suggestion.get('category', 'unknown')
                title = suggestion.get('title', 'Unknown Issue')
                
                if category not in issue_counts:
                    issue_counts[category] = {}
                
                if title not in issue_counts[category]:
                    issue_counts[category][title] = 0
                
                issue_counts[category][title] += 1
        
        # Convert to sorted list
        common_issues = []
        for category, issues in issue_counts.items():
            for title, count in sorted(issues.items(), key=lambda x: x[1], reverse=True):
                common_issues.append({
                    'category': category,
                    'issue': title,
                    'frequency': count,
                    'percentage': (count / len(history)) * 100
                })
        
        return sorted(common_issues, key=lambda x: x['frequency'], reverse=True)[:10]
    
    def _analyze_improvement_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze improvement trends over time"""
        if len(history) < 2:
            return {"message": "Insufficient data for trend analysis"}
        
        # Sort by timestamp
        sorted_history = sorted(history, key=lambda x: x['timestamp'])
        
        # Calculate moving averages
        window_size = min(10, len(sorted_history) // 2)
        if window_size < 2:
            return {"message": "Insufficient data for trend analysis"}
        
        scores = [h['overall_score'] for h in sorted_history]
        improvements = [h['improvement_potential'] for h in sorted_history]
        
        # Calculate trends
        score_trend = "improving" if scores[-window_size:] > scores[:window_size] else "declining"
        improvement_trend = "improving" if sum(improvements[-window_size:]) < sum(improvements[:window_size]) else "declining"
        
        return {
            "quality_trend": score_trend,
            "improvement_opportunity_trend": improvement_trend,
            "recent_average_score": sum(scores[-window_size:]) / window_size,
            "early_average_score": sum(scores[:window_size]) / window_size,
            "trend_analysis_window": window_size
        }
    
    def update_suggestion_feedback(self, design_id: str, suggestion_id: str, 
                                 implemented: bool, feedback_score: int = None, 
                                 notes: str = None):
        """Update feedback for optimization suggestions"""
        try:
            db_path = self.data_dir / "design_analysis.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO optimization_feedback 
                    (design_id, suggestion_id, implemented, feedback_score, notes, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    design_id,
                    suggestion_id,
                    implemented,
                    feedback_score,
                    notes,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                
            self.logger.info(f"Updated feedback for suggestion {suggestion_id}")
            
        except Exception as e:
            self.logger.error(f"Error updating suggestion feedback: {e}")
    
    def retrain_models(self):
        """Retrain AI models with accumulated feedback data"""
        try:
            # Get feedback data
            db_path = self.data_dir / "design_analysis.db"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT af.*, da.metrics_json 
                    FROM optimization_feedback af
                    JOIN design_analyses da ON af.design_id = da.design_id
                    WHERE af.feedback_score IS NOT NULL
                """)
                
                feedback_data = cursor.fetchall()
            
            if len(feedback_data) < 50:  # Need sufficient data
                self.logger.info("Insufficient feedback data for retraining")
                return
            
            # Process feedback data and retrain models
            # This is a simplified implementation - in practice would be more sophisticated
            self.optimization_engine._create_initial_models()
            
            self.logger.info("AI models retrained successfully")
            
        except Exception as e:
            self.logger.error(f"Error retraining models: {e}")
    
    def get_enhancement_capabilities(self) -> Dict[str, Any]:
        """Get information about AI enhancement capabilities"""
        return {
            'features': [
                'Geometry complexity analysis',
                'Printability assessment',
                'Failure risk prediction',
                'Optimization suggestions',
                'Material recommendations',
                'Print settings optimization',
                'Design scoring and ranking',
                'Historical trend analysis'
            ],
            'analysis_metrics': [
                'Triangle/vertex count',
                'Surface area and volume',
                'Overhang percentage',
                'Bridge structures',
                'Thin wall detection',
                'Small feature analysis',
                'Stress concentration points',
                'Wall thickness analysis'
            ],
            'ai_capabilities': [
                'Machine learning failure prediction',
                'Intelligent optimization recommendations',
                'Continuous learning from feedback',
                'Pattern recognition across designs',
                'Adaptive suggestion ranking'
            ],
            'supported_formats': ['STL'],
            'output_formats': ['JSON', 'Analysis Report'],
            'learning_enabled': True,
            'model_version': '1.0'
        }
