"""
WebSocket API Endpoints
=======================

Real-time WebSocket endpoints for live system updates and monitoring.
Provides live data streaming for dashboards, monitoring tools, and real-time analytics.

Features:
- Real-time system metrics streaming
- Live process and service monitoring
- Project runtime status updates  
- Memory system deliberation progress
- Knowledge graph updates and insights
- Scanner progress and results
- Performance alerts and notifications
- Multi-room support for different data types
- Connection management and heartbeat
- Rate limiting and authentication
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import get_db_session
from ..services.runtime_monitor import RuntimeMonitor
from ..services.enhanced_scanner import EnhancedProjectScanner
from ..council.memory_system import get_memory_system
from ..council.optimus_knowledge_graph import OptimusKnowledgeGraph
from ..models.project import Project

logger = logging.getLogger(__name__)
router = APIRouter()

# =================== CONNECTION MANAGEMENT ===================

class WebSocketRoom(str, Enum):
    """WebSocket room types for organizing connections"""
    SYSTEM_METRICS = "system_metrics"
    PROJECT_MONITORING = "project_monitoring"
    SCANNER_PROGRESS = "scanner_progress"
    DELIBERATIONS = "deliberations"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    DASHBOARD = "dashboard"
    ALERTS = "alerts"


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        # Active connections by room
        self.rooms: Dict[WebSocketRoom, Set[WebSocket]] = defaultdict(set)
        
        # Connection metadata
        self.connections: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Message rate limiting
        self.message_rates: Dict[WebSocket, List[datetime]] = defaultdict(list)
        self.rate_limit_window = timedelta(seconds=60)  # 1 minute window
        self.max_messages_per_window = 1000
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[WebSocket, datetime] = {}
        self.heartbeat_interval = 30  # seconds
        
    async def connect(self, websocket: WebSocket, room: WebSocketRoom, metadata: Dict[str, Any] = None):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        # Add to room
        self.rooms[room].add(websocket)
        
        # Store metadata
        self.connections[websocket] = {
            "room": room,
            "connected_at": datetime.now(),
            "metadata": metadata or {},
            "message_count": 0
        }
        
        # Initialize heartbeat
        self.last_heartbeat[websocket] = datetime.now()
        
        logger.info(f"WebSocket connected to room {room.value}. Total connections: {self.total_connections}")
        
        # Send welcome message
        await self.send_to_connection(websocket, {
            "type": "connection_established",
            "room": room.value,
            "timestamp": datetime.now().isoformat(),
            "server_info": {
                "heartbeat_interval": self.heartbeat_interval,
                "rate_limit": self.max_messages_per_window
            }
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove and cleanup a WebSocket connection"""
        if websocket in self.connections:
            room = self.connections[websocket]["room"]
            
            # Remove from room
            self.rooms[room].discard(websocket)
            
            # Cleanup metadata
            del self.connections[websocket]
            self.message_rates.pop(websocket, None)
            self.last_heartbeat.pop(websocket, None)
            
            logger.info(f"WebSocket disconnected from room {room.value}. Total connections: {self.total_connections}")
    
    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a specific connection with rate limiting"""
        try:
            # Check rate limiting
            if not self._check_rate_limit(websocket):
                logger.warning(f"Rate limit exceeded for WebSocket connection")
                await websocket.send_text(json.dumps({
                    "type": "rate_limit_exceeded",
                    "message": "Message rate limit exceeded",
                    "timestamp": datetime.now().isoformat()
                }))
                return False
            
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            
            # Send message
            await websocket.send_text(json.dumps(message))
            
            # Update message count
            if websocket in self.connections:
                self.connections[websocket]["message_count"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            return False
    
    async def broadcast_to_room(self, room: WebSocketRoom, message: Dict[str, Any], exclude: Set[WebSocket] = None):
        """Broadcast message to all connections in a room"""
        exclude = exclude or set()
        connections = self.rooms[room] - exclude
        
        if not connections:
            return
        
        # Add timestamp
        message["timestamp"] = datetime.now().isoformat()
        message_text = json.dumps(message)
        
        # Send to all connections concurrently
        tasks = []
        for websocket in list(connections):  # Create list to avoid modification during iteration
            if websocket in self.connections:  # Check connection is still valid
                tasks.append(self._safe_send(websocket, message_text))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle failed sends
            failed_connections = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    websocket = list(connections)[i]
                    failed_connections.append(websocket)
                    logger.warning(f"Failed to send to WebSocket: {result}")
            
            # Remove failed connections
            for websocket in failed_connections:
                self.disconnect(websocket)
    
    async def _safe_send(self, websocket: WebSocket, message_text: str):
        """Safely send message to WebSocket with error handling"""
        try:
            await websocket.send_text(message_text)
        except Exception as e:
            # Connection likely closed
            raise e
    
    def _check_rate_limit(self, websocket: WebSocket) -> bool:
        """Check if connection is within rate limits"""
        now = datetime.now()
        
        # Clean old messages outside window
        cutoff = now - self.rate_limit_window
        self.message_rates[websocket] = [
            msg_time for msg_time in self.message_rates[websocket]
            if msg_time > cutoff
        ]
        
        # Check if under limit
        if len(self.message_rates[websocket]) >= self.max_messages_per_window:
            return False
        
        # Add current message
        self.message_rates[websocket].append(now)
        return True
    
    @property
    def total_connections(self) -> int:
        """Get total number of active connections"""
        return len(self.connections)
    
    def get_room_stats(self) -> Dict[str, int]:
        """Get connection statistics by room"""
        return {room.value: len(connections) for room, connections in self.rooms.items()}
    
    async def cleanup_stale_connections(self):
        """Remove connections that haven't sent heartbeat"""
        now = datetime.now()
        stale_connections = []
        
        for websocket, last_heartbeat in self.last_heartbeat.items():
            if (now - last_heartbeat).seconds > self.heartbeat_interval * 2:
                stale_connections.append(websocket)
        
        for websocket in stale_connections:
            logger.info("Removing stale WebSocket connection")
            self.disconnect(websocket)


# Global connection manager instance
connection_manager = ConnectionManager()


# =================== WEBSOCKET ENDPOINTS ===================

@router.websocket("/system/metrics")
async def system_metrics_websocket(websocket: WebSocket):
    """
    Real-time system metrics WebSocket endpoint.
    
    Streams live CPU, memory, disk, and network metrics
    for dashboard monitoring and alerting.
    """
    await connection_manager.connect(websocket, WebSocketRoom.SYSTEM_METRICS)
    
    try:
        # Get session for monitoring
        session = next(get_db_session())
        monitor = RuntimeMonitor(session)
        await monitor.initialize()
        
        # Send initial metrics
        initial_metrics = await monitor.collect_system_metrics()
        await connection_manager.send_to_connection(websocket, {
            "type": "initial_metrics",
            "data": {
                "cpu_percent": initial_metrics.cpu_percent,
                "memory_percent": initial_metrics.memory_percent,
                "disk_usage_percent": initial_metrics.disk_usage_percent,
                "network_bytes_sent": initial_metrics.network_bytes_sent,
                "network_bytes_recv": initial_metrics.network_bytes_recv,
                "load_average": initial_metrics.load_average,
                "processes_count": initial_metrics.processes_count,
                "active_connections": initial_metrics.active_connections
            }
        })
        
        # Start metrics streaming loop
        while True:
            try:
                # Wait for client message or timeout
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    message = json.loads(data)
                    
                    # Handle heartbeat
                    if message.get("type") == "heartbeat":
                        connection_manager.last_heartbeat[websocket] = datetime.now()
                        await connection_manager.send_to_connection(websocket, {
                            "type": "heartbeat_ack"
                        })
                        continue
                    
                except asyncio.TimeoutError:
                    # No message received, continue with metrics collection
                    pass
                
                # Collect and send metrics
                metrics = await monitor.collect_system_metrics()
                
                await connection_manager.send_to_connection(websocket, {
                    "type": "metrics_update",
                    "data": {
                        "cpu_percent": metrics.cpu_percent,
                        "memory_percent": metrics.memory_percent,
                        "disk_usage_percent": metrics.disk_usage_percent,
                        "network_bytes_sent": metrics.network_bytes_sent,
                        "network_bytes_recv": metrics.network_bytes_recv,
                        "load_average": metrics.load_average,
                        "processes_count": metrics.processes_count,
                        "active_connections": metrics.active_connections,
                        "timestamp": metrics.timestamp.isoformat()
                    }
                })
                
                # Check for performance alerts
                alerts = []
                if metrics.cpu_percent > 80:
                    alerts.append({
                        "type": "cpu_high",
                        "severity": "warning" if metrics.cpu_percent < 90 else "critical",
                        "value": metrics.cpu_percent,
                        "threshold": 80
                    })
                
                if metrics.memory_percent > 85:
                    alerts.append({
                        "type": "memory_high",
                        "severity": "warning" if metrics.memory_percent < 95 else "critical",
                        "value": metrics.memory_percent,
                        "threshold": 85
                    })
                
                if alerts:
                    await connection_manager.send_to_connection(websocket, {
                        "type": "performance_alerts",
                        "alerts": alerts
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in system metrics WebSocket: {e}")
                await connection_manager.send_to_connection(websocket, {
                    "type": "error",
                    "message": str(e)
                })
                await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


@router.websocket("/projects/monitoring")
async def project_monitoring_websocket(websocket: WebSocket):
    """
    Real-time project monitoring WebSocket endpoint.
    
    Streams live process status, runtime information,
    and project activity for all monitored projects.
    """
    await connection_manager.connect(websocket, WebSocketRoom.PROJECT_MONITORING)
    
    try:
        session = next(get_db_session())
        monitor = RuntimeMonitor(session)
        await monitor.initialize()
        
        # Send initial project status
        overview = await monitor.get_system_overview()
        await connection_manager.send_to_connection(websocket, {
            "type": "initial_overview",
            "data": overview
        })
        
        # Monitoring loop
        while True:
            try:
                # Wait for client message or timeout
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                    message = json.loads(data)
                    
                    if message.get("type") == "heartbeat":
                        connection_manager.last_heartbeat[websocket] = datetime.now()
                        continue
                    
                    elif message.get("type") == "subscribe_project":
                        project_id = message.get("project_id")
                        if project_id:
                            # Send specific project status
                            status = await monitor.get_project_runtime_status(project_id)
                            await connection_manager.send_to_connection(websocket, {
                                "type": "project_status",
                                "project_id": project_id,
                                "data": status
                            })
                        continue
                    
                except asyncio.TimeoutError:
                    pass
                
                # Scan for process updates
                processes = await monitor.scan_processes()
                services = await monitor.scan_services()
                
                # Send process updates
                active_processes = [
                    {
                        "pid": p.pid,
                        "name": p.name,
                        "project_id": p.project_id,
                        "cpu_percent": p.cpu_percent,
                        "memory_percent": p.memory_percent,
                        "status": p.status,
                        "ports": p.ports
                    }
                    for p in processes if p.project_id
                ]
                
                await connection_manager.send_to_connection(websocket, {
                    "type": "processes_update",
                    "data": active_processes
                })
                
                # Send service updates
                active_services = [
                    {
                        "name": s.name,
                        "host": s.host,
                        "port": s.port,
                        "status": s.status,
                        "response_time_ms": s.response_time_ms,
                        "project_path": s.project_path
                    }
                    for s in services if s.status == "active"
                ]
                
                await connection_manager.send_to_connection(websocket, {
                    "type": "services_update",
                    "data": active_services
                })
                
                # Check for containers if Docker is available
                if monitor.docker_client:
                    containers = await monitor.scan_containers()
                    container_data = [
                        {
                            "id": c.id[:12],
                            "name": c.name,
                            "image": c.image,
                            "status": c.status,
                            "project_path": c.project_path
                        }
                        for c in containers
                    ]
                    
                    await connection_manager.send_to_connection(websocket, {
                        "type": "containers_update",
                        "data": container_data
                    })
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in project monitoring WebSocket: {e}")
                await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


@router.websocket("/scanner/progress")
async def scanner_progress_websocket(websocket: WebSocket):
    """
    Scanner progress WebSocket endpoint.
    
    Streams live updates during project scanning operations
    including discovery progress, analysis status, and results.
    """
    await connection_manager.connect(websocket, WebSocketRoom.SCANNER_PROGRESS)
    
    try:
        session = next(get_db_session())
        
        # Handle client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "heartbeat":
                    connection_manager.last_heartbeat[websocket] = datetime.now()
                    continue
                
                elif message.get("type") == "start_scan":
                    # Start scan and stream progress
                    base_path = message.get("base_path")
                    scan_options = message.get("options", {})
                    
                    await connection_manager.send_to_connection(websocket, {
                        "type": "scan_started",
                        "base_path": base_path,
                        "options": scan_options
                    })
                    
                    # Create scanner and start scan
                    scanner = EnhancedProjectScanner(session)
                    
                    # This would ideally be a streaming scan with progress callbacks
                    # For now, simulate progress updates
                    total_steps = 5
                    for step in range(1, total_steps + 1):
                        await asyncio.sleep(2)  # Simulate work
                        
                        progress = (step / total_steps) * 100
                        step_names = [
                            "Discovering projects",
                            "Analyzing technology stacks", 
                            "Scanning dependencies",
                            "Running security checks",
                            "Generating insights"
                        ]
                        
                        await connection_manager.send_to_connection(websocket, {
                            "type": "scan_progress",
                            "progress_percent": progress,
                            "current_step": step_names[step - 1],
                            "step": step,
                            "total_steps": total_steps
                        })
                    
                    # Complete scan
                    try:
                        project_ids, metrics = await scanner.scan_and_save_all(base_path)
                        
                        await connection_manager.send_to_connection(websocket, {
                            "type": "scan_completed",
                            "projects_found": len(project_ids),
                            "metrics": {
                                "projects_scanned": metrics.projects_scanned,
                                "files_analyzed": metrics.files_analyzed,
                                "dependencies_found": metrics.dependencies_found,
                                "vulnerabilities_detected": metrics.vulnerabilities_detected,
                                "elapsed_time": metrics.elapsed_time()
                            }
                        })
                        
                    except Exception as e:
                        await connection_manager.send_to_connection(websocket, {
                            "type": "scan_error",
                            "error": str(e)
                        })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in scanner WebSocket: {e}")
                await connection_manager.send_to_connection(websocket, {
                    "type": "error", 
                    "message": str(e)
                })
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


@router.websocket("/deliberations/{deliberation_id}")
async def deliberation_progress_websocket(websocket: WebSocket, deliberation_id: str):
    """
    Deliberation progress WebSocket endpoint.
    
    Streams live updates during Council of Minds deliberations
    including persona responses, consensus building, and final results.
    """
    await connection_manager.connect(
        websocket, 
        WebSocketRoom.DELIBERATIONS,
        metadata={"deliberation_id": deliberation_id}
    )
    
    try:
        # Send connection confirmation
        await connection_manager.send_to_connection(websocket, {
            "type": "deliberation_connected",
            "deliberation_id": deliberation_id
        })
        
        # Handle client messages and stream deliberation updates
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                if message.get("type") == "heartbeat":
                    connection_manager.last_heartbeat[websocket] = datetime.now()
                    continue
                
                elif message.get("type") == "subscribe":
                    new_deliberation_id = message.get("deliberation_id")
                    if new_deliberation_id:
                        connection_manager.connections[websocket]["metadata"]["deliberation_id"] = new_deliberation_id
                        await connection_manager.send_to_connection(websocket, {
                            "type": "subscription_updated",
                            "deliberation_id": new_deliberation_id
                        })
                
            except asyncio.TimeoutError:
                # Send heartbeat ping
                await connection_manager.send_to_connection(websocket, {
                    "type": "ping"
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in deliberation WebSocket: {e}")
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


@router.websocket("/dashboard/live")
async def dashboard_websocket(websocket: WebSocket):
    """
    Live dashboard WebSocket endpoint.
    
    Streams aggregated real-time data for dashboard widgets
    including metrics, alerts, insights, and system status.
    """
    await connection_manager.connect(websocket, WebSocketRoom.DASHBOARD)
    
    try:
        session = next(get_db_session())
        
        # Send initial dashboard data
        from .dashboard import _get_system_health_metrics, _get_performance_metrics
        
        health_metrics = await _get_system_health_metrics(session)
        performance_metrics = await _get_performance_metrics(session)
        
        await connection_manager.send_to_connection(websocket, {
            "type": "dashboard_init",
            "data": {
                "health": health_metrics,
                "performance": performance_metrics,
                "timestamp": datetime.now().isoformat()
            }
        })
        
        # Dashboard update loop
        while True:
            try:
                # Wait for client message or timeout
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
                    message = json.loads(data)
                    
                    if message.get("type") == "heartbeat":
                        connection_manager.last_heartbeat[websocket] = datetime.now()
                        continue
                    
                    elif message.get("type") == "request_update":
                        widget_type = message.get("widget")
                        
                        if widget_type == "health":
                            health_data = await _get_system_health_metrics(session)
                            await connection_manager.send_to_connection(websocket, {
                                "type": "widget_update",
                                "widget": "health",
                                "data": health_data
                            })
                        
                        elif widget_type == "performance":
                            perf_data = await _get_performance_metrics(session)
                            await connection_manager.send_to_connection(websocket, {
                                "type": "widget_update", 
                                "widget": "performance",
                                "data": perf_data
                            })
                        
                        continue
                
                except asyncio.TimeoutError:
                    pass
                
                # Send periodic dashboard updates
                current_time = datetime.now()
                
                # Update health metrics every 30 seconds
                if current_time.second % 30 == 0:
                    health_data = await _get_system_health_metrics(session)
                    await connection_manager.send_to_connection(websocket, {
                        "type": "health_update",
                        "data": health_data
                    })
                
                # Update performance metrics every 10 seconds  
                if current_time.second % 10 == 0:
                    perf_data = await _get_performance_metrics(session)
                    await connection_manager.send_to_connection(websocket, {
                        "type": "performance_update",
                        "data": perf_data
                    })
                
                await asyncio.sleep(1)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in dashboard WebSocket: {e}")
                await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


@router.websocket("/alerts/live")
async def alerts_websocket(websocket: WebSocket):
    """
    Live alerts WebSocket endpoint.
    
    Streams real-time alerts, warnings, and notifications
    from all system components for immediate attention.
    """
    await connection_manager.connect(websocket, WebSocketRoom.ALERTS)
    
    try:
        # Send connection confirmation
        await connection_manager.send_to_connection(websocket, {
            "type": "alerts_connected",
            "message": "Connected to live alerts stream"
        })
        
        # Alerts monitoring loop
        while True:
            try:
                # Wait for client message or timeout
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=20.0)
                    message = json.loads(data)
                    
                    if message.get("type") == "heartbeat":
                        connection_manager.last_heartbeat[websocket] = datetime.now()
                        continue
                    
                    elif message.get("type") == "set_filters":
                        # Store alert filters in connection metadata
                        filters = message.get("filters", {})
                        connection_manager.connections[websocket]["metadata"]["alert_filters"] = filters
                        
                        await connection_manager.send_to_connection(websocket, {
                            "type": "filters_updated",
                            "filters": filters
                        })
                        continue
                
                except asyncio.TimeoutError:
                    pass
                
                # Check for new alerts (placeholder - would integrate with actual alert system)
                current_time = datetime.now()
                
                # Example: Generate test alert every 2 minutes
                if current_time.second == 0 and current_time.minute % 2 == 0:
                    test_alert = {
                        "alert_id": f"test_{current_time.timestamp()}",
                        "type": "performance", 
                        "severity": "warning",
                        "title": "High CPU Usage Detected",
                        "description": "CPU usage exceeded 80% threshold",
                        "timestamp": current_time.isoformat(),
                        "source": "monitor",
                        "project_id": None,
                        "auto_dismiss": True
                    }
                    
                    # Check filters
                    filters = connection_manager.connections[websocket]["metadata"].get("alert_filters", {})
                    if not filters or self._alert_matches_filters(test_alert, filters):
                        await connection_manager.send_to_connection(websocket, {
                            "type": "new_alert",
                            "alert": test_alert
                        })
                
                await asyncio.sleep(1)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in alerts WebSocket: {e}")
                await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


# =================== UTILITY FUNCTIONS ===================

def _alert_matches_filters(alert: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Check if alert matches the specified filters"""
    # Check severity filter
    if "severity" in filters:
        allowed_severities = filters["severity"]
        if isinstance(allowed_severities, str):
            allowed_severities = [allowed_severities]
        if alert.get("severity") not in allowed_severities:
            return False
    
    # Check type filter
    if "type" in filters:
        allowed_types = filters["type"]
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]
        if alert.get("type") not in allowed_types:
            return False
    
    # Check project filter
    if "project_id" in filters:
        if alert.get("project_id") != filters["project_id"]:
            return False
    
    return True


# =================== BROADCAST FUNCTIONS ===================

async def broadcast_system_alert(alert: Dict[str, Any]):
    """Broadcast system alert to all alert subscribers"""
    await connection_manager.broadcast_to_room(WebSocketRoom.ALERTS, {
        "type": "system_alert",
        "alert": alert
    })


async def broadcast_scan_progress(progress_data: Dict[str, Any]):
    """Broadcast scan progress to scanner subscribers"""
    await connection_manager.broadcast_to_room(WebSocketRoom.SCANNER_PROGRESS, {
        "type": "scan_progress_broadcast",
        "data": progress_data
    })


async def broadcast_deliberation_update(deliberation_id: str, update_data: Dict[str, Any]):
    """Broadcast deliberation update to specific deliberation subscribers"""
    # Find connections subscribed to this deliberation
    relevant_connections = set()
    for websocket, metadata in connection_manager.connections.items():
        if (metadata.get("room") == WebSocketRoom.DELIBERATIONS and 
            metadata.get("metadata", {}).get("deliberation_id") == deliberation_id):
            relevant_connections.add(websocket)
    
    if relevant_connections:
        message = {
            "type": "deliberation_update",
            "deliberation_id": deliberation_id,
            "data": update_data
        }
        
        for websocket in relevant_connections:
            await connection_manager.send_to_connection(websocket, message)


async def broadcast_knowledge_graph_update(update_data: Dict[str, Any]):
    """Broadcast knowledge graph updates"""
    await connection_manager.broadcast_to_room(WebSocketRoom.KNOWLEDGE_GRAPH, {
        "type": "kg_update",
        "data": update_data
    })


# =================== MANAGEMENT ENDPOINTS ===================

@router.websocket("/admin/connections")
async def admin_connections_websocket(websocket: WebSocket):
    """
    Admin WebSocket for monitoring all connections and system status.
    
    Provides administrative view of active connections, room statistics,
    and connection health monitoring.
    """
    await connection_manager.connect(websocket, WebSocketRoom.DASHBOARD, {
        "admin": True,
        "permissions": ["view_connections", "manage_connections"]
    })
    
    try:
        # Send initial connection stats
        await connection_manager.send_to_connection(websocket, {
            "type": "connection_stats",
            "total_connections": connection_manager.total_connections,
            "room_stats": connection_manager.get_room_stats(),
            "timestamp": datetime.now().isoformat()
        })
        
        # Admin monitoring loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                message = json.loads(data)
                
                if message.get("type") == "heartbeat":
                    connection_manager.last_heartbeat[websocket] = datetime.now()
                    continue
                
                elif message.get("type") == "get_stats":
                    await connection_manager.send_to_connection(websocket, {
                        "type": "connection_stats", 
                        "total_connections": connection_manager.total_connections,
                        "room_stats": connection_manager.get_room_stats()
                    })
                
                elif message.get("type") == "cleanup_stale":
                    await connection_manager.cleanup_stale_connections()
                    await connection_manager.send_to_connection(websocket, {
                        "type": "cleanup_completed",
                        "remaining_connections": connection_manager.total_connections
                    })
                
            except asyncio.TimeoutError:
                # Send periodic stats update
                await connection_manager.send_to_connection(websocket, {
                    "type": "stats_update",
                    "total_connections": connection_manager.total_connections,
                    "room_stats": connection_manager.get_room_stats()
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in admin WebSocket: {e}")
                await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)


# =================== BACKGROUND TASKS ===================

async def start_websocket_background_tasks():
    """Start background tasks for WebSocket management"""
    
    async def cleanup_task():
        """Periodic cleanup of stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await connection_manager.cleanup_stale_connections()
            except Exception as e:
                logger.error(f"Error in WebSocket cleanup task: {e}")
    
    # Start cleanup task
    asyncio.create_task(cleanup_task())
    logger.info("WebSocket background tasks started")


# Initialize task will be created by the FastAPI app startup