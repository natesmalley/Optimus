"""
Monetization opportunities model.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import String, Text, Integer, DateTime, func, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, CheckConstraint
from sqlalchemy.types import DECIMAL

from .base import Base, TimestampMixin


class MonetizationOpportunity(Base, TimestampMixin):
    """Track revenue generation potential and business opportunities."""
    
    __tablename__ = "monetization_opportunities"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    opportunity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    potential_revenue: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 2))
    effort_required: Mapped[Optional[str]] = mapped_column(String(20))
    priority: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="identified")
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2))
    market_analysis: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    implementation_plan: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    project = relationship("Project", back_populates="monetization_opportunities")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("effort_required IN ('low', 'medium', 'high', 'very_high')"),
        CheckConstraint("priority BETWEEN 1 AND 10"),
        CheckConstraint("status IN ('identified', 'evaluating', 'in_progress', 'implemented', 'on_hold', 'rejected')"),
        CheckConstraint("confidence_score BETWEEN 0 AND 1"),
        Index("idx_monetization_project_id", "project_id"),
        Index("idx_monetization_type", "opportunity_type"),
        Index("idx_monetization_status", "status"),
        Index("idx_monetization_priority", "priority", postgresql_using="btree",
              postgresql_ops={"priority": "DESC"}),
        Index("idx_monetization_revenue", "potential_revenue", postgresql_using="btree",
              postgresql_ops={"potential_revenue": "DESC"}),
        Index("idx_monetization_confidence", "confidence_score", postgresql_using="btree",
              postgresql_ops={"confidence_score": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<MonetizationOpportunity(opportunity_type='{self.opportunity_type}', potential_revenue={self.potential_revenue})>"
    
    @property
    def opportunity_score(self) -> Optional[float]:
        """Calculate weighted opportunity score based on revenue, effort, and confidence."""
        if not all([self.potential_revenue, self.effort_required, self.confidence_score]):
            return None
            
        revenue = float(self.potential_revenue)
        confidence = float(self.confidence_score)
        
        # Weight based on effort required
        effort_weights = {
            "low": 1.5,
            "medium": 1.0,
            "high": 0.7,
            "very_high": 0.5
        }
        
        effort_weight = effort_weights.get(self.effort_required, 1.0)
        return revenue * confidence * effort_weight
    
    @property
    def risk_level(self) -> str:
        """Calculate risk level based on confidence score."""
        if self.confidence_score is None:
            return "unknown"
            
        confidence = float(self.confidence_score)
        if confidence >= 0.8:
            return "low"
        elif confidence >= 0.6:
            return "medium"
        elif confidence >= 0.4:
            return "high"
        else:
            return "very_high"