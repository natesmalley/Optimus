"""
Council of Minds Integration Layer
Connects the Council AI system to the API with real-time deliberation updates.
"""

import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...council.orchestrator import OptimusOrchestrator
from ...council.consensus import ConsensusReached
from ..websocket_manager import websocket_manager, Channel
from ...config import logger


class DeliberationRequest(BaseModel):
    """Council deliberation request."""
    topic: str
    context: Dict[str, Any] = {}
    required_personas: List[str] = []
    priority: int = 5  # 1-10, 10 is highest
    timeout_minutes: int = 30
    user_id: Optional[str] = None
    require_consensus: bool = True


class DeliberationResponse(BaseModel):
    """Council deliberation response."""
    deliberation_id: str
    topic: str
    status: str  # pending, deliberating, completed, failed, timeout
    consensus: Optional[Dict[str, Any]] = None
    personas_participated: List[str] = []
    total_deliberation_time: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class PersonaResponse(BaseModel):
    """Individual persona response."""
    persona_name: str
    timestamp: datetime
    response: Dict[str, Any]
    confidence: float
    reasoning: str
    vote: Optional[str] = None  # for, against, abstain


class DeliberationProgress(BaseModel):
    """Deliberation progress update."""
    deliberation_id: str
    phase: str  # starting, collecting, analyzing, converging, finalizing
    personas_responded: List[str]
    personas_pending: List[str]
    current_consensus: Optional[Dict[str, Any]] = None
    confidence_level: float
    estimated_completion: Optional[datetime] = None


class CouncilStats(BaseModel):
    """Council statistics."""
    total_deliberations: int
    active_deliberations: int
    completed_deliberations: int
    failed_deliberations: int
    average_deliberation_time: float
    consensus_rate: float
    most_active_personas: List[Dict[str, Any]]
    recent_topics: List[str]


class CouncilIntegration:
    """Integration layer for Council of Minds system."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.orchestrator = OptimusOrchestrator(session)
        self.active_deliberations: Dict[str, DeliberationRequest] = {}
        self.deliberation_progress: Dict[str, DeliberationProgress] = {}
        self.deliberation_history: List[DeliberationResponse] = []
        self.persona_responses: Dict[str, List[PersonaResponse]] = {}  # deliberation_id -> responses
        
        # Statistics
        self.stats = {
            "total_deliberations": 0,
            "active_deliberations": 0,
            "completed_deliberations": 0,
            "failed_deliberations": 0,
            "deliberation_times": [],
            "consensus_achieved": 0,
            "persona_participation": {},
            "recent_topics": []
        }
    
    async def start_deliberation(self, request: DeliberationRequest) -> str:
        """Start a new Council deliberation."""
        deliberation_id = str(uuid4())
        
        self.active_deliberations[deliberation_id] = request
        self.persona_responses[deliberation_id] = []
        self.stats["total_deliberations"] += 1
        self.stats["active_deliberations"] += 1
        self.stats["recent_topics"].append(request.topic)
        
        # Keep only last 20 topics
        if len(self.stats["recent_topics"]) > 20:
            self.stats["recent_topics"] = self.stats["recent_topics"][-20:]
        
        # Initialize progress tracking
        progress = DeliberationProgress(
            deliberation_id=deliberation_id,
            phase="starting",
            personas_responded=[],
            personas_pending=request.required_personas or [],
            confidence_level=0.0
        )
        self.deliberation_progress[deliberation_id] = progress
        
        # Start deliberation in background
        asyncio.create_task(
            self._execute_deliberation(deliberation_id, request)
        )
        
        # Broadcast deliberation started
        await self._broadcast_deliberation_update({
            "deliberation_id": deliberation_id,
            "type": "deliberation_started",
            "topic": request.topic,
            "status": "pending",
            "required_personas": request.required_personas
        })
        
        logger.info(f"Council deliberation started: {deliberation_id} - {request.topic}")
        return deliberation_id
    
    async def _execute_deliberation(self, deliberation_id: str, request: DeliberationRequest):
        """Execute Council deliberation."""
        response = DeliberationResponse(
            deliberation_id=deliberation_id,
            topic=request.topic,
            status="deliberating",
            started_at=datetime.now(),
            personas_participated=[]
        )
        
        try:
            # Update progress
            progress = self.deliberation_progress[deliberation_id]
            progress.phase = "collecting"
            await self._broadcast_progress_update(progress)
            
            # Trigger Council deliberation
            council_result = await self.orchestrator.deliberate_with_council(
                question=request.topic,
                context=request.context,
                required_personas=request.required_personas,
                consensus_threshold=0.7 if request.require_consensus else 0.5
            )
            
            # Process Council result
            if isinstance(council_result, ConsensusReached):
                response.status = "completed"
                response.consensus = {
                    "decision": council_result.final_decision,
                    "confidence": council_result.confidence,
                    "reasoning": council_result.reasoning,
                    "consensus_score": council_result.consensus_score,
                    "deliberation_summary": council_result.deliberation_summary
                }
                response.personas_participated = list(council_result.persona_votes.keys())
                
                # Record individual persona responses
                await self._record_persona_responses(deliberation_id, council_result)
                
                self.stats["completed_deliberations"] += 1
                self.stats["consensus_achieved"] += 1
                
                # Update progress
                progress.phase = "finalizing"
                progress.current_consensus = response.consensus
                progress.confidence_level = council_result.confidence
                progress.personas_responded = response.personas_participated
                progress.personas_pending = []
                await self._broadcast_progress_update(progress)
                
            else:
                response.status = "completed"
                response.consensus = {
                    "decision": "No consensus reached",
                    "reasoning": "The Council could not reach sufficient agreement",
                    "individual_responses": council_result if isinstance(council_result, dict) else {}
                }
                self.stats["completed_deliberations"] += 1
            
            response.completed_at = datetime.now()
            
            # Calculate deliberation time
            deliberation_time = (response.completed_at - response.started_at).total_seconds()
            response.total_deliberation_time = deliberation_time
            self.stats["deliberation_times"].append(deliberation_time)
            
            # Broadcast completion
            await self._broadcast_deliberation_update({
                "deliberation_id": deliberation_id,
                "type": "deliberation_completed",
                "topic": request.topic,
                "status": "completed",
                "consensus": response.consensus,
                "deliberation_time": deliberation_time,
                "personas_participated": response.personas_participated
            })
            
            logger.info(f"Council deliberation completed: {deliberation_id}")
            
        except asyncio.TimeoutError:
            response.status = "timeout"
            response.error = f"Deliberation timed out after {request.timeout_minutes} minutes"
            response.completed_at = datetime.now()
            self.stats["failed_deliberations"] += 1
            
            await self._broadcast_deliberation_update({
                "deliberation_id": deliberation_id,
                "type": "deliberation_timeout",
                "topic": request.topic,
                "status": "timeout",
                "error": response.error
            })
            
            logger.warning(f"Council deliberation timed out: {deliberation_id}")
            
        except Exception as e:
            response.status = "failed"
            response.error = str(e)
            response.completed_at = datetime.now()
            self.stats["failed_deliberations"] += 1
            
            await self._broadcast_deliberation_update({
                "deliberation_id": deliberation_id,
                "type": "deliberation_failed",
                "topic": request.topic,
                "status": "failed",
                "error": str(e)
            })
            
            logger.error(f"Council deliberation failed: {deliberation_id} - {e}")
        
        finally:
            # Clean up
            self.active_deliberations.pop(deliberation_id, None)
            self.deliberation_progress.pop(deliberation_id, None)
            self.stats["active_deliberations"] -= 1
            self.deliberation_history.append(response)
            
            # Keep only last 1000 deliberations in history
            if len(self.deliberation_history) > 1000:
                self.deliberation_history = self.deliberation_history[-1000:]
    
    async def _record_persona_responses(self, deliberation_id: str, consensus_result: ConsensusReached):
        """Record individual persona responses."""
        responses = []
        
        for persona_name, vote_info in consensus_result.persona_votes.items():
            # Update persona participation stats
            if persona_name not in self.stats["persona_participation"]:
                self.stats["persona_participation"][persona_name] = {
                    "total_participations": 0,
                    "votes_for": 0,
                    "votes_against": 0,
                    "abstentions": 0,
                    "average_confidence": 0.0,
                    "confidences": []
                }
            
            stats = self.stats["persona_participation"][persona_name]
            stats["total_participations"] += 1
            
            # Extract vote and confidence if available
            vote = "abstain"  # default
            confidence = 0.5  # default
            reasoning = "No specific reasoning provided"
            
            if isinstance(vote_info, dict):
                vote = vote_info.get("vote", "abstain")
                confidence = vote_info.get("confidence", 0.5)
                reasoning = vote_info.get("reasoning", reasoning)
            
            # Update vote counts
            if vote == "for":
                stats["votes_for"] += 1
            elif vote == "against":
                stats["votes_against"] += 1
            else:
                stats["abstentions"] += 1
            
            # Update confidence tracking
            stats["confidences"].append(confidence)
            stats["average_confidence"] = sum(stats["confidences"]) / len(stats["confidences"])
            
            # Create persona response record
            persona_response = PersonaResponse(
                persona_name=persona_name,
                timestamp=datetime.now(),
                response=vote_info if isinstance(vote_info, dict) else {"vote": vote_info},
                confidence=confidence,
                reasoning=reasoning,
                vote=vote
            )
            responses.append(persona_response)
            
            # Broadcast individual response
            await self._broadcast_persona_response(deliberation_id, persona_response)
        
        self.persona_responses[deliberation_id] = responses
    
    async def get_deliberation_status(self, deliberation_id: str) -> Optional[DeliberationResponse]:
        """Get deliberation status."""
        # Check if still active
        if deliberation_id in self.active_deliberations:
            request = self.active_deliberations[deliberation_id]
            progress = self.deliberation_progress.get(deliberation_id)
            
            return DeliberationResponse(
                deliberation_id=deliberation_id,
                topic=request.topic,
                status="deliberating",
                started_at=datetime.now(),  # This should be stored properly
                personas_participated=progress.personas_responded if progress else []
            )
        
        # Check history
        for response in self.deliberation_history:
            if response.deliberation_id == deliberation_id:
                return response
        
        return None
    
    async def get_deliberation_progress(self, deliberation_id: str) -> Optional[DeliberationProgress]:
        """Get current deliberation progress."""
        return self.deliberation_progress.get(deliberation_id)
    
    async def get_persona_responses(self, deliberation_id: str) -> List[PersonaResponse]:
        """Get all persona responses for a deliberation."""
        return self.persona_responses.get(deliberation_id, [])
    
    async def cancel_deliberation(self, deliberation_id: str) -> bool:
        """Cancel an active deliberation."""
        if deliberation_id in self.active_deliberations:
            # Remove from active deliberations
            request = self.active_deliberations.pop(deliberation_id)
            self.deliberation_progress.pop(deliberation_id, None)
            self.stats["active_deliberations"] -= 1
            
            # Add to history as cancelled
            response = DeliberationResponse(
                deliberation_id=deliberation_id,
                topic=request.topic,
                status="cancelled",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                error="Deliberation cancelled by user"
            )
            self.deliberation_history.append(response)
            
            # Broadcast cancellation
            await self._broadcast_deliberation_update({
                "deliberation_id": deliberation_id,
                "type": "deliberation_cancelled",
                "topic": request.topic,
                "status": "cancelled"
            })
            
            logger.info(f"Council deliberation cancelled: {deliberation_id}")
            return True
        
        return False
    
    async def get_council_statistics(self) -> CouncilStats:
        """Get Council statistics."""
        # Calculate averages
        deliberation_times = self.stats["deliberation_times"]
        avg_time = sum(deliberation_times) / len(deliberation_times) if deliberation_times else 0
        
        completed = self.stats["completed_deliberations"]
        consensus_rate = self.stats["consensus_achieved"] / completed if completed > 0 else 0
        
        # Get most active personas
        persona_stats = self.stats["persona_participation"]
        most_active = sorted(
            [
                {
                    "name": name,
                    "participations": stats["total_participations"],
                    "average_confidence": stats["average_confidence"]
                }
                for name, stats in persona_stats.items()
            ],
            key=lambda x: x["participations"],
            reverse=True
        )[:10]
        
        return CouncilStats(
            total_deliberations=self.stats["total_deliberations"],
            active_deliberations=self.stats["active_deliberations"],
            completed_deliberations=completed,
            failed_deliberations=self.stats["failed_deliberations"],
            average_deliberation_time=avg_time,
            consensus_rate=consensus_rate,
            most_active_personas=most_active,
            recent_topics=self.stats["recent_topics"].copy()
        )
    
    async def get_active_deliberations(self) -> List[Dict[str, Any]]:
        """Get all active deliberations."""
        active = []
        for deliberation_id, request in self.active_deliberations.items():
            progress = self.deliberation_progress.get(deliberation_id)
            
            active.append({
                "deliberation_id": deliberation_id,
                "topic": request.topic,
                "priority": request.priority,
                "user_id": request.user_id,
                "required_personas": request.required_personas,
                "phase": progress.phase if progress else "unknown",
                "personas_responded": progress.personas_responded if progress else [],
                "confidence_level": progress.confidence_level if progress else 0.0
            })
        
        return active
    
    async def get_deliberation_history(self, limit: int = 100) -> List[DeliberationResponse]:
        """Get deliberation history."""
        return self.deliberation_history[-limit:] if self.deliberation_history else []
    
    async def get_persona_statistics(self, persona_name: Optional[str] = None) -> Dict[str, Any]:
        """Get persona statistics."""
        if persona_name:
            return self.stats["persona_participation"].get(persona_name, {})
        else:
            return self.stats["persona_participation"].copy()
    
    async def _broadcast_deliberation_update(self, data: Dict[str, Any]):
        """Broadcast deliberation update via WebSocket."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.COUNCIL, {
                "type": "deliberation_update",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting deliberation update: {e}")
    
    async def _broadcast_progress_update(self, progress: DeliberationProgress):
        """Broadcast deliberation progress update."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.COUNCIL, {
                "type": "deliberation_progress",
                "data": progress.dict(),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting progress update: {e}")
    
    async def _broadcast_persona_response(self, deliberation_id: str, response: PersonaResponse):
        """Broadcast individual persona response."""
        try:
            await websocket_manager.broadcast_to_channel(Channel.COUNCIL, {
                "type": "persona_response",
                "data": {
                    "deliberation_id": deliberation_id,
                    "persona_response": response.dict()
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting persona response: {e}")
    
    async def quick_consultation(self, question: str, context: Dict[str, Any] = None, 
                                personas: List[str] = None) -> Dict[str, Any]:
        """Quick consultation without full deliberation tracking."""
        try:
            # Use orchestrator for quick consultation
            result = await self.orchestrator.quick_council_consultation(
                question=question,
                context=context or {},
                personas=personas or []
            )
            
            # Broadcast quick consultation result
            await websocket_manager.broadcast_to_channel(Channel.COUNCIL, {
                "type": "quick_consultation",
                "data": {
                    "question": question,
                    "result": result,
                    "personas": personas or []
                },
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Quick consultation failed: {e}")
            return {"error": str(e)}
    
    async def get_available_personas(self) -> List[Dict[str, Any]]:
        """Get list of available Council personas."""
        try:
            personas = await self.orchestrator.get_available_personas()
            
            # Enhance with statistics
            enhanced_personas = []
            for persona in personas:
                persona_name = persona.get("name", "")
                stats = self.stats["persona_participation"].get(persona_name, {})
                
                enhanced_personas.append({
                    **persona,
                    "statistics": {
                        "total_participations": stats.get("total_participations", 0),
                        "average_confidence": stats.get("average_confidence", 0.0),
                        "votes_for": stats.get("votes_for", 0),
                        "votes_against": stats.get("votes_against", 0),
                        "abstentions": stats.get("abstentions", 0)
                    }
                })
            
            return enhanced_personas
            
        except Exception as e:
            logger.error(f"Error getting available personas: {e}")
            return []