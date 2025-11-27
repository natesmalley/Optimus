"""
Council of Minds API endpoints for deliberation and decision making.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..council.orchestrator import Orchestrator, DeliberationRequest
from ..council.consensus import ConsensusMethod

logger = logging.getLogger(__name__)

# Import websocket manager from main module
# We'll use a global variable that gets set by main.py
websocket_manager = None

def set_websocket_manager(manager):
    """Set the websocket manager instance"""
    global websocket_manager
    websocket_manager = manager

# Global orchestrator instance
_orchestrator: Optional[Orchestrator] = None

class DeliberationRequestModel(BaseModel):
    """Request model for deliberation"""
    query: str = Field(..., description="The question or decision to make")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    topic: Optional[str] = Field(None, description="Topic for blackboard organization")
    required_personas: Optional[List[str]] = Field(None, description="Specific personas to include")
    consensus_method: Optional[str] = Field(None, description="How to reach consensus")
    timeout: float = Field(30.0, description="Maximum deliberation time in seconds")

class DeliberationResponseModel(BaseModel):
    """Response model for deliberation"""
    id: str
    query: str
    decision: str
    confidence: float
    agreement_level: float
    deliberation_time: float
    personas_consulted: int
    timestamp: str
    consensus_details: Dict[str, Any]
    supporting_personas: List[str]
    dissenting_personas: List[str]
    alternative_views: Dict[str, str]
    statistics: Dict[str, Any]

class PersonaInfoModel(BaseModel):
    """Information about a persona"""
    id: str
    name: str
    description: str
    expertise_domains: List[str]
    personality_traits: List[str]

router = APIRouter()

async def send_websocket_update(deliberation_id: str, message_type: str, data: Any):
    """Send update via WebSocket if manager is available"""
    if websocket_manager:
        try:
            message = {
                "type": message_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            await websocket_manager.send_to_deliberation_subscribers(deliberation_id, message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket update: {e}")

async def deliberate_with_realtime_updates(
    orchestrator: Orchestrator,
    request: DeliberationRequest,
    deliberation_id: str
) -> Any:
    """Perform deliberation with real-time WebSocket updates"""
    try:
        # Notify start
        await send_websocket_update(deliberation_id, "deliberation_start", {
            "deliberation_id": deliberation_id,
            "query": request.query,
            "stage": "starting"
        })

        # Initialize orchestrator if needed
        if not orchestrator.is_initialized:
            await orchestrator.initialize()

        # Send status update
        await send_websocket_update(deliberation_id, "deliberation_progress", {
            "deliberation_id": deliberation_id,
            "stage": "gathering_responses",
            "total_personas": len(orchestrator.personas)
        })

        # Perform deliberation
        result = await orchestrator.deliberate(request)

        # Send persona responses as they complete
        personas_completed = []
        for response in result.persona_responses:
            personas_completed.append(response.persona_id)
            await send_websocket_update(deliberation_id, "persona_response", {
                "deliberation_id": deliberation_id,
                "persona_id": response.persona_id,
                "confidence": response.confidence,
                "recommendation": response.recommendation[:100] + "..." if len(response.recommendation) > 100 else response.recommendation,
                "personas_completed": personas_completed,
                "total_personas": len(result.persona_responses)
            })

        # Send consensus update
        await send_websocket_update(deliberation_id, "consensus_update", {
            "deliberation_id": deliberation_id,
            "stage": "reaching_consensus",
            "confidence": result.consensus.confidence,
            "agreement_level": result.consensus.agreement_level
        })

        # Send completion
        await send_websocket_update(deliberation_id, "deliberation_complete", {
            "deliberation_id": deliberation_id,
            "stage": "complete",
            "decision": result.consensus.decision,
            "confidence": result.consensus.confidence,
            "agreement_level": result.consensus.agreement_level,
            "deliberation_time": result.deliberation_time
        })

        return result

    except Exception as e:
        # Send error update
        await send_websocket_update(deliberation_id, "error", {
            "deliberation_id": deliberation_id,
            "error": str(e),
            "stage": "error"
        })
        raise

async def get_orchestrator() -> Orchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(use_all_personas=True)
        await _orchestrator.initialize()
        logger.info("Council orchestrator initialized")
    return _orchestrator

@router.post("/deliberate", response_model=DeliberationResponseModel)
async def create_deliberation(
    request: DeliberationRequestModel,
    background_tasks: BackgroundTasks,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> DeliberationResponseModel:
    """
    Submit a query for deliberation by the Council of Minds
    """
    try:
        # Convert consensus method string to enum
        consensus_method = None
        if request.consensus_method:
            try:
                consensus_method = ConsensusMethod(request.consensus_method)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid consensus method: {request.consensus_method}"
                )
        
        # Generate unique ID
        deliberation_id = f"delib_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create deliberation request
        deliberation_request = DeliberationRequest(
            query=request.query,
            context=request.context,
            topic=request.topic,
            required_personas=request.required_personas,
            consensus_method=consensus_method,
            timeout=request.timeout
        )
        
        # Perform deliberation with real-time updates
        result = await deliberate_with_realtime_updates(
            orchestrator, 
            deliberation_request, 
            deliberation_id
        )
        
        # Convert to response model
        response = DeliberationResponseModel(
            id=deliberation_id,
            query=result.request.query,
            decision=result.consensus.decision,
            confidence=result.consensus.confidence,
            agreement_level=result.consensus.agreement_level,
            deliberation_time=result.deliberation_time,
            personas_consulted=len(result.persona_responses),
            timestamp=result.timestamp.isoformat(),
            consensus_details=result.consensus.to_dict(),
            supporting_personas=result.consensus.supporting_personas,
            dissenting_personas=result.consensus.dissenting_personas,
            alternative_views=result.consensus.alternative_views,
            statistics=result.statistics
        )
        
        logger.info(f"Deliberation completed: {deliberation_id} - {response.confidence:.1%} confidence")
        return response
        
    except Exception as e:
        logger.error(f"Error in deliberation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deliberation failed: {str(e)}")

@router.get("/deliberations/{deliberation_id}")
async def get_deliberation(deliberation_id: str):
    """
    Get deliberation result by ID (placeholder - would need persistence)
    """
    # This would typically fetch from database
    raise HTTPException(
        status_code=404, 
        detail="Deliberation persistence not implemented yet"
    )

@router.get("/personas", response_model=List[PersonaInfoModel])
async def list_personas(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> List[PersonaInfoModel]:
    """
    List all available personas
    """
    try:
        personas = []
        for persona_id, persona in orchestrator.personas.items():
            personas.append(PersonaInfoModel(
                id=persona.persona_id,
                name=persona.name,
                description=persona.description,
                expertise_domains=persona.expertise_domains,
                personality_traits=persona.personality_traits
            ))
        
        return personas
        
    except Exception as e:
        logger.error(f"Error listing personas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list personas: {str(e)}")

@router.get("/personas/{persona_id}")
async def get_persona(
    persona_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> PersonaInfoModel:
    """
    Get information about a specific persona
    """
    try:
        persona = orchestrator.personas.get(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
        
        return PersonaInfoModel(
            id=persona.persona_id,
            name=persona.name,
            description=persona.description,
            expertise_domains=persona.expertise_domains,
            personality_traits=persona.personality_traits
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona {persona_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get persona: {str(e)}")

@router.get("/performance")
async def get_persona_performance(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get performance metrics for all personas
    """
    try:
        performance = await orchestrator.get_persona_performance()
        return {
            "timestamp": datetime.now().isoformat(),
            "personas": performance
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get performance: {str(e)}")

@router.get("/history")
async def get_deliberation_history(
    limit: int = 10,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get recent deliberation history
    """
    try:
        history = await orchestrator.get_deliberation_history(limit)
        return {
            "timestamp": datetime.now().isoformat(),
            "deliberations": history,
            "total": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting deliberation history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@router.get("/health/detailed")
async def detailed_health_check(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Detailed health check for the Council of Minds system
    """
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "orchestrator": {
                "initialized": orchestrator.is_initialized,
                "personas_loaded": len(orchestrator.personas),
                "deliberations_processed": len(orchestrator.deliberation_history)
            },
            "personas": {}
        }
        
        # Check each persona
        for persona_id, persona in orchestrator.personas.items():
            health_data["personas"][persona_id] = {
                "name": persona.name,
                "blackboard_connected": persona.blackboard is not None,
                "decisions_made": len(persona.decision_history),
                "memory_size": len(persona.memory)
            }
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error in detailed health check: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/reset")
async def reset_orchestrator():
    """
    Reset the orchestrator (useful for testing)
    """
    global _orchestrator
    try:
        if _orchestrator:
            # Clear history and reset state
            _orchestrator.deliberation_history.clear()
            for persona in _orchestrator.personas.values():
                persona.decision_history.clear()
                persona.memory.clear()
            
            logger.info("Orchestrator state reset")
        
        return {
            "status": "success",
            "message": "Orchestrator state reset",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting orchestrator: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset: {str(e)}")