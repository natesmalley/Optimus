"""
Resource Allocator Service

Manages resource allocation, monitoring, and optimization for projects including
CPU limits, memory constraints, and dynamic resource adjustment based on usage patterns.
"""

import asyncio
import psutil
import logging
import json
import signal
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources that can be managed."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESSES = "processes"
    FILE_DESCRIPTORS = "file_descriptors"


class ResourcePriority(Enum):
    """Priority levels for resource allocation."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class ResourceLimits:
    """Resource limits configuration."""
    cpu_percent: Optional[float] = None  # Max CPU percentage
    cpu_cores: Optional[int] = None      # Max CPU cores
    memory_mb: Optional[int] = None      # Max memory in MB
    memory_percent: Optional[float] = None  # Max memory percentage
    disk_read_mb_s: Optional[float] = None  # Max disk read MB/s
    disk_write_mb_s: Optional[float] = None  # Max disk write MB/s
    network_upload_kb_s: Optional[float] = None  # Max network upload KB/s
    network_download_kb_s: Optional[float] = None  # Max network download KB/s
    max_processes: Optional[int] = None  # Max number of processes
    max_file_descriptors: Optional[int] = None  # Max open file descriptors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "cpu_percent": self.cpu_percent,
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "disk_read_mb_s": self.disk_read_mb_s,
            "disk_write_mb_s": self.disk_write_mb_s,
            "network_upload_kb_s": self.network_upload_kb_s,
            "network_download_kb_s": self.network_download_kb_s,
            "max_processes": self.max_processes,
            "max_file_descriptors": self.max_file_descriptors
        }


@dataclass
class ResourceMetrics:
    """Current resource usage metrics."""
    project_id: str
    timestamp: datetime
    cpu_percent: float
    cpu_cores_used: float
    memory_mb: float
    memory_percent: float
    disk_read_mb_s: float = 0.0
    disk_write_mb_s: float = 0.0
    network_upload_kb_s: float = 0.0
    network_download_kb_s: float = 0.0
    process_count: int = 0
    file_descriptors: int = 0
    load_average: Optional[Tuple[float, float, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "project_id": self.project_id,
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "cpu_cores_used": self.cpu_cores_used,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "disk_read_mb_s": self.disk_read_mb_s,
            "disk_write_mb_s": self.disk_write_mb_s,
            "network_upload_kb_s": self.network_upload_kb_s,
            "network_download_kb_s": self.network_download_kb_s,
            "process_count": self.process_count,
            "file_descriptors": self.file_descriptors,
            "load_average": self.load_average
        }


@dataclass
class ResourceRequirements:
    """Resource requirements for a project."""
    min_cpu_percent: float = 5.0
    max_cpu_percent: float = 80.0
    min_memory_mb: int = 64
    max_memory_mb: int = 2048
    priority: ResourcePriority = ResourcePriority.NORMAL
    auto_scale: bool = True
    scale_threshold_cpu: float = 70.0
    scale_threshold_memory: float = 80.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "min_cpu_percent": self.min_cpu_percent,
            "max_cpu_percent": self.max_cpu_percent,
            "min_memory_mb": self.min_memory_mb,
            "max_memory_mb": self.max_memory_mb,
            "priority": self.priority.value,
            "auto_scale": self.auto_scale,
            "scale_threshold_cpu": self.scale_threshold_cpu,
            "scale_threshold_memory": self.scale_threshold_memory
        }


@dataclass
class Allocation:
    """Resource allocation result."""
    project_id: str
    limits: ResourceLimits
    allocated_at: datetime
    enforced: bool = False
    enforcement_method: Optional[str] = None  # 'cgroups', 'docker', 'process_limits'
    cgroup_path: Optional[str] = None
    container_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "project_id": self.project_id,
            "limits": self.limits.to_dict(),
            "allocated_at": self.allocated_at.isoformat(),
            "enforced": self.enforced,
            "enforcement_method": self.enforcement_method,
            "cgroup_path": self.cgroup_path,
            "container_id": self.container_id
        }


@dataclass
class UsagePrediction:
    """Resource usage prediction."""
    project_id: str
    prediction_horizon: timedelta
    predicted_cpu_percent: float
    predicted_memory_mb: float
    confidence: float
    recommended_limits: ResourceLimits
    reasoning: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "project_id": self.project_id,
            "prediction_horizon": str(self.prediction_horizon),
            "predicted_cpu_percent": self.predicted_cpu_percent,
            "predicted_memory_mb": self.predicted_memory_mb,
            "confidence": self.confidence,
            "recommended_limits": self.recommended_limits.to_dict(),
            "reasoning": self.reasoning
        }


@dataclass
class OptimizationPlan:
    """Resource optimization plan for multiple projects."""
    projects: List[str]
    total_cpu_saved: float
    total_memory_saved: float
    recommendations: List[Dict[str, Any]]
    estimated_savings: Dict[str, float]
    implementation_priority: List[str]  # Project IDs in order of implementation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "projects": self.projects,
            "total_cpu_saved": self.total_cpu_saved,
            "total_memory_saved": self.total_memory_saved,
            "recommendations": self.recommendations,
            "estimated_savings": self.estimated_savings,
            "implementation_priority": self.implementation_priority
        }


class ResourceAllocator:
    """
    Manages resource allocation, monitoring, and optimization for projects.
    
    Provides CPU and memory limits using cgroups/Docker, dynamic resource adjustment,
    priority-based allocation, usage predictions, and optimization recommendations.
    """
    
    def __init__(self, base_projects_path: str = "/Users/nathanial.smalley/projects"):
        """
        Initialize the ResourceAllocator.
        
        Args:
            base_projects_path: Base directory containing all projects
        """
        self.base_projects_path = Path(base_projects_path)
        self.allocations: Dict[str, Allocation] = {}
        self.metrics_history: Dict[str, List[ResourceMetrics]] = {}
        self.requirements: Dict[str, ResourceRequirements] = {}
        
        # System information
        self.total_cpu_cores = psutil.cpu_count()
        self.total_memory_mb = psutil.virtual_memory().total // (1024 * 1024)
        
        # Monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.history_retention_days = 30
        self.alert_thresholds = {
            "cpu_critical": 90.0,
            "memory_critical": 95.0,
            "disk_critical": 90.0
        }
        
        # Resource enforcement
        self.cgroups_enabled = self._check_cgroups_support()
        self.docker_enabled = self._check_docker_support()
        
        logger.info(f"ResourceAllocator initialized - CPU cores: {self.total_cpu_cores}, Memory: {self.total_memory_mb}MB")
        logger.info(f"Resource enforcement - CGroups: {self.cgroups_enabled}, Docker: {self.docker_enabled}")
    
    async def allocate_resources(self, project_id: str, requirements: ResourceRequirements) -> Allocation:
        """
        Allocate resources for a project based on requirements.
        
        Args:
            project_id: Project identifier
            requirements: Resource requirements specification
            
        Returns:
            Allocation: Resource allocation details
        """
        logger.info(f"Allocating resources for project {project_id}")
        
        try:
            # Store requirements
            self.requirements[project_id] = requirements
            
            # Calculate resource limits based on requirements and system capacity
            limits = await self._calculate_resource_limits(project_id, requirements)
            
            # Create allocation
            allocation = Allocation(
                project_id=project_id,
                limits=limits,
                allocated_at=datetime.now()
            )
            
            # Apply resource limits
            success = await self._apply_resource_limits(allocation)
            allocation.enforced = success
            
            # Store allocation
            self.allocations[project_id] = allocation
            
            # Start monitoring if not already running
            if project_id not in self.metrics_history:
                self.metrics_history[project_id] = []
                asyncio.create_task(self._monitor_project_resources(project_id))
            
            logger.info(f"Successfully allocated resources for {project_id} - enforced: {success}")
            return allocation
            
        except Exception as e:
            logger.error(f"Failed to allocate resources for {project_id}: {str(e)}")
            raise
    
    async def monitor_usage(self, project_id: str) -> ResourceMetrics:
        """
        Get current resource usage metrics for a project.
        
        Args:
            project_id: Project to monitor
            
        Returns:
            ResourceMetrics: Current usage metrics
        """
        logger.debug(f"Monitoring resource usage for project {project_id}")
        
        try:
            # Find project processes
            processes = await self._find_project_processes(project_id)
            
            if not processes:
                logger.warning(f"No processes found for project {project_id}")
                return ResourceMetrics(
                    project_id=project_id,
                    timestamp=datetime.now(),
                    cpu_percent=0.0,
                    cpu_cores_used=0.0,
                    memory_mb=0.0,
                    memory_percent=0.0
                )
            
            # Aggregate metrics across all processes
            total_cpu = sum(p.cpu_percent() for p in processes)
            total_memory = sum(p.memory_info().rss for p in processes)
            total_memory_mb = total_memory / (1024 * 1024)
            memory_percent = (total_memory / psutil.virtual_memory().total) * 100
            
            # Get I/O metrics
            disk_read = disk_write = 0.0
            network_sent = network_recv = 0.0
            file_descriptors = 0
            
            for process in processes:
                try:
                    # Disk I/O
                    io_counters = process.io_counters()
                    disk_read += io_counters.read_bytes
                    disk_write += io_counters.write_bytes
                    
                    # Network I/O (if available)
                    try:
                        net_connections = process.connections()
                        # This is a simplified approach - actual network monitoring
                        # would require more sophisticated tracking
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
                    
                    # File descriptors
                    file_descriptors += process.num_fds() if hasattr(process, 'num_fds') else 0
                    
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
            
            # Create metrics object
            metrics = ResourceMetrics(
                project_id=project_id,
                timestamp=datetime.now(),
                cpu_percent=total_cpu,
                cpu_cores_used=total_cpu / 100.0 * self.total_cpu_cores,
                memory_mb=total_memory_mb,
                memory_percent=memory_percent,
                disk_read_mb_s=disk_read / (1024 * 1024),  # Simplified - would need time delta
                disk_write_mb_s=disk_write / (1024 * 1024),
                process_count=len(processes),
                file_descriptors=file_descriptors,
                load_average=psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            )
            
            # Store in history
            if project_id not in self.metrics_history:
                self.metrics_history[project_id] = []
            
            self.metrics_history[project_id].append(metrics)
            
            # Cleanup old metrics
            await self._cleanup_old_metrics(project_id)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to monitor usage for {project_id}: {str(e)}")
            raise
    
    async def optimize_allocation(self, projects: List[str]) -> OptimizationPlan:
        """
        Optimize resource allocation across multiple projects.
        
        Args:
            projects: List of project IDs to optimize
            
        Returns:
            OptimizationPlan: Optimization recommendations
        """
        logger.info(f"Optimizing resource allocation for {len(projects)} projects")
        
        try:
            recommendations = []
            total_cpu_saved = 0.0
            total_memory_saved = 0.0
            
            # Analyze each project
            for project_id in projects:
                if project_id not in self.metrics_history or not self.metrics_history[project_id]:
                    continue
                
                # Get historical usage
                recent_metrics = self.metrics_history[project_id][-100:]  # Last 100 measurements
                
                if not recent_metrics:
                    continue
                
                # Calculate usage statistics
                avg_cpu = statistics.mean(m.cpu_percent for m in recent_metrics)
                max_cpu = max(m.cpu_percent for m in recent_metrics)
                avg_memory = statistics.mean(m.memory_mb for m in recent_metrics)
                max_memory = max(m.memory_mb for m in recent_metrics)
                
                # Get current allocation
                current_allocation = self.allocations.get(project_id)
                
                if not current_allocation:
                    continue
                
                # Optimization recommendations
                project_recommendations = []
                cpu_savings = 0.0
                memory_savings = 0.0
                
                # CPU optimization
                if current_allocation.limits.cpu_percent:
                    target_cpu = max(avg_cpu * 1.2, max_cpu * 1.1, 5.0)  # 20% buffer over average
                    if target_cpu < current_allocation.limits.cpu_percent * 0.8:
                        cpu_savings = current_allocation.limits.cpu_percent - target_cpu
                        project_recommendations.append({
                            "type": "cpu_reduction",
                            "current": current_allocation.limits.cpu_percent,
                            "recommended": target_cpu,
                            "savings": cpu_savings,
                            "reason": f"Average CPU usage ({avg_cpu:.1f}%) well below limit"
                        })
                
                # Memory optimization
                if current_allocation.limits.memory_mb:
                    target_memory = max(avg_memory * 1.3, max_memory * 1.1, 64)  # 30% buffer over average
                    if target_memory < current_allocation.limits.memory_mb * 0.8:
                        memory_savings = current_allocation.limits.memory_mb - target_memory
                        project_recommendations.append({
                            "type": "memory_reduction",
                            "current": current_allocation.limits.memory_mb,
                            "recommended": target_memory,
                            "savings": memory_savings,
                            "reason": f"Average memory usage ({avg_memory:.1f}MB) well below limit"
                        })
                
                # Check for underutilized resources
                if avg_cpu < 10.0 and current_allocation.limits.cpu_percent and current_allocation.limits.cpu_percent > 20.0:
                    project_recommendations.append({
                        "type": "priority_reduction",
                        "reason": "Very low CPU usage suggests project could run at lower priority",
                        "action": "Consider reducing resource priority"
                    })
                
                # Check for resource pressure
                if max_cpu > (current_allocation.limits.cpu_percent or 100) * 0.95:
                    project_recommendations.append({
                        "type": "cpu_increase",
                        "reason": "CPU usage approaching limit, may need more resources",
                        "action": "Consider increasing CPU allocation"
                    })
                
                if project_recommendations:
                    recommendations.append({
                        "project_id": project_id,
                        "recommendations": project_recommendations,
                        "potential_cpu_savings": cpu_savings,
                        "potential_memory_savings": memory_savings
                    })
                    
                    total_cpu_saved += cpu_savings
                    total_memory_saved += memory_savings
            
            # Calculate implementation priority based on savings potential
            implementation_priority = sorted(
                [r["project_id"] for r in recommendations],
                key=lambda pid: next(
                    r["potential_cpu_savings"] + r["potential_memory_savings"] / 100
                    for r in recommendations if r["project_id"] == pid
                ),
                reverse=True
            )
            
            # Estimate cost savings (simplified)
            estimated_savings = {
                "cpu_hours_saved_daily": total_cpu_saved * 24,
                "memory_gb_saved": total_memory_saved / 1024,
                "estimated_cost_savings_monthly": (total_cpu_saved * 0.05 + total_memory_saved / 1024 * 0.02) * 24 * 30
            }
            
            optimization_plan = OptimizationPlan(
                projects=projects,
                total_cpu_saved=total_cpu_saved,
                total_memory_saved=total_memory_saved,
                recommendations=recommendations,
                estimated_savings=estimated_savings,
                implementation_priority=implementation_priority
            )
            
            logger.info(f"Optimization complete - CPU saved: {total_cpu_saved:.1f}%, Memory saved: {total_memory_saved:.1f}MB")
            return optimization_plan
            
        except Exception as e:
            logger.error(f"Failed to optimize allocation: {str(e)}")
            raise
    
    async def set_limits(self, project_id: str, limits: ResourceLimits) -> bool:
        """
        Set resource limits for a project.
        
        Args:
            project_id: Project identifier
            limits: Resource limits to apply
            
        Returns:
            bool: True if successfully set
        """
        logger.info(f"Setting resource limits for project {project_id}")
        
        try:
            # Create or update allocation
            if project_id in self.allocations:
                allocation = self.allocations[project_id]
                allocation.limits = limits
                allocation.allocated_at = datetime.now()
            else:
                allocation = Allocation(
                    project_id=project_id,
                    limits=limits,
                    allocated_at=datetime.now()
                )
            
            # Apply limits
            success = await self._apply_resource_limits(allocation)
            allocation.enforced = success
            
            # Store allocation
            self.allocations[project_id] = allocation
            
            logger.info(f"Successfully set limits for {project_id} - enforced: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to set limits for {project_id}: {str(e)}")
            return False
    
    async def predict_usage(self, project_id: str, horizon: timedelta = timedelta(hours=1)) -> UsagePrediction:
        """
        Predict future resource usage for a project.
        
        Args:
            project_id: Project to predict usage for
            horizon: Prediction time horizon
            
        Returns:
            UsagePrediction: Usage prediction
        """
        logger.info(f"Predicting resource usage for {project_id} over {horizon}")
        
        try:
            if project_id not in self.metrics_history or not self.metrics_history[project_id]:
                raise ValueError(f"No historical data available for project {project_id}")
            
            # Get recent metrics for analysis
            recent_metrics = self.metrics_history[project_id][-200:]  # Last 200 measurements
            
            if len(recent_metrics) < 10:
                raise ValueError(f"Insufficient historical data for prediction (need at least 10 measurements, have {len(recent_metrics)})")
            
            # Simple trend analysis (in production, would use more sophisticated ML models)
            reasoning = []
            
            # CPU prediction
            cpu_values = [m.cpu_percent for m in recent_metrics[-50:]]  # Last 50 measurements
            cpu_trend = self._calculate_trend(cpu_values)
            avg_cpu = statistics.mean(cpu_values)
            
            # Apply trend to predict future usage
            predicted_cpu = max(0, avg_cpu + cpu_trend * (horizon.total_seconds() / 3600))  # Extrapolate per hour
            
            # Memory prediction
            memory_values = [m.memory_mb for m in recent_metrics[-50:]]
            memory_trend = self._calculate_trend(memory_values)
            avg_memory = statistics.mean(memory_values)
            
            predicted_memory = max(0, avg_memory + memory_trend * (horizon.total_seconds() / 3600))
            
            # Calculate confidence based on data consistency
            cpu_variance = statistics.variance(cpu_values) if len(cpu_values) > 1 else 0
            memory_variance = statistics.variance(memory_values) if len(memory_values) > 1 else 0
            
            # Lower variance = higher confidence
            confidence = max(0.3, min(0.95, 1.0 - (cpu_variance / 1000 + memory_variance / 10000)))
            
            # Generate reasoning
            if cpu_trend > 1:
                reasoning.append(f"CPU usage trending upward (+{cpu_trend:.1f}%/hour)")
            elif cpu_trend < -1:
                reasoning.append(f"CPU usage trending downward ({cpu_trend:.1f}%/hour)")
            else:
                reasoning.append("CPU usage is stable")
            
            if memory_trend > 10:
                reasoning.append(f"Memory usage trending upward (+{memory_trend:.1f}MB/hour)")
            elif memory_trend < -10:
                reasoning.append(f"Memory usage trending downward ({memory_trend:.1f}MB/hour)")
            else:
                reasoning.append("Memory usage is stable")
            
            reasoning.append(f"Prediction confidence: {confidence:.0%}")
            
            # Recommend resource limits based on prediction
            recommended_limits = ResourceLimits(
                cpu_percent=max(20, predicted_cpu * 1.5),  # 50% buffer
                memory_mb=int(max(128, predicted_memory * 1.4))  # 40% buffer
            )
            
            prediction = UsagePrediction(
                project_id=project_id,
                prediction_horizon=horizon,
                predicted_cpu_percent=predicted_cpu,
                predicted_memory_mb=predicted_memory,
                confidence=confidence,
                recommended_limits=recommended_limits,
                reasoning=reasoning
            )
            
            logger.info(f"Prediction complete for {project_id}: CPU={predicted_cpu:.1f}%, Memory={predicted_memory:.1f}MB")
            return prediction
            
        except Exception as e:
            logger.error(f"Failed to predict usage for {project_id}: {str(e)}")
            raise
    
    async def get_system_resources(self) -> Dict[str, Any]:
        """
        Get current system resource information.
        
        Returns:
            Dict[str, Any]: System resource data
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "count": self.total_cpu_cores,
                "usage_percent": cpu_percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            },
            "memory": {
                "total_mb": self.total_memory_mb,
                "available_mb": memory.available // (1024 * 1024),
                "used_mb": memory.used // (1024 * 1024),
                "usage_percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total // (1024 * 1024 * 1024),
                "free_gb": disk.free // (1024 * 1024 * 1024),
                "used_gb": disk.used // (1024 * 1024 * 1024),
                "usage_percent": (disk.used / disk.total) * 100
            }
        }
    
    # Private helper methods
    
    async def _find_project_processes(self, project_id: str) -> List[psutil.Process]:
        """Find all processes related to a project."""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
                try:
                    # Check if process is related to project
                    if self._is_project_process(proc, project_id):
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning(f"Error finding processes for {project_id}: {e}")
        
        return processes
    
    def _is_project_process(self, process: psutil.Process, project_id: str) -> bool:
        """Check if a process belongs to a project."""
        try:
            # Check command line arguments
            cmdline = process.info.get('cmdline', [])
            if cmdline and any(project_id in arg for arg in cmdline):
                return True
            
            # Check working directory
            cwd = process.info.get('cwd')
            if cwd and project_id in cwd:
                return True
            
            # Check process name
            name = process.info.get('name', '')
            if project_id in name:
                return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            pass
        
        return False
    
    async def _calculate_resource_limits(self, project_id: str, requirements: ResourceRequirements) -> ResourceLimits:
        """Calculate appropriate resource limits based on requirements."""
        # Get current system load
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        # Calculate available resources
        available_cpu = max(10, 100 - cpu_percent)
        available_memory = max(256, self.total_memory_mb * (100 - memory_percent) / 100)
        
        # Apply requirements within available resources
        cpu_limit = min(requirements.max_cpu_percent, available_cpu * 0.8)  # Reserve 20%
        memory_limit = min(requirements.max_memory_mb, available_memory * 0.8)  # Reserve 20%
        
        # Priority adjustments
        priority_multipliers = {
            ResourcePriority.CRITICAL: 1.0,
            ResourcePriority.HIGH: 0.8,
            ResourcePriority.NORMAL: 0.6,
            ResourcePriority.LOW: 0.4,
            ResourcePriority.BACKGROUND: 0.2
        }
        
        multiplier = priority_multipliers.get(requirements.priority, 0.6)
        cpu_limit *= multiplier
        memory_limit *= multiplier
        
        return ResourceLimits(
            cpu_percent=max(requirements.min_cpu_percent, cpu_limit),
            memory_mb=max(requirements.min_memory_mb, int(memory_limit)),
            max_processes=50,  # Default process limit
            max_file_descriptors=1024  # Default file descriptor limit
        )
    
    async def _apply_resource_limits(self, allocation: Allocation) -> bool:
        """Apply resource limits using available enforcement mechanisms."""
        try:
            # Try Docker first if available
            if self.docker_enabled:
                success = await self._apply_docker_limits(allocation)
                if success:
                    allocation.enforcement_method = "docker"
                    return True
            
            # Try cgroups if available
            if self.cgroups_enabled:
                success = await self._apply_cgroups_limits(allocation)
                if success:
                    allocation.enforcement_method = "cgroups"
                    return True
            
            # Fallback to process-level limits (limited effectiveness)
            success = await self._apply_process_limits(allocation)
            if success:
                allocation.enforcement_method = "process_limits"
                return True
            
            logger.warning(f"Could not apply resource limits for {allocation.project_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to apply resource limits: {e}")
            return False
    
    async def _apply_docker_limits(self, allocation: Allocation) -> bool:
        """Apply resource limits using Docker."""
        try:
            # This would require integration with Docker API
            # For now, return False as Docker integration is not implemented
            logger.debug("Docker resource limits not implemented")
            return False
        except Exception as e:
            logger.error(f"Docker limits error: {e}")
            return False
    
    async def _apply_cgroups_limits(self, allocation: Allocation) -> bool:
        """Apply resource limits using cgroups."""
        try:
            if not self.cgroups_enabled:
                return False
            
            # Create cgroup for project
            cgroup_name = f"optimus-{allocation.project_id}"
            cgroup_path = f"/sys/fs/cgroup/optimus/{cgroup_name}"
            
            # This is a simplified implementation
            # In production, would need proper cgroup management
            logger.debug("CGroups resource limits not fully implemented")
            return False
            
        except Exception as e:
            logger.error(f"CGroups limits error: {e}")
            return False
    
    async def _apply_process_limits(self, allocation: Allocation) -> bool:
        """Apply resource limits at process level (limited effectiveness)."""
        try:
            # Find project processes
            processes = await self._find_project_processes(allocation.project_id)
            
            for process in processes:
                try:
                    # Set CPU affinity (if supported)
                    if hasattr(process, 'cpu_affinity') and allocation.limits.cpu_cores:
                        available_cpus = list(range(min(allocation.limits.cpu_cores, self.total_cpu_cores)))
                        process.cpu_affinity(available_cpus)
                    
                    # Set process priority based on resource allocation
                    if hasattr(process, 'nice'):
                        if allocation.limits.cpu_percent and allocation.limits.cpu_percent < 20:
                            process.nice(10)  # Lower priority
                        elif allocation.limits.cpu_percent and allocation.limits.cpu_percent > 60:
                            process.nice(-5)  # Higher priority
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            logger.info(f"Applied process-level limits to {len(processes)} processes")
            return True
            
        except Exception as e:
            logger.error(f"Process limits error: {e}")
            return False
    
    def _check_cgroups_support(self) -> bool:
        """Check if cgroups are available on the system."""
        try:
            return Path("/sys/fs/cgroup").exists()
        except:
            return False
    
    def _check_docker_support(self) -> bool:
        """Check if Docker is available on the system."""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple linear trend from a series of values."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    async def _monitor_project_resources(self, project_id: str):
        """Background task to continuously monitor project resources."""
        while project_id in self.allocations:
            try:
                # Monitor usage
                await self.monitor_usage(project_id)
                
                # Check for alerts
                await self._check_resource_alerts(project_id)
                
                # Auto-scale if enabled
                if project_id in self.requirements and self.requirements[project_id].auto_scale:
                    await self._auto_scale_resources(project_id)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring resources for {project_id}: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _check_resource_alerts(self, project_id: str):
        """Check if any resource usage exceeds alert thresholds."""
        if project_id not in self.metrics_history or not self.metrics_history[project_id]:
            return
        
        latest_metrics = self.metrics_history[project_id][-1]
        
        # Check CPU alert
        if latest_metrics.cpu_percent > self.alert_thresholds["cpu_critical"]:
            logger.warning(f"CRITICAL: Project {project_id} CPU usage at {latest_metrics.cpu_percent:.1f}%")
        
        # Check memory alert
        if latest_metrics.memory_percent > self.alert_thresholds["memory_critical"]:
            logger.warning(f"CRITICAL: Project {project_id} memory usage at {latest_metrics.memory_percent:.1f}%")
    
    async def _auto_scale_resources(self, project_id: str):
        """Auto-scale resources based on usage patterns."""
        if project_id not in self.requirements or project_id not in self.allocations:
            return
        
        requirements = self.requirements[project_id]
        allocation = self.allocations[project_id]
        
        if not self.metrics_history[project_id]:
            return
        
        # Get recent usage
        recent_metrics = self.metrics_history[project_id][-10:]  # Last 10 measurements
        avg_cpu = statistics.mean(m.cpu_percent for m in recent_metrics)
        avg_memory = statistics.mean(m.memory_mb for m in recent_metrics)
        
        # Check if scaling is needed
        scale_needed = False
        new_limits = ResourceLimits(
            cpu_percent=allocation.limits.cpu_percent,
            memory_mb=allocation.limits.memory_mb
        )
        
        # Scale up if consistently hitting thresholds
        if avg_cpu > requirements.scale_threshold_cpu and allocation.limits.cpu_percent:
            new_cpu = min(requirements.max_cpu_percent, allocation.limits.cpu_percent * 1.2)
            if new_cpu > allocation.limits.cpu_percent:
                new_limits.cpu_percent = new_cpu
                scale_needed = True
                logger.info(f"Auto-scaling CPU up for {project_id}: {allocation.limits.cpu_percent} -> {new_cpu}")
        
        if avg_memory > allocation.limits.memory_mb * (requirements.scale_threshold_memory / 100):
            new_memory = min(requirements.max_memory_mb, int(allocation.limits.memory_mb * 1.2))
            if new_memory > allocation.limits.memory_mb:
                new_limits.memory_mb = new_memory
                scale_needed = True
                logger.info(f"Auto-scaling memory up for {project_id}: {allocation.limits.memory_mb} -> {new_memory}")
        
        # Scale down if consistently underutilized
        if avg_cpu < requirements.scale_threshold_cpu * 0.3 and allocation.limits.cpu_percent:
            new_cpu = max(requirements.min_cpu_percent, allocation.limits.cpu_percent * 0.9)
            if new_cpu < allocation.limits.cpu_percent:
                new_limits.cpu_percent = new_cpu
                scale_needed = True
                logger.info(f"Auto-scaling CPU down for {project_id}: {allocation.limits.cpu_percent} -> {new_cpu}")
        
        # Apply new limits if scaling is needed
        if scale_needed:
            await self.set_limits(project_id, new_limits)
    
    async def _cleanup_old_metrics(self, project_id: str):
        """Clean up old metrics data to prevent memory bloat."""
        if project_id not in self.metrics_history:
            return
        
        cutoff_time = datetime.now() - timedelta(days=self.history_retention_days)
        
        # Filter out old metrics
        self.metrics_history[project_id] = [
            m for m in self.metrics_history[project_id]
            if m.timestamp > cutoff_time
        ]