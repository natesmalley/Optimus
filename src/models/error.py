"""
Error patterns and issues models.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import String, Text, Integer, DateTime, func, Index, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, CheckConstraint
from sqlalchemy.types import DECIMAL

from .base import Base, TimestampMixin


class ErrorPattern(Base):
    """Store and track common error patterns for intelligent troubleshooting."""
    
    __tablename__ = "error_patterns"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    error_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    error_type: Mapped[Optional[str]] = mapped_column(String(100))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolution_confidence: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2))
    auto_fixable: Mapped[bool] = mapped_column(Boolean, default=False)
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Relationships
    project = relationship("Project", back_populates="error_patterns")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')"),
        Index("idx_error_project_id", "project_id"),
        Index("idx_error_hash", "error_hash"),
        Index("idx_error_type", "error_type"),
        Index("idx_error_occurrence", "occurrence_count", postgresql_using="btree",
              postgresql_ops={"occurrence_count": "DESC"}),
        Index("idx_error_last_seen", "last_seen", postgresql_using="btree",
              postgresql_ops={"last_seen": "DESC"}),
        Index("idx_error_severity", "severity"),
        UniqueConstraint("project_id", "error_hash", name="idx_error_project_hash"),
    )
    
    def __repr__(self) -> str:
        return f"<ErrorPattern(error_type='{self.error_type}', severity='{self.severity}', count={self.occurrence_count})>"
    
    @property
    def is_recent(self) -> bool:
        """Check if error occurred in the last 24 hours."""
        if not self.last_seen:
            return False
        return (datetime.utcnow() - self.last_seen.replace(tzinfo=None)).total_seconds() < 86400
    
    @property
    def is_frequent(self) -> bool:
        """Check if error occurs frequently (>10 times)."""
        return self.occurrence_count > 10


class Issue(Base, TimestampMixin):
    """Legacy compatibility issues table - consider migrating to error_patterns."""
    
    __tablename__ = "issues"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    solution: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    auto_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    project = relationship("Project", back_populates="issues")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')"),
        Index("idx_issues_project_severity", "project_id", "severity"),
        Index("idx_issues_type", "type"),
        Index("idx_issues_resolved", "resolved"),
    )
    
    def __repr__(self) -> str:
        return f"<Issue(type='{self.type}', severity='{self.severity}', resolved={self.resolved})>"