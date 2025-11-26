"""
Analysis results model for storing code quality and security analysis.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import String, Integer, DateTime, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy.types import DECIMAL

from .base import Base


class AnalysisResult(Base):
    """Store code quality metrics and analysis outcomes."""
    
    __tablename__ = "analysis_results"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    results: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    issues_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    analyzer_version: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Relationships
    project = relationship("Project", back_populates="analysis_results")
    
    # Indexes
    __table_args__ = (
        Index("idx_analysis_project_id", "project_id"),
        Index("idx_analysis_type", "analysis_type"),
        Index("idx_analysis_score", "score", postgresql_using="btree",
              postgresql_ops={"score": "DESC"}),
        Index("idx_analysis_created_at", "created_at", postgresql_using="btree",
              postgresql_ops={"created_at": "DESC"}),
        Index("idx_analysis_results", "results", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<AnalysisResult(analysis_type='{self.analysis_type}', score={self.score}, issues_count={self.issues_count})>"
    
    @property
    def grade(self) -> str:
        """Convert score to letter grade."""
        if self.score is None:
            return "N/A"
        
        score = float(self.score)
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    @property
    def is_passing(self) -> bool:
        """Check if analysis result is passing (score >= 70)."""
        if self.score is None:
            return False
        return float(self.score) >= 70.0