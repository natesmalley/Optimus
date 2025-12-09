"""
Life Assistant Database Models
Extends Optimus for personal life and work management
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Time, Text, JSON, ARRAY, ForeignKey, DECIMAL, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from pydantic import BaseModel, Field

Base = declarative_base()

# =====================================================
# Enums
# =====================================================

class LifeContext(str, Enum):
    WORK = "WORK"
    HEALTH = "HEALTH"
    SOCIAL = "SOCIAL"
    GROWTH = "GROWTH"
    FAMILY = "FAMILY"
    
class GoalType(str, Enum):
    ACHIEVEMENT = "ACHIEVEMENT"
    HABIT = "HABIT"
    MILESTONE = "MILESTONE"
    PROJECT = "PROJECT"

class GoalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class EventStatus(str, Enum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class SuggestionType(str, Enum):
    TASK = "TASK"
    EVENT = "EVENT"
    RESPONSE = "RESPONSE"
    DECISION = "DECISION"
    OPTIMIZATION = "OPTIMIZATION"

class SuggestionStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

# =====================================================
# SQLAlchemy Models
# =====================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    timezone = Column(String(50), default="America/Los_Angeles")
    preferences = Column(JSON, default={})
    voice_settings = Column(JSON, default={"voice_id": "pNInz6obpgDQGcFmaJgB", "transform": True})
    notification_settings = Column(JSON, default={
        "email": True,
        "push": False,
        "quiet_hours": {"start": "22:00", "end": "08:00"}
    })
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contexts = relationship("LifeContextModel", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")
    suggestions = relationship("Suggestion", back_populates="user", cascade="all, delete-orphan")

class LifeContextModel(Base):
    __tablename__ = "life_contexts"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    code = Column(String(20), nullable=False)
    description = Column(Text)
    color = Column(String(7), default="#3B82F6")
    icon = Column(String(50))
    priority = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="contexts")
    goals = relationship("Goal", back_populates="context")
    events = relationship("Event", back_populates="context")
    tasks = relationship("Task", back_populates="context")
    
    __table_args__ = (
        UniqueConstraint("user_id", "code"),
    )

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    context_id = Column(PG_UUID(as_uuid=True), ForeignKey("life_contexts.id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), default=GoalType.ACHIEVEMENT)
    status = Column(String(50), default=GoalStatus.ACTIVE)
    priority = Column(Integer, default=5)
    target_date = Column(Date)
    completed_date = Column(Date)
    progress_percentage = Column(Integer, default=0)
    success_metrics = Column(JSON, default=[])
    blockers = Column(JSON, default=[])
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="goals")
    context = relationship("LifeContextModel", back_populates="goals")
    tasks = relationship("Task", back_populates="goal")
    habits = relationship("Habit", back_populates="goal", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_goals_user_status", "user_id", "status"),
        Index("idx_goals_target_date", "target_date"),
    )

class Habit(Base):
    __tablename__ = "habits"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    goal_id = Column(PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    frequency = Column(String(50), nullable=False)  # DAILY, WEEKLY, MONTHLY
    target_count = Column(Integer, default=1)
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    reminder_time = Column(Time)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    goal = relationship("Goal", back_populates="habits")

class Event(Base):
    __tablename__ = "events"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    context_id = Column(PG_UUID(as_uuid=True), ForeignKey("life_contexts.id", ondelete="SET NULL"))
    external_id = Column(String(255))
    source = Column(String(50))  # GOOGLE_CALENDAR, OUTLOOK, MANUAL, GENERATED
    title = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(255))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    all_day = Column(Boolean, default=False)
    recurring_rule = Column(Text)
    attendees = Column(JSON, default=[])
    reminders = Column(JSON, default=[])
    status = Column(String(50), default=EventStatus.CONFIRMED)
    category = Column(String(50))  # MEETING, FOCUS, PERSONAL, SOCIAL, HEALTH
    energy_level = Column(Integer)  # 1-5
    preparation_time = Column(Integer)  # minutes
    travel_time = Column(Integer)  # minutes
    event_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="events")
    context = relationship("LifeContextModel", back_populates="events")
    
    __table_args__ = (
        UniqueConstraint("external_id", "source"),
        Index("idx_events_user_time", "user_id", "start_time", "end_time"),
        Index("idx_events_source", "source", "external_id"),
    )

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal_id = Column(PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"))
    context_id = Column(PG_UUID(as_uuid=True), ForeignKey("life_contexts.id", ondelete="SET NULL"))
    external_id = Column(String(255))
    source = Column(String(50))  # TODOIST, NOTION, MANUAL, GENERATED
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default=TaskStatus.PENDING)
    priority = Column(Integer, default=5)
    due_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))
    estimated_minutes = Column(Integer)
    actual_minutes = Column(Integer)
    energy_required = Column(Integer)  # 1-5
    focus_required = Column(Integer)  # 1-5
    tags = Column(ARRAY(String))
    dependencies = Column(ARRAY(PG_UUID(as_uuid=True)))
    recurrence_rule = Column(Text)
    task_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    goal = relationship("Goal", back_populates="tasks")
    context = relationship("LifeContextModel", back_populates="tasks")
    
    __table_args__ = (
        Index("idx_tasks_user_status", "user_id", "status"),
        Index("idx_tasks_due_date", "due_date"),
    )

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    context_id = Column(PG_UUID(as_uuid=True), ForeignKey("life_contexts.id", ondelete="SET NULL"))
    external_id = Column(String(255))
    source = Column(String(50), nullable=False)  # GMAIL, OUTLOOK, SLACK, etc.
    type = Column(String(50), nullable=False)  # EMAIL, MESSAGE, CALL, MEETING_NOTES
    direction = Column(String(10))  # INBOUND, OUTBOUND
    counterpart_name = Column(String(255))
    counterpart_email = Column(String(255))
    subject = Column(String(500))
    preview = Column(Text)
    content = Column(Text)  # Should be encrypted
    sentiment = Column(String(50))  # POSITIVE, NEUTRAL, NEGATIVE, URGENT
    importance_score = Column(Integer)  # 1-10
    requires_response = Column(Boolean, default=False)
    response_deadline = Column(DateTime(timezone=True))
    response_drafted = Column(Boolean, default=False)
    response_sent = Column(Boolean, default=False)
    thread_id = Column(String(255))
    attachments = Column(JSON, default=[])
    interaction_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    interaction_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    
    __table_args__ = (
        Index("idx_interactions_user_time", "user_id", "interaction_time"),
        Index("idx_interactions_response", "user_id", "requires_response", "response_sent"),
    )

class Suggestion(Base):
    __tablename__ = "suggestions"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    category = Column(String(50))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reasoning = Column(Text)
    confidence_score = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    priority = Column(Integer, default=5)
    status = Column(String(50), default=SuggestionStatus.PENDING)
    suggested_actions = Column(JSON, default=[])
    context_data = Column(JSON, default={})
    expires_at = Column(DateTime(timezone=True))
    presented_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))
    response = Column(String(50))  # ACCEPTED, REJECTED, MODIFIED, DEFERRED
    user_feedback = Column(Text)
    outcome_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="suggestions")
    
    __table_args__ = (
        Index("idx_suggestions_user_status", "user_id", "status"),
        Index("idx_suggestions_expires", "expires_at"),
    )

class AssistantInteraction(Base):
    __tablename__ = "assistant_interactions"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query = Column(Text, nullable=False)
    query_type = Column(String(50))  # PLANNING, DRAFTING, DECISION, ANALYSIS, GENERAL
    mode = Column(String(50))  # AUTO, WORK, LIFE, SOCIAL, GROWTH
    context = Column(JSON, default={})
    agents_used = Column(ARRAY(String))
    tools_used = Column(ARRAY(String))
    response = Column(Text)
    response_format = Column(String(50))  # TEXT, STRUCTURED, ACTIONS
    confidence_score = Column(DECIMAL(3, 2))
    processing_time_ms = Column(Integer)
    tokens_used = Column(Integer)
    suggestion_ids = Column(ARRAY(PG_UUID(as_uuid=True)))
    user_rating = Column(Integer)  # 1-5
    user_feedback = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_assistant_interactions_user", "user_id", "created_at"),
    )

# =====================================================
# Pydantic Models for API
# =====================================================

class UserCreate(BaseModel):
    email: str
    name: str
    timezone: str = "America/Los_Angeles"
    preferences: Dict[str, Any] = {}

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: GoalType = GoalType.ACHIEVEMENT
    context_code: Optional[str] = None
    priority: int = 5
    target_date: Optional[datetime] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    context_code: Optional[str] = None
    goal_id: Optional[UUID] = None
    priority: int = 5
    due_date: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    energy_required: Optional[int] = None
    tags: List[str] = []

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    context_code: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    energy_level: Optional[int] = None

class SuggestionCreate(BaseModel):
    type: SuggestionType
    category: Optional[str] = None
    title: str
    description: str
    reasoning: Optional[str] = None
    confidence_score: float = 0.5
    priority: int = 5
    suggested_actions: List[Dict[str, Any]] = []
    expires_at: Optional[datetime] = None

class AssistantQuery(BaseModel):
    query: str
    mode: Optional[str] = "AUTO"
    context: Dict[str, Any] = {}

class AssistantResponse(BaseModel):
    answer: str
    actions: List[Dict[str, Any]] = []
    confidence: float
    risk_flags: List[str] = []
    suggestions_created: List[UUID] = []

# =====================================================
# Service Functions
# =====================================================

class LifeAssistantService:
    """Service layer for life assistant operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_user(self, email: str, name: str) -> User:
        """Get existing user or create new one."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=name)
            self.db.add(user)
            self.db.commit()
            self._create_default_contexts(user)
        return user
    
    def _create_default_contexts(self, user: User):
        """Create default life contexts for new user."""
        default_contexts = [
            ("Work", "WORK", "#3B82F6", "💼"),
            ("Health", "HEALTH", "#10B981", "🏃"),
            ("Social", "SOCIAL", "#F59E0B", "👥"),
            ("Growth", "GROWTH", "#8B5CF6", "📚"),
            ("Family", "FAMILY", "#EF4444", "👨‍👩‍👧‍👦"),
        ]
        
        for name, code, color, icon in default_contexts:
            context = LifeContextModel(
                user_id=user.id,
                name=name,
                code=code,
                color=color,
                icon=icon
            )
            self.db.add(context)
        self.db.commit()
    
    def create_goal(self, user_id: UUID, goal_data: GoalCreate) -> Goal:
        """Create a new goal."""
        context = None
        if goal_data.context_code:
            context = self.db.query(LifeContextModel).filter(
                LifeContextModel.user_id == user_id,
                LifeContextModel.code == goal_data.context_code
            ).first()
        
        goal = Goal(
            user_id=user_id,
            context_id=context.id if context else None,
            title=goal_data.title,
            description=goal_data.description,
            type=goal_data.type,
            priority=goal_data.priority,
            target_date=goal_data.target_date
        )
        self.db.add(goal)
        self.db.commit()
        return goal
    
    def get_today_agenda(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get today's events and tasks."""
        today = datetime.now().date()
        
        # Get events
        events = self.db.query(Event).filter(
            Event.user_id == user_id,
            Event.start_time >= today,
            Event.start_time < today + datetime.timedelta(days=1)
        ).order_by(Event.start_time).all()
        
        # Get tasks
        tasks = self.db.query(Task).filter(
            Task.user_id == user_id,
            Task.due_date >= today,
            Task.due_date < today + datetime.timedelta(days=1),
            Task.status != TaskStatus.COMPLETED
        ).order_by(Task.due_date).all()
        
        agenda = []
        for event in events:
            agenda.append({
                "type": "event",
                "id": event.id,
                "title": event.title,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "location": event.location,
                "energy_level": event.energy_level
            })
        
        for task in tasks:
            agenda.append({
                "type": "task",
                "id": task.id,
                "title": task.title,
                "due_date": task.due_date,
                "priority": task.priority,
                "estimated_minutes": task.estimated_minutes
            })
        
        return sorted(agenda, key=lambda x: x.get("start_time") or x.get("due_date"))
    
    def create_suggestion(self, user_id: UUID, suggestion_data: SuggestionCreate) -> Suggestion:
        """Create a new AI suggestion."""
        suggestion = Suggestion(
            user_id=user_id,
            type=suggestion_data.type,
            category=suggestion_data.category,
            title=suggestion_data.title,
            description=suggestion_data.description,
            reasoning=suggestion_data.reasoning,
            confidence_score=suggestion_data.confidence_score,
            priority=suggestion_data.priority,
            suggested_actions=suggestion_data.suggested_actions,
            expires_at=suggestion_data.expires_at
        )
        self.db.add(suggestion)
        self.db.commit()
        return suggestion
    
    def get_pending_suggestions(self, user_id: UUID) -> List[Suggestion]:
        """Get all pending suggestions for user."""
        return self.db.query(Suggestion).filter(
            Suggestion.user_id == user_id,
            Suggestion.status == SuggestionStatus.PENDING,
            Suggestion.expires_at > datetime.utcnow()
        ).order_by(Suggestion.priority.desc()).all()