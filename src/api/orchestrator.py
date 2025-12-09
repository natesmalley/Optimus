"""
Orchestrator API Endpoints

Comprehensive API endpoints for project orchestration including project management,
resource allocation, environment switching, deployment automation, and backup coordination.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path as FastAPIPath
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.config import get_db_session
from ..orchestrator import (
    ProjectLauncher, EnvironmentManager, ResourceAllocator, 
    DeploymentAssistant, BackupCoordinator
)

logger = logging.getLogger(__name__)

# Initialize orchestrator services
project_launcher = ProjectLauncher()
environment_manager = EnvironmentManager()
resource_allocator = ResourceAllocator()
deployment_assistant = DeploymentAssistant()
backup_coordinator = BackupCoordinator()

router = APIRouter(prefix="/api/v1/orchestrator", tags=["orchestrator"])


# Pydantic models for API requests/responses

class ProjectStartRequest(BaseModel):
    """Request to start a project."""
    environment: str = Field(default="development", description="Target environment")
    custom_command: Optional[str] = Field(None, description="Custom startup command")
    ports: Optional[List[int]] = Field(None, description="Ports to allocate")
    env_vars: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    resource_limits: Optional[Dict[str, Any]] = Field(None, description="Resource limits")


class ProcessInfoResponse(BaseModel):
    """Response containing process information."""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_rss: int
    memory_percent: float
    ports: List[int]
    started_at: datetime
    last_seen: datetime
    command: Optional[str]
    environment: Optional[str]
    logs_path: Optional[str]


class RunningProjectResponse(BaseModel):
    """Response containing running project information."""
    project_id: str
    name: str
    path: str
    project_type: str
    status: str
    processes: List[ProcessInfoResponse]
    primary_port: Optional[int]
    health_url: Optional[str]
    started_at: Optional[datetime]
    environment: str
    resource_limits: Dict[str, Any]


class EnvironmentVariablesRequest(BaseModel):
    """Request to set environment variables."""
    variables: Dict[str, str] = Field(..., description="Variables to set")
    environment_name: str = Field(default="development", description="Target environment")


class EnvironmentResponse(BaseModel):
    """Response containing environment information."""
    name: str
    type: str
    variables: Dict[str, Any]
    config_files: List[str]
    active: bool
    created_at: datetime
    last_modified: datetime
    description: Optional[str]


class ResourceLimitsRequest(BaseModel):
    """Request to set resource limits."""
    cpu_percent: Optional[float] = Field(None, ge=0, le=100, description="Maximum CPU percentage")
    cpu_cores: Optional[int] = Field(None, ge=1, description="Maximum CPU cores")
    memory_mb: Optional[int] = Field(None, ge=64, description="Maximum memory in MB")
    memory_percent: Optional[float] = Field(None, ge=0, le=100, description="Maximum memory percentage")
    max_processes: Optional[int] = Field(None, ge=1, description="Maximum number of processes")


class ResourceRequirementsRequest(BaseModel):
    """Request to allocate resources with requirements."""
    min_cpu_percent: float = Field(5.0, ge=0, le=100)
    max_cpu_percent: float = Field(80.0, ge=0, le=100)
    min_memory_mb: int = Field(64, ge=1)
    max_memory_mb: int = Field(2048, ge=1)
    priority: str = Field("normal", regex="^(critical|high|normal|low|background)$")
    auto_scale: bool = Field(True)
    scale_threshold_cpu: float = Field(70.0, ge=0, le=100)
    scale_threshold_memory: float = Field(80.0, ge=0, le=100)


class ResourceMetricsResponse(BaseModel):
    """Response containing resource usage metrics."""
    project_id: str
    timestamp: datetime
    cpu_percent: float
    cpu_cores_used: float
    memory_mb: float
    memory_percent: float
    disk_read_mb_s: float
    disk_write_mb_s: float
    network_upload_kb_s: float
    network_download_kb_s: float
    process_count: int
    file_descriptors: int
    load_average: Optional[List[float]]


class DeploymentRequest(BaseModel):
    """Request to deploy a project."""
    target: str = Field(..., description="Deployment target")
    environment: str = Field("production", description="Target environment")
    build_command: Optional[str] = Field(None, description="Custom build command")
    test_command: Optional[str] = Field(None, description="Custom test command")
    deploy_command: Optional[str] = Field(None, description="Custom deploy command")
    health_check_url: Optional[str] = Field(None, description="Health check URL")
    env_vars: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    auto_rollback: bool = Field(True, description="Enable automatic rollback on failure")


class DeploymentResponse(BaseModel):
    """Response containing deployment information."""
    deployment_id: str
    project_id: str
    status: str
    target: str
    environment: str
    commit_hash: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    build_logs: List[str]
    deploy_logs: List[str]
    error_message: Optional[str]
    health_status: str
    rollback_deployment_id: Optional[str]
    artifacts: Dict[str, str]


class BackupRequest(BaseModel):
    """Request to create a backup."""
    incremental: bool = Field(True, description="Create incremental backup")
    tags: Optional[List[str]] = Field(None, description="Backup tags")
    compression: str = Field("gzip", regex="^(none|gzip|bzip2|xz)$", description="Compression type")
    encryption: bool = Field(False, description="Enable encryption")


class BackupResponse(BaseModel):
    """Response containing backup information."""
    backup_id: str
    project_id: str
    backup_type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    size_bytes: Optional[int]
    compressed_size_bytes: Optional[int]
    file_count: Optional[int]
    checksum: Optional[str]
    compression: str
    encrypted: bool
    parent_backup_id: Optional[str]
    retention_until: Optional[datetime]
    tags: List[str]
    notes: Optional[str]


class RestoreRequest(BaseModel):
    """Request to restore from backup."""
    target_path: str = Field(..., description="Target directory for restoration")
    selective_restore: Optional[List[str]] = Field(None, description="Specific files to restore")


class ScheduleBackupRequest(BaseModel):
    """Request to schedule automatic backups."""
    schedule: str = Field(..., description="Cron expression for backup schedule")
    backup_type: str = Field("incremental", regex="^(full|incremental)$")
    compression: str = Field("gzip", regex="^(none|gzip|bzip2|xz)$")
    retention_days: int = Field(30, ge=1, le=365)


# Project Launcher Endpoints

@router.post("/projects/{project_id}/start", response_model=ProcessInfoResponse)
async def start_project(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    request: ProjectStartRequest = ...,
    db: AsyncSession = Depends(get_db_session)
):
    """Start a project with the specified configuration."""
    try:
        # Build custom startup config if provided
        custom_config = None
        if any([request.custom_command, request.ports, request.env_vars, request.resource_limits]):
            from ..orchestrator.project_launcher import StartupConfig
            custom_config = StartupConfig(
                command=request.custom_command,
                environment=request.environment,
                ports=request.ports or [],
                env_vars=request.env_vars or {},
                resource_limits=request.resource_limits or {}
            )
        
        process_info = await project_launcher.start_project(
            project_id, request.environment, custom_config
        )
        
        return ProcessInfoResponse(
            pid=process_info.pid,
            name=process_info.name,
            status=process_info.status,
            cpu_percent=process_info.cpu_percent,
            memory_rss=process_info.memory_rss,
            memory_percent=process_info.memory_percent,
            ports=process_info.ports,
            started_at=process_info.started_at,
            last_seen=process_info.last_seen,
            command=process_info.command,
            environment=process_info.environment,
            logs_path=process_info.logs_path
        )
    except Exception as e:
        logger.error(f"Failed to start project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/stop")
async def stop_project(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    graceful: bool = Query(True, description="Graceful shutdown"),
    db: AsyncSession = Depends(get_db_session)
):
    """Stop a running project."""
    try:
        success = await project_launcher.stop_project(project_id, graceful)
        return {"success": success, "message": f"Project {project_id} stop {'succeeded' if success else 'failed'}"}
    except Exception as e:
        logger.error(f"Failed to stop project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/restart", response_model=ProcessInfoResponse)
async def restart_project(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    environment: Optional[str] = Query(None, description="New environment"),
    db: AsyncSession = Depends(get_db_session)
):
    """Restart a project with optional environment change."""
    try:
        process_info = await project_launcher.restart_project(project_id, environment)
        
        return ProcessInfoResponse(
            pid=process_info.pid,
            name=process_info.name,
            status=process_info.status,
            cpu_percent=process_info.cpu_percent,
            memory_rss=process_info.memory_rss,
            memory_percent=process_info.memory_percent,
            ports=process_info.ports,
            started_at=process_info.started_at,
            last_seen=process_info.last_seen,
            command=process_info.command,
            environment=process_info.environment,
            logs_path=process_info.logs_path
        )
    except Exception as e:
        logger.error(f"Failed to restart project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/status", response_model=RunningProjectResponse)
async def get_project_status(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get current status of a project."""
    try:
        running_project = await project_launcher.get_project_status(project_id)
        
        processes = [
            ProcessInfoResponse(
                pid=p.pid,
                name=p.name,
                status=p.status,
                cpu_percent=p.cpu_percent,
                memory_rss=p.memory_rss,
                memory_percent=p.memory_percent,
                ports=p.ports,
                started_at=p.started_at,
                last_seen=p.last_seen,
                command=p.command,
                environment=p.environment,
                logs_path=p.logs_path
            ) for p in running_project.processes
        ]
        
        return RunningProjectResponse(
            project_id=running_project.project_id,
            name=running_project.name,
            path=running_project.path,
            project_type=running_project.project_type.value,
            status=running_project.status.value,
            processes=processes,
            primary_port=running_project.primary_port,
            health_url=running_project.health_url,
            started_at=running_project.started_at,
            environment=running_project.environment,
            resource_limits=running_project.resource_limits
        )
    except Exception as e:
        logger.error(f"Failed to get status for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/running", response_model=List[RunningProjectResponse])
async def list_running_projects(db: AsyncSession = Depends(get_db_session)):
    """List all running projects."""
    try:
        running_projects = await project_launcher.list_running_projects()
        
        result = []
        for rp in running_projects:
            processes = [
                ProcessInfoResponse(
                    pid=p.pid,
                    name=p.name,
                    status=p.status,
                    cpu_percent=p.cpu_percent,
                    memory_rss=p.memory_rss,
                    memory_percent=p.memory_percent,
                    ports=p.ports,
                    started_at=p.started_at,
                    last_seen=p.last_seen,
                    command=p.command,
                    environment=p.environment,
                    logs_path=p.logs_path
                ) for p in rp.processes
            ]
            
            result.append(RunningProjectResponse(
                project_id=rp.project_id,
                name=rp.name,
                path=rp.path,
                project_type=rp.project_type.value,
                status=rp.status.value,
                processes=processes,
                primary_port=rp.primary_port,
                health_url=rp.health_url,
                started_at=rp.started_at,
                environment=rp.environment,
                resource_limits=rp.resource_limits
            ))
        
        return result
    except Exception as e:
        logger.error(f"Failed to list running projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/logs")
async def get_project_logs(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    lines: int = Query(100, ge=1, le=10000, description="Number of log lines to return"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get recent log lines for a project."""
    try:
        logs = await project_launcher.get_project_logs(project_id, lines)
        return {"project_id": project_id, "logs": logs, "line_count": len(logs)}
    except Exception as e:
        logger.error(f"Failed to get logs for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Environment Manager Endpoints

@router.post("/projects/{project_id}/environment/switch")
async def switch_environment(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    environment_name: str = Query(..., description="Target environment name"),
    db: AsyncSession = Depends(get_db_session)
):
    """Switch a project to a different environment."""
    try:
        success = await environment_manager.switch_environment(project_id, environment_name)
        return {"success": success, "message": f"Environment switch to {environment_name} {'succeeded' if success else 'failed'}"}
    except Exception as e:
        logger.error(f"Failed to switch environment for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/environment/variables")
async def set_environment_variables(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    request: EnvironmentVariablesRequest = ...,
    db: AsyncSession = Depends(get_db_session)
):
    """Set environment variables for a project."""
    try:
        success = await environment_manager.set_variables(
            project_id, request.variables, request.environment_name
        )
        return {"success": success, "message": f"Environment variables {'set' if success else 'failed to set'}"}
    except Exception as e:
        logger.error(f"Failed to set variables for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/environment/{environment_name}", response_model=EnvironmentResponse)
async def get_environment(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    environment_name: str = FastAPIPath(..., description="Environment name"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get environment configuration for a project."""
    try:
        environment = await environment_manager.get_environment(project_id, environment_name)
        if not environment:
            raise HTTPException(status_code=404, detail=f"Environment {environment_name} not found")
        
        return EnvironmentResponse(
            name=environment.name,
            type=environment.type.value,
            variables=environment.variables,
            config_files=list(environment.config_files.keys()),
            active=environment.active,
            created_at=environment.created_at,
            last_modified=environment.last_modified,
            description=environment.description
        )
    except Exception as e:
        logger.error(f"Failed to get environment for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/environments", response_model=List[EnvironmentResponse])
async def list_environments(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """List all environments for a project."""
    try:
        environments = await environment_manager.list_environments(project_id)
        
        return [
            EnvironmentResponse(
                name=env.name,
                type=env.type.value,
                variables=env.variables,
                config_files=list(env.config_files.keys()),
                active=env.active,
                created_at=env.created_at,
                last_modified=env.last_modified,
                description=env.description
            ) for env in environments
        ]
    except Exception as e:
        logger.error(f"Failed to list environments for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/environment/template")
async def create_environment_template(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    template_name: str = Query("default", description="Template to use"),
    db: AsyncSession = Depends(get_db_session)
):
    """Create an environment template file for a project."""
    try:
        template_path = await environment_manager.create_env_template(project_id, template_name)
        return {"template_path": template_path, "message": "Environment template created successfully"}
    except Exception as e:
        logger.error(f"Failed to create environment template for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Resource Allocator Endpoints

@router.post("/projects/{project_id}/resources/allocate")
async def allocate_resources(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    request: ResourceRequirementsRequest = ...,
    db: AsyncSession = Depends(get_db_session)
):
    """Allocate resources for a project based on requirements."""
    try:
        from ..orchestrator.resource_allocator import ResourceRequirements, ResourcePriority
        
        requirements = ResourceRequirements(
            min_cpu_percent=request.min_cpu_percent,
            max_cpu_percent=request.max_cpu_percent,
            min_memory_mb=request.min_memory_mb,
            max_memory_mb=request.max_memory_mb,
            priority=ResourcePriority(request.priority),
            auto_scale=request.auto_scale,
            scale_threshold_cpu=request.scale_threshold_cpu,
            scale_threshold_memory=request.scale_threshold_memory
        )
        
        allocation = await resource_allocator.allocate_resources(project_id, requirements)
        return allocation.to_dict()
    except Exception as e:
        logger.error(f"Failed to allocate resources for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/resources/limits")
async def set_resource_limits(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    request: ResourceLimitsRequest = ...,
    db: AsyncSession = Depends(get_db_session)
):
    """Set resource limits for a project."""
    try:
        from ..orchestrator.resource_allocator import ResourceLimits
        
        limits = ResourceLimits(
            cpu_percent=request.cpu_percent,
            cpu_cores=request.cpu_cores,
            memory_mb=request.memory_mb,
            memory_percent=request.memory_percent,
            max_processes=request.max_processes
        )
        
        success = await resource_allocator.set_limits(project_id, limits)
        return {"success": success, "message": f"Resource limits {'set' if success else 'failed to set'}"}
    except Exception as e:
        logger.error(f"Failed to set resource limits for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/resources/usage", response_model=ResourceMetricsResponse)
async def get_resource_usage(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get current resource usage metrics for a project."""
    try:
        metrics = await resource_allocator.monitor_usage(project_id)
        
        return ResourceMetricsResponse(
            project_id=metrics.project_id,
            timestamp=metrics.timestamp,
            cpu_percent=float(metrics.cpu_percent),
            cpu_cores_used=float(metrics.cpu_cores_used),
            memory_mb=float(metrics.memory_mb),
            memory_percent=float(metrics.memory_percent),
            disk_read_mb_s=float(metrics.disk_read_mb_s),
            disk_write_mb_s=float(metrics.disk_write_mb_s),
            network_upload_kb_s=float(metrics.network_upload_kb_s),
            network_download_kb_s=float(metrics.network_download_kb_s),
            process_count=metrics.process_count,
            file_descriptors=metrics.file_descriptors,
            load_average=list(metrics.load_average) if metrics.load_average else None
        )
    except Exception as e:
        logger.error(f"Failed to get resource usage for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resources/optimize")
async def optimize_resource_allocation(
    project_ids: List[str] = Query(..., description="Project IDs to optimize"),
    db: AsyncSession = Depends(get_db_session)
):
    """Optimize resource allocation across multiple projects."""
    try:
        optimization_plan = await resource_allocator.optimize_allocation(project_ids)
        return optimization_plan.to_dict()
    except Exception as e:
        logger.error(f"Failed to optimize resource allocation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/resources/predict")
async def predict_resource_usage(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    hours: int = Query(1, ge=1, le=168, description="Prediction horizon in hours"),
    db: AsyncSession = Depends(get_db_session)
):
    """Predict future resource usage for a project."""
    try:
        horizon = timedelta(hours=hours)
        prediction = await resource_allocator.predict_usage(project_id, horizon)
        return prediction.to_dict()
    except Exception as e:
        logger.error(f"Failed to predict resource usage for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/system")
async def get_system_resources(db: AsyncSession = Depends(get_db_session)):
    """Get current system resource information."""
    try:
        system_info = await resource_allocator.get_system_resources()
        return system_info
    except Exception as e:
        logger.error(f"Failed to get system resources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Deployment Assistant Endpoints

@router.post("/projects/{project_id}/deploy", response_model=DeploymentResponse)
async def deploy_project(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    request: DeploymentRequest = ...,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Deploy a project to the specified target."""
    try:
        from ..orchestrator.deployment_assistant import DeploymentConfig, DeploymentTarget
        
        config = DeploymentConfig(
            target=DeploymentTarget(request.target),
            environment=request.environment,
            build_command=request.build_command,
            test_command=request.test_command,
            deploy_command=request.deploy_command,
            health_check_url=request.health_check_url,
            env_vars=request.env_vars or {},
            auto_rollback_on_failure=request.auto_rollback
        )
        
        # Start deployment in background
        deployment_result = await deployment_assistant.deploy(
            project_id, request.target, request.environment, config
        )
        
        return DeploymentResponse(
            deployment_id=deployment_result.deployment_id,
            project_id=deployment_result.project_id,
            status=deployment_result.status.value,
            target=deployment_result.target.value,
            environment=deployment_result.environment,
            commit_hash=deployment_result.commit_hash,
            started_at=deployment_result.started_at,
            completed_at=deployment_result.completed_at,
            duration_seconds=float(deployment_result.duration_seconds) if deployment_result.duration_seconds else None,
            build_logs=deployment_result.build_logs,
            deploy_logs=deployment_result.deploy_logs,
            error_message=deployment_result.error_message,
            health_status=deployment_result.health_status.value,
            rollback_deployment_id=deployment_result.rollback_deployment_id,
            artifacts=deployment_result.artifacts
        )
    except Exception as e:
        logger.error(f"Failed to deploy project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str = FastAPIPath(..., description="Deployment identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """Rollback a deployment to the previous version."""
    try:
        success = await deployment_assistant.rollback(deployment_id)
        return {"success": success, "message": f"Rollback {'succeeded' if success else 'failed'}"}
    except Exception as e:
        logger.error(f"Failed to rollback deployment {deployment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployments/{deployment_id}/status", response_model=DeploymentResponse)
async def get_deployment_status(
    deployment_id: str = FastAPIPath(..., description="Deployment identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get status of a specific deployment."""
    try:
        deployment_result = await deployment_assistant.get_deployment_status(deployment_id)
        if not deployment_result:
            raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
        
        return DeploymentResponse(
            deployment_id=deployment_result.deployment_id,
            project_id=deployment_result.project_id,
            status=deployment_result.status.value,
            target=deployment_result.target.value,
            environment=deployment_result.environment,
            commit_hash=deployment_result.commit_hash,
            started_at=deployment_result.started_at,
            completed_at=deployment_result.completed_at,
            duration_seconds=float(deployment_result.duration_seconds) if deployment_result.duration_seconds else None,
            build_logs=deployment_result.build_logs,
            deploy_logs=deployment_result.deploy_logs,
            error_message=deployment_result.error_message,
            health_status=deployment_result.health_status.value,
            rollback_deployment_id=deployment_result.rollback_deployment_id,
            artifacts=deployment_result.artifacts
        )
    except Exception as e:
        logger.error(f"Failed to get deployment status for {deployment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/deployments", response_model=List[DeploymentResponse])
async def list_project_deployments(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """List deployments for a specific project."""
    try:
        deployments = await deployment_assistant.list_deployments(project_id)
        
        return [
            DeploymentResponse(
                deployment_id=d.deployment_id,
                project_id=d.project_id,
                status=d.status.value,
                target=d.target.value,
                environment=d.environment,
                commit_hash=d.commit_hash,
                started_at=d.started_at,
                completed_at=d.completed_at,
                duration_seconds=float(d.duration_seconds) if d.duration_seconds else None,
                build_logs=d.build_logs[-20:],  # Limit logs in list view
                deploy_logs=d.deploy_logs[-20:],
                error_message=d.error_message,
                health_status=d.health_status.value,
                rollback_deployment_id=d.rollback_deployment_id,
                artifacts=d.artifacts
            ) for d in deployments
        ]
    except Exception as e:
        logger.error(f"Failed to list deployments for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deployments/{deployment_id}/health-check")
async def run_health_check(
    deployment_id: str = FastAPIPath(..., description="Deployment identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """Run health checks for a deployment."""
    try:
        health_status = await deployment_assistant.run_health_checks(deployment_id)
        return {"deployment_id": deployment_id, "health_status": health_status.value}
    except Exception as e:
        logger.error(f"Failed to run health check for deployment {deployment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Backup Coordinator Endpoints

@router.post("/projects/{project_id}/backup", response_model=BackupResponse)
async def create_backup(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    request: BackupRequest = ...,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a backup of a project."""
    try:
        backup = await backup_coordinator.backup_project(
            project_id, request.incremental, request.tags
        )
        
        return BackupResponse(
            backup_id=backup.metadata.backup_id,
            project_id=backup.metadata.project_id,
            backup_type=backup.metadata.backup_type.value,
            status=backup.metadata.status.value,
            created_at=backup.metadata.created_at,
            completed_at=backup.metadata.completed_at,
            size_bytes=backup.metadata.size_bytes,
            compressed_size_bytes=backup.metadata.compressed_size_bytes,
            file_count=backup.metadata.file_count,
            checksum=backup.metadata.checksum,
            compression=backup.metadata.compression.value,
            encrypted=backup.metadata.encrypted,
            parent_backup_id=backup.metadata.parent_backup_id,
            retention_until=backup.metadata.retention_until,
            tags=backup.metadata.tags,
            notes=backup.metadata.notes
        )
    except Exception as e:
        logger.error(f"Failed to create backup for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: str = FastAPIPath(..., description="Backup identifier"),
    request: RestoreRequest = ...,
    db: AsyncSession = Depends(get_db_session)
):
    """Restore a project from backup."""
    try:
        success = await backup_coordinator.restore_project(
            backup_id, request.target_path, request.selective_restore
        )
        return {"success": success, "message": f"Restore {'succeeded' if success else 'failed'}"}
    except Exception as e:
        logger.error(f"Failed to restore backup {backup_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/backups", response_model=List[BackupResponse])
async def list_project_backups(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """List all backups for a project."""
    try:
        backups = await backup_coordinator.list_backups(project_id)
        
        return [
            BackupResponse(
                backup_id=b.metadata.backup_id,
                project_id=b.metadata.project_id,
                backup_type=b.metadata.backup_type.value,
                status=b.metadata.status.value,
                created_at=b.metadata.created_at,
                completed_at=b.metadata.completed_at,
                size_bytes=b.metadata.size_bytes,
                compressed_size_bytes=b.metadata.compressed_size_bytes,
                file_count=b.metadata.file_count,
                checksum=b.metadata.checksum,
                compression=b.metadata.compression.value,
                encrypted=b.metadata.encrypted,
                parent_backup_id=b.metadata.parent_backup_id,
                retention_until=b.metadata.retention_until,
                tags=b.metadata.tags,
                notes=b.metadata.notes
            ) for b in backups
        ]
    except Exception as e:
        logger.error(f"Failed to list backups for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/backup/schedule")
async def schedule_project_backup(
    project_id: str = FastAPIPath(..., description="Project identifier"),
    request: ScheduleBackupRequest = ...,
    db: AsyncSession = Depends(get_db_session)
):
    """Schedule automatic backups for a project."""
    try:
        from ..orchestrator.backup_coordinator import BackupConfig, BackupType, CompressionType
        
        config = BackupConfig(
            project_id=project_id,
            backup_type=BackupType(request.backup_type),
            compression=CompressionType(request.compression),
            retention_days=request.retention_days
        )
        
        scheduled_job = await backup_coordinator.schedule_backup(project_id, request.schedule, config)
        return scheduled_job.to_dict()
    except Exception as e:
        logger.error(f"Failed to schedule backup for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backups/cleanup")
async def cleanup_old_backups(
    days: int = Query(30, ge=1, le=365, description="Age threshold in days"),
    db: AsyncSession = Depends(get_db_session)
):
    """Clean up backups older than specified days."""
    try:
        cleaned_count = await backup_coordinator.cleanup_old_backups(days)
        return {"cleaned_count": cleaned_count, "message": f"Cleaned up {cleaned_count} old backups"}
    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backups/{backup_id}/verify")
async def verify_backup(
    backup_id: str = FastAPIPath(..., description="Backup identifier"),
    db: AsyncSession = Depends(get_db_session)
):
    """Verify integrity of a backup."""
    try:
        verification_results = await backup_coordinator.verify_backup(backup_id)
        return verification_results
    except Exception as e:
        logger.error(f"Failed to verify backup {backup_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))