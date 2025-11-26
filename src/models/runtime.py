"""
Runtime status model for tracking running processes.
"""

import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Integer, DateTime, func, Index, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID
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
    pid: Mapped[Optional[int]] = mapped_column(Integer)
    port: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    cpu_usage: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    memory_usage: Mapped[Optional[int]] = mapped_column(BigInteger)
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