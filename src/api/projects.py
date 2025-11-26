"""
Projects API endpoints.
Handles CRUD operations for projects and project-related data.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..models import Project, RuntimeStatus, AnalysisResult, MonetizationOpportunity
from ..services import ProjectScanner


logger = logging.getLogger("optimus.api.projects")
router = APIRouter()


# Request/Response Models
class ProjectResponse(BaseModel):
    """Project response model."""
    id: str
    name: str
    path: str
    description: Optional[str] = None
    tech_stack: Dict[str, Any] = Field(default_factory=dict)
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    status: str
    git_url: Optional[str] = None
    default_branch: str = "main"
    last_commit_hash: Optional[str] = None
    language_stats: Dict[str, Any] = Field(default_factory=dict)
    last_scanned: Optional[str] = None
    created_at: str
    updated_at: str
    
    # Runtime information
    is_running: bool = False
    process_count: int = 0
    running_ports: List[int] = Field(default_factory=list)
    
    # Analysis information
    latest_quality_score: Optional[float] = None
    open_issues_count: int = 0
    monetization_opportunities: int = 0
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Projects list response model."""
    projects: List[ProjectResponse]
    total: int
    page: int
    size: int


class ProjectDetailResponse(ProjectResponse):
    """Detailed project response with additional information."""
    runtime_processes: List[Dict[str, Any]] = Field(default_factory=list)
    recent_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    monetization_summary: Dict[str, Any] = Field(default_factory=dict)


# Dependency for database session
async def get_db_session():
    """Get database session dependency."""
    from ..config import db_manager
    async for session in db_manager.get_session():
        yield session


@router.get("/", response_model=ProjectListResponse)
async def get_projects(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tech_stack: Optional[str] = Query(None, description="Filter by technology"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get list of projects with optional filtering and pagination."""
    
    try:
        # Build base query
        query = select(Project)
        
        # Apply filters
        if status:
            query = query.where(Project.status == status)
        
        if tech_stack:
            query = query.where(
                Project.tech_stack.op('->>')('language') == tech_stack
            )
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                Project.name.ilike(search_term) | 
                Project.description.ilike(search_term)
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(Project.updated_at.desc())
        
        # Execute query
        result = await session.execute(query)
        projects = result.scalars().all()
        
        # Enhance with runtime and analysis data
        enhanced_projects = []
        for project in projects:
            project_data = await _enhance_project_data(session, project)
            enhanced_projects.append(ProjectResponse(**project_data))
        
        return ProjectListResponse(
            projects=enhanced_projects,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"Error fetching projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch projects")


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """Get detailed project information."""
    
    try:
        # Get project with relationships
        query = (
            select(Project)
            .options(
                selectinload(Project.runtime_statuses),
                selectinload(Project.analysis_results),
                selectinload(Project.monetization_opportunities)
            )
            .where(Project.id == project_id)
        )
        
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build detailed response
        project_data = await _enhance_project_data(session, project, detailed=True)
        
        return ProjectDetailResponse(**project_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch project")


@router.post("/{project_id}/scan")
async def scan_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """Trigger a scan for a specific project."""
    
    try:
        # Get project
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Initialize scanner and scan the project directory
        scanner = ProjectScanner(session)
        project_info = await scanner._analyze_directory(project.path)
        
        if project_info:
            await scanner.save_project(project_info)
            return {
                "message": f"Project {project.name} scanned successfully",
                "project_id": str(project_id),
                "status": "completed"
            }
        else:
            return {
                "message": f"No project found at {project.path}",
                "project_id": str(project_id),
                "status": "no_project"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to scan project")


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a project (soft delete by changing status)."""
    
    try:
        # Get project
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Soft delete by changing status
        project.status = "archived"
        await session.commit()
        
        return {
            "message": f"Project {project.name} archived successfully",
            "project_id": str(project_id),
            "status": "archived"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.get("/{project_id}/analysis")
async def get_project_analysis(
    project_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Limit results"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get analysis results for a project."""
    
    try:
        # Get recent analysis results
        query = (
            select(AnalysisResult)
            .where(AnalysisResult.project_id == project_id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
        )
        
        result = await session.execute(query)
        analyses = result.scalars().all()
        
        return {
            "project_id": str(project_id),
            "analysis_results": [
                {
                    "id": str(analysis.id),
                    "analysis_type": analysis.analysis_type,
                    "score": float(analysis.score) if analysis.score else None,
                    "issues_count": analysis.issues_count,
                    "results": analysis.results,
                    "analyzer_version": analysis.analyzer_version,
                    "created_at": analysis.created_at.isoformat(),
                    "grade": analysis.grade,
                    "is_passing": analysis.is_passing
                }
                for analysis in analyses
            ],
            "total": len(analyses)
        }
        
    except Exception as e:
        logger.error(f"Error fetching analysis for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch analysis")


@router.get("/{project_id}/monetization")
async def get_project_monetization(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """Get monetization opportunities for a project."""
    
    try:
        # Get monetization opportunities
        query = (
            select(MonetizationOpportunity)
            .where(MonetizationOpportunity.project_id == project_id)
            .order_by(MonetizationOpportunity.priority.desc())
        )
        
        result = await session.execute(query)
        opportunities = result.scalars().all()
        
        # Calculate summary stats
        total_revenue = sum(
            float(opp.potential_revenue) for opp in opportunities 
            if opp.potential_revenue
        )
        
        active_opportunities = [
            opp for opp in opportunities 
            if opp.status in ("identified", "evaluating", "in_progress")
        ]
        
        return {
            "project_id": str(project_id),
            "opportunities": [
                {
                    "id": str(opp.id),
                    "opportunity_type": opp.opportunity_type,
                    "description": opp.description,
                    "potential_revenue": float(opp.potential_revenue) if opp.potential_revenue else None,
                    "effort_required": opp.effort_required,
                    "priority": opp.priority,
                    "status": opp.status,
                    "confidence_score": float(opp.confidence_score) if opp.confidence_score else None,
                    "opportunity_score": opp.opportunity_score,
                    "risk_level": opp.risk_level,
                    "created_at": opp.created_at.isoformat(),
                    "updated_at": opp.updated_at.isoformat()
                }
                for opp in opportunities
            ],
            "summary": {
                "total_opportunities": len(opportunities),
                "active_opportunities": len(active_opportunities),
                "total_potential_revenue": total_revenue,
                "highest_priority": max((opp.priority for opp in opportunities), default=0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching monetization for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch monetization data")


async def _enhance_project_data(
    session: AsyncSession, 
    project: Project, 
    detailed: bool = False
) -> Dict[str, Any]:
    """Enhance project data with runtime and analysis information."""
    
    # Base project data
    project_data = {
        "id": str(project.id),
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "tech_stack": project.tech_stack or {},
        "dependencies": project.dependencies or {},
        "status": project.status,
        "git_url": project.git_url,
        "default_branch": project.default_branch,
        "last_commit_hash": project.last_commit_hash,
        "language_stats": project.language_stats or {},
        "last_scanned": project.last_scanned.isoformat() if project.last_scanned else None,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }
    
    # Get runtime information
    runtime_query = select(RuntimeStatus).where(
        RuntimeStatus.project_id == project.id,
        RuntimeStatus.status.in_(["running", "starting"])
    )
    runtime_result = await session.execute(runtime_query)
    runtime_statuses = runtime_result.scalars().all()
    
    project_data.update({
        "is_running": len(runtime_statuses) > 0,
        "process_count": len(runtime_statuses),
        "running_ports": [rs.port for rs in runtime_statuses if rs.port],
    })
    
    # Get latest analysis score
    analysis_query = (
        select(AnalysisResult)
        .where(
            AnalysisResult.project_id == project.id,
            AnalysisResult.analysis_type == "code_quality"
        )
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    analysis_result = await session.execute(analysis_query)
    latest_analysis = analysis_result.scalar_one_or_none()
    
    project_data["latest_quality_score"] = (
        float(latest_analysis.score) if latest_analysis and latest_analysis.score else None
    )
    
    # Get monetization count
    monetization_query = select(func.count()).where(
        MonetizationOpportunity.project_id == project.id,
        MonetizationOpportunity.status.in_(["identified", "evaluating", "in_progress"])
    )
    monetization_result = await session.execute(monetization_query)
    monetization_count = monetization_result.scalar()
    
    project_data["monetization_opportunities"] = monetization_count
    
    # Add detailed information if requested
    if detailed:
        project_data["runtime_processes"] = [
            {
                "pid": rs.pid,
                "name": rs.process_name,
                "status": rs.status,
                "cpu_usage": float(rs.cpu_usage) if rs.cpu_usage else None,
                "memory_usage_mb": rs.memory_usage_mb,
                "port": rs.port,
                "started_at": rs.started_at.isoformat(),
                "last_heartbeat": rs.last_heartbeat.isoformat(),
            }
            for rs in runtime_statuses
        ]
        
        # Get recent analysis results
        recent_analysis_query = (
            select(AnalysisResult)
            .where(AnalysisResult.project_id == project.id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(5)
        )
        recent_analysis_result = await session.execute(recent_analysis_query)
        recent_analyses = recent_analysis_result.scalars().all()
        
        project_data["recent_analysis"] = [
            {
                "analysis_type": analysis.analysis_type,
                "score": float(analysis.score) if analysis.score else None,
                "issues_count": analysis.issues_count,
                "created_at": analysis.created_at.isoformat(),
                "grade": analysis.grade
            }
            for analysis in recent_analyses
        ]
        
        # Get monetization summary
        monetization_summary_query = select(MonetizationOpportunity).where(
            MonetizationOpportunity.project_id == project.id
        )
        monetization_summary_result = await session.execute(monetization_summary_query)
        all_opportunities = monetization_summary_result.scalars().all()
        
        total_potential = sum(
            float(opp.potential_revenue) for opp in all_opportunities 
            if opp.potential_revenue
        )
        
        project_data["monetization_summary"] = {
            "total_opportunities": len(all_opportunities),
            "total_potential_revenue": total_potential,
            "active_opportunities": len([
                opp for opp in all_opportunities 
                if opp.status in ("identified", "evaluating", "in_progress")
            ])
        }
    
    return project_data