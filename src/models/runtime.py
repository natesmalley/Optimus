"""
Runtime status model for tracking running processes.
"""

import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Integer, DateTime, func, Index, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy.types import DECIMAL

from .base import Base


class RuntimeStatus(Base):
    """Track running processes and their resource consumption."""
    
    __tablename__ = "runtime_status"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    process_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pid: Mapped[Optional[int]] = mapped_column(Integer)  # Process ID
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    cpu_usage: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    memory_usage: Mapped[Optional[int]] = mapped_column(BigInteger)  # Memory in bytes
    port: Mapped[Optional[int]] = mapped_column(Integer)  # Port number
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    project = relationship("Project", back_populates="runtime_statuses")
    
    # Indexes
    __table_args__ = (
        Index("idx_runtime_project_id", "project_id"),
        Index("idx_runtime_status", "status"),
        Index("idx_runtime_active", "project_id", "status", 
              postgresql_where="status IN ('starting', 'running')"),
        Index("idx_runtime_port", "port", postgresql_where="port IS NOT NULL"),
        Index("idx_runtime_heartbeat", "last_heartbeat", postgresql_using="btree",
              postgresql_ops={"last_heartbeat": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<RuntimeStatus(process_name='{self.process_name}', status='{self.status}', pid={self.pid})>"
    
    @property
    def is_running(self) -> bool:
        """Check if process is currently running."""
        return self.status in ("starting", "running")
    
    @property
    def memory_usage_mb(self) -> Optional[float]:
        """Get memory usage in MB."""
        if self.memory_usage is None:
            return None
        return self.memory_usage / (1024 * 1024)
    
    @property
    def primary_port(self) -> Optional[int]:
        """Get the primary port if any ports are defined."""
        if self.ports and len(self.ports) > 0:
            return self.ports[0]
        return None


class ProcessSnapshot(Base):
    """Historical snapshots of process performance metrics."""
    
    __tablename__ = "process_snapshots"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    process_id: Mapped[int] = mapped_column(Integer, nullable=False)
    process_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_percent: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    memory_rss: Mapped[Optional[int]] = mapped_column(BigInteger)  # Bytes
    memory_percent: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    disk_io_read: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    disk_io_write: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    network_io_sent: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    network_io_recv: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    open_files: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    threads: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)  # How long process was running
    
    # Relationships
    project = relationship("Project", back_populates="process_snapshots")
    
    # Indexes for time-series queries
    __table_args__ = (
        Index("idx_process_snapshots_project_time", "project_id", "snapshot_time"),
        Index("idx_process_snapshots_process_id", "process_id", "snapshot_time"),
        Index("idx_process_snapshots_time", "snapshot_time", postgresql_using="btree",
              postgresql_ops={"snapshot_time": "DESC"}),
        Index("idx_process_snapshots_cpu", "cpu_percent", "snapshot_time"),
        Index("idx_process_snapshots_memory", "memory_rss", "snapshot_time"),
    )


class PerformanceAlert(Base):
    """Performance alerts and warnings generated by monitoring."""
    
    __tablename__ = "performance_alerts"
    
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True  # System-wide alerts have no project
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)  # cpu_spike, memory_leak, etc.
    severity: Mapped[str] = mapped_column(String(20), nullable=False)     # low, medium, high, critical
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    threshold_value: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(15, 4))
    current_value: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(15, 4))
    metric_name: Mapped[Optional[str]] = mapped_column(String(100))
    process_id: Mapped[Optional[int]] = mapped_column(Integer)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), 
        server_default='active',
        nullable=False
    )  # active, resolved, suppressed
    
    # Relationships
    project = relationship("Project", back_populates="performance_alerts")
    
    # Indexes
    __table_args__ = (
        Index("idx_performance_alerts_project", "project_id", "triggered_at"),
        Index("idx_performance_alerts_type", "alert_type", "severity"),
        Index("idx_performance_alerts_status", "status", "triggered_at"),
        Index("idx_performance_alerts_severity", "severity", "triggered_at"),
        Index("idx_performance_alerts_time", "triggered_at", postgresql_using="btree",
              postgresql_ops={"triggered_at": "DESC"}),
    )


class LogEntry(Base):
    """Application and system log entries for monitoring and analysis."""
    
    __tablename__ = "log_entries"
    
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True  # System logs have no project
    )
    log_level: Mapped[str] = mapped_column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    source: Mapped[str] = mapped_column(String(255), nullable=False)    # File path or logger name
    message: Mapped[str] = mapped_column(Text, nullable=False)
    full_content: Mapped[Optional[str]] = mapped_column(Text)           # Full log line if different from message
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    process_id: Mapped[Optional[int]] = mapped_column(Integer)
    thread_id: Mapped[Optional[str]] = mapped_column(String(100))
    function_name: Mapped[Optional[str]] = mapped_column(String(255))
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    exception_type: Mapped[Optional[str]] = mapped_column(String(255))
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String(50)))     # Searchable tags
    context: Mapped[Optional[dict]] = mapped_column(JSONB)              # Additional context data
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    project = relationship("Project", back_populates="log_entries")
    
    # Indexes for log analysis
    __table_args__ = (
        Index("idx_log_entries_project_time", "project_id", "timestamp"),
        Index("idx_log_entries_level_time", "log_level", "timestamp"),
        Index("idx_log_entries_source", "source", "timestamp"),
        Index("idx_log_entries_time", "timestamp", postgresql_using="btree",
              postgresql_ops={"timestamp": "DESC"}),
        Index("idx_log_entries_process", "process_id", "timestamp"),
        Index("idx_log_entries_tags", "tags", postgresql_using="gin"),
        Index("idx_log_entries_context", "context", postgresql_using="gin"),
        Index("idx_log_entries_exception", "exception_type", "timestamp"),
        # Text search index for message content
        Index("idx_log_entries_message_text", "message", postgresql_using="gin",
              postgresql_ops={"message": "gin_trgm_ops"}),
    )