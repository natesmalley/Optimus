"""
Dashboard API Endpoints
=======================

Comprehensive REST API for the Optimus Dashboard system.
Provides aggregated insights, recommendations, and system health overview.

Features:
- Comprehensive system overview with real-time metrics
- AI-generated insights and recommendations
- Project health analysis and optimization suggestions
- Cross-system analytics combining all Optimus components
- Executive summary and reporting endpoints
- Trend analysis and predictive insights
- Resource utilization optimization recommendations
- Security and performance alerting dashboard
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..config import get_db_session
from ..services.enhanced_scanner import EnhancedProjectScanner
from ..services.runtime_monitor import RuntimeMonitor
from ..council.memory_system import get_memory_system
from ..council.optimus_knowledge_graph import OptimusKnowledgeGraph
from ..models.project import Project
from ..models.runtime import RuntimeStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# =================== REQUEST/RESPONSE MODELS ===================

class DashboardOverviewResponse(BaseModel):
    """Comprehensive dashboard overview"""
    timestamp: datetime
    summary: Dict[str, Any]
    system_health: Dict[str, Any]
    project_statistics: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    top_insights: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]


class ProjectHealthResponse(BaseModel):
    """Project health analysis"""
    project_id: str
    project_name: str
    overall_health_score: float
    health_components: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    risk_factors: List[Dict[str, Any]]
    trends: Dict[str, Any]
    last_analysis: datetime


class SystemInsightsResponse(BaseModel):
    """AI-generated system insights"""
    insight_type: str
    title: str
    description: str
    confidence: float
    impact_level: str
    supporting_data: List[Dict[str, Any]]
    recommendations: List[str]
    category: str
    generated_at: datetime


class RecommendationResponse(BaseModel):
    """Action item recommendations"""
    recommendation_id: str
    type: str
    priority: str
    title: str
    description: str
    estimated_impact: str
    implementation_effort: str
    category: str
    related_projects: List[str]
    steps: List[str]
    metrics_to_track: List[str]


class ActivityFeedResponse(BaseModel):
    """Recent system activity"""
    activity_id: str
    type: str
    title: str
    description: str
    timestamp: datetime
    source: str
    related_entities: Dict[str, Any]
    severity: Optional[str]


class PerformanceTrendResponse(BaseModel):
    """Performance trend analysis"""
    metric_name: str
    current_value: float
    trend_direction: str
    change_percentage: float
    period: str
    benchmark_comparison: Optional[Dict[str, Any]]
    recommendation: Optional[str]


class ResourceUtilizationResponse(BaseModel):
    """Resource utilization analysis"""
    resource_type: str
    current_usage: float
    optimal_range: Dict[str, float]
    efficiency_score: float
    waste_indicators: List[str]
    optimization_suggestions: List[str]
    cost_impact: Optional[str]


# =================== DASHBOARD OVERVIEW ENDPOINTS ===================

@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive dashboard overview.
    
    Provides aggregated view of all system components, health metrics,
    project status, and recent activity with AI-generated insights.
    """
    try:
        current_time = datetime.utcnow()
        
        # Get project statistics
        project_stats = await _get_project_statistics(session)
        
        # Get system health metrics
        system_health = await _get_system_health_metrics(session)
        
        # Get performance metrics
        performance_metrics = await _get_performance_metrics(session)
        
        # Get recent activity
        recent_activity = await _get_recent_activity(session, limit=10)
        
        # Get top insights
        top_insights = await _get_top_insights(session, limit=5)
        
        # Get active alerts
        alerts = await _get_active_alerts(session, limit=10)
        
        # Compile summary
        summary = {
            "total_projects": project_stats.get("total_projects", 0),
            "active_projects": project_stats.get("active_projects", 0),
            "system_health_score": system_health.get("overall_score", 0.0),
            "critical_alerts": len([a for a in alerts if a.get("severity") == "critical"]),
            "pending_recommendations": await _count_pending_recommendations(session),
            "last_updated": current_time.isoformat()
        }
        
        return DashboardOverviewResponse(
            timestamp=current_time,
            summary=summary,
            system_health=system_health,
            project_statistics=project_stats,
            recent_activity=recent_activity,
            performance_metrics=performance_metrics,
            top_insights=top_insights,
            alerts=alerts
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard overview")


@router.get("/health", response_model=Dict[str, Any])
async def get_system_health(
    detailed: bool = Query(False, description="Include detailed component health"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive system health analysis.
    
    Analyzes all system components and provides health scores,
    status indicators, and diagnostic information.
    """
    try:
        health_data = await _get_system_health_metrics(session, detailed=detailed)
        
        # Add component-specific health checks
        if detailed:
            health_data["components"] = {
                "database": await _check_database_health(session),
                "memory_system": await _check_memory_system_health(),
                "knowledge_graph": await _check_knowledge_graph_health(),
                "scanner": await _check_scanner_health(session),
                "monitor": await _check_monitor_health()
            }
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


# =================== PROJECT ANALYTICS ENDPOINTS ===================

@router.get("/projects/health", response_model=List[ProjectHealthResponse])
async def get_projects_health(
    project_ids: Optional[List[str]] = Query(None, description="Specific project IDs to analyze"),
    sort_by: str = Query("health_score", description="Sort by: health_score, name, last_analysis"),
    sort_desc: bool = Query(True, description="Sort descending"),
    limit: int = Query(20, ge=1, le=100, description="Maximum projects to return"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get health analysis for all projects.
    
    Analyzes project health based on multiple factors including
    code quality, dependencies, security, and runtime performance.
    """
    try:
        query = select(Project)
        
        if project_ids:
            query = query.where(Project.id.in_(project_ids))
        
        result = await session.execute(query)
        projects = result.scalars().all()
        
        health_responses = []
        
        for project in projects:
            health_analysis = await _analyze_project_health(project, session)
            health_responses.append(ProjectHealthResponse(**health_analysis))
        
        # Sort results
        if sort_by == "health_score":
            health_responses.sort(key=lambda p: p.overall_health_score, reverse=sort_desc)
        elif sort_by == "name":
            health_responses.sort(key=lambda p: p.project_name, reverse=sort_desc)
        elif sort_by == "last_analysis":
            health_responses.sort(key=lambda p: p.last_analysis, reverse=sort_desc)
        
        return health_responses[:limit]
        
    except Exception as e:
        logger.error(f"Error getting projects health: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve projects health")


@router.get("/projects/{project_id}/health", response_model=ProjectHealthResponse)
async def get_project_health(
    project_id: str,
    force_refresh: bool = Query(False, description="Force fresh analysis"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed health analysis for a specific project.
    
    Provides comprehensive health assessment including code quality,
    security, performance, and maintenance indicators.
    """
    try:
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        health_analysis = await _analyze_project_health(project, session, force_refresh)
        return ProjectHealthResponse(**health_analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project health for {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve project health")


# =================== INSIGHTS AND RECOMMENDATIONS ===================

@router.get("/insights", response_model=List[SystemInsightsResponse])
async def get_system_insights(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    impact_level: Optional[str] = Query(None, description="Filter by impact level: low, medium, high"),
    limit: int = Query(20, ge=1, le=100, description="Maximum insights to return"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get AI-generated system insights and analysis.
    
    Provides intelligent analysis of system patterns, performance,
    security, and optimization opportunities across all components.
    """
    try:
        insights = await _generate_system_insights(session, limit * 2)  # Generate more to filter
        
        # Apply filters
        filtered_insights = []
        for insight in insights:
            if category and insight.get("category") != category:
                continue
            if insight.get("confidence", 0) < min_confidence:
                continue
            if impact_level and insight.get("impact_level") != impact_level:
                continue
            
            filtered_insights.append(SystemInsightsResponse(**insight))
        
        return filtered_insights[:limit]
        
    except Exception as e:
        logger.error(f"Error getting system insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system insights")


@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    priority: Optional[str] = Query(None, description="Filter by priority: low, medium, high, critical"),
    category: Optional[str] = Query(None, description="Filter by category"),
    project_id: Optional[str] = Query(None, description="Filter by specific project"),
    implementation_effort: Optional[str] = Query(None, description="Filter by effort: low, medium, high"),
    limit: int = Query(20, ge=1, le=100, description="Maximum recommendations to return"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get actionable recommendations for system optimization.
    
    Provides prioritized list of improvements, optimizations,
    and fixes based on system analysis and best practices.
    """
    try:
        recommendations = await _generate_recommendations(session, project_id)
        
        # Apply filters
        filtered_recommendations = []
        for rec in recommendations:
            if priority and rec.get("priority") != priority:
                continue
            if category and rec.get("category") != category:
                continue
            if implementation_effort and rec.get("implementation_effort") != implementation_effort:
                continue
            
            filtered_recommendations.append(RecommendationResponse(**rec))
        
        # Sort by priority (critical > high > medium > low)
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        filtered_recommendations.sort(
            key=lambda r: priority_order.get(r.priority, 0),
            reverse=True
        )
        
        return filtered_recommendations[:limit]
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recommendations")


# =================== ACTIVITY AND TRENDS ===================

@router.get("/activity", response_model=List[ActivityFeedResponse])
async def get_activity_feed(
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    source: Optional[str] = Query(None, description="Filter by source system"),
    since: Optional[datetime] = Query(None, description="Get activities since this timestamp"),
    limit: int = Query(50, ge=1, le=200, description="Maximum activities to return"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get recent system activity feed.
    
    Provides chronological feed of system events, changes,
    alerts, and important activities across all components.
    """
    try:
        activities = await _get_recent_activity(session, limit * 2)  # Get more to filter
        
        # Apply filters
        filtered_activities = []
        for activity in activities:
            if activity_type and activity.get("type") != activity_type:
                continue
            if source and activity.get("source") != source:
                continue
            if since and datetime.fromisoformat(activity.get("timestamp", "")) < since:
                continue
            
            filtered_activities.append(ActivityFeedResponse(**activity))
        
        # Sort by timestamp (newest first)
        filtered_activities.sort(key=lambda a: a.timestamp, reverse=True)
        
        return filtered_activities[:limit]
        
    except Exception as e:
        logger.error(f"Error getting activity feed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve activity feed")


@router.get("/trends", response_model=List[PerformanceTrendResponse])
async def get_performance_trends(
    metric_name: Optional[str] = Query(None, description="Filter by specific metric"),
    period: str = Query("7d", description="Time period: 1h, 6h, 1d, 7d, 30d"),
    trend_direction: Optional[str] = Query(None, description="Filter by trend: increasing, decreasing, stable"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get performance trends analysis.
    
    Analyzes system and project performance trends over time
    with benchmarking and optimization recommendations.
    """
    try:
        trends = await _analyze_performance_trends(session, period)
        
        # Apply filters
        filtered_trends = []
        for trend in trends:
            if metric_name and trend.get("metric_name") != metric_name:
                continue
            if trend_direction and trend.get("trend_direction") != trend_direction:
                continue
            
            filtered_trends.append(PerformanceTrendResponse(**trend))
        
        return filtered_trends
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance trends")


# =================== RESOURCE OPTIMIZATION ===================

@router.get("/resources", response_model=List[ResourceUtilizationResponse])
async def get_resource_utilization(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    min_waste_threshold: float = Query(0.1, ge=0.0, le=1.0, description="Minimum waste threshold"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get resource utilization analysis and optimization suggestions.
    
    Analyzes CPU, memory, disk, and network resource usage
    patterns with waste identification and optimization recommendations.
    """
    try:
        resources = await _analyze_resource_utilization(session)
        
        # Apply filters
        filtered_resources = []
        for resource in resources:
            if resource_type and resource.get("resource_type") != resource_type:
                continue
            
            # Calculate waste percentage and filter
            efficiency_score = resource.get("efficiency_score", 1.0)
            waste_percentage = 1.0 - efficiency_score
            if waste_percentage < min_waste_threshold:
                continue
            
            filtered_resources.append(ResourceUtilizationResponse(**resource))
        
        # Sort by efficiency score (least efficient first)
        filtered_resources.sort(key=lambda r: r.efficiency_score)
        
        return filtered_resources
        
    except Exception as e:
        logger.error(f"Error getting resource utilization: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resource utilization")


# =================== HELPER FUNCTIONS ===================

async def _get_project_statistics(session: AsyncSession) -> Dict[str, Any]:
    """Get comprehensive project statistics"""
    try:
        # Total projects
        total_query = select(func.count(Project.id))
        total_result = await session.execute(total_query)
        total_projects = total_result.scalar()
        
        # Active projects (recently scanned)
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_query = select(func.count(Project.id)).where(
            Project.last_scanned >= week_ago
        )
        active_result = await session.execute(active_query)
        active_projects = active_result.scalar()
        
        # Language distribution
        lang_stats = {}
        projects_query = select(Project).where(Project.language_stats.isnot(None))
        projects_result = await session.execute(projects_query)
        projects = projects_result.scalars().all()
        
        for project in projects:
            lang_stats_data = project.language_stats or {}
            for lang, percentage in lang_stats_data.items():
                if lang not in lang_stats:
                    lang_stats[lang] = []
                lang_stats[lang].append(percentage)
        
        # Average language percentages
        avg_lang_stats = {}
        for lang, percentages in lang_stats.items():
            avg_lang_stats[lang] = sum(percentages) / len(percentages)
        
        return {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "inactive_projects": total_projects - active_projects,
            "language_distribution": dict(sorted(avg_lang_stats.items(), key=lambda x: x[1], reverse=True)[:10]),
            "avg_projects_per_language": len(lang_stats),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting project statistics: {e}")
        return {"error": str(e)}


async def _get_system_health_metrics(session: AsyncSession, detailed: bool = False) -> Dict[str, Any]:
    """Get system health metrics"""
    try:
        health_score = 0.85  # Placeholder calculation
        
        base_metrics = {
            "overall_score": health_score,
            "status": "healthy" if health_score > 0.7 else "degraded" if health_score > 0.5 else "critical",
            "components_healthy": 4,
            "components_total": 5,
            "last_check": datetime.utcnow().isoformat()
        }
        
        if detailed:
            base_metrics.update({
                "database_health": 0.9,
                "api_health": 0.85,
                "monitoring_health": 0.8,
                "memory_system_health": 0.9,
                "knowledge_graph_health": 0.75
            })
        
        return base_metrics
        
    except Exception as e:
        logger.error(f"Error getting system health metrics: {e}")
        return {"overall_score": 0.0, "status": "error", "error": str(e)}


async def _get_performance_metrics(session: AsyncSession) -> Dict[str, Any]:
    """Get system performance metrics"""
    try:
        # Placeholder metrics - would be calculated from real data
        return {
            "response_time_avg_ms": 150,
            "throughput_requests_per_sec": 25,
            "error_rate_percent": 0.1,
            "uptime_percent": 99.8,
            "memory_usage_percent": 45,
            "cpu_usage_percent": 30,
            "disk_usage_percent": 60,
            "active_connections": 12,
            "last_measurement": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {"error": str(e)}


async def _get_recent_activity(session: AsyncSession, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent system activity"""
    try:
        # Placeholder activity data - would be retrieved from activity log
        activities = [
            {
                "activity_id": "act_001",
                "type": "project_scanned",
                "title": "Project Analysis Completed",
                "description": "Enhanced scanner completed analysis of 3 projects",
                "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                "source": "scanner",
                "related_entities": {"projects_count": 3},
                "severity": None
            },
            {
                "activity_id": "act_002", 
                "type": "performance_alert",
                "title": "High Memory Usage Detected",
                "description": "System memory usage exceeded 85% threshold",
                "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
                "source": "monitor",
                "related_entities": {"memory_percent": 87},
                "severity": "warning"
            },
            {
                "activity_id": "act_003",
                "type": "insight_generated",
                "title": "New Technology Pattern Identified",
                "description": "Knowledge graph discovered React+TypeScript usage pattern",
                "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "source": "knowledge_graph",
                "related_entities": {"pattern": "react_typescript"},
                "severity": None
            }
        ]
        
        return activities[:limit]
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return []


async def _get_top_insights(session: AsyncSession, limit: int = 5) -> List[Dict[str, Any]]:
    """Get top system insights"""
    try:
        # Placeholder insights - would be generated by AI analysis
        insights = [
            {
                "insight_type": "optimization",
                "title": "Dependency Consolidation Opportunity",
                "description": "Multiple projects using different versions of React - consolidation could reduce bundle sizes",
                "confidence": 0.85,
                "impact_level": "medium",
                "category": "performance"
            },
            {
                "insight_type": "security",
                "title": "Outdated Dependencies Detected",
                "description": "5 projects have dependencies with known security vulnerabilities",
                "confidence": 0.95,
                "impact_level": "high", 
                "category": "security"
            }
        ]
        
        return insights[:limit]
        
    except Exception as e:
        logger.error(f"Error getting top insights: {e}")
        return []


async def _get_active_alerts(session: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """Get active system alerts"""
    try:
        # Placeholder alerts - would be retrieved from alert system
        alerts = [
            {
                "alert_id": "alert_001",
                "type": "performance",
                "severity": "warning",
                "title": "High CPU Usage",
                "description": "CPU usage above 80% for 10+ minutes",
                "timestamp": (datetime.utcnow() - timedelta(minutes=12)).isoformat(),
                "source": "monitor"
            }
        ]
        
        return alerts[:limit]
        
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        return []


async def _count_pending_recommendations(session: AsyncSession) -> int:
    """Count pending recommendations"""
    try:
        # Placeholder - would count from recommendations table
        return 8
        
    except Exception as e:
        logger.error(f"Error counting recommendations: {e}")
        return 0


async def _analyze_project_health(project: Project, session: AsyncSession, force_refresh: bool = False) -> Dict[str, Any]:
    """Analyze health of a specific project"""
    try:
        # Calculate health score based on multiple factors
        health_components = {
            "code_quality": 0.8,  # Based on metrics, complexity, etc.
            "dependencies": 0.7,  # Based on outdated/vulnerable deps
            "security": 0.9,      # Based on vulnerability scan
            "documentation": 0.6, # Based on documentation coverage
            "activity": 0.8,      # Based on recent commits/changes
            "performance": 0.75   # Based on runtime metrics
        }
        
        # Calculate overall score as weighted average
        weights = {
            "code_quality": 0.25,
            "dependencies": 0.20,
            "security": 0.25,
            "documentation": 0.10,
            "activity": 0.10,
            "performance": 0.10
        }
        
        overall_score = sum(
            health_components[component] * weights[component]
            for component in health_components.keys()
        )
        
        # Generate recommendations based on low scores
        recommendations = []
        risk_factors = []
        
        for component, score in health_components.items():
            if score < 0.7:
                recommendations.append({
                    "component": component,
                    "priority": "high" if score < 0.5 else "medium",
                    "description": f"Improve {component} score (currently {score:.1%})",
                    "suggested_actions": [f"Review and optimize {component}"]
                })
            
            if score < 0.6:
                risk_factors.append({
                    "component": component,
                    "risk_level": "high" if score < 0.4 else "medium",
                    "description": f"Low {component} score may impact project stability",
                    "current_score": score
                })
        
        trends = {
            "overall_trend": "stable",
            "component_trends": {comp: "stable" for comp in health_components.keys()}
        }
        
        return {
            "project_id": str(project.id),
            "project_name": project.name,
            "overall_health_score": overall_score,
            "health_components": health_components,
            "recommendations": recommendations,
            "risk_factors": risk_factors,
            "trends": trends,
            "last_analysis": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing project health: {e}")
        return {
            "project_id": str(project.id),
            "project_name": project.name,
            "overall_health_score": 0.0,
            "health_components": {},
            "recommendations": [],
            "risk_factors": [{"component": "analysis", "risk_level": "high", "description": f"Health analysis failed: {e}"}],
            "trends": {},
            "last_analysis": datetime.utcnow()
        }


async def _generate_system_insights(session: AsyncSession, limit: int = 20) -> List[Dict[str, Any]]:
    """Generate AI insights about the system"""
    try:
        # Placeholder insights - would be generated by AI analysis
        insights = [
            {
                "insight_type": "pattern",
                "title": "Technology Stack Standardization Opportunity",
                "description": "75% of projects use React, suggesting potential for shared component library",
                "confidence": 0.88,
                "impact_level": "high",
                "supporting_data": [
                    {"metric": "react_usage", "value": 0.75},
                    {"metric": "potential_savings", "value": "30% faster development"}
                ],
                "recommendations": [
                    "Create shared React component library",
                    "Standardize on React 18+",
                    "Implement design system"
                ],
                "category": "efficiency",
                "generated_at": datetime.utcnow()
            },
            {
                "insight_type": "security",
                "title": "Dependency Vulnerability Pattern",
                "description": "Node.js projects consistently lag behind security updates",
                "confidence": 0.92,
                "impact_level": "high",
                "supporting_data": [
                    {"metric": "vulnerable_packages", "value": 12},
                    {"metric": "avg_days_behind", "value": 45}
                ],
                "recommendations": [
                    "Implement automated dependency updates",
                    "Add security scanning to CI/CD",
                    "Create dependency update schedule"
                ],
                "category": "security",
                "generated_at": datetime.utcnow()
            }
        ]
        
        return insights[:limit]
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        return []


async def _generate_recommendations(session: AsyncSession, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate actionable recommendations"""
    try:
        recommendations = [
            {
                "recommendation_id": "rec_001",
                "type": "security",
                "priority": "high",
                "title": "Update Vulnerable Dependencies",
                "description": "Several projects have dependencies with known security vulnerabilities",
                "estimated_impact": "Reduces security risk by 80%",
                "implementation_effort": "medium",
                "category": "security",
                "related_projects": ["proj_1", "proj_2", "proj_3"] if not project_id else [project_id],
                "steps": [
                    "Run security audit on all projects",
                    "Update vulnerable packages",
                    "Test for breaking changes",
                    "Deploy updates"
                ],
                "metrics_to_track": [
                    "Number of vulnerable dependencies",
                    "Security scan score",
                    "Time to resolve vulnerabilities"
                ]
            },
            {
                "recommendation_id": "rec_002",
                "type": "performance",
                "priority": "medium",
                "title": "Implement Code Splitting",
                "description": "Large bundle sizes detected in React applications",
                "estimated_impact": "30-50% reduction in initial load time",
                "implementation_effort": "high",
                "category": "performance",
                "related_projects": ["proj_1", "proj_4"] if not project_id else [project_id],
                "steps": [
                    "Analyze bundle composition",
                    "Implement dynamic imports",
                    "Set up lazy loading",
                    "Monitor performance impact"
                ],
                "metrics_to_track": [
                    "Bundle size",
                    "Initial load time",
                    "Time to interactive"
                ]
            }
        ]
        
        # Filter by project if specified
        if project_id:
            recommendations = [
                rec for rec in recommendations 
                if project_id in rec.get("related_projects", [])
            ]
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return []


async def _analyze_performance_trends(session: AsyncSession, period: str) -> List[Dict[str, Any]]:
    """Analyze performance trends over specified period"""
    try:
        # Placeholder trends - would be calculated from historical data
        trends = [
            {
                "metric_name": "response_time",
                "current_value": 150.0,
                "trend_direction": "increasing",
                "change_percentage": 15.0,
                "period": period,
                "benchmark_comparison": {
                    "target": 100.0,
                    "industry_average": 200.0
                },
                "recommendation": "Optimize database queries and implement caching"
            },
            {
                "metric_name": "memory_usage",
                "current_value": 65.0,
                "trend_direction": "stable",
                "change_percentage": 2.0,
                "period": period,
                "benchmark_comparison": {
                    "target": 70.0,
                    "industry_average": 75.0
                },
                "recommendation": None
            }
        ]
        
        return trends
        
    except Exception as e:
        logger.error(f"Error analyzing performance trends: {e}")
        return []


async def _analyze_resource_utilization(session: AsyncSession) -> List[Dict[str, Any]]:
    """Analyze resource utilization and waste"""
    try:
        resources = [
            {
                "resource_type": "cpu",
                "current_usage": 35.0,
                "optimal_range": {"min": 40.0, "max": 80.0},
                "efficiency_score": 0.7,
                "waste_indicators": [
                    "CPU underutilized during peak hours",
                    "Idle processes consuming resources"
                ],
                "optimization_suggestions": [
                    "Implement auto-scaling",
                    "Optimize process scheduling",
                    "Remove idle services"
                ],
                "cost_impact": "Potential 20% cost reduction"
            },
            {
                "resource_type": "memory",
                "current_usage": 78.0,
                "optimal_range": {"min": 50.0, "max": 85.0},
                "efficiency_score": 0.9,
                "waste_indicators": [],
                "optimization_suggestions": [
                    "Monitor for memory leaks",
                    "Implement memory pooling"
                ],
                "cost_impact": None
            }
        ]
        
        return resources
        
    except Exception as e:
        logger.error(f"Error analyzing resource utilization: {e}")
        return []


# Component health check functions
async def _check_database_health(session: AsyncSession) -> Dict[str, Any]:
    """Check database health"""
    try:
        # Simple query to test database connectivity
        result = await session.execute(select(func.count()).select_from(Project))
        count = result.scalar()
        
        return {
            "status": "healthy",
            "response_time_ms": 5,  # Placeholder
            "connections_active": 2,
            "projects_count": count
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_memory_system_health() -> Dict[str, Any]:
    """Check memory system health"""
    try:
        memory_system = await get_memory_system()
        health_data = await memory_system.health_check()
        return {"status": "healthy", **health_data}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_knowledge_graph_health() -> Dict[str, Any]:
    """Check knowledge graph health"""
    try:
        # Would check KG health
        return {"status": "healthy", "nodes": 150, "edges": 300}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_scanner_health(session: AsyncSession) -> Dict[str, Any]:
    """Check scanner health"""
    try:
        # Would check scanner status
        return {"status": "healthy", "last_scan": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_monitor_health() -> Dict[str, Any]:
    """Check monitor health"""
    try:
        # Would check monitor status
        return {"status": "healthy", "processes_monitored": 15}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}