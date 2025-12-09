"""
Backup Coordinator Service

Manages project backups including full and incremental backups, database backup support,
file system snapshots, scheduled backups, compression, and encryption.
"""

import asyncio
import os
import subprocess
import logging
import json
import tarfile
import gzip
import shutil
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import psutil
import aiofiles
from croniter import croniter

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Types of backups."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    """Backup operation status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"


class CompressionType(Enum):
    """Compression options for backups."""
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    XZ = "xz"


@dataclass
class BackupMetadata:
    """Metadata for a backup."""
    backup_id: str
    project_id: str
    backup_type: BackupType
    status: BackupStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    size_bytes: Optional[int] = None
    compressed_size_bytes: Optional[int] = None
    file_count: Optional[int] = None
    checksum: Optional[str] = None
    compression: CompressionType = CompressionType.GZIP
    encrypted: bool = False
    parent_backup_id: Optional[str] = None  # For incremental backups
    retention_until: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "backup_id": self.backup_id,
            "project_id": self.project_id,
            "backup_type": self.backup_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "file_count": self.file_count,
            "checksum": self.checksum,
            "compression": self.compression.value,
            "encrypted": self.encrypted,
            "parent_backup_id": self.parent_backup_id,
            "retention_until": self.retention_until.isoformat() if self.retention_until else None,
            "tags": self.tags,
            "notes": self.notes
        }


@dataclass
class Backup:
    """Complete backup information."""
    metadata: BackupMetadata
    files: List[str] = field(default_factory=list)
    excluded_patterns: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    manifest_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            **self.metadata.to_dict(),
            "files": self.files[:100],  # Limit file list in API responses
            "total_files": len(self.files),
            "excluded_patterns": self.excluded_patterns,
            "backup_path": self.backup_path,
            "manifest_path": self.manifest_path
        }


@dataclass
class BackupConfig:
    """Backup configuration for a project."""
    project_id: str
    enabled: bool = True
    backup_type: BackupType = BackupType.INCREMENTAL
    compression: CompressionType = CompressionType.GZIP
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    retention_days: int = 30
    max_backups: int = 50
    include_patterns: List[str] = field(default_factory=lambda: ["**/*"])
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/__pycache__/**",
        "**/node_modules/**",
        "**/.git/**",
        "**/venv/**",
        "**/env/**",
        "**/*.log",
        "**/tmp/**",
        "**/*.tmp"
    ])
    database_backup_enabled: bool = True
    database_connections: List[Dict[str, str]] = field(default_factory=list)
    pre_backup_commands: List[str] = field(default_factory=list)
    post_backup_commands: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "project_id": self.project_id,
            "enabled": self.enabled,
            "backup_type": self.backup_type.value,
            "compression": self.compression.value,
            "encryption_enabled": self.encryption_enabled,
            "retention_days": self.retention_days,
            "max_backups": self.max_backups,
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "database_backup_enabled": self.database_backup_enabled,
            "database_connections": len(self.database_connections),
            "pre_backup_commands": self.pre_backup_commands,
            "post_backup_commands": self.post_backup_commands
        }


@dataclass
class ScheduledJob:
    """Scheduled backup job."""
    job_id: str
    project_id: str
    schedule: str  # Cron expression
    config: BackupConfig
    enabled: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_status: Optional[BackupStatus] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status.value if self.last_status else None,
            "created_at": self.created_at.isoformat(),
            "config": self.config.to_dict()
        }


class BackupCoordinator:
    """
    Coordinates backup operations including full and incremental backups,
    database backups, file system snapshots, and scheduled backup jobs.
    """
    
    def __init__(self, 
                 base_projects_path: str = "/Users/nathanial.smalley/projects",
                 backup_storage_path: str = "/Users/nathanial.smalley/projects/.optimus/backups"):
        """
        Initialize the BackupCoordinator.
        
        Args:
            base_projects_path: Base directory containing all projects
            backup_storage_path: Directory to store backups
        """
        self.base_projects_path = Path(base_projects_path)
        self.backup_storage_path = Path(backup_storage_path)
        self.backup_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Internal state
        self.backups: Dict[str, Backup] = {}  # backup_id -> Backup
        self.configs: Dict[str, BackupConfig] = {}  # project_id -> BackupConfig
        self.scheduled_jobs: Dict[str, ScheduledJob] = {}  # job_id -> ScheduledJob
        self.running_backups: Set[str] = set()
        
        # Configuration
        self.max_concurrent_backups = 3
        self.compression_level = 6
        self.chunk_size = 64 * 1024 * 1024  # 64MB chunks for large files
        
        # Initialize metadata database
        self.metadata_db_path = self.backup_storage_path / "metadata.db"
        asyncio.create_task(self._initialize_metadata_db())
        
        # Start scheduler
        asyncio.create_task(self._backup_scheduler())
        
        logger.info(f"BackupCoordinator initialized - Storage: {self.backup_storage_path}")
    
    async def backup_project(self, project_id: str, incremental: bool = True, tags: Optional[List[str]] = None) -> Backup:
        """
        Create a backup of a project.
        
        Args:
            project_id: Project identifier
            incremental: Whether to create incremental backup
            tags: Optional tags for the backup
            
        Returns:
            Backup: Created backup information
        """
        backup_id = f"backup_{project_id}_{int(datetime.now().timestamp())}"
        logger.info(f"Starting backup {backup_id} for project {project_id} (incremental={incremental})")
        
        try:
            # Check concurrent backup limits
            if len(self.running_backups) >= self.max_concurrent_backups:
                raise RuntimeError(f"Maximum concurrent backups ({self.max_concurrent_backups}) reached")
            
            # Get project path and configuration
            project_path = await self._find_project_path(project_id)
            config = await self._get_backup_config(project_id)
            
            # Determine backup type
            if incremental and config.backup_type == BackupType.INCREMENTAL:
                backup_type = BackupType.INCREMENTAL
                parent_backup = await self._find_latest_backup(project_id)
            else:
                backup_type = BackupType.FULL
                parent_backup = None
            
            # Create backup metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                project_id=project_id,
                backup_type=backup_type,
                status=BackupStatus.PENDING,
                created_at=datetime.now(),
                compression=config.compression,
                encrypted=config.encryption_enabled,
                parent_backup_id=parent_backup.metadata.backup_id if parent_backup else None,
                retention_until=datetime.now() + timedelta(days=config.retention_days),
                tags=tags or []
            )
            
            # Create backup object
            backup = Backup(
                metadata=metadata,
                excluded_patterns=config.exclude_patterns
            )
            
            # Register backup
            self.backups[backup_id] = backup
            self.running_backups.add(backup_id)
            
            # Execute backup
            success = await self._execute_backup(backup, config, project_path, parent_backup)
            
            if success:
                backup.metadata.status = BackupStatus.SUCCESS
                backup.metadata.completed_at = datetime.now()
                
                # Save metadata to database
                await self._save_backup_metadata(backup)
                
                # Cleanup old backups
                await self._cleanup_old_backups(project_id, config)
            else:
                backup.metadata.status = BackupStatus.FAILED
                backup.metadata.completed_at = datetime.now()
            
            # Cleanup
            self.running_backups.discard(backup_id)
            
            logger.info(f"Backup {backup_id} completed with status: {backup.metadata.status.value}")
            return backup
            
        except Exception as e:
            logger.error(f"Backup {backup_id} failed: {str(e)}")
            
            # Update status if backup exists
            if backup_id in self.backups:
                self.backups[backup_id].metadata.status = BackupStatus.FAILED
                self.backups[backup_id].metadata.completed_at = datetime.now()
            
            # Cleanup
            self.running_backups.discard(backup_id)
            
            raise RuntimeError(f"Backup failed: {str(e)}")
    
    async def restore_project(self, backup_id: str, target_path: str, selective_restore: Optional[List[str]] = None) -> bool:
        """
        Restore a project from backup.
        
        Args:
            backup_id: Backup to restore from
            target_path: Target directory for restoration
            selective_restore: Optional list of specific files/directories to restore
            
        Returns:
            bool: True if successfully restored
        """
        logger.info(f"Restoring backup {backup_id} to {target_path}")
        
        try:
            # Get backup information
            backup = await self._get_backup_by_id(backup_id)
            if not backup:
                raise ValueError(f"Backup {backup_id} not found")
            
            if backup.metadata.status != BackupStatus.SUCCESS:
                raise ValueError(f"Cannot restore from backup with status {backup.metadata.status.value}")
            
            # Prepare target directory
            target_path = Path(target_path)
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Execute restore based on backup type
            if backup.metadata.backup_type == BackupType.INCREMENTAL:
                success = await self._restore_incremental(backup, target_path, selective_restore)
            else:
                success = await self._restore_full(backup, target_path, selective_restore)
            
            if success:
                logger.info(f"Successfully restored backup {backup_id} to {target_path}")
                
                # Restore database if available
                await self._restore_databases(backup, target_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Restore failed for backup {backup_id}: {str(e)}")
            return False
    
    async def schedule_backup(self, project_id: str, schedule: str, config: Optional[BackupConfig] = None) -> ScheduledJob:
        """
        Schedule automatic backups for a project.
        
        Args:
            project_id: Project identifier
            schedule: Cron expression for backup schedule
            config: Optional backup configuration
            
        Returns:
            ScheduledJob: Created scheduled job
        """
        job_id = f"job_{project_id}_{int(datetime.now().timestamp())}"
        logger.info(f"Scheduling backup job {job_id} for project {project_id} with schedule: {schedule}")
        
        try:
            # Validate cron expression
            cron = croniter(schedule)
            next_run = cron.get_next(datetime)
            
            # Get configuration
            backup_config = config or await self._get_backup_config(project_id)
            
            # Create scheduled job
            job = ScheduledJob(
                job_id=job_id,
                project_id=project_id,
                schedule=schedule,
                config=backup_config,
                next_run=next_run
            )
            
            # Store job
            self.scheduled_jobs[job_id] = job
            
            # Save to persistent storage
            await self._save_scheduled_job(job)
            
            logger.info(f"Successfully scheduled backup job {job_id}, next run: {next_run}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to schedule backup: {str(e)}")
            raise
    
    async def list_backups(self, project_id: str) -> List[Backup]:
        """
        List all backups for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List[Backup]: List of backups for the project
        """
        try:
            # Load from database if not in memory
            if not any(b.metadata.project_id == project_id for b in self.backups.values()):
                await self._load_project_backups(project_id)
            
            return [b for b in self.backups.values() if b.metadata.project_id == project_id]
            
        except Exception as e:
            logger.error(f"Failed to list backups for {project_id}: {str(e)}")
            return []
    
    async def cleanup_old_backups(self, days: int = 30) -> int:
        """
        Clean up backups older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            int: Number of backups cleaned up
        """
        logger.info(f"Cleaning up backups older than {days} days")
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_count = 0
            
            # Find expired backups
            expired_backups = []
            for backup in self.backups.values():
                if backup.metadata.retention_until and backup.metadata.retention_until < datetime.now():
                    expired_backups.append(backup)
                elif backup.metadata.created_at < cutoff_date:
                    expired_backups.append(backup)
            
            # Delete expired backups
            for backup in expired_backups:
                try:
                    await self._delete_backup_files(backup)
                    await self._delete_backup_metadata(backup.metadata.backup_id)
                    
                    # Remove from memory
                    if backup.metadata.backup_id in self.backups:
                        del self.backups[backup.metadata.backup_id]
                    
                    backup.metadata.status = BackupStatus.EXPIRED
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup.metadata.backup_id}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} expired backups")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {str(e)}")
            return 0
    
    async def get_backup_status(self, backup_id: str) -> Optional[BackupMetadata]:
        """
        Get status of a specific backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Optional[BackupMetadata]: Backup metadata if found
        """
        backup = self.backups.get(backup_id)
        if backup:
            return backup.metadata
        
        # Try loading from database
        backup = await self._get_backup_by_id(backup_id)
        return backup.metadata if backup else None
    
    async def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Verify integrity of a backup.
        
        Args:
            backup_id: Backup to verify
            
        Returns:
            Dict[str, Any]: Verification results
        """
        logger.info(f"Verifying backup {backup_id}")
        
        try:
            backup = await self._get_backup_by_id(backup_id)
            if not backup:
                return {"valid": False, "error": "Backup not found"}
            
            results = {
                "backup_id": backup_id,
                "valid": True,
                "errors": [],
                "warnings": [],
                "checksum_valid": False,
                "files_accessible": False,
                "size_matches": False
            }
            
            # Check if backup files exist
            if backup.backup_path and Path(backup.backup_path).exists():
                results["files_accessible"] = True
                
                # Verify checksum
                if backup.metadata.checksum:
                    calculated_checksum = await self._calculate_file_checksum(backup.backup_path)
                    results["checksum_valid"] = (calculated_checksum == backup.metadata.checksum)
                    
                    if not results["checksum_valid"]:
                        results["valid"] = False
                        results["errors"].append("Checksum verification failed")
                
                # Verify size
                actual_size = Path(backup.backup_path).stat().st_size
                if backup.metadata.compressed_size_bytes:
                    results["size_matches"] = (actual_size == backup.metadata.compressed_size_bytes)
                    
                    if not results["size_matches"]:
                        results["warnings"].append(f"Size mismatch: expected {backup.metadata.compressed_size_bytes}, got {actual_size}")
                
            else:
                results["valid"] = False
                results["errors"].append("Backup files not accessible")
            
            # Verify manifest if exists
            if backup.manifest_path and Path(backup.manifest_path).exists():
                manifest_valid = await self._verify_manifest(backup)
                if not manifest_valid:
                    results["warnings"].append("Manifest verification failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Backup verification failed: {str(e)}")
            return {"valid": False, "error": str(e)}
    
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
    
    async def _get_backup_config(self, project_id: str) -> BackupConfig:
        """Get backup configuration for a project."""
        if project_id in self.configs:
            return self.configs[project_id]
        
        # Try to load from project directory
        try:
            project_path = await self._find_project_path(project_id)
            config_file = project_path / ".optimus" / "backup-config.json"
            
            if config_file.exists():
                async with aiofiles.open(config_file, 'r') as f:
                    config_data = json.loads(await f.read())
                
                config = BackupConfig(
                    project_id=project_id,
                    enabled=config_data.get("enabled", True),
                    backup_type=BackupType(config_data.get("backup_type", "incremental")),
                    compression=CompressionType(config_data.get("compression", "gzip")),
                    encryption_enabled=config_data.get("encryption_enabled", False),
                    retention_days=config_data.get("retention_days", 30),
                    max_backups=config_data.get("max_backups", 50),
                    include_patterns=config_data.get("include_patterns", ["**/*"]),
                    exclude_patterns=config_data.get("exclude_patterns", [
                        "**/__pycache__/**", "**/node_modules/**", "**/.git/**"
                    ])
                )
                
                self.configs[project_id] = config
                return config
        except Exception as e:
            logger.warning(f"Failed to load backup config: {e}")
        
        # Default configuration
        config = BackupConfig(project_id=project_id)
        self.configs[project_id] = config
        return config
    
    async def _find_latest_backup(self, project_id: str) -> Optional[Backup]:
        """Find the most recent successful backup for a project."""
        project_backups = [
            b for b in self.backups.values()
            if b.metadata.project_id == project_id
            and b.metadata.status == BackupStatus.SUCCESS
        ]
        
        if not project_backups:
            # Try loading from database
            await self._load_project_backups(project_id)
            project_backups = [
                b for b in self.backups.values()
                if b.metadata.project_id == project_id
                and b.metadata.status == BackupStatus.SUCCESS
            ]
        
        if not project_backups:
            return None
        
        return max(project_backups, key=lambda b: b.metadata.created_at)
    
    async def _execute_backup(self, backup: Backup, config: BackupConfig, project_path: Path, parent_backup: Optional[Backup]) -> bool:
        """Execute the actual backup operation."""
        try:
            backup.metadata.status = BackupStatus.RUNNING
            
            # Execute pre-backup commands
            for command in config.pre_backup_commands:
                await self._run_command(command.split(), cwd=project_path)
            
            # Create backup directory
            backup_dir = self.backup_storage_path / backup.metadata.backup_id
            backup_dir.mkdir(exist_ok=True)
            
            # Collect files to backup
            files_to_backup = await self._collect_files(project_path, config, parent_backup)
            backup.files = files_to_backup
            
            # Create manifest
            manifest_path = backup_dir / "manifest.json"
            await self._create_manifest(backup, manifest_path)
            backup.manifest_path = str(manifest_path)
            
            # Create backup archive
            backup_archive = backup_dir / f"backup.{config.compression.value}"
            await self._create_backup_archive(files_to_backup, project_path, backup_archive, config)
            backup.backup_path = str(backup_archive)
            
            # Calculate checksums and sizes
            backup.metadata.size_bytes = sum(Path(project_path / f).stat().st_size for f in files_to_backup if (project_path / f).exists())
            backup.metadata.compressed_size_bytes = backup_archive.stat().st_size
            backup.metadata.file_count = len(files_to_backup)
            backup.metadata.checksum = await self._calculate_file_checksum(str(backup_archive))
            
            # Backup databases
            if config.database_backup_enabled:
                await self._backup_databases(backup, config, backup_dir)
            
            # Execute post-backup commands
            for command in config.post_backup_commands:
                await self._run_command(command.split(), cwd=project_path)
            
            logger.info(f"Backup completed: {backup.metadata.file_count} files, {backup.metadata.size_bytes} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Backup execution failed: {str(e)}")
            return False
    
    async def _collect_files(self, project_path: Path, config: BackupConfig, parent_backup: Optional[Backup]) -> List[str]:
        """Collect files to be included in the backup."""
        files_to_backup = []
        
        # Get all files matching include patterns
        import fnmatch
        
        for pattern in config.include_patterns:
            if pattern.startswith("**/"):
                # Recursive pattern
                for file_path in project_path.rglob(pattern[3:]):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(project_path)
                        files_to_backup.append(str(relative_path))
            else:
                for file_path in project_path.glob(pattern):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(project_path)
                        files_to_backup.append(str(relative_path))
        
        # Remove files matching exclude patterns
        filtered_files = []
        for file_path in files_to_backup:
            excluded = False
            for exclude_pattern in config.exclude_patterns:
                if fnmatch.fnmatch(file_path, exclude_pattern) or fnmatch.fnmatch(f"**/{file_path}", exclude_pattern):
                    excluded = True
                    break
            
            if not excluded:
                filtered_files.append(file_path)
        
        # For incremental backups, only include changed files
        if parent_backup and config.backup_type == BackupType.INCREMENTAL:
            changed_files = await self._find_changed_files(filtered_files, project_path, parent_backup)
            return changed_files
        
        return filtered_files
    
    async def _find_changed_files(self, files: List[str], project_path: Path, parent_backup: Backup) -> List[str]:
        """Find files that have changed since the parent backup."""
        if not parent_backup.manifest_path or not Path(parent_backup.manifest_path).exists():
            return files  # If no parent manifest, include all files
        
        # Load parent manifest
        async with aiofiles.open(parent_backup.manifest_path, 'r') as f:
            parent_manifest = json.loads(await f.read())
        
        parent_files = {item["path"]: item for item in parent_manifest.get("files", [])}
        
        changed_files = []
        for file_path in files:
            full_path = project_path / file_path
            
            if not full_path.exists():
                continue
            
            # Check if file is new or modified
            if file_path not in parent_files:
                changed_files.append(file_path)  # New file
            else:
                # Check modification time and size
                stat = full_path.stat()
                parent_stat = parent_files[file_path]
                
                if (stat.st_mtime > parent_stat.get("mtime", 0) or
                    stat.st_size != parent_stat.get("size", 0)):
                    changed_files.append(file_path)  # Modified file
        
        logger.info(f"Incremental backup: {len(changed_files)} changed files out of {len(files)} total")
        return changed_files
    
    async def _create_manifest(self, backup: Backup, manifest_path: Path):
        """Create backup manifest with file metadata."""
        project_path = await self._find_project_path(backup.metadata.project_id)
        
        manifest = {
            "backup_id": backup.metadata.backup_id,
            "project_id": backup.metadata.project_id,
            "backup_type": backup.metadata.backup_type.value,
            "created_at": backup.metadata.created_at.isoformat(),
            "parent_backup_id": backup.metadata.parent_backup_id,
            "files": []
        }
        
        for file_path in backup.files:
            full_path = project_path / file_path
            if full_path.exists():
                stat = full_path.stat()
                manifest["files"].append({
                    "path": file_path,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "checksum": await self._calculate_file_checksum(str(full_path)) if stat.st_size < 100 * 1024 * 1024 else None  # Skip checksum for large files
                })
        
        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(manifest, indent=2))
    
    async def _create_backup_archive(self, files: List[str], project_path: Path, archive_path: Path, config: BackupConfig):
        """Create compressed backup archive."""
        compression_map = {
            CompressionType.GZIP: "gz",
            CompressionType.BZIP2: "bz2",
            CompressionType.XZ: "xz",
            CompressionType.NONE: ""
        }
        
        mode = f"w:{compression_map.get(config.compression, '')}"
        
        with tarfile.open(archive_path, mode) as tar:
            for file_path in files:
                full_path = project_path / file_path
                if full_path.exists():
                    tar.add(full_path, arcname=file_path)
        
        logger.info(f"Created backup archive: {archive_path}")
    
    async def _backup_databases(self, backup: Backup, config: BackupConfig, backup_dir: Path):
        """Backup databases associated with the project."""
        if not config.database_connections:
            return
        
        db_backup_dir = backup_dir / "databases"
        db_backup_dir.mkdir(exist_ok=True)
        
        for db_config in config.database_connections:
            try:
                db_type = db_config.get("type", "unknown")
                db_name = db_config.get("name", "database")
                
                if db_type == "postgresql":
                    await self._backup_postgresql(db_config, db_backup_dir / f"{db_name}.sql")
                elif db_type == "mysql":
                    await self._backup_mysql(db_config, db_backup_dir / f"{db_name}.sql")
                elif db_type == "sqlite":
                    await self._backup_sqlite(db_config, db_backup_dir / f"{db_name}.db")
                else:
                    logger.warning(f"Unsupported database type: {db_type}")
                    
            except Exception as e:
                logger.error(f"Database backup failed for {db_config}: {e}")
    
    async def _backup_postgresql(self, db_config: Dict[str, str], output_path: Path):
        """Backup PostgreSQL database."""
        command = [
            "pg_dump",
            "-h", db_config.get("host", "localhost"),
            "-p", str(db_config.get("port", 5432)),
            "-U", db_config.get("username", "postgres"),
            "-d", db_config["database"],
            "-f", str(output_path),
            "--clean", "--create"
        ]
        
        env = {}
        if "password" in db_config:
            env["PGPASSWORD"] = db_config["password"]
        
        await self._run_command(command, env=env)
    
    async def _backup_mysql(self, db_config: Dict[str, str], output_path: Path):
        """Backup MySQL database."""
        command = [
            "mysqldump",
            "-h", db_config.get("host", "localhost"),
            "-P", str(db_config.get("port", 3306)),
            "-u", db_config.get("username", "root")
        ]
        
        if "password" in db_config:
            command.extend(["-p" + db_config["password"]])
        
        command.extend([
            "--single-transaction",
            "--routines",
            "--triggers",
            db_config["database"]
        ])
        
        # Redirect output to file
        with open(output_path, 'w') as f:
            await self._run_command(command, stdout=f)
    
    async def _backup_sqlite(self, db_config: Dict[str, str], output_path: Path):
        """Backup SQLite database."""
        source_path = db_config.get("path")
        if source_path and Path(source_path).exists():
            shutil.copy2(source_path, output_path)
        else:
            raise ValueError(f"SQLite database not found: {source_path}")
    
    async def _restore_full(self, backup: Backup, target_path: Path, selective_restore: Optional[List[str]]) -> bool:
        """Restore from a full backup."""
        try:
            if not backup.backup_path or not Path(backup.backup_path).exists():
                raise ValueError("Backup archive not found")
            
            # Extract backup archive
            with tarfile.open(backup.backup_path, 'r:*') as tar:
                if selective_restore:
                    # Extract only specific files
                    for file_path in selective_restore:
                        try:
                            tar.extract(file_path, target_path)
                        except KeyError:
                            logger.warning(f"File not found in backup: {file_path}")
                else:
                    # Extract all files
                    tar.extractall(target_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Full restore failed: {str(e)}")
            return False
    
    async def _restore_incremental(self, backup: Backup, target_path: Path, selective_restore: Optional[List[str]]) -> bool:
        """Restore from incremental backup chain."""
        try:
            # Build backup chain
            backup_chain = await self._build_backup_chain(backup)
            
            # Restore in order (oldest to newest)
            for chain_backup in backup_chain:
                success = await self._restore_full(chain_backup, target_path, selective_restore)
                if not success:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Incremental restore failed: {str(e)}")
            return False
    
    async def _build_backup_chain(self, backup: Backup) -> List[Backup]:
        """Build the chain of backups needed for incremental restore."""
        chain = []
        current_backup = backup
        
        # Walk back the parent chain
        while current_backup:
            chain.insert(0, current_backup)  # Insert at beginning
            
            if current_backup.metadata.parent_backup_id:
                parent = await self._get_backup_by_id(current_backup.metadata.parent_backup_id)
                current_backup = parent
            else:
                break
        
        return chain
    
    async def _restore_databases(self, backup: Backup, target_path: Path):
        """Restore databases from backup."""
        db_backup_dir = Path(backup.backup_path).parent / "databases"
        
        if not db_backup_dir.exists():
            return
        
        for db_file in db_backup_dir.iterdir():
            try:
                if db_file.suffix == '.sql':
                    # SQL dump file
                    logger.info(f"Found database backup: {db_file}")
                    # In a real implementation, would restore based on database type
                elif db_file.suffix == '.db':
                    # SQLite file
                    target_db = target_path / db_file.name
                    shutil.copy2(db_file, target_db)
                    logger.info(f"Restored SQLite database: {target_db}")
            except Exception as e:
                logger.error(f"Failed to restore database {db_file}: {e}")
    
    async def _verify_manifest(self, backup: Backup) -> bool:
        """Verify backup manifest integrity."""
        try:
            if not backup.manifest_path or not Path(backup.manifest_path).exists():
                return False
            
            async with aiofiles.open(backup.manifest_path, 'r') as f:
                manifest = json.loads(await f.read())
            
            # Basic validation
            required_fields = ["backup_id", "project_id", "created_at", "files"]
            for field in required_fields:
                if field not in manifest:
                    return False
            
            # Verify file count matches
            if len(manifest["files"]) != backup.metadata.file_count:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Manifest verification failed: {e}")
            return False
    
    async def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(self.chunk_size):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _backup_scheduler(self):
        """Background scheduler for automatic backups."""
        while True:
            try:
                current_time = datetime.now()
                
                for job in list(self.scheduled_jobs.values()):
                    if not job.enabled:
                        continue
                    
                    if job.next_run and current_time >= job.next_run:
                        try:
                            # Execute backup
                            await self.backup_project(
                                job.project_id,
                                incremental=(job.config.backup_type == BackupType.INCREMENTAL),
                                tags=["scheduled"]
                            )
                            
                            job.last_run = current_time
                            job.last_status = BackupStatus.SUCCESS
                            
                        except Exception as e:
                            logger.error(f"Scheduled backup failed for {job.project_id}: {e}")
                            job.last_status = BackupStatus.FAILED
                        
                        # Calculate next run time
                        cron = croniter(job.schedule, current_time)
                        job.next_run = cron.get_next(datetime)
                        
                        # Update persistent storage
                        await self._save_scheduled_job(job)
                
                # Sleep for a minute before checking again
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Backup scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _initialize_metadata_db(self):
        """Initialize SQLite database for backup metadata."""
        async with aiofiles.open(self.metadata_db_path, 'ab'):
            pass  # Create file if it doesn't exist
        
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                backup_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                size_bytes INTEGER,
                compressed_size_bytes INTEGER,
                file_count INTEGER,
                checksum TEXT,
                compression TEXT,
                encrypted INTEGER,
                parent_backup_id TEXT,
                retention_until TEXT,
                tags TEXT,
                notes TEXT,
                backup_path TEXT,
                manifest_path TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                job_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                schedule TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                next_run TEXT,
                last_run TEXT,
                last_status TEXT,
                created_at TEXT NOT NULL,
                config TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _save_backup_metadata(self, backup: Backup):
        """Save backup metadata to database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO backups VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            backup.metadata.backup_id,
            backup.metadata.project_id,
            backup.metadata.backup_type.value,
            backup.metadata.status.value,
            backup.metadata.created_at.isoformat(),
            backup.metadata.completed_at.isoformat() if backup.metadata.completed_at else None,
            backup.metadata.size_bytes,
            backup.metadata.compressed_size_bytes,
            backup.metadata.file_count,
            backup.metadata.checksum,
            backup.metadata.compression.value,
            1 if backup.metadata.encrypted else 0,
            backup.metadata.parent_backup_id,
            backup.metadata.retention_until.isoformat() if backup.metadata.retention_until else None,
            json.dumps(backup.metadata.tags),
            backup.metadata.notes,
            backup.backup_path,
            backup.manifest_path
        ))
        
        conn.commit()
        conn.close()
    
    async def _save_scheduled_job(self, job: ScheduledJob):
        """Save scheduled job to database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO scheduled_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.job_id,
            job.project_id,
            job.schedule,
            1 if job.enabled else 0,
            job.next_run.isoformat() if job.next_run else None,
            job.last_run.isoformat() if job.last_run else None,
            job.last_status.value if job.last_status else None,
            job.created_at.isoformat(),
            json.dumps(job.config.to_dict())
        ))
        
        conn.commit()
        conn.close()
    
    async def _load_project_backups(self, project_id: str):
        """Load backup metadata from database for a project."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM backups WHERE project_id = ? ORDER BY created_at DESC
        ''', (project_id,))
        
        for row in cursor.fetchall():
            backup_id = row[0]
            if backup_id not in self.backups:
                metadata = BackupMetadata(
                    backup_id=row[0],
                    project_id=row[1],
                    backup_type=BackupType(row[2]),
                    status=BackupStatus(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    completed_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    size_bytes=row[6],
                    compressed_size_bytes=row[7],
                    file_count=row[8],
                    checksum=row[9],
                    compression=CompressionType(row[10]),
                    encrypted=bool(row[11]),
                    parent_backup_id=row[12],
                    retention_until=datetime.fromisoformat(row[13]) if row[13] else None,
                    tags=json.loads(row[14]) if row[14] else [],
                    notes=row[15]
                )
                
                backup = Backup(
                    metadata=metadata,
                    backup_path=row[16],
                    manifest_path=row[17]
                )
                
                self.backups[backup_id] = backup
        
        conn.close()
    
    async def _get_backup_by_id(self, backup_id: str) -> Optional[Backup]:
        """Get backup by ID, loading from database if necessary."""
        if backup_id in self.backups:
            return self.backups[backup_id]
        
        # Load from database
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM backups WHERE backup_id = ?', (backup_id,))
        row = cursor.fetchone()
        
        if row:
            metadata = BackupMetadata(
                backup_id=row[0],
                project_id=row[1],
                backup_type=BackupType(row[2]),
                status=BackupStatus(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                completed_at=datetime.fromisoformat(row[5]) if row[5] else None,
                size_bytes=row[6],
                compressed_size_bytes=row[7],
                file_count=row[8],
                checksum=row[9],
                compression=CompressionType(row[10]),
                encrypted=bool(row[11]),
                parent_backup_id=row[12],
                retention_until=datetime.fromisoformat(row[13]) if row[13] else None,
                tags=json.loads(row[14]) if row[14] else [],
                notes=row[15]
            )
            
            backup = Backup(
                metadata=metadata,
                backup_path=row[16],
                manifest_path=row[17]
            )
            
            self.backups[backup_id] = backup
            conn.close()
            return backup
        
        conn.close()
        return None
    
    async def _delete_backup_metadata(self, backup_id: str):
        """Delete backup metadata from database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM backups WHERE backup_id = ?', (backup_id,))
        conn.commit()
        conn.close()
    
    async def _delete_backup_files(self, backup: Backup):
        """Delete backup files from filesystem."""
        try:
            if backup.backup_path and Path(backup.backup_path).exists():
                Path(backup.backup_path).unlink()
            
            if backup.manifest_path and Path(backup.manifest_path).exists():
                Path(backup.manifest_path).unlink()
            
            # Delete backup directory if empty
            backup_dir = Path(backup.backup_path).parent if backup.backup_path else None
            if backup_dir and backup_dir.exists() and not any(backup_dir.iterdir()):
                backup_dir.rmdir()
                
        except Exception as e:
            logger.error(f"Failed to delete backup files: {e}")
    
    async def _cleanup_old_backups(self, project_id: str, config: BackupConfig):
        """Clean up old backups based on retention policy."""
        project_backups = [
            b for b in self.backups.values()
            if b.metadata.project_id == project_id
            and b.metadata.status == BackupStatus.SUCCESS
        ]
        
        # Sort by creation date (newest first)
        project_backups.sort(key=lambda b: b.metadata.created_at, reverse=True)
        
        # Keep only max_backups number of backups
        if len(project_backups) > config.max_backups:
            backups_to_delete = project_backups[config.max_backups:]
            
            for backup in backups_to_delete:
                try:
                    await self._delete_backup_files(backup)
                    await self._delete_backup_metadata(backup.metadata.backup_id)
                    
                    if backup.metadata.backup_id in self.backups:
                        del self.backups[backup.metadata.backup_id]
                    
                except Exception as e:
                    logger.error(f"Failed to delete old backup {backup.metadata.backup_id}: {e}")
    
    async def _run_command(self, command: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None, stdout=None):
        """Run a shell command asynchronously."""
        try:
            full_env = dict(os.environ)
            if env:
                full_env.update(env)
            
            if stdout:
                subprocess.run(command, cwd=cwd, env=full_env, stdout=stdout, check=True)
            else:
                result = subprocess.run(command, cwd=cwd, env=full_env, capture_output=True, text=True, check=True)
                return result.stdout
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}")
            raise