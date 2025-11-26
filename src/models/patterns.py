"""
Learning patterns model for troubleshooting patterns.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import String, Integer, DateTime, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DECIMAL

from .base import Base


class Pattern(Base):
    """Learning patterns for troubleshooting and optimization."""
    
    __tablename__ = "patterns"
    
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False)
    pattern_signature: Mapped[str] = mapped_column(String(255), nullable=False)
    pattern_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    solution_template: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    success_rate: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=0.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_patterns_type", "pattern_type"),
        Index("idx_patterns_signature", "pattern_signature"),
        Index("idx_patterns_success", "success_rate", postgresql_using="btree",
              postgresql_ops={"success_rate": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<Pattern(pattern_type='{self.pattern_type}', signature='{self.pattern_signature}', success_rate={self.success_rate})>"
    
    @property
    def is_reliable(self) -> bool:
        """Check if pattern has high success rate (>70%)."""
        return float(self.success_rate) > 0.70
    
    @property
    def is_frequently_used(self) -> bool:
        """Check if pattern is used frequently (>5 times)."""
        return self.usage_count > 5
    
    def update_success_rate(self, success: bool) -> None:
        """Update success rate based on new usage outcome."""
        if self.usage_count == 0:
            self.success_rate = Decimal("1.0" if success else "0.0")
        else:
            current_successes = float(self.success_rate) * self.usage_count
            if success:
                current_successes += 1
            self.success_rate = Decimal(str(current_successes / (self.usage_count + 1)))
        
        self.usage_count += 1
        self.last_used = datetime.utcnow()