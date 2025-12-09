"""
Enhanced FastAPI application with comprehensive API expansion.
Integrates all Phase 2 components with advanced features.
"""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Import all the enhanced API components
from .gateway import create_gateway_middleware, api_metrics
from .websocket_manager import websocket_manager, websocket_cleanup_task, websocket_heartbeat_task
from .auth import auth_manager, get_current_user_flexible, Permission
from .errors import error_handler, handle_api_error
from .monitoring import api_monitoring, record_api_request, increment_active_requests, decrement_active_requests
from .cache import advanced_cache, response_cache, cache_warm_up
from .transformers.pagination import get_pagination_params
from .docs.openapi_generator import generate_openapi_spec, DocumentationLevel, export_documentation

# Import integration layers
from .integration import (
    OrchestrationIntegration,
    DeploymentIntegration, 
    ResourceIntegration,
    BackupIntegration,
    CouncilIntegration
)

# Import existing routers
from . import projects, runtime, metrics, council, memory, knowledge_graph, scanner, monitor, dashboard, websocket

from ..config import get_settings, db_manager, redis_manager, logger


# Global integration instances
orchestration_integration = None
deployment_integration = None  
resource_integration = None
backup_integration = None
council_integration = None

# Background tasks
background_tasks = set()


@asynccontextmanager
async def enhanced_lifespan(app: FastAPI):
    """Enhanced application lifespan with all Phase 2 components."""
    logger.info("Starting Enhanced Optimus API...")
    
    try:
        # Initialize database and Redis
        await db_manager.initialize()
        await redis_manager.initialize()
        logger.info("Database and Redis initialized")
        
        # Initialize cache
        await cache_warm_up()
        logger.info("Cache warmed up")
        
        # Start API monitoring
        await api_monitoring.start_monitoring()
        logger.info("API monitoring started")
        
        # Start WebSocket management
        task1 = asyncio.create_task(websocket_cleanup_task())
        task2 = asyncio.create_task(websocket_heartbeat_task())
        background_tasks.add(task1)
        background_tasks.add(task2)
        logger.info("WebSocket management started")
        
        # Initialize integration layers
        async for session in db_manager.get_session():
            global orchestration_integration, deployment_integration, resource_integration
            global backup_integration, council_integration
            
            orchestration_integration = OrchestrationIntegration(session)
            deployment_integration = DeploymentIntegration(session)
            resource_integration = ResourceIntegration(session)
            backup_integration = BackupIntegration(session)
            council_integration = CouncilIntegration(session)
            
            # Start resource monitoring
            await resource_integration.start_monitoring()
            logger.info("Integration layers initialized")
            break
        
        logger.info("Enhanced Optimus API startup complete")
        
        yield
        
    finally:
        logger.info("Shutting down Enhanced Optimus API...")
        
        # Stop background tasks
        for task in background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop monitoring
        await api_monitoring.stop_monitoring()
        if resource_integration:
            await resource_integration.stop_monitoring()
        
        # Close connections
        await db_manager.close()
        await redis_manager.close()
        
        logger.info("Enhanced shutdown complete")


def create_enhanced_app() -> FastAPI:
    """Create enhanced FastAPI application with all features."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="Optimus API - Enhanced",
        description="AI-powered project orchestration platform with comprehensive features",
        version=settings.app_version,
        lifespan=enhanced_lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add middleware stack
    _setup_middleware(app)
    
    # Add enhanced routes
    _setup_routes(app)
    
    # Setup enhanced error handling
    _setup_error_handling(app)
    
    # Setup WebSocket routes
    _setup_websockets(app)
    
    return app


def _setup_middleware(app: FastAPI):
    """Setup comprehensive middleware stack."""
    settings = get_settings()
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API Gateway middleware (rate limiting, circuit breaker, etc.)
    gateway_middleware = create_gateway_middleware()
    app.add_middleware(type(gateway_middleware), app=None, config={})
    
    # Request/Response middleware for monitoring and caching
    @app.middleware("http")
    async def monitoring_middleware(request: Request, call_next):
        # Increment active requests
        increment_active_requests()
        
        # Generate request ID
        request_id = f"req_{int(datetime.now().timestamp() * 1000)}"
        request.state.request_id = request_id
        
        start_time = datetime.now()
        
        try:
            # Check cache for GET requests
            if request.method == "GET":
                cached_response = await response_cache.get_cached_response(request)
                if cached_response:
                    content, etag = cached_response
                    
                    # Check conditional request
                    if response_cache.check_if_none_match(request, etag):
                        return Response(status_code=304, headers={"ETag": etag})
                    
                    return JSONResponse(
                        content=content,
                        headers={"ETag": etag, "X-Cache": "HIT", "X-Request-ID": request_id}
                    )
            
            # Process request
            response = await call_next(request)
            
            # Cache successful GET responses
            if request.method == "GET" and response.status_code == 200:
                # This would need to be implemented properly with response body capture
                pass
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{(datetime.now() - start_time).total_seconds():.3f}s"
            
            # Record metrics
            duration = (datetime.now() - start_time).total_seconds()
            await record_api_request(request, response, duration, request_id)
            
            return response
            
        finally:
            # Decrement active requests
            decrement_active_requests()
    
    logger.info("Middleware stack configured")


def _setup_routes(app: FastAPI):
    """Setup all API routes with enhanced features."""
    settings = get_settings()
    
    # Include existing routers with enhanced features
    app.include_router(
        projects.router,
        prefix=f"{settings.api_prefix}/projects",
        tags=["projects"],
        dependencies=[Depends(get_current_user_flexible)]
    )
    
    app.include_router(
        runtime.router,
        prefix=f"{settings.api_prefix}/runtime",
        tags=["runtime"],
        dependencies=[Depends(get_current_user_flexible)]
    )
    
    app.include_router(
        council.router,
        prefix=f"{settings.api_prefix}/council",
        tags=["council"],
        dependencies=[Depends(get_current_user_flexible)]
    )
    
    # Enhanced orchestration endpoints
    @app.post(f"{settings.api_prefix}/orchestration/requests")
    async def submit_orchestration_request(
        request_data: dict,
        user = Depends(get_current_user_flexible)
    ):
        """Submit orchestration request with enhanced features."""
        if not orchestration_integration:
            raise HTTPException(status_code=503, detail="Orchestration service unavailable")
        
        from .transformers.request_validators import validate_orchestration_request
        validated_data = validate_orchestration_request(request_data)
        validated_data["user_id"] = user.id
        
        request_id = await orchestration_integration.submit_orchestration_request(validated_data)
        
        return {
            "success": True,
            "data": {"request_id": request_id},
            "message": "Orchestration request submitted successfully"
        }
    
    @app.get(f"{settings.api_prefix}/orchestration/requests/{{request_id}}/status")
    async def get_orchestration_status(
        request_id: str,
        user = Depends(get_current_user_flexible)
    ):
        """Get orchestration request status."""
        if not orchestration_integration:
            raise HTTPException(status_code=503, detail="Orchestration service unavailable")
        
        status = await orchestration_integration.get_orchestration_status(request_id)
        if not status:
            raise HTTPException(status_code=404, detail="Orchestration request not found")
        
        from .transformers.response_serializers import serialize_orchestration_response
        return {
            "success": True,
            "data": serialize_orchestration_response(status.dict())
        }
    
    # Enhanced deployment endpoints
    @app.post(f"{settings.api_prefix}/deployments")
    async def submit_deployment(
        deployment_data: dict,
        user = Depends(get_current_user_flexible)
    ):
        """Submit deployment with enhanced pipeline management."""
        if not deployment_integration:
            raise HTTPException(status_code=503, detail="Deployment service unavailable")
        
        from .transformers.request_validators import validate_deployment_request
        validated_data = validate_deployment_request(deployment_data)
        validated_data["user_id"] = user.id
        
        deployment_id = await deployment_integration.submit_deployment(validated_data)
        
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "data": {"deployment_id": deployment_id},
                "message": "Deployment initiated successfully"
            }
        )
    
    # Council integration endpoints
    @app.post(f"{settings.api_prefix}/council/deliberations")
    async def start_deliberation(
        deliberation_data: dict,
        user = Depends(get_current_user_flexible)
    ):
        """Start Council deliberation with enhanced tracking."""
        if not council_integration:
            raise HTTPException(status_code=503, detail="Council service unavailable")
        
        from .transformers.request_validators import validate_council_request
        validated_data = validate_council_request(deliberation_data)
        validated_data["user_id"] = user.id
        
        deliberation_id = await council_integration.start_deliberation(validated_data)
        
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "data": {"deliberation_id": deliberation_id},
                "message": "Deliberation started successfully"
            }
        )
    
    # System monitoring endpoints
    @app.get(f"{settings.api_prefix}/monitoring/health")
    async def get_system_health(user = Depends(get_current_user_flexible)):
        """Get comprehensive system health status."""
        if not resource_integration:
            raise HTTPException(status_code=503, detail="Monitoring service unavailable")
        
        health_data = await resource_integration.get_system_health()
        return {
            "success": True,
            "data": health_data
        }
    
    @app.get(f"{settings.api_prefix}/monitoring/metrics")
    async def get_api_metrics(user = Depends(get_current_user_flexible)):
        """Get API performance metrics."""
        stats = await api_monitoring.get_performance_stats()
        return {
            "success": True,
            "data": stats.__dict__
        }
    
    # Authentication endpoints
    @app.post(f"{settings.api_prefix}/auth/login")
    async def login(login_data: dict):
        """Enhanced login with JWT tokens."""
        username = login_data.get("username")
        password = login_data.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        
        user = await auth_manager.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = auth_manager.create_access_token(user)
        refresh_token = auth_manager.create_refresh_token(user)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": auth_manager.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        }
    
    # Export documentation
    @app.get(f"{settings.api_prefix}/docs/export")
    async def export_api_docs(
        format: str = "json",
        level: str = "standard",
        user = Depends(get_current_user_flexible)
    ):
        """Export API documentation in various formats."""
        try:
            doc_level = DocumentationLevel(level)
        except ValueError:
            doc_level = DocumentationLevel.STANDARD
        
        spec = generate_openapi_spec(app, doc_level)
        
        if format.lower() == "yaml":
            from .docs.openapi_generator import OpenAPIGenerator
            generator = OpenAPIGenerator(app)
            content = generator.export_yaml(spec)
            media_type = "application/x-yaml"
        else:
            import json
            content = json.dumps(spec, indent=2)
            media_type = "application/json"
        
        return Response(content=content, media_type=media_type)
    
    logger.info("Enhanced routes configured")


def _setup_error_handling(app: FastAPI):
    """Setup comprehensive error handling."""
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all exceptions with enhanced error responses."""
        return await handle_api_error(request, exc)
    
    logger.info("Enhanced error handling configured")


def _setup_websockets(app: FastAPI):
    """Setup enhanced WebSocket endpoints."""
    @app.websocket("/ws/enhanced/{channel}")
    async def enhanced_websocket_endpoint(websocket, channel: str):
        """Enhanced WebSocket endpoint with channel support."""
        client_ip = websocket.client.host if websocket.client else "unknown"
        user_agent = websocket.headers.get("user-agent", "unknown")
        
        connection_id = await websocket_manager.connect(websocket, client_ip, user_agent)
        
        try:
            while True:
                data = await websocket.receive_text()
                await websocket_manager.handle_message(connection_id, data)
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await websocket_manager.disconnect(connection_id)
    
    # Include existing WebSocket routes
    app.include_router(
        websocket.router,
        prefix="/ws",
        tags=["websocket"]
    )
    
    logger.info("Enhanced WebSocket endpoints configured")


# Create the enhanced app instance
enhanced_app = create_enhanced_app()


if __name__ == "__main__":
    settings = get_settings()
    
    # Export documentation on startup in development
    if settings.debug:
        try:
            export_documentation(enhanced_app, "docs/generated", DocumentationLevel.COMPREHENSIVE)
        except Exception as e:
            logger.warning(f"Failed to export documentation: {e}")
    
    # Run the enhanced application
    uvicorn.run(
        "src.api.enhanced_main:enhanced_app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        workers=1 if settings.debug else 4
    )