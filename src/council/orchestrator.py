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
from .tool_integration import PersonaToolIntegration, ToolCapability
# Memory and knowledge graph integration - to be connected later
# from .memory_integration import get_optimized_memory_system
# from .knowledge_graph_integration import get_optimized_knowledge_graph
from .knowledge_graph import NodeType, EdgeType

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
        
        # Tool integration
        self.tool_integration: Optional[PersonaToolIntegration] = None
        
        # Memory and Knowledge Graph integration
        self.memory_system = None  # Will be initialized in initialize()
        self.knowledge_graph = None  # Will be connected when integration is fixed
        
    async def initialize(self):
        """Initialize the council with personas"""
        if self.is_initialized:
            return
        
        logger.info("Initializing Optimus Council of Minds...")
        
        # Initialize core personas
        persona_classes = CORE_PERSONAS
        
        if self.use_all_personas:
            from .personas import ALL_PERSONAS
            persona_classes = ALL_PERSONAS
            
        # Create and register personas
        for PersonaClass in persona_classes:
            try:
                persona = PersonaClass()
                persona.connect_blackboard(self.blackboard)
                self.personas[persona.persona_id] = persona
                logger.info(f"Initialized {persona.name}")
            except Exception as e:
                logger.error(f"Failed to initialize {PersonaClass.__name__}: {e}")
        
        # Add custom personas if any
        for PersonaClass in self.custom_personas:
            try:
                persona = PersonaClass()
                persona.connect_blackboard(self.blackboard)
                self.personas[persona.persona_id] = persona
                logger.info(f"Initialized custom persona {persona.name}")
            except Exception as e:
                logger.error(f"Failed to initialize custom persona: {e}")
        
        # Initialize tool integration
        try:
            self.tool_integration = PersonaToolIntegration()
            await self.tool_integration.initialize()
            
            # Add tool capabilities to all personas
            for persona in self.personas.values():
                tool_capability = ToolCapability(
                    tool_integration=self.tool_integration,
                    persona_context={"persona_id": persona.persona_id, "name": persona.name}
                )
                persona.add_tool_capabilities(tool_capability)
            
            logger.info("Tool integration initialized and connected to personas")
        except Exception as e:
            logger.warning(f"Tool integration failed to initialize: {e}")
            # Continue without tools - not critical for basic operation

        # Initialize memory system
        try:
            from .memory_system import get_memory_system
            self.memory_system = await get_memory_system()
            logger.info("Memory system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize memory system: {e}")
            # Continue without memory system - not critical for basic operation
        
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
        
        # Recall relevant memories for context enhancement
        enhanced_context = await self._enhance_context_with_memories(request, selected_personas)
        
        # Post initial query to blackboard
        query_entry = BlackboardEntry(
            persona_id="orchestrator",
            entry_type=EntryType.QUESTION,
            content=request.query,
            metadata=enhanced_context,
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
        
        # Post-deliberation hooks: store memories and update knowledge graph
        await self._post_deliberation_hooks(result)
        
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
    
    async def _enhance_context_with_memories(self, 
                                           request: DeliberationRequest,
                                           personas: List[Persona]) -> Dict[str, Any]:
        """
        Enhance request context with relevant memories from personas
        """
        enhanced_context = request.context.copy()
        enhanced_context['remembered_experiences'] = []
        
        if not self.memory_system:
            return enhanced_context
        
        try:
            # Import the memory query class
            from .memory_system import MemoryQuery
            
            # Recall memories using the new system
            memory_query = MemoryQuery(
                query_text=request.query,
                context=request.context,
                topic=request.topic,
                limit=5,
                min_relevance=0.3,
                include_context=True
            )
            
            recall_result = await self.memory_system.recall_memories(memory_query)
            
            if recall_result.memories:
                # Group memories by topic/similarity for context
                memories_context = []
                for memory, relevance in zip(recall_result.memories, recall_result.relevance_scores):
                    memories_context.append({
                        'query': memory.query,
                        'decision': memory.consensus_result.get('decision', ''),
                        'confidence': memory.consensus_confidence,
                        'topic': memory.topic,
                        'relevance': relevance,
                        'timestamp': memory.created_at.isoformat(),
                        'importance': memory.importance_score
                    })
                
                enhanced_context['remembered_experiences'] = memories_context
                enhanced_context['memory_context_available'] = True
                
                logger.debug(f"Enhanced context with {len(memories_context)} relevant memories")
                
        except Exception as e:
            logger.warning(f"Failed to recall memories for context enhancement: {e}")
            enhanced_context['memory_context_available'] = False
        
        return enhanced_context
    
    async def _post_deliberation_hooks(self, result: DeliberationResult):
        """
        Post-deliberation processing: store memories and update knowledge graph
        """
        try:
            # Store memories for each persona
            await self._store_deliberation_memories(result)
            
            # Update knowledge graph
            await self._update_knowledge_graph(result)
            
            logger.debug(f"Post-deliberation hooks completed for topic: {result.blackboard_topic}")
            
        except Exception as e:
            logger.error(f"Error in post-deliberation hooks: {e}", exc_info=True)
    
    async def _store_deliberation_memories(self, result: DeliberationResult):
        """
        Store deliberation results as memories using the new memory system
        """
        if not self.memory_system:
            logger.warning("Memory system not available - skipping memory storage")
            return
            
        try:
            # Store the complete deliberation in the memory system
            await self.memory_system.store_deliberation(result.request, result)
            logger.debug(f"Stored deliberation memory for topic: {result.blackboard_topic}")
            
        except Exception as e:
            logger.error(f"Failed to store deliberation memories: {e}", exc_info=True)
    
    async def _update_knowledge_graph(self, result: DeliberationResult):
        """
        Update knowledge graph with concepts and relationships from deliberation
        """
        try:
            # Extract key concepts from the query
            query_concepts = await self._extract_concepts(result.request.query)
            
            # Create or update nodes for key concepts
            concept_nodes = []
            for concept in query_concepts:
                node = await self.knowledge_graph.add_node(
                    name=concept,
                    node_type=NodeType.CONCEPT,
                    importance=0.7,  # Concepts from deliberations are fairly important
                    attributes={'source': 'deliberation', 'topic': result.blackboard_topic}
                )
                concept_nodes.append(node)
            
            # Create decision node
            decision_node = await self.knowledge_graph.add_node(
                name=f"Decision: {result.consensus.decision[:50]}",
                node_type=NodeType.DECISION,
                importance=min(1.0, result.consensus.confidence * 1.1),
                attributes={
                    'decision': result.consensus.decision,
                    'confidence': result.consensus.confidence,
                    'agreement_level': result.consensus.agreement_level,
                    'timestamp': result.timestamp.isoformat()
                }
            )
            
            # Link concepts to decision
            for concept_node in concept_nodes:
                await self.knowledge_graph.add_edge(
                    source_id=concept_node.id,
                    target_id=decision_node.id,
                    edge_type=EdgeType.LEADS_TO,
                    weight=result.consensus.confidence,
                    confidence=0.8
                )
            
            # Create persona expertise connections
            for response in result.persona_responses:
                # Find or create persona node
                persona_node = await self.knowledge_graph.add_node(
                    name=f"Persona: {response.persona_id}",
                    node_type=NodeType.PERSON,
                    importance=0.8,
                    attributes={'persona_type': 'ai_assistant'}
                )
                
                # Link persona to decision with confidence as weight
                await self.knowledge_graph.add_edge(
                    source_id=persona_node.id,
                    target_id=decision_node.id,
                    edge_type=EdgeType.INFLUENCES,
                    weight=response.confidence,
                    confidence=response.confidence,
                    attributes={
                        'recommendation': response.recommendation,
                        'concerns': response.concerns[:3],  # Top 3 concerns
                        'opportunities': response.opportunities[:3]  # Top 3 opportunities
                    }
                )
                
                # Link persona to concepts they have expertise in
                persona = self.personas.get(response.persona_id)
                if persona:
                    for domain in persona.expertise_domains[:3]:  # Top 3 domains
                        domain_node = await self.knowledge_graph.add_node(
                            name=domain,
                            node_type=NodeType.SKILL,
                            importance=0.6
                        )
                        
                        await self.knowledge_graph.add_edge(
                            source_id=persona_node.id,
                            target_id=domain_node.id,
                            edge_type=EdgeType.BELONGS_TO,
                            weight=0.8,
                            confidence=0.9
                        )
            
            logger.debug(f"Updated knowledge graph with {len(concept_nodes)} concepts and 1 decision")
            
        except Exception as e:
            logger.error(f"Failed to update knowledge graph: {e}", exc_info=True)
    
    async def _extract_concepts(self, text: str) -> List[str]:
        """
        Extract key concepts from text for knowledge graph
        Simple keyword extraction - could be enhanced with NLP
        """
        # Simple approach: extract meaningful words
        import re
        
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by', 'from', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'when', 'where', 'why', 'how', 'should', 'would', 'could', 'can', 'will', 'may', 'might', 'must'}
        
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        concepts = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Return top 5 unique concepts
        unique_concepts = list(dict.fromkeys(concepts))[:5]
        return unique_concepts