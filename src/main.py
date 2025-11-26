"""
FastAPI application for Optimus backend.
Main entry point with routing, middleware, and application lifecycle management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings, db_manager, redis_manager, logger
from .api import projects, runtime, metrics
from .services import ProjectScanner, RuntimeMonitor


# Background monitoring task
background_monitor_task = None


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
        
        # Start background monitoring
        global background_monitor_task
        background_monitor_task = asyncio.create_task(start_background_monitoring())
        logger.info("Background monitoring started")
        
        yield
        
    finally:
        logger.info("Shutting down Optimus backend...")
        
        # Cancel background tasks
        if background_monitor_task and not background_monitor_task.done():
            background_monitor_task.cancel()
            try:
                await background_monitor_task
            except asyncio.CancelledError:
                pass
        
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
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
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
        port=8002,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )