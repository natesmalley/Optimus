"""
Deployment Integration Layer
Connects deployment pipelines and management to the API.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..websocket_manager import websocket_manager, Channel
from ...config import logger


class DeploymentStatus(str, Enum):
    """Deployment status values."""
    PENDING = "pending"
    PREPARING = "preparing"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"


class DeploymentEnvironment(str, Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DeploymentStrategy(str, Enum):
    """Deployment strategies."""
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"
    RECREATE = "recreate"
    IMMEDIATE = "immediate"


class DeploymentRequest(BaseModel):
    """Deployment request model."""
    project_id: str
    environment: DeploymentEnvironment
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    git_ref: Optional[str] = "main"  # branch, tag, or commit hash
    build_args: Dict[str, Any] = {}
    environment_vars: Dict[str, str] = {}
    replicas: int = 1
    health_check_url: Optional[str] = None
    rollback_on_failure: bool = True
    user_id: Optional[str] = None
    notes: Optional[str] = None


class DeploymentStep(BaseModel):
    """Individual deployment step."""
    step_id: str
    name: str
    status: str  # pending, running, completed, failed, skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    logs: List[str] = []
    error: Optional[str] = None


class DeploymentInfo(BaseModel):
    """Deployment information."""
    deployment_id: str
    project_id: str
    project_name: str
    environment: DeploymentEnvironment
    strategy: DeploymentStrategy
    status: DeploymentStatus
    git_ref: str
    build_number: Optional[int] = None
    steps: List[DeploymentStep] = []
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    deployed_by: Optional[str] = None
    rollback_target: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = {}


class DeploymentStats(BaseModel):
    """Deployment statistics."""
    total_deployments: int
    active_deployments: int
    completed_deployments: int
    failed_deployments: int
    success_rate: float
    average_deployment_time: float
    deployments_by_environment: Dict[str, int]
    deployments_by_status: Dict[str, int]
    recent_activity: List[Dict[str, Any]]


class DeploymentIntegration:
    """Integration layer for deployment management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.active_deployments: Dict[str, DeploymentInfo] = {}
        self.deployment_history: List[DeploymentInfo] = []
        self.deployment_queue: List[DeploymentRequest] = []
        
        # Statistics
        self.stats = {
            "total_deployments": 0,
            "active_deployments": 0,
            "completed_deployments": 0,
            "failed_deployments": 0,
            "deployment_times": [],
            "deployments_by_env": {env.value: 0 for env in DeploymentEnvironment},
            "deployments_by_status": {status.value: 0 for status in DeploymentStatus}
        }
        
        # Configuration
        self.max_concurrent_deployments = 5
        self.deployment_timeout_minutes = 30
    
    async def submit_deployment(self, request: DeploymentRequest) -> str:
        """Submit a new deployment request."""
        import uuid
        deployment_id = str(uuid.uuid4())
        
        # Create deployment info
        deployment = DeploymentInfo(
            deployment_id=deployment_id,
            project_id=request.project_id,
            project_name=request.project_id,  # Would be fetched from project service
            environment=request.environment,
            strategy=request.strategy,
            status=DeploymentStatus.PENDING,
            git_ref=request.git_ref or "main",
            created_at=datetime.now(),
            deployed_by=request.user_id,
            notes=request.notes,
            metadata={
                "build_args": request.build_args,
                "environment_vars": request.environment_vars,
                "replicas": request.replicas,
                "health_check_url": request.health_check_url,
                "rollback_on_failure": request.rollback_on_failure
            }
        )
        
        # Check if we can start immediately or need to queue
        if len(self.active_deployments) < self.max_concurrent_deployments:
            self.active_deployments[deployment_id] = deployment
            self.stats["active_deployments"] += 1
            
            # Start deployment
            asyncio.create_task(self._execute_deployment(deployment_id, request))
        else:
            # Add to queue
            self.deployment_queue.append(request)
            deployment.metadata["queued"] = True
        
        self.stats["total_deployments"] += 1
        self.stats["deployments_by_env"][request.environment.value] += 1
        self.stats["deployments_by_status"][DeploymentStatus.PENDING.value] += 1
        
        # Broadcast deployment submitted
        await self._broadcast_deployment_update({
            "deployment_id": deployment_id,
            "type": "deployment_submitted",
            "status": deployment.status.value,
            "project_id": request.project_id,
            "environment": request.environment.value,
            "queued": deployment.metadata.get("queued", False)
        })
        
        logger.info(f"Deployment submitted: {deployment_id} for project {request.project_id}")
        return deployment_id
    
    async def _execute_deployment(self, deployment_id: str, request: DeploymentRequest):
        """Execute a deployment."""
        deployment = self.active_deployments[deployment_id]
        
        try:
            deployment.status = DeploymentStatus.PREPARING
            deployment.started_at = datetime.now()
            self.stats["deployments_by_status"][DeploymentStatus.PREPARING.value] += 1
            
            await self._broadcast_deployment_update({
                "deployment_id": deployment_id,
                "type": "deployment_started",
                "status": deployment.status.value,
                "project_id": request.project_id,
                "environment": request.environment.value
            })
            
            # Define deployment steps based on strategy
            steps = self._get_deployment_steps(request.strategy)
            deployment.steps = [
                DeploymentStep(
                    step_id=f"{deployment_id}_{i}",
                    name=step_name,
                    status="pending"
                )
                for i, step_name in enumerate(steps)
            ]
            
            # Execute each step
            for step in deployment.steps:
                await self._execute_deployment_step(deployment, step, request)
                
                if step.status == "failed":
                    deployment.status = DeploymentStatus.FAILED
                    break
            else:
                deployment.status = DeploymentStatus.COMPLETED
                self.stats["completed_deployments"] += 1
            
            deployment.completed_at = datetime.now()
            if deployment.started_at:
                duration = (deployment.completed_at - deployment.started_at).total_seconds()
                deployment.duration_seconds = duration
                self.stats["deployment_times"].append(duration)
            
            # Update status counts
            self.stats["deployments_by_status"][deployment.status.value] += 1
            if deployment.status == DeploymentStatus.FAILED:
                self.stats["failed_deployments"] += 1
            
            # Broadcast completion
            await self._broadcast_deployment_update({
                "deployment_id": deployment_id,
                "type": "deployment_completed",
                "status": deployment.status.value,
                "project_id": request.project_id,
                "environment": request.environment.value,
                "duration": deployment.duration_seconds,
                "success": deployment.status == DeploymentStatus.COMPLETED
            })
            
            logger.info(f"Deployment {'completed' if deployment.status == DeploymentStatus.COMPLETED else 'failed'}: {deployment_id}")
            
        except asyncio.TimeoutError:
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.now()
            self.stats["failed_deployments"] += 1
            
            logger.error(f"Deployment timed out: {deployment_id}")
            
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.now()
            self.stats["failed_deployments"] += 1
            
            logger.error(f"Deployment failed: {deployment_id} - {e}")
        
        finally:
            # Move to history
            self.active_deployments.pop(deployment_id, None)
            self.stats["active_deployments"] -= 1
            self.deployment_history.append(deployment)
            
            # Keep only last 1000 deployments
            if len(self.deployment_history) > 1000:
                self.deployment_history = self.deployment_history[-1000:]
            
            # Start next deployment from queue
            await self._start_next_from_queue()
    
    def _get_deployment_steps(self, strategy: DeploymentStrategy) -> List[str]:
        """Get deployment steps based on strategy."""
        common_steps = [
            "Validate Configuration",
            "Pull Source Code",
            "Build Application",
            "Run Tests"
        ]
        
        if strategy == DeploymentStrategy.BLUE_GREEN:
            return common_steps + [
                "Create Blue Environment",
                "Deploy to Blue",
                "Health Check Blue",
                "Switch Traffic to Blue",
                "Terminate Green"
            ]
        elif strategy == DeploymentStrategy.ROLLING:
            return common_steps + [
                "Start Rolling Update",
                "Update Instance 1",
                "Health Check Instance 1",
                "Update Instance 2",
                "Health Check Instance 2",
                "Complete Rolling Update"
            ]
        elif strategy == DeploymentStrategy.CANARY:
            return common_steps + [
                "Deploy Canary (10%)",
                "Monitor Canary",
                "Deploy to 50%",
                "Monitor Performance",
                "Deploy to 100%"
            ]
        else:  # RECREATE or IMMEDIATE
            return common_steps + [
                "Stop Existing Services",
                "Deploy New Version",
                "Start Services",
                "Health Check"
            ]
    
    async def _execute_deployment_step(self, deployment: DeploymentInfo, step: DeploymentStep, 
                                     request: DeploymentRequest):
        """Execute a single deployment step."""
        step.status = "running"
        step.started_at = datetime.now()
        
        # Broadcast step update
        await self._broadcast_step_update(deployment.deployment_id, step)
        
        try:
            # Simulate step execution based on step name
            if "Build" in step.name:
                await self._simulate_build_step(step, request)
            elif "Test" in step.name:
                await self._simulate_test_step(step, request)
            elif "Deploy" in step.name:
                await self._simulate_deploy_step(step, request)
            elif "Health Check" in step.name:
                await self._simulate_health_check_step(step, request)
            else:
                await self._simulate_generic_step(step, request)
            
            step.status = "completed"
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.logs.append(f"ERROR: {e}")
        
        step.completed_at = datetime.now()
        if step.started_at:
            step.duration_seconds = (step.completed_at - step.started_at).total_seconds()
        
        # Broadcast step completion
        await self._broadcast_step_update(deployment.deployment_id, step)
    
    async def _simulate_build_step(self, step: DeploymentStep, request: DeploymentRequest):
        """Simulate build step."""
        step.logs.append("Starting build process...")
        await asyncio.sleep(2)  # Simulate build time
        
        step.logs.append(f"Building project {request.project_id}")
        await asyncio.sleep(3)
        
        step.logs.append("Build completed successfully")
    
    async def _simulate_test_step(self, step: DeploymentStep, request: DeploymentRequest):
        """Simulate test step."""
        step.logs.append("Running test suite...")
        await asyncio.sleep(1)
        
        step.logs.append("All tests passed")
    
    async def _simulate_deploy_step(self, step: DeploymentStep, request: DeploymentRequest):
        """Simulate deploy step."""
        step.logs.append(f"Deploying to {request.environment.value}")
        await asyncio.sleep(2)
        
        step.logs.append(f"Deployment to {request.environment.value} completed")
    
    async def _simulate_health_check_step(self, step: DeploymentStep, request: DeploymentRequest):
        """Simulate health check step."""
        step.logs.append("Performing health check...")
        await asyncio.sleep(1)
        
        health_check_url = request.health_check_url
        if health_check_url:
            step.logs.append(f"Health check URL: {health_check_url}")
        
        step.logs.append("Health check passed")
    
    async def _simulate_generic_step(self, step: DeploymentStep, request: DeploymentRequest):
        """Simulate generic step."""
        step.logs.append(f"Executing {step.name}...")
        await asyncio.sleep(1)
        
        step.logs.append(f"{step.name} completed")
    
    async def _start_next_from_queue(self):
        """Start next deployment from queue if available."""
        if (self.deployment_queue and 
            len(self.active_deployments) < self.max_concurrent_deployments):
            
            next_request = self.deployment_queue.pop(0)
            
            # Submit the queued deployment
            await self.submit_deployment(next_request)
    
    async def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentInfo]:
        """Get deployment status."""
        # Check active deployments
        if deployment_id in self.active_deployments:
            return self.active_deployments[deployment_id]
        
        # Check history
        for deployment in self.deployment_history:
            if deployment.deployment_id == deployment_id:
                return deployment
        
        return None
    
    async def get_deployments_by_project(self, project_id: str) -> List[DeploymentInfo]:
        """Get deployments for a specific project."""
        deployments = []
        
        # Add active deployments
        for deployment in self.active_deployments.values():
            if deployment.project_id == project_id:
                deployments.append(deployment)
        
        # Add historical deployments
        for deployment in self.deployment_history:
            if deployment.project_id == project_id:
                deployments.append(deployment)
        
        # Sort by creation time, newest first
        deployments.sort(key=lambda x: x.created_at, reverse=True)
        return deployments
    
    async def get_deployments_by_environment(self, environment: DeploymentEnvironment) -> List[DeploymentInfo]:
        """Get deployments for a specific environment."""
        deployments = []
        
        # Add active deployments
        for deployment in self.active_deployments.values():
            if deployment.environment == environment:
                deployments.append(deployment)
        
        # Add historical deployments
        for deployment in self.deployment_history:
            if deployment.environment == environment:
                deployments.append(deployment)
        
        deployments.sort(key=lambda x: x.created_at, reverse=True)
        return deployments
    
    async def cancel_deployment(self, deployment_id: str) -> bool:
        """Cancel an active deployment."""
        if deployment_id in self.active_deployments:
            deployment = self.active_deployments[deployment_id]
            deployment.status = DeploymentStatus.CANCELLED
            deployment.completed_at = datetime.now()
            
            # Move to history
            self.active_deployments.pop(deployment_id)
            self.stats["active_deployments"] -= 1
            self.deployment_history.append(deployment)
            
            # Broadcast cancellation
            await self._broadcast_deployment_update({
                "deployment_id": deployment_id,
                "type": "deployment_cancelled",
                "status": deployment.status.value,
                "project_id": deployment.project_id,
                "environment": deployment.environment.value
            })
            
            # Start next from queue
            await self._start_next_from_queue()
            
            logger.info(f"Deployment cancelled: {deployment_id}")
            return True
        
        return False
    
    async def rollback_deployment(self, project_id: str, environment: DeploymentEnvironment, 
                                target_deployment_id: str = None) -> str:
        """Initiate rollback for a project environment."""
        # Find target deployment for rollback
        project_deployments = await self.get_deployments_by_project(project_id)
        environment_deployments = [
            d for d in project_deployments 
            if d.environment == environment and d.status == DeploymentStatus.COMPLETED
        ]
        
        if not environment_deployments:
            raise ValueError(f"No successful deployments found for {project_id} in {environment.value}")
        
        if target_deployment_id:
            target_deployment = next(
                (d for d in environment_deployments if d.deployment_id == target_deployment_id),
                None
            )
            if not target_deployment:
                raise ValueError(f"Target deployment {target_deployment_id} not found")
        else:
            # Use the second most recent (rollback to previous)
            if len(environment_deployments) < 2:
                raise ValueError("No previous deployment to rollback to")
            target_deployment = environment_deployments[1]
        
        # Create rollback deployment request
        rollback_request = DeploymentRequest(
            project_id=project_id,
            environment=environment,
            strategy=DeploymentStrategy.IMMEDIATE,  # Fast rollback
            git_ref=target_deployment.git_ref,
            build_args=target_deployment.metadata.get("build_args", {}),
            environment_vars=target_deployment.metadata.get("environment_vars", {}),
            replicas=target_deployment.metadata.get("replicas", 1),
            notes=f"Rollback to deployment {target_deployment.deployment_id}"
        )
        
        deployment_id = await self.submit_deployment(rollback_request)
        
        # Mark as rollback
        if deployment_id in self.active_deployments:
            self.active_deployments[deployment_id].rollback_target = target_deployment.deployment_id
        
        return deployment_id
    
    async def get_deployment_statistics(self) -> DeploymentStats:
        """Get deployment statistics."""
        # Calculate success rate
        completed = self.stats["completed_deployments"]
        failed = self.stats["failed_deployments"]
        total_finished = completed + failed
        success_rate = completed / total_finished if total_finished > 0 else 0
        
        # Calculate average deployment time
        times = self.stats["deployment_times"]
        avg_time = sum(times) / len(times) if times else 0
        
        # Recent activity (last 10 deployments)
        recent_activity = []
        all_deployments = list(self.active_deployments.values()) + self.deployment_history
        all_deployments.sort(key=lambda x: x.created_at, reverse=True)
        
        for deployment in all_deployments[:10]:
            recent_activity.append({
                "deployment_id": deployment.deployment_id,
                "project_id": deployment.project_id,
                "environment": deployment.environment.value,
                "status": deployment.status.value,
                "created_at": deployment.created_at.isoformat(),
                "duration": deployment.duration_seconds
            })
        
        return DeploymentStats(
            total_deployments=self.stats["total_deployments"],
            active_deployments=self.stats["active_deployments"],
            completed_deployments=completed,
            failed_deployments=failed,
            success_rate=success_rate,
            average_deployment_time=avg_time,
            deployments_by_environment=dict(self.stats["deployments_by_env"]),
            deployments_by_status=dict(self.stats["deployments_by_status"]),
            recent_activity=recent_activity
        )
    
    async def get_deployment_queue(self) -> List[Dict[str, Any]]:
        """Get current deployment queue."""
        return [
            {
                "project_id": req.project_id,
                "environment": req.environment.value,
                "strategy": req.strategy.value,
                "git_ref": req.git_ref,
                "user_id": req.user_id,
                "notes": req.notes
            }
            for req in self.deployment_queue
        ]
    
    async def _broadcast_deployment_update(self, data: Dict[str, Any]):
        """Broadcast deployment update via WebSocket."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.DEPLOYMENT, {
                "type": "deployment_update",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting deployment update: {e}")
    
    async def _broadcast_step_update(self, deployment_id: str, step: DeploymentStep):
        """Broadcast deployment step update."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.DEPLOYMENT, {
                "type": "deployment_step_update",
                "data": {
                    "deployment_id": deployment_id,
                    "step": step.dict()
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting step update: {e}")