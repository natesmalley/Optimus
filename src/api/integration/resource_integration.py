"""
Resource Integration Layer
Connects resource monitoring and management to the API.
"""

import asyncio
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..websocket_manager import websocket_manager, Channel
from ...config import logger


class ResourceMetrics(BaseModel):
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available: int  # bytes
    memory_used: int  # bytes
    disk_percent: float
    disk_free: int  # bytes
    network_io: Dict[str, int]  # bytes_sent, bytes_recv
    process_count: int
    load_average: List[float]
    timestamp: datetime


class ProjectResourceUsage(BaseModel):
    """Project-specific resource usage."""
    project_id: str
    project_name: str
    cpu_percent: float
    memory_mb: float
    disk_usage_mb: float
    network_connections: int
    processes: List[Dict[str, Any]]
    last_updated: datetime


class ResourceAlert(BaseModel):
    """Resource alert/threshold."""
    alert_id: str
    alert_type: str  # cpu, memory, disk, network
    threshold: float
    current_value: float
    severity: str  # low, medium, high, critical
    message: str
    triggered_at: datetime
    project_id: Optional[str] = None


class ResourceIntegration:
    """Integration layer for resource monitoring."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.metrics_history: List[ResourceMetrics] = []
        self.project_usage: Dict[str, ProjectResourceUsage] = {}
        self.active_alerts: Dict[str, ResourceAlert] = {}
        self.alert_history: List[ResourceAlert] = []
        
        # Thresholds
        self.thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 80.0,
            "memory_critical": 95.0,
            "disk_warning": 85.0,
            "disk_critical": 95.0,
            "process_limit": 1000
        }
        
        # Keep metrics for 24 hours
        self.metrics_retention_hours = 24
        
        # Start monitoring
        self._monitoring_task = None
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start resource monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info("Resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while True:
            try:
                # Collect system metrics
                metrics = await self._collect_system_metrics()
                
                # Store metrics
                self.metrics_history.append(metrics)
                
                # Clean old metrics
                cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m.timestamp > cutoff_time
                ]
                
                # Check thresholds and generate alerts
                await self._check_thresholds(metrics)
                
                # Update project-specific usage
                await self._update_project_usage()
                
                # Broadcast resource update
                await self._broadcast_resource_update(metrics)
                
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def _collect_system_metrics(self) -> ResourceMetrics:
        """Collect current system metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage (root partition)
        disk = psutil.disk_usage('/')
        
        # Network I/O
        network = psutil.net_io_counters()
        
        # Process count
        process_count = len(psutil.pids())
        
        # Load average (Unix-like systems)
        try:
            load_avg = list(psutil.getloadavg())
        except (AttributeError, OSError):
            load_avg = [0.0, 0.0, 0.0]
        
        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available=memory.available,
            memory_used=memory.used,
            disk_percent=disk.used / disk.total * 100,
            disk_free=disk.free,
            network_io={
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv
            },
            process_count=process_count,
            load_average=load_avg,
            timestamp=datetime.now()
        )
    
    async def _check_thresholds(self, metrics: ResourceMetrics):
        """Check metrics against thresholds and generate alerts."""
        alerts = []
        
        # CPU alerts
        if metrics.cpu_percent >= self.thresholds["cpu_critical"]:
            alerts.append(self._create_alert(
                "cpu", metrics.cpu_percent, self.thresholds["cpu_critical"],
                "critical", "Critical CPU usage detected"
            ))
        elif metrics.cpu_percent >= self.thresholds["cpu_warning"]:
            alerts.append(self._create_alert(
                "cpu", metrics.cpu_percent, self.thresholds["cpu_warning"],
                "high", "High CPU usage detected"
            ))
        
        # Memory alerts
        if metrics.memory_percent >= self.thresholds["memory_critical"]:
            alerts.append(self._create_alert(
                "memory", metrics.memory_percent, self.thresholds["memory_critical"],
                "critical", "Critical memory usage detected"
            ))
        elif metrics.memory_percent >= self.thresholds["memory_warning"]:
            alerts.append(self._create_alert(
                "memory", metrics.memory_percent, self.thresholds["memory_warning"],
                "high", "High memory usage detected"
            ))
        
        # Disk alerts
        if metrics.disk_percent >= self.thresholds["disk_critical"]:
            alerts.append(self._create_alert(
                "disk", metrics.disk_percent, self.thresholds["disk_critical"],
                "critical", "Critical disk usage detected"
            ))
        elif metrics.disk_percent >= self.thresholds["disk_warning"]:
            alerts.append(self._create_alert(
                "disk", metrics.disk_percent, self.thresholds["disk_warning"],
                "high", "High disk usage detected"
            ))
        
        # Process count alert
        if metrics.process_count >= self.thresholds["process_limit"]:
            alerts.append(self._create_alert(
                "processes", metrics.process_count, self.thresholds["process_limit"],
                "medium", f"High process count: {metrics.process_count}"
            ))
        
        # Process new alerts
        for alert in alerts:
            await self._handle_alert(alert)
    
    def _create_alert(self, alert_type: str, current_value: float, threshold: float,
                     severity: str, message: str, project_id: str = None) -> ResourceAlert:
        """Create a new resource alert."""
        from uuid import uuid4
        
        return ResourceAlert(
            alert_id=str(uuid4()),
            alert_type=alert_type,
            threshold=threshold,
            current_value=current_value,
            severity=severity,
            message=message,
            triggered_at=datetime.now(),
            project_id=project_id
        )
    
    async def _handle_alert(self, alert: ResourceAlert):
        """Handle a new alert."""
        # Check if similar alert already exists
        existing_alert_key = f"{alert.alert_type}_{alert.severity}"
        
        # Only create new alert if we don't have a recent similar one
        recent_cutoff = datetime.now() - timedelta(minutes=5)
        has_recent_similar = any(
            existing.alert_type == alert.alert_type and
            existing.severity == alert.severity and
            existing.triggered_at > recent_cutoff
            for existing in self.active_alerts.values()
        )
        
        if not has_recent_similar:
            self.active_alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            
            # Broadcast alert
            await self._broadcast_alert(alert)
            
            logger.warning(f"Resource alert: {alert.message}")
    
    async def _update_project_usage(self):
        """Update project-specific resource usage."""
        try:
            # This is a placeholder - in a real implementation, you'd
            # identify processes by project and calculate usage per project
            # For now, we'll create mock data for demonstration
            
            current_time = datetime.now()
            
            # Mock project usage data
            mock_projects = [
                {"id": "web-app-01", "name": "Web Application"},
                {"id": "api-service-02", "name": "API Service"},
                {"id": "background-worker-03", "name": "Background Worker"}
            ]
            
            for project in mock_projects:
                # In a real implementation, you'd calculate actual usage
                usage = ProjectResourceUsage(
                    project_id=project["id"],
                    project_name=project["name"],
                    cpu_percent=psutil.cpu_percent() / len(mock_projects),  # Mock distribution
                    memory_mb=psutil.virtual_memory().used / 1024 / 1024 / len(mock_projects),
                    disk_usage_mb=100.0,  # Mock value
                    network_connections=10,  # Mock value
                    processes=[],  # Would contain actual process info
                    last_updated=current_time
                )
                
                self.project_usage[project["id"]] = usage
        
        except Exception as e:
            logger.error(f"Error updating project usage: {e}")
    
    async def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource metrics."""
        return await self._collect_system_metrics()
    
    async def get_metrics_history(self, hours: int = 1) -> List[ResourceMetrics]:
        """Get metrics history for specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
    
    async def get_project_usage(self, project_id: str = None) -> Dict[str, Any]:
        """Get project resource usage."""
        if project_id:
            return self.project_usage.get(project_id)
        return dict(self.project_usage)
    
    async def get_active_alerts(self) -> List[ResourceAlert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    async def get_alert_history(self, hours: int = 24) -> List[ResourceAlert]:
        """Get alert history."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if alert.triggered_at > cutoff_time
        ]
    
    async def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts.pop(alert_id)
            
            # Broadcast alert dismissal
            await websocket_manager.broadcast_to_channel(Channel.RESOURCES, {
                "type": "alert_dismissed",
                "data": {
                    "alert_id": alert_id,
                    "alert_type": alert.alert_type,
                    "dismissed_at": datetime.now().isoformat()
                }
            })
            
            return True
        return False
    
    async def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update alert thresholds."""
        self.thresholds.update(new_thresholds)
        
        # Broadcast threshold update
        await websocket_manager.broadcast_to_channel(Channel.RESOURCES, {
            "type": "thresholds_updated",
            "data": {
                "thresholds": self.thresholds,
                "updated_at": datetime.now().isoformat()
            }
        })
        
        logger.info("Resource thresholds updated")
    
    async def get_resource_statistics(self) -> Dict[str, Any]:
        """Get resource statistics and trends."""
        if not self.metrics_history:
            return {"error": "No metrics data available"}
        
        # Calculate trends
        recent_metrics = self.metrics_history[-60:]  # Last 60 readings
        
        if len(recent_metrics) < 2:
            return {"error": "Insufficient data for trends"}
        
        # CPU trend
        cpu_values = [m.cpu_percent for m in recent_metrics]
        cpu_trend = "stable"
        if len(cpu_values) > 10:
            recent_avg = sum(cpu_values[-10:]) / 10
            older_avg = sum(cpu_values[-20:-10]) / 10 if len(cpu_values) > 20 else recent_avg
            if recent_avg > older_avg * 1.1:
                cpu_trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                cpu_trend = "decreasing"
        
        # Memory trend
        memory_values = [m.memory_percent for m in recent_metrics]
        memory_trend = "stable"
        if len(memory_values) > 10:
            recent_avg = sum(memory_values[-10:]) / 10
            older_avg = sum(memory_values[-20:-10]) / 10 if len(memory_values) > 20 else recent_avg
            if recent_avg > older_avg * 1.1:
                memory_trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                memory_trend = "decreasing"
        
        return {
            "current_metrics": recent_metrics[-1].dict() if recent_metrics else {},
            "trends": {
                "cpu": {
                    "trend": cpu_trend,
                    "average": sum(cpu_values) / len(cpu_values),
                    "peak": max(cpu_values),
                    "minimum": min(cpu_values)
                },
                "memory": {
                    "trend": memory_trend,
                    "average": sum(memory_values) / len(memory_values),
                    "peak": max(memory_values),
                    "minimum": min(memory_values)
                }
            },
            "alerts": {
                "active_count": len(self.active_alerts),
                "total_today": len([
                    a for a in self.alert_history
                    if a.triggered_at > datetime.now() - timedelta(days=1)
                ])
            },
            "projects": {
                "monitored_count": len(self.project_usage),
                "total_cpu_usage": sum(p.cpu_percent for p in self.project_usage.values()),
                "total_memory_usage": sum(p.memory_mb for p in self.project_usage.values())
            }
        }
    
    async def _broadcast_resource_update(self, metrics: ResourceMetrics):
        """Broadcast resource update via WebSocket."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.RESOURCES, {
                "type": "resource_metrics",
                "data": metrics.dict(),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting resource update: {e}")
    
    async def _broadcast_alert(self, alert: ResourceAlert):
        """Broadcast resource alert."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.RESOURCES, {
                "type": "resource_alert",
                "data": alert.dict(),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting alert: {e}")
    
    async def force_cleanup(self):
        """Force cleanup of old data."""
        # Clean metrics
        cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
        old_count = len(self.metrics_history)
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        # Clean old alerts from history (keep 1 week)
        alert_cutoff = datetime.now() - timedelta(days=7)
        old_alert_count = len(self.alert_history)
        self.alert_history = [
            a for a in self.alert_history
            if a.triggered_at > alert_cutoff
        ]
        
        # Clear resolved alerts older than 1 hour
        resolved_cutoff = datetime.now() - timedelta(hours=1)
        resolved_alerts = []
        for alert_id, alert in self.active_alerts.items():
            if alert.triggered_at < resolved_cutoff and alert.severity in ["low", "medium"]:
                resolved_alerts.append(alert_id)
        
        for alert_id in resolved_alerts:
            self.active_alerts.pop(alert_id, None)
        
        logger.info(f"Resource cleanup: removed {old_count - len(self.metrics_history)} old metrics, "
                   f"{old_alert_count - len(self.alert_history)} old alerts, "
                   f"{len(resolved_alerts)} resolved alerts")