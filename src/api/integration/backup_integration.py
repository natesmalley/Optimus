"""
Backup Integration Layer
Connects backup services and management to the API.
"""

import asyncio
import os
import shutil
import tarfile
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..websocket_manager import websocket_manager, Channel
from ...config import get_settings, logger


class BackupType(str, Enum):
    """Backup types."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    DATABASE = "database"
    FILES = "files"
    CONFIG = "config"


class BackupStatus(str, Enum):
    """Backup status values."""
    SCHEDULED = "scheduled"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VERIFYING = "verifying"
    VERIFIED = "verified"


class BackupRequest(BaseModel):
    """Backup request model."""
    project_id: Optional[str] = None
    backup_type: BackupType
    include_patterns: List[str] = ["*"]
    exclude_patterns: List[str] = []
    compression: bool = True
    encryption: bool = False
    retention_days: int = 30
    destination: Optional[str] = None
    user_id: Optional[str] = None
    notes: Optional[str] = None
    schedule: Optional[str] = None  # cron expression


class BackupInfo(BaseModel):
    """Backup information model."""
    backup_id: str
    project_id: Optional[str]
    backup_type: BackupType
    status: BackupStatus
    size_bytes: Optional[int] = None
    compressed_size_bytes: Optional[int] = None
    file_count: Optional[int] = None
    source_path: Optional[str] = None
    destination_path: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    created_by: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None


class RestoreRequest(BaseModel):
    """Restore request model."""
    backup_id: str
    destination_path: Optional[str] = None
    overwrite_existing: bool = False
    restore_permissions: bool = True
    user_id: Optional[str] = None


class RestoreInfo(BaseModel):
    """Restore operation information."""
    restore_id: str
    backup_id: str
    status: str  # pending, running, completed, failed
    destination_path: str
    files_restored: int = 0
    bytes_restored: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class BackupSchedule(BaseModel):
    """Backup schedule configuration."""
    schedule_id: str
    project_id: Optional[str]
    backup_type: BackupType
    cron_expression: str
    enabled: bool = True
    retain_count: int = 10
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    created_at: datetime


class BackupStats(BaseModel):
    """Backup statistics."""
    total_backups: int
    active_backups: int
    completed_backups: int
    failed_backups: int
    total_size_gb: float
    average_backup_time: float
    success_rate: float
    storage_usage_gb: float
    oldest_backup: Optional[datetime] = None
    newest_backup: Optional[datetime] = None


class BackupIntegration:
    """Integration layer for backup management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.backup_root = Path(self.settings.projects_base_path) / ".optimus" / "backups"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        self.active_backups: Dict[str, BackupInfo] = {}
        self.backup_history: List[BackupInfo] = []
        self.active_restores: Dict[str, RestoreInfo] = {}
        self.backup_schedules: Dict[str, BackupSchedule] = {}
        
        # Statistics
        self.stats = {
            "total_backups": 0,
            "active_backups": 0,
            "completed_backups": 0,
            "failed_backups": 0,
            "backup_times": [],
            "total_size": 0,
            "storage_used": 0
        }
    
    async def submit_backup_request(self, request: BackupRequest) -> str:
        """Submit a backup request."""
        import uuid
        backup_id = str(uuid.uuid4())
        
        # Create backup info
        backup_info = BackupInfo(
            backup_id=backup_id,
            project_id=request.project_id,
            backup_type=request.backup_type,
            status=BackupStatus.PENDING,
            created_at=datetime.now(),
            created_by=request.user_id,
            metadata={
                "include_patterns": request.include_patterns,
                "exclude_patterns": request.exclude_patterns,
                "compression": request.compression,
                "encryption": request.encryption,
                "retention_days": request.retention_days,
                "destination": request.destination,
                "notes": request.notes
            }
        )
        
        self.active_backups[backup_id] = backup_info
        self.stats["total_backups"] += 1
        self.stats["active_backups"] += 1
        
        # Start backup in background
        asyncio.create_task(self._execute_backup(backup_id, request))
        
        # Broadcast backup started
        await self._broadcast_backup_update({
            "backup_id": backup_id,
            "type": "backup_submitted",
            "status": backup_info.status.value,
            "project_id": request.project_id,
            "backup_type": request.backup_type.value
        })
        
        logger.info(f"Backup submitted: {backup_id} for project {request.project_id}")
        return backup_id
    
    async def _execute_backup(self, backup_id: str, request: BackupRequest):
        """Execute backup operation."""
        backup_info = self.active_backups[backup_id]
        
        try:
            backup_info.status = BackupStatus.RUNNING
            backup_info.started_at = datetime.now()
            
            # Determine source path
            if request.project_id:
                source_path = Path(self.settings.projects_base_path) / request.project_id
            else:
                source_path = Path(self.settings.projects_base_path)
            
            if not source_path.exists():
                raise FileNotFoundError(f"Source path not found: {source_path}")
            
            backup_info.source_path = str(source_path)
            
            # Determine destination path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{request.backup_type.value}_{backup_id[:8]}_{timestamp}"
            if request.compression:
                backup_name += ".tar.gz"
            else:
                backup_name += ".tar"
            
            destination_path = self.backup_root / backup_name
            backup_info.destination_path = str(destination_path)
            
            await self._broadcast_backup_update({
                "backup_id": backup_id,
                "type": "backup_started",
                "status": backup_info.status.value,
                "source_path": str(source_path),
                "destination_path": str(destination_path)
            })
            
            # Perform backup based on type
            if request.backup_type == BackupType.FULL:
                await self._create_full_backup(source_path, destination_path, request)
            elif request.backup_type == BackupType.FILES:
                await self._create_files_backup(source_path, destination_path, request)
            elif request.backup_type == BackupType.DATABASE:
                await self._create_database_backup(destination_path, request)
            elif request.backup_type == BackupType.CONFIG:
                await self._create_config_backup(source_path, destination_path, request)
            else:
                raise ValueError(f"Backup type not implemented: {request.backup_type}")
            
            # Verify backup
            backup_info.status = BackupStatus.VERIFYING
            await self._verify_backup(destination_path, backup_info)
            
            backup_info.status = BackupStatus.VERIFIED
            backup_info.completed_at = datetime.now()
            
            if backup_info.started_at:
                duration = (backup_info.completed_at - backup_info.started_at).total_seconds()
                backup_info.duration_seconds = duration
                self.stats["backup_times"].append(duration)
            
            # Get final backup size
            if destination_path.exists():
                backup_info.compressed_size_bytes = destination_path.stat().st_size
                self.stats["total_size"] += backup_info.compressed_size_bytes
                self.stats["storage_used"] += backup_info.compressed_size_bytes
            
            self.stats["completed_backups"] += 1
            
            await self._broadcast_backup_update({
                "backup_id": backup_id,
                "type": "backup_completed",
                "status": backup_info.status.value,
                "size_bytes": backup_info.size_bytes,
                "compressed_size_bytes": backup_info.compressed_size_bytes,
                "duration_seconds": backup_info.duration_seconds
            })
            
            logger.info(f"Backup completed: {backup_id}")
            
        except Exception as e:
            backup_info.status = BackupStatus.FAILED
            backup_info.error = str(e)
            backup_info.completed_at = datetime.now()
            self.stats["failed_backups"] += 1
            
            await self._broadcast_backup_update({
                "backup_id": backup_id,
                "type": "backup_failed",
                "status": backup_info.status.value,
                "error": str(e)
            })
            
            logger.error(f"Backup failed: {backup_id} - {e}")
        
        finally:
            # Move to history
            self.active_backups.pop(backup_id, None)
            self.stats["active_backups"] -= 1
            self.backup_history.append(backup_info)
            
            # Keep only last 1000 backups in memory
            if len(self.backup_history) > 1000:
                self.backup_history = self.backup_history[-1000:]
    
    async def _create_full_backup(self, source_path: Path, destination_path: Path, 
                                 request: BackupRequest):
        """Create a full backup."""
        exclude_patterns = set(request.exclude_patterns)
        exclude_patterns.update({
            "*.pyc", "__pycache__", ".git", "node_modules", ".env",
            "*.log", "*.tmp", ".DS_Store"
        })
        
        mode = "w:gz" if request.compression else "w"
        
        with tarfile.open(destination_path, mode) as tar:
            def filter_func(tarinfo):
                # Apply exclude patterns
                for pattern in exclude_patterns:
                    if pattern in tarinfo.name:
                        return None
                return tarinfo
            
            tar.add(source_path, arcname=source_path.name, filter=filter_func)
        
        # Calculate original size
        total_size = 0
        file_count = 0
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.exists():
                    total_size += file_path.stat().st_size
                    file_count += 1
        
        backup_info = self.active_backups[destination_path.stem.split('_')[1]]  # Extract backup_id
        backup_info.size_bytes = total_size
        backup_info.file_count = file_count
    
    async def _create_files_backup(self, source_path: Path, destination_path: Path,
                                  request: BackupRequest):
        """Create a files-only backup."""
        # Similar to full backup but with more selective file inclusion
        await self._create_full_backup(source_path, destination_path, request)
    
    async def _create_database_backup(self, destination_path: Path, request: BackupRequest):
        """Create a database backup."""
        # This is a placeholder - implement actual database backup logic
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "database",
            "tables": ["projects", "runtime", "metrics"],  # Example tables
            "note": "Database backup placeholder"
        }
        
        with open(destination_path.with_suffix(".json"), 'w') as f:
            json.dump(backup_data, f, indent=2)
    
    async def _create_config_backup(self, source_path: Path, destination_path: Path,
                                   request: BackupRequest):
        """Create a configuration files backup."""
        config_patterns = ["*.conf", "*.ini", "*.yaml", "*.yml", "*.json", ".env*"]
        
        mode = "w:gz" if request.compression else "w"
        
        with tarfile.open(destination_path, mode) as tar:
            for root, dirs, files in os.walk(source_path):
                for file in files:
                    file_path = Path(root) / file
                    if any(file_path.match(pattern) for pattern in config_patterns):
                        tar.add(file_path, arcname=file_path.relative_to(source_path))
    
    async def _verify_backup(self, backup_path: Path, backup_info: BackupInfo):
        """Verify backup integrity."""
        if not backup_path.exists():
            raise FileNotFoundError("Backup file not found")
        
        if backup_path.suffix in ['.gz', '.tar']:
            # Test tar file integrity
            try:
                with tarfile.open(backup_path, 'r') as tar:
                    tar.getmembers()  # This will raise an exception if corrupted
            except Exception as e:
                raise ValueError(f"Backup verification failed: {e}")
        
        # Calculate checksum
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(backup_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        backup_info.checksum = sha256_hash.hexdigest()
    
    async def submit_restore_request(self, request: RestoreRequest) -> str:
        """Submit a restore request."""
        import uuid
        restore_id = str(uuid.uuid4())
        
        # Find backup
        backup_info = await self.get_backup_info(request.backup_id)
        if not backup_info:
            raise ValueError(f"Backup not found: {request.backup_id}")
        
        if backup_info.status != BackupStatus.VERIFIED:
            raise ValueError(f"Backup is not verified: {backup_info.status}")
        
        # Determine destination
        destination_path = request.destination_path or backup_info.source_path
        
        restore_info = RestoreInfo(
            restore_id=restore_id,
            backup_id=request.backup_id,
            status="pending",
            destination_path=destination_path
        )
        
        self.active_restores[restore_id] = restore_info
        
        # Start restore in background
        asyncio.create_task(self._execute_restore(restore_id, request, backup_info))
        
        logger.info(f"Restore submitted: {restore_id} from backup {request.backup_id}")
        return restore_id
    
    async def _execute_restore(self, restore_id: str, request: RestoreRequest,
                              backup_info: BackupInfo):
        """Execute restore operation."""
        restore_info = self.active_restores[restore_id]
        
        try:
            restore_info.status = "running"
            restore_info.started_at = datetime.now()
            
            backup_path = Path(backup_info.destination_path)
            destination_path = Path(restore_info.destination_path)
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Create destination directory if it doesn't exist
            destination_path.mkdir(parents=True, exist_ok=True)
            
            # Extract backup
            with tarfile.open(backup_path, 'r') as tar:
                members = tar.getmembers()
                
                for member in members:
                    target_path = destination_path / member.name
                    
                    # Check for overwrite
                    if target_path.exists() and not request.overwrite_existing:
                        continue
                    
                    tar.extract(member, destination_path)
                    restore_info.files_restored += 1
                    restore_info.bytes_restored += member.size
            
            restore_info.status = "completed"
            restore_info.completed_at = datetime.now()
            
            await self._broadcast_backup_update({
                "restore_id": restore_id,
                "type": "restore_completed",
                "status": restore_info.status,
                "files_restored": restore_info.files_restored,
                "bytes_restored": restore_info.bytes_restored
            })
            
            logger.info(f"Restore completed: {restore_id}")
            
        except Exception as e:
            restore_info.status = "failed"
            restore_info.error = str(e)
            restore_info.completed_at = datetime.now()
            
            logger.error(f"Restore failed: {restore_id} - {e}")
        
        finally:
            # Keep restore info for a while, then clean up
            asyncio.create_task(self._cleanup_restore(restore_id, delay=3600))  # 1 hour
    
    async def _cleanup_restore(self, restore_id: str, delay: int):
        """Clean up restore info after delay."""
        await asyncio.sleep(delay)
        self.active_restores.pop(restore_id, None)
    
    async def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """Get backup information."""
        # Check active backups
        if backup_id in self.active_backups:
            return self.active_backups[backup_id]
        
        # Check history
        for backup in self.backup_history:
            if backup.backup_id == backup_id:
                return backup
        
        return None
    
    async def get_project_backups(self, project_id: str) -> List[BackupInfo]:
        """Get backups for a specific project."""
        backups = []
        
        # Add active backups
        for backup in self.active_backups.values():
            if backup.project_id == project_id:
                backups.append(backup)
        
        # Add historical backups
        for backup in self.backup_history:
            if backup.project_id == project_id:
                backups.append(backup)
        
        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups
    
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        backup_info = await self.get_backup_info(backup_id)
        if not backup_info:
            return False
        
        # Remove file
        if backup_info.destination_path:
            backup_path = Path(backup_info.destination_path)
            if backup_path.exists():
                backup_path.unlink()
                self.stats["storage_used"] -= backup_info.compressed_size_bytes or 0
        
        # Remove from history
        self.backup_history = [
            b for b in self.backup_history 
            if b.backup_id != backup_id
        ]
        
        logger.info(f"Backup deleted: {backup_id}")
        return True
    
    async def cleanup_old_backups(self, retention_days: int = 30):
        """Clean up old backups."""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        backups_to_delete = [
            backup for backup in self.backup_history
            if backup.created_at < cutoff_date
        ]
        
        for backup in backups_to_delete:
            await self.delete_backup(backup.backup_id)
        
        logger.info(f"Cleaned up {len(backups_to_delete)} old backups")
        return len(backups_to_delete)
    
    async def get_backup_statistics(self) -> BackupStats:
        """Get backup statistics."""
        # Calculate success rate
        completed = self.stats["completed_backups"]
        failed = self.stats["failed_backups"]
        total_finished = completed + failed
        success_rate = completed / total_finished if total_finished > 0 else 0
        
        # Calculate average backup time
        times = self.stats["backup_times"]
        avg_time = sum(times) / len(times) if times else 0
        
        # Find oldest and newest backups
        all_backups = list(self.active_backups.values()) + self.backup_history
        oldest = min(all_backups, key=lambda x: x.created_at).created_at if all_backups else None
        newest = max(all_backups, key=lambda x: x.created_at).created_at if all_backups else None
        
        return BackupStats(
            total_backups=self.stats["total_backups"],
            active_backups=self.stats["active_backups"],
            completed_backups=completed,
            failed_backups=failed,
            total_size_gb=self.stats["total_size"] / (1024**3),
            average_backup_time=avg_time,
            success_rate=success_rate,
            storage_usage_gb=self.stats["storage_used"] / (1024**3),
            oldest_backup=oldest,
            newest_backup=newest
        )
    
    async def _broadcast_backup_update(self, data: Dict[str, Any]):
        """Broadcast backup update via WebSocket."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.BACKUP, {
                "type": "backup_update",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting backup update: {e}")
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage information."""
        total_size = 0
        backup_count = 0
        
        # Calculate from backup directory
        for backup_file in self.backup_root.glob("*"):
            if backup_file.is_file():
                total_size += backup_file.stat().st_size
                backup_count += 1
        
        # Get available space
        statvfs = os.statvfs(self.backup_root)
        available_bytes = statvfs.f_frsize * statvfs.f_bavail
        total_disk_bytes = statvfs.f_frsize * statvfs.f_blocks
        
        return {
            "backup_storage_gb": total_size / (1024**3),
            "backup_count": backup_count,
            "available_space_gb": available_bytes / (1024**3),
            "total_disk_space_gb": total_disk_bytes / (1024**3),
            "disk_usage_percent": ((total_disk_bytes - available_bytes) / total_disk_bytes) * 100
        }