"""
Project model and related entities.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, func, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    """Central registry for all discovered and managed projects."""
    
    __tablename__ = "projects"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tech_stack: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    dependencies: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), 
        default="discovered",
        nullable=False
    )
    git_url: Mapped[Optional[str]] = mapped_column(Text)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    last_commit_hash: Mapped[Optional[str]] = mapped_column(String(64))
    language_stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_scanned: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    runtime_statuses = relationship("RuntimeStatus", back_populates="project", cascade="all, delete-orphan")
    process_snapshots = relationship("ProcessSnapshot", back_populates="project", cascade="all, delete-orphan")
    performance_alerts = relationship("PerformanceAlert", back_populates="project", cascade="all, delete-orphan")
    log_entries = relationship("LogEntry", back_populates="project", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="project", cascade="all, delete-orphan")
    scan_results = relationship("ScanResult", back_populates="project", cascade="all, delete-orphan")
    monetization_opportunities = relationship("MonetizationOpportunity", back_populates="project", cascade="all, delete-orphan")
    error_patterns = relationship("ErrorPattern", back_populates="project", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan")
    project_metrics = relationship("ProjectMetric", back_populates="project", cascade="all, delete-orphan")
    action_histories = relationship("ActionHistory", back_populates="project", cascade="all, delete-orphan")
    scheduled_tasks = relationship("ScheduledTask", back_populates="project", cascade="all, delete-orphan")
    dependencies_from = relationship("ProjectDependency", foreign_keys="ProjectDependency.project_id", back_populates="project")
    dependencies_to = relationship("ProjectDependency", foreign_keys="ProjectDependency.depends_on_id", back_populates="depends_on")
    
    # Orchestration relationships
    deployment_records = relationship("DeploymentRecord", back_populates="project", cascade="all, delete-orphan")
    resource_allocations = relationship("ResourceAllocation", back_populates="project", cascade="all, delete-orphan")  
    backup_records = relationship("BackupRecord", back_populates="project", cascade="all, delete-orphan")
    environment_configurations = relationship("EnvironmentConfiguration", back_populates="project", cascade="all, delete-orphan")
    pipeline_definitions = relationship("PipelineDefinition", back_populates="project", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_projects_status", "status"),
        Index("idx_projects_path", "path"),
        Index("idx_projects_last_scanned", "last_scanned"),
        Index("idx_projects_tech_stack", "tech_stack", postgresql_using="gin"),
        Index("idx_projects_dependencies", "dependencies", postgresql_using="gin"),
        Index("idx_projects_language_stats", "language_stats", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<Project(name='{self.name}', path='{self.path}', status='{self.status}')>"


class ProjectDependency(Base, TimestampMixin):
    """Track dependencies between projects."""
    
    __tablename__ = "project_dependencies"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    depends_on_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    dependency_type: Mapped[Optional[str]] = mapped_column(String(50))
    version: Mapped[Optional[str]] = mapped_column(String(50))
    is_critical: Mapped[bool] = mapped_column(default=False)
    
    # Relationships
    project = relationship("Project", foreign_keys=[project_id], back_populates="dependencies_from")
    depends_on = relationship("Project", foreign_keys=[depends_on_id], back_populates="dependencies_to")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("project_id", "depends_on_id", "dependency_type"),
    )
    
    def __repr__(self) -> str:
        return f"<ProjectDependency(project_id='{self.project_id}', depends_on_id='{self.depends_on_id}')>"