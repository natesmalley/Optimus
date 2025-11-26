"""
Runtime API endpoints.
Handles process monitoring and runtime status operations.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..models import RuntimeStatus, Project
from ..services import RuntimeMonitor


logger = logging.getLogger("optimus.api.runtime")
router = APIRouter()


# Response Models
class ProcessInfo(BaseModel):
    """Process information model."""
    pid: int
    name: str
    status: str
    cpu_usage: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    port: Optional[int] = None
    started_at: str
    last_heartbeat: str
    
    class Config:
        from_attributes = True


class RuntimeSummary(BaseModel):
    """Runtime summary model."""
    project_id: str
    project_name: str
    is_running: bool
    process_count: int
    total_cpu_usage: float
    total_memory_usage_mb: float
    ports: List[int]
    processes: List[ProcessInfo]


class SystemRuntimeResponse(BaseModel):
    """System-wide runtime response."""
    total_projects: int
    running_projects: int
    total_processes: int
    total_cpu_usage: float
    total_memory_usage_mb: float
    projects: List[RuntimeSummary]


class MonitorCycleResponse(BaseModel):
    """Monitor cycle response."""
    timestamp: str
    duration_seconds: float
    processes_found: int
    status: str
    error: Optional[str] = None


# Dependency for database session
async def get_db_session():
    """Get database session dependency."""
    from ..config import db_manager
    async for session in db_manager.get_session():
        yield session


@router.get("/", response_model=SystemRuntimeResponse)
async def get_runtime_overview(
    running_only: bool = Query(False, description="Show only running projects"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get system-wide runtime overview."""
    
    try:
        # Get projects with runtime status
        query = (
            select(Project)
            .options(selectinload(Project.runtime_statuses))
            .where(Project.status.in_(["active", "discovered"]))
        )
        
        if running_only:
            # Only projects with running processes
            query = query.join(RuntimeStatus).where(
                RuntimeStatus.status.in_(["running", "starting"])
            ).distinct()
        
        result = await session.execute(query)
        projects = result.scalars().all()
        
        # Build runtime summaries
        runtime_summaries = []
        total_cpu = 0.0
        total_memory = 0.0
        total_processes = 0
        running_projects = 0
        
        for project in projects:
            running_processes = [
                rs for rs in project.runtime_statuses
                if rs.status in ("running", "starting")
            ]
            
            if running_only and not running_processes:
                continue
            
            project_cpu = sum(rs.cpu_usage or 0 for rs in running_processes)
            project_memory = sum(rs.memory_usage or 0 for rs in running_processes)
            project_memory_mb = project_memory / (1024 * 1024) if project_memory else 0
            
            is_running = len(running_processes) > 0
            if is_running:
                running_projects += 1
                total_cpu += project_cpu
                total_memory += project_memory_mb
                total_processes += len(running_processes)
            
            runtime_summary = RuntimeSummary(
                project_id=str(project.id),
                project_name=project.name,
                is_running=is_running,
                process_count=len(running_processes),
                total_cpu_usage=project_cpu,
                total_memory_usage_mb=project_memory_mb,
                ports=[rs.port for rs in running_processes if rs.port],
                processes=[
                    ProcessInfo(
                        pid=rs.pid,
                        name=rs.process_name,
                        status=rs.status,
                        cpu_usage=rs.cpu_usage,
                        memory_usage_mb=rs.memory_usage / (1024 * 1024) if rs.memory_usage else None,
                        port=rs.port,
                        started_at=rs.started_at.isoformat(),
                        last_heartbeat=rs.last_heartbeat.isoformat()
                    )
                    for rs in running_processes
                ]
            )
            runtime_summaries.append(runtime_summary)
        
        return SystemRuntimeResponse(
            total_projects=len(projects),
            running_projects=running_projects,
            total_processes=total_processes,
            total_cpu_usage=total_cpu,
            total_memory_usage_mb=total_memory,
            projects=runtime_summaries
        )
        
    except Exception as e:
        logger.error(f"Error fetching runtime overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch runtime overview")


@router.get("/project/{project_id}", response_model=RuntimeSummary)
async def get_project_runtime(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """Get runtime information for a specific project."""
    
    try:
        # Get project with runtime status
        query = (
            select(Project)
            .options(selectinload(Project.runtime_statuses))
            .where(Project.id == project_id)
        )
        
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get runtime monitor to build summary
        monitor = RuntimeMonitor(session)
        runtime_data = await monitor.get_project_runtime_summary(str(project_id))
        
        return RuntimeSummary(
            project_id=str(project.id),
            project_name=project.name,
            is_running=runtime_data["is_running"],
            process_count=runtime_data["process_count"],
            total_cpu_usage=runtime_data["total_cpu_usage"],
            total_memory_usage_mb=runtime_data["memory_usage_mb"],
            ports=runtime_data["ports"],
            processes=[
                ProcessInfo(
                    pid=proc["pid"],
                    name=proc["name"],
                    status=proc["status"],
                    cpu_usage=proc["cpu_usage"],
                    memory_usage_mb=proc["memory_usage_mb"],
                    port=proc["port"],
                    started_at=proc["started_at"].isoformat(),
                    last_heartbeat=proc["last_heartbeat"].isoformat()
                )
                for proc in runtime_data["processes"]
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project runtime {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch project runtime")


@router.post("/monitor", response_model=MonitorCycleResponse)
async def trigger_monitor_cycle(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session)
):
    """Trigger a manual monitoring cycle."""
    
    try:
        monitor = RuntimeMonitor(session)
        
        # Run monitoring cycle
        result = await monitor.monitor_cycle()
        
        return MonitorCycleResponse(
            timestamp=result["timestamp"].isoformat(),
            duration_seconds=result["duration_seconds"],
            processes_found=result["processes_found"],
            status=result["status"],
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error triggering monitor cycle: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger monitoring cycle")


@router.get("/processes", response_model=List[ProcessInfo])
async def get_all_processes(
    status: Optional[str] = Query(None, description="Filter by process status"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get all tracked processes with optional filtering."""
    
    try:
        # Build query
        query = select(RuntimeStatus)
        
        if status:
            query = query.where(RuntimeStatus.status == status)
        
        if project_id:
            query = query.where(RuntimeStatus.project_id == project_id)
        
        query = query.order_by(RuntimeStatus.last_heartbeat.desc())
        
        result = await session.execute(query)
        processes = result.scalars().all()
        
        return [
            ProcessInfo(
                pid=rs.pid,
                name=rs.process_name,
                status=rs.status,
                cpu_usage=rs.cpu_usage,
                memory_usage_mb=rs.memory_usage / (1024 * 1024) if rs.memory_usage else None,
                port=rs.port,
                started_at=rs.started_at.isoformat(),
                last_heartbeat=rs.last_heartbeat.isoformat()
            )
            for rs in processes
        ]
        
    except Exception as e:
        logger.error(f"Error fetching processes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch processes")


@router.delete("/process/{pid}")
async def stop_process_tracking(
    pid: int,
    session: AsyncSession = Depends(get_db_session)
):
    """Stop tracking a specific process (mark as stopped)."""
    
    try:
        # Find the runtime status record
        query = select(RuntimeStatus).where(RuntimeStatus.pid == pid)
        result = await session.execute(query)
        runtime_status = result.scalar_one_or_none()
        
        if not runtime_status:
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Mark as stopped
        runtime_status.status = "stopped"
        runtime_status.stopped_at = func.now()
        
        await session.commit()
        
        return {
            "message": f"Process {pid} marked as stopped",
            "pid": pid,
            "status": "stopped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping process tracking {pid}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to stop process tracking")


@router.get("/stats")
async def get_runtime_stats(
    session: AsyncSession = Depends(get_db_session)
):
    """Get overall runtime statistics."""
    
    try:
        # Get counts by status
        status_query = select(
            RuntimeStatus.status,
            func.count(RuntimeStatus.id).label("count")
        ).group_by(RuntimeStatus.status)
        
        status_result = await session.execute(status_query)
        status_counts = {row.status: row.count for row in status_result}
        
        # Get total resource usage for running processes
        resource_query = select(
            func.sum(RuntimeStatus.cpu_usage).label("total_cpu"),
            func.sum(RuntimeStatus.memory_usage).label("total_memory"),
            func.count(RuntimeStatus.id).label("running_count")
        ).where(RuntimeStatus.status.in_(["running", "starting"]))
        
        resource_result = await session.execute(resource_query)
        resource_stats = resource_result.first()
        
        # Get unique ports in use
        ports_query = select(RuntimeStatus.port).where(
            RuntimeStatus.port.isnot(None),
            RuntimeStatus.status.in_(["running", "starting"])
        ).distinct()
        
        ports_result = await session.execute(ports_query)
        active_ports = [row.port for row in ports_result]
        
        return {
            "status_counts": status_counts,
            "running_processes": resource_stats.running_count or 0,
            "total_cpu_usage": float(resource_stats.total_cpu or 0),
            "total_memory_usage_mb": (resource_stats.total_memory or 0) / (1024 * 1024),
            "active_ports": sorted(active_ports),
            "port_count": len(active_ports)
        }
        
    except Exception as e:
        logger.error(f"Error fetching runtime stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch runtime statistics")