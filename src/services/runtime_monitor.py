"""
Runtime Monitor Service
======================

Monitors running processes, services, and applications to detect active projects.
Features include:

- Process detection using psutil for cross-platform compatibility
- Port scanning to identify running web services
- Docker container monitoring
- Resource usage tracking (CPU, memory, disk I/O)
- Log file monitoring for errors and patterns
- Service health checking and status reporting
- Performance metrics collection

Integrates with:
- Project scanner to match processes with discovered projects
- Knowledge graph to track runtime relationships
- Memory system for learning runtime patterns
- Alert system for performance issues and failures
"""

import asyncio
import json
import logging
import os
import platform
import re
import socket
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field

import psutil
import docker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from ..config import get_settings
from ..models import Project, RuntimeStatus
from ..council.memory_integration import MemoryIntegration
from ..council.knowledge_graph_integration import KnowledgeGraphIntegration


logger = logging.getLogger("optimus.runtime_monitor")


@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    name: str
    cmdline: List[str]
    cwd: Optional[str]
    status: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int  # Resident Set Size in bytes
    create_time: float
    ports: List[int] = field(default_factory=list)
    project_path: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class ServiceInfo:
    """Information about a detected service."""
    name: str
    host: str
    port: int
    protocol: str
    status: str  # active, inactive, failed
    pid: Optional[int] = None
    process_name: Optional[str] = None
    project_path: Optional[str] = None
    response_time_ms: Optional[float] = None
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ContainerInfo:
    """Information about a Docker container."""
    id: str
    name: str
    image: str
    status: str
    ports: Dict[str, List[Dict]]
    labels: Dict[str, str]
    created: datetime
    project_path: Optional[str] = None


@dataclass
class SystemMetrics:
    """System-wide resource metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: Tuple[float, float, float]  # 1min, 5min, 15min
    processes_count: int
    active_connections: int


@dataclass
class PerformanceAlert:
    """Performance alert for detected issues."""
    project_id: Optional[str]
    alert_type: str  # memory_leak, cpu_spike, disk_full, etc.
    severity: str    # low, medium, high, critical
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    threshold_exceeded: float
    current_value: float


@dataclass
class ProcessTrend:
    """Process performance trend analysis."""
    process_name: str
    pid: int
    trend_direction: str  # increasing, decreasing, stable
    metric_type: str      # cpu, memory, disk_io, network
    change_rate: float    # percent change per minute
    duration_minutes: int
    confidence: float     # 0-1 confidence in trend


class RuntimeMonitor:
    """Monitor running processes and services for project activity detection."""
    
    def __init__(self, session: AsyncSession, memory_integration: MemoryIntegration = None,
                 kg_integration: KnowledgeGraphIntegration = None):
        self.session = session
        self.settings = get_settings()
        self.memory = memory_integration
        self.kg = kg_integration
        
        # Docker client (optional)
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.debug(f"Docker not available: {e}")
        
        # Process monitoring state
        self.known_processes: Dict[int, ProcessInfo] = {}
        self.known_services: Dict[str, ServiceInfo] = {}
        self.known_containers: Dict[str, ContainerInfo] = {}
        self.project_mapping: Dict[str, str] = {}  # path -> project_id
        
        # Common development server patterns
        self.dev_server_patterns = {
            "python": [
                r"python.*manage\.py.*runserver",  # Django
                r"python.*-m.*uvicorn",  # FastAPI
                r"python.*app\.py",  # Flask
                r"python.*-m.*streamlit",  # Streamlit
                r"python.*-m.*jupyter",  # Jupyter
                r"gunicorn.*",  # Gunicorn
            ],
            "node": [
                r"node.*server\.js",  # Node.js
                r"node.*app\.js",
                r"npm.*start",
                r"yarn.*start",
                r"next.*dev",  # Next.js
                r"nuxt.*dev",  # Nuxt.js
                r"vue-cli-service.*serve",  # Vue CLI
                r"ng.*serve",  # Angular CLI
            ],
            "rust": [
                r"cargo.*run",
                r"target/debug/.*",
                r"target/release/.*",
            ],
            "go": [
                r"go.*run",
                r".*\.go$",
            ],
            "java": [
                r"java.*\.jar",
                r"mvn.*spring-boot:run",
                r"gradle.*bootRun",
            ],
            "php": [
                r"php.*artisan.*serve",  # Laravel
                r"php.*-S.*",  # Built-in server
            ],
            "ruby": [
                r"ruby.*rails.*server",
                r"bundle.*exec.*rails",
                r"puma.*",
                r"unicorn.*",
            ]
        }
        
        # Common ports for development services
        self.common_dev_ports = {
            3000: "React/Node.js dev server",
            3001: "React/Node.js (alt)",
            4200: "Angular dev server",
            5000: "Flask default",
            8000: "Django/FastAPI default",
            8080: "Common dev server",
            8888: "Jupyter Notebook",
            9000: "Various dev tools",
            5173: "Vite dev server",
            4000: "Ruby on Rails",
            3333: "AdonisJS",
        }
        
        # Log file patterns to monitor
        self.log_patterns = [
            "*.log", "logs/*.log", "log/*.log",
            "var/log/*.log", "tmp/*.log",
            ".pm2/logs/*.log", "nohup.out"
        ]
        
        # Error patterns to detect in logs
        self.error_patterns = [
            r"ERROR",
            r"CRITICAL",
            r"FATAL",
            r"Exception",
            r"Traceback",
            r"500 Internal Server Error",
            r"connection refused",
            r"timeout",
            r"failed to connect",
            r"OutOfMemoryError",
            r"StackOverflowError",
            r"segmentation fault",
            r"panic:",
            r"SIGSEGV",
            r"core dumped"
        ]
        
        # Performance thresholds for alerts
        self.performance_thresholds = {
            'cpu_percent': {'warning': 80.0, 'critical': 95.0},
            'memory_percent': {'warning': 85.0, 'critical': 95.0},
            'disk_percent': {'warning': 85.0, 'critical': 95.0},
            'process_cpu': {'warning': 50.0, 'critical': 80.0},
            'process_memory': {'warning': 500 * 1024 * 1024, 'critical': 1024 * 1024 * 1024},  # MB to bytes
            'network_connections': {'warning': 1000, 'critical': 2000}
        }
        
        # Performance history for trend analysis
        self.performance_history: Dict[str, List[Dict]] = defaultdict(list)
        self.process_history: Dict[int, List[ProcessInfo]] = defaultdict(list)
        
        # Alert tracking to avoid spam
        self.recent_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=5)
    
    async def initialize(self) -> None:
        """Initialize runtime monitor and load project mappings."""
        logger.info("Initializing runtime monitor")
        
        # Load project mappings from database
        await self._load_project_mappings()
        
        # Initial system scan
        await self._scan_initial_state()
        
        logger.info(f"Runtime monitor initialized. Tracking {len(self.project_mapping)} projects")
    
    async def _load_project_mappings(self) -> None:
        """Load project path to ID mappings from database."""
        try:
            stmt = select(Project.id, Project.path).where(Project.status != "inactive")
            result = await self.session.execute(stmt)
            
            for project_id, project_path in result.fetchall():
                self.project_mapping[project_path] = str(project_id)
            
            logger.debug(f"Loaded {len(self.project_mapping)} project mappings")
            
        except Exception as e:
            logger.error(f"Error loading project mappings: {e}")
    
    async def _scan_initial_state(self) -> None:
        """Perform initial scan of system state."""
        logger.info("Performing initial system state scan")
        
        # Scan processes
        await self.scan_processes()
        
        # Scan services/ports
        await self.scan_services()
        
        # Scan Docker containers
        if self.docker_client:
            await self.scan_containers()
        
        logger.info(f"Initial scan complete: {len(self.known_processes)} processes, "
                   f"{len(self.known_services)} services, {len(self.known_containers)} containers")
    
    async def scan_processes(self) -> List[ProcessInfo]:
        """Scan for running processes and detect project-related ones."""
        current_processes = {}
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd', 'status',
                                           'cpu_percent', 'memory_percent', 'memory_info',
                                           'create_time']):
                try:
                    info = proc.info
                    if not info['cmdline']:
                        continue
                    
                    cmdline_str = ' '.join(info['cmdline'])
                    
                    # Skip system processes and common non-dev processes
                    if self._should_skip_process(info['name'], cmdline_str):
                        continue
                    
                    # Check if process might be development-related
                    if self._is_development_process(info['name'], cmdline_str):
                        process_info = ProcessInfo(
                            pid=info['pid'],
                            name=info['name'],
                            cmdline=info['cmdline'],
                            cwd=info.get('cwd'),
                            status=info['status'],
                            cpu_percent=info['cpu_percent'],
                            memory_percent=info['memory_percent'],
                            memory_rss=info['memory_info'].rss if info['memory_info'] else 0,
                            create_time=info['create_time']
                        )
                        
                        # Try to match process to a project
                        await self._match_process_to_project(process_info)
                        
                        # Get ports used by this process
                        process_info.ports = await self._get_process_ports(info['pid'])
                        
                        current_processes[info['pid']] = process_info
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.debug(f"Error processing process: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scanning processes: {e}")
        
        # Update known processes
        self.known_processes = current_processes
        
        # Store runtime status in database
        await self._store_process_status()
        
        return list(current_processes.values())
    
    def _should_skip_process(self, name: str, cmdline: str) -> bool:
        """Check if process should be skipped from monitoring."""
        # Skip system processes
        system_processes = {
            'kernel_task', 'launchd', 'kextd', 'mds', 'mdworker', 'spotlight',
            'WindowServer', 'Dock', 'Finder', 'SystemUIServer',
            'init', 'kthreadd', 'ksoftirqd', 'systemd', 'dbus'
        }
        
        if name.lower() in system_processes:
            return True
        
        # Skip common system commands
        skip_patterns = [
            r'^/System/',
            r'^/usr/bin/(ps|top|htop|grep|awk|sed)',
            r'^/usr/sbin/',
            r'com\.apple\.',
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, cmdline):
                return True
        
        return False
    
    def _is_development_process(self, name: str, cmdline: str) -> bool:
        """Check if process is likely development-related."""
        # Check for development tools and languages
        dev_indicators = [
            'python', 'node', 'npm', 'yarn', 'cargo', 'go', 'java', 'mvn',
            'gradle', 'php', 'ruby', 'rails', 'bundle', 'docker', 'docker-compose'
        ]
        
        name_lower = name.lower()
        cmdline_lower = cmdline.lower()
        
        # Direct name match
        if any(indicator in name_lower for indicator in dev_indicators):
            return True
        
        # Command line pattern matching
        for lang, patterns in self.dev_server_patterns.items():
            for pattern in patterns:
                if re.search(pattern, cmdline_lower):
                    return True
        
        # Check for common development keywords
        dev_keywords = [
            'serve', 'server', 'dev', 'development', 'watch', 'hot-reload',
            'livereload', 'nodemon', 'webpack', 'vite', 'rollup'
        ]
        
        if any(keyword in cmdline_lower for keyword in dev_keywords):
            return True
        
        return False
    
    async def _match_process_to_project(self, process_info: ProcessInfo) -> None:
        """Try to match a process to a known project."""
        if not process_info.cwd:
            return
        
        cwd_path = Path(process_info.cwd)
        
        # Look for exact match
        if process_info.cwd in self.project_mapping:
            process_info.project_path = process_info.cwd
            process_info.project_id = self.project_mapping[process_info.cwd]
            return
        
        # Look for parent directory match
        for project_path, project_id in self.project_mapping.items():
            project_path_obj = Path(project_path)
            
            # Check if process CWD is within project directory
            try:
                cwd_path.relative_to(project_path_obj)
                process_info.project_path = project_path
                process_info.project_id = project_id
                return
            except ValueError:
                continue
        
        # Check command line for project paths
        cmdline_str = ' '.join(process_info.cmdline)
        for project_path in self.project_mapping.keys():
            if project_path in cmdline_str:
                process_info.project_path = project_path
                process_info.project_id = self.project_mapping[project_path]
                return
    
    async def _get_process_ports(self, pid: int) -> List[int]:
        """Get ports used by a specific process."""
        ports = []
        
        try:
            proc = psutil.Process(pid)
            connections = proc.connections(kind='inet')
            
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    ports.append(conn.laddr.port)
        
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception as e:
            logger.debug(f"Error getting ports for PID {pid}: {e}")
        
        return ports
    
    async def scan_services(self) -> List[ServiceInfo]:
        """Scan for active services by checking common ports."""
        discovered_services = {}
        
        # Common ports to check
        ports_to_check = list(self.common_dev_ports.keys()) + [
            80, 443, 3306, 5432, 6379, 27017, 9200, 5000, 8001, 8002, 8003
        ]
        
        # Add ports from known processes
        for proc in self.known_processes.values():
            ports_to_check.extend(proc.ports)
        
        # Remove duplicates
        ports_to_check = list(set(ports_to_check))
        
        # Check each port
        for port in ports_to_check:
            service_info = await self._check_port_service(port)
            if service_info:
                service_key = f"{service_info.host}:{service_info.port}"
                discovered_services[service_key] = service_info
        
        self.known_services = discovered_services
        return list(discovered_services.values())
    
    async def _check_port_service(self, port: int, host: str = "localhost") -> Optional[ServiceInfo]:
        """Check if a service is running on the specified port."""
        try:
            # Try to connect to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)  # 1 second timeout
            
            start_time = time.time()
            result = sock.connect_ex((host, port))
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            sock.close()
            
            if result == 0:  # Connection successful
                # Try to determine what's running on this port
                service_name = self.common_dev_ports.get(port, f"Service on port {port}")
                
                # Try to find the process using this port
                listening_pid = None
                process_name = None
                
                for proc_info in self.known_processes.values():
                    if port in proc_info.ports:
                        listening_pid = proc_info.pid
                        process_name = proc_info.name
                        break
                
                service_info = ServiceInfo(
                    name=service_name,
                    host=host,
                    port=port,
                    protocol="tcp",
                    status="active",
                    pid=listening_pid,
                    process_name=process_name,
                    response_time_ms=response_time,
                    last_check=datetime.now(timezone.utc)
                )
                
                # Try to match service to project
                await self._match_service_to_project(service_info)
                
                return service_info
        
        except Exception as e:
            logger.debug(f"Error checking port {port}: {e}")
        
        return None
    
    async def _match_service_to_project(self, service_info: ServiceInfo) -> None:
        """Try to match a service to a known project."""
        # If we found the process, use its project mapping
        if service_info.pid:
            for proc_info in self.known_processes.values():
                if proc_info.pid == service_info.pid and proc_info.project_path:
                    service_info.project_path = proc_info.project_path
                    return
        
        # Try to match by port conventions
        if service_info.port in self.common_dev_ports:
            # This is a heuristic approach - could be enhanced
            pass
    
    async def scan_containers(self) -> List[ContainerInfo]:
        """Scan Docker containers for running project services."""
        if not self.docker_client:
            return []
        
        containers = {}
        
        try:
            for container in self.docker_client.containers.list(all=True):
                container_info = ContainerInfo(
                    id=container.id,
                    name=container.name,
                    image=container.image.tags[0] if container.image.tags else container.image.id,
                    status=container.status,
                    ports=container.ports,
                    labels=container.labels,
                    created=datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00'))
                )
                
                # Try to match container to project
                await self._match_container_to_project(container_info)
                
                containers[container.id] = container_info
        
        except Exception as e:
            logger.error(f"Error scanning Docker containers: {e}")
        
        self.known_containers = containers
        return list(containers.values())
    
    async def _match_container_to_project(self, container_info: ContainerInfo) -> None:
        """Try to match a Docker container to a known project."""
        # Check container labels for project information
        if 'project.path' in container_info.labels:
            project_path = container_info.labels['project.path']
            if project_path in self.project_mapping:
                container_info.project_path = project_path
                return
        
        # Check if container name matches a project
        for project_path, project_id in self.project_mapping.items():
            project_name = Path(project_path).name
            if project_name.lower() in container_info.name.lower():
                container_info.project_path = project_path
                return
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect system-wide performance metrics."""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage (root partition)
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Load average (Unix-like systems only)
            load_avg = (0.0, 0.0, 0.0)
            if hasattr(os, 'getloadavg'):
                try:
                    load_avg = os.getloadavg()
                except OSError:
                    pass
            
            # Active connections
            connections = len(psutil.net_connections(kind='inet'))
            
            # Process count
            process_count = len(psutil.pids())
            
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                load_average=load_avg,
                processes_count=process_count,
                active_connections=connections
            )
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                load_average=(0.0, 0.0, 0.0),
                processes_count=0,
                active_connections=0
            )
    
    async def monitor_log_files(self, project_path: str, max_lines: int = 100) -> Dict[str, List[str]]:
        """Monitor log files for errors and patterns."""
        log_entries = {"errors": [], "warnings": [], "info": []}
        
        try:
            project_dir = Path(project_path)
            
            # Find log files
            log_files = []
            for pattern in self.log_patterns:
                log_files.extend(list(project_dir.glob(pattern)))
            
            # Analyze recent log entries
            for log_file in log_files[:10]:  # Limit to 10 log files
                try:
                    if log_file.is_file() and log_file.stat().st_size > 0:
                        entries = await self._analyze_log_file(log_file, max_lines)
                        for category, entries_list in entries.items():
                            log_entries[category].extend(entries_list)
                except Exception as e:
                    logger.debug(f"Error analyzing log file {log_file}: {e}")
        
        except Exception as e:
            logger.warning(f"Error monitoring log files for {project_path}: {e}")
        
        return log_entries
    
    async def _analyze_log_file(self, log_file: Path, max_lines: int) -> Dict[str, List[str]]:
        """Analyze a single log file for errors and patterns."""
        entries = {"errors": [], "warnings": [], "info": []}
        
        try:
            # Read last N lines of the log file
            lines = []
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-max_lines:]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                line_lower = line.lower()
                
                # Categorize log entry
                if any(pattern.lower() in line_lower for pattern in ['error', 'critical', 'fatal', 'exception']):
                    entries["errors"].append(line)
                elif any(pattern.lower() in line_lower for pattern in ['warning', 'warn']):
                    entries["warnings"].append(line)
                else:
                    # Only keep recent info entries to avoid noise
                    if len(entries["info"]) < 20:
                        entries["info"].append(line)
        
        except Exception as e:
            logger.debug(f"Error reading log file {log_file}: {e}")
        
        return entries
    
    async def _store_process_status(self) -> None:
        """Store process status information in database."""
        try:
            for process_info in self.known_processes.values():
                if process_info.project_id:
                    # Create or update runtime status
                    status_data = {
                        "project_id": process_info.project_id,
                        "status": "running",
                        "process_id": process_info.pid,
                        "process_name": process_info.name,
                        "cpu_usage": process_info.cpu_percent,
                        "memory_usage": process_info.memory_percent,
                        "ports": process_info.ports,
                        "last_seen": datetime.utcnow(),
                        "process_metadata": {
                            "cmdline": process_info.cmdline[:5],  # First 5 args
                            "cwd": process_info.cwd,
                            "memory_rss": process_info.memory_rss,
                            "create_time": process_info.create_time
                        }
                    }
                    
                    # Use upsert to handle existing records
                    stmt = insert(RuntimeStatus).values(**status_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['project_id', 'process_id'],
                        set_=dict(
                            status=stmt.excluded.status,
                            cpu_usage=stmt.excluded.cpu_usage,
                            memory_usage=stmt.excluded.memory_usage,
                            ports=stmt.excluded.ports,
                            last_seen=stmt.excluded.last_seen,
                            process_metadata=stmt.excluded.process_metadata
                        )
                    )
                    
                    await self.session.execute(stmt)
            
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Error storing process status: {e}")
            await self.session.rollback()
    
    async def get_project_runtime_status(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive runtime status for a specific project."""
        try:
            # Get database records
            stmt = select(RuntimeStatus).where(RuntimeStatus.project_id == project_id)
            result = await self.session.execute(stmt)
            db_statuses = result.scalars().all()
            
            # Get live process information
            live_processes = [p for p in self.known_processes.values() if p.project_id == project_id]
            live_services = [s for s in self.known_services.values() if s.project_path and project_id in self.project_mapping.get(s.project_path, '')]
            live_containers = [c for c in self.known_containers.values() if c.project_path and project_id in self.project_mapping.get(c.project_path, '')]
            
            # Compile status
            status = {
                "project_id": project_id,
                "is_running": len(live_processes) > 0,
                "processes": [
                    {
                        "pid": p.pid,
                        "name": p.name,
                        "status": p.status,
                        "cpu_percent": p.cpu_percent,
                        "memory_percent": p.memory_percent,
                        "ports": p.ports,
                        "cwd": p.cwd
                    } for p in live_processes
                ],
                "services": [
                    {
                        "name": s.name,
                        "host": s.host,
                        "port": s.port,
                        "status": s.status,
                        "response_time_ms": s.response_time_ms
                    } for s in live_services
                ],
                "containers": [
                    {
                        "id": c.id[:12],  # Short ID
                        "name": c.name,
                        "image": c.image,
                        "status": c.status,
                        "ports": c.ports
                    } for c in live_containers
                ],
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting runtime status for project {project_id}: {e}")
            return {
                "project_id": project_id,
                "is_running": False,
                "error": str(e),
                "last_update": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide runtime overview."""
        try:
            # Collect current metrics
            metrics = await self.collect_system_metrics()
            
            # Summarize running projects
            active_projects = set()
            for proc in self.known_processes.values():
                if proc.project_id:
                    active_projects.add(proc.project_id)
            
            # Service summary
            service_summary = defaultdict(int)
            for service in self.known_services.values():
                if service.status == "active":
                    service_summary["active"] += 1
                else:
                    service_summary["inactive"] += 1
            
            overview = {
                "timestamp": metrics.timestamp.isoformat(),
                "system": {
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": metrics.memory_percent,
                    "disk_percent": metrics.disk_usage_percent,
                    "load_average": metrics.load_average,
                    "total_processes": metrics.processes_count,
                    "network_connections": metrics.active_connections
                },
                "projects": {
                    "total_tracked": len(self.project_mapping),
                    "currently_active": len(active_projects),
                    "active_project_ids": list(active_projects)
                },
                "processes": {
                    "development_processes": len(self.known_processes),
                    "by_language": self._summarize_processes_by_language()
                },
                "services": {
                    "total_discovered": len(self.known_services),
                    "active": service_summary["active"],
                    "inactive": service_summary.get("inactive", 0),
                    "common_ports": list(set(s.port for s in self.known_services.values()))
                },
                "containers": {
                    "total": len(self.known_containers),
                    "running": len([c for c in self.known_containers.values() if c.status == "running"]),
                    "stopped": len([c for c in self.known_containers.values() if c.status != "running"])
                }
            }
            
            return overview
            
        except Exception as e:
            logger.error(f"Error generating system overview: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _summarize_processes_by_language(self) -> Dict[str, int]:
        """Summarize processes by detected programming language."""
        language_counts = defaultdict(int)
        
        for proc in self.known_processes.values():
            cmdline_str = ' '.join(proc.cmdline).lower()
            
            # Simple language detection based on command line
            if 'python' in cmdline_str or 'python3' in cmdline_str:
                language_counts['python'] += 1
            elif 'node' in cmdline_str or 'npm' in cmdline_str:
                language_counts['javascript'] += 1
            elif 'cargo' in cmdline_str or 'rust' in cmdline_str:
                language_counts['rust'] += 1
            elif 'java' in cmdline_str or 'mvn' in cmdline_str:
                language_counts['java'] += 1
            elif 'go run' in cmdline_str:
                language_counts['go'] += 1
            elif 'php' in cmdline_str:
                language_counts['php'] += 1
            elif 'ruby' in cmdline_str or 'rails' in cmdline_str:
                language_counts['ruby'] += 1
            else:
                language_counts['other'] += 1
        
        return dict(language_counts)
    
    async def continuous_monitoring(self, interval_seconds: int = 30) -> None:
        """Run continuous monitoring loop."""
        logger.info(f"Starting continuous runtime monitoring (interval: {interval_seconds}s)")
        
        try:
            while True:
                start_time = time.time()
                
                # Refresh project mappings periodically
                if len(self.known_processes) % 20 == 0:  # Every 20 cycles
                    await self._load_project_mappings()
                
                # Scan for changes
                await self.scan_processes()
                await self.scan_services()
                
                if self.docker_client:
                    await self.scan_containers()
                
                # Store metrics in memory system
                if self.memory:
                    await self._store_monitoring_data_in_memory()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval_seconds - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            logger.info("Runtime monitoring stopped")
        except Exception as e:
            logger.error(f"Error in continuous monitoring: {e}", exc_info=True)
    
    async def _store_monitoring_data_in_memory(self) -> None:
        """Store monitoring data in memory system for learning."""
        try:
            if not self.memory:
                return
            
            # Create summary of current state
            monitoring_context = {
                "type": "runtime_monitoring",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_processes": len(self.known_processes),
                "active_services": len([s for s in self.known_services.values() if s.status == "active"]),
                "active_containers": len([c for c in self.known_containers.values() if c.status == "running"]),
                "system_metrics": (await self.collect_system_metrics()).__dict__,
                "project_activity": {
                    proj_id: len([p for p in self.known_processes.values() if p.project_id == proj_id])
                    for proj_id in set(p.project_id for p in self.known_processes.values() if p.project_id)
                },
                "performance_alerts": len(getattr(self, 'recent_alerts', {})),
                "memory_leaks": len(await self.detect_memory_leaks()) if hasattr(self, 'detect_memory_leaks') else 0
            }
            
            await self.memory.store_context("runtime_monitoring", monitoring_context)
            
        except Exception as e:
            logger.debug(f"Error storing monitoring data in memory: {e}")
    
    async def detect_memory_leaks(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Detect potential memory leaks in running processes."""
        memory_leaks = []
        
        try:
            processes_to_check = [
                p for p in self.known_processes.values()
                if not project_id or p.project_id == project_id
            ]
            
            for process in processes_to_check:
                history = getattr(self, 'process_history', {}).get(process.pid, [])
                
                if len(history) < 20:  # Need at least 10 minutes of data
                    continue
                
                # Analyze memory usage trend over last 20 data points
                recent_memory = [p.memory_rss for p in history[-20:]]
                memory_trend = self._calculate_trend(recent_memory)
                
                # Check for consistent memory growth
                if (memory_trend.get('significant') and 
                    memory_trend.get('direction') == 'increasing' and
                    memory_trend.get('confidence', 0) > 0.8):
                    
                    # Calculate growth rate per minute
                    time_span_minutes = 10  # 20 data points over 10 minutes
                    growth_per_minute = memory_trend.get('rate', 0) * 6  # Convert to per-minute
                    
                    if growth_per_minute > 1024 * 1024:  # Growing by more than 1MB per minute
                        current_mb = process.memory_rss / (1024 * 1024)
                        growth_mb_per_min = growth_per_minute / (1024 * 1024)
                        
                        memory_leaks.append({
                            'project_id': process.project_id,
                            'process_name': process.name,
                            'pid': process.pid,
                            'current_memory_mb': current_mb,
                            'growth_mb_per_minute': growth_mb_per_min,
                            'confidence': memory_trend['confidence'],
                            'duration_minutes': time_span_minutes,
                            'cmdline': process.cmdline[:3]
                        })
            
            return memory_leaks
            
        except Exception as e:
            logger.error(f"Error detecting memory leaks: {e}")
            return memory_leaks
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and significance for a series of values."""
        if len(values) < 3:
            return {'significant': False}
        
        # Simple linear regression to find trend
        x = list(range(len(values)))
        n = len(values)
        
        # Calculate slope (rate of change)
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return {'significant': False}
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Calculate correlation coefficient for confidence
        mean_x = sum_x / n
        mean_y = sum_y / n
        
        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denom_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        denom_y = sum((values[i] - mean_y) ** 2 for i in range(n))
        
        if denom_x == 0 or denom_y == 0:
            correlation = 0
        else:
            correlation = numerator / (denom_x * denom_y) ** 0.5
        
        # Determine if trend is significant
        significant = abs(correlation) > 0.7 and abs(slope) > 0.1
        
        if not significant:
            return {'significant': False}
        
        direction = 'increasing' if slope > 0 else 'decreasing'
        confidence = abs(correlation)
        
        return {
            'significant': True,
            'direction': direction,
            'rate': abs(slope),
            'confidence': confidence
        }