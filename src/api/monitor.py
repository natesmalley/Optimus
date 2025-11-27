"""
Runtime Monitor API Endpoints
=============================

Comprehensive REST API for the Runtime Monitor system.
Provides endpoints for process monitoring, service detection, and performance analysis.

Features:
- Real-time process and service monitoring
- System performance metrics and alerts
- Memory leak detection and trend analysis
- Docker container monitoring and status
- Project runtime status tracking
- Performance alerting and threshold management
- Log file monitoring and error detection
- Resource usage analysis and optimization recommendations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..config import get_db_session
from ..services.runtime_monitor import (
    RuntimeMonitor, ProcessInfo, ServiceInfo, ContainerInfo,
    SystemMetrics, PerformanceAlert, ProcessTrend
)
from ..models.runtime import RuntimeStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# Global runtime monitor instance
_runtime_monitor: Optional[RuntimeMonitor] = None

async def get_runtime_monitor(session: AsyncSession = Depends(get_db_session)) -> RuntimeMonitor:
    """Get or create runtime monitor instance"""
    global _runtime_monitor
    if _runtime_monitor is None:
        _runtime_monitor = RuntimeMonitor(session)
        await _runtime_monitor.initialize()
    return _runtime_monitor

# =================== REQUEST/RESPONSE MODELS ===================

class ProcessResponse(BaseModel):
    """Response model for process information"""
    pid: int
    name: str
    cmdline: List[str]
    cwd: Optional[str]
    status: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    create_time: float
    ports: List[int]
    project_path: Optional[str]
    project_id: Optional[str]


class ServiceResponse(BaseModel):
    """Response model for service information"""
    name: str
    host: str
    port: int
    protocol: str
    status: str
    pid: Optional[int]
    process_name: Optional[str]
    project_path: Optional[str]
    response_time_ms: Optional[float]
    last_check: datetime


class ContainerResponse(BaseModel):
    """Response model for container information"""
    id: str
    name: str
    image: str
    status: str
    ports: Dict[str, List[Dict]]
    labels: Dict[str, str]
    created: datetime
    project_path: Optional[str]


class SystemMetricsResponse(BaseModel):
    """Response model for system metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: tuple
    processes_count: int
    active_connections: int


class PerformanceAlertResponse(BaseModel):
    """Response model for performance alerts"""
    project_id: Optional[str]
    alert_type: str
    severity: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    threshold_exceeded: float
    current_value: float


class ProcessTrendResponse(BaseModel):
    """Response model for process trends"""
    process_name: str
    pid: int
    trend_direction: str
    metric_type: str
    change_rate: float
    duration_minutes: int
    confidence: float


class ProjectRuntimeStatus(BaseModel):
    """Response model for project runtime status"""
    project_id: str
    is_running: bool
    processes: List[Dict[str, Any]]
    services: List[Dict[str, Any]]
    containers: List[Dict[str, Any]]
    last_update: str


class SystemOverviewResponse(BaseModel):
    """Response model for system overview"""
    timestamp: str
    system: Dict[str, Any]
    projects: Dict[str, Any]
    processes: Dict[str, Any]
    services: Dict[str, Any]
    containers: Dict[str, Any]


class MonitoringRequest(BaseModel):
    """Request model for monitoring configuration"""
    enable_process_monitoring: bool = Field(True, description="Enable process monitoring")
    enable_service_monitoring: bool = Field(True, description="Enable service monitoring")
    enable_container_monitoring: bool = Field(True, description="Enable container monitoring")
    enable_log_monitoring: bool = Field(True, description="Enable log file monitoring")
    monitoring_interval: int = Field(30, ge=10, le=300, description="Monitoring interval in seconds")
    performance_thresholds: Optional[Dict[str, Dict[str, float]]] = Field(None, description="Custom performance thresholds")


class MemoryLeakResponse(BaseModel):
    """Response model for memory leak detection"""
    project_id: Optional[str]
    process_name: str
    pid: int
    current_memory_mb: float
    growth_mb_per_minute: float
    confidence: float
    duration_minutes: int
    cmdline: List[str]


# =================== PROCESS MONITORING ENDPOINTS ===================

@router.get("/processes", response_model=List[ProcessResponse])
async def list_running_processes(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by process status"),
    min_cpu: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum CPU usage %"),
    min_memory: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum memory usage %"),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    limit: int = Query(50, ge=1, le=200, description="Maximum processes to return"),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    List currently running development processes.
    
    Returns processes detected as development-related with their resource
    usage, project associations, and runtime characteristics.
    """
    try:
        # Trigger fresh process scan
        processes = await monitor.scan_processes()
        
        # Apply filters
        filtered_processes = []
        
        for process in processes:
            # Project ID filter
            if project_id and process.project_id != project_id:
                continue
            
            # Status filter
            if status and process.status != status:
                continue
            
            # CPU usage filter
            if min_cpu is not None and process.cpu_percent < min_cpu:
                continue
            
            # Memory usage filter
            if min_memory is not None and process.memory_percent < min_memory:
                continue
            
            # Language filter (basic heuristic)
            if language:
                cmdline_str = ' '.join(process.cmdline).lower()
                if language.lower() not in cmdline_str:
                    continue
            
            filtered_processes.append(ProcessResponse(
                pid=process.pid,
                name=process.name,
                cmdline=process.cmdline,
                cwd=process.cwd,
                status=process.status,
                cpu_percent=process.cpu_percent,
                memory_percent=process.memory_percent,
                memory_rss=process.memory_rss,
                create_time=process.create_time,
                ports=process.ports,
                project_path=process.project_path,
                project_id=process.project_id
            ))
        
        # Sort by CPU usage (highest first) and limit
        filtered_processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        return filtered_processes[:limit]
        
    except Exception as e:
        logger.error(f"Error listing processes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve processes")


@router.get("/processes/{pid}", response_model=ProcessResponse)
async def get_process_details(
    pid: int,
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Get detailed information about a specific process.
    
    Includes resource usage, project association, ports, and performance trends.
    """
    try:
        # Check if process is in our known processes
        if pid in monitor.known_processes:
            process = monitor.known_processes[pid]
            
            return ProcessResponse(
                pid=process.pid,
                name=process.name,
                cmdline=process.cmdline,
                cwd=process.cwd,
                status=process.status,
                cpu_percent=process.cpu_percent,
                memory_percent=process.memory_percent,
                memory_rss=process.memory_rss,
                create_time=process.create_time,
                ports=process.ports,
                project_path=process.project_path,
                project_id=process.project_id
            )
        else:
            raise HTTPException(status_code=404, detail="Process not found or not monitored")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process {pid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve process details")


# =================== SERVICE MONITORING ENDPOINTS ===================

@router.get("/services", response_model=List[ServiceResponse])
async def list_active_services(
    host: str = Query("localhost", description="Host to check services on"),
    status: Optional[str] = Query(None, description="Filter by service status"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    min_response_time: Optional[float] = Query(None, ge=0.0, description="Minimum response time in ms"),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    List active services and their status.
    
    Detects running services on common ports and provides health
    information, response times, and project associations.
    """
    try:
        # Trigger fresh service scan
        services = await monitor.scan_services()
        
        # Apply filters
        filtered_services = []
        
        for service in services:
            # Host filter
            if service.host != host:
                continue
            
            # Status filter
            if status and service.status != status:
                continue
            
            # Project filter (basic implementation)
            if project_id and not (service.project_path and project_id in str(service.project_path)):
                continue
            
            # Response time filter
            if min_response_time is not None and (not service.response_time_ms or service.response_time_ms < min_response_time):
                continue
            
            filtered_services.append(ServiceResponse(
                name=service.name,
                host=service.host,
                port=service.port,
                protocol=service.protocol,
                status=service.status,
                pid=service.pid,
                process_name=service.process_name,
                project_path=service.project_path,
                response_time_ms=service.response_time_ms,
                last_check=service.last_check
            ))
        
        # Sort by port number
        filtered_services.sort(key=lambda s: s.port)
        return filtered_services
        
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve services")


@router.get("/services/{port}/health")
async def check_service_health(
    port: int,
    host: str = Query("localhost", description="Host to check"),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Check health of a specific service.
    
    Performs connectivity test and returns response time and status.
    """
    try:
        service_info = await monitor._check_port_service(port, host)
        
        if service_info:
            return {
                "port": port,
                "host": host,
                "status": "healthy",
                "service_name": service_info.name,
                "response_time_ms": service_info.response_time_ms,
                "last_check": service_info.last_check.isoformat(),
                "process_info": {
                    "pid": service_info.pid,
                    "process_name": service_info.process_name
                } if service_info.pid else None
            }
        else:
            return {
                "port": port,
                "host": host,
                "status": "unreachable",
                "message": "No service responding on this port",
                "last_check": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error checking service health on port {port}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check service health")


# =================== CONTAINER MONITORING ENDPOINTS ===================

@router.get("/containers", response_model=List[ContainerResponse])
async def list_docker_containers(
    status: Optional[str] = Query(None, description="Filter by container status"),
    project_path: Optional[str] = Query(None, description="Filter by project path"),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    List Docker containers and their status.
    
    Shows running and stopped containers with their project associations,
    port mappings, and resource usage.
    """
    try:
        # Check if Docker is available
        if not monitor.docker_client:
            return []
        
        # Trigger fresh container scan
        containers = await monitor.scan_containers()
        
        # Apply filters
        filtered_containers = []
        
        for container in containers:
            # Status filter
            if status and container.status != status:
                continue
            
            # Project path filter
            if project_path and container.project_path != project_path:
                continue
            
            filtered_containers.append(ContainerResponse(
                id=container.id,
                name=container.name,
                image=container.image,
                status=container.status,
                ports=container.ports,
                labels=container.labels,
                created=container.created,
                project_path=container.project_path
            ))
        
        # Sort by creation time (newest first)
        filtered_containers.sort(key=lambda c: c.created, reverse=True)
        return filtered_containers
        
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve containers")


# =================== PERFORMANCE MONITORING ENDPOINTS ===================

@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Get current system performance metrics.
    
    Returns CPU, memory, disk, and network usage statistics
    along with system load and process counts.
    """
    try:
        metrics = await monitor.collect_system_metrics()
        
        return SystemMetricsResponse(
            timestamp=metrics.timestamp,
            cpu_percent=metrics.cpu_percent,
            memory_percent=metrics.memory_percent,
            disk_usage_percent=metrics.disk_usage_percent,
            network_bytes_sent=metrics.network_bytes_sent,
            network_bytes_recv=metrics.network_bytes_recv,
            load_average=metrics.load_average,
            processes_count=metrics.processes_count,
            active_connections=metrics.active_connections
        )
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")


@router.get("/alerts", response_model=List[PerformanceAlertResponse])
async def get_performance_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    since: Optional[datetime] = Query(None, description="Get alerts since this timestamp"),
    limit: int = Query(50, ge=1, le=200, description="Maximum alerts to return"),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Get performance alerts and warnings.
    
    Returns alerts for resource usage thresholds, memory leaks,
    performance degradation, and system issues.
    """
    try:
        # This is a placeholder implementation
        # In a real system, you would retrieve alerts from a database or cache
        
        # For now, return empty list or generate sample alerts
        alerts = []
        
        # Check current system metrics for immediate alerts
        metrics = await monitor.collect_system_metrics()
        
        # Generate alerts based on current metrics
        if metrics.cpu_percent > 80:
            alerts.append(PerformanceAlertResponse(
                project_id=None,
                alert_type="high_cpu",
                severity="warning" if metrics.cpu_percent < 90 else "critical",
                message=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                details={
                    "cpu_percent": metrics.cpu_percent,
                    "load_average": metrics.load_average,
                    "process_count": metrics.processes_count
                },
                timestamp=metrics.timestamp,
                threshold_exceeded=80.0,
                current_value=metrics.cpu_percent
            ))
        
        if metrics.memory_percent > 85:
            alerts.append(PerformanceAlertResponse(
                project_id=None,
                alert_type="high_memory",
                severity="warning" if metrics.memory_percent < 95 else "critical",
                message=f"High memory usage: {metrics.memory_percent:.1f}%",
                details={
                    "memory_percent": metrics.memory_percent,
                    "active_connections": metrics.active_connections
                },
                timestamp=metrics.timestamp,
                threshold_exceeded=85.0,
                current_value=metrics.memory_percent
            ))
        
        if metrics.disk_usage_percent > 90:
            alerts.append(PerformanceAlertResponse(
                project_id=None,
                alert_type="disk_full",
                severity="critical",
                message=f"Disk usage critical: {metrics.disk_usage_percent:.1f}%",
                details={
                    "disk_percent": metrics.disk_usage_percent
                },
                timestamp=metrics.timestamp,
                threshold_exceeded=90.0,
                current_value=metrics.disk_usage_percent
            ))
        
        # Apply filters
        filtered_alerts = alerts
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        if project_id:
            filtered_alerts = [a for a in filtered_alerts if a.project_id == project_id]
        
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a.alert_type == alert_type]
        
        if since:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        filtered_alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return filtered_alerts[:limit]
        
    except Exception as e:
        logger.error(f"Error getting performance alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance alerts")


@router.get("/trends", response_model=List[ProcessTrendResponse])
async def get_performance_trends(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type: cpu, memory, disk_io, network"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum trend confidence"),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Get performance trends for running processes.
    
    Analyzes resource usage patterns to identify trends in CPU,
    memory, disk I/O, and network usage over time.
    """
    try:
        # This is a placeholder implementation
        # In a real system, you would analyze historical data
        
        trends = []
        
        # Analyze current processes for basic trends
        for process in monitor.known_processes.values():
            if project_id and process.project_id != project_id:
                continue
            
            # Generate sample trend data based on current usage
            if process.memory_percent > 20:  # Only for processes using significant memory
                trend = ProcessTrendResponse(
                    process_name=process.name,
                    pid=process.pid,
                    trend_direction="stable",
                    metric_type="memory",
                    change_rate=0.1,  # Placeholder
                    duration_minutes=10,  # Placeholder
                    confidence=0.8  # Placeholder
                )
                
                # Basic heuristics for trend detection
                if process.memory_percent > 50:
                    trend.trend_direction = "increasing"
                    trend.change_rate = 2.5
                    trend.confidence = 0.9
                
                if trend.confidence >= min_confidence:
                    if not metric_type or trend.metric_type == metric_type:
                        trends.append(trend)
        
        # Sort by confidence (highest first)
        trends.sort(key=lambda t: t.confidence, reverse=True)
        return trends
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance trends")


# =================== PROJECT RUNTIME STATUS ===================

@router.get("/projects/{project_id}/status", response_model=ProjectRuntimeStatus)
async def get_project_runtime_status(
    project_id: str,
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Get comprehensive runtime status for a specific project.
    
    Returns all running processes, services, containers, and
    performance metrics associated with the project.
    """
    try:
        status = await monitor.get_project_runtime_status(project_id)
        
        return ProjectRuntimeStatus(
            project_id=status["project_id"],
            is_running=status["is_running"],
            processes=status["processes"],
            services=status["services"],
            containers=status["containers"],
            last_update=status["last_update"]
        )
        
    except Exception as e:
        logger.error(f"Error getting project runtime status for {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve project runtime status")


@router.get("/projects/{project_id}/logs")
async def get_project_logs(
    project_id: str,
    log_type: str = Query("errors", description="Log type: errors, warnings, info, all"),
    max_lines: int = Query(100, ge=1, le=1000, description="Maximum log lines to return"),
    session: AsyncSession = Depends(get_db_session),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Get recent log entries for a project.
    
    Monitors project log files for errors, warnings, and
    important events with real-time analysis.
    """
    try:
        # Get project path from database
        from ..models.project import Project
        
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Monitor log files
        log_entries = await monitor.monitor_log_files(project.path, max_lines)
        
        # Filter by log type
        if log_type == "all":
            filtered_logs = {
                "errors": log_entries.get("errors", []),
                "warnings": log_entries.get("warnings", []),
                "info": log_entries.get("info", [])
            }
        else:
            filtered_logs = {
                log_type: log_entries.get(log_type, [])
            }
        
        return {
            "project_id": project_id,
            "project_path": project.path,
            "log_type": log_type,
            "max_lines": max_lines,
            "logs": filtered_logs,
            "total_entries": sum(len(entries) for entries in filtered_logs.values()),
            "last_check": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project logs for {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve project logs")


# =================== SYSTEM OVERVIEW AND ANALYTICS ===================

@router.get("/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Get comprehensive system overview.
    
    Provides aggregated view of all running processes, services,
    containers, and system performance metrics.
    """
    try:
        overview = await monitor.get_system_overview()
        
        return SystemOverviewResponse(
            timestamp=overview["timestamp"],
            system=overview["system"],
            projects=overview["projects"],
            processes=overview["processes"],
            services=overview["services"],
            containers=overview["containers"]
        )
        
    except Exception as e:
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system overview")


@router.get("/memory-leaks", response_model=List[MemoryLeakResponse])
async def detect_memory_leaks(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    min_confidence: float = Query(0.8, ge=0.0, le=1.0, description="Minimum detection confidence"),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Detect potential memory leaks in running processes.
    
    Analyzes memory usage trends to identify processes with
    consistent memory growth patterns indicating leaks.
    """
    try:
        memory_leaks = await monitor.detect_memory_leaks(project_id)
        
        # Filter by confidence
        filtered_leaks = [
            leak for leak in memory_leaks
            if leak.get("confidence", 0) >= min_confidence
        ]
        
        # Convert to response format
        leak_responses = []
        for leak in filtered_leaks:
            leak_responses.append(MemoryLeakResponse(
                project_id=leak.get("project_id"),
                process_name=leak["process_name"],
                pid=leak["pid"],
                current_memory_mb=leak["current_memory_mb"],
                growth_mb_per_minute=leak["growth_mb_per_minute"],
                confidence=leak["confidence"],
                duration_minutes=leak["duration_minutes"],
                cmdline=leak["cmdline"]
            ))
        
        return leak_responses
        
    except Exception as e:
        logger.error(f"Error detecting memory leaks: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect memory leaks")


# =================== MONITORING CONTROL ===================

@router.post("/start")
async def start_monitoring(
    config: MonitoringRequest,
    background_tasks: BackgroundTasks,
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Start continuous monitoring with specified configuration.
    
    Begins background monitoring of processes, services, and
    system performance with customizable intervals and thresholds.
    """
    try:
        # Update thresholds if provided
        if config.performance_thresholds:
            monitor.performance_thresholds.update(config.performance_thresholds)
        
        # Start monitoring in background
        background_tasks.add_task(
            monitor.continuous_monitoring,
            config.monitoring_interval
        )
        
        return {
            "message": "Monitoring started",
            "configuration": {
                "process_monitoring": config.enable_process_monitoring,
                "service_monitoring": config.enable_service_monitoring,
                "container_monitoring": config.enable_container_monitoring,
                "log_monitoring": config.enable_log_monitoring,
                "interval_seconds": config.monitoring_interval,
                "custom_thresholds": bool(config.performance_thresholds)
            },
            "status": "started",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to start monitoring")


@router.post("/projects/{project_id}/track")
async def track_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
    monitor: RuntimeMonitor = Depends(get_runtime_monitor)
):
    """
    Start tracking a specific project for runtime monitoring.
    
    Adds project to active monitoring and begins collecting
    performance data and process associations.
    """
    try:
        # Get project from database
        from ..models.project import Project
        
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Add to project mappings
        monitor.project_mapping[project.path] = project_id
        
        # Perform initial scan for this project
        await monitor.scan_processes()
        
        # Get current status
        status = await monitor.get_project_runtime_status(project_id)
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "project_path": project.path,
            "tracking_status": "active",
            "initial_status": status,
            "message": "Project tracking started",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start project tracking")


# =================== REAL-TIME MONITORING WEBSOCKET ===================

@router.websocket("/realtime")
async def monitor_realtime(websocket: WebSocket):
    """
    WebSocket endpoint for real-time monitoring updates.
    
    Provides live updates of system metrics, process changes,
    and performance alerts as they occur.
    """
    await websocket.accept()
    
    try:
        # Get monitor instance
        session = next(get_db_session())
        monitor = await get_runtime_monitor(session)
        
        # Send initial state
        overview = await monitor.get_system_overview()
        await websocket.send_json({
            "type": "system_overview",
            "data": overview,
            "timestamp": datetime.now().isoformat()
        })
        
        # Continuous monitoring loop
        while True:
            try:
                # Collect current metrics
                metrics = await monitor.collect_system_metrics()
                
                # Send metrics update
                await websocket.send_json({
                    "type": "system_metrics",
                    "data": {
                        "cpu_percent": metrics.cpu_percent,
                        "memory_percent": metrics.memory_percent,
                        "disk_usage_percent": metrics.disk_usage_percent,
                        "process_count": metrics.processes_count,
                        "active_connections": metrics.active_connections,
                        "load_average": metrics.load_average
                    },
                    "timestamp": metrics.timestamp.isoformat()
                })
                
                # Send process updates
                processes = await monitor.scan_processes()
                active_processes = [
                    {
                        "pid": p.pid,
                        "name": p.name,
                        "cpu_percent": p.cpu_percent,
                        "memory_percent": p.memory_percent,
                        "project_id": p.project_id
                    }
                    for p in processes[:20]  # Limit to top 20
                ]
                
                await websocket.send_json({
                    "type": "process_update",
                    "data": active_processes,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Check for alerts
                if metrics.cpu_percent > 80 or metrics.memory_percent > 85:
                    await websocket.send_json({
                        "type": "performance_alert",
                        "data": {
                            "alert_type": "resource_usage",
                            "severity": "warning",
                            "message": f"High resource usage: CPU {metrics.cpu_percent:.1f}%, Memory {metrics.memory_percent:.1f}%",
                            "cpu_percent": metrics.cpu_percent,
                            "memory_percent": metrics.memory_percent
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Wait before next update
                await asyncio.sleep(5)  # 5 second updates
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in realtime monitoring: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from realtime monitoring")
    except Exception as e:
        logger.error(f"WebSocket error in realtime monitoring: {e}")
    finally:
        await websocket.close()


@router.get("/health")
async def monitor_health_check():
    """
    Check runtime monitor system health.
    
    Returns monitoring capability status and performance metrics.
    """
    try:
        return {
            "status": "healthy",
            "capabilities": {
                "process_monitoring": True,
                "service_monitoring": True,
                "container_monitoring": True,  # Depends on Docker availability
                "log_monitoring": True,
                "performance_analysis": True,
                "memory_leak_detection": True,
                "trend_analysis": True
            },
            "supported_platforms": ["linux", "darwin", "windows"],
            "supported_languages": [
                "Python", "JavaScript", "TypeScript", "Rust", "Go",
                "Java", "C#", "PHP", "Ruby"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Monitor health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }