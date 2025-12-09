"""
Deployment Assistant Service

Manages automated deployment pipelines, Git integration, Docker deployments,
rollback capabilities, and health check validation for seamless project deployments.
"""

import asyncio
import subprocess
import logging
import json
import yaml
import shutil
import tempfile
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Deployment status enumeration."""
    PENDING = "pending"
    PREPARING = "preparing"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class DeploymentTarget(Enum):
    """Supported deployment targets."""
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    HEROKU = "heroku"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    VERCEL = "vercel"
    NETLIFY = "netlify"
    CUSTOM = "custom"


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    target: DeploymentTarget
    environment: str = "production"
    build_command: Optional[str] = None
    test_command: Optional[str] = None
    deploy_command: Optional[str] = None
    health_check_url: Optional[str] = None
    health_check_timeout: int = 60
    rollback_enabled: bool = True
    auto_rollback_on_failure: bool = True
    env_vars: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    docker_config: Optional[Dict[str, Any]] = None
    kubernetes_config: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "target": self.target.value,
            "environment": self.environment,
            "build_command": self.build_command,
            "test_command": self.test_command,
            "deploy_command": self.deploy_command,
            "health_check_url": self.health_check_url,
            "health_check_timeout": self.health_check_timeout,
            "rollback_enabled": self.rollback_enabled,
            "auto_rollback_on_failure": self.auto_rollback_on_failure,
            "env_vars": self.env_vars,
            "secrets": {k: "***REDACTED***" for k in self.secrets.keys()},
            "docker_config": self.docker_config,
            "kubernetes_config": self.kubernetes_config
        }


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    deployment_id: str
    project_id: str
    status: DeploymentStatus
    target: DeploymentTarget
    environment: str
    commit_hash: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    build_logs: List[str] = field(default_factory=list)
    deploy_logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    health_status: HealthStatus = HealthStatus.UNKNOWN
    rollback_deployment_id: Optional[str] = None
    artifacts: Dict[str, str] = field(default_factory=dict)  # artifact_name -> location
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "deployment_id": self.deployment_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "target": self.target.value,
            "environment": self.environment,
            "commit_hash": self.commit_hash,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "build_logs": self.build_logs[-50:],  # Last 50 lines only
            "deploy_logs": self.deploy_logs[-50:],  # Last 50 lines only
            "error_message": self.error_message,
            "health_status": self.health_status.value,
            "rollback_deployment_id": self.rollback_deployment_id,
            "artifacts": self.artifacts
        }


@dataclass
class Pipeline:
    """Deployment pipeline configuration."""
    name: str
    project_id: str
    stages: List[Dict[str, Any]]
    triggers: List[str] = field(default_factory=list)  # git branches, tags, manual
    config: DeploymentConfig = field(default_factory=lambda: DeploymentConfig(DeploymentTarget.LOCAL))
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "project_id": self.project_id,
            "stages": self.stages,
            "triggers": self.triggers,
            "config": self.config.to_dict(),
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class HealthCheck:
    """Health check configuration and result."""
    url: str
    method: str = "GET"
    expected_status: int = 200
    timeout: int = 30
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    response_text: Optional[str] = None
    response_time_ms: Optional[float] = None
    status: HealthStatus = HealthStatus.UNKNOWN
    error_message: Optional[str] = None
    checked_at: Optional[datetime] = None


@dataclass
class Deployment:
    """Blue-green deployment information."""
    deployment_id: str
    project_id: str
    environment: str
    blue_instance: Optional[str] = None
    green_instance: Optional[str] = None
    active_instance: Optional[str] = "blue"
    traffic_split: Dict[str, int] = field(default_factory=lambda: {"blue": 100, "green": 0})
    switch_time: Optional[datetime] = None


class DeploymentAssistant:
    """
    Manages automated deployment pipelines with Git integration, Docker support,
    rollback capabilities, and comprehensive health checking.
    """
    
    def __init__(self, base_projects_path: str = "/Users/nathanial.smalley/projects"):
        """
        Initialize the DeploymentAssistant.
        
        Args:
            base_projects_path: Base directory containing all projects
        """
        self.base_projects_path = Path(base_projects_path)
        self.deployments: Dict[str, DeploymentResult] = {}
        self.pipelines: Dict[str, Pipeline] = {}
        self.deployment_configs: Dict[str, DeploymentConfig] = {}
        self.blue_green_deployments: Dict[str, Deployment] = {}
        
        # Deployment tracking
        self.deployment_counter = 0
        self.max_concurrent_deployments = 3
        self.active_deployments: Set[str] = set()
        
        # Paths
        self.deployments_dir = Path("deployments")
        self.deployments_dir.mkdir(exist_ok=True)
        
        logger.info(f"DeploymentAssistant initialized with base path: {self.base_projects_path}")
    
    async def deploy(self, project_id: str, target: str, environment: str = "production", config: Optional[DeploymentConfig] = None) -> DeploymentResult:
        """
        Deploy a project to the specified target.
        
        Args:
            project_id: Project identifier
            target: Deployment target
            environment: Target environment
            config: Optional deployment configuration
            
        Returns:
            DeploymentResult: Deployment result
        """
        deployment_id = f"deploy_{project_id}_{int(datetime.now().timestamp())}"
        logger.info(f"Starting deployment {deployment_id} for project {project_id} to {target}")
        
        try:
            # Check concurrent deployment limits
            if len(self.active_deployments) >= self.max_concurrent_deployments:
                raise RuntimeError(f"Maximum concurrent deployments ({self.max_concurrent_deployments}) reached")
            
            # Get deployment configuration
            deploy_config = config or await self._get_deployment_config(project_id, target, environment)
            
            # Create deployment result
            result = DeploymentResult(
                deployment_id=deployment_id,
                project_id=project_id,
                status=DeploymentStatus.PREPARING,
                target=DeploymentTarget(target),
                environment=environment
            )
            
            # Register deployment
            self.deployments[deployment_id] = result
            self.active_deployments.add(deployment_id)
            
            # Get project path and Git info
            project_path = await self._find_project_path(project_id)
            commit_hash = await self._get_current_commit(project_path)
            result.commit_hash = commit_hash
            
            # Create deployment directory
            deployment_dir = self.deployments_dir / deployment_id
            deployment_dir.mkdir(exist_ok=True)
            
            # Execute deployment pipeline
            success = await self._execute_deployment_pipeline(result, deploy_config, project_path, deployment_dir)
            
            if success:
                result.status = DeploymentStatus.SUCCESS
                result.health_status = await self._perform_health_check(deploy_config)
                
                # Auto-rollback on health check failure
                if result.health_status == HealthStatus.UNHEALTHY and deploy_config.auto_rollback_on_failure:
                    logger.warning(f"Health check failed for {deployment_id}, initiating auto-rollback")
                    await self._auto_rollback(result)
            else:
                result.status = DeploymentStatus.FAILED
                
                # Auto-rollback on deployment failure
                if deploy_config.auto_rollback_on_failure:
                    await self._auto_rollback(result)
            
            # Complete deployment
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            
            # Cleanup
            self.active_deployments.discard(deployment_id)
            
            logger.info(f"Deployment {deployment_id} completed with status: {result.status.value}")
            return result
            
        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {str(e)}")
            
            # Update result if it exists
            if deployment_id in self.deployments:
                result = self.deployments[deployment_id]
                result.status = DeploymentStatus.FAILED
                result.error_message = str(e)
                result.completed_at = datetime.now()
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            
            # Cleanup
            self.active_deployments.discard(deployment_id)
            
            raise RuntimeError(f"Deployment failed: {str(e)}")
    
    async def rollback(self, deployment_id: str) -> bool:
        """
        Rollback a deployment to the previous version.
        
        Args:
            deployment_id: Deployment to rollback
            
        Returns:
            bool: True if successfully rolled back
        """
        logger.info(f"Rolling back deployment {deployment_id}")
        
        try:
            if deployment_id not in self.deployments:
                raise ValueError(f"Deployment {deployment_id} not found")
            
            deployment = self.deployments[deployment_id]
            
            if deployment.status != DeploymentStatus.SUCCESS:
                raise ValueError(f"Cannot rollback deployment with status {deployment.status.value}")
            
            # Find previous successful deployment
            previous_deployment = await self._find_previous_deployment(deployment.project_id, deployment_id)
            
            if not previous_deployment:
                raise ValueError("No previous deployment found for rollback")
            
            # Create rollback deployment
            rollback_id = f"rollback_{deployment_id}_{int(datetime.now().timestamp())}"
            
            rollback_result = DeploymentResult(
                deployment_id=rollback_id,
                project_id=deployment.project_id,
                status=DeploymentStatus.ROLLING_BACK,
                target=deployment.target,
                environment=deployment.environment,
                commit_hash=previous_deployment.commit_hash
            )
            
            self.deployments[rollback_id] = rollback_result
            
            # Execute rollback
            success = await self._execute_rollback(deployment, previous_deployment, rollback_result)
            
            if success:
                deployment.status = DeploymentStatus.ROLLED_BACK
                rollback_result.status = DeploymentStatus.SUCCESS
                deployment.rollback_deployment_id = rollback_id
            else:
                rollback_result.status = DeploymentStatus.FAILED
            
            rollback_result.completed_at = datetime.now()
            rollback_result.duration_seconds = (rollback_result.completed_at - rollback_result.started_at).total_seconds()
            
            logger.info(f"Rollback completed with status: {rollback_result.status.value}")
            return success
            
        except Exception as e:
            logger.error(f"Rollback failed for {deployment_id}: {str(e)}")
            return False
    
    async def create_pipeline(self, project_id: str, pipeline_name: str, config: DeploymentConfig) -> Pipeline:
        """
        Create a deployment pipeline for a project.
        
        Args:
            project_id: Project identifier
            pipeline_name: Name of the pipeline
            config: Deployment configuration
            
        Returns:
            Pipeline: Created pipeline
        """
        logger.info(f"Creating pipeline '{pipeline_name}' for project {project_id}")
        
        try:
            # Default pipeline stages
            stages = [
                {"name": "checkout", "type": "git", "config": {"fetch": True, "clean": True}},
                {"name": "build", "type": "command", "config": {"command": config.build_command}},
                {"name": "test", "type": "command", "config": {"command": config.test_command}},
                {"name": "deploy", "type": "deploy", "config": config.to_dict()},
                {"name": "health_check", "type": "health", "config": {"url": config.health_check_url}}
            ]
            
            # Remove stages with empty commands
            stages = [stage for stage in stages if stage["config"].get("command") or stage["type"] in ["git", "deploy", "health"]]
            
            pipeline = Pipeline(
                name=pipeline_name,
                project_id=project_id,
                stages=stages,
                triggers=["main", "master", "production"],  # Default triggers
                config=config
            )
            
            # Store pipeline
            pipeline_key = f"{project_id}_{pipeline_name}"
            self.pipelines[pipeline_key] = pipeline
            
            # Save pipeline configuration
            await self._save_pipeline_config(pipeline)
            
            logger.info(f"Successfully created pipeline '{pipeline_name}' with {len(stages)} stages")
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to create pipeline: {str(e)}")
            raise
    
    async def run_health_checks(self, deployment_id: str) -> HealthStatus:
        """
        Run comprehensive health checks for a deployment.
        
        Args:
            deployment_id: Deployment to check
            
        Returns:
            HealthStatus: Overall health status
        """
        logger.info(f"Running health checks for deployment {deployment_id}")
        
        try:
            if deployment_id not in self.deployments:
                raise ValueError(f"Deployment {deployment_id} not found")
            
            deployment = self.deployments[deployment_id]
            config = await self._get_deployment_config(deployment.project_id, deployment.target.value, deployment.environment)
            
            health_checks = []
            
            # Primary health check
            if config.health_check_url:
                primary_check = HealthCheck(
                    url=config.health_check_url,
                    timeout=config.health_check_timeout
                )
                result = await self._execute_health_check(primary_check)
                health_checks.append(result)
            
            # Additional health checks based on target
            additional_checks = await self._get_additional_health_checks(deployment)
            for check in additional_checks:
                result = await self._execute_health_check(check)
                health_checks.append(result)
            
            # Determine overall health status
            if not health_checks:
                overall_status = HealthStatus.UNKNOWN
            elif all(check.status == HealthStatus.HEALTHY for check in health_checks):
                overall_status = HealthStatus.HEALTHY
            elif any(check.status == HealthStatus.UNHEALTHY for check in health_checks):
                overall_status = HealthStatus.UNHEALTHY
            else:
                overall_status = HealthStatus.DEGRADED
            
            # Update deployment health status
            deployment.health_status = overall_status
            
            logger.info(f"Health checks completed for {deployment_id}: {overall_status.value}")
            return overall_status
            
        except Exception as e:
            logger.error(f"Health check failed for {deployment_id}: {str(e)}")
            return HealthStatus.UNHEALTHY
    
    async def blue_green_deploy(self, project_id: str, environment: str = "production") -> Deployment:
        """
        Perform blue-green deployment for zero-downtime deployments.
        
        Args:
            project_id: Project identifier
            environment: Target environment
            
        Returns:
            Deployment: Blue-green deployment information
        """
        logger.info(f"Starting blue-green deployment for project {project_id}")
        
        try:
            # Get or create blue-green deployment record
            bg_key = f"{project_id}_{environment}"
            
            if bg_key not in self.blue_green_deployments:
                bg_deployment = Deployment(
                    deployment_id=f"bg_{project_id}_{int(datetime.now().timestamp())}",
                    project_id=project_id,
                    environment=environment
                )
                self.blue_green_deployments[bg_key] = bg_deployment
            else:
                bg_deployment = self.blue_green_deployments[bg_key]
            
            # Determine target instance (switch to inactive one)
            if bg_deployment.active_instance == "blue":
                target_instance = "green"
            else:
                target_instance = "blue"
            
            logger.info(f"Deploying to {target_instance} instance")
            
            # Deploy to target instance
            config = await self._get_deployment_config(project_id, "docker", environment)
            
            # Modify config for blue-green deployment
            instance_config = DeploymentConfig(
                target=config.target,
                environment=f"{environment}_{target_instance}",
                build_command=config.build_command,
                test_command=config.test_command,
                deploy_command=config.deploy_command,
                health_check_url=config.health_check_url.replace("//", f"//{target_instance}.") if config.health_check_url else None,
                env_vars={**config.env_vars, "INSTANCE": target_instance}
            )
            
            # Execute deployment to target instance
            deployment_result = await self.deploy(project_id, config.target.value, instance_config.environment, instance_config)
            
            if deployment_result.status == DeploymentStatus.SUCCESS:
                # Update instance information
                if target_instance == "blue":
                    bg_deployment.blue_instance = deployment_result.deployment_id
                else:
                    bg_deployment.green_instance = deployment_result.deployment_id
                
                # Perform health check on new instance
                health_status = await self.run_health_checks(deployment_result.deployment_id)
                
                if health_status == HealthStatus.HEALTHY:
                    # Switch traffic to new instance
                    await self._switch_traffic(bg_deployment, target_instance)
                    bg_deployment.active_instance = target_instance
                    bg_deployment.switch_time = datetime.now()
                    
                    logger.info(f"Blue-green deployment successful, switched to {target_instance}")
                else:
                    logger.warning(f"Health check failed on {target_instance} instance, keeping traffic on {bg_deployment.active_instance}")
            
            return bg_deployment
            
        except Exception as e:
            logger.error(f"Blue-green deployment failed: {str(e)}")
            raise
    
    async def list_deployments(self, project_id: Optional[str] = None) -> List[DeploymentResult]:
        """
        List deployments, optionally filtered by project.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            List[DeploymentResult]: List of deployments
        """
        if project_id:
            return [d for d in self.deployments.values() if d.project_id == project_id]
        else:
            return list(self.deployments.values())
    
    async def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentResult]:
        """
        Get status of a specific deployment.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Optional[DeploymentResult]: Deployment result if found
        """
        return self.deployments.get(deployment_id)
    
    # Private helper methods
    
    async def _find_project_path(self, project_id: str) -> Path:
        """Find the filesystem path for a project."""
        project_path = self.base_projects_path / project_id
        if project_path.exists():
            return project_path
        
        # Search for project in subdirectories
        for item in self.base_projects_path.iterdir():
            if item.is_dir() and item.name.lower() == project_id.lower():
                return item
        
        raise ValueError(f"Project {project_id} not found in {self.base_projects_path}")
    
    async def _get_current_commit(self, project_path: Path) -> Optional[str]:
        """Get current Git commit hash."""
        try:
            result = await self._run_command(
                ["git", "rev-parse", "HEAD"],
                cwd=project_path,
                capture_output=True
            )
            return result.strip() if result else None
        except Exception:
            return None
    
    async def _get_deployment_config(self, project_id: str, target: str, environment: str) -> DeploymentConfig:
        """Get deployment configuration for a project."""
        # Check if config is cached
        config_key = f"{project_id}_{target}_{environment}"
        if config_key in self.deployment_configs:
            return self.deployment_configs[config_key]
        
        # Try to load from project directory
        project_path = await self._find_project_path(project_id)
        config_file = project_path / "optimus-deploy.yml"
        
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config_data = yaml.safe_load(f)
                
                target_config = config_data.get("targets", {}).get(target, {})
                env_config = target_config.get("environments", {}).get(environment, {})
                
                # Merge global and environment-specific config
                merged_config = {**target_config, **env_config}
                
                config = DeploymentConfig(
                    target=DeploymentTarget(target),
                    environment=environment,
                    build_command=merged_config.get("build_command"),
                    test_command=merged_config.get("test_command"),
                    deploy_command=merged_config.get("deploy_command"),
                    health_check_url=merged_config.get("health_check_url"),
                    health_check_timeout=merged_config.get("health_check_timeout", 60),
                    rollback_enabled=merged_config.get("rollback_enabled", True),
                    auto_rollback_on_failure=merged_config.get("auto_rollback_on_failure", True),
                    env_vars=merged_config.get("env_vars", {}),
                    secrets=merged_config.get("secrets", {}),
                    docker_config=merged_config.get("docker_config"),
                    kubernetes_config=merged_config.get("kubernetes_config")
                )
                
                self.deployment_configs[config_key] = config
                return config
                
            except Exception as e:
                logger.warning(f"Failed to load deployment config: {e}")
        
        # Default configuration
        config = await self._create_default_config(project_path, target, environment)
        self.deployment_configs[config_key] = config
        return config
    
    async def _create_default_config(self, project_path: Path, target: str, environment: str) -> DeploymentConfig:
        """Create default deployment configuration based on project type."""
        # Detect project type
        if (project_path / "package.json").exists():
            # Node.js project
            return DeploymentConfig(
                target=DeploymentTarget(target),
                environment=environment,
                build_command="npm run build",
                test_command="npm test",
                deploy_command="npm start",
                health_check_url="http://localhost:3000/health"
            )
        elif (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
            # Python project
            return DeploymentConfig(
                target=DeploymentTarget(target),
                environment=environment,
                build_command="pip install -r requirements.txt",
                test_command="python -m pytest",
                deploy_command="python main.py",
                health_check_url="http://localhost:8000/health"
            )
        elif (project_path / "Dockerfile").exists():
            # Docker project
            return DeploymentConfig(
                target=DeploymentTarget.DOCKER,
                environment=environment,
                build_command="docker build -t app .",
                deploy_command="docker run -d -p 80:80 app",
                health_check_url="http://localhost/health"
            )
        else:
            # Generic configuration
            return DeploymentConfig(
                target=DeploymentTarget(target),
                environment=environment
            )
    
    async def _execute_deployment_pipeline(self, result: DeploymentResult, config: DeploymentConfig, project_path: Path, deployment_dir: Path) -> bool:
        """Execute the deployment pipeline."""
        try:
            # Prepare stage
            result.status = DeploymentStatus.PREPARING
            await self._prepare_deployment(project_path, deployment_dir, config)
            
            # Build stage
            if config.build_command:
                result.status = DeploymentStatus.BUILDING
                success = await self._execute_build(result, config, deployment_dir)
                if not success:
                    return False
            
            # Test stage
            if config.test_command:
                result.status = DeploymentStatus.TESTING
                success = await self._execute_tests(result, config, deployment_dir)
                if not success:
                    return False
            
            # Deploy stage
            result.status = DeploymentStatus.DEPLOYING
            success = await self._execute_deploy(result, config, deployment_dir)
            if not success:
                return False
            
            return True
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Deployment pipeline failed: {e}")
            return False
    
    async def _prepare_deployment(self, project_path: Path, deployment_dir: Path, config: DeploymentConfig):
        """Prepare deployment directory."""
        # Copy project to deployment directory
        source_dir = deployment_dir / "source"
        shutil.copytree(project_path, source_dir, ignore=shutil.ignore_patterns('.git', '__pycache__', 'node_modules', '.env'))
        
        # Create environment file
        env_file = source_dir / ".env"
        with open(env_file, 'w') as f:
            for key, value in config.env_vars.items():
                f.write(f"{key}={value}\n")
            for key, value in config.secrets.items():
                f.write(f"{key}={value}\n")
    
    async def _execute_build(self, result: DeploymentResult, config: DeploymentConfig, deployment_dir: Path) -> bool:
        """Execute build command."""
        try:
            source_dir = deployment_dir / "source"
            
            logger.info(f"Executing build: {config.build_command}")
            output = await self._run_command(
                config.build_command.split(),
                cwd=source_dir,
                capture_output=True
            )
            
            result.build_logs.extend(output.split('\n'))
            return True
            
        except subprocess.CalledProcessError as e:
            result.build_logs.extend(str(e.output).split('\n'))
            result.error_message = f"Build failed: {e}"
            return False
    
    async def _execute_tests(self, result: DeploymentResult, config: DeploymentConfig, deployment_dir: Path) -> bool:
        """Execute test command."""
        try:
            source_dir = deployment_dir / "source"
            
            logger.info(f"Executing tests: {config.test_command}")
            output = await self._run_command(
                config.test_command.split(),
                cwd=source_dir,
                capture_output=True
            )
            
            result.deploy_logs.extend(output.split('\n'))
            return True
            
        except subprocess.CalledProcessError as e:
            result.deploy_logs.extend(str(e.output).split('\n'))
            result.error_message = f"Tests failed: {e}"
            return False
    
    async def _execute_deploy(self, result: DeploymentResult, config: DeploymentConfig, deployment_dir: Path) -> bool:
        """Execute deployment command."""
        try:
            source_dir = deployment_dir / "source"
            
            if config.target == DeploymentTarget.DOCKER:
                return await self._deploy_docker(result, config, source_dir)
            elif config.target == DeploymentTarget.LOCAL:
                return await self._deploy_local(result, config, source_dir)
            else:
                # Generic deployment
                if config.deploy_command:
                    logger.info(f"Executing deploy: {config.deploy_command}")
                    output = await self._run_command(
                        config.deploy_command.split(),
                        cwd=source_dir,
                        capture_output=True
                    )
                    result.deploy_logs.extend(output.split('\n'))
                
                return True
                
        except Exception as e:
            result.error_message = f"Deploy failed: {e}"
            return False
    
    async def _deploy_docker(self, result: DeploymentResult, config: DeploymentConfig, source_dir: Path) -> bool:
        """Deploy using Docker."""
        try:
            image_tag = f"{result.project_id}:{result.deployment_id}"
            
            # Build Docker image
            logger.info(f"Building Docker image: {image_tag}")
            build_output = await self._run_command(
                ["docker", "build", "-t", image_tag, "."],
                cwd=source_dir,
                capture_output=True
            )
            result.build_logs.extend(build_output.split('\n'))
            
            # Run container
            logger.info(f"Running Docker container: {image_tag}")
            container_name = f"{result.project_id}_{result.deployment_id}"
            
            docker_args = ["docker", "run", "-d", "--name", container_name]
            
            # Add port mappings
            if config.docker_config and "ports" in config.docker_config:
                for port_mapping in config.docker_config["ports"]:
                    docker_args.extend(["-p", port_mapping])
            else:
                docker_args.extend(["-p", "80:80"])  # Default port mapping
            
            # Add environment variables
            for key, value in {**config.env_vars, **config.secrets}.items():
                docker_args.extend(["-e", f"{key}={value}"])
            
            docker_args.append(image_tag)
            
            run_output = await self._run_command(docker_args, capture_output=True)
            result.deploy_logs.extend(run_output.split('\n'))
            
            # Store container ID
            container_id = run_output.strip()
            result.artifacts["container_id"] = container_id
            result.artifacts["image_tag"] = image_tag
            
            return True
            
        except Exception as e:
            logger.error(f"Docker deployment failed: {e}")
            return False
    
    async def _deploy_local(self, result: DeploymentResult, config: DeploymentConfig, source_dir: Path) -> bool:
        """Deploy locally."""
        try:
            if config.deploy_command:
                # Start the application in the background
                logger.info(f"Starting local deployment: {config.deploy_command}")
                
                # Create a script to run the command
                script_path = source_dir / "run_deployment.sh"
                with open(script_path, 'w') as f:
                    f.write("#!/bin/bash\n")
                    f.write(f"cd {source_dir}\n")
                    f.write(f"{config.deploy_command}\n")
                
                script_path.chmod(0o755)
                
                # Run the script in the background
                process = subprocess.Popen(
                    [str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                result.artifacts["process_id"] = str(process.pid)
                result.artifacts["script_path"] = str(script_path)
                
            return True
            
        except Exception as e:
            logger.error(f"Local deployment failed: {e}")
            return False
    
    async def _perform_health_check(self, config: DeploymentConfig) -> HealthStatus:
        """Perform health check on deployment."""
        if not config.health_check_url:
            return HealthStatus.UNKNOWN
        
        health_check = HealthCheck(url=config.health_check_url, timeout=config.health_check_timeout)
        result = await self._execute_health_check(health_check)
        return result.status
    
    async def _execute_health_check(self, health_check: HealthCheck) -> HealthCheck:
        """Execute a single health check."""
        try:
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    health_check.method,
                    health_check.url,
                    headers=health_check.headers,
                    data=health_check.body,
                    timeout=aiohttp.ClientTimeout(total=health_check.timeout)
                ) as response:
                    end_time = datetime.now()
                    health_check.response_time_ms = (end_time - start_time).total_seconds() * 1000
                    health_check.response_text = await response.text()
                    health_check.checked_at = end_time
                    
                    if response.status == health_check.expected_status:
                        health_check.status = HealthStatus.HEALTHY
                    else:
                        health_check.status = HealthStatus.UNHEALTHY
                        health_check.error_message = f"Expected status {health_check.expected_status}, got {response.status}"
            
        except asyncio.TimeoutError:
            health_check.status = HealthStatus.UNHEALTHY
            health_check.error_message = "Health check timeout"
            health_check.checked_at = datetime.now()
        except Exception as e:
            health_check.status = HealthStatus.UNHEALTHY
            health_check.error_message = str(e)
            health_check.checked_at = datetime.now()
        
        return health_check
    
    async def _get_additional_health_checks(self, deployment: DeploymentResult) -> List[HealthCheck]:
        """Get additional health checks based on deployment target."""
        checks = []
        
        # Add basic connectivity check
        if deployment.target == DeploymentTarget.DOCKER and "container_id" in deployment.artifacts:
            # Check if container is running
            # This would require Docker API integration
            pass
        
        return checks
    
    async def _find_previous_deployment(self, project_id: str, current_deployment_id: str) -> Optional[DeploymentResult]:
        """Find the most recent successful deployment for rollback."""
        project_deployments = [
            d for d in self.deployments.values()
            if d.project_id == project_id and d.deployment_id != current_deployment_id
            and d.status == DeploymentStatus.SUCCESS
        ]
        
        if not project_deployments:
            return None
        
        # Return most recent successful deployment
        return max(project_deployments, key=lambda d: d.started_at)
    
    async def _execute_rollback(self, current: DeploymentResult, previous: DeploymentResult, rollback: DeploymentResult) -> bool:
        """Execute rollback to previous deployment."""
        try:
            if current.target == DeploymentTarget.DOCKER:
                return await self._rollback_docker(current, previous, rollback)
            elif current.target == DeploymentTarget.LOCAL:
                return await self._rollback_local(current, previous, rollback)
            else:
                # Generic rollback - redeploy previous version
                project_path = await self._find_project_path(current.project_id)
                
                # Checkout previous commit
                if previous.commit_hash:
                    await self._run_command(
                        ["git", "checkout", previous.commit_hash],
                        cwd=project_path
                    )
                
                # Redeploy
                config = await self._get_deployment_config(current.project_id, current.target.value, current.environment)
                deployment_dir = self.deployments_dir / rollback.deployment_id
                deployment_dir.mkdir(exist_ok=True)
                
                return await self._execute_deployment_pipeline(rollback, config, project_path, deployment_dir)
                
        except Exception as e:
            rollback.error_message = f"Rollback failed: {e}"
            logger.error(f"Rollback execution failed: {e}")
            return False
    
    async def _rollback_docker(self, current: DeploymentResult, previous: DeploymentResult, rollback: DeploymentResult) -> bool:
        """Rollback Docker deployment."""
        try:
            # Stop current container
            if "container_id" in current.artifacts:
                await self._run_command(["docker", "stop", current.artifacts["container_id"]])
                await self._run_command(["docker", "rm", current.artifacts["container_id"]])
            
            # Start previous container if available
            if "image_tag" in previous.artifacts:
                # Run previous image
                container_name = f"{current.project_id}_{rollback.deployment_id}"
                run_output = await self._run_command([
                    "docker", "run", "-d", "--name", container_name,
                    "-p", "80:80", previous.artifacts["image_tag"]
                ], capture_output=True)
                
                rollback.artifacts["container_id"] = run_output.strip()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Docker rollback failed: {e}")
            return False
    
    async def _rollback_local(self, current: DeploymentResult, previous: DeploymentResult, rollback: DeploymentResult) -> bool:
        """Rollback local deployment."""
        try:
            # Stop current process
            if "process_id" in current.artifacts:
                try:
                    import psutil
                    process = psutil.Process(int(current.artifacts["process_id"]))
                    process.terminate()
                except:
                    pass
            
            # Start previous version
            # This would require more sophisticated process management
            return True
            
        except Exception as e:
            logger.error(f"Local rollback failed: {e}")
            return False
    
    async def _auto_rollback(self, deployment: DeploymentResult):
        """Automatically rollback a failed deployment."""
        try:
            await self.rollback(deployment.deployment_id)
        except Exception as e:
            logger.error(f"Auto-rollback failed for {deployment.deployment_id}: {e}")
    
    async def _switch_traffic(self, bg_deployment: Deployment, target_instance: str):
        """Switch traffic to target instance in blue-green deployment."""
        # This would integrate with load balancer/proxy configuration
        # For now, just update the traffic split
        if target_instance == "blue":
            bg_deployment.traffic_split = {"blue": 100, "green": 0}
        else:
            bg_deployment.traffic_split = {"blue": 0, "green": 100}
        
        logger.info(f"Switched traffic to {target_instance} instance")
    
    async def _save_pipeline_config(self, pipeline: Pipeline):
        """Save pipeline configuration to file."""
        config_dir = Path("config/pipelines")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / f"{pipeline.project_id}_{pipeline.name}.yml"
        
        with open(config_file, 'w') as f:
            yaml.dump(pipeline.to_dict(), f, default_flow_style=False)
    
    async def _run_command(self, command: List[str], cwd: Optional[Path] = None, capture_output: bool = False) -> Optional[str]:
        """Run a shell command asynchronously."""
        try:
            if capture_output:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout
            else:
                subprocess.run(command, cwd=cwd, check=True)
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}")
            raise