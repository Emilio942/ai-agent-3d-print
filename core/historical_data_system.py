"""
Historical Data & Learning System for AI Agent 3D Print System

This module provides comprehensive historical data tracking, analytics, and 
continuous learning capabilities for the 3D printing system. It tracks print
history, analyzes patterns, learns from successes and failures, and provides
insights for continuous improvement.

Features:
- Print history tracking and storage
- Success/failure pattern analysis
- User preference learning
- Performance trend analytics
- Predictive modeling for future prints
- Continuous improvement recommendations
"""

import json
import logging
import sqlite3
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import defaultdict, Counter

from core.logger import get_logger

logger = get_logger(__name__)

class PrintStatus(Enum):
    """Print job status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class FailureType(Enum):
    """Print failure type classification"""
    WARPING = "warping"
    LAYER_ADHESION = "layer_adhesion"
    SUPPORT_FAILURE = "support_failure"
    STRINGING = "stringing"
    UNDER_EXTRUSION = "under_extrusion"
    OVER_EXTRUSION = "over_extrusion"
    NOZZLE_CLOG = "nozzle_clog"
    FILAMENT_RUNOUT = "filament_runout"
    POWER_FAILURE = "power_failure"
    MECHANICAL_ISSUE = "mechanical_issue"
    USER_CANCELLED = "user_cancelled"
    DESIGN_ISSUE = "design_issue"
    UNKNOWN = "unknown"

@dataclass
class PrintJob:
    """Complete print job information"""
    job_id: str
    user_id: str
    design_name: str
    design_file_path: str
    
    # Print parameters
    material_type: str
    layer_height: float
    infill_percentage: int
    print_speed: int
    nozzle_temperature: int
    bed_temperature: int
    support_enabled: bool
    
    # Timing information
    start_time: datetime
    end_time: Optional[datetime]
    estimated_duration: float  # hours
    actual_duration: Optional[float]  # hours
    
    # Status and outcome
    status: PrintStatus
    success_rating: Optional[int]  # 1-10 scale
    failure_type: Optional[FailureType]
    failure_description: Optional[str]
    
    # Quality metrics
    surface_quality: Optional[int]  # 1-10 scale
    dimensional_accuracy: Optional[int]  # 1-10 scale
    structural_integrity: Optional[int]  # 1-10 scale
    
    # Resource usage
    filament_used: Optional[float]  # grams
    estimated_filament: Optional[float]  # grams
    energy_consumed: Optional[float]  # kWh
    
    # User feedback
    user_notes: Optional[str]
    would_print_again: Optional[bool]
    
    # Design metrics (from AI analysis)
    design_complexity: Optional[float]
    printability_score: Optional[float]
    ai_suggestions_count: Optional[int]
    ai_suggestions_implemented: Optional[int]

@dataclass
class UserPreferences:
    """User printing preferences learned from history"""
    user_id: str
    
    # Material preferences
    preferred_materials: List[str]
    avoided_materials: List[str]
    
    # Quality vs speed preference (0.0 = speed, 1.0 = quality)
    quality_preference: float
    
    # Common settings
    typical_layer_height: float
    typical_infill: int
    typical_speed: int
    
    # Risk tolerance (0.0 = conservative, 1.0 = experimental)
    risk_tolerance: float
    
    # Success patterns
    successful_combinations: List[Dict[str, Any]]
    problematic_combinations: List[Dict[str, Any]]
    
    # Learning metadata
    data_points: int
    confidence_score: float
    last_updated: datetime

@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    period_start: datetime
    period_end: datetime
    
    # Print statistics
    total_prints: int
    successful_prints: int
    failed_prints: int
    success_rate: float
    
    # Time metrics
    average_print_time: float
    total_print_time: float
    time_estimation_accuracy: float
    
    # Quality metrics
    average_quality_rating: float
    average_surface_quality: float
    average_dimensional_accuracy: float
    
    # Resource efficiency
    average_filament_efficiency: float  # actual vs estimated
    total_filament_used: float
    average_energy_consumption: float
    
    # Failure analysis
    common_failure_types: List[Tuple[FailureType, int]]
    failure_trends: Dict[str, float]
    
    # Improvement metrics
    quality_trend: str  # "improving", "declining", "stable"
    efficiency_trend: str
    learning_effectiveness: float

class HistoricalDataManager:
    """Manages historical print data storage and retrieval"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/history")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "print_history.db"
        self.logger = get_logger(f"{__name__}.HistoricalDataManager")
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for historical data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Print jobs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS print_jobs (
                        job_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        design_name TEXT NOT NULL,
                        design_file_path TEXT,
                        
                        material_type TEXT NOT NULL,
                        layer_height REAL NOT NULL,
                        infill_percentage INTEGER NOT NULL,
                        print_speed INTEGER NOT NULL,
                        nozzle_temperature INTEGER NOT NULL,
                        bed_temperature INTEGER NOT NULL,
                        support_enabled BOOLEAN NOT NULL,
                        
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        estimated_duration REAL NOT NULL,
                        actual_duration REAL,
                        
                        status TEXT NOT NULL,
                        success_rating INTEGER,
                        failure_type TEXT,
                        failure_description TEXT,
                        
                        surface_quality INTEGER,
                        dimensional_accuracy INTEGER,
                        structural_integrity INTEGER,
                        
                        filament_used REAL,
                        estimated_filament REAL,
                        energy_consumed REAL,
                        
                        user_notes TEXT,
                        would_print_again BOOLEAN,
                        
                        design_complexity REAL,
                        printability_score REAL,
                        ai_suggestions_count INTEGER,
                        ai_suggestions_implemented INTEGER,
                        
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # User preferences table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY,
                        preferences_json TEXT NOT NULL,
                        last_updated TEXT NOT NULL,
                        data_points INTEGER NOT NULL DEFAULT 0,
                        confidence_score REAL NOT NULL DEFAULT 0.0
                    )
                """)
                
                # Performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        period_start TEXT NOT NULL,
                        period_end TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Learning insights table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS learning_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        insight_type TEXT NOT NULL,
                        insight_data TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON print_jobs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON print_jobs(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_start_time ON print_jobs(start_time)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_material ON print_jobs(material_type)")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def add_print_job(self, job: PrintJob) -> bool:
        """Add a new print job to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO print_jobs VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    job.job_id, job.user_id, job.design_name, job.design_file_path,
                    job.material_type, job.layer_height, job.infill_percentage,
                    job.print_speed, job.nozzle_temperature, job.bed_temperature,
                    job.support_enabled, job.start_time.isoformat(),
                    job.end_time.isoformat() if job.end_time else None,
                    job.estimated_duration, job.actual_duration,
                    job.status.value, job.success_rating,
                    job.failure_type.value if job.failure_type else None,
                    job.failure_description, job.surface_quality,
                    job.dimensional_accuracy, job.structural_integrity,
                    job.filament_used, job.estimated_filament, job.energy_consumed,
                    job.user_notes, job.would_print_again,
                    job.design_complexity, job.printability_score,
                    job.ai_suggestions_count, job.ai_suggestions_implemented,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                
            self.logger.info(f"Added print job {job.job_id} to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding print job: {e}")
            return False
    
    def get_print_job(self, job_id: str) -> Optional[PrintJob]:
        """Retrieve a specific print job"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM print_jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_print_job(row)
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving print job {job_id}: {e}")
            return None
    
    def get_user_print_history(self, user_id: str, limit: int = 100) -> List[PrintJob]:
        """Get print history for a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM print_jobs 
                    WHERE user_id = ? 
                    ORDER BY start_time DESC 
                    LIMIT ?
                """, (user_id, limit))
                
                rows = cursor.fetchall()
                return [self._row_to_print_job(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error retrieving user history for {user_id}: {e}")
            return []
    
    def get_print_statistics(self, user_id: str = None, 
                           days: int = 30) -> Dict[str, Any]:
        """Get print statistics for a user or globally"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query conditions
                conditions = []
                params = []
                
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                if days:
                    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                    conditions.append("start_time >= ?")
                    params.append(cutoff_date)
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                
                # Get basic statistics
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_prints,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        AVG(actual_duration) as avg_duration,
                        AVG(success_rating) as avg_rating,
                        SUM(filament_used) as total_filament,
                        AVG(filament_used) as avg_filament
                    FROM print_jobs {where_clause}
                """, params)
                
                stats = cursor.fetchone()
                
                if stats[0] == 0:  # No prints found
                    return {"message": "No print data found for the specified criteria"}
                
                return {
                    "total_prints": stats[0],
                    "successful_prints": stats[1] or 0,
                    "failed_prints": stats[2] or 0,
                    "success_rate": (stats[1] or 0) / stats[0] * 100,
                    "average_duration_hours": stats[3] or 0,
                    "average_rating": stats[4] or 0,
                    "total_filament_grams": stats[5] or 0,
                    "average_filament_per_print": stats[6] or 0
                }
                
        except Exception as e:
            self.logger.error(f"Error getting print statistics: {e}")
            return {"error": str(e)}
    
    def _row_to_print_job(self, row) -> PrintJob:
        """Convert database row to PrintJob object"""
        return PrintJob(
            job_id=row[0],
            user_id=row[1],
            design_name=row[2],
            design_file_path=row[3],
            material_type=row[4],
            layer_height=row[5],
            infill_percentage=row[6],
            print_speed=row[7],
            nozzle_temperature=row[8],
            bed_temperature=row[9],
            support_enabled=bool(row[10]),
            start_time=datetime.fromisoformat(row[11]),
            end_time=datetime.fromisoformat(row[12]) if row[12] else None,
            estimated_duration=row[13],
            actual_duration=row[14],
            status=PrintStatus(row[15]),
            success_rating=row[16],
            failure_type=FailureType(row[17]) if row[17] else None,
            failure_description=row[18],
            surface_quality=row[19],
            dimensional_accuracy=row[20],
            structural_integrity=row[21],
            filament_used=row[22],
            estimated_filament=row[23],
            energy_consumed=row[24],
            user_notes=row[25],
            would_print_again=bool(row[26]) if row[26] is not None else None,
            design_complexity=row[27],
            printability_score=row[28],
            ai_suggestions_count=row[29],
            ai_suggestions_implemented=row[30]
        )

class LearningEngine:
    """Machine learning and pattern recognition engine"""
    
    def __init__(self, data_manager: HistoricalDataManager):
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.LearningEngine")
    
    def learn_user_preferences(self, user_id: str) -> UserPreferences:
        """Learn and update user preferences from print history"""
        try:
            # Get user's print history
            history = self.data_manager.get_user_print_history(user_id, limit=200)
            
            if len(history) < 5:
                # Insufficient data, return defaults
                return UserPreferences(
                    user_id=user_id,
                    preferred_materials=["PLA"],
                    avoided_materials=[],
                    quality_preference=0.5,
                    typical_layer_height=0.2,
                    typical_infill=20,
                    typical_speed=50,
                    risk_tolerance=0.3,
                    successful_combinations=[],
                    problematic_combinations=[],
                    data_points=len(history),
                    confidence_score=0.1,
                    last_updated=datetime.now()
                )
            
            # Analyze successful vs failed prints
            successful_prints = [job for job in history if job.status == PrintStatus.COMPLETED 
                               and (job.success_rating or 0) >= 7]
            failed_prints = [job for job in history if job.status == PrintStatus.FAILED]
            
            # Learn material preferences
            material_success = defaultdict(int)
            material_total = defaultdict(int)
            
            for job in history:
                material_total[job.material_type] += 1
                if job in successful_prints:
                    material_success[job.material_type] += 1
            
            # Calculate success rates for materials
            material_success_rates = {}
            for material, total in material_total.items():
                if total >= 3:  # Only consider materials with sufficient data
                    success_rate = material_success[material] / total
                    material_success_rates[material] = success_rate
            
            preferred_materials = [material for material, rate in material_success_rates.items() 
                                 if rate >= 0.8]
            avoided_materials = [material for material, rate in material_success_rates.items() 
                               if rate <= 0.3]
            
            if not preferred_materials:  # Fallback
                preferred_materials = ["PLA"]
            
            # Learn quality vs speed preference
            quality_jobs = [job for job in successful_prints if job.layer_height <= 0.15]
            speed_jobs = [job for job in successful_prints if job.print_speed >= 80]
            
            quality_preference = len(quality_jobs) / (len(quality_jobs) + len(speed_jobs)) \
                               if (len(quality_jobs) + len(speed_jobs)) > 0 else 0.5
            
            # Learn typical settings
            successful_settings = {
                'layer_heights': [job.layer_height for job in successful_prints],
                'infills': [job.infill_percentage for job in successful_prints],
                'speeds': [job.print_speed for job in successful_prints]
            }
            
            typical_layer_height = statistics.median(successful_settings['layer_heights']) \
                                 if successful_settings['layer_heights'] else 0.2
            typical_infill = int(statistics.median(successful_settings['infills'])) \
                           if successful_settings['infills'] else 20
            typical_speed = int(statistics.median(successful_settings['speeds'])) \
                          if successful_settings['speeds'] else 50
            
            # Learn risk tolerance
            experimental_jobs = [job for job in history if 
                                job.ai_suggestions_implemented and job.ai_suggestions_implemented > 0]
            risk_tolerance = len(experimental_jobs) / len(history) if history else 0.3
            
            # Find successful and problematic combinations
            successful_combinations = self._extract_setting_combinations(successful_prints)
            problematic_combinations = self._extract_setting_combinations(failed_prints)
            
            # Calculate confidence score
            confidence_score = min(len(history) / 50.0, 1.0)  # Full confidence at 50+ prints
            
            preferences = UserPreferences(
                user_id=user_id,
                preferred_materials=preferred_materials,
                avoided_materials=avoided_materials,
                quality_preference=quality_preference,
                typical_layer_height=typical_layer_height,
                typical_infill=typical_infill,
                typical_speed=typical_speed,
                risk_tolerance=risk_tolerance,
                successful_combinations=successful_combinations[:10],  # Top 10
                problematic_combinations=problematic_combinations[:5],  # Top 5
                data_points=len(history),
                confidence_score=confidence_score,
                last_updated=datetime.now()
            )
            
            # Save preferences to database
            self._save_user_preferences(preferences)
            
            return preferences
            
        except Exception as e:
            self.logger.error(f"Error learning user preferences: {e}")
            raise
    
    def _extract_setting_combinations(self, jobs: List[PrintJob]) -> List[Dict[str, Any]]:
        """Extract common setting combinations from print jobs"""
        combinations = []
        
        for job in jobs:
            combination = {
                'material_type': job.material_type,
                'layer_height': job.layer_height,
                'infill_percentage': job.infill_percentage,
                'print_speed': job.print_speed,
                'nozzle_temperature': job.nozzle_temperature,
                'bed_temperature': job.bed_temperature,
                'support_enabled': job.support_enabled,
                'success_rating': job.success_rating
            }
            combinations.append(combination)
        
        # Group similar combinations and count frequency
        grouped_combinations = defaultdict(list)
        for combo in combinations:
            # Create a key for grouping (rounded values for similar settings)
            key = (
                combo['material_type'],
                round(combo['layer_height'], 1),
                combo['infill_percentage'] // 5 * 5,  # Group by 5% increments
                combo['print_speed'] // 10 * 10,      # Group by 10mm/s increments
                combo['nozzle_temperature'] // 5 * 5, # Group by 5°C increments
                combo['support_enabled']
            )
            grouped_combinations[key].append(combo)
        
        # Sort by frequency and average success rating
        result = []
        for key, group in grouped_combinations.items():
            if len(group) >= 2:  # Only include combinations used multiple times
                avg_rating = statistics.mean([c['success_rating'] or 5 for c in group])
                frequency = len(group)
                
                representative = group[0].copy()
                representative['frequency'] = frequency
                representative['average_rating'] = avg_rating
                
                result.append(representative)
        
        # Sort by frequency then by rating
        result.sort(key=lambda x: (x['frequency'], x['average_rating']), reverse=True)
        return result
    
    def _save_user_preferences(self, preferences: UserPreferences):
        """Save user preferences to database"""
        try:
            with sqlite3.connect(self.data_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO user_preferences 
                    (user_id, preferences_json, last_updated, data_points, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    preferences.user_id,
                    json.dumps(asdict(preferences), default=str),
                    preferences.last_updated.isoformat(),
                    preferences.data_points,
                    preferences.confidence_score
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error saving user preferences: {e}")
    
    def analyze_failure_patterns(self, days: int = 90) -> Dict[str, Any]:
        """Analyze failure patterns across all prints"""
        try:
            with sqlite3.connect(self.data_manager.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # Get failure data
                cursor.execute("""
                    SELECT failure_type, material_type, layer_height, 
                           nozzle_temperature, bed_temperature, support_enabled,
                           design_complexity, printability_score
                    FROM print_jobs 
                    WHERE status = 'failed' AND start_time >= ?
                """, (cutoff_date,))
                
                failures = cursor.fetchall()
                
                if not failures:
                    return {"message": "No failure data found"}
                
                # Analyze patterns
                failure_counts = Counter([f[0] for f in failures if f[0]])
                material_failures = defaultdict(list)
                temperature_failures = defaultdict(list)
                
                for failure in failures:
                    failure_type, material, layer_height, nozzle_temp, bed_temp, supports, complexity, printability = failure
                    
                    if material:
                        material_failures[material].append(failure_type)
                    
                    if nozzle_temp:
                        temp_range = f"{nozzle_temp//10*10}-{nozzle_temp//10*10+9}°C"
                        temperature_failures[temp_range].append(failure_type)
                
                return {
                    "analysis_period_days": days,
                    "total_failures": len(failures),
                    "most_common_failures": dict(failure_counts.most_common(5)),
                    "material_failure_patterns": dict(material_failures),
                    "temperature_failure_patterns": dict(temperature_failures),
                    "recommendations": self._generate_failure_recommendations(failure_counts, material_failures)
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing failure patterns: {e}")
            return {"error": str(e)}
    
    def _generate_failure_recommendations(self, failure_counts: Counter, 
                                        material_failures: Dict) -> List[str]:
        """Generate recommendations based on failure analysis"""
        recommendations = []
        
        # Most common failure recommendations
        if failure_counts:
            most_common = failure_counts.most_common(1)[0]
            failure_type, count = most_common
            
            if failure_type == "warping":
                recommendations.append("Consider using a heated bed or better bed adhesion")
            elif failure_type == "layer_adhesion":
                recommendations.append("Check nozzle temperature and print speed settings")
            elif failure_type == "support_failure":
                recommendations.append("Optimize support density and overhang angles")
            elif failure_type == "stringing":
                recommendations.append("Adjust retraction settings and temperature")
        
        # Material-specific recommendations
        for material, failures in material_failures.items():
            material_counter = Counter(failures)
            if material_counter:
                most_common_for_material = material_counter.most_common(1)[0][0]
                recommendations.append(f"For {material}: focus on preventing {most_common_for_material}")
        
        return recommendations[:5]  # Limit to 5 recommendations

class PerformanceAnalyzer:
    """Analyzes system performance and generates insights"""
    
    def __init__(self, data_manager: HistoricalDataManager):
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.PerformanceAnalyzer")
    
    def generate_performance_report(self, days: int = 30) -> PerformanceMetrics:
        """Generate comprehensive performance report"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            with sqlite3.connect(self.data_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all prints in the period
                cursor.execute("""
                    SELECT * FROM print_jobs 
                    WHERE start_time >= ? AND start_time <= ?
                """, (start_date.isoformat(), end_date.isoformat()))
                
                rows = cursor.fetchall()
                jobs = [self.data_manager._row_to_print_job(row) for row in rows]
                
                if not jobs:
                    return self._empty_performance_metrics(start_date, end_date)
                
                # Calculate metrics
                total_prints = len(jobs)
                successful_prints = len([j for j in jobs if j.status == PrintStatus.COMPLETED])
                failed_prints = len([j for j in jobs if j.status == PrintStatus.FAILED])
                success_rate = (successful_prints / total_prints * 100) if total_prints > 0 else 0
                
                # Time metrics
                completed_jobs = [j for j in jobs if j.actual_duration is not None]
                avg_print_time = statistics.mean([j.actual_duration for j in completed_jobs]) \
                               if completed_jobs else 0
                total_print_time = sum([j.actual_duration for j in completed_jobs])
                
                # Time estimation accuracy
                accurate_estimates = [j for j in completed_jobs if j.estimated_duration > 0]
                time_accuracy = 100 - statistics.mean([
                    abs(j.actual_duration - j.estimated_duration) / j.estimated_duration * 100
                    for j in accurate_estimates
                ]) if accurate_estimates else 0
                
                # Quality metrics
                rated_jobs = [j for j in jobs if j.success_rating is not None]
                avg_quality = statistics.mean([j.success_rating for j in rated_jobs]) \
                            if rated_jobs else 0
                
                surface_quality_jobs = [j for j in jobs if j.surface_quality is not None]
                avg_surface_quality = statistics.mean([j.surface_quality for j in surface_quality_jobs]) \
                                    if surface_quality_jobs else 0
                
                dimensional_jobs = [j for j in jobs if j.dimensional_accuracy is not None]
                avg_dimensional = statistics.mean([j.dimensional_accuracy for j in dimensional_jobs]) \
                                if dimensional_jobs else 0
                
                # Resource efficiency
                filament_jobs = [j for j in jobs if j.filament_used and j.estimated_filament]
                avg_filament_efficiency = statistics.mean([
                    j.filament_used / j.estimated_filament * 100
                    for j in filament_jobs
                ]) if filament_jobs else 100
                
                total_filament = sum([j.filament_used for j in jobs if j.filament_used]) or 0
                
                energy_jobs = [j for j in jobs if j.energy_consumed]
                avg_energy = statistics.mean([j.energy_consumed for j in energy_jobs]) \
                           if energy_jobs else 0
                
                # Failure analysis
                failure_types = [j.failure_type for j in jobs if j.failure_type]
                common_failures = Counter(failure_types).most_common(5)
                
                # Calculate trends (simplified)
                quality_trend = self._calculate_trend([j.success_rating for j in rated_jobs])
                efficiency_trend = self._calculate_trend([j.actual_duration for j in completed_jobs])
                
                return PerformanceMetrics(
                    period_start=start_date,
                    period_end=end_date,
                    total_prints=total_prints,
                    successful_prints=successful_prints,
                    failed_prints=failed_prints,
                    success_rate=success_rate,
                    average_print_time=avg_print_time,
                    total_print_time=total_print_time,
                    time_estimation_accuracy=time_accuracy,
                    average_quality_rating=avg_quality,
                    average_surface_quality=avg_surface_quality,
                    average_dimensional_accuracy=avg_dimensional,
                    average_filament_efficiency=avg_filament_efficiency,
                    total_filament_used=total_filament,
                    average_energy_consumption=avg_energy,
                    common_failure_types=common_failures,
                    failure_trends={},  # Would calculate with more historical data
                    quality_trend=quality_trend,
                    efficiency_trend=efficiency_trend,
                    learning_effectiveness=self._calculate_learning_effectiveness(jobs)
                )
                
        except Exception as e:
            self.logger.error(f"Error generating performance report: {e}")
            return self._empty_performance_metrics(start_date, end_date)
    
    def _empty_performance_metrics(self, start_date: datetime, 
                                 end_date: datetime) -> PerformanceMetrics:
        """Return empty performance metrics"""
        return PerformanceMetrics(
            period_start=start_date,
            period_end=end_date,
            total_prints=0,
            successful_prints=0,
            failed_prints=0,
            success_rate=0,
            average_print_time=0,
            total_print_time=0,
            time_estimation_accuracy=0,
            average_quality_rating=0,
            average_surface_quality=0,
            average_dimensional_accuracy=0,
            average_filament_efficiency=0,
            total_filament_used=0,
            average_energy_consumption=0,
            common_failure_types=[],
            failure_trends={},
            quality_trend="stable",
            efficiency_trend="stable",
            learning_effectiveness=0
        )
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate if trend is improving, declining, or stable"""
        if len(values) < 4:
            return "stable"
        
        mid_point = len(values) // 2
        first_half = values[:mid_point]
        second_half = values[mid_point:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        change_percentage = (second_avg - first_avg) / first_avg * 100 if first_avg > 0 else 0
        
        if change_percentage > 5:
            return "improving"
        elif change_percentage < -5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_learning_effectiveness(self, jobs: List[PrintJob]) -> float:
        """Calculate how effective the AI learning system is"""
        ai_jobs = [j for j in jobs if j.ai_suggestions_count and j.ai_suggestions_count > 0]
        
        if not ai_jobs:
            return 0.0
        
        # Calculate success rate for jobs with AI suggestions
        successful_ai_jobs = [j for j in ai_jobs if j.status == PrintStatus.COMPLETED 
                             and (j.success_rating or 0) >= 7]
        
        ai_success_rate = len(successful_ai_jobs) / len(ai_jobs) * 100
        
        # Compare to overall success rate
        overall_successful = [j for j in jobs if j.status == PrintStatus.COMPLETED 
                            and (j.success_rating or 0) >= 7]
        overall_success_rate = len(overall_successful) / len(jobs) * 100 if jobs else 0
        
        # Learning effectiveness is the improvement over baseline
        improvement = ai_success_rate - overall_success_rate
        return max(0, min(100, improvement + 50))  # Normalize to 0-100 scale

class HistoricalDataSystem:
    """Main historical data and learning system"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/historical")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.data_manager = HistoricalDataManager(self.data_dir)
        self.learning_engine = LearningEngine(self.data_manager)
        self.performance_analyzer = PerformanceAnalyzer(self.data_manager)
        self.logger = get_logger(f"{__name__}.HistoricalDataSystem")
    
    def add_print_result(self, job: PrintJob) -> bool:
        """Add a completed print job to the historical database"""
        try:
            success = self.data_manager.add_print_job(job)
            
            if success:
                # Trigger learning update for the user
                self.learning_engine.learn_user_preferences(job.user_id)
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error adding print result: {e}")
            return False
    
    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive insights for a user"""
        try:
            # Get user preferences
            preferences = self.learning_engine.learn_user_preferences(user_id)
            
            # Get user statistics
            stats = self.data_manager.get_print_statistics(user_id=user_id, days=90)
            
            # Get recent performance
            history = self.data_manager.get_user_print_history(user_id, limit=10)
            
            return {
                "user_id": user_id,
                "preferences": asdict(preferences),
                "statistics": stats,
                "recent_prints": len(history),
                "learning_confidence": preferences.confidence_score,
                "recommendations": self._generate_user_recommendations(preferences, stats)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user insights: {e}")
            return {"error": str(e)}
    
    def get_system_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get system-wide performance metrics"""
        try:
            metrics = self.performance_analyzer.generate_performance_report(days)
            failure_analysis = self.learning_engine.analyze_failure_patterns(days)
            
            return {
                "performance_metrics": asdict(metrics),
                "failure_analysis": failure_analysis,
                "analysis_period_days": days
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system performance: {e}")
            return {"error": str(e)}
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about the learning system effectiveness"""
        try:
            # Get overall statistics
            overall_stats = self.data_manager.get_print_statistics(days=90)
            
            # Get performance metrics
            performance = self.performance_analyzer.generate_performance_report(30)
            
            return {
                "system_overview": overall_stats,
                "learning_effectiveness": performance.learning_effectiveness,
                "quality_trend": performance.quality_trend,
                "success_rate": performance.success_rate,
                "total_data_points": overall_stats.get("total_prints", 0),
                "insights_available": overall_stats.get("total_prints", 0) >= 20
            }
            
        except Exception as e:
            self.logger.error(f"Error getting learning insights: {e}")
            return {"error": str(e)}
    
    def _generate_user_recommendations(self, preferences: UserPreferences, 
                                     stats: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations for a user"""
        recommendations = []
        
        # Success rate recommendations
        success_rate = stats.get("success_rate", 0)
        if success_rate < 70:
            recommendations.append("Consider using more conservative print settings to improve success rate")
        
        # Material recommendations
        if len(preferences.preferred_materials) == 1:
            recommendations.append("Try experimenting with different materials to expand your experience")
        
        # Quality vs speed recommendations
        if preferences.quality_preference < 0.3:
            recommendations.append("Consider occasionally prioritizing quality for important prints")
        elif preferences.quality_preference > 0.8:
            recommendations.append("You could save time by using faster settings for prototype prints")
        
        # Risk tolerance recommendations
        if preferences.risk_tolerance < 0.2:
            recommendations.append("Consider trying some AI optimization suggestions to improve your prints")
        
        return recommendations[:3]  # Limit to 3 recommendations
    
    def get_historical_capabilities(self) -> Dict[str, Any]:
        """Get information about historical data system capabilities"""
        return {
            "features": [
                "Complete print history tracking",
                "User preference learning",
                "Failure pattern analysis",
                "Performance trend monitoring",
                "Predictive analytics",
                "Continuous improvement insights"
            ],
            "data_points_tracked": [
                "Print parameters and settings",
                "Success/failure outcomes",
                "Quality ratings",
                "Resource usage",
                "User feedback",
                "AI suggestion effectiveness"
            ],
            "learning_capabilities": [
                "Material preference detection",
                "Quality vs speed preference",
                "Risk tolerance assessment",
                "Successful setting combinations",
                "Failure pattern recognition"
            ],
            "analytics_provided": [
                "Success rate trends",
                "Quality improvement tracking",
                "Resource efficiency monitoring",
                "Failure type analysis",
                "Learning effectiveness measurement"
            ],
            "minimum_data_for_insights": 5,
            "full_confidence_data_points": 50,
            "retention_period_days": 365
        }
