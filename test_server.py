#!/usr/bin/env python
"""
Simplified test server for Phase 2 user testing
Runs without database dependencies for demo purposes
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Set
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

# Import API routers
try:
    from src.api.voice_agent_api import router as voice_router
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False
    print("⚠️ Voice API not available - install dependencies with: pip install httpx")

try:
    from src.api.mobile_api_direct import router as mobile_router
    MOBILE_ENABLED = True
    print("✅ Using REAL mobile API with PostgreSQL database (direct connection)")
except ImportError:
    try:
        from src.api.mobile_api import router as mobile_router
        MOBILE_ENABLED = True
        print("⚠️ Using mock mobile API (real API not available)")
    except ImportError:
        MOBILE_ENABLED = False
        print("❌ Mobile API not available")

try:
    from src.api.assistant_api import router as assistant_router
    ASSISTANT_ENABLED = True
except ImportError:
    ASSISTANT_ENABLED = False
    print("⚠️ Assistant API not available")

# Import complete API implementation
try:
    from src.api.complete_api import (
        projects_router, deployment_router, monitoring_router,
        backup_router, auth_router, notification_router, 
        orchestration_router, create_tables
    )
    COMPLETE_API = True
    print("✅ Complete API implementation loaded - All features available!")
except ImportError as e:
    COMPLETE_API = False
    print(f"❌ Complete API not available: {e}")

# Initialize FastAPI app
app = FastAPI(title="Optimus Test Server", version="2.0.0")

# Configure CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.orchestration_subs: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        self.orchestration_subs.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Mock data for testing
mock_projects = [
    {
        "id": "proj-1",
        "name": "E-Commerce Platform",
        "path": "/projects/ecommerce",
        "tech_stack": {"language": "Python", "framework": "FastAPI", "database": "PostgreSQL"},
        "status": "running",
        "cpu_usage": 45.2,
        "memory_usage": 512,
        "environment": "production",
        "last_deployed": "2024-11-28T10:30:00Z"
    },
    {
        "id": "proj-2", 
        "name": "Analytics Dashboard",
        "path": "/projects/analytics",
        "tech_stack": {"language": "TypeScript", "framework": "React", "bundler": "Vite"},
        "status": "stopped",
        "cpu_usage": 0,
        "memory_usage": 0,
        "environment": "development",
        "last_deployed": "2024-11-27T15:45:00Z"
    },
    {
        "id": "proj-3",
        "name": "ML Pipeline",
        "path": "/projects/ml-pipeline",
        "tech_stack": {"language": "Python", "framework": "FastAPI", "ml": "TensorFlow"},
        "status": "running",
        "cpu_usage": 78.5,
        "memory_usage": 2048,
        "environment": "staging",
        "last_deployed": "2024-11-28T08:00:00Z"
    }
]

# Request/Response models
class DeliberationRequest(BaseModel):
    query: str
    context: Dict = {}

class LaunchRequest(BaseModel):
    environment: str = "development"

class ResourceRequest(BaseModel):
    cpu_limit: int
    memory_limit: int

class DeployRequest(BaseModel):
    strategy: str = "blue-green"
    version: str = "latest"

# Mount frontend directory as static files
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

# Static file serving
@app.get("/")
async def read_root():
    """Serve the dashboard HTML."""
    dashboard_path = Path("frontend/simple-dashboard.html")
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    else:
        # Serve the orchestration dashboard as fallback
        orch_dashboard = Path("frontend/orchestration-dashboard.html")
        if orch_dashboard.exists():
            return FileResponse(orch_dashboard)
        return HTMLResponse("""
        <html>
        <head>
            <title>Optimus Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-900 text-white p-8">
            <h1 class="text-3xl font-bold mb-4">🚀 Optimus Orchestration Dashboard</h1>
            <p>Dashboard file not found. API server is running on port 8003.</p>
            <div class="mt-4">
                <h2 class="text-xl mb-2">Available Endpoints:</h2>
                <ul class="list-disc list-inside">
                    <li>/api/projects - Get all projects</li>
                    <li>/api/orchestration/launch/{project_id} - Launch project</li>
                    <li>/api/orchestration/stop/{project_id} - Stop project</li>
                    <li>/ws - WebSocket connection</li>
                </ul>
            </div>
        </body>
        </html>
        """)

# API Endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Commented out - using real implementation from complete_api
# @app.get("/api/projects")
# async def get_projects():
#     """Get all projects with their current status."""
#     return mock_projects

# Commented out - using real implementation from complete_api
# @app.get("/api/projects/{project_id}")
# async def get_project(project_id: str):
#     """Get specific project details."""
#     project = next((p for p in mock_projects if p["id"] == project_id), None)
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")
#     return project

# Orchestration endpoints
@app.post("/api/orchestration/launch/{project_id}")
async def launch_project(project_id: str, request: LaunchRequest):
    """Launch a project."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Simulate launch
    project["status"] = "starting"
    await manager.broadcast({
        "type": "project.starting",
        "project_id": project_id,
        "timestamp": datetime.now().isoformat()
    })
    
    # Simulate async startup
    await asyncio.sleep(2)
    
    project["status"] = "running"
    project["cpu_usage"] = random.uniform(20, 60)
    project["memory_usage"] = random.randint(256, 1024)
    project["environment"] = request.environment
    
    await manager.broadcast({
        "type": "project.started",
        "project_id": project_id,
        "environment": request.environment,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "project_id": project_id,
        "status": "running",
        "environment": request.environment,
        "port": random.randint(8000, 9000)
    }

@app.post("/api/orchestration/stop/{project_id}")
async def stop_project(project_id: str):
    """Stop a running project."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project["status"] = "stopping"
    await manager.broadcast({
        "type": "project.stopping",
        "project_id": project_id,
        "timestamp": datetime.now().isoformat()
    })
    
    await asyncio.sleep(1)
    
    project["status"] = "stopped"
    project["cpu_usage"] = 0
    project["memory_usage"] = 0
    
    await manager.broadcast({
        "type": "project.stopped",
        "project_id": project_id,
        "timestamp": datetime.now().isoformat()
    })
    
    return {"success": True, "project_id": project_id, "status": "stopped"}

@app.get("/api/orchestration/environments/{project_id}")
async def get_environment(project_id: str):
    """Get current environment for a project."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "project_id": project_id,
        "current": project.get("environment", "development"),
        "available": ["development", "staging", "production"]
    }

@app.post("/api/orchestration/environments/{project_id}/switch")
async def switch_environment(project_id: str, environment: str):
    """Switch project environment."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    old_env = project.get("environment", "development")
    project["environment"] = environment
    
    await manager.broadcast({
        "type": "environment.switched",
        "project_id": project_id,
        "from": old_env,
        "to": environment,
        "timestamp": datetime.now().isoformat()
    })
    
    return {"success": True, "previous": old_env, "current": environment}

@app.post("/api/orchestration/resources/allocate")
async def allocate_resources(project_id: str, request: ResourceRequest):
    """Allocate resources to a project."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "success": True,
        "project_id": project_id,
        "cpu_limit": request.cpu_limit,
        "memory_limit": request.memory_limit,
        "optimized": True
    }

@app.get("/api/orchestration/resources/{project_id}")
async def get_resources(project_id: str):
    """Get resource usage for a project."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "project_id": project_id,
        "cpu_usage": project.get("cpu_usage", 0),
        "memory_usage": project.get("memory_usage", 0),
        "cpu_limit": 2000,
        "memory_limit": 4096
    }

@app.post("/api/orchestration/deploy/{project_id}")
async def deploy_project(project_id: str, request: DeployRequest):
    """Deploy a project."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    deployment_id = f"deploy-{int(time.time())}"
    
    await manager.broadcast({
        "type": "deployment.started",
        "project_id": project_id,
        "deployment_id": deployment_id,
        "strategy": request.strategy,
        "timestamp": datetime.now().isoformat()
    })
    
    # Simulate deployment progress
    for progress in [25, 50, 75, 100]:
        await asyncio.sleep(1)
        await manager.broadcast({
            "type": "deployment.progress",
            "project_id": project_id,
            "deployment_id": deployment_id,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
    
    project["last_deployed"] = datetime.now().isoformat()
    
    return {
        "success": True,
        "deployment_id": deployment_id,
        "strategy": request.strategy,
        "version": request.version,
        "status": "completed"
    }

@app.post("/api/orchestration/backups/{project_id}")
async def create_backup(project_id: str):
    """Create a backup of a project."""
    project = next((p for p in mock_projects if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    backup_id = f"backup-{int(time.time())}"
    
    await manager.broadcast({
        "type": "backup.started",
        "project_id": project_id,
        "backup_id": backup_id,
        "timestamp": datetime.now().isoformat()
    })
    
    await asyncio.sleep(2)
    
    await manager.broadcast({
        "type": "backup.completed",
        "project_id": project_id,
        "backup_id": backup_id,
        "size_mb": random.randint(100, 500),
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "backup_id": backup_id,
        "size_mb": random.randint(100, 500),
        "encrypted": True
    }

# Council of Minds endpoint
@app.post("/api/council/deliberate")
async def council_deliberate(request: DeliberationRequest):
    """Council of Minds - Holistic advisor for technical and life decisions."""
    
    # Simulate deliberation time
    await asyncio.sleep(2)
    
    query = request.query.lower()
    
    # The Council adapts its perspective based on the domain of the question
    
    # Technical/Software decisions
    if any(word in query for word in ["deploy", "production", "release", "code", "api", "database"]):
        perspectives = [
            {"persona": "Strategist", "stance": "agree", "confidence": 0.85, 
             "reasoning": "Aligns with technical roadmap and business objectives"},
            {"persona": "Guardian", "stance": "proceed_with_caution", "confidence": 0.75,
             "reasoning": "Ensure comprehensive testing and risk mitigation"},
            {"persona": "Innovator", "stance": "strongly_agree", "confidence": 0.90,
             "reasoning": "Enables faster iteration and learning cycles"},
            {"persona": "Analyst", "stance": "agree", "confidence": 0.80,
             "reasoning": "Data supports technical feasibility"},
            {"persona": "Pragmatist", "stance": "agree", "confidence": 0.82,
             "reasoning": "Resources and timing are favorable"}
        ]
        consensus = "proceed_with_caution"
        recommendations = [
            "Implement incrementally with monitoring",
            "Set up rollback procedures",
            "Document decisions and rationale",
            "Measure impact and iterate"
        ]
    
    # Architecture/Design decisions
    elif any(word in query for word in ["microservice", "architecture", "design", "pattern", "framework"]):
        perspectives = [
            {"persona": "Strategist", "stance": "agree", "confidence": 0.88,
             "reasoning": "Architectural choice supports long-term scalability"},
            {"persona": "Guardian", "stance": "neutral", "confidence": 0.70,
             "reasoning": "Consider complexity and maintenance burden"},
            {"persona": "Innovator", "stance": "strongly_agree", "confidence": 0.92,
             "reasoning": "Opens new possibilities for innovation"},
            {"persona": "Analyst", "stance": "agree", "confidence": 0.78,
             "reasoning": "Trade-offs are well understood and acceptable"},
            {"persona": "Pragmatist", "stance": "proceed_with_caution", "confidence": 0.74,
             "reasoning": "Start simple, evolve based on actual needs"}
        ]
        consensus = "proceed"
        recommendations = [
            "Begin with proof of concept",
            "Define clear boundaries and interfaces",
            "Plan for iterative refinement",
            "Establish success metrics"
        ]
    
    # Vehicle/Transportation decisions (like car seat question)
    elif any(word in query for word in ["car", "vehicle", "buy", "purchase", "carseat", "driving"]):
        perspectives = [
            {"persona": "Strategist", "stance": "agree", "confidence": 0.80,
             "reasoning": "Consider long-term value and total cost of ownership"},
            {"persona": "Guardian", "stance": "proceed_with_caution", "confidence": 0.75,
             "reasoning": "Safety ratings and reliability should be primary factors"},
            {"persona": "Innovator", "stance": "agree", "confidence": 0.85,
             "reasoning": "Look for features that will remain relevant over time"},
            {"persona": "Analyst", "stance": "agree", "confidence": 0.78,
             "reasoning": "Depreciation curves suggest 2-3 year old vehicles offer best value"},
            {"persona": "Pragmatist", "stance": "agree", "confidence": 0.76,
             "reasoning": "Balance current needs with reasonable future flexibility"}
        ]
        
        # Specific advice for car seats
        if "carseat" in query or "car seat" in query:
            consensus = "proceed"
            recommendations = [
                "Prioritize safety certifications and crash test ratings",
                "Consider convertible seats for longer usability (infant to toddler)",
                "Check compatibility with your vehicle model",
                "Balance cost with quality - mid-range often best value",
                "Look for ease of installation and cleaning features"
            ]
        else:
            consensus = "proceed"
            recommendations = [
                "Research reliability ratings and ownership costs",
                "Consider certified pre-owned for warranty + value",
                "Test drive multiple options before deciding",
                "Factor in insurance and maintenance costs"
            ]
    
    # Parenting/Family decisions
    elif any(word in query for word in ["baby", "newborn", "child", "parent", "family", "kids"]):
        perspectives = [
            {"persona": "Strategist", "stance": "agree", "confidence": 0.82,
             "reasoning": "Plan for growth and changing needs over time"},
            {"persona": "Guardian", "stance": "proceed_with_caution", "confidence": 0.85,
             "reasoning": "Safety and well-being are paramount considerations"},
            {"persona": "Innovator", "stance": "agree", "confidence": 0.75,
             "reasoning": "Explore modern solutions while respecting proven approaches"},
            {"persona": "Analyst", "stance": "agree", "confidence": 0.78,
             "reasoning": "Research-based parenting strategies show positive outcomes"},
            {"persona": "Pragmatist", "stance": "agree", "confidence": 0.80,
             "reasoning": "Focus on essentials first, add complexity gradually"}
        ]
        consensus = "proceed"
        recommendations = [
            "Trust your instincts while staying informed",
            "Build a support network of family and friends",
            "Prioritize sleep and self-care for sustainability",
            "Be flexible - what works for others may not work for you",
            "Document memories but stay present in moments"
        ]
    
    # Career/Professional decisions
    elif any(word in query for word in ["job", "career", "work", "salary", "promotion", "quit", "hire"]):
        perspectives = [
            {"persona": "Strategist", "stance": "agree", "confidence": 0.85,
             "reasoning": "Align decisions with long-term career trajectory"},
            {"persona": "Guardian", "stance": "proceed_with_caution", "confidence": 0.75,
             "reasoning": "Ensure financial stability during transitions"},
            {"persona": "Innovator", "stance": "agree", "confidence": 0.80,
             "reasoning": "Growth often requires taking calculated risks"},
            {"persona": "Analyst", "stance": "agree", "confidence": 0.77,
             "reasoning": "Market data and trends support this direction"},
            {"persona": "Pragmatist", "stance": "proceed_with_caution", "confidence": 0.78,
             "reasoning": "Have contingency plans before major changes"}
        ]
        consensus = "proceed_with_caution"
        recommendations = [
            "Network actively before making moves",
            "Negotiate from a position of strength",
            "Consider total compensation, not just salary",
            "Invest in continuous skill development",
            "Maintain emergency fund for flexibility"
        ]
    
    # Financial/Investment decisions
    elif any(word in query for word in ["invest", "money", "save", "budget", "financial", "retirement"]):
        perspectives = [
            {"persona": "Strategist", "stance": "agree", "confidence": 0.83,
             "reasoning": "Long-term financial planning is essential"},
            {"persona": "Guardian", "stance": "proceed_with_caution", "confidence": 0.88,
             "reasoning": "Risk management and diversification are critical"},
            {"persona": "Innovator", "stance": "neutral", "confidence": 0.70,
             "reasoning": "Balance innovation with proven strategies"},
            {"persona": "Analyst", "stance": "agree", "confidence": 0.85,
             "reasoning": "Historical data supports disciplined investing"},
            {"persona": "Pragmatist", "stance": "agree", "confidence": 0.82,
             "reasoning": "Start with basics: emergency fund, then invest"}
        ]
        consensus = "proceed_with_caution"
        recommendations = [
            "Diversify across asset classes",
            "Automate savings and investments",
            "Minimize fees and tax implications",
            "Review and rebalance periodically",
            "Seek professional advice for complex situations"
        ]
    
    # Generic/Philosophical questions
    else:
        perspectives = [
            {"persona": "Strategist", "stance": "agree", "confidence": 0.80,
             "reasoning": f"Long-term thinking applied to: {request.query[:80]}"},
            {"persona": "Guardian", "stance": "proceed_with_caution", "confidence": 0.75,
             "reasoning": "Consider risks and mitigation strategies"},
            {"persona": "Innovator", "stance": "agree", "confidence": 0.85,
             "reasoning": "Embrace change while learning from experience"},
            {"persona": "Analyst", "stance": "agree", "confidence": 0.78,
             "reasoning": "Evidence supports thoughtful action"},
            {"persona": "Pragmatist", "stance": "agree", "confidence": 0.76,
             "reasoning": "Focus on what's actionable and within your control"}
        ]
        consensus = "proceed"
        recommendations = [
            "Break complex decisions into smaller steps",
            "Gather diverse perspectives before committing",
            "Set measurable goals and track progress",
            "Be willing to adjust based on outcomes",
            "Learn from both successes and failures"
        ]
    
    # Add context about the Council's holistic approach
    council_note = ("The Council of Minds provides perspectives across all aspects of life - "
                    "technical, personal, financial, and professional. Each persona brings their "
                    "unique lens to help you make informed decisions.")
    
    return {
        "query": request.query,
        "consensus": consensus,
        "confidence": sum(p["confidence"] for p in perspectives) / len(perspectives),
        "perspectives": perspectives,
        "recommendations": recommendations,
        "context": request.context,
        "council_note": council_note,
        "timestamp": datetime.now().isoformat()
    }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection.established",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "subscribe":
                channel = message.get("channel")
                if channel == "orchestration":
                    manager.orchestration_subs.add(websocket)
                    await websocket.send_json({
                        "type": "subscription.confirmed",
                        "channel": channel
                    })
            
            # Echo back for testing
            await websocket.send_json({
                "type": "echo",
                "received": message,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task to simulate activity
async def simulate_activity():
    """Simulate system activity for demo."""
    while True:
        await asyncio.sleep(10)
        
        # Random resource usage updates
        for project in mock_projects:
            if project["status"] == "running":
                project["cpu_usage"] = random.uniform(20, 80)
                project["memory_usage"] = random.randint(256, 2048)
                
                await manager.broadcast({
                    "type": "resource.update",
                    "project_id": project["id"],
                    "cpu": project["cpu_usage"],
                    "memory": project["memory_usage"],
                    "timestamp": datetime.now().isoformat()
                })

# Register API routes
if VOICE_ENABLED:
    app.include_router(voice_router)
    print("✅ Voice API enabled at /api/voice")

if MOBILE_ENABLED:
    app.include_router(mobile_router)
    print("✅ Mobile API enabled at /api/mobile")

if ASSISTANT_ENABLED:
    app.include_router(assistant_router)
    print("✅ Assistant API enabled at /api/assistant")

if COMPLETE_API:
    # Include all real API implementations
    app.include_router(projects_router)
    app.include_router(deployment_router)
    app.include_router(monitoring_router)
    app.include_router(backup_router)
    app.include_router(auth_router)
    app.include_router(notification_router)
    app.include_router(orchestration_router)
    print("✅ Complete API system loaded:")
    print("   • Real project scanning")
    print("   • Deployment management")
    print("   • Resource monitoring")
    print("   • Backup & recovery")
    print("   • Authentication")
    print("   • Notifications")
    print("   • Workflow orchestration")

@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    if COMPLETE_API:
        # Create database tables
        await create_tables()
        print("✅ Database tables initialized")
    asyncio.create_task(simulate_activity())

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 OPTIMUS TEST SERVER - PHASE 2 USER TESTING")
    print("="*60)
    print("\nStarting server with:")
    if COMPLETE_API:
        print("  • ✅ REAL project scanning and monitoring")
        print("  • ✅ REAL deployment system")
        print("  • ✅ REAL resource metrics")
        print("  • ✅ REAL backup system")
    else:
        print("  • Mock projects and orchestration")
    print("  • WebSocket real-time updates")
    print("  • Council of Minds")
    print("  • All API endpoints")
    if VOICE_ENABLED:
        print("  • 🎤 ElevenLabs Voice Integration")
    if MOBILE_ENABLED:
        print("  • 📱 Mobile API with widgets and shortcuts")
    if ASSISTANT_ENABLED:
        print("  • 🤖 Unified Assistant with Life Council")
    print("\n📍 Access the dashboard at: http://localhost:8003")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8003)