"""
Memory models for Optimus Council of Minds.
Defines PostgreSQL models for storing deliberation history and persona memories.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from sqlalchemy import (
    String, Text, DateTime, Float, Integer, Boolean, 
    ForeignKey, Index, func, JSON, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class DeliberationMemory(Base, TimestampMixin):
    """
    Records of deliberation sessions conducted by the Council of Minds.
    Stores query, context, results, and metadata for each deliberation.
    """
    __tablename__ = "deliberation_memories"

    # Core deliberation data
    query: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Results and consensus
    consensus_result: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    consensus_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consensus_method: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Performance metrics
    deliberation_time: Mapped[float] = mapped_column(Float, nullable=False)
    persona_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Categorization and searchability
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # For similarity matching
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Relationships
    persona_responses: Mapped[List["PersonaResponseMemory"]] = relationship(
        "PersonaResponseMemory", 
        back_populates="deliberation",
        cascade="all, delete-orphan"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_deliberation_query_hash', 'query_hash'),
        Index('ix_deliberation_created_at', 'created_at'),
        Index('ix_deliberation_importance', 'importance_score'),
        Index('ix_deliberation_topic_created', 'topic', 'created_at'),
        Index('ix_deliberation_tags', 'tags', postgresql_using='gin'),
        Index('ix_deliberation_context', 'context', postgresql_using='gin'),
    )


class PersonaResponseMemory(Base, TimestampMixin):
    """
    Individual persona responses within deliberations.
    Stores how each persona responded to specific queries.
    """
    __tablename__ = "persona_response_memories"

    # Foreign key to deliberation
    deliberation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("deliberation_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Persona identification
    persona_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    persona_role: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Response data
    response: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Response metadata
    response_time: Mapped[float] = mapped_column(Float, nullable=False)
    tools_used: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    context_considered: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Learning metrics
    agreement_score: Mapped[float] = mapped_column(Float, nullable=True)  # How much others agreed
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # If outcome is known
    
    # Relationships
    deliberation: Mapped["DeliberationMemory"] = relationship(
        "DeliberationMemory",
        back_populates="persona_responses"
    )
    
    context_memories: Mapped[List["ContextMemory"]] = relationship(
        "ContextMemory",
        back_populates="response",
        cascade="all, delete-orphan"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_persona_response_persona_name', 'persona_name'),
        Index('ix_persona_response_confidence', 'confidence'),
        Index('ix_persona_response_deliberation', 'deliberation_id'),
        Index('ix_persona_response_persona_created', 'persona_name', 'created_at'),
        Index('ix_persona_response_tools', 'tools_used', postgresql_using='gin'),
    )


class ContextMemory(Base, TimestampMixin):
    """
    Context information that influenced persona responses.
    Stores related memories, associations, and contextual data.
    """
    __tablename__ = "context_memories"

    # Foreign key to persona response
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persona_response_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Context type and data
    context_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'similar_query', 'related_memory', etc.
    context_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Source information
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'deliberation', 'external', 'inferred'
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    response: Mapped["PersonaResponseMemory"] = relationship(
        "PersonaResponseMemory",
        back_populates="context_memories"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_context_memory_response', 'response_id'),
        Index('ix_context_memory_type', 'context_type'),
        Index('ix_context_memory_relevance', 'relevance_score'),
        Index('ix_context_memory_data', 'context_data', postgresql_using='gin'),
    )


class PersonaLearningPattern(Base, TimestampMixin):
    """
    Tracks learning patterns and performance trends for each persona.
    Enables adaptive behavior based on past performance.
    """
    __tablename__ = "persona_learning_patterns"

    # Persona identification
    persona_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Pattern identification
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'confidence_trend', 'accuracy_pattern', etc.
    pattern_context: Mapped[str] = mapped_column(String(255), nullable=False)  # Query type, topic, etc.
    
    # Pattern data
    pattern_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Tracking metrics
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_reinforced: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_learning_pattern_persona', 'persona_name'),
        Index('ix_learning_pattern_type', 'pattern_type'),
        Index('ix_learning_pattern_context', 'pattern_context'),
        Index('ix_learning_pattern_strength', 'strength'),
    )


class MemoryAssociation(Base, TimestampMixin):
    """
    Tracks associations between different memories.
    Enables discovery of patterns and related experiences.
    """
    __tablename__ = "memory_associations"

    # Source and target memories
    source_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deliberation_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    target_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deliberation_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Association properties
    association_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'similar', 'contradictory', 'builds_on'
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Association metadata
    discovered_by: Mapped[str] = mapped_column(String(100), nullable=True)  # Which algorithm found this
    association_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Tracking
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_memory_association_source', 'source_memory_id'),
        Index('ix_memory_association_target', 'target_memory_id'),
        Index('ix_memory_association_type', 'association_type'),
        Index('ix_memory_association_strength', 'strength'),
    )


class MemoryMetrics(Base, TimestampMixin):
    """
    Stores performance metrics and statistics about the memory system.
    Enables monitoring and optimization of memory operations.
    """
    __tablename__ = "memory_metrics"

    # Metric identification
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'recall_accuracy', 'storage_latency', etc.
    metric_scope: Mapped[str] = mapped_column(String(100), nullable=False)  # 'global', 'persona', 'topic'
    scope_identifier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metric data
    value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Time window
    measurement_period: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_memory_metrics_type', 'metric_type'),
        Index('ix_memory_metrics_scope', 'metric_scope', 'scope_identifier'),
        Index('ix_memory_metrics_period', 'measurement_period'),
    )