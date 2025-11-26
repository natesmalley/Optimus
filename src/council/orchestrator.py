"""
Orchestrator - Central Coordinator for the Council of Minds

Manages the flow of queries through personas, coordinates deliberation,
and produces final decisions through consensus.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Type
from dataclasses import dataclass, field

from .blackboard import Blackboard, BlackboardEntry, EntryType
from .persona import Persona, PersonaResponse
from .consensus import ConsensusEngine, ConsensusResult, ConsensusMethod
from .personas import CORE_PERSONAS

logger = logging.getLogger(__name__)


@dataclass
class DeliberationRequest:
    """Request for council deliberation"""
    query: str                               # The question or decision to make
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context
    topic: Optional[str] = None             # Topic for blackboard organization
    required_personas: Optional[List[str]] = None  # Specific personas to include
    consensus_method: Optional[ConsensusMethod] = None  # How to reach consensus
    timeout: float = 30.0                   # Maximum deliberation time
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliberationResult:
    """Result of council deliberation"""
    request: DeliberationRequest            # Original request
    consensus: ConsensusResult              # Final consensus
    persona_responses: List[PersonaResponse]  # Individual responses
    deliberation_time: float               # Time taken
    blackboard_topic: str                  # Topic used for blackboard
    statistics: Dict[str, Any]             # Deliberation statistics
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'query': self.request.query,
            'decision': self.consensus.decision,
            'confidence': self.consensus.confidence,
            'agreement': self.consensus.agreement_level,
            'time_taken': self.deliberation_time,
            'personas_consulted': len(self.persona_responses),
            'timestamp': self.timestamp.isoformat(),
            'consensus_details': self.consensus.to_dict(),
            'statistics': self.statistics
        }


class Orchestrator:
    """
    Central orchestrator for the Council of Minds
    
    Responsibilities:
    - Initialize and manage personas
    - Route queries to relevant personas
    - Coordinate deliberation process
    - Manage blackboard interactions
    - Produce final decisions through consensus
    """
    
    def __init__(self, 
                 use_all_personas: bool = False,
                 custom_personas: Optional[List[Type[Persona]]] = None):
        """
        Initialize the orchestrator
        
        Args:
            use_all_personas: Whether to use all available personas (vs just core)
            custom_personas: Additional custom personas to include
        """
        self.blackboard = Blackboard()
        self.consensus_engine = ConsensusEngine(self.blackboard)
        self.personas: Dict[str, Persona] = {}
        self.deliberation_history: List[DeliberationResult] = []
        self.is_initialized = False
        
        # Persona configuration
        self.use_all_personas = use_all_personas
        self.custom_personas = custom_personas or []
        
    async def initialize(self):
        """Initialize the council with personas"""
        if self.is_initialized:
            return
        
        logger.info("Initializing Optimus Council of Minds...")
        
        # Initialize core personas
        for PersonaClass in CORE_PERSONAS:
            persona = PersonaClass()
            persona.connect_blackboard(self.blackboard)
            self.personas[persona.persona_id] = persona
            logger.info(f"Initialized {persona.name}")
        
        # Initialize custom personas if provided
        for PersonaClass in self.custom_personas:
            persona = PersonaClass()
            persona.connect_blackboard(self.blackboard)
            self.personas[persona.persona_id] = persona
            logger.info(f"Initialized custom persona: {persona.name}")
        
        self.is_initialized = True
        logger.info(f"Council initialized with {len(self.personas)} personas")
    
    async def deliberate(self, request: DeliberationRequest) -> DeliberationResult:
        """
        Process a deliberation request through the council
        
        Args:
            request: The deliberation request
            
        Returns:
            DeliberationResult with consensus and details
        """
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        # Determine topic for blackboard
        topic = request.topic or f"deliberation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Select personas for this deliberation
        selected_personas = self._select_personas(request)
        
        # Post initial query to blackboard
        query_entry = BlackboardEntry(
            persona_id="orchestrator",
            entry_type=EntryType.QUESTION,
            content=request.query,
            metadata=request.metadata,
            tags={'query', 'deliberation'}
        )
        await self.blackboard.post(topic, query_entry)
        
        # Gather persona responses
        persona_responses = await self._gather_persona_responses(
            selected_personas,
            topic,
            request
        )
        
        # Calculate expertise weights
        weights = self._calculate_expertise_weights(
            persona_responses,
            request.query,
            request.context
        )
        
        # Reach consensus
        consensus = await self.consensus_engine.reach_consensus(
            topic,
            persona_responses,
            weights,
            request.consensus_method
        )
        
        # Allow personas to reflect on consensus
        await self._persona_reflections(
            selected_personas,
            topic,
            consensus
        )
        
        # Calculate statistics
        deliberation_time = time.time() - start_time
        statistics = await self._calculate_statistics(
            topic,
            persona_responses,
            consensus,
            deliberation_time
        )
        
        # Create result
        result = DeliberationResult(
            request=request,
            consensus=consensus,
            persona_responses=persona_responses,
            deliberation_time=deliberation_time,
            blackboard_topic=topic,
            statistics=statistics
        )
        
        # Store in history
        self.deliberation_history.append(result)
        
        logger.info(f"Deliberation complete: {consensus.decision} "
                   f"(confidence: {consensus.confidence:.0%}, "
                   f"agreement: {consensus.agreement_level:.0%})")
        
        return result
    
    def _select_personas(self, request: DeliberationRequest) -> List[Persona]:
        """
        Select which personas should participate in deliberation
        """
        if request.required_personas:
            # Use specifically requested personas
            selected = []
            for persona_id in request.required_personas:
                if persona_id in self.personas:
                    selected.append(self.personas[persona_id])
                else:
                    logger.warning(f"Requested persona {persona_id} not found")
            return selected
        
        # Use all personas or just core based on configuration
        if self.use_all_personas:
            return list(self.personas.values())
        else:
            # Use core personas plus any with relevant expertise
            selected = []
            query_lower = request.query.lower()
            
            for persona_id, persona in self.personas.items():
                # Always include core personas
                if persona_id in ['strategist', 'pragmatist', 'innovator', 'guardian', 'analyst']:
                    selected.append(persona)
                # Include if expertise matches
                elif any(domain.lower() in query_lower for domain in persona.expertise_domains):
                    selected.append(persona)
            
            return selected
    
    async def _gather_persona_responses(self,
                                       personas: List[Persona],
                                       topic: str,
                                       request: DeliberationRequest) -> List[PersonaResponse]:
        """
        Gather responses from all selected personas
        """
        tasks = []
        for persona in personas:
            task = asyncio.create_task(
                persona.deliberate(topic, request.query, request.context)
            )
            tasks.append(task)
        
        # Wait for all responses with timeout
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=request.timeout
            )
            return responses
        except asyncio.TimeoutError:
            logger.warning(f"Deliberation timeout after {request.timeout}s")
            # Return whatever responses we have
            completed_responses = []
            for task in tasks:
                if task.done() and not task.cancelled():
                    try:
                        completed_responses.append(task.result())
                    except Exception:
                        pass
            return completed_responses
    
    def _calculate_expertise_weights(self,
                                    responses: List[PersonaResponse],
                                    query: str,
                                    context: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate expertise weights for each persona
        """
        weights = {}
        
        for response in responses:
            persona = self.personas.get(response.persona_id)
            if persona:
                # Get persona's self-assessed expertise weight
                weight = persona.get_expertise_weight(query, context)
                
                # Adjust based on response quality indicators
                if len(response.data_points) > 5:
                    weight *= 1.1  # Bonus for data-rich response
                if response.confidence > 0.8:
                    weight *= 1.05  # Small bonus for high confidence
                
                weights[response.persona_id] = min(1.0, weight)
            else:
                weights[response.persona_id] = 1.0  # Default weight
        
        return weights
    
    async def _persona_reflections(self,
                                  personas: List[Persona],
                                  topic: str,
                                  consensus: ConsensusResult):
        """
        Allow personas to reflect on the consensus
        """
        reflection_tasks = []
        
        consensus_data = {
            'decision': consensus.decision,
            'confidence': consensus.confidence,
            'agreement': consensus.agreement_level,
            'method': consensus.method_used.value
        }
        
        for persona in personas:
            if persona.persona_id in consensus.dissenting_personas:
                # Dissenters may want to reflect more
                task = asyncio.create_task(
                    persona.reflect_on_consensus(topic, consensus.decision, consensus_data)
                )
                reflection_tasks.append(task)
        
        if reflection_tasks:
            await asyncio.gather(*reflection_tasks, return_exceptions=True)
    
    async def _calculate_statistics(self,
                                   topic: str,
                                   responses: List[PersonaResponse],
                                   consensus: ConsensusResult,
                                   deliberation_time: float) -> Dict[str, Any]:
        """
        Calculate statistics about the deliberation
        """
        blackboard_stats = await self.blackboard.get_statistics(topic)
        
        # Response statistics
        confidence_scores = [r.confidence for r in responses]
        
        # Concern and opportunity counts
        total_concerns = sum(len(r.concerns) for r in responses)
        total_opportunities = sum(len(r.opportunities) for r in responses)
        
        # Priority distribution
        priority_counts = {}
        for response in responses:
            p = response.priority.value
            priority_counts[p] = priority_counts.get(p, 0) + 1
        
        return {
            'deliberation_time': deliberation_time,
            'personas_consulted': len(responses),
            'blackboard_entries': blackboard_stats['total_entries'],
            'consensus_method': consensus.method_used.value,
            'agreement_level': consensus.agreement_level,
            'avg_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'confidence_range': {
                'min': min(confidence_scores) if confidence_scores else 0,
                'max': max(confidence_scores) if confidence_scores else 0
            },
            'concerns_raised': total_concerns,
            'opportunities_identified': total_opportunities,
            'priority_distribution': priority_counts,
            'dissent_rate': len(consensus.dissenting_personas) / len(responses) if responses else 0
        }
    
    async def get_deliberation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent deliberation history
        
        Args:
            limit: Maximum number of deliberations to return
            
        Returns:
            List of deliberation summaries
        """
        history = []
        for result in self.deliberation_history[-limit:]:
            history.append(result.to_dict())
        return history
    
    async def get_persona_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics for each persona
        
        Returns:
            Dictionary of persona metrics
        """
        performance = {}
        
        for persona_id, persona in self.personas.items():
            # Count participation
            participation_count = sum(
                1 for result in self.deliberation_history
                for response in result.persona_responses
                if response.persona_id == persona_id
            )
            
            # Count times in consensus
            consensus_count = sum(
                1 for result in self.deliberation_history
                if persona_id in result.consensus.supporting_personas
            )
            
            # Count times dissenting
            dissent_count = sum(
                1 for result in self.deliberation_history
                if persona_id in result.consensus.dissenting_personas
            )
            
            # Average confidence
            confidences = [
                response.confidence
                for result in self.deliberation_history
                for response in result.persona_responses
                if response.persona_id == persona_id
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            performance[persona_id] = {
                'name': persona.name,
                'participation_count': participation_count,
                'consensus_rate': consensus_count / participation_count if participation_count > 0 else 0,
                'dissent_rate': dissent_count / participation_count if participation_count > 0 else 0,
                'avg_confidence': avg_confidence,
                'expertise_domains': persona.expertise_domains[:3]  # Top 3
            }
        
        return performance
    
    async def explain_decision(self, topic: str) -> str:
        """
        Generate a human-readable explanation of a decision
        
        Args:
            topic: The blackboard topic for the deliberation
            
        Returns:
            Narrative explanation of the decision process
        """
        # Get the consensus trail
        trail = await self.blackboard.get_consensus_trail(topic)
        
        if not trail:
            return "No deliberation found for this topic."
        
        # Find key entries
        question = None
        insights = []
        recommendations = []
        concerns = []
        consensus = None
        
        for entry in trail:
            if entry.entry_type == EntryType.QUESTION:
                question = entry.content
            elif entry.entry_type == EntryType.INSIGHT:
                insights.append(f"{entry.metadata.get('persona_name', 'Unknown')}: {entry.content}")
            elif entry.entry_type == EntryType.RECOMMENDATION:
                recommendations.append(f"{entry.metadata.get('persona_name', 'Unknown')}: {entry.content}")
            elif entry.entry_type == EntryType.CONCERN:
                concerns.append(f"{entry.metadata.get('persona_name', 'Unknown')}: {entry.content}")
            elif entry.entry_type == EntryType.CONSENSUS:
                consensus = entry
        
        # Build explanation
        explanation = f"**Question:** {question}\n\n"
        
        if insights:
            explanation += "**Key Insights:**\n"
            for insight in insights[:3]:  # Top 3
                explanation += f"- {insight}\n"
            explanation += "\n"
        
        if recommendations:
            explanation += "**Recommendations:**\n"
            for rec in recommendations[:3]:
                explanation += f"- {rec}\n"
            explanation += "\n"
        
        if concerns:
            explanation += "**Concerns Raised:**\n"
            for concern in concerns[:3]:
                explanation += f"- {concern}\n"
            explanation += "\n"
        
        if consensus:
            explanation += f"**Final Decision:** {consensus.content}\n"
            explanation += f"**Confidence:** {consensus.confidence:.0%}\n"
            explanation += f"**Agreement Level:** {consensus.metadata.get('agreement_level', 0):.0%}\n"
        
        return explanation