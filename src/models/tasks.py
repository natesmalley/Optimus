"""
Scheduled tasks model.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, func, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base


class ScheduledTask(Base):
    """Scheduled tasks for project automation."""
    
    __tablename__ = "scheduled_tasks"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(50))
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    project = relationship("Project", back_populates="scheduled_tasks")
    
    def __repr__(self) -> str:
        return f"<ScheduledTask(task_type='{self.task_type}', enabled={self.enabled}, next_run='{self.next_run}')>"
    
    @property
    def is_due(self) -> bool:
        """Check if task is due to run."""
        if not self.enabled or not self.next_run:
            return False
        return datetime.utcnow() >= self.next_run.replace(tzinfo=None)
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue (past next_run by more than 1 hour)."""
        if not self.is_due:
            return False
        overdue_threshold = 3600  # 1 hour in seconds
        return (datetime.utcnow() - self.next_run.replace(tzinfo=None)).total_seconds() > overdue_threshold