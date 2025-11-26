"""
Action history model for audit trail.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, Integer, DateTime, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base


class ActionHistory(Base):
    """Track all actions performed on projects for audit purposes."""
    
    __tablename__ = "action_history"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(50), default="system")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Relationships
    project = relationship("Project", back_populates="action_histories")
    
    # Indexes
    __table_args__ = (
        Index("idx_actions_project", "project_id"),
        Index("idx_actions_timestamp", "started_at", postgresql_using="btree",
              postgresql_ops={"started_at": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<ActionHistory(action_type='{self.action_type}', status='{self.status}', initiated_by='{self.initiated_by}')>"
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.duration_ms is None:
            return None
        return self.duration_ms / 1000.0
    
    @property
    def is_successful(self) -> bool:
        """Check if action was successful."""
        return self.status.lower() in ("success", "completed", "finished")
    
    @property
    def is_failed(self) -> bool:
        """Check if action failed."""
        return self.status.lower() in ("failed", "error", "cancelled")