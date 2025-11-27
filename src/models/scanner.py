"""
Scanner models for comprehensive project analysis results.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import String, Integer, DateTime, func, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy.types import DECIMAL

from .base import Base, TimestampMixin


class ScanResult(Base, TimestampMixin):
    """Store comprehensive project scan results."""
    
    __tablename__ = "scan_results"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # full, incremental, etc.
    scanner_version: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Overall scores
    overall_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    security_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    quality_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    maintainability_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    performance_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    test_coverage: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    
    # Counts
    security_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    vulnerabilities_critical: Mapped[int] = mapped_column(Integer, default=0)
    vulnerabilities_high: Mapped[int] = mapped_column(Integer, default=0)
    vulnerabilities_medium: Mapped[int] = mapped_column(Integer, default=0)
    vulnerabilities_low: Mapped[int] = mapped_column(Integer, default=0)
    
    # Detailed results
    code_metrics: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    security_issues: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    quality_issues: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    test_analysis: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    documentation_analysis: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    performance_analysis: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    recommendations: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Scan metadata
    scan_duration_seconds: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3))
    files_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    lines_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    project = relationship("Project", back_populates="scan_results")
    
    # Indexes
    __table_args__ = (
        Index("idx_scan_results_project_id", "project_id"),
        Index("idx_scan_results_scan_type", "scan_type"),
        Index("idx_scan_results_overall_score", "overall_score", postgresql_using="btree"),
        Index("idx_scan_results_created_at", "created_at", postgresql_using="btree",
              postgresql_ops={"created_at": "DESC"}),
        Index("idx_scan_results_security_score", "security_score", postgresql_using="btree"),
        Index("idx_scan_results_critical_vulns", "vulnerabilities_critical", postgresql_using="btree"),
        Index("idx_scan_results_recommendations", "recommendations", postgresql_using="gin"),
        Index("idx_scan_results_code_metrics", "code_metrics", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<ScanResult(project_id='{self.project_id}', scan_type='{self.scan_type}', overall_score={self.overall_score})>"
    
    @property
    def grade(self) -> str:
        """Convert overall score to letter grade."""
        if self.overall_score is None:
            return "N/A"
        
        score = float(self.overall_score)
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
    def security_grade(self) -> str:
        """Convert security score to letter grade."""
        if self.security_score is None:
            return "N/A"
        
        score = float(self.security_score)
        if score >= 95:
            return "A"
        elif score >= 85:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if scan found critical security issues."""
        return self.vulnerabilities_critical > 0
    
    @property
    def total_vulnerabilities(self) -> int:
        """Get total vulnerability count."""
        return (self.vulnerabilities_critical + self.vulnerabilities_high + 
                self.vulnerabilities_medium + self.vulnerabilities_low)
    
    @property
    def risk_level(self) -> str:
        """Determine overall risk level."""
        if self.vulnerabilities_critical > 0:
            return "critical"
        elif self.vulnerabilities_high > 5:
            return "high"
        elif self.vulnerabilities_high > 0 or self.vulnerabilities_medium > 10:
            return "medium"
        elif self.total_vulnerabilities > 0:
            return "low"
        else:
            return "minimal"


class ScanJob(Base, TimestampMixin):
    """Track scanning job status and progress."""
    
    __tablename__ = "scan_jobs"
    
    job_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending, running, completed, failed, cancelled
    
    # Progress tracking
    progress_percent: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=0)
    total_projects: Mapped[int] = mapped_column(Integer, default=0)
    processed_projects: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Results and errors
    results: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Filters
    project_filter: Mapped[Optional[list]] = mapped_column(JSONB)  # Specific projects to scan
    
    # Indexes
    __table_args__ = (
        Index("idx_scan_jobs_job_id", "job_id"),
        Index("idx_scan_jobs_status", "status"),
        Index("idx_scan_jobs_scan_type", "scan_type"),
        Index("idx_scan_jobs_created_at", "created_at", postgresql_using="btree",
              postgresql_ops={"created_at": "DESC"}),
        Index("idx_scan_jobs_progress", "progress_percent", postgresql_using="btree"),
        Index("idx_scan_jobs_active", "status", postgresql_where="status IN ('pending', 'running')"),
    )
    
    def __repr__(self) -> str:
        return f"<ScanJob(job_id='{self.job_id}', scan_type='{self.scan_type}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in ("pending", "running")
    
    @property
    def is_completed(self) -> bool:
        """Check if job completed successfully."""
        return self.status == "completed"
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()


class TechnologyUsage(Base, TimestampMixin):
    """Track technology usage across projects."""
    
    __tablename__ = "technology_usage"
    
    technology_name: Mapped[str] = mapped_column(String(100), nullable=False)
    technology_type: Mapped[str] = mapped_column(String(50), nullable=False)  # language, framework, database, etc.
    project_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Statistics
    average_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 2))
    vulnerability_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Technology metadata
    tech_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Indexes
    __table_args__ = (
        Index("idx_tech_usage_name", "technology_name"),
        Index("idx_tech_usage_type", "technology_type"),
        Index("idx_tech_usage_project_count", "project_count", postgresql_using="btree",
              postgresql_ops={"project_count": "DESC"}),
        Index("idx_tech_usage_last_seen", "last_seen", postgresql_using="btree"),
        Index("idx_tech_usage_combo", "technology_type", "technology_name"),
    )
    
    def __repr__(self) -> str:
        return f"<TechnologyUsage(name='{self.technology_name}', type='{self.technology_type}', projects={self.project_count})>"


class SecurityPattern(Base, TimestampMixin):
    """Track recurring security patterns and vulnerabilities."""
    
    __tablename__ = "security_patterns"
    
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)
    cwe_id: Mapped[Optional[str]] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Occurrence tracking
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    project_count: Mapped[int] = mapped_column(Integer, default=1)
    last_occurrence: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_occurrence: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Pattern details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Related technologies
    affected_technologies: Mapped[list] = mapped_column(JSONB, default=list)
    common_contexts: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Indexes
    __table_args__ = (
        Index("idx_security_patterns_type", "pattern_type"),
        Index("idx_security_patterns_severity", "severity"),
        Index("idx_security_patterns_cwe", "cwe_id"),
        Index("idx_security_patterns_occurrence", "occurrence_count", postgresql_using="btree",
              postgresql_ops={"occurrence_count": "DESC"}),
        Index("idx_security_patterns_last_seen", "last_occurrence", postgresql_using="btree"),
        Index("idx_security_patterns_technologies", "affected_technologies", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<SecurityPattern(type='{self.pattern_type}', severity='{self.severity}', count={self.occurrence_count})>"


# Add relationships to existing Project model
# This would be added to src/models/project.py in the Project class:
# scan_results = relationship("ScanResult", back_populates="project", cascade="all, delete-orphan")