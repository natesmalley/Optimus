"""
Metrics API endpoints.
Handles project metrics, analytics, and performance data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from ..models import ProjectMetric, Project, AnalysisResult, ErrorPattern


logger = logging.getLogger("optimus.api.metrics")
router = APIRouter()


# Response Models
class MetricPoint(BaseModel):
    """Single metric data point."""
    timestamp: str
    value: float
    unit: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricSeries(BaseModel):
    """Time series of metrics."""
    metric_type: str
    project_id: str
    project_name: str
    data_points: List[MetricPoint]
    summary: Dict[str, Any] = Field(default_factory=dict)


class ProjectMetricsResponse(BaseModel):
    """Project metrics response."""
    project_id: str
    project_name: str
    metrics: List[MetricSeries]
    period: str
    total_points: int


class SystemMetricsResponse(BaseModel):
    """System-wide metrics response."""
    period: str
    projects: List[ProjectMetricsResponse]
    summary: Dict[str, Any] = Field(default_factory=dict)


class HealthScoreResponse(BaseModel):
    """Project health score response."""
    project_id: str
    project_name: str
    overall_score: float
    components: Dict[str, float]
    last_updated: str
    grade: str


# Dependency for database session
async def get_db_session():
    """Get database session dependency."""
    from ..config import db_manager
    async for session in db_manager.get_session():
        yield session


@router.get("/projects/{project_id}", response_model=ProjectMetricsResponse)
async def get_project_metrics(
    project_id: UUID,
    metric_types: Optional[List[str]] = Query(None, description="Filter by metric types"),
    period: str = Query("24h", description="Time period (1h, 24h, 7d, 30d)"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get metrics for a specific project."""
    
    try:
        # Get project
        project_query = select(Project).where(Project.id == project_id)
        project_result = await session.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Parse period
        time_delta = _parse_period(period)
        start_time = datetime.utcnow() - time_delta
        
        # Build metrics query
        metrics_query = select(ProjectMetric).where(
            ProjectMetric.project_id == project_id,
            ProjectMetric.timestamp >= start_time
        ).order_by(ProjectMetric.timestamp.desc())
        
        if metric_types:
            metrics_query = metrics_query.where(
                ProjectMetric.metric_type.in_(metric_types)
            )
        
        metrics_result = await session.execute(metrics_query)
        metrics = metrics_result.scalars().all()
        
        # Group metrics by type
        metrics_by_type = {}
        for metric in metrics:
            if metric.metric_type not in metrics_by_type:
                metrics_by_type[metric.metric_type] = []
            metrics_by_type[metric.metric_type].append(metric)
        
        # Build metric series
        metric_series = []
        for metric_type, metric_list in metrics_by_type.items():
            data_points = [
                MetricPoint(
                    timestamp=metric.timestamp.isoformat(),
                    value=float(metric.value),
                    unit=metric.unit,
                    metadata=metric.metadata or {}
                )
                for metric in metric_list
            ]
            
            # Calculate summary statistics
            values = [float(m.value) for m in metric_list]
            summary = {
                "count": len(values),
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "avg": sum(values) / len(values) if values else 0,
                "latest": values[0] if values else 0  # First in desc order
            }
            
            metric_series.append(MetricSeries(
                metric_type=metric_type,
                project_id=str(project_id),
                project_name=project.name,
                data_points=data_points,
                summary=summary
            ))
        
        return ProjectMetricsResponse(
            project_id=str(project_id),
            project_name=project.name,
            metrics=metric_series,
            period=period,
            total_points=len(metrics)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project metrics {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch project metrics")


@router.get("/", response_model=SystemMetricsResponse)
async def get_system_metrics(
    metric_types: Optional[List[str]] = Query(None, description="Filter by metric types"),
    period: str = Query("24h", description="Time period (1h, 24h, 7d, 30d)"),
    project_ids: Optional[List[UUID]] = Query(None, description="Filter by project IDs"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get system-wide metrics."""
    
    try:
        # Parse period
        time_delta = _parse_period(period)
        start_time = datetime.utcnow() - time_delta
        
        # Build base query
        query = (
            select(ProjectMetric, Project.name.label("project_name"))
            .join(Project)
            .where(ProjectMetric.timestamp >= start_time)
            .order_by(ProjectMetric.project_id, ProjectMetric.timestamp.desc())
        )
        
        if metric_types:
            query = query.where(ProjectMetric.metric_type.in_(metric_types))
        
        if project_ids:
            query = query.where(ProjectMetric.project_id.in_(project_ids))
        
        result = await session.execute(query)
        metrics_data = result.all()
        
        # Group by project
        projects_metrics = {}
        for metric, project_name in metrics_data:
            project_id = str(metric.project_id)
            
            if project_id not in projects_metrics:
                projects_metrics[project_id] = {
                    "project_name": project_name,
                    "metrics": {}
                }
            
            metric_type = metric.metric_type
            if metric_type not in projects_metrics[project_id]["metrics"]:
                projects_metrics[project_id]["metrics"][metric_type] = []
            
            projects_metrics[project_id]["metrics"][metric_type].append(metric)
        
        # Build response
        projects_response = []
        all_values_by_type = {}
        
        for project_id, project_data in projects_metrics.items():
            metric_series = []
            total_points = 0
            
            for metric_type, metric_list in project_data["metrics"].items():
                data_points = [
                    MetricPoint(
                        timestamp=metric.timestamp.isoformat(),
                        value=float(metric.value),
                        unit=metric.unit,
                        metadata=metric.metadata or {}
                    )
                    for metric in metric_list
                ]
                
                values = [float(m.value) for m in metric_list]
                summary = {
                    "count": len(values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "avg": sum(values) / len(values) if values else 0,
                    "latest": values[0] if values else 0
                }
                
                # Collect for system summary
                if metric_type not in all_values_by_type:
                    all_values_by_type[metric_type] = []
                all_values_by_type[metric_type].extend(values)
                
                metric_series.append(MetricSeries(
                    metric_type=metric_type,
                    project_id=project_id,
                    project_name=project_data["project_name"],
                    data_points=data_points,
                    summary=summary
                ))
                
                total_points += len(data_points)
            
            projects_response.append(ProjectMetricsResponse(
                project_id=project_id,
                project_name=project_data["project_name"],
                metrics=metric_series,
                period=period,
                total_points=total_points
            ))
        
        # Calculate system summary
        system_summary = {}
        for metric_type, values in all_values_by_type.items():
            if values:
                system_summary[metric_type] = {
                    "total_data_points": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "projects_count": len([p for p in projects_response 
                                        if any(m.metric_type == metric_type for m in p.metrics)])
                }
        
        return SystemMetricsResponse(
            period=period,
            projects=projects_response,
            summary=system_summary
        )
        
    except Exception as e:
        logger.error(f"Error fetching system metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch system metrics")


@router.get("/health/{project_id}", response_model=HealthScoreResponse)
async def get_project_health_score(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """Calculate and return project health score."""
    
    try:
        # Get project
        project_query = select(Project).where(Project.id == project_id)
        project_result = await session.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Calculate health score components
        components = {}
        
        # 1. Code Quality Score (from latest analysis)
        analysis_query = (
            select(AnalysisResult)
            .where(
                AnalysisResult.project_id == project_id,
                AnalysisResult.analysis_type == "code_quality"
            )
            .order_by(AnalysisResult.created_at.desc())
            .limit(1)
        )
        analysis_result = await session.execute(analysis_query)
        latest_analysis = analysis_result.scalar_one_or_none()
        
        components["code_quality"] = (
            float(latest_analysis.score) if latest_analysis and latest_analysis.score else 50.0
        )
        
        # 2. Error Rate (based on recent error patterns)
        last_week = datetime.utcnow() - timedelta(days=7)
        error_query = select(func.count()).where(
            ErrorPattern.project_id == project_id,
            ErrorPattern.last_seen >= last_week
        )
        error_result = await session.execute(error_query)
        recent_errors = error_result.scalar() or 0
        
        # Lower score for more errors (inverse relationship)
        components["stability"] = max(0, 100 - (recent_errors * 5))
        
        # 3. Maintenance Score (based on last scan/commit)
        days_since_update = 0
        if project.last_scanned:
            days_since_update = (datetime.utcnow() - project.last_scanned.replace(tzinfo=None)).days
        
        # Lower score for older projects
        components["maintenance"] = max(0, 100 - (days_since_update * 2))
        
        # 4. Performance Score (from recent metrics)
        performance_query = select(ProjectMetric).where(
            ProjectMetric.project_id == project_id,
            ProjectMetric.metric_type == "performance",
            ProjectMetric.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(ProjectMetric.timestamp.desc()).limit(10)
        
        performance_result = await session.execute(performance_query)
        performance_metrics = performance_result.scalars().all()
        
        if performance_metrics:
            avg_performance = sum(float(m.value) for m in performance_metrics) / len(performance_metrics)
            components["performance"] = min(100, max(0, avg_performance))
        else:
            components["performance"] = 75.0  # Default neutral score
        
        # 5. Security Score
        security_query = (
            select(AnalysisResult)
            .where(
                AnalysisResult.project_id == project_id,
                AnalysisResult.analysis_type == "security"
            )
            .order_by(AnalysisResult.created_at.desc())
            .limit(1)
        )
        security_result = await session.execute(security_query)
        latest_security = security_result.scalar_one_or_none()
        
        components["security"] = (
            float(latest_security.score) if latest_security and latest_security.score else 70.0
        )
        
        # Calculate weighted overall score
        weights = {
            "code_quality": 0.25,
            "stability": 0.20,
            "maintenance": 0.15,
            "performance": 0.20,
            "security": 0.20
        }
        
        overall_score = sum(
            components.get(component, 0) * weight 
            for component, weight in weights.items()
        )
        
        # Convert to letter grade
        def score_to_grade(score: float) -> str:
            if score >= 90:
                return "A"
            elif score >= 80:
                return "B"
            elif score >= 70:
                return "C"
            elif score >= 60:
                return "D"
            else:
                return "F"
        
        return HealthScoreResponse(
            project_id=str(project_id),
            project_name=project.name,
            overall_score=round(overall_score, 1),
            components=components,
            last_updated=datetime.utcnow().isoformat(),
            grade=score_to_grade(overall_score)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating health score for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate health score")


@router.get("/trends")
async def get_metrics_trends(
    metric_type: str = Query(..., description="Metric type to analyze"),
    period: str = Query("7d", description="Analysis period"),
    project_ids: Optional[List[UUID]] = Query(None, description="Filter by project IDs"),
    session: AsyncSession = Depends(get_db_session)
):
    """Analyze trends in metrics over time."""
    
    try:
        time_delta = _parse_period(period)
        start_time = datetime.utcnow() - time_delta
        
        # Get metrics for trend analysis
        query = (
            select(ProjectMetric, Project.name.label("project_name"))
            .join(Project)
            .where(
                ProjectMetric.metric_type == metric_type,
                ProjectMetric.timestamp >= start_time
            )
            .order_by(ProjectMetric.timestamp)
        )
        
        if project_ids:
            query = query.where(ProjectMetric.project_id.in_(project_ids))
        
        result = await session.execute(query)
        metrics_data = result.all()
        
        if not metrics_data:
            return {
                "metric_type": metric_type,
                "period": period,
                "trends": [],
                "summary": {"message": "No data available for analysis"}
            }
        
        # Group by project and calculate trends
        projects_data = {}
        for metric, project_name in metrics_data:
            project_id = str(metric.project_id)
            if project_id not in projects_data:
                projects_data[project_id] = {
                    "project_name": project_name,
                    "values": [],
                    "timestamps": []
                }
            
            projects_data[project_id]["values"].append(float(metric.value))
            projects_data[project_id]["timestamps"].append(metric.timestamp)
        
        # Calculate trend for each project
        trends = []
        overall_values = []
        
        for project_id, data in projects_data.items():
            values = data["values"]
            overall_values.extend(values)
            
            if len(values) < 2:
                trend_direction = "insufficient_data"
                trend_slope = 0
            else:
                # Simple linear trend calculation
                n = len(values)
                sum_x = sum(range(n))
                sum_y = sum(values)
                sum_xy = sum(i * values[i] for i in range(n))
                sum_x2 = sum(i * i for i in range(n))
                
                trend_slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                
                if abs(trend_slope) < 0.1:  # Threshold for "stable"
                    trend_direction = "stable"
                elif trend_slope > 0:
                    trend_direction = "increasing"
                else:
                    trend_direction = "decreasing"
            
            trends.append({
                "project_id": project_id,
                "project_name": data["project_name"],
                "trend_direction": trend_direction,
                "trend_slope": trend_slope,
                "value_count": len(values),
                "latest_value": values[-1] if values else None,
                "min_value": min(values) if values else None,
                "max_value": max(values) if values else None,
                "avg_value": sum(values) / len(values) if values else None
            })
        
        # Overall summary
        if overall_values:
            overall_avg = sum(overall_values) / len(overall_values)
            summary = {
                "total_projects": len(projects_data),
                "total_data_points": len(overall_values),
                "overall_min": min(overall_values),
                "overall_max": max(overall_values),
                "overall_avg": overall_avg,
                "projects_trending_up": len([t for t in trends if t["trend_direction"] == "increasing"]),
                "projects_trending_down": len([t for t in trends if t["trend_direction"] == "decreasing"]),
                "projects_stable": len([t for t in trends if t["trend_direction"] == "stable"])
            }
        else:
            summary = {"message": "No data available"}
        
        return {
            "metric_type": metric_type,
            "period": period,
            "trends": trends,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error analyzing trends for {metric_type}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze trends")


def _parse_period(period: str) -> timedelta:
    """Parse period string into timedelta."""
    period_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90)
    }
    
    if period not in period_map:
        raise HTTPException(status_code=400, detail="Invalid period. Use 1h, 24h, 7d, 30d, or 90d")
    
    return period_map[period]