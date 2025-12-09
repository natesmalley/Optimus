"""
Mobile API endpoints for Optimus Assistant
Optimized for mobile devices with lightweight responses
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from uuid import UUID, uuid4
import asyncio
import json
from sqlalchemy.orm import Session

# Import life assistant models
from src.models.life_assistant import (
    LifeAssistantService, 
    GoalCreate, 
    TaskCreate, 
    EventCreate,
    SuggestionCreate,
    AssistantQuery,
    User,
    Task,
    Event,
    Goal,
    TaskStatus,
    EventStatus,
    SuggestionType
)

router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# =====================================================
# Mobile-Specific Models
# =====================================================

class QuickAddRequest(BaseModel):
    """Quick add for voice or gesture input."""
    type: str  # task, event, note, reminder
    content: str
    priority: Optional[int] = 5
    context: Optional[str] = None
    due_date: Optional[datetime] = None

class MobileAgendaItem(BaseModel):
    """Lightweight agenda item for mobile."""
    id: str
    type: str  # event, task, suggestion
    title: str
    time: Optional[str] = None
    priority: Optional[int] = None
    energy: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class MobileSummary(BaseModel):
    """Daily summary optimized for mobile."""
    greeting: str
    weather: Optional[Dict[str, Any]] = None
    next_event: Optional[MobileAgendaItem] = None
    urgent_tasks: List[MobileAgendaItem] = []
    suggestions: List[MobileAgendaItem] = []
    stats: Dict[str, int] = {}

class VoiceCommand(BaseModel):
    """Voice command from mobile."""
    transcript: str
    context: Dict[str, Any] = {}
    device_info: Dict[str, Any] = {}

class WidgetData(BaseModel):
    """Data for iOS widgets."""
    widget_type: str  # small, medium, large, lockscreen
    last_updated: datetime
    content: Dict[str, Any]

class PushSubscription(BaseModel):
    """Push notification subscription."""
    device_token: str
    device_type: str  # ios, android
    user_id: Optional[UUID] = None
    preferences: Dict[str, bool] = {}

# =====================================================
# Mock Data (replace with real DB queries)
# =====================================================

def get_mock_user():
    """Get mock user for testing."""
    return {
        "id": str(uuid4()),
        "email": "user@optimus.local",
        "name": "User",
        "timezone": "America/Los_Angeles"
    }

def get_mock_agenda():
    """Get mock agenda items."""
    now = datetime.now()
    return [
        MobileAgendaItem(
            id="1",
            type="event",
            title="Team Standup",
            time="9:00 AM",
            icon="👥",
            color="#3B82F6"
        ),
        MobileAgendaItem(
            id="2",
            type="task",
            title="Review pull requests",
            priority=1,
            energy=3,
            icon="💻",
            color="#10B981"
        ),
        MobileAgendaItem(
            id="3",
            type="event",
            title="Lunch with Sarah",
            time="12:30 PM",
            icon="🍽️",
            color="#F59E0B"
        ),
        MobileAgendaItem(
            id="4",
            type="task",
            title="Prepare presentation",
            priority=2,
            energy=4,
            icon="📊",
            color="#8B5CF6"
        )
    ]

# =====================================================
# Endpoints
# =====================================================

@router.get("/summary")
async def get_mobile_summary() -> MobileSummary:
    """Get daily summary for mobile dashboard."""
    
    now = datetime.now()
    hour = now.hour
    
    # Generate greeting based on time
    if hour < 12:
        greeting = "Good morning! Ready to transform and roll out?"
    elif hour < 17:
        greeting = "Good afternoon! Let's keep the momentum going."
    elif hour < 21:
        greeting = "Good evening! Time to wrap up and recharge."
    else:
        greeting = "Night shift activated. What needs attention?"
    
    # Get agenda items
    agenda = get_mock_agenda()
    
    # Find next event
    next_event = next((item for item in agenda if item.type == "event"), None)
    
    # Get urgent tasks
    urgent_tasks = [item for item in agenda if item.type == "task" and item.priority and item.priority <= 2][:3]
    
    # Generate suggestions
    suggestions = [
        MobileAgendaItem(
            id="s1",
            type="suggestion",
            title="Block 2 hours for deep work",
            icon="🎯",
            color="#EF4444"
        ),
        MobileAgendaItem(
            id="s2",
            type="suggestion",
            title="Call Mom - it's been 2 weeks",
            icon="📞",
            color="#F59E0B"
        )
    ]
    
    # Stats
    stats = {
        "tasks_today": 8,
        "completed": 3,
        "meetings": 4,
        "focus_hours": 2
    }
    
    # Mock weather
    weather = {
        "temp": "72°F",
        "condition": "Sunny",
        "icon": "☀️"
    }
    
    return MobileSummary(
        greeting=greeting,
        weather=weather,
        next_event=next_event,
        urgent_tasks=urgent_tasks,
        suggestions=suggestions,
        stats=stats
    )

@router.get("/today")
async def get_today_agenda() -> Dict[str, List[MobileAgendaItem]]:
    """Get today's agenda optimized for mobile."""
    
    agenda = get_mock_agenda()
    
    # Group by morning, afternoon, evening
    morning = []
    afternoon = []
    evening = []
    anytime = []
    
    for item in agenda:
        if item.time:
            # Parse time and categorize
            if "AM" in item.time:
                morning.append(item)
            elif "PM" in item.time:
                hour = int(item.time.split(":")[0])
                if hour < 5 or hour == 12:
                    afternoon.append(item)
                else:
                    evening.append(item)
        else:
            anytime.append(item)
    
    return {
        "morning": morning,
        "afternoon": afternoon,
        "evening": evening,
        "anytime": anytime,
        "total_items": len(agenda)
    }

@router.post("/quick-add")
async def quick_add(request: QuickAddRequest) -> Dict[str, Any]:
    """Quick add task, event, or note from mobile."""
    
    # Parse the content based on type
    if request.type == "task":
        # Create task
        task_id = str(uuid4())
        return {
            "success": True,
            "type": "task",
            "id": task_id,
            "message": f"Task added: {request.content}",
            "item": {
                "id": task_id,
                "title": request.content,
                "priority": request.priority,
                "due_date": request.due_date
            }
        }
    
    elif request.type == "event":
        # Create event
        event_id = str(uuid4())
        return {
            "success": True,
            "type": "event",
            "id": event_id,
            "message": f"Event scheduled: {request.content}",
            "item": {
                "id": event_id,
                "title": request.content,
                "time": request.due_date
            }
        }
    
    elif request.type == "reminder":
        # Create reminder
        reminder_id = str(uuid4())
        return {
            "success": True,
            "type": "reminder",
            "id": reminder_id,
            "message": f"I'll remind you: {request.content}",
            "item": {
                "id": reminder_id,
                "content": request.content,
                "time": request.due_date
            }
        }
    
    else:
        # Note or generic
        note_id = str(uuid4())
        return {
            "success": True,
            "type": "note",
            "id": note_id,
            "message": f"Noted: {request.content}",
            "item": {
                "id": note_id,
                "content": request.content
            }
        }

@router.post("/voice")
async def process_voice_command(command: VoiceCommand) -> Dict[str, Any]:
    """Process voice command from mobile."""
    
    transcript = command.transcript.lower()
    
    # Intent detection (simple for now)
    if any(word in transcript for word in ["schedule", "calendar", "meeting", "appointment"]):
        # Calendar intent
        return {
            "intent": "calendar",
            "response": "I'll check your calendar. You have 3 meetings today.",
            "actions": [
                {"type": "show_calendar", "date": "today"}
            ],
            "audio_response": True
        }
    
    elif any(word in transcript for word in ["add task", "todo", "remind me"]):
        # Task creation
        task_content = transcript.replace("add task", "").replace("todo", "").strip()
        return {
            "intent": "create_task",
            "response": f"I've added that to your tasks: {task_content}",
            "actions": [
                {"type": "create_task", "content": task_content}
            ],
            "audio_response": True
        }
    
    elif any(word in transcript for word in ["email", "message", "reply"]):
        # Email/message intent
        return {
            "intent": "communication",
            "response": "You have 5 unread emails. 2 require immediate attention.",
            "actions": [
                {"type": "show_emails", "filter": "important"}
            ],
            "audio_response": True
        }
    
    elif any(word in transcript for word in ["status", "summary", "how's my day"]):
        # Status update
        return {
            "intent": "status",
            "response": "You're on track! 3 of 8 tasks completed, next meeting in 45 minutes.",
            "actions": [
                {"type": "show_summary"}
            ],
            "audio_response": True
        }
    
    elif any(word in transcript for word in ["focus", "deep work", "do not disturb"]):
        # Focus mode
        return {
            "intent": "focus",
            "response": "Initiating focus mode. I'll handle interruptions for the next 2 hours.",
            "actions": [
                {"type": "enable_focus", "duration": 120}
            ],
            "audio_response": True
        }
    
    else:
        # General query
        return {
            "intent": "general",
            "response": f"I heard: '{command.transcript}'. How can I help with that?",
            "actions": [],
            "audio_response": True
        }

@router.get("/widgets/{widget_type}")
async def get_widget_data(widget_type: str) -> WidgetData:
    """Get data for iOS widgets."""
    
    now = datetime.now()
    
    if widget_type == "small":
        # Small widget: Next event + task count
        agenda = get_mock_agenda()
        next_event = next((item for item in agenda if item.type == "event"), None)
        
        content = {
            "next_event": {
                "title": next_event.title if next_event else "Free time!",
                "time": next_event.time if next_event else "",
                "icon": next_event.icon if next_event else "✨"
            },
            "tasks_remaining": 5,
            "tasks_completed": 3
        }
    
    elif widget_type == "medium":
        # Medium widget: Today's highlights
        agenda = get_mock_agenda()[:3]
        
        content = {
            "greeting": "Good morning!",
            "items": [
                {
                    "title": item.title,
                    "time": item.time,
                    "icon": item.icon
                } for item in agenda
            ],
            "motivation": "You've got this! 💪"
        }
    
    elif widget_type == "large":
        # Large widget: Full day view
        agenda = get_mock_agenda()
        
        content = {
            "date": now.strftime("%A, %B %d"),
            "timeline": [
                {
                    "hour": f"{h}:00",
                    "items": []
                } for h in range(8, 20)
            ],
            "stats": {
                "meetings": 4,
                "tasks": 8,
                "focus_time": "2h"
            }
        }
    
    elif widget_type == "lockscreen":
        # Lock screen widget
        content = {
            "quick_stat": "5 tasks | 2 urgent",
            "next_up": "Standup in 30 min"
        }
    
    else:
        content = {}
    
    return WidgetData(
        widget_type=widget_type,
        last_updated=now,
        content=content
    )

@router.post("/push/register")
async def register_push_token(subscription: PushSubscription) -> Dict[str, bool]:
    """Register device for push notifications."""
    
    # Store device token (mock for now)
    print(f"Registered device: {subscription.device_token[:10]}...")
    
    return {
        "success": True,
        "registered": True
    }

@router.post("/sync")
async def sync_offline_changes(changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sync offline changes from mobile."""
    
    processed = 0
    errors = []
    
    for change in changes:
        try:
            # Process each change based on type
            if change["type"] == "task_create":
                # Create task
                pass
            elif change["type"] == "task_update":
                # Update task
                pass
            elif change["type"] == "event_create":
                # Create event
                pass
            
            processed += 1
        except Exception as e:
            errors.append({
                "change_id": change.get("id"),
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "processed": processed,
        "errors": errors,
        "server_time": datetime.now()
    }

@router.get("/shortcuts")
async def get_siri_shortcuts() -> List[Dict[str, Any]]:
    """Get available Siri shortcuts for iOS."""
    
    shortcuts = [
        {
            "id": "plan_my_day",
            "phrase": "Plan my day",
            "title": "Daily Planning",
            "icon": "calendar",
            "color": "#3B82F6",
            "action": "/api/mobile/voice",
            "params": {"transcript": "plan my day"}
        },
        {
            "id": "whats_next",
            "phrase": "What's next",
            "title": "Next Task",
            "icon": "checkmark.circle",
            "color": "#10B981",
            "action": "/api/mobile/today",
            "params": {}
        },
        {
            "id": "add_task",
            "phrase": "Add task",
            "title": "Quick Task",
            "icon": "plus.circle",
            "color": "#F59E0B",
            "action": "/api/mobile/quick-add",
            "params": {"type": "task"}
        },
        {
            "id": "focus_time",
            "phrase": "Focus time",
            "title": "Start Focus",
            "icon": "moon.circle",
            "color": "#8B5CF6",
            "action": "/api/mobile/focus",
            "params": {"duration": 120}
        },
        {
            "id": "daily_summary",
            "phrase": "How's my day",
            "title": "Daily Summary",
            "icon": "chart.bar",
            "color": "#EF4444",
            "action": "/api/mobile/summary",
            "params": {}
        }
    ]
    
    return shortcuts

@router.get("/watch/complications")
async def get_watch_complications() -> Dict[str, Any]:
    """Get Apple Watch complication data."""
    
    return {
        "modular_small": {
            "line1": "5 tasks",
            "line2": "2 urgent"
        },
        "circular_small": {
            "value": 3,
            "total": 8,
            "label": "Tasks"
        },
        "graphic_corner": {
            "outer": "Next: Standup",
            "inner": "9:00 AM"
        },
        "graphic_rectangular": {
            "header": "Optimus",
            "body": "Standup at 9:00 AM\n5 tasks remaining\n2 hours focus time",
            "gauge": 0.375  # 3 of 8 tasks
        }
    }

@router.get("/stats/weekly")
async def get_weekly_stats() -> Dict[str, Any]:
    """Get weekly statistics for mobile dashboard."""
    
    return {
        "week_of": date.today().strftime("%B %d"),
        "productivity_score": 78,
        "tasks_completed": 42,
        "tasks_created": 51,
        "meetings_attended": 18,
        "focus_hours": 16.5,
        "email_response_time": "2.3 hours",
        "goals_progress": {
            "work": 0.7,
            "health": 0.5,
            "social": 0.6,
            "growth": 0.4
        },
        "trends": {
            "productivity": "up",
            "stress": "stable",
            "balance": "improving"
        }
    }

@router.websocket("/ws")
async def mobile_websocket(websocket: WebSocket):
    """WebSocket for real-time mobile updates."""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif data.get("type") == "subscribe":
                # Subscribe to updates
                await websocket.send_json({
                    "type": "subscribed",
                    "channels": data.get("channels", [])
                })
            
            # Send periodic updates
            await asyncio.sleep(30)
            await websocket.send_json({
                "type": "update",
                "data": {
                    "new_tasks": 0,
                    "completed_tasks": 1,
                    "next_event_in": "45 minutes"
                }
            })
            
    except WebSocketDisconnect:
        pass

# =====================================================
# Background Tasks
# =====================================================

async def send_push_notification(device_token: str, title: str, body: str, data: Dict[str, Any] = None):
    """Send push notification to mobile device."""
    # This would integrate with APNs (iOS) or FCM (Android)
    print(f"Sending push to {device_token[:10]}: {title}")
    # Implement actual push notification service

async def process_suggestion_generation(user_id: str):
    """Generate proactive suggestions for mobile."""
    # Analyze user patterns and generate suggestions
    pass

# =====================================================
# Health Check
# =====================================================

@router.get("/health")
async def mobile_health_check():
    """Health check for mobile API."""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "endpoints_available": 15,
        "server_time": datetime.now()
    }