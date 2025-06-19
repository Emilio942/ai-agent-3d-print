"""
Advanced Analytics API Endpoints for AI Agent 3D Print System

This module provides REST API endpoints for the advanced analytics and monitoring
dashboard, including real-time metrics, performance trends, alerts management,
and system insights.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel

from core.advanced_analytics import AdvancedAnalytics, SystemMetrics, Alert, PerformanceTrend
from core.logger import get_logger
from core.ai_design_enhancer import AIDesignEnhancer
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

logger = get_logger(__name__)

# Initialize analytics system
analytics = AdvancedAnalytics()

# Initialize AI systems
ai_enhancer = AIDesignEnhancer()

# Create router
router = APIRouter(prefix="/api/advanced/analytics", tags=["analytics"])


class AlertAcknowledge(BaseModel):
    """Request model for acknowledging alerts"""
    alert_id: str
    user_id: Optional[str] = None
    notes: Optional[str] = None


class MetricsQuery(BaseModel):
    """Request model for metrics queries"""
    metric_names: List[str]
    time_range: str = "24h"
    aggregation: Optional[str] = "avg"  # avg, min, max, sum


@router.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data including metrics, trends, and alerts"""
    try:
        dashboard_data = await analytics.get_dashboard_data()
        
        return {
            "success": True,
            "data": dashboard_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/current")
async def get_current_metrics():
    """Get current system metrics"""
    try:
        metrics = await analytics.collect_metrics()
        
        return {
            "success": True,
            "metrics": {
                "timestamp": metrics.timestamp.isoformat(),
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "disk_usage": metrics.disk_usage,
                "cache_hit_rate": metrics.cache_hit_rate,
                "active_requests": metrics.active_requests,
                "response_time_avg": metrics.response_time_avg,
                "error_rate": metrics.error_rate,
                "workflow_count": metrics.workflow_count,
                "queue_size": metrics.queue_size
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/history")
async def get_metrics_history(
    metric_name: str = Query(..., description="Name of the metric to retrieve"),
    time_range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    limit: int = Query(1000, description="Maximum number of data points")
):
    """Get historical metrics data"""
    try:
        data_points = await analytics._get_historical_data(metric_name, time_range)
        
        # Limit data points if requested
        if len(data_points) > limit:
            # Sample data points evenly
            step = len(data_points) // limit
            data_points = data_points[::step][:limit]
        
        return {
            "success": True,
            "metric_name": metric_name,
            "time_range": time_range,
            "data_points": [
                {
                    "timestamp": point[0].isoformat(),
                    "value": point[1]
                }
                for point in data_points
            ],
            "count": len(data_points)
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{metric_name}")
async def get_performance_trend(
    metric_name: str,
    time_range: str = Query("24h", description="Time range for trend analysis")
):
    """Get performance trend analysis for a specific metric"""
    try:
        trend = await analytics.analyze_performance_trends(metric_name, time_range)
        
        return {
            "success": True,
            "trend": {
                "metric_name": trend.metric_name,
                "time_range": trend.time_range,
                "trend_direction": trend.trend_direction,
                "change_percentage": trend.change_percentage,
                "prediction_24h": trend.prediction_24h,
                "confidence_score": trend.confidence_score,
                "data_points_count": len(trend.data_points)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: critical, warning, info"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(50, description="Maximum number of alerts to return")
):
    """Get system alerts with optional filtering"""
    try:
        alerts = analytics.alerts.copy()
        
        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limit results
        alerts = alerts[:limit]
        
        return {
            "success": True,
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "category": alert.category,
                    "title": alert.title,
                    "description": alert.description,
                    "threshold_value": alert.threshold_value,
                    "current_value": alert.current_value,
                    "timestamp": alert.timestamp.isoformat(),
                    "acknowledged": alert.acknowledged,
                    "resolved": alert.resolved
                }
                for alert in alerts
            ],
            "total_count": len(analytics.alerts),
            "filtered_count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/acknowledge")
async def acknowledge_alert(request: AlertAcknowledge):
    """Acknowledge an alert"""
    try:
        success = await analytics.acknowledge_alert(request.alert_id)
        
        if success:
            return {
                "success": True,
                "message": f"Alert {request.alert_id} acknowledged successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-score")
async def get_health_score():
    """Get current system health score"""
    try:
        current_metrics = await analytics.collect_metrics()
        health_score = await analytics._calculate_health_score(current_metrics)
        
        # Determine status
        if health_score > 80:
            status = "healthy"
            color = "green"
        elif health_score > 60:
            status = "warning"
            color = "yellow"
        else:
            status = "critical"
            color = "red"
        
        return {
            "success": True,
            "health_score": health_score,
            "status": status,
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "cpu": "healthy" if current_metrics.cpu_usage < 75 else "warning" if current_metrics.cpu_usage < 90 else "critical",
                "memory": "healthy" if current_metrics.memory_usage < 70 else "warning" if current_metrics.memory_usage < 85 else "critical",
                "cache": "healthy" if current_metrics.cache_hit_rate > 80 else "warning" if current_metrics.cache_hit_rate > 50 else "critical",
                "response_time": "healthy" if current_metrics.response_time_avg < 500 else "warning" if current_metrics.response_time_avg < 1000 else "critical"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting health score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations():
    """Get performance improvement recommendations"""
    try:
        current_metrics = await analytics.collect_metrics()
        
        # Get trends for key metrics
        key_metrics = ["cpu_usage", "memory_usage", "response_time_avg", "cache_hit_rate"]
        trends = {}
        
        for metric in key_metrics:
            trends[metric] = await analytics.analyze_performance_trends(metric, "24h")
        
        recommendations = await analytics._generate_recommendations(current_metrics, trends)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
            "count": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_analytics_summary():
    """Get comprehensive analytics summary"""
    try:
        summary = await analytics.get_analytics_summary()
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start")
async def start_monitoring(
    background_tasks: BackgroundTasks,
    interval: int = Query(60, description="Monitoring interval in seconds")
):
    """Start continuous monitoring"""
    try:
        # Add monitoring task to background
        background_tasks.add_task(analytics.start_monitoring, interval)
        
        return {
            "success": True,
            "message": f"Monitoring started with {interval}s interval",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop continuous monitoring"""
    try:
        analytics.stop_monitoring()
        
        return {
            "success": True,
            "message": "Monitoring stopped",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/aggregated")
async def get_aggregated_metrics(
    time_range: str = Query("24h", description="Time range for aggregation"),
    metrics: str = Query("cpu_usage,memory_usage,response_time_avg", description="Comma-separated metric names"),
    aggregation: str = Query("avg", description="Aggregation type: avg, min, max")
):
    """Get aggregated metrics data"""
    try:
        metric_list = [m.strip() for m in metrics.split(",")]
        results = {}
        
        for metric_name in metric_list:
            data_points = await analytics._get_historical_data(metric_name, time_range)
            
            if data_points:
                values = [point[1] for point in data_points]
                
                if aggregation == "avg":
                    results[metric_name] = sum(values) / len(values)
                elif aggregation == "min":
                    results[metric_name] = min(values)
                elif aggregation == "max":
                    results[metric_name] = max(values)
                else:
                    results[metric_name] = None
            else:
                results[metric_name] = None
        
        return {
            "success": True,
            "time_range": time_range,
            "aggregation": aggregation,
            "metrics": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting aggregated metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        current_metrics = await analytics.collect_metrics()
        health_score = await analytics._calculate_health_score(current_metrics)
        
        # Count alerts by severity
        alert_counts = {
            "critical": len([a for a in analytics.alerts if a.severity == "critical" and not a.resolved]),
            "warning": len([a for a in analytics.alerts if a.severity == "warning" and not a.resolved]),
            "info": len([a for a in analytics.alerts if a.severity == "info" and not a.resolved])
        }
        
        # System uptime (placeholder - would calculate actual uptime)
        uptime = "99.9%"
        
        return {
            "success": True,
            "system_status": {
                "overall_health": health_score,
                "status": "healthy" if health_score > 80 else "warning" if health_score > 60 else "critical",
                "uptime": uptime,
                "current_load": {
                    "cpu": current_metrics.cpu_usage,
                    "memory": current_metrics.memory_usage,
                    "disk": current_metrics.disk_usage
                },
                "performance": {
                    "avg_response_time": current_metrics.response_time_avg,
                    "cache_hit_rate": current_metrics.cache_hit_rate,
                    "error_rate": current_metrics.error_rate
                },
                "alerts": alert_counts,
                "active_workflows": sum(current_metrics.workflow_count.values()),
                "queue_size": current_metrics.queue_size
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/metrics")
async def export_metrics(
    time_range: str = Query("24h", description="Time range for export"),
    format: str = Query("json", description="Export format: json, csv")
):
    """Export metrics data"""
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'csv'")
        
        # Get data for key metrics
        key_metrics = ["cpu_usage", "memory_usage", "response_time_avg", "cache_hit_rate", "error_rate"]
        export_data = {}
        
        for metric in key_metrics:
            data_points = await analytics._get_historical_data(metric, time_range)
            export_data[metric] = [
                {
                    "timestamp": point[0].isoformat(),
                    "value": point[1]
                }
                for point in data_points
            ]
        
        if format == "json":
            return {
                "success": True,
                "format": "json",
                "time_range": time_range,
                "data": export_data,
                "exported_at": datetime.now().isoformat()
            }
        else:
            # CSV format would require additional processing
            return {
                "success": True,
                "format": "csv",
                "message": "CSV export functionality to be implemented",
                "data": export_data
            }
        
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ML-Powered Analytics Endpoints

@router.get("/ml/failure-prediction")
async def get_failure_prediction():
    """Get ML-powered failure prediction analysis"""
    try:
        from core.ai_design_enhancer import AIOptimizationEngine, DesignMetrics
        
        # Initialize AI engine
        ai_engine = AIOptimizationEngine()
        
        # Get current system metrics
        current_metrics = await analytics.collect_metrics()
        
        # Create design metrics from system metrics (mock data for demonstration)
        design_metrics = DesignMetrics(
            triangle_count=50000,
            surface_area=1500.0,
            volume=800.0,
            bounding_box=(100, 100, 50),
            overhangs_percentage=current_metrics.cpu_usage * 0.5,  # Use CPU as proxy
            thin_walls_count=int(current_metrics.memory_usage * 0.1),
            bridges_count=max(1, int(current_metrics.error_rate * 10)),
            small_features_count=10,
            complexity_score=min(100, current_metrics.cpu_usage + current_metrics.memory_usage),
            printability_score=max(0, 100 - current_metrics.cpu_usage),
            support_required=current_metrics.cpu_usage > 50,
            estimated_print_time=240,
            estimated_material_usage=25.5,
            aspect_ratio=2.0
        )
        
        # Get ML predictions
        failure_predictions = ai_engine.predict_print_failure(design_metrics)
        optimization_suggestions = ai_engine.generate_optimization_suggestions(design_metrics)
        material_recommendations = ai_engine.recommend_materials(design_metrics)
        
        return {
            "success": True,
            "predictions": {
                "failure_risks": failure_predictions,
                "optimization_suggestions": [
                    {
                        "id": suggestion.suggestion_id,
                        "category": suggestion.category,
                        "priority": suggestion.priority,
                        "title": suggestion.title,
                        "description": suggestion.description,
                        "expected_improvement": suggestion.expected_improvement,
                        "difficulty": suggestion.implementation_difficulty,
                        "time_savings": suggestion.estimated_time_savings,
                        "material_savings": suggestion.estimated_material_savings,
                        "confidence": suggestion.confidence_score
                    }
                    for suggestion in optimization_suggestions[:5]  # Top 5 suggestions
                ],
                "material_recommendations": material_recommendations,
                "risk_score": len(failure_predictions) * 20,  # Simple risk scoring
                "system_health_impact": {
                    "cpu_optimized": current_metrics.cpu_usage < 70,
                    "memory_optimized": current_metrics.memory_usage < 80,
                    "performance_optimized": current_metrics.response_time_avg < 500
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ML failure prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/performance-optimization")
async def get_performance_optimization():
    """Get ML-powered performance optimization recommendations"""
    try:
        current_metrics = await analytics.collect_metrics()
        
        # Analyze performance trends
        cpu_trend = await analytics.analyze_performance_trends("cpu_usage", "1h")
        memory_trend = await analytics.analyze_performance_trends("memory_usage", "1h")
        response_trend = await analytics.analyze_performance_trends("response_time_avg", "1h")
        
        # Generate optimization recommendations
        optimizations = []
        
        # CPU optimization
        if current_metrics.cpu_usage > 75:
            optimizations.append({
                "category": "cpu",
                "priority": "high",
                "title": "High CPU Usage Detected",
                "description": f"CPU usage is {current_metrics.cpu_usage:.1f}%. Consider scaling resources or optimizing processes.",
                "expected_improvement": "Reduce CPU load by 20-40%",
                "implementation": "Scale horizontally or optimize algorithms",
                "urgency": "immediate"
            })
        
        # Memory optimization
        if current_metrics.memory_usage > 80:
            optimizations.append({
                "category": "memory",
                "priority": "high",
                "title": "Memory Usage Warning",
                "description": f"Memory usage is {current_metrics.memory_usage:.1f}%. Risk of performance degradation.",
                "expected_improvement": "Reduce memory pressure and improve stability",
                "implementation": "Clear caches, optimize data structures, or add memory",
                "urgency": "high"
            })
        
        # Cache optimization
        if current_metrics.cache_hit_rate < 50:
            optimizations.append({
                "category": "cache",
                "priority": "medium",
                "title": "Low Cache Hit Rate",
                "description": f"Cache hit rate is {current_metrics.cache_hit_rate:.1f}%. Poor caching efficiency detected.",
                "expected_improvement": "Improve response times by 30-50%",
                "implementation": "Optimize cache strategy, increase cache size, or tune cache TTL",
                "urgency": "medium"
            })
        
        # Response time optimization
        if current_metrics.response_time_avg > 1000:
            optimizations.append({
                "category": "performance",
                "priority": "high",
                "title": "Slow Response Times",
                "description": f"Average response time is {current_metrics.response_time_avg:.1f}ms. Performance optimization needed.",
                "expected_improvement": "Reduce response times by 40-60%",
                "implementation": "Optimize database queries, implement caching, or scale infrastructure",
                "urgency": "high"
            })
        
        # Trend-based predictions
        predictions = {
            "cpu_forecast_24h": cpu_trend.prediction_24h if cpu_trend.prediction_24h else current_metrics.cpu_usage,
            "memory_forecast_24h": memory_trend.prediction_24h if memory_trend.prediction_24h else current_metrics.memory_usage,
            "response_time_forecast_24h": response_trend.prediction_24h if response_trend.prediction_24h else current_metrics.response_time_avg,
            "trend_analysis": {
                "cpu_trend": cpu_trend.trend_direction,
                "memory_trend": memory_trend.trend_direction,
                "performance_trend": response_trend.trend_direction
            }
        }
        
        return {
            "success": True,
            "optimization_analysis": {
                "current_status": {
                    "cpu_usage": current_metrics.cpu_usage,
                    "memory_usage": current_metrics.memory_usage,
                    "cache_hit_rate": current_metrics.cache_hit_rate,
                    "response_time_avg": current_metrics.response_time_avg,
                    "error_rate": current_metrics.error_rate
                },
                "optimizations": optimizations,
                "predictions": predictions,
                "confidence_scores": {
                    "cpu_confidence": cpu_trend.confidence_score,
                    "memory_confidence": memory_trend.confidence_score,
                    "performance_confidence": response_trend.confidence_score
                },
                "overall_health_score": await analytics._calculate_health_score(current_metrics),
                "optimization_priority": "high" if len(optimizations) >= 3 else "medium" if len(optimizations) >= 1 else "low"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/predictive-alerts")
async def get_predictive_alerts():
    """Get predictive alerts based on trend analysis"""
    try:
        current_metrics = await analytics.collect_metrics()
        
        # Analyze key metrics trends
        key_metrics = ["cpu_usage", "memory_usage", "response_time_avg", "cache_hit_rate", "error_rate"]
        predictive_alerts = []
        
        for metric in key_metrics:
            trend = await analytics.analyze_performance_trends(metric, "1h")
            
            if trend.prediction_24h is not None and trend.confidence_score > 0.5:
                current_value = getattr(current_metrics, metric)
                predicted_value = trend.prediction_24h
                
                # Check for concerning trends
                if metric == "cpu_usage" and predicted_value > 90:
                    predictive_alerts.append({
                        "alert_type": "predictive",
                        "severity": "warning",
                        "metric": metric,
                        "title": "CPU Usage Trend Alert",
                        "description": f"CPU usage predicted to reach {predicted_value:.1f}% in 24h (currently {current_value:.1f}%)",
                        "current_value": current_value,
                        "predicted_value": predicted_value,
                        "confidence": trend.confidence_score,
                        "time_to_threshold": "~24 hours",
                        "recommended_action": "Scale resources or optimize CPU-intensive processes"
                    })
                
                elif metric == "memory_usage" and predicted_value > 85:
                    predictive_alerts.append({
                        "alert_type": "predictive",
                        "severity": "critical",
                        "metric": metric,
                        "title": "Memory Usage Trend Alert",
                        "description": f"Memory usage predicted to reach {predicted_value:.1f}% in 24h (currently {current_value:.1f}%)",
                        "current_value": current_value,
                        "predicted_value": predicted_value,
                        "confidence": trend.confidence_score,
                        "time_to_threshold": "~24 hours",
                        "recommended_action": "Clear caches, optimize memory usage, or add RAM"
                    })
                
                elif metric == "response_time_avg" and predicted_value > 2000:
                    predictive_alerts.append({
                        "alert_type": "predictive",
                        "severity": "warning",
                        "metric": metric,
                        "title": "Response Time Trend Alert",
                        "description": f"Response time predicted to reach {predicted_value:.1f}ms in 24h (currently {current_value:.1f}ms)",
                        "current_value": current_value,
                        "predicted_value": predicted_value,
                        "confidence": trend.confidence_score,
                        "time_to_threshold": "~24 hours",
                        "recommended_action": "Optimize performance bottlenecks or scale infrastructure"
                    })
        
        return {
            "success": True,
            "predictive_alerts": predictive_alerts,
            "alert_count": len(predictive_alerts),
            "analysis_confidence": sum(alert["confidence"] for alert in predictive_alerts) / len(predictive_alerts) if predictive_alerts else 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting predictive alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/system-health")
async def predict_system_health():
    """Predict system health trends using ML"""
    try:
        # Get recent metrics for prediction
        current_metrics = await analytics.collect_metrics()
        
        # Get historical data for ML model
        historical_cpu = await analytics._get_historical_data("cpu_usage", "24h")
        historical_memory = await analytics._get_historical_data("memory_usage", "24h")
        historical_response = await analytics._get_historical_data("response_time_avg", "24h")
        
        if len(historical_cpu) < 10:
            return {
                "success": True,
                "prediction": "insufficient_data",
                "message": "Need more historical data for accurate predictions",
                "confidence": 0.0
            }
        
        # Prepare data for ML model
        cpu_values = [point[1] for point in historical_cpu[-20:]]  # Last 20 points
        memory_values = [point[1] for point in historical_memory[-20:]]
        response_values = [point[1] for point in historical_response[-20:]]
        
        # Normalize values
        scaler = MinMaxScaler()
        features = np.array([cpu_values[-10:], memory_values[-10:], response_values[-10:]]).T
        features_normalized = scaler.fit_transform(features)
        
        # Simple trend prediction using linear regression
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        
        # Prepare training data
        X = np.arange(len(features_normalized)).reshape(-1, 1)
        
        predictions = {}
        confidence_scores = {}
        
        for i, metric_name in enumerate(["cpu_usage", "memory_usage", "response_time_avg"]):
            y = features_normalized[:, i]
            model.fit(X, y)
            
            # Predict next 6 hours (assuming 1 point per hour)
            future_X = np.arange(len(y), len(y) + 6).reshape(-1, 1)
            future_predictions = model.predict(future_X)
            
            # Calculate confidence based on R² score
            confidence = max(0.0, min(1.0, model.score(X, y)))
            
            predictions[metric_name] = {
                "current_value": float(getattr(current_metrics, metric_name)),
                "predicted_6h": float(future_predictions[-1] * 100),  # Convert back to percentage
                "trend": "increasing" if future_predictions[-1] > y[-1] else "decreasing",
                "confidence": confidence
            }
        
        # Overall health prediction
        avg_confidence = np.mean([pred["confidence"] for pred in predictions.values()])
        
        # Predict potential issues
        issues = []
        if predictions["cpu_usage"]["predicted_6h"] > 85:
            issues.append("High CPU usage expected in next 6 hours")
        if predictions["memory_usage"]["predicted_6h"] > 90:
            issues.append("Memory pressure expected in next 6 hours")
        if predictions["response_time_avg"]["predicted_6h"] > 1000:
            issues.append("Response time degradation expected")
        
        return {
            "success": True,
            "predictions": predictions,
            "overall_confidence": avg_confidence,
            "predicted_issues": issues,
            "recommendation": "Monitor system closely" if issues else "System health looks stable",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error predicting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomaly-detection")
async def detect_anomalies():
    """Detect anomalies in system metrics using ML"""
    try:
        # Get recent metrics data
        metrics_data = []
        metric_names = ["cpu_usage", "memory_usage", "response_time_avg", "cache_hit_rate"]
        
        for metric in metric_names:
            data_points = await analytics._get_historical_data(metric, "24h")
            if len(data_points) >= 20:
                values = [point[1] for point in data_points[-50:]]  # Last 50 points
                metrics_data.append(values)
        
        if len(metrics_data) < 3:
            return {
                "success": True,
                "anomalies": [],
                "message": "Insufficient data for anomaly detection"
            }
        
        # Prepare data for anomaly detection
        min_length = min(len(values) for values in metrics_data)
        feature_matrix = np.array([values[:min_length] for values in metrics_data]).T
        
        # Use Isolation Forest for anomaly detection
        isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        anomaly_scores = isolation_forest.fit_predict(feature_matrix)
        
        # Find anomalous time points
        anomalies = []
        current_time = datetime.now()
        
        for i, score in enumerate(anomaly_scores):
            if score == -1:  # Anomaly detected
                time_ago = (min_length - i) * 60  # Assuming 1 point per minute
                anomaly_time = current_time - timedelta(minutes=time_ago)
                
                anomalies.append({
                    "timestamp": anomaly_time.isoformat(),
                    "severity": "high" if i > len(anomaly_scores) * 0.9 else "medium",
                    "metrics": {
                        metric_names[j]: float(feature_matrix[i][j]) 
                        for j in range(len(metric_names))
                    },
                    "description": f"Anomalous system behavior detected {time_ago} minutes ago"
                })
        
        # Sort by timestamp (most recent first)
        anomalies.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "success": True,
            "anomalies": anomalies[:10],  # Limit to 10 most recent
            "total_data_points": min_length,
            "anomaly_rate": len(anomalies) / min_length * 100,
            "analysis_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity-planning")
async def capacity_planning():
    """Provide capacity planning recommendations using ML analysis"""
    try:
        current_metrics = await analytics.collect_metrics()
        
        # Get historical data for trend analysis
        cpu_data = await analytics._get_historical_data("cpu_usage", "7d")
        memory_data = await analytics._get_historical_data("memory_usage", "7d")
        
        if len(cpu_data) < 20 or len(memory_data) < 20:
            return {
                "success": True,
                "recommendations": ["Collect more historical data for accurate capacity planning"],
                "confidence": 0.1
            }
        
        # Analyze growth trends
        cpu_values = [point[1] for point in cpu_data]
        memory_values = [point[1] for point in memory_data]
        
        # Calculate growth rates
        cpu_growth_rate = (cpu_values[-1] - cpu_values[0]) / len(cpu_values)
        memory_growth_rate = (memory_values[-1] - memory_values[0]) / len(memory_values)
        
        # Predict when thresholds will be reached
        cpu_threshold = 85.0
        memory_threshold = 90.0
        
        recommendations = []
        
        # CPU capacity analysis
        if cpu_growth_rate > 0:
            days_to_cpu_limit = (cpu_threshold - current_metrics.cpu_usage) / cpu_growth_rate
            if days_to_cpu_limit > 0 and days_to_cpu_limit < 30:
                recommendations.append(f"CPU may reach {cpu_threshold}% in {days_to_cpu_limit:.0f} days - consider scaling")
        
        # Memory capacity analysis
        if memory_growth_rate > 0:
            days_to_memory_limit = (memory_threshold - current_metrics.memory_usage) / memory_growth_rate
            if days_to_memory_limit > 0 and days_to_memory_limit < 30:
                recommendations.append(f"Memory may reach {memory_threshold}% in {days_to_memory_limit:.0f} days - consider scaling")
        
        # Workload analysis
        workflow_utilization = sum(current_metrics.workflow_count.values())
        if workflow_utilization > 80:
            recommendations.append("High workflow utilization - consider adding more processing capacity")
        
        # Cache optimization
        if current_metrics.cache_hit_rate < 80:
            recommendations.append("Low cache hit rate - consider increasing cache size or optimizing cache strategy")
        
        # Response time analysis
        if current_metrics.response_time_avg > 500:
            recommendations.append("Response times are elevated - consider performance optimization or scaling")
        
        if not recommendations:
            recommendations.append("System capacity looks good - no immediate scaling needed")
        
        # Calculate confidence based on data quality
        confidence = min(1.0, len(cpu_data) / 100.0)  # Full confidence with 100+ data points
        
        return {
            "success": True,
            "current_utilization": {
                "cpu": current_metrics.cpu_usage,
                "memory": current_metrics.memory_usage,
                "workflows": workflow_utilization,
                "cache_efficiency": current_metrics.cache_hit_rate
            },
            "growth_trends": {
                "cpu_growth_rate": cpu_growth_rate,
                "memory_growth_rate": memory_growth_rate
            },
            "recommendations": recommendations,
            "confidence": confidence,
            "analysis_period": "7 days",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in capacity planning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml-insights")
async def get_ml_insights():
    """Get ML-powered insights and predictions"""
    try:
        # Collect various ML insights
        insights = []
        
        # Performance pattern analysis
        current_metrics = await analytics.collect_metrics()
        
        # CPU pattern analysis
        cpu_data = await analytics._get_historical_data("cpu_usage", "24h")
        if len(cpu_data) >= 24:
            cpu_values = [point[1] for point in cpu_data[-24:]]  # Last 24 hours
            avg_cpu = np.mean(cpu_values)
            std_cpu = np.std(cpu_values)
            
            if std_cpu > 15:  # High variability
                insights.append({
                    "type": "pattern_analysis",
                    "category": "cpu",
                    "insight": "High CPU usage variability detected",
                    "recommendation": "Consider load balancing or optimizing peak-time operations",
                    "confidence": 0.8
                })
        
        # Memory usage pattern
        memory_data = await analytics._get_historical_data("memory_usage", "24h")
        if len(memory_data) >= 24:
            memory_values = [point[1] for point in memory_data[-24:]]
            memory_trend = np.polyfit(range(len(memory_values)), memory_values, 1)[0]
            
            if memory_trend > 0.5:  # Increasing trend
                insights.append({
                    "type": "trend_analysis",
                    "category": "memory",
                    "insight": "Memory usage is trending upward",
                    "recommendation": "Monitor for potential memory leaks or optimize memory usage",
                    "confidence": 0.7
                })
        
        # Response time correlation analysis
        response_data = await analytics._get_historical_data("response_time_avg", "24h")
        if len(response_data) >= 10 and len(cpu_data) >= 10:
            # Check correlation between CPU and response time
            min_length = min(len(response_data), len(cpu_data))
            response_values = [point[1] for point in response_data[-min_length:]]
            cpu_values_for_corr = [point[1] for point in cpu_data[-min_length:]]
            
            correlation = np.corrcoef(cpu_values_for_corr, response_values)[0, 1]
            
            if abs(correlation) > 0.7:
                insights.append({
                    "type": "correlation_analysis",
                    "category": "performance",
                    "insight": f"Strong correlation ({correlation:.2f}) between CPU usage and response time",
                    "recommendation": "Focus on CPU optimization to improve response times",
                    "confidence": abs(correlation)
                })
        
        # Efficiency insights
        return {
            "success": True,
            "data": {
                "insights": insights,
                "total_insights": len(insights),
                "categories": list(set([insight["category"] for insight in insights])),
                "generated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating ML insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate ML insights")