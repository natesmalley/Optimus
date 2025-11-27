"""
Memory System API Endpoints
===========================

Comprehensive REST API for the Optimus Memory System.
Provides endpoints for deliberations, persona memories, patterns, search, and analytics.

Features:
- Complete deliberation history and retrieval
- Persona-specific memory access and analytics
- Semantic memory search with similarity scoring
- Learning pattern analysis and insights
- Memory consolidation and health monitoring
- Real-time memory statistics and performance metrics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from ..config import get_db_session
from ..council.memory_system import get_memory_system, MemoryQuery, MemoryRecall
from ..models.memory import (
    DeliberationMemory, 
    PersonaResponseMemory, 
    ContextMemory,
    PersonaLearningPattern,
    MemoryAssociation,
    MemoryMetrics
)

logger = logging.getLogger(__name__)
router = APIRouter()

# =================== REQUEST/RESPONSE MODELS ===================

class DeliberationResponse(BaseModel):
    """Response model for deliberation data"""
    id: str
    query: str
    topic: str
    consensus_result: Dict[str, Any]
    consensus_confidence: float
    consensus_method: str
    deliberation_time: float
    persona_count: int
    tags: List[str]
    importance_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class PersonaResponseResponse(BaseModel):
    """Response model for persona response data"""
    id: str
    deliberation_id: str
    persona_name: str
    persona_role: str
    response: str
    reasoning: str
    confidence: float
    response_time: float
    tools_used: List[str]
    context_considered: Dict[str, Any]
    agreement_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class MemorySearchRequest(BaseModel):
    """Request model for memory search"""
    query: str = Field(..., description="Search query text")
    persona_name: Optional[str] = Field(None, description="Filter by persona name")
    topic: Optional[str] = Field(None, description="Filter by topic")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    min_relevance: float = Field(0.3, ge=0.0, le=1.0, description="Minimum relevance score")
    include_context: bool = Field(True, description="Include context memories")
    days_back: Optional[int] = Field(None, ge=1, le=365, description="Limit to last N days")


class MemorySearchResponse(BaseModel):
    """Response model for memory search results"""
    memories: List[DeliberationResponse]
    relevance_scores: List[float]
    context_memories: List[Dict[str, Any]]
    learning_patterns: List[Dict[str, Any]]
    total_found: int
    query_time: float


class LearningPatternResponse(BaseModel):
    """Response model for learning patterns"""
    id: str
    persona_name: str
    pattern_type: str
    pattern_context: str
    pattern_data: Dict[str, Any]
    strength: float
    confidence: float
    observation_count: int
    last_reinforced: datetime
    
    class Config:
        from_attributes = True


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics"""
    total_deliberations: int
    total_responses: int
    total_patterns: int
    total_associations: int
    latest_deliberation: Optional[datetime]
    average_confidence: float
    top_personas: List[Dict[str, Any]]
    memory_growth_trend: List[Dict[str, Any]]


class PersonaMemorySummary(BaseModel):
    """Response model for persona memory summary"""
    persona_name: str
    total_responses: int
    average_confidence: float
    learning_patterns: int
    strongest_patterns: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


# =================== ENDPOINTS ===================

@router.get("/deliberations", response_model=List[DeliberationResponse])
async def list_deliberations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum consensus confidence"),
    since: Optional[datetime] = Query(None, description="Get deliberations since this date"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List all stored deliberations with filtering and pagination.
    
    Returns comprehensive deliberation records with consensus results,
    persona counts, and importance scores.
    """
    try:
        query = select(DeliberationMemory)
        
        # Apply filters
        filters = []
        if topic:
            filters.append(DeliberationMemory.topic == topic)
        if min_confidence is not None:
            filters.append(DeliberationMemory.consensus_confidence >= min_confidence)
        if since:
            filters.append(DeliberationMemory.created_at >= since)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Order by recency and apply pagination
        query = query.order_by(desc(DeliberationMemory.created_at)).offset(skip).limit(limit)
        
        result = await session.execute(query)
        deliberations = result.scalars().all()
        
        return [DeliberationResponse.from_orm(d) for d in deliberations]
        
    except Exception as e:
        logger.error(f"Error listing deliberations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve deliberations")


@router.get("/deliberations/{deliberation_id}", response_model=DeliberationResponse)
async def get_deliberation(
    deliberation_id: str,
    include_responses: bool = Query(False, description="Include persona responses"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed information about a specific deliberation.
    
    Optionally includes all persona responses and their reasoning.
    """
    try:
        query = select(DeliberationMemory).where(DeliberationMemory.id == deliberation_id)
        result = await session.execute(query)
        deliberation = result.scalar_one_or_none()
        
        if not deliberation:
            raise HTTPException(status_code=404, detail="Deliberation not found")
        
        response = DeliberationResponse.from_orm(deliberation)
        
        # Include persona responses if requested
        if include_responses:
            responses_query = select(PersonaResponseMemory).where(
                PersonaResponseMemory.deliberation_id == deliberation_id
            ).order_by(desc(PersonaResponseMemory.confidence))
            
            responses_result = await session.execute(responses_query)
            responses = responses_result.scalars().all()
            
            response_data = [PersonaResponseResponse.from_orm(r) for r in responses]
            # Add responses to the response (extend the model if needed)
            response.persona_responses = response_data
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deliberation {deliberation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve deliberation")


@router.get("/personas/{persona_name}/history", response_model=List[PersonaResponseResponse])
async def get_persona_history(
    persona_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    since: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get response history for a specific persona.
    
    Returns all responses made by the persona with confidence scores,
    reasoning, and agreement metrics.
    """
    try:
        query = select(PersonaResponseMemory).where(
            PersonaResponseMemory.persona_name == persona_name
        )
        
        if since:
            query = query.where(PersonaResponseMemory.created_at >= since)
        
        query = query.order_by(desc(PersonaResponseMemory.created_at)).offset(skip).limit(limit)
        
        result = await session.execute(query)
        responses = result.scalars().all()
        
        return [PersonaResponseResponse.from_orm(r) for r in responses]
        
    except Exception as e:
        logger.error(f"Error getting persona history for {persona_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve persona history")


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(
    search_request: MemorySearchRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Search memories using semantic similarity and filtering.
    
    Performs intelligent memory retrieval based on query text, context,
    and optional filters. Returns relevance scores and associated patterns.
    """
    try:
        memory_system = await get_memory_system()
        
        # Build time range if specified
        time_range = None
        if search_request.days_back:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=search_request.days_back)
            time_range = (start_date, end_date)
        
        # Create memory query
        memory_query = MemoryQuery(
            query_text=search_request.query,
            context={},  # Could be enhanced to accept context in request
            persona_name=search_request.persona_name,
            topic=search_request.topic,
            limit=search_request.limit,
            min_relevance=search_request.min_relevance,
            include_context=search_request.include_context,
            time_range=time_range
        )
        
        # Execute search
        recall_result: MemoryRecall = await memory_system.recall_memories(memory_query)
        
        # Convert to response format
        memories = [DeliberationResponse.from_orm(m) for m in recall_result.memories]
        
        context_memories = []
        for cm in recall_result.context_memories:
            context_memories.append({
                "id": str(cm.id),
                "context_type": cm.context_type,
                "context_data": cm.context_data,
                "relevance_score": cm.relevance_score,
                "source_type": cm.source_type,
                "source_id": cm.source_id
            })
        
        learning_patterns = []
        for lp in recall_result.learning_patterns:
            learning_patterns.append({
                "pattern_type": lp.pattern_type,
                "pattern_context": lp.pattern_context,
                "strength": lp.strength,
                "observation_count": lp.observation_count
            })
        
        return MemorySearchResponse(
            memories=memories,
            relevance_scores=recall_result.relevance_scores,
            context_memories=context_memories,
            learning_patterns=learning_patterns,
            total_found=recall_result.total_found,
            query_time=recall_result.query_time
        )
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to search memories")


@router.get("/patterns", response_model=List[LearningPatternResponse])
async def list_learning_patterns(
    persona_name: Optional[str] = Query(None, description="Filter by persona"),
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    min_strength: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum pattern strength"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List learning patterns discovered by the memory system.
    
    Shows how personas have adapted their behavior based on past
    deliberations and feedback.
    """
    try:
        query = select(PersonaLearningPattern)
        
        # Apply filters
        filters = []
        if persona_name:
            filters.append(PersonaLearningPattern.persona_name == persona_name)
        if pattern_type:
            filters.append(PersonaLearningPattern.pattern_type == pattern_type)
        if min_strength is not None:
            filters.append(PersonaLearningPattern.strength >= min_strength)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(desc(PersonaLearningPattern.strength)).limit(limit)
        
        result = await session.execute(query)
        patterns = result.scalars().all()
        
        return [LearningPatternResponse.from_orm(p) for p in patterns]
        
    except Exception as e:
        logger.error(f"Error listing learning patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve learning patterns")


@router.post("/consolidate")
async def consolidate_memories(
    background_tasks: BackgroundTasks,
    days_threshold: int = Query(90, ge=30, le=365, description="Age threshold for consolidation"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Trigger memory consolidation to optimize storage.
    
    Runs in background to consolidate old, low-importance memories
    while preserving significant deliberations.
    """
    try:
        memory_system = await get_memory_system()
        
        # Run consolidation in background
        background_tasks.add_task(
            memory_system.consolidate_old_memories, 
            days_threshold
        )
        
        return {
            "message": "Memory consolidation initiated",
            "days_threshold": days_threshold,
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Error initiating memory consolidation: {e}")
        raise HTTPException(status_code=500, detail="Failed to start memory consolidation")


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_statistics(
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive memory system statistics.
    
    Returns counts, growth trends, performance metrics, and persona activity.
    """
    try:
        # Get basic counts
        deliberations_count_query = select(func.count(DeliberationMemory.id))
        responses_count_query = select(func.count(PersonaResponseMemory.id))
        patterns_count_query = select(func.count(PersonaLearningPattern.id))
        associations_count_query = select(func.count(MemoryAssociation.id))
        
        deliberations_result = await session.execute(deliberations_count_query)
        responses_result = await session.execute(responses_count_query)
        patterns_result = await session.execute(patterns_count_query)
        associations_result = await session.execute(associations_count_query)
        
        total_deliberations = deliberations_result.scalar()
        total_responses = responses_result.scalar()
        total_patterns = patterns_result.scalar()
        total_associations = associations_result.scalar()
        
        # Get latest deliberation
        latest_query = select(DeliberationMemory.created_at).order_by(
            desc(DeliberationMemory.created_at)
        ).limit(1)
        latest_result = await session.execute(latest_query)
        latest_deliberation = latest_result.scalar()
        
        # Get average confidence
        avg_confidence_query = select(func.avg(DeliberationMemory.consensus_confidence))
        avg_confidence_result = await session.execute(avg_confidence_query)
        average_confidence = float(avg_confidence_result.scalar() or 0.0)
        
        # Get top personas by response count
        top_personas_query = select(
            PersonaResponseMemory.persona_name,
            func.count(PersonaResponseMemory.id).label('response_count'),
            func.avg(PersonaResponseMemory.confidence).label('avg_confidence')
        ).group_by(PersonaResponseMemory.persona_name).order_by(
            desc('response_count')
        ).limit(10)
        
        top_personas_result = await session.execute(top_personas_query)
        top_personas_data = top_personas_result.fetchall()
        
        top_personas = []
        for persona_name, response_count, avg_confidence in top_personas_data:
            top_personas.append({
                "persona_name": persona_name,
                "response_count": response_count,
                "average_confidence": float(avg_confidence or 0.0)
            })
        
        # Get memory growth trend (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        growth_query = select(
            func.date_trunc('day', DeliberationMemory.created_at).label('date'),
            func.count(DeliberationMemory.id).label('count')
        ).where(
            DeliberationMemory.created_at >= thirty_days_ago
        ).group_by('date').order_by('date')
        
        growth_result = await session.execute(growth_query)
        growth_data = growth_result.fetchall()
        
        memory_growth_trend = []
        for date, count in growth_data:
            memory_growth_trend.append({
                "date": date.isoformat(),
                "deliberations": count
            })
        
        return MemoryStatsResponse(
            total_deliberations=total_deliberations,
            total_responses=total_responses,
            total_patterns=total_patterns,
            total_associations=total_associations,
            latest_deliberation=latest_deliberation,
            average_confidence=average_confidence,
            top_personas=top_personas,
            memory_growth_trend=memory_growth_trend
        )
        
    except Exception as e:
        logger.error(f"Error getting memory statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve memory statistics")


@router.get("/personas/{persona_name}/summary", response_model=PersonaMemorySummary)
async def get_persona_memory_summary(
    persona_name: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive memory summary for a specific persona.
    
    Includes response statistics, learning patterns, recent activity,
    and performance metrics.
    """
    try:
        memory_system = await get_memory_system()
        
        # Get basic summary from memory system
        basic_summary = await memory_system.get_persona_memory_summary(persona_name)
        
        # Get recent activity (last 10 responses)
        recent_query = select(PersonaResponseMemory).where(
            PersonaResponseMemory.persona_name == persona_name
        ).order_by(desc(PersonaResponseMemory.created_at)).limit(10)
        
        recent_result = await session.execute(recent_query)
        recent_responses = recent_result.scalars().all()
        
        recent_activity = []
        for response in recent_responses:
            recent_activity.append({
                "deliberation_id": str(response.deliberation_id),
                "response_time": response.response_time,
                "confidence": response.confidence,
                "agreement_score": response.agreement_score,
                "created_at": response.created_at.isoformat(),
                "response_preview": response.response[:100] + "..." if len(response.response) > 100 else response.response
            })
        
        # Calculate performance metrics
        if recent_responses:
            avg_response_time = sum(r.response_time for r in recent_responses) / len(recent_responses)
            avg_agreement = sum(r.agreement_score for r in recent_responses) / len(recent_responses)
        else:
            avg_response_time = 0.0
            avg_agreement = 0.0
        
        performance_metrics = {
            "average_response_time": avg_response_time,
            "average_agreement_score": avg_agreement,
            "recent_activity_count": len(recent_responses),
            "confidence_trend": "stable"  # Could be calculated based on recent confidence scores
        }
        
        return PersonaMemorySummary(
            persona_name=basic_summary["persona_name"],
            total_responses=basic_summary["total_responses"],
            average_confidence=basic_summary["average_confidence"],
            learning_patterns=basic_summary["learning_patterns"],
            strongest_patterns=basic_summary["strongest_patterns"],
            recent_activity=recent_activity,
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error(f"Error getting persona memory summary for {persona_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve persona memory summary")


@router.get("/health")
async def memory_health_check():
    """
    Check memory system health and performance.
    
    Returns system status, database connectivity, and performance metrics.
    """
    try:
        memory_system = await get_memory_system()
        health_data = await memory_system.health_check()
        
        return {
            "status": "healthy",
            "memory_system": health_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Memory system health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# =================== SIMILARITY AND ASSOCIATIONS ===================

@router.get("/similar")
async def find_similar_memories(
    query: str = Query(..., description="Text to find similar memories for"),
    limit: int = Query(5, ge=1, le=20, description="Number of similar memories to return"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Find memories similar to the provided text query.
    
    Uses semantic similarity to identify related deliberations
    and their relevance scores.
    """
    try:
        memory_system = await get_memory_system()
        
        similar_memories = await memory_system.find_similar_memories(
            query_text=query,
            limit=limit,
            threshold=threshold
        )
        
        results = []
        for memory, similarity_score in similar_memories:
            results.append({
                "deliberation": DeliberationResponse.from_orm(memory),
                "similarity_score": similarity_score
            })
        
        return {
            "query": query,
            "similar_memories": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error finding similar memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar memories")


@router.get("/associations/{deliberation_id}")
async def get_memory_associations(
    deliberation_id: str,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get memory associations for a specific deliberation.
    
    Returns related memories discovered through similarity,
    temporal proximity, or shared contexts.
    """
    try:
        query = select(MemoryAssociation).where(
            MemoryAssociation.source_memory_id == deliberation_id
        ).order_by(desc(MemoryAssociation.strength)).limit(limit)
        
        result = await session.execute(query)
        associations = result.scalars().all()
        
        # Get associated memories
        associated_memories = []
        for association in associations:
            target_query = select(DeliberationMemory).where(
                DeliberationMemory.id == association.target_memory_id
            )
            target_result = await session.execute(target_query)
            target_memory = target_result.scalar_one_or_none()
            
            if target_memory:
                associated_memories.append({
                    "association": {
                        "type": association.association_type,
                        "strength": association.strength,
                        "discovered_by": association.discovered_by,
                        "metadata": association.association_metadata
                    },
                    "memory": DeliberationResponse.from_orm(target_memory)
                })
        
        return {
            "deliberation_id": deliberation_id,
            "associations": associated_memories,
            "count": len(associated_memories)
        }
        
    except Exception as e:
        logger.error(f"Error getting memory associations for {deliberation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve memory associations")