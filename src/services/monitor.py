"""
Runtime monitor service for tracking running processes and resource usage.
Uses psutil to detect and monitor project processes.
"""

import asyncio
import logging
import platform
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any

import psutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..models import Project, RuntimeStatus


logger = logging.getLogger("optimus.monitor")


class RuntimeMonitor:
    """Monitor running processes and their resource consumption."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        
        # Common development server patterns
        self.dev_server_patterns = {
            "python": [
                r"python.*manage\.py.*runserver",  # Django
                r"python.*app\.py",                # Flask
                r"uvicorn.*",                      # FastAPI/ASGI
                r"gunicorn.*",                     # WSGI
                r"streamlit.*run",                 # Streamlit
                r"jupyter.*",                      # Jupyter
                r"python.*-m.*flask",              # Flask CLI
                r"python.*-m.*django",             # Django CLI
            ],
            "nodejs": [
                r"node.*server\.js",               # Express
                r"npm.*start",                     # NPM scripts
                r"yarn.*start",                    # Yarn scripts
                r"next.*dev",                      # Next.js dev
                r"nuxt.*dev",                      # Nuxt.js dev
                r"vue-cli-service.*serve",         # Vue CLI
                r"ng.*serve",                      # Angular CLI
                r"nodemon.*",                      # Nodemon
            ],
            "go": [
                r"go.*run.*main\.go",              # Go run
                r"\.\/.*",                         # Compiled binary
            ],
            "rust": [
                r"cargo.*run",                     # Cargo run
                r"target/debug/.*",                # Debug binary
                r"target/release/.*",              # Release binary
            ],
            "java": [
                r"java.*-jar.*",                   # JAR execution
                r"mvn.*spring-boot:run",           # Maven Spring Boot
                r"gradle.*bootRun",                # Gradle Spring Boot
                r"./gradlew.*bootRun",             # Gradle wrapper
            ],
            "other": [
                r"docker-compose.*up",            # Docker Compose
                r"docker.*run.*",                  # Docker
                r".*webpack.*serve",               # Webpack dev server
                r".*parcel.*",                     # Parcel bundler
                r".*vite.*",                       # Vite dev server
            ]
        }
        
        # Port ranges commonly used for development
        self.common_dev_ports = range(3000, 9000)
    
    async def scan_running_processes(self) -> List[Dict[str, Any]]:
        """Scan all running processes and identify project-related ones."""
        logger.info("Scanning running processes...")
        
        project_processes = []
        
        try:
            # Get all projects from database
            stmt = select(Project).where(Project.status.in_(["active", "discovered"]))
            result = await self.session.execute(stmt)
            projects = result.scalars().all()
            
            # Create mapping of paths to projects
            project_path_map = {project.path: project for project in projects}
            
            # Scan all running processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd', 'create_time']):
                try:
                    process_info = proc.info
                    if not process_info['cmdline']:
                        continue
                    
                    cmdline = ' '.join(process_info['cmdline'])
                    working_dir = process_info.get('cwd', '')
                    
                    # Try to match process to project
                    matched_project = await self._match_process_to_project(
                        cmdline, working_dir, project_path_map
                    )
                    
                    if matched_project:
                        process_data = await self._extract_process_data(proc, matched_project)
                        if process_data:
                            project_processes.append(process_data)
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.debug(f"Error processing process {proc.pid}: {e}")
                    
        except Exception as e:
            logger.error(f"Error scanning processes: {e}", exc_info=True)
        
        logger.info(f"Found {len(project_processes)} project-related processes")
        return project_processes
    
    async def _match_process_to_project(
        self, 
        cmdline: str, 
        working_dir: str, 
        project_path_map: Dict[str, Project]
    ) -> Optional[Project]:
        """Match a process to a project based on command line and working directory."""
        
        # First, try to match by working directory
        for project_path, project in project_path_map.items():
            if working_dir.startswith(project_path):
                return project
        
        # Then, try to match by command line patterns
        for project_path, project in project_path_map.items():
            if project_path in cmdline:
                return project
        
        # Finally, try pattern matching based on tech stack
        for project_path, project in project_path_map.items():
            tech_stack = project.tech_stack or {}
            language = tech_stack.get("language", "")
            
            patterns = self.dev_server_patterns.get(language, [])
            patterns.extend(self.dev_server_patterns.get("other", []))
            
            for pattern in patterns:
                if re.search(pattern, cmdline, re.IGNORECASE):
                    # Additional check: does the command reference the project directory?
                    if (project_path in cmdline or 
                        working_dir.startswith(project_path) or
                        any(part in project_path for part in cmdline.split())):
                        return project
        
        return None
    
    async def _extract_process_data(self, proc: psutil.Process, project: Project) -> Optional[Dict[str, Any]]:
        """Extract detailed information about a process."""
        try:
            # Get basic process info
            with proc.oneshot():
                pid = proc.pid
                name = proc.name()
                cmdline = ' '.join(proc.cmdline())
                create_time = datetime.fromtimestamp(proc.create_time())
                
                # Get resource usage
                cpu_percent = proc.cpu_percent(interval=None)
                memory_info = proc.memory_info()
                memory_usage = memory_info.rss  # Resident Set Size
                
                # Try to get network connections (port info)
                port = await self._get_process_port(proc)
                
                # Determine process status
                status = self._determine_process_status(proc)
                
                return {
                    "project_id": project.id,
                    "process_name": name,
                    "pid": pid,
                    "port": port,
                    "status": status,
                    "cpu_usage": cpu_percent,
                    "memory_usage": memory_usage,
                    "started_at": create_time,
                    "cmdline": cmdline,
                    "last_heartbeat": datetime.utcnow(),
                }
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
        except Exception as e:
            logger.debug(f"Error extracting process data for PID {proc.pid}: {e}")
            return None
    
    async def _get_process_port(self, proc: psutil.Process) -> Optional[int]:
        """Try to determine the port a process is listening on."""
        try:
            connections = proc.connections()
            for conn in connections:
                if (conn.status == psutil.CONN_LISTEN and 
                    conn.laddr and 
                    conn.laddr.port in self.common_dev_ports):
                    return conn.laddr.port
                    
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        except Exception as e:
            logger.debug(f"Error getting port for process {proc.pid}: {e}")
        
        return None
    
    def _determine_process_status(self, proc: psutil.Process) -> str:
        """Determine the status of a process."""
        try:
            psutil_status = proc.status()
            
            # Map psutil status to our status
            status_map = {
                psutil.STATUS_RUNNING: "running",
                psutil.STATUS_SLEEPING: "running",  # Often sleeping but considered running
                psutil.STATUS_DISK_SLEEP: "running",
                psutil.STATUS_STOPPED: "stopped",
                psutil.STATUS_ZOMBIE: "crashed",
                psutil.STATUS_DEAD: "stopped",
            }
            
            return status_map.get(psutil_status, "running")
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "stopped"
    
    async def update_runtime_status(self, process_data: List[Dict[str, Any]]) -> None:
        """Update runtime status table with current process data."""
        try:
            # Get current runtime statuses
            stmt = select(RuntimeStatus).options(selectinload(RuntimeStatus.project))
            result = await self.session.execute(stmt)
            current_statuses = {(rs.project_id, rs.pid): rs for rs in result.scalars().all()}
            
            updated_pids = set()
            
            # Update or create runtime status records
            for proc_data in process_data:
                project_id = proc_data["project_id"]
                pid = proc_data["pid"]
                key = (project_id, pid)
                
                updated_pids.add(key)
                
                if key in current_statuses:
                    # Update existing record
                    runtime_status = current_statuses[key]
                    runtime_status.status = proc_data["status"]
                    runtime_status.cpu_usage = proc_data["cpu_usage"]
                    runtime_status.memory_usage = proc_data["memory_usage"]
                    runtime_status.last_heartbeat = proc_data["last_heartbeat"]
                    runtime_status.port = proc_data.get("port")
                    
                else:
                    # Create new record
                    runtime_status = RuntimeStatus(
                        project_id=project_id,
                        process_name=proc_data["process_name"],
                        pid=pid,
                        port=proc_data.get("port"),
                        status=proc_data["status"],
                        cpu_usage=proc_data["cpu_usage"],
                        memory_usage=proc_data["memory_usage"],
                        started_at=proc_data["started_at"],
                        last_heartbeat=proc_data["last_heartbeat"],
                    )
                    self.session.add(runtime_status)
            
            # Mark processes as stopped if they're no longer running
            stale_threshold = datetime.utcnow() - timedelta(seconds=self.settings.heartbeat_threshold)
            
            for key, runtime_status in current_statuses.items():
                if (key not in updated_pids and 
                    runtime_status.status in ("running", "starting") and
                    runtime_status.last_heartbeat < stale_threshold):
                    
                    runtime_status.status = "stopped"
                    runtime_status.stopped_at = datetime.utcnow()
                    logger.info(f"Marked process {runtime_status.pid} as stopped (stale)")
            
            await self.session.commit()
            logger.debug(f"Updated runtime status for {len(process_data)} processes")
            
        except Exception as e:
            logger.error(f"Error updating runtime status: {e}", exc_info=True)
            await self.session.rollback()
    
    async def cleanup_old_records(self) -> None:
        """Clean up old runtime status records."""
        try:
            # Remove records older than 24 hours for stopped processes
            cleanup_threshold = datetime.utcnow() - timedelta(hours=24)
            
            stmt = delete(RuntimeStatus).where(
                RuntimeStatus.status == "stopped",
                RuntimeStatus.stopped_at < cleanup_threshold
            )
            
            result = await self.session.execute(stmt)
            deleted_count = result.rowcount
            
            await self.session.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old runtime status records")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            await self.session.rollback()
    
    async def get_project_runtime_summary(self, project_id: str) -> Dict[str, Any]:
        """Get runtime summary for a specific project."""
        try:
            stmt = select(RuntimeStatus).where(
                RuntimeStatus.project_id == project_id,
                RuntimeStatus.status.in_(["running", "starting"])
            )
            result = await self.session.execute(stmt)
            running_processes = result.scalars().all()
            
            total_cpu = sum(rs.cpu_usage or 0 for rs in running_processes)
            total_memory = sum(rs.memory_usage or 0 for rs in running_processes)
            ports = [rs.port for rs in running_processes if rs.port]
            
            return {
                "is_running": len(running_processes) > 0,
                "process_count": len(running_processes),
                "total_cpu_usage": total_cpu,
                "total_memory_usage": total_memory,
                "memory_usage_mb": total_memory / (1024 * 1024) if total_memory else 0,
                "ports": ports,
                "processes": [
                    {
                        "pid": rs.pid,
                        "name": rs.process_name,
                        "status": rs.status,
                        "cpu_usage": rs.cpu_usage,
                        "memory_usage_mb": rs.memory_usage / (1024 * 1024) if rs.memory_usage else 0,
                        "port": rs.port,
                        "started_at": rs.started_at,
                        "last_heartbeat": rs.last_heartbeat,
                    }
                    for rs in running_processes
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting runtime summary for project {project_id}: {e}")
            return {
                "is_running": False,
                "process_count": 0,
                "total_cpu_usage": 0,
                "total_memory_usage": 0,
                "memory_usage_mb": 0,
                "ports": [],
                "processes": []
            }
    
    async def monitor_cycle(self) -> Dict[str, Any]:
        """Perform a complete monitoring cycle."""
        start_time = datetime.utcnow()
        
        try:
            # Scan running processes
            process_data = await self.scan_running_processes()
            
            # Update runtime status
            await self.update_runtime_status(process_data)
            
            # Cleanup old records
            await self.cleanup_old_records()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            summary = {
                "timestamp": end_time,
                "duration_seconds": duration,
                "processes_found": len(process_data),
                "status": "success"
            }
            
            logger.info(f"Monitor cycle completed in {duration:.2f}s, found {len(process_data)} processes")
            return summary
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"Monitor cycle failed after {duration:.2f}s: {e}", exc_info=True)
            
            return {
                "timestamp": end_time,
                "duration_seconds": duration,
                "processes_found": 0,
                "status": "error",
                "error": str(e)
            }
    
    async def start_monitoring(self, interval: Optional[int] = None) -> None:
        """Start continuous monitoring (for use in background tasks)."""
        monitor_interval = interval or self.settings.monitor_interval
        
        logger.info(f"Starting runtime monitoring with {monitor_interval}s interval")
        
        while True:
            try:
                await self.monitor_cycle()
                await asyncio.sleep(monitor_interval)
                
            except asyncio.CancelledError:
                logger.info("Runtime monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(monitor_interval)