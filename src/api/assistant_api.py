"""
Unified Assistant API for Optimus
Central endpoint for all assistant interactions
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import asyncio
import json
from enum import Enum

# Import models
from src.models.life_assistant import (
    AssistantQuery,
    AssistantResponse,
    SuggestionCreate,
    SuggestionType
)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# =====================================================
# Enums and Models
# =====================================================

class QueryMode(str, Enum):
    AUTO = "AUTO"
    WORK = "WORK"
    LIFE = "LIFE"
    SOCIAL = "SOCIAL"
    GROWTH = "GROWTH"
    HEALTH = "HEALTH"

class QueryType(str, Enum):
    PLANNING = "PLANNING"
    DRAFTING = "DRAFTING"
    DECISION = "DECISION"
    ANALYSIS = "ANALYSIS"
    GENERAL = "GENERAL"
    EMERGENCY = "EMERGENCY"

class AssistantRequest(BaseModel):
    """Main request model for assistant."""
    query: str
    mode: QueryMode = QueryMode.AUTO
    context: Dict[str, Any] = Field(default_factory=dict)
    require_voice: bool = False
    device: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class AssistantAction(BaseModel):
    """Structured action for assistant to take."""
    type: str  # create_task, schedule_event, send_email, etc.
    params: Dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_confirmation: bool = False

class CouncilMember(BaseModel):
    """Council member opinion."""
    name: str
    role: str
    opinion: str
    confidence: float
    concerns: List[str] = []
    recommendations: List[str] = []

class CouncilDeliberation(BaseModel):
    """Full council deliberation result."""
    query: str
    members: List[CouncilMember]
    consensus: str
    confidence: float
    dissenting_opinions: List[str] = []
    action_items: List[str] = []
    risk_assessment: str

class EnhancedAssistantResponse(BaseModel):
    """Enhanced response with full context."""
    # Core response
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Structured data
    actions: List[AssistantAction] = []
    suggestions: List[Dict[str, Any]] = []
    
    # Metadata
    query_type: QueryType
    mode_used: QueryMode
    agents_consulted: List[str] = []
    tools_used: List[str] = []
    
    # Safety
    risk_flags: List[str] = []
    requires_human_review: bool = False
    
    # Voice
    audio_url: Optional[str] = None
    voice_text: Optional[str] = None
    
    # Debug
    processing_time_ms: int = 0
    tokens_used: int = 0

# =====================================================
# Intent Classification
# =====================================================

class IntentClassifier:
    """Classify user intent from query."""
    
    @staticmethod
    def classify_query_type(query: str) -> QueryType:
        """Determine query type from text."""
        query_lower = query.lower()
        
        # Emergency detection
        emergency_keywords = ["urgent", "emergency", "asap", "critical", "immediately"]
        if any(keyword in query_lower for keyword in emergency_keywords):
            return QueryType.EMERGENCY
        
        # Planning detection
        planning_keywords = ["plan", "schedule", "organize", "prepare", "agenda"]
        if any(keyword in query_lower for keyword in planning_keywords):
            return QueryType.PLANNING
        
        # Drafting detection
        drafting_keywords = ["write", "draft", "compose", "reply", "email", "message"]
        if any(keyword in query_lower for keyword in drafting_keywords):
            return QueryType.DRAFTING
        
        # Decision detection
        decision_keywords = ["should", "decide", "choose", "option", "recommend", "advice"]
        if any(keyword in query_lower for keyword in decision_keywords):
            return QueryType.DECISION
        
        # Analysis detection
        analysis_keywords = ["analyze", "review", "evaluate", "assess", "compare"]
        if any(keyword in query_lower for keyword in analysis_keywords):
            return QueryType.ANALYSIS
        
        return QueryType.GENERAL
    
    @staticmethod
    def classify_mode(query: str, context: Dict[str, Any]) -> QueryMode:
        """Determine which mode to use."""
        query_lower = query.lower()
        
        # Check context hints
        if context.get("mode"):
            return QueryMode(context["mode"])
        
        # Work mode detection
        work_keywords = ["meeting", "project", "deadline", "task", "email", "presentation"]
        if any(keyword in query_lower for keyword in work_keywords):
            return QueryMode.WORK
        
        # Social mode detection
        social_keywords = ["friend", "family", "party", "date", "relationship", "call"]
        if any(keyword in query_lower for keyword in social_keywords):
            return QueryMode.SOCIAL
        
        # Health mode detection
        health_keywords = ["workout", "exercise", "health", "doctor", "medicine", "sleep"]
        if any(keyword in query_lower for keyword in health_keywords):
            return QueryMode.HEALTH
        
        # Growth mode detection
        growth_keywords = ["learn", "study", "course", "skill", "book", "practice"]
        if any(keyword in query_lower for keyword in growth_keywords):
            return QueryMode.GROWTH
        
        return QueryMode.AUTO

# =====================================================
# Council System
# =====================================================

class LifeCouncil:
    """Council of specialized advisors."""
    
    def __init__(self):
        self.members = {
            "work_orchestrator": {
                "name": "Magnus",
                "role": "Work Orchestrator",
                "expertise": ["productivity", "time management", "project coordination"]
            },
            "social_coach": {
                "name": "Harmony",
                "role": "Social Coach",
                "expertise": ["relationships", "communication", "social dynamics"]
            },
            "health_guardian": {
                "name": "Vitalis",
                "role": "Health Guardian",
                "expertise": ["physical health", "mental wellness", "work-life balance"]
            },
            "growth_mentor": {
                "name": "Sage",
                "role": "Growth Mentor",
                "expertise": ["learning", "skill development", "personal growth"]
            },
            "safety_officer": {
                "name": "Sentinel",
                "role": "Safety Officer",
                "expertise": ["risk assessment", "boundary enforcement", "ethical review"]
            }
        }
    
    async def deliberate(self, query: str, mode: QueryMode, context: Dict[str, Any]) -> CouncilDeliberation:
        """Have the council deliberate on a query."""
        
        members_consulted = []
        
        # Always include safety officer
        safety_opinion = await self._get_safety_assessment(query, context)
        members_consulted.append(safety_opinion)
        
        # Select relevant council members based on mode
        if mode == QueryMode.WORK:
            work_opinion = await self._get_work_opinion(query, context)
            members_consulted.append(work_opinion)
        
        if mode == QueryMode.SOCIAL:
            social_opinion = await self._get_social_opinion(query, context)
            members_consulted.append(social_opinion)
        
        if mode == QueryMode.HEALTH:
            health_opinion = await self._get_health_opinion(query, context)
            members_consulted.append(health_opinion)
        
        if mode == QueryMode.GROWTH:
            growth_opinion = await self._get_growth_opinion(query, context)
            members_consulted.append(growth_opinion)
        
        # If AUTO mode, consult all relevant members
        if mode == QueryMode.AUTO:
            # Simplified for now - in production, would analyze query
            work_opinion = await self._get_work_opinion(query, context)
            members_consulted.append(work_opinion)
        
        # Generate consensus
        consensus = self._generate_consensus(members_consulted)
        
        return CouncilDeliberation(
            query=query,
            members=members_consulted,
            consensus=consensus["decision"],
            confidence=consensus["confidence"],
            dissenting_opinions=consensus["dissents"],
            action_items=consensus["actions"],
            risk_assessment=safety_opinion.concerns[0] if safety_opinion.concerns else "Low risk"
        )
    
    async def _get_safety_assessment(self, query: str, context: Dict[str, Any]) -> CouncilMember:
        """Get safety officer's assessment."""
        # Simulate safety check
        concerns = []
        recommendations = []
        
        # Check for risky keywords
        risky_keywords = ["medical", "financial", "legal", "investment", "diagnosis"]
        if any(keyword in query.lower() for keyword in risky_keywords):
            concerns.append("Query touches on regulated domain requiring professional advice")
            recommendations.append("Provide information only, emphasize need for professional consultation")
        
        return CouncilMember(
            name="Sentinel",
            role="Safety Officer",
            opinion="Query assessed for safety and ethical concerns",
            confidence=0.9,
            concerns=concerns,
            recommendations=recommendations
        )
    
    async def _get_work_opinion(self, query: str, context: Dict[str, Any]) -> CouncilMember:
        """Get work orchestrator's opinion."""
        return CouncilMember(
            name="Magnus",
            role="Work Orchestrator",
            opinion="From a productivity perspective, this requires careful time allocation",
            confidence=0.85,
            concerns=["May conflict with existing deadlines"],
            recommendations=["Block 2 hours of focus time", "Delegate non-critical tasks"]
        )
    
    async def _get_social_opinion(self, query: str, context: Dict[str, Any]) -> CouncilMember:
        """Get social coach's opinion."""
        return CouncilMember(
            name="Harmony",
            role="Social Coach",
            opinion="Consider the relationship dynamics and communication style",
            confidence=0.75,
            concerns=["Timing might be sensitive"],
            recommendations=["Use empathetic language", "Schedule follow-up check-in"]
        )
    
    async def _get_health_opinion(self, query: str, context: Dict[str, Any]) -> CouncilMember:
        """Get health guardian's opinion."""
        return CouncilMember(
            name="Vitalis",
            role="Health Guardian",
            opinion="Ensure this aligns with your wellness goals and energy levels",
            confidence=0.8,
            concerns=["May impact sleep schedule", "Consider stress levels"],
            recommendations=["Add buffer time for recovery", "Maintain workout routine"]
        )
    
    async def _get_growth_opinion(self, query: str, context: Dict[str, Any]) -> CouncilMember:
        """Get growth mentor's opinion."""
        return CouncilMember(
            name="Sage",
            role="Growth Mentor",
            opinion="This presents a learning opportunity worth considering",
            confidence=0.7,
            concerns=["Requires significant time investment"],
            recommendations=["Document learnings", "Set measurable milestones"]
        )
    
    def _generate_consensus(self, members: List[CouncilMember]) -> Dict[str, Any]:
        """Generate consensus from member opinions."""
        # Calculate average confidence
        avg_confidence = sum(m.confidence for m in members) / len(members)
        
        # Collect all recommendations
        all_recommendations = []
        for member in members:
            all_recommendations.extend(member.recommendations)
        
        # Find dissenting opinions (simplified)
        dissents = []
        for member in members:
            if member.confidence < 0.5:
                dissents.append(f"{member.name}: {member.concerns[0] if member.concerns else 'Low confidence'}")
        
        # Generate decision
        if avg_confidence > 0.7:
            decision = "Proceed with recommended approach"
        elif avg_confidence > 0.5:
            decision = "Proceed with caution and monitoring"
        else:
            decision = "Reconsider or gather more information"
        
        return {
            "decision": decision,
            "confidence": avg_confidence,
            "actions": all_recommendations[:5],  # Top 5 actions
            "dissents": dissents
        }

# =====================================================
# Main Assistant Logic
# =====================================================

class OptimusAssistant:
    """Main assistant orchestrator."""
    
    def __init__(self):
        self.classifier = IntentClassifier()
        self.council = LifeCouncil()
    
    async def process_query(self, request: AssistantRequest) -> EnhancedAssistantResponse:
        """Process a user query through the assistant pipeline."""
        
        start_time = datetime.now()
        
        # Classify intent
        query_type = self.classifier.classify_query_type(request.query)
        mode = request.mode if request.mode != QueryMode.AUTO else self.classifier.classify_mode(request.query, request.context)
        
        # Handle emergency queries immediately
        if query_type == QueryType.EMERGENCY:
            return await self._handle_emergency(request)
        
        # Get council deliberation for complex queries
        agents_consulted = []
        if query_type in [QueryType.DECISION, QueryType.PLANNING]:
            deliberation = await self.council.deliberate(request.query, mode, request.context)
            agents_consulted = [m.name for m in deliberation.members]
            
            # Build response from deliberation
            answer = self._format_deliberation_response(deliberation)
            confidence = deliberation.confidence
            risk_flags = [deliberation.risk_assessment] if deliberation.risk_assessment != "Low risk" else []
        else:
            # Handle simpler queries directly
            answer, confidence = await self._handle_simple_query(request, query_type)
            risk_flags = []
        
        # Generate actions based on query type
        actions = self._generate_actions(request.query, query_type, mode)
        
        # Generate suggestions
        suggestions = await self._generate_suggestions(request, query_type, mode)
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Build response
        response = EnhancedAssistantResponse(
            answer=answer,
            confidence=confidence,
            actions=actions,
            suggestions=suggestions,
            query_type=query_type,
            mode_used=mode,
            agents_consulted=agents_consulted,
            tools_used=["intent_classifier", "life_council"] if agents_consulted else ["intent_classifier"],
            risk_flags=risk_flags,
            requires_human_review=len(risk_flags) > 0,
            processing_time_ms=processing_time,
            tokens_used=len(request.query.split()) * 10  # Rough estimate
        )
        
        # Add voice if requested
        if request.require_voice:
            response.voice_text = answer
            response.audio_url = "/api/voice/generate"  # Would generate actual audio
        
        return response
    
    async def _handle_emergency(self, request: AssistantRequest) -> EnhancedAssistantResponse:
        """Handle emergency queries with priority."""
        return EnhancedAssistantResponse(
            answer="I'm treating this as urgent. Here's what I recommend immediately:",
            confidence=0.95,
            query_type=QueryType.EMERGENCY,
            mode_used=request.mode,
            actions=[
                AssistantAction(
                    type="alert",
                    params={"priority": "high"},
                    confidence=1.0,
                    requires_confirmation=False
                )
            ],
            risk_flags=["Emergency query - handled with priority"],
            processing_time_ms=50
        )
    
    async def _handle_simple_query(self, request: AssistantRequest, query_type: QueryType) -> tuple[str, float]:
        """Handle simple queries without council."""
        
        if query_type == QueryType.GENERAL:
            return (
                f"I understand you're asking about: {request.query}. Let me help with that.",
                0.7
            )
        elif query_type == QueryType.DRAFTING:
            return (
                f"I'll help you draft that. Here's a suggested approach based on the context.",
                0.8
            )
        elif query_type == QueryType.ANALYSIS:
            return (
                f"Let me analyze that for you. Based on the available data, here's what I found.",
                0.75
            )
        else:
            return (
                f"I'm processing your request. Here's what I recommend.",
                0.6
            )
    
    def _format_deliberation_response(self, deliberation: CouncilDeliberation) -> str:
        """Format council deliberation into user-friendly response."""
        response = f"After consulting with the council, here's my recommendation:\n\n"
        response += f"**Consensus**: {deliberation.consensus}\n"
        response += f"**Confidence**: {deliberation.confidence:.0%}\n\n"
        
        if deliberation.action_items:
            response += "**Recommended Actions**:\n"
            for i, action in enumerate(deliberation.action_items[:3], 1):
                response += f"{i}. {action}\n"
        
        if deliberation.dissenting_opinions:
            response += f"\n**Note**: {deliberation.dissenting_opinions[0]}"
        
        return response
    
    def _generate_actions(self, query: str, query_type: QueryType, mode: QueryMode) -> List[AssistantAction]:
        """Generate structured actions from query."""
        actions = []
        
        if query_type == QueryType.PLANNING:
            actions.append(AssistantAction(
                type="create_time_block",
                params={"duration": 120, "purpose": "planning"},
                confidence=0.8,
                requires_confirmation=True
            ))
        
        elif query_type == QueryType.DRAFTING:
            actions.append(AssistantAction(
                type="draft_document",
                params={"template": "email", "tone": "professional"},
                confidence=0.85,
                requires_confirmation=True
            ))
        
        return actions
    
    async def _generate_suggestions(self, request: AssistantRequest, query_type: QueryType, mode: QueryMode) -> List[Dict[str, Any]]:
        """Generate proactive suggestions."""
        suggestions = []
        
        # Add contextual suggestions based on mode
        if mode == QueryMode.WORK:
            suggestions.append({
                "title": "Block focus time after this task",
                "type": "optimization",
                "confidence": 0.7
            })
        
        elif mode == QueryMode.HEALTH:
            suggestions.append({
                "title": "Schedule a break in 90 minutes",
                "type": "wellness",
                "confidence": 0.8
            })
        
        return suggestions

# =====================================================
# API Endpoints
# =====================================================

# Initialize assistant
assistant = OptimusAssistant()

@router.post("/ask", response_model=EnhancedAssistantResponse)
async def ask_assistant(request: AssistantRequest) -> EnhancedAssistantResponse:
    """Main endpoint for assistant queries."""
    
    try:
        # Process through assistant pipeline
        response = await assistant.process_query(request)
        return response
        
    except Exception as e:
        # Return error response
        return EnhancedAssistantResponse(
            answer=f"I encountered an error processing your request: {str(e)}",
            confidence=0.0,
            query_type=QueryType.GENERAL,
            mode_used=request.mode,
            risk_flags=["Processing error"],
            requires_human_review=True,
            processing_time_ms=0
        )

@router.post("/council/deliberate")
async def council_deliberation(
    query: str,
    mode: QueryMode = QueryMode.AUTO,
    context: Dict[str, Any] = {}
) -> CouncilDeliberation:
    """Get full council deliberation on a query."""
    
    council = LifeCouncil()
    deliberation = await council.deliberate(query, mode, context)
    return deliberation

@router.get("/suggestions")
async def get_proactive_suggestions(
    user_id: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get proactive suggestions for the user."""
    
    # Mock suggestions for now
    suggestions = [
        {
            "id": str(uuid4()),
            "type": "scheduling",
            "title": "Your afternoon is free - schedule deep work?",
            "description": "You have a 3-hour block from 2-5 PM. Perfect for the project review.",
            "confidence": 0.85,
            "expires_at": datetime.now() + timedelta(hours=2)
        },
        {
            "id": str(uuid4()),
            "type": "wellness",
            "title": "You've been working for 2 hours straight",
            "description": "Time for a 15-minute break to maintain productivity.",
            "confidence": 0.9,
            "expires_at": datetime.now() + timedelta(minutes=30)
        },
        {
            "id": str(uuid4()),
            "type": "social",
            "title": "It's been 2 weeks since you called Mom",
            "description": "Schedule a call this weekend?",
            "confidence": 0.75,
            "expires_at": datetime.now() + timedelta(days=3)
        }
    ]
    
    return suggestions[:limit]

@router.get("/capabilities")
async def get_assistant_capabilities() -> Dict[str, Any]:
    """Get current assistant capabilities."""
    
    return {
        "version": "2.0.0",
        "capabilities": {
            "query_types": [t.value for t in QueryType],
            "modes": [m.value for m in QueryMode],
            "council_members": 5,
            "voice_enabled": True,
            "languages": ["en"],
            "integrations": [
                "calendar",
                "email",
                "tasks",
                "voice"
            ]
        },
        "limits": {
            "max_query_length": 1000,
            "max_actions_per_response": 10,
            "max_suggestions": 20,
            "rate_limit": "100/hour"
        }
    }

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "assistant_api",
        "timestamp": datetime.now()
    }