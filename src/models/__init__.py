"""
Database models for Optimus backend.
Defines SQLAlchemy models matching the PostgreSQL schema.
"""

from .base import Base
from .project import Project, ProjectDependency
from .runtime import RuntimeStatus
from .analysis import AnalysisResult
from .monetization import MonetizationOpportunity
from .error import ErrorPattern, Issue
from .metrics import ProjectMetric
from .audit import ActionHistory
from .patterns import Pattern
from .tasks import ScheduledTask
from .conversation import ConversationContext
from .scanner import ScanResult, ScanJob, TechnologyUsage, SecurityPattern
from .memory import (
    DeliberationMemory, 
    PersonaResponseMemory, 
    ContextMemory, 
    PersonaLearningPattern, 
    MemoryAssociation, 
    MemoryMetrics
)
from .troubleshooting import (
    Solution,
    ErrorContext,
    FixAttempt,
    SolutionEffectiveness,
    KnowledgeBase,
    TroubleshootingSession
)

__all__ = [
    "Base",
    "Project",
    "ProjectDependency", 
    "RuntimeStatus",
    "AnalysisResult",
    "MonetizationOpportunity",
    "ErrorPattern",
    "Issue",
    "ProjectMetric",
    "ActionHistory",
    "Pattern",
    "ScheduledTask",
    "ConversationContext",
    "ScanResult",
    "ScanJob",
    "TechnologyUsage",
    "SecurityPattern",
    "DeliberationMemory",
    "PersonaResponseMemory", 
    "ContextMemory", 
    "PersonaLearningPattern", 
    "MemoryAssociation", 
    "MemoryMetrics",
    "Solution",
    "ErrorContext",
    "FixAttempt",
    "SolutionEffectiveness",
    "KnowledgeBase",
    "TroubleshootingSession",
]