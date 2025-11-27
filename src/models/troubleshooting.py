"""
Smart Troubleshooting Models
===========================

Database models for the intelligent troubleshooting system that learns from every error
and gets better over time. These models support comprehensive error analysis, solution
tracking, and automated fix attempts with safety features.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from enum import Enum

from sqlalchemy import String, Text, Integer, DateTime, func, Index, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, CheckConstraint
from sqlalchemy.types import DECIMAL

from .base import Base, TimestampMixin


class SeverityLevel(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FixStatus(str, Enum):
    """Status of fix attempts."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    REQUIRES_APPROVAL = "requires_approval"


class SolutionCategory(str, Enum):
    """Categories of solutions."""
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    PROCESS = "process"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    CODE = "code"
    DATABASE = "database"
    SECURITY = "security"
    ENVIRONMENT = "environment"


class ErrorCategory(str, Enum):
    """Categories of errors."""
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    NETWORK = "network"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    MEMORY = "memory"
    PERMISSION = "permission"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    BUILD = "build"
    DEPLOYMENT = "deployment"
    PERFORMANCE = "performance"


class Solution(Base, TimestampMixin):
    """Reusable solutions for common problems with success tracking."""
    
    __tablename__ = "solutions"
    
    # Basic info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(50))  # Programming language
    framework: Mapped[Optional[str]] = mapped_column(String(100))  # Framework/tool
    
    # Solution content
    fix_commands: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    verification_commands: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    rollback_commands: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    
    # Metadata
    solution_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    prerequisites: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    is_destructive: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Success tracking
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=0.0)
    avg_execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Source information
    source: Mapped[str] = mapped_column(String(100), default="internal")  # internal, stackoverflow, github
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Relationships
    fix_attempts = relationship("FixAttempt", back_populates="solution")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("category IN ('dependency', 'configuration', 'process', 'network', 'permission', 'resource', 'code', 'database', 'security', 'environment')"),
        CheckConstraint("risk_level IN ('low', 'medium', 'high', 'critical')"),
        Index("idx_solution_category", "category"),
        Index("idx_solution_language", "language"),
        Index("idx_solution_success_rate", "success_rate", postgresql_using="btree", postgresql_ops={"success_rate": "DESC"}),
        Index("idx_solution_usage", "success_count", postgresql_using="btree", postgresql_ops={"success_count": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<Solution(title='{self.title[:50]}', success_rate={self.success_rate})>"
    
    @property
    def is_proven(self) -> bool:
        """Check if solution has proven successful (>80% success rate, >5 attempts)."""
        return self.success_rate >= 0.8 and (self.success_count + self.failure_count) >= 5
    
    @property
    def is_safe(self) -> bool:
        """Check if solution is safe to auto-execute."""
        return not self.is_destructive and self.risk_level in ["low", "medium"] and not self.requires_approval
    
    def update_success_rate(self):
        """Update success rate based on attempt counts."""
        total_attempts = self.success_count + self.failure_count
        if total_attempts > 0:
            self.success_rate = Decimal(self.success_count) / Decimal(total_attempts)
        else:
            self.success_rate = Decimal(0.0)


class ErrorContext(Base, TimestampMixin):
    """Context information when an error occurred."""
    
    __tablename__ = "error_contexts"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    error_pattern_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_patterns.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Environmental context
    os_info: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    python_version: Mapped[Optional[str]] = mapped_column(String(20))
    node_version: Mapped[Optional[str]] = mapped_column(String(20))
    environment_vars: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict)
    installed_packages: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    
    # System state
    cpu_usage: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    memory_usage: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    disk_space: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    network_status: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Process context
    process_id: Mapped[Optional[int]] = mapped_column(Integer)
    process_name: Mapped[Optional[str]] = mapped_column(String(255))
    command_line: Mapped[Optional[str]] = mapped_column(Text)
    working_directory: Mapped[Optional[str]] = mapped_column(Text)
    
    # Additional context
    user_actions: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    recent_changes: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    
    # Relationships
    project = relationship("Project")
    error_pattern = relationship("ErrorPattern")
    
    # Indexes
    __table_args__ = (
        Index("idx_error_context_project", "project_id"),
        Index("idx_error_context_pattern", "error_pattern_id"),
        Index("idx_error_context_created", "created_at"),
    )


class FixAttempt(Base, TimestampMixin):
    """Record of all fix attempts, successful or failed."""
    
    __tablename__ = "fix_attempts"
    
    # Linked entities
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    error_pattern_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_patterns.id", ondelete="SET NULL")
    )
    solution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("solutions.id", ondelete="SET NULL")
    )
    
    # Attempt details
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    execution_type: Mapped[str] = mapped_column(String(20), default="automatic")  # automatic, manual
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Execution details
    commands_executed: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    execution_output: Mapped[Optional[str]] = mapped_column(Text)
    error_output: Mapped[Optional[str]] = mapped_column(Text)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Results
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    side_effects: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    verification_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Rollback information
    rollback_available: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_commands: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Metadata
    confidence_score: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=0.0)
    initiated_by: Mapped[str] = mapped_column(String(100), default="system")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Learning data
    feedback_score: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5 user rating
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    project = relationship("Project")
    error_pattern = relationship("ErrorPattern")
    solution = relationship("Solution", back_populates="fix_attempts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'success', 'failed', 'rolled_back', 'requires_approval')"),
        CheckConstraint("execution_type IN ('automatic', 'manual', 'hybrid')"),
        CheckConstraint("feedback_score IS NULL OR (feedback_score >= 1 AND feedback_score <= 5)"),
        Index("idx_fix_attempt_project", "project_id"),
        Index("idx_fix_attempt_solution", "solution_id"),
        Index("idx_fix_attempt_status", "status"),
        Index("idx_fix_attempt_success", "success"),
        Index("idx_fix_attempt_created", "created_at", postgresql_using="btree", postgresql_ops={"created_at": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<FixAttempt(status='{self.status}', success={self.success})>"


class SolutionEffectiveness(Base, TimestampMixin):
    """Track effectiveness of solutions across different contexts."""
    
    __tablename__ = "solution_effectiveness"
    
    solution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("solutions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Context for effectiveness
    language: Mapped[Optional[str]] = mapped_column(String(50))
    framework: Mapped[Optional[str]] = mapped_column(String(100))
    os_type: Mapped[Optional[str]] = mapped_column(String(50))
    error_category: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Effectiveness metrics
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    successful_attempts: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=0.0)
    avg_execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Quality metrics
    user_satisfaction: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2))  # 1-5 average rating
    false_positive_rate: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=0.0)
    side_effect_rate: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=0.0)
    
    # Temporal data
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_failure: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    trend_direction: Mapped[str] = mapped_column(String(20), default="stable")  # improving, declining, stable
    
    # Relationships
    solution = relationship("Solution")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("trend_direction IN ('improving', 'declining', 'stable')"),
        Index("idx_solution_effectiveness_solution", "solution_id"),
        Index("idx_solution_effectiveness_context", "language", "framework", "os_type"),
        Index("idx_solution_effectiveness_rate", "success_rate", postgresql_using="btree", postgresql_ops={"success_rate": "DESC"}),
        UniqueConstraint("solution_id", "language", "framework", "os_type", "error_category", name="uq_solution_context"),
    )
    
    def update_metrics(self, success: bool, execution_time_ms: Optional[int] = None, satisfaction: Optional[int] = None):
        """Update effectiveness metrics after a fix attempt."""
        self.total_attempts += 1
        
        if success:
            self.successful_attempts += 1
            self.last_success = datetime.utcnow()
        else:
            self.last_failure = datetime.utcnow()
        
        # Update success rate
        self.success_rate = Decimal(self.successful_attempts) / Decimal(self.total_attempts)
        
        # Update execution time (moving average)
        if execution_time_ms is not None:
            if self.avg_execution_time_ms is None:
                self.avg_execution_time_ms = execution_time_ms
            else:
                # Simple moving average with weight for recent data
                weight = 0.8
                self.avg_execution_time_ms = int(
                    (1 - weight) * self.avg_execution_time_ms + weight * execution_time_ms
                )
        
        # Update satisfaction (moving average)
        if satisfaction is not None:
            if self.user_satisfaction is None:
                self.user_satisfaction = Decimal(satisfaction)
            else:
                weight = Decimal("0.8")
                self.user_satisfaction = (
                    (Decimal("1") - weight) * self.user_satisfaction + 
                    weight * Decimal(satisfaction)
                )


class KnowledgeBase(Base, TimestampMixin):
    """Curated knowledge base of troubleshooting information."""
    
    __tablename__ = "knowledge_base"
    
    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String(50)), default=list)
    
    # Context
    languages: Mapped[List[str]] = mapped_column(ARRAY(String(50)), default=list)
    frameworks: Mapped[List[str]] = mapped_column(ARRAY(String(100)), default=list)
    error_patterns: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    
    # Metadata
    source: Mapped[str] = mapped_column(String(100), default="manual")
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Usage tracking
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    helpful_votes: Mapped[int] = mapped_column(Integer, default=0)
    unhelpful_votes: Mapped[int] = mapped_column(Integer, default=0)
    
    # Search optimization
    search_vector: Mapped[Optional[str]] = mapped_column(Text)  # For full-text search
    
    # Constraints
    __table_args__ = (
        CheckConstraint("category IN ('troubleshooting', 'best_practices', 'configuration', 'deployment', 'performance', 'security')"),
        Index("idx_knowledge_category", "category"),
        Index("idx_knowledge_tags", "tags", postgresql_using="gin"),
        Index("idx_knowledge_languages", "languages", postgresql_using="gin"),
        Index("idx_knowledge_helpful", "helpful_votes", postgresql_using="btree", postgresql_ops={"helpful_votes": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeBase(title='{self.title[:50]}', category='{self.category}')>"
    
    @property
    def helpfulness_ratio(self) -> float:
        """Calculate helpfulness ratio."""
        total_votes = self.helpful_votes + self.unhelpful_votes
        if total_votes == 0:
            return 0.0
        return self.helpful_votes / total_votes


class TroubleshootingSession(Base, TimestampMixin):
    """Track troubleshooting sessions for learning and analysis."""
    
    __tablename__ = "troubleshooting_sessions"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Session info
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    initiated_by: Mapped[str] = mapped_column(String(100), default="system")
    
    # Problem description
    original_error: Mapped[str] = mapped_column(Text, nullable=False)
    error_category: Mapped[Optional[str]] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    
    # Solution tracking
    solutions_tried: Mapped[List[str]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    current_solution_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    
    # Outcomes
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_time_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    final_solution_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    user_satisfaction: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5 rating
    
    # Learning data
    manual_intervention_required: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_to_human: Mapped[bool] = mapped_column(Boolean, default=False)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text)
    
    # Session metadata
    context_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    project = relationship("Project")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('active', 'resolved', 'escalated', 'abandoned')"),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')"),
        CheckConstraint("user_satisfaction IS NULL OR (user_satisfaction >= 1 AND user_satisfaction <= 5)"),
        Index("idx_session_project", "project_id"),
        Index("idx_session_status", "status"),
        Index("idx_session_resolved", "resolved"),
        Index("idx_session_created", "created_at", postgresql_using="btree", postgresql_ops={"created_at": "DESC"}),
    )
    
    def __repr__(self) -> str:
        return f"<TroubleshootingSession(session_id='{self.session_id}', resolved={self.resolved})>"