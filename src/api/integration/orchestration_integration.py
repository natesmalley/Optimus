"""
Orchestration Integration Layer
Connects the orchestration service to the API with real-time updates.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...council.orchestrator import OptimusOrchestrator
from ...models.project import Project, ProjectStatus
from ...models.runtime import RuntimeEnvironment
from ..websocket_manager import websocket_manager, Channel
from ...config import logger


class OrchestrationRequest(BaseModel):
    """Orchestration request model."""
    project_id: Optional[str] = None
    action: str  # start, stop, restart, deploy, scale
    params: Dict[str, Any] = {}
    priority: int = 5  # 1-10, 10 is highest
    user_id: Optional[str] = None


class OrchestrationResponse(BaseModel):
    """Orchestration response model."""
    request_id: str
    project_id: Optional[str]
    action: str
    status: str  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    logs: List[str] = []


class ProjectLifecycleEvent(BaseModel):
    """Project lifecycle event."""
    project_id: str
    event_type: str  # started, stopped, deployed, scaled, error
    timestamp: datetime
    details: Dict[str, Any] = {}
    user_id: Optional[str] = None


class OrchestrationStats(BaseModel):
    """Orchestration statistics."""
    total_requests: int
    active_requests: int
    completed_requests: int
    failed_requests: int
    average_completion_time: float
    active_projects: int
    running_projects: int
    stopped_projects: int
    error_projects: int


class OrchestrationIntegration:
    """Integration layer for orchestration services."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.orchestrator = OptimusOrchestrator(session)
        self.active_requests: Dict[str, OrchestrationRequest] = {}
        self.request_history: List[OrchestrationResponse] = []
        self.stats = {
            "total_requests": 0,
            "active_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "completion_times": [],
            "active_projects": 0,
            "running_projects": 0,
            "stopped_projects": 0,
            "error_projects": 0
        }
    
    async def submit_orchestration_request(self, request: OrchestrationRequest) -> str:
        """Submit orchestration request and return request ID."""
        import uuid
        request_id = str(uuid.uuid4())
        
        self.active_requests[request_id] = request
        self.stats["total_requests"] += 1
        self.stats["active_requests"] += 1
        
        # Create response object
        response = OrchestrationResponse(
            request_id=request_id,
            project_id=request.project_id,
            action=request.action,
            status="pending",
            started_at=datetime.now()
        )
        
        # Start orchestration in background
        asyncio.create_task(
            self._execute_orchestration(request_id, request, response)
        )
        
        # Broadcast orchestration update
        await self._broadcast_orchestration_update({
            "type": "request_submitted",
            "request_id": request_id,
            "action": request.action,
            "project_id": request.project_id,
            "status": "pending"
        })
        
        logger.info(f"Orchestration request submitted: {request_id} - {request.action}")
        return request_id
    
    async def _execute_orchestration(self, request_id: str, request: OrchestrationRequest, 
                                   response: OrchestrationResponse):
        """Execute orchestration request."""
        try:
            response.status = "running"
            await self._broadcast_orchestration_update({
                "type": "request_started",
                "request_id": request_id,
                "action": request.action,
                "project_id": request.project_id,
                "status": "running"
            })
            
            # Execute based on action
            if request.action == "start":
                result = await self._start_project(request.project_id, request.params)
            elif request.action == "stop":
                result = await self._stop_project(request.project_id, request.params)
            elif request.action == "restart":
                result = await self._restart_project(request.project_id, request.params)
            elif request.action == "deploy":
                result = await self._deploy_project(request.project_id, request.params)
            elif request.action == "scale":
                result = await self._scale_project(request.project_id, request.params)
            elif request.action == "analyze":
                result = await self._analyze_project(request.project_id, request.params)
            elif request.action == "optimize":
                result = await self._optimize_project(request.project_id, request.params)
            else:
                raise ValueError(f"Unknown action: {request.action}")
            
            response.status = "completed"
            response.result = result
            response.completed_at = datetime.now()
            
            # Update statistics
            completion_time = (response.completed_at - response.started_at).total_seconds()
            self.stats["completion_times"].append(completion_time)
            self.stats["completed_requests"] += 1
            
            await self._broadcast_orchestration_update({
                "type": "request_completed",
                "request_id": request_id,
                "action": request.action,
                "project_id": request.project_id,
                "status": "completed",
                "result": result,
                "completion_time": completion_time
            })
            
            logger.info(f"Orchestration request completed: {request_id}")
            
        except Exception as e:
            response.status = "failed"
            response.error = str(e)
            response.completed_at = datetime.now()
            
            self.stats["failed_requests"] += 1
            
            await self._broadcast_orchestration_update({
                "type": "request_failed",
                "request_id": request_id,
                "action": request.action,
                "project_id": request.project_id,
                "status": "failed",
                "error": str(e)
            })
            
            logger.error(f"Orchestration request failed: {request_id} - {e}")
        
        finally:
            # Clean up
            self.active_requests.pop(request_id, None)
            self.stats["active_requests"] -= 1
            self.request_history.append(response)
            
            # Keep only last 1000 requests in history
            if len(self.request_history) > 1000:
                self.request_history = self.request_history[-1000:]
    
    async def _start_project(self, project_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start a project."""
        if not project_id:
            raise ValueError("Project ID is required for start action")
        
        # Get project
        project = await self.orchestrator.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")
        
        # Start project using orchestrator
        result = await self.orchestrator.start_project(
            project_id=project_id,
            environment=params.get("environment", "development"),
            force=params.get("force", False)
        )
        
        # Broadcast project lifecycle event
        await self._broadcast_lifecycle_event({
            "project_id": project_id,
            "event_type": "started",
            "details": {
                "environment": params.get("environment", "development"),
                "result": result
            }
        })
        
        return result
    
    async def _stop_project(self, project_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a project."""
        if not project_id:
            raise ValueError("Project ID is required for stop action")
        
        result = await self.orchestrator.stop_project(
            project_id=project_id,
            graceful=params.get("graceful", True)
        )
        
        await self._broadcast_lifecycle_event({
            "project_id": project_id,
            "event_type": "stopped",
            "details": {
                "graceful": params.get("graceful", True),
                "result": result
            }
        })
        
        return result
    
    async def _restart_project(self, project_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Restart a project."""
        if not project_id:
            raise ValueError("Project ID is required for restart action")
        
        # Stop then start
        stop_result = await self._stop_project(project_id, params)
        await asyncio.sleep(2)  # Brief pause between stop and start
        start_result = await self._start_project(project_id, params)
        
        return {
            "stop_result": stop_result,
            "start_result": start_result,
            "restart_completed": True
        }
    
    async def _deploy_project(self, project_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a project."""
        if not project_id:
            raise ValueError("Project ID is required for deploy action")
        
        result = await self.orchestrator.deploy_project(
            project_id=project_id,
            target_environment=params.get("environment", "production"),
            build_args=params.get("build_args", {}),
            deploy_config=params.get("deploy_config", {})
        )
        
        await self._broadcast_lifecycle_event({
            "project_id": project_id,
            "event_type": "deployed",
            "details": {
                "environment": params.get("environment", "production"),
                "result": result
            }
        })
        
        return result
    
    async def _scale_project(self, project_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Scale a project."""
        if not project_id:
            raise ValueError("Project ID is required for scale action")
        
        replicas = params.get("replicas", 1)
        if not isinstance(replicas, int) or replicas < 0:
            raise ValueError("Replicas must be a non-negative integer")
        
        result = await self.orchestrator.scale_project(
            project_id=project_id,
            replicas=replicas
        )
        
        await self._broadcast_lifecycle_event({
            "project_id": project_id,
            "event_type": "scaled",
            "details": {
                "replicas": replicas,
                "result": result
            }
        })
        
        return result
    
    async def _analyze_project(self, project_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a project."""
        if not project_id:
            raise ValueError("Project ID is required for analyze action")
        
        analysis_type = params.get("type", "full")  # full, security, performance, dependencies
        
        result = await self.orchestrator.analyze_project(
            project_id=project_id,
            analysis_type=analysis_type,
            deep_scan=params.get("deep_scan", False)
        )
        
        await self._broadcast_lifecycle_event({
            "project_id": project_id,
            "event_type": "analyzed",
            "details": {
                "analysis_type": analysis_type,
                "result": result
            }
        })
        
        return result
    
    async def _optimize_project(self, project_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize a project."""
        if not project_id:
            raise ValueError("Project ID is required for optimize action")
        
        optimization_type = params.get("type", "performance")  # performance, dependencies, security
        
        result = await self.orchestrator.optimize_project(
            project_id=project_id,
            optimization_type=optimization_type,
            auto_apply=params.get("auto_apply", False)
        )
        
        await self._broadcast_lifecycle_event({
            "project_id": project_id,
            "event_type": "optimized",
            "details": {
                "optimization_type": optimization_type,
                "auto_applied": params.get("auto_apply", False),
                "result": result
            }
        })
        
        return result
    
    async def get_orchestration_status(self, request_id: str) -> Optional[OrchestrationResponse]:
        """Get orchestration request status."""
        # Check active requests first
        if request_id in self.active_requests:
            request = self.active_requests[request_id]
            return OrchestrationResponse(
                request_id=request_id,
                project_id=request.project_id,
                action=request.action,
                status="running",
                started_at=datetime.now()  # This should be stored properly
            )
        
        # Check history
        for response in self.request_history:
            if response.request_id == request_id:
                return response
        
        return None
    
    async def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive project status."""
        try:
            # Get project from orchestrator
            project = await self.orchestrator.get_project(project_id)
            if not project:
                return {"error": "Project not found"}
            
            # Get runtime status
            runtime_status = await self.orchestrator.get_project_runtime_status(project_id)
            
            # Get recent lifecycle events
            recent_events = [
                event for event in self.request_history[-50:]  # Last 50 events
                if event.project_id == project_id
            ]
            
            return {
                "project": asdict(project),
                "runtime_status": runtime_status,
                "recent_events": [event.dict() for event in recent_events],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting project status {project_id}: {e}")
            return {"error": str(e)}
    
    async def get_orchestration_statistics(self) -> OrchestrationStats:
        """Get orchestration statistics."""
        # Calculate averages
        completion_times = self.stats["completion_times"]
        avg_completion = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Update project counts
        try:
            await self._update_project_counts()
        except Exception as e:
            logger.error(f"Error updating project counts: {e}")
        
        return OrchestrationStats(
            total_requests=self.stats["total_requests"],
            active_requests=self.stats["active_requests"],
            completed_requests=self.stats["completed_requests"],
            failed_requests=self.stats["failed_requests"],
            average_completion_time=avg_completion,
            active_projects=self.stats["active_projects"],
            running_projects=self.stats["running_projects"],
            stopped_projects=self.stats["stopped_projects"],
            error_projects=self.stats["error_projects"]
        )
    
    async def _update_project_counts(self):
        """Update project status counts."""
        try:
            projects = await self.orchestrator.get_all_projects()
            
            active = sum(1 for p in projects if p.status == ProjectStatus.ACTIVE)
            running = sum(1 for p in projects if p.status == ProjectStatus.RUNNING) 
            stopped = sum(1 for p in projects if p.status == ProjectStatus.STOPPED)
            error = sum(1 for p in projects if p.status == ProjectStatus.ERROR)
            
            self.stats.update({
                "active_projects": active,
                "running_projects": running,
                "stopped_projects": stopped,
                "error_projects": error
            })
            
        except Exception as e:
            logger.error(f"Error updating project counts: {e}")
    
    async def _broadcast_orchestration_update(self, data: Dict[str, Any]):
        """Broadcast orchestration update via WebSocket."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.ORCHESTRATION, {
                "type": "orchestration_update",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting orchestration update: {e}")
    
    async def _broadcast_lifecycle_event(self, event_data: Dict[str, Any]):
        """Broadcast project lifecycle event."""
        try:
            event = ProjectLifecycleEvent(
                timestamp=datetime.now(),
                **event_data
            )
            
            await websocket_manager.broadcast_to_channel(Channel.PROJECTS, {
                "type": "lifecycle_event",
                "data": event.dict(),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting lifecycle event: {e}")
    
    async def cancel_orchestration_request(self, request_id: str) -> bool:
        """Cancel an active orchestration request."""
        if request_id in self.active_requests:
            # Remove from active requests
            request = self.active_requests.pop(request_id)
            self.stats["active_requests"] -= 1
            
            # Add to history as cancelled
            response = OrchestrationResponse(
                request_id=request_id,
                project_id=request.project_id,
                action=request.action,
                status="cancelled",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                error="Request cancelled by user"
            )
            self.request_history.append(response)
            
            # Broadcast cancellation
            await self._broadcast_orchestration_update({
                "type": "request_cancelled",
                "request_id": request_id,
                "action": request.action,
                "project_id": request.project_id,
                "status": "cancelled"
            })
            
            logger.info(f"Orchestration request cancelled: {request_id}")
            return True
        
        return False
    
    async def get_active_requests(self) -> List[Dict[str, Any]]:
        """Get all active orchestration requests."""
        active = []
        for request_id, request in self.active_requests.items():
            active.append({
                "request_id": request_id,
                "project_id": request.project_id,
                "action": request.action,
                "priority": request.priority,
                "user_id": request.user_id,
                "params": request.params
            })
        
        return active
    
    async def get_request_history(self, limit: int = 100) -> List[OrchestrationResponse]:
        """Get orchestration request history."""
        return self.request_history[-limit:] if self.request_history else []