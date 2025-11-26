"""
Conversation context model for voice interaction.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, func, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base


class ConversationContext(Base):
    """Store conversation context for voice interaction preparation."""
    
    __tablename__ = "conversation_context"
    
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="SET NULL")
    )
    user_input: Mapped[Optional[str]] = mapped_column(Text)
    system_response: Mapped[Optional[str]] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String(50))
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships - optional since project_id can be null
    project = relationship("Project", foreign_keys=[project_id])
    
    def __repr__(self) -> str:
        return f"<ConversationContext(session_id='{self.session_id}', intent='{self.intent}')>"
    
    @property
    def is_recent(self) -> bool:
        """Check if conversation is from the last hour."""
        if not self.timestamp:
            return False
        return (datetime.utcnow() - self.timestamp.replace(tzinfo=None)).total_seconds() < 3600