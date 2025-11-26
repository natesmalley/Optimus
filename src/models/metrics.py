"""
Project metrics model for time-series data.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import String, DateTime, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy.types import DECIMAL

from .base import Base


class ProjectMetric(Base):
    """Time-series data for project performance and health metrics."""
    
    __tablename__ = "project_metrics"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[Decimal] = mapped_column(DECIMAL(15, 4), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    metric_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    project = relationship("Project", back_populates="project_metrics")
    
    # Indexes
    __table_args__ = (
        Index("idx_metrics_project_type", "project_id", "metric_type"),
        Index("idx_metrics_timestamp", "timestamp", postgresql_using="btree",
              postgresql_ops={"timestamp": "DESC"}),
        Index("idx_metrics_value", "value"),
        Index("idx_metrics_time_partition", "timestamp", "project_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ProjectMetric(metric_type='{self.metric_type}', value={self.value}, unit='{self.unit}')>"
    
    @property
    def formatted_value(self) -> str:
        """Format value with unit."""
        if self.unit:
            return f"{self.value} {self.unit}"
        return str(self.value)
    
    @property
    def is_recent(self) -> bool:
        """Check if metric is from the last hour."""
        if not self.timestamp:
            return False
        return (datetime.utcnow() - self.timestamp.replace(tzinfo=None)).total_seconds() < 3600