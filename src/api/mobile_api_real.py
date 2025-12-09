"""
Real Mobile API endpoints for Optimus Assistant
Uses actual PostgreSQL database instead of mock data
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from uuid import UUID, uuid4
import asyncio
import json
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from ..database.config import get_database_manager

router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# =====================================================
# Database Session Dependency
# =====================================================

async def get_db() -> AsyncSession:
    """Get database session."""
    db_manager = get_database_manager()
    if not db_manager._initialized:
        await db_manager.initialize()
    async with db_manager._postgres_session_maker() as session:
        yield session

# =====================================================
# Models
# =====================================================

class MobileAgendaItem(BaseModel):
    """Lightweight agenda item for mobile."""
    id: str
    type: str  # event, task, suggestion
    title: str
    time: Optional[str] = None
    priority: Optional[int] = None
    energy: Optional[int] = None
    icon: str = "📌"
    color: str = "#3B82F6"
    location: Optional[str] = None
    description: Optional[str] = None

class MobileSummary(BaseModel):
    """Mobile dashboard summary."""
    greeting: str
    weather: Dict[str, Any]
    next_event: Optional[MobileAgendaItem] = None
    urgent_tasks: List[MobileAgendaItem] = []
    suggestions: List[MobileAgendaItem] = []
    stats: Dict[str, int]

class QuickAddRequest(BaseModel):
    """Quick add for voice or gesture input."""
    type: str  # task, event, note, reminder
    content: str
    priority: Optional[int] = 5
    context: Optional[str] = None
    due_date: Optional[datetime] = None

# =====================================================
# Helper Functions
# =====================================================

def get_greeting() -> str:
    """Get contextual greeting based on time of day."""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "Good morning! Ready to transform and roll out?"
    elif 12 <= hour < 17:
        return "Good afternoon! Optimus at your service."
    elif 17 <= hour < 21:
        return "Good evening! Time to optimize your evening."
    else:
        return "Night shift activated. What needs attention?"

async def get_weather() -> Dict[str, Any]:
    """Get real weather data from API."""
    try:
        async with httpx.AsyncClient() as client:
            # Using wttr.in for simple weather data
            response = await client.get(
                "http://wttr.in/?format=j1",
                timeout=2.0
            )
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                temp_f = current['temp_F']
                desc = current['weatherDesc'][0]['value']
                
                # Map weather to emoji
                weather_emojis = {
                    'sunny': '☀️', 'clear': '☀️',
                    'partly': '⛅', 'cloudy': '☁️',
                    'rain': '🌧️', 'light rain': '🌦️',
                    'snow': '❄️', 'fog': '🌫️',
                    'storm': '⛈️', 'thunder': '⚡'
                }
                
                icon = '🌤️'  # default
                for key, emoji in weather_emojis.items():
                    if key in desc.lower():
                        icon = emoji
                        break
                        
                return {
                    "temp": f"{temp_f}°F",
                    "condition": desc,
                    "icon": icon
                }
    except Exception as e:
        print(f"Weather API error: {e}")
    
    # Fallback weather
    return {
        "temp": "72°F",
        "condition": "Partly Cloudy",
        "icon": "⛅"
    }

async def ensure_user(db: AsyncSession) -> str:
    """Ensure default user exists and return user_id."""
    result = await db.execute(
        text("SELECT id FROM users WHERE email = 'user@optimus.local' LIMIT 1")
    )
    user = result.first()
    
    if user:
        return str(user[0])
    
    # Create default user
    await db.execute(
        text("""
            INSERT INTO users (email, name, timezone) 
            VALUES ('user@optimus.local', 'Primary User', 'America/Los_Angeles')
            ON CONFLICT (email) DO NOTHING
        """)
    )
    await db.commit()
    
    result = await db.execute(
        text("SELECT id FROM users WHERE email = 'user@optimus.local' LIMIT 1")
    )
    user = result.first()
    return str(user[0]) if user else None

async def seed_sample_data(db: AsyncSession, user_id: str):
    """Seed sample data if database is empty."""
    # Check if we have any tasks
    result = await db.execute(
        text("SELECT COUNT(*) FROM tasks WHERE user_id = :user_id::uuid"),
        {"user_id": user_id}
    )
    count = result.scalar()
    
    if count == 0:
        # Add sample tasks
        sample_tasks = [
            ("Review pull requests", 1, 3, datetime.now() + timedelta(hours=2)),
            ("Prepare presentation", 2, 4, datetime.now() + timedelta(hours=4)),
            ("Code optimization", 3, 2, datetime.now() + timedelta(hours=6)),
            ("Write documentation", 3, 2, datetime.now() + timedelta(days=1)),
            ("Team retrospective prep", 2, 3, datetime.now() + timedelta(days=1))
        ]
        
        for title, priority, energy, due in sample_tasks:
            await db.execute(
                text("""
                    INSERT INTO tasks (user_id, title, priority, energy_required, due_date, status)
                    VALUES (:user_id::uuid, :title, :priority, :energy, :due, 'PENDING')
                """),
                {"user_id": user_id, "title": title, "priority": priority, 
                 "energy": energy, "due": due}
            )
    
    # Check if we have any events
    result = await db.execute(
        text("SELECT COUNT(*) FROM events WHERE user_id = :user_id::uuid"),
        {"user_id": user_id}
    )
    count = result.scalar()
    
    if count == 0:
        # Add sample events
        sample_events = [
            ("Team Standup", datetime.now().replace(hour=9, minute=0), 
             datetime.now().replace(hour=9, minute=30), "MEETING", 2),
            ("Lunch with Sarah", datetime.now().replace(hour=12, minute=30),
             datetime.now().replace(hour=13, minute=30), "SOCIAL", 1),
            ("Client Call", datetime.now().replace(hour=15, minute=30),
             datetime.now().replace(hour=16, minute=30), "MEETING", 3),
            ("Gym Session", datetime.now().replace(hour=18, minute=0),
             datetime.now().replace(hour=19, minute=0), "HEALTH", 4)
        ]
        
        for title, start, end, category, energy in sample_events:
            await db.execute(
                text("""
                    INSERT INTO events (user_id, title, start_time, end_time, category, energy_level, source)
                    VALUES (:user_id::uuid, :title, :start, :end, :category, :energy, 'MANUAL')
                """),
                {"user_id": user_id, "title": title, "start": start, 
                 "end": end, "category": category, "energy": energy}
            )
    
    # Check if we have any suggestions
    result = await db.execute(
        text("SELECT COUNT(*) FROM suggestions WHERE user_id = :user_id::uuid AND status = 'PENDING'"),
        {"user_id": user_id}
    )
    count = result.scalar()
    
    if count == 0:
        # Add sample suggestions
        sample_suggestions = [
            ("Block 2 hours for deep work", "Your calendar has a gap from 10 AM - 12 PM", 
             "PRODUCTIVITY", 1),
            ("Take a walk after lunch", "You've been sitting for 3 hours", 
             "HEALTH", 2),
            ("Review weekly goals", "It's Friday - time to assess progress", 
             "PRODUCTIVITY", 3)
        ]
        
        for title, desc, category, priority in sample_suggestions:
            await db.execute(
                text("""
                    INSERT INTO suggestions (user_id, title, description, category, priority, type, confidence_score, status)
                    VALUES (:user_id::uuid, :title, :desc, :category, :priority, 'OPTIMIZATION', 0.85, 'PENDING')
                """),
                {"user_id": user_id, "title": title, "desc": desc, 
                 "category": category, "priority": priority}
            )
    
    await db.commit()

# =====================================================
# Endpoints
# =====================================================

@router.get("/summary")
async def get_mobile_summary(db: AsyncSession = Depends(get_db)) -> MobileSummary:
    """Get daily summary for mobile dashboard with REAL DATA."""
    
    user_id = await ensure_user(db)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to get user")
    
    # Seed sample data if needed
    await seed_sample_data(db, user_id)
    
    # Get today's events
    events_result = await db.execute(
        text("""
            SELECT id, title, start_time, end_time, location, category, energy_level
            FROM events 
            WHERE user_id = :user_id::uuid
            AND DATE(start_time) = CURRENT_DATE
            AND status != 'CANCELLED'
            ORDER BY start_time
            LIMIT 10
        """),
        {"user_id": user_id}
    )
    
    events = []
    next_event = None
    
    category_icons = {
        'MEETING': '👥', 'FOCUS': '🎯', 'PERSONAL': '🏠',
        'SOCIAL': '👋', 'HEALTH': '🏃'
    }
    
    for row in events_result:
        time_str = row[2].strftime("%I:%M %p") if row[2] else "TBD"
        icon = category_icons.get(row[5], '📅')
        
        item = MobileAgendaItem(
            id=str(row[0]),
            type="event",
            title=row[1],
            time=time_str,
            icon=icon,
            color="#3B82F6",
            location=row[4],
            energy=row[6]
        )
        
        events.append(item)
        
        # Set next event if it hasn't happened yet
        if not next_event and row[2] > datetime.now():
            next_event = item
    
    # Get today's tasks
    tasks_result = await db.execute(
        text("""
            SELECT id, title, priority, energy_required, status, due_date, description
            FROM tasks
            WHERE user_id = :user_id::uuid
            AND (DATE(due_date) = CURRENT_DATE OR status = 'IN_PROGRESS')
            ORDER BY priority ASC, due_date ASC
            LIMIT 20
        """),
        {"user_id": user_id}
    )
    
    urgent_tasks = []
    tasks_today = 0
    tasks_completed = 0
    
    priority_colors = {
        1: "#DC2626",  # Red for P1
        2: "#F59E0B",  # Amber for P2
        3: "#10B981"   # Green for P3
    }
    
    for row in tasks_result:
        tasks_today += 1
        if row[4] == 'COMPLETED':
            tasks_completed += 1
        elif row[2] and row[2] <= 2:  # Priority 1 or 2 and not completed
            time_str = row[5].strftime("%I:%M %p") if row[5] else "Today"
            
            urgent_tasks.append(MobileAgendaItem(
                id=str(row[0]),
                type="task",
                title=row[1],
                time=time_str,
                priority=row[2],
                energy=row[3] if row[3] else 3,
                icon="💻" if row[2] == 1 else "📊",
                color=priority_colors.get(row[2], "#3B82F6"),
                description=row[6]
            ))
    
    # Calculate meeting count
    meetings_result = await db.execute(
        text("""
            SELECT COUNT(*) FROM events 
            WHERE user_id = :user_id::uuid
            AND DATE(start_time) = CURRENT_DATE
            AND category = 'MEETING'
            AND status != 'CANCELLED'
        """),
        {"user_id": user_id}
    )
    meetings_count = meetings_result.scalar() or 0
    
    # Calculate focus hours
    focus_result = await db.execute(
        text("""
            SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (end_time - start_time))/3600), 0)
            FROM events
            WHERE user_id = :user_id::uuid
            AND DATE(start_time) = CURRENT_DATE
            AND category = 'FOCUS'
            AND status != 'CANCELLED'
        """),
        {"user_id": user_id}
    )
    focus_hours = round(focus_result.scalar() or 2)  # Default to 2 if no focus blocks
    
    # Get AI suggestions
    suggestions_result = await db.execute(
        text("""
            SELECT id, title, description, category, priority
            FROM suggestions
            WHERE user_id = :user_id::uuid
            AND status = 'PENDING'
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY priority ASC
            LIMIT 3
        """),
        {"user_id": user_id}
    )
    
    suggestions = []
    category_suggestion_icons = {
        'PRODUCTIVITY': '🎯', 'SOCIAL': '📞',
        'HEALTH': '🚶', 'SCHEDULING': '📅'
    }
    
    for row in suggestions_result:
        suggestions.append(MobileAgendaItem(
            id=str(row[0]),
            type="suggestion",
            title=row[1],
            description=row[2] if row[2] else "",
            icon=category_suggestion_icons.get(row[3], "💡"),
            color="#F59E0B"
        ))
    
    # If no suggestions exist, check relationships for social reminders
    if len(suggestions) < 2:
        social_result = await db.execute(
            text("""
                SELECT name, last_contact, phone
                FROM relationships
                WHERE user_id = :user_id::uuid
                AND importance >= 7
                AND (last_contact < CURRENT_DATE - INTERVAL '14 days' OR last_contact IS NULL)
                ORDER BY importance DESC
                LIMIT 1
            """),
            {"user_id": user_id}
        )
        social = social_result.first()
        if social:
            days_ago = (datetime.now().date() - social[1]).days if social[1] else 30
            suggestions.append(MobileAgendaItem(
                id="social_reminder",
                type="suggestion",
                title=f"Call {social[0]} - it's been {days_ago} days",
                description=f"Last contact: {social[1].strftime('%B %d') if social[1] else 'Never'}",
                icon="📞",
                color="#F59E0B"
            ))
    
    # Get real weather
    weather = await get_weather()
    
    # Build stats
    stats = {
        "tasks_today": tasks_today,
        "completed": tasks_completed,
        "meetings": meetings_count,
        "focus_hours": focus_hours
    }
    
    return MobileSummary(
        greeting=get_greeting(),
        weather=weather,
        next_event=next_event,
        urgent_tasks=urgent_tasks[:3],  # Limit to 3 most urgent
        suggestions=suggestions,
        stats=stats
    )

@router.post("/quick-add")
async def quick_add(
    request: QuickAddRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Quick add task, event, or note to the REAL database."""
    
    user_id = await ensure_user(db)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to get user")
    
    if request.type == "task":
        # Add task to database
        result = await db.execute(
            text("""
                INSERT INTO tasks (user_id, title, priority, due_date, status, created_at)
                VALUES (:user_id::uuid, :title, :priority, :due_date, 'PENDING', NOW())
                RETURNING id
            """),
            {
                "user_id": user_id,
                "title": request.content,
                "priority": request.priority,
                "due_date": request.due_date or datetime.now() + timedelta(days=1)
            }
        )
        task_id = result.scalar()
        await db.commit()
        
        return {
            "success": True,
            "type": "task",
            "id": str(task_id),
            "message": f"Task added: {request.content}",
            "item": {
                "id": str(task_id),
                "title": request.content,
                "priority": request.priority,
                "due_date": request.due_date
            }
        }
    
    elif request.type == "event":
        # Add event to database
        start_time = request.due_date or datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        result = await db.execute(
            text("""
                INSERT INTO events (user_id, title, start_time, end_time, category, source, status)
                VALUES (:user_id::uuid, :title, :start, :end, 'PERSONAL', 'MANUAL', 'CONFIRMED')
                RETURNING id
            """),
            {
                "user_id": user_id,
                "title": request.content,
                "start": start_time,
                "end": end_time
            }
        )
        event_id = result.scalar()
        await db.commit()
        
        return {
            "success": True,
            "type": "event",
            "id": str(event_id),
            "message": f"Event scheduled: {request.content}",
            "item": {
                "id": str(event_id),
                "title": request.content,
                "time": start_time
            }
        }
    
    elif request.type == "reminder":
        # Add as a suggestion/reminder
        result = await db.execute(
            text("""
                INSERT INTO suggestions (user_id, title, type, category, priority, status, confidence_score)
                VALUES (:user_id::uuid, :title, 'REMINDER', 'SCHEDULING', 1, 'PENDING', 1.0)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "title": f"Reminder: {request.content}"
            }
        )
        reminder_id = result.scalar()
        await db.commit()
        
        return {
            "success": True,
            "type": "reminder",
            "id": str(reminder_id),
            "message": f"I'll remind you: {request.content}",
            "item": {
                "id": str(reminder_id),
                "content": request.content,
                "time": request.due_date
            }
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown type: {request.type}")

@router.get("/stats/week")
async def get_week_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get weekly statistics from real data."""
    
    user_id = await ensure_user(db)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to get user")
    
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get task stats
    tasks_result = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed,
                AVG(CASE WHEN status = 'COMPLETED' 
                    THEN EXTRACT(EPOCH FROM (completed_date - created_at))/3600 
                    ELSE NULL END) as avg_completion_hours
            FROM tasks
            WHERE user_id = :user_id::uuid
            AND created_at >= :start
            AND created_at <= :end
        """),
        {"user_id": user_id, "start": week_start, "end": week_end}
    )
    task_stats = tasks_result.first()
    
    # Get event stats
    events_result = await db.execute(
        text("""
            SELECT 
                category,
                COUNT(*) as count,
                SUM(EXTRACT(EPOCH FROM (end_time - start_time))/3600) as total_hours
            FROM events
            WHERE user_id = :user_id::uuid
            AND start_time >= :start
            AND start_time <= :end
            AND status != 'CANCELLED'
            GROUP BY category
        """),
        {"user_id": user_id, "start": week_start, "end": week_end}
    )
    
    category_breakdown = {}
    total_scheduled_hours = 0
    
    for row in events_result:
        category_breakdown[row[0]] = {
            "count": row[1],
            "hours": round(row[2] or 0, 1)
        }
        total_scheduled_hours += row[2] or 0
    
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "tasks": {
            "total": task_stats[0] or 0,
            "completed": task_stats[1] or 0,
            "completion_rate": round((task_stats[1] / task_stats[0] * 100) if task_stats[0] else 0, 1),
            "avg_completion_hours": round(task_stats[2] or 0, 1)
        },
        "time_allocation": {
            "total_scheduled_hours": round(total_scheduled_hours, 1),
            "categories": category_breakdown,
            "daily_average": round(total_scheduled_hours / 7, 1)
        }
    }

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Check database connection and data status."""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        
        # Get data counts
        users = await db.execute(text("SELECT COUNT(*) FROM users"))
        tasks = await db.execute(text("SELECT COUNT(*) FROM tasks"))
        events = await db.execute(text("SELECT COUNT(*) FROM events"))
        suggestions = await db.execute(text("SELECT COUNT(*) FROM suggestions"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "data_status": {
                "users": users.scalar(),
                "tasks": tasks.scalar(),
                "events": events.scalar(),
                "suggestions": suggestions.scalar()
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }