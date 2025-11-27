"""
FastAPI application for Optimus backend.
Main entry point with routing, middleware, and application lifecycle management.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Set

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings, db_manager, redis_manager, logger
from .api import projects, runtime, metrics, council, memory, knowledge_graph, scanner, monitor, dashboard, websocket
from .services import ProjectScanner, RuntimeMonitor


# Background monitoring task
background_monitor_task = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.deliberation_subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # Remove from deliberation subscriptions
        for deliberation_id, subscribers in self.deliberation_subscribers.items():
            subscribers.discard(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

    def subscribe_to_deliberation(self, deliberation_id: str, websocket: WebSocket):
        if deliberation_id not in self.deliberation_subscribers:
            self.deliberation_subscribers[deliberation_id] = set()
        self.deliberation_subscribers[deliberation_id].add(websocket)

    async def send_to_deliberation_subscribers(self, deliberation_id: str, message: dict):
        if deliberation_id in self.deliberation_subscribers:
            subscribers = list(self.deliberation_subscribers[deliberation_id])
            for websocket in subscribers:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending to subscriber: {e}")
                    self.deliberation_subscribers[deliberation_id].discard(websocket)

websocket_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Optimus backend...")
    
    try:
        # Initialize database
        await db_manager.initialize()
        logger.info("Database initialized")
        
        # Initialize Redis
        await redis_manager.initialize()
        logger.info("Redis initialized")
        
        # Start background monitoring (disabled for testing)
        # global background_monitor_task
        # background_monitor_task = asyncio.create_task(start_background_monitoring())
        logger.info("Background monitoring disabled for testing")
        
        yield
        
    finally:
        logger.info("Shutting down Optimus backend...")
        
        # Cancel background tasks (disabled for testing)
        # if background_monitor_task and not background_monitor_task.done():
        #     background_monitor_task.cancel()
        #     try:
        #         await background_monitor_task
        #     except asyncio.CancelledError:
        #         pass
        
        # Close connections
        await db_manager.close()
        await redis_manager.close()
        
        logger.info("Shutdown complete")


async def start_background_monitoring():
    """Start background monitoring tasks."""
    settings = get_settings()
    
    try:
        while True:
            try:
                async for session in db_manager.get_session():
                    monitor = RuntimeMonitor(session)
                    await monitor.monitor_cycle()
                    break
                    
                await asyncio.sleep(settings.monitor_interval)
                
            except asyncio.CancelledError:
                logger.info("Background monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background monitoring: {e}", exc_info=True)
                await asyncio.sleep(30)  # Wait before retrying
                
    except asyncio.CancelledError:
        logger.info("Background monitoring task cancelled")


# Create FastAPI application
settings = get_settings()
app = FastAPI(
    title="Optimus Backend",
    description="AI-powered project orchestration and management platform",
    version=settings.app_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency for database session
async def get_db_session():
    """Get database session dependency."""
    async for session in db_manager.get_session():
        yield session


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "type": "http_error"}
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": "internal_error",
            "message": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "optimus-backend",
        "version": settings.app_version
    }


# WebSocket endpoint for real-time deliberations
@app.websocket("/ws/deliberation/{deliberation_id}")
async def websocket_deliberation(websocket: WebSocket, deliberation_id: str):
    """WebSocket endpoint for real-time deliberation updates."""
    await websocket_manager.connect(websocket)
    websocket_manager.subscribe_to_deliberation(deliberation_id, websocket)
    
    try:
        # Send connection confirmation
        await websocket_manager.send_personal_message({
            "type": "connection_established",
            "data": {
                "deliberation_id": deliberation_id,
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                elif message.get("type") == "subscribe":
                    # Handle subscription to different deliberation
                    new_deliberation_id = message.get("deliberation_id")
                    if new_deliberation_id:
                        websocket_manager.subscribe_to_deliberation(new_deliberation_id, websocket)
                        await websocket_manager.send_personal_message({
                            "type": "subscription_confirmed",
                            "data": {"deliberation_id": new_deliberation_id},
                            "timestamp": datetime.now().isoformat()
                        }, websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"},
                    "timestamp": datetime.now().isoformat()
                }, websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": str(e)},
                    "timestamp": datetime.now().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        websocket_manager.disconnect(websocket)


# Global WebSocket endpoint for system updates
@app.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    """WebSocket endpoint for system-wide updates."""
    await websocket_manager.connect(websocket)
    
    try:
        await websocket_manager.send_personal_message({
            "type": "system_connected",
            "data": {"status": "connected"},
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"System WebSocket error: {e}")
                
    except WebSocketDisconnect:
        pass
    finally:
        websocket_manager.disconnect(websocket)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Optimus Backend",
        "version": settings.app_version,
        "description": "AI-powered project orchestration platform",
        "api_prefix": settings.api_prefix,
        "endpoints": {
            "health": "/health",
            "projects": f"{settings.api_prefix}/projects",
            "runtime": f"{settings.api_prefix}/runtime", 
            "metrics": f"{settings.api_prefix}/metrics",
            "council": f"{settings.api_prefix}/council",
            "memory": f"{settings.api_prefix}/memory",
            "knowledge_graph": f"{settings.api_prefix}/graph",
            "scanner": f"{settings.api_prefix}/scanner",
            "monitor": f"{settings.api_prefix}/monitor",
            "dashboard": f"{settings.api_prefix}/dashboard",
            "websocket": "/ws"
        }
    }


# Include API routers
app.include_router(
    projects.router,
    prefix=f"{settings.api_prefix}/projects",
    tags=["projects"]
)

app.include_router(
    runtime.router,
    prefix=f"{settings.api_prefix}/runtime",
    tags=["runtime"]
)

app.include_router(
    metrics.router,
    prefix=f"{settings.api_prefix}/metrics",
    tags=["metrics"]
)

app.include_router(
    council.router,
    prefix=f"{settings.api_prefix}/council",
    tags=["council"]
)

# Include new API routers
app.include_router(
    memory.router,
    prefix=f"{settings.api_prefix}/memory",
    tags=["memory"]
)

app.include_router(
    knowledge_graph.router,
    prefix=f"{settings.api_prefix}/graph",
    tags=["knowledge_graph"]
)

app.include_router(
    scanner.router,
    prefix=f"{settings.api_prefix}/scanner",
    tags=["scanner"]
)

app.include_router(
    monitor.router,
    prefix=f"{settings.api_prefix}/monitor",
    tags=["monitor"]
)

app.include_router(
    dashboard.router,
    prefix=f"{settings.api_prefix}/dashboard",
    tags=["dashboard"]
)

# Include WebSocket routes
app.include_router(
    websocket.router,
    prefix="/ws",
    tags=["websocket"]
)

# Set websocket manager for council API
council.set_websocket_manager(websocket_manager)


# Scan projects endpoint (manual trigger)
@app.post(f"{settings.api_prefix}/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    base_path: str = None,
    session: AsyncSession = Depends(get_db_session)
):
    """Manually trigger a project scan."""
    try:
        scanner = ProjectScanner(session)
        
        # Run scan in background
        background_tasks.add_task(
            scanner.scan_and_save_all,
            base_path
        )
        
        return {
            "message": "Project scan initiated",
            "base_path": base_path or settings.projects_base_path,
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Error triggering scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate scan")


# Monitor endpoint (manual trigger)
@app.post(f"{settings.api_prefix}/monitor")
async def trigger_monitor(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session)
):
    """Manually trigger a monitoring cycle."""
    try:
        monitor = RuntimeMonitor(session)
        
        # Run monitor cycle in background
        background_tasks.add_task(monitor.monitor_cycle)
        
        return {
            "message": "Monitoring cycle initiated",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Error triggering monitor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate monitoring")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8005,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )