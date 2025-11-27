"""
Troubleshooting API Endpoints
============================

REST API endpoints for the Smart Troubleshooting Engine.
Provides endpoints for error analysis, solution finding,
automated fixes, and learning from troubleshooting sessions.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.config import get_session
from ..council.memory_integration import get_memory_integration
from ..council.knowledge_graph_integration import get_knowledge_graph_integration
from ..services.troubleshooting_engine import TroubleshootingEngine
from ..services.solution_library import SolutionLibrary
from ..services.auto_fixer import AutoFixer, ExecutionContext
from ..services.solution_search import SolutionSearchService
from ..services.troubleshooting_integration import TroubleshootingIntegrationService
from ..services.runtime_monitor import RuntimeMonitor

logger = logging.getLogger("optimus.api.troubleshooting")

router = APIRouter(prefix="/api/troubleshooting", tags=["troubleshooting"])


# Request/Response Models
class ErrorAnalysisRequest(BaseModel):
    """Request model for error analysis."""
    error_message: str = Field(..., description="The error message to analyze")
    project_id: Optional[str] = Field(None, description="Project ID where error occurred")
    language: Optional[str] = Field(None, description="Programming language")
    framework: Optional[str] = Field(None, description="Framework or library")
    file_path: Optional[str] = Field(None, description="File where error occurred")
    line_number: Optional[int] = Field(None, description="Line number of error")
    stack_trace: Optional[str] = Field(None, description="Full stack trace")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ErrorAnalysisResponse(BaseModel):
    """Response model for error analysis."""
    error_hash: str
    error_type: str
    severity: str
    category: str
    language: Optional[str]
    framework: Optional[str]
    confidence: float
    similar_errors: List[str]
    analysis_time_ms: int


class SolutionRequest(BaseModel):
    """Request model for finding solutions."""
    error_analysis: ErrorAnalysisResponse
    project_context: Optional[Dict[str, Any]] = None
    max_results: int = Field(10, le=50, description="Maximum number of solutions to return")
    include_external: bool = Field(True, description="Include external search results")


class SolutionResponse(BaseModel):
    """Response model for solutions."""
    solution_id: str
    title: str
    description: str
    confidence: float
    success_rate: float
    category: str
    risk_level: str
    requires_approval: bool
    estimated_time_ms: Optional[int]
    source: str  # internal, stackoverflow, github, memory
    metadata: Dict[str, Any]


class FixRequest(BaseModel):
    """Request model for executing fixes."""
    solution_id: str
    project_id: str
    working_directory: str
    environment_vars: Optional[Dict[str, str]] = None
    dry_run: bool = Field(True, description="Execute in dry run mode")
    force_approval: bool = Field(False, description="Skip approval checks")
    timeout_seconds: int = Field(300, le=600, description="Execution timeout")


class FixResponse(BaseModel):
    """Response model for fix execution."""
    attempt_id: str
    success: bool
    error_resolved: bool
    execution_time_ms: int
    commands_executed: List[str]
    output: str
    error_output: Optional[str]
    verification_passed: bool
    rollback_available: bool
    metadata: Dict[str, Any]


class TroubleshootingSessionRequest(BaseModel):
    """Request model for troubleshooting sessions."""
    project_id: str
    error_message: str
    user_context: Optional[Dict[str, Any]] = None


class TroubleshootingSessionResponse(BaseModel):
    """Response model for troubleshooting sessions."""
    session_id: str
    error_analysis: ErrorAnalysisResponse
    solutions: List[SolutionResponse]
    context_insights: Dict[str, Any]
    recommendations: List[Dict[str, Any]]


class LearningFeedbackRequest(BaseModel):
    """Request model for learning feedback."""
    session_id: str
    successful_solution_id: Optional[str] = None
    user_satisfaction: Optional[int] = Field(None, ge=1, le=5, description="User satisfaction (1-5)")
    resolution_time_minutes: Optional[int] = None
    feedback_notes: Optional[str] = None
    preferred_solution_type: Optional[str] = None


class PredictiveInsightsResponse(BaseModel):
    """Response model for predictive insights."""
    project_id: str
    potential_issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    confidence_score: float
    analysis_timestamp: str


# Dependency injection
async def get_troubleshooting_engine(session: AsyncSession = Depends(get_session)) -> TroubleshootingEngine:
    """Get troubleshooting engine instance."""
    memory = await get_memory_integration()
    kg = await get_knowledge_graph_integration()
    return TroubleshootingEngine(session, memory, kg)


async def get_solution_library(session: AsyncSession = Depends(get_session)) -> SolutionLibrary:
    """Get solution library instance."""
    return SolutionLibrary(session)


async def get_auto_fixer(session: AsyncSession = Depends(get_session)) -> AutoFixer:
    """Get auto fixer instance."""
    return AutoFixer(session)


async def get_troubleshooting_integration(
    session: AsyncSession = Depends(get_session)
) -> TroubleshootingIntegrationService:
    """Get troubleshooting integration service."""
    memory = await get_memory_integration()
    kg = await get_knowledge_graph_integration()
    engine = TroubleshootingEngine(session, memory, kg)
    # runtime_monitor would be injected here in real implementation
    return TroubleshootingIntegrationService(session, memory, kg, engine)


# Active troubleshooting sessions
active_sessions: Dict[str, Dict[str, Any]] = {}


# API Endpoints
@router.post("/analyze", response_model=ErrorAnalysisResponse)
async def analyze_error(
    request: ErrorAnalysisRequest,
    engine: TroubleshootingEngine = Depends(get_troubleshooting_engine)
):
    """
    Analyze an error message and extract structured information.
    
    This endpoint performs intelligent error analysis including:
    - Error type classification
    - Severity assessment  
    - Language and framework detection
    - Confidence scoring
    - Similar error identification
    """
    try:
        start_time = datetime.now()
        
        # Build context from request
        context = {}
        if request.project_id:
            context["project_id"] = request.project_id
        if request.language:
            context["language"] = request.language
        if request.framework:
            context["framework"] = request.framework
        if request.file_path:
            context["file_path"] = request.file_path
        if request.line_number:
            context["line_number"] = request.line_number
        if request.additional_context:
            context.update(request.additional_context)
        
        # Perform analysis
        analysis = await engine.analyze_error(request.error_message, context)
        
        analysis_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return ErrorAnalysisResponse(
            error_hash=analysis.error_hash,
            error_type=analysis.error_type,
            severity=analysis.severity,
            category=analysis.category,
            language=analysis.language,
            framework=analysis.framework,
            confidence=analysis.confidence,
            similar_errors=analysis.similar_errors,
            analysis_time_ms=analysis_time
        )
        
    except Exception as e:
        logger.error(f"Error analyzing error message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analysis failed: {str(e)}"
        )


@router.post("/solutions", response_model=List[SolutionResponse])
async def find_solutions(
    request: SolutionRequest,
    background_tasks: BackgroundTasks,
    engine: TroubleshootingEngine = Depends(get_troubleshooting_engine)
):
    """
    Find solutions for an analyzed error.
    
    Returns ranked solutions from multiple sources:
    - Internal solution library
    - Memory patterns from past successes
    - Knowledge graph from similar projects
    - External sources (Stack Overflow, GitHub) if enabled
    """
    try:
        # Convert request to ErrorAnalysis
        from ..services.troubleshooting_engine import ErrorAnalysis
        
        analysis = ErrorAnalysis(
            error_hash=request.error_analysis.error_hash,
            error_type=request.error_analysis.error_type,
            severity=request.error_analysis.severity,
            category=request.error_analysis.category,
            message="",  # Not included in response model
            stack_trace=None,
            file_path=None,
            line_number=None,
            language=request.error_analysis.language,
            framework=request.error_analysis.framework,
            confidence=request.error_analysis.confidence,
            similar_errors=request.error_analysis.similar_errors
        )
        
        # Find solutions
        solutions = await engine.find_solutions(analysis, request.project_context)
        
        # Convert to response format
        solution_responses = []
        for solution in solutions[:request.max_results]:
            solution_response = SolutionResponse(
                solution_id=solution.solution_id,
                title=solution.title,
                description=solution.description,
                confidence=solution.confidence,
                success_rate=solution.success_rate,
                category=solution.category,
                risk_level=solution.risk_level,
                requires_approval=solution.requires_approval,
                estimated_time_ms=solution.estimated_time_ms,
                source=solution.metadata.get("source", "internal"),
                metadata=solution.metadata
            )
            solution_responses.append(solution_response)
        
        # Search external sources in background if enabled
        if request.include_external and len(solution_responses) < 5:
            background_tasks.add_task(
                _search_external_solutions_background,
                request.error_analysis,
                request.project_context
            )
        
        return solution_responses
        
    except Exception as e:
        logger.error(f"Error finding solutions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Solution search failed: {str(e)}"
        )


@router.post("/fix", response_model=FixResponse)
async def execute_fix(
    request: FixRequest,
    fixer: AutoFixer = Depends(get_auto_fixer),
    engine: TroubleshootingEngine = Depends(get_troubleshooting_engine)
):
    """
    Execute an automated fix with safety checks.
    
    Features:
    - Dry run mode for safe testing
    - Comprehensive safety checks
    - Automatic rollback on failure
    - Verification after execution
    - Resource monitoring during execution
    """
    try:
        # Get solution details
        solutions = await engine.find_solutions_by_id(request.solution_id)
        if not solutions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Solution not found: {request.solution_id}"
            )
        
        solution = solutions[0]
        
        # Create execution context
        context = ExecutionContext(
            working_directory=request.working_directory,
            environment_vars=request.environment_vars or {},
            timeout_seconds=request.timeout_seconds,
            allow_sudo=False,  # Never allow sudo through API
            allow_network=True
        )
        
        # Execute fix
        fix_result = await fixer.execute_fix(
            solution,
            context,
            dry_run=request.dry_run,
            force_approval=request.force_approval
        )
        
        # Learn from outcome in background
        if not request.dry_run:
            # Create minimal error analysis for learning
            from ..services.troubleshooting_engine import ErrorAnalysis
            
            analysis = ErrorAnalysis(
                error_hash="api_fix",
                error_type="api_requested_fix",
                severity="medium",
                category="unknown",
                message="Fix requested via API",
                stack_trace=None,
                file_path=None,
                line_number=None,
                language=None,
                framework=None,
                confidence=0.8,
                context={"project_id": request.project_id}
            )
            
            await engine.learn_from_outcome(fix_result, analysis, request.solution_id)
        
        return FixResponse(
            attempt_id=fix_result.attempt_id,
            success=fix_result.success,
            error_resolved=fix_result.error_resolved,
            execution_time_ms=fix_result.execution_time_ms,
            commands_executed=fix_result.commands_executed,
            output=fix_result.output,
            error_output=fix_result.error_output,
            verification_passed=fix_result.verification_passed,
            rollback_available=fix_result.rollback_available,
            metadata=fix_result.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing fix: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fix execution failed: {str(e)}"
        )


@router.post("/session", response_model=TroubleshootingSessionResponse)
async def start_troubleshooting_session(
    request: TroubleshootingSessionRequest,
    integration: TroubleshootingIntegrationService = Depends(get_troubleshooting_integration)
):
    """
    Start a comprehensive troubleshooting session with context awareness.
    
    Provides:
    - Rich context analysis from project history
    - Memory-enhanced error analysis
    - Context-aware solution recommendations
    - Predictive insights and recommendations
    """
    try:
        session_id = str(uuid.uuid4())
        
        # Analyze error with full context
        analysis, context = await integration.analyze_error_with_context(
            request.error_message,
            request.project_id,
            request.user_context
        )
        
        # Find context-aware solutions
        solutions = await integration.find_context_aware_solutions(analysis, context)
        
        # Get predictive insights
        insights = await integration.get_predictive_insights(request.project_id)
        
        # Store session
        active_sessions[session_id] = {
            "created_at": datetime.now(),
            "project_id": request.project_id,
            "analysis": analysis,
            "context": context,
            "solutions": solutions,
            "user_context": request.user_context
        }
        
        # Convert to response format
        solution_responses = [
            SolutionResponse(
                solution_id=solution.solution_id,
                title=solution.title,
                description=solution.description,
                confidence=solution.confidence,
                success_rate=solution.success_rate,
                category=solution.category,
                risk_level=solution.risk_level,
                requires_approval=solution.requires_approval,
                estimated_time_ms=solution.estimated_time_ms,
                source=solution.metadata.get("source", "internal"),
                metadata=solution.metadata
            )
            for solution in solutions
        ]
        
        return TroubleshootingSessionResponse(
            session_id=session_id,
            error_analysis=ErrorAnalysisResponse(
                error_hash=analysis.error_hash,
                error_type=analysis.error_type,
                severity=analysis.severity,
                category=analysis.category,
                language=analysis.language,
                framework=analysis.framework,
                confidence=analysis.confidence,
                similar_errors=analysis.similar_errors,
                analysis_time_ms=0
            ),
            solutions=solution_responses,
            context_insights={
                "project_type": context.project_type,
                "tech_stack": context.tech_stack,
                "similar_projects": context.similar_projects,
                "team_expertise": context.team_expertise,
                "historical_patterns": context.historical_patterns
            },
            recommendations=insights.get("recommendations", [])
        )
        
    except Exception as e:
        logger.error(f"Error starting troubleshooting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start troubleshooting session: {str(e)}"
        )


@router.post("/session/{session_id}/feedback")
async def provide_learning_feedback(
    session_id: str,
    request: LearningFeedbackRequest,
    integration: TroubleshootingIntegrationService = Depends(get_troubleshooting_integration)
):
    """
    Provide feedback on a troubleshooting session for learning.
    
    Helps the system learn from:
    - Which solutions worked
    - User preferences and satisfaction
    - Time to resolution
    - Team-specific patterns
    """
    try:
        if session_id not in active_sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Troubleshooting session not found: {session_id}"
            )
        
        session_data = active_sessions[session_id]
        
        # Find successful solution
        successful_solution = None
        if request.successful_solution_id:
            successful_solution = next(
                (s for s in session_data["solutions"] if s.solution_id == request.successful_solution_id),
                None
            )
        
        # Prepare user feedback
        user_feedback = {
            "satisfaction": request.user_satisfaction,
            "resolution_time_minutes": request.resolution_time_minutes,
            "notes": request.feedback_notes,
            "preferred_solution": request.successful_solution_id,
            "preferred_solution_type": request.preferred_solution_type
        }
        
        # Learn from session
        await integration.learn_from_troubleshooting_session(
            session_id,
            session_data["analysis"],
            session_data["context"],
            session_data["solutions"],
            successful_solution,
            user_feedback
        )
        
        # Clean up session
        del active_sessions[session_id]
        
        return {"status": "feedback_received", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing learning feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process feedback: {str(e)}"
        )


@router.get("/insights/{project_id}", response_model=PredictiveInsightsResponse)
async def get_predictive_insights(
    project_id: str,
    integration: TroubleshootingIntegrationService = Depends(get_troubleshooting_integration)
):
    """
    Get predictive insights about potential issues for a project.
    
    Provides:
    - Potential issues based on current metrics
    - Historical pattern analysis
    - Proactive recommendations
    - Cross-project learning insights
    """
    try:
        insights = await integration.get_predictive_insights(project_id)
        
        # Calculate overall confidence score
        potential_issues = insights.get("potential_issues", [])
        avg_confidence = 0.0
        if potential_issues:
            avg_confidence = sum(issue.get("confidence", 0.0) for issue in potential_issues) / len(potential_issues)
        
        return PredictiveInsightsResponse(
            project_id=project_id,
            potential_issues=potential_issues,
            recommendations=insights.get("recommendations", []),
            confidence_score=avg_confidence,
            analysis_timestamp=insights.get("timestamp", datetime.now().isoformat())
        )
        
    except Exception as e:
        logger.error(f"Error getting predictive insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get predictive insights: {str(e)}"
        )


@router.get("/statistics")
async def get_troubleshooting_statistics(
    engine: TroubleshootingEngine = Depends(get_troubleshooting_engine),
    library: SolutionLibrary = Depends(get_solution_library)
):
    """
    Get comprehensive troubleshooting system statistics.
    
    Returns:
    - Error pattern analysis
    - Solution effectiveness metrics
    - Fix attempt success rates
    - System performance metrics
    """
    try:
        # Get engine statistics
        engine_stats = await engine.get_troubleshooting_statistics()
        
        # Get library statistics
        library_stats = await library.get_solution_statistics()
        
        return {
            "troubleshooting_engine": engine_stats,
            "solution_library": library_stats,
            "active_sessions": len(active_sessions),
            "system_status": "operational",
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting troubleshooting statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# Background tasks
async def _search_external_solutions_background(
    error_analysis: ErrorAnalysisResponse,
    project_context: Optional[Dict[str, Any]]
):
    """Background task to search external sources for additional solutions."""
    try:
        async with SolutionSearchService() as search_service:
            # This would search external sources and store results
            # Implementation would depend on having API keys configured
            logger.info(f"Searching external sources for {error_analysis.error_type}")
            
    except Exception as e:
        logger.error(f"Error in background external search: {e}")


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint for troubleshooting system."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(active_sessions),
            "components": {
                "troubleshooting_engine": "operational",
                "solution_library": "operational",
                "auto_fixer": "operational",
                "integration_service": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Troubleshooting system is unhealthy"
        )