"""
Orchestration models for project lifecycle management.

These models support the orchestration services including deployment history,
resource allocations, backup metadata, and environment configurations.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal

from sqlalchemy import String, Text, DateTime, func, Index, Boolean, Integer, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base, TimestampMixin


class DeploymentRecord(Base, TimestampMixin):
    """Track deployment history and status."""
    
    __tablename__ = "deployment_records"
    
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    target_environment: Mapped[str] = mapped_column(String(50), nullable=False)
    deployment_target: Mapped[str] = mapped_column(String(50), nullable=False)  # docker, local, kubernetes, etc.
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, running, success, failed, rolled_back
    commit_hash: Mapped[Optional[str]] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    
    # Deployment configuration
    build_command: Mapped[Optional[str]] = mapped_column(Text)
    test_command: Mapped[Optional[str]] = mapped_column(Text)
    deploy_command: Mapped[Optional[str]] = mapped_column(Text)
    
    # Results and artifacts
    build_logs: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    deploy_logs: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    health_status: Mapped[Optional[str]] = mapped_column(String(20))  # healthy, unhealthy, degraded, unknown
    rollback_deployment_id: Mapped[Optional[str]] = mapped_column(String(255))
    artifacts: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)  # container_id, image_tag, etc.
    
    # Health check configuration
    health_check_url: Mapped[Optional[str]] = mapped_column(Text)
    health_check_timeout: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Rollback settings
    rollback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_rollback_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Environment variables and secrets (encrypted)
    environment_variables: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    
    # Relationships
    project = relationship("Project", back_populates="deployment_records")
    pipeline_runs = relationship("PipelineRun", back_populates="deployment", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_deployment_project_id", "project_id"),
        Index("idx_deployment_status", "status"),
        Index("idx_deployment_target", "deployment_target"),
        Index("idx_deployment_environment", "target_environment"),
        Index("idx_deployment_started_at", "started_at"),
        Index("idx_deployment_commit", "commit_hash"),
        Index("idx_deployment_project_status", "project_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<DeploymentRecord(id='{self.deployment_id}', project='{self.project_id}', status='{self.status}')>"


class ResourceAllocation(Base, TimestampMixin):
    """Track resource allocations for projects."""
    
    __tablename__ = "resource_allocations"
    
    allocation_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Resource limits
    cpu_percent: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer)
    memory_mb: Mapped[Optional[int]] = mapped_column(Integer)
    memory_percent: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    disk_read_mb_s: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    disk_write_mb_s: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    network_upload_kb_s: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    network_download_kb_s: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    max_processes: Mapped[Optional[int]] = mapped_column(Integer)
    max_file_descriptors: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Allocation metadata
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enforced: Mapped[bool] = mapped_column(Boolean, default=False)
    enforcement_method: Mapped[Optional[str]] = mapped_column(String(50))  # cgroups, docker, process_limits
    cgroup_path: Mapped[Optional[str]] = mapped_column(Text)
    container_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Priority and auto-scaling
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # critical, high, normal, low, background
    auto_scale_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scale_threshold_cpu: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=70.0)
    scale_threshold_memory: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=80.0)
    
    # Requirements
    min_cpu_percent: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=5.0)
    max_cpu_percent: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=80.0)
    min_memory_mb: Mapped[int] = mapped_column(Integer, default=64)
    max_memory_mb: Mapped[int] = mapped_column(Integer, default=2048)
    
    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    project = relationship("Project", back_populates="resource_allocations")
    usage_metrics = relationship("ResourceUsageMetric", back_populates="allocation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_resource_allocation_project", "project_id"),
        Index("idx_resource_allocation_active", "active", "allocated_at"),
        Index("idx_resource_allocation_priority", "priority", "allocated_at"),
        Index("idx_resource_allocation_enforcement", "enforcement_method", "enforced"),
    )
    
    def __repr__(self) -> str:
        return f"<ResourceAllocation(id='{self.allocation_id}', project='{self.project_id}', cpu={self.cpu_percent}%, memory={self.memory_mb}MB)>"


class ResourceUsageMetric(Base):
    """Track historical resource usage metrics."""
    
    __tablename__ = "resource_usage_metrics"
    
    allocation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("resource_allocations.id", ondelete="CASCADE"),
        nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Usage metrics
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cpu_percent: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    cpu_cores_used: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    memory_mb: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    memory_percent: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    disk_read_mb_s: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0.0)
    disk_write_mb_s: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0.0)
    network_upload_kb_s: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0.0)
    network_download_kb_s: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0.0)
    process_count: Mapped[int] = mapped_column(Integer, default=0)
    file_descriptors: Mapped[int] = mapped_column(Integer, default=0)
    load_average_1m: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    load_average_5m: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    load_average_15m: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    
    # Relationships
    allocation = relationship("ResourceAllocation", back_populates="usage_metrics")
    project = relationship("Project")
    
    # Indexes for time-series queries
    __table_args__ = (
        Index("idx_resource_usage_allocation_time", "allocation_id", "timestamp"),
        Index("idx_resource_usage_project_time", "project_id", "timestamp"),
        Index("idx_resource_usage_timestamp", "timestamp", postgresql_using="btree",
              postgresql_ops={"timestamp": "DESC"}),
        Index("idx_resource_usage_cpu", "cpu_percent", "timestamp"),
        Index("idx_resource_usage_memory", "memory_percent", "timestamp"),
    )


class BackupRecord(Base, TimestampMixin):
    """Track backup metadata and status."""
    
    __tablename__ = "backup_records"
    
    backup_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Backup configuration
    backup_type: Mapped[str] = mapped_column(String(20), nullable=False)  # full, incremental, differential, snapshot
    compression_type: Mapped[str] = mapped_column(String(20), default="gzip")
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Backup metadata
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, running, success, failed, expired
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    
    # Size and content information
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    compressed_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    file_count: Mapped[Optional[int]] = mapped_column(Integer)
    checksum: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256
    
    # Storage information
    backup_path: Mapped[Optional[str]] = mapped_column(Text)
    manifest_path: Mapped[Optional[str]] = mapped_column(Text)
    storage_location: Mapped[Optional[str]] = mapped_column(Text)  # local, s3, gcp, etc.
    
    # Relationships and dependencies
    parent_backup_id: Mapped[Optional[str]] = mapped_column(String(255))  # For incremental backups
    
    # Retention and lifecycle
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(50)))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Backup configuration snapshot
    include_patterns: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    exclude_patterns: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    database_backup_included: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    project = relationship("Project", back_populates="backup_records")
    
    # Indexes
    __table_args__ = (
        Index("idx_backup_project_id", "project_id"),
        Index("idx_backup_status", "status"),
        Index("idx_backup_type", "backup_type"),
        Index("idx_backup_started_at", "started_at"),
        Index("idx_backup_retention", "retention_until"),
        Index("idx_backup_parent", "parent_backup_id"),
        Index("idx_backup_project_status", "project_id", "status"),
        Index("idx_backup_tags", "tags", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<BackupRecord(id='{self.backup_id}', project='{self.project_id}', type='{self.backup_type}', status='{self.status}')>"


class EnvironmentConfiguration(Base, TimestampMixin):
    """Store environment configurations for projects."""
    
    __tablename__ = "environment_configurations"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    environment_name: Mapped[str] = mapped_column(String(50), nullable=False)
    environment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # development, staging, production, testing, local
    
    # Configuration state
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Environment variables (sensitive data should be encrypted)
    variables: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)  # {key: {value, is_secret, description, etc.}}
    
    # Configuration files
    config_files: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB)  # filename -> content
    
    # Validation and constraints
    required_variables: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(255)))
    validation_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    
    # Lifecycle
    last_activated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_from_template: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Relationships
    project = relationship("Project", back_populates="environment_configurations")
    
    # Indexes
    __table_args__ = (
        Index("idx_env_config_project", "project_id"),
        Index("idx_env_config_name", "environment_name"),
        Index("idx_env_config_type", "environment_type"),
        Index("idx_env_config_active", "active", "last_activated"),
        Index("idx_env_config_project_name", "project_id", "environment_name"),
        Index("idx_env_config_variables", "variables", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<EnvironmentConfiguration(project='{self.project_id}', name='{self.environment_name}', type='{self.environment_type}')>"


class PipelineDefinition(Base, TimestampMixin):
    """Define deployment pipelines for projects."""
    
    __tablename__ = "pipeline_definitions"
    
    pipeline_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Pipeline metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Pipeline configuration
    stages: Mapped[List[Dict[str, Any]]] = mapped_column(ARRAY(JSONB))  # Array of stage definitions
    triggers: Mapped[List[str]] = mapped_column(ARRAY(String(100)))  # git branches, tags, manual
    environment: Mapped[str] = mapped_column(String(50), default="production")
    
    # Deployment settings
    deployment_target: Mapped[str] = mapped_column(String(50), nullable=False)
    deployment_config: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    
    # Pipeline behavior
    auto_trigger: Mapped[bool] = mapped_column(Boolean, default=False)
    parallel_execution: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_strategy: Mapped[str] = mapped_column(String(20), default="stop")  # stop, continue, rollback
    
    # Statistics
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    successful_runs: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_run_status: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Relationships
    project = relationship("Project", back_populates="pipeline_definitions")
    pipeline_runs = relationship("PipelineRun", back_populates="pipeline", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_pipeline_project", "project_id"),
        Index("idx_pipeline_enabled", "enabled", "last_run_at"),
        Index("idx_pipeline_triggers", "triggers", postgresql_using="gin"),
        Index("idx_pipeline_target", "deployment_target"),
        Index("idx_pipeline_project_name", "project_id", "name"),
    )
    
    def __repr__(self) -> str:
        return f"<PipelineDefinition(id='{self.pipeline_id}', name='{self.name}', project='{self.project_id}')>"


class PipelineRun(Base, TimestampMixin):
    """Track individual pipeline execution runs."""
    
    __tablename__ = "pipeline_runs"
    
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("pipeline_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    deployment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("deployment_records.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Run metadata
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)  # manual, git_push, schedule, api
    trigger_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)  # commit info, user info, etc.
    
    # Execution tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, running, success, failed, cancelled
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    
    # Stage tracking
    current_stage: Mapped[Optional[str]] = mapped_column(String(100))
    completed_stages: Mapped[List[str]] = mapped_column(ARRAY(String(100)), default=list)
    failed_stage: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Results
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    stage_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)  # detailed stage results
    artifacts: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB)  # output artifacts
    
    # Configuration snapshot
    pipeline_config: Mapped[Dict[str, Any]] = mapped_column(JSONB)  # snapshot of pipeline config at run time
    
    # Relationships
    pipeline = relationship("PipelineDefinition", back_populates="pipeline_runs")
    deployment = relationship("DeploymentRecord", back_populates="pipeline_runs")
    
    # Indexes
    __table_args__ = (
        Index("idx_pipeline_run_pipeline", "pipeline_id"),
        Index("idx_pipeline_run_status", "status"),
        Index("idx_pipeline_run_started", "started_at"),
        Index("idx_pipeline_run_trigger", "trigger_type", "started_at"),
        Index("idx_pipeline_run_deployment", "deployment_id"),
    )
    
    def __repr__(self) -> str:
        return f"<PipelineRun(id='{self.run_id}', pipeline='{self.pipeline_id}', status='{self.status}')>"


# Note: ScheduledTask is defined in tasks.py to avoid duplicate definition
# Commented out to prevent SQLAlchemy duplicate table error
'''
class ScheduledTask(Base, TimestampMixin):
    """Track scheduled tasks for projects (backups, deployments, etc.)."""
    
    __tablename__ = "scheduled_tasks"
    
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Task definition
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # backup, deployment, health_check, cleanup
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Schedule configuration
    schedule_expression: Mapped[str] = mapped_column(String(100), nullable=False)  # cron expression
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Execution tracking
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[Optional[str]] = mapped_column(String(20))  # success, failed, running
    last_duration_seconds: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Task configuration
    task_config: Mapped[Dict[str, Any]] = mapped_column(JSONB)  # task-specific configuration
    
    # Statistics
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    successful_runs: Mapped[int] = mapped_column(Integer, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, default=0)
    
    # Task behavior
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=300)  # 5 minutes
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3600)  # 1 hour
    
    # Relationships
    project = relationship("Project", back_populates="scheduled_tasks")
    
    # Indexes
    __table_args__ = (
        Index("idx_scheduled_task_project", "project_id"),
        Index("idx_scheduled_task_type", "task_type"),
        Index("idx_scheduled_task_enabled", "enabled", "next_run_at"),
        Index("idx_scheduled_task_next_run", "next_run_at"),
        Index("idx_scheduled_task_status", "last_status", "last_run_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ScheduledTask(id='{self.task_id}', name='{self.task_name}', type='{self.task_type}')>"
'''


# Update Project model relationships (this would be added to the existing Project model)
# These are the additional relationship definitions that would be added to src/models/project.py:

"""
Add these relationships to the Project class in src/models/project.py:

# Orchestration relationships
deployment_records = relationship("DeploymentRecord", back_populates="project", cascade="all, delete-orphan")
resource_allocations = relationship("ResourceAllocation", back_populates="project", cascade="all, delete-orphan")  
backup_records = relationship("BackupRecord", back_populates="project", cascade="all, delete-orphan")
environment_configurations = relationship("EnvironmentConfiguration", back_populates="project", cascade="all, delete-orphan")
pipeline_definitions = relationship("PipelineDefinition", back_populates="project", cascade="all, delete-orphan")
scheduled_tasks = relationship("ScheduledTask", back_populates="project", cascade="all, delete-orphan")
"""