"""
Base Persona Class - Foundation for All Council Members

Each persona represents a unique perspective and decision-making approach.
Personas analyze situations, contribute insights, and participate in consensus.
Now enhanced with comprehensive tool integration capabilities.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum

from .blackboard import Blackboard, BlackboardEntry, EntryType

# Avoid circular import by importing ToolCapability at runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .tool_integration import ToolCapability, PersonaToolIntegration

logger = logging.getLogger(__name__)


class PersonaPriority(Enum):
    """Priority levels for persona responses"""
    CRITICAL = 1    # Must be addressed immediately
    HIGH = 2        # Important consideration
    MEDIUM = 3      # Standard priority
    LOW = 4         # Nice to have
    INFORMATIONAL = 5  # FYI only


@dataclass
class PersonaResponse:
    """Response from a persona's analysis"""
    persona_id: str
    persona_name: str
    recommendation: str  # Main recommendation
    reasoning: str  # Explanation of thinking
    confidence: float  # 0.0 to 1.0
    priority: PersonaPriority = PersonaPriority.MEDIUM
    concerns: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    data_points: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'persona_id': self.persona_id,
            'persona_name': self.persona_name,
            'recommendation': self.recommendation,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'priority': self.priority.value,
            'concerns': self.concerns,
            'opportunities': self.opportunities,
            'data_points': self.data_points,
            'tags': list(self.tags),
            'timestamp': self.timestamp.isoformat()
        }


class Persona(ABC):
    """
    Abstract base class for all personas in the Council of Minds
    
    Each persona has:
    - Unique identity and perspective
    - Domain expertise areas
    - Analysis capabilities
    - Confidence calculation methods
    - Communication style
    - Tool integration capabilities (via composition)
    """
    
    def __init__(self, 
                 persona_id: str,
                 name: str,
                 description: str,
                 expertise_domains: List[str],
                 personality_traits: List[str]):
        """
        Initialize a persona
        
        Args:
            persona_id: Unique identifier for this persona
            name: Human-readable name
            description: Description of persona's role and perspective
            expertise_domains: Areas where this persona has authority
            personality_traits: Traits that influence decision-making
        """
        self.persona_id = persona_id
        self.name = name
        self.description = description
        self.expertise_domains = expertise_domains
        self.personality_traits = personality_traits
        self.blackboard: Optional[Blackboard] = None
        self.memory: Dict[str, Any] = {}  # Persona's private memory
        self.decision_history: List[PersonaResponse] = []
        
        # Tool capabilities will be added via composition
        self._tool_capability: Optional['ToolCapability'] = None
        
    def connect_blackboard(self, blackboard: Blackboard):
        """Connect this persona to the shared blackboard"""
        self.blackboard = blackboard
        logger.info(f"{self.name} connected to blackboard")
    
    def add_tool_capabilities(self, tool_capability: 'ToolCapability'):
        """Add tool capabilities to this persona"""
        self._tool_capability = tool_capability
        
    def get_tool_capabilities(self) -> Optional['ToolCapability']:
        """Get tool capabilities if available"""
        return self._tool_capability
    
    @abstractmethod
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze a query and provide this persona's perspective
        
        Args:
            query: The question or situation to analyze
            context: Additional context (project data, metrics, etc.)
            related_entries: Relevant blackboard entries from other personas
            
        Returns:
            PersonaResponse with this persona's analysis
        """
        pass
    
    @abstractmethod
    def calculate_confidence(self, 
                           query: str,
                           context: Dict[str, Any]) -> float:
        """
        Calculate confidence level for this query
        
        Args:
            query: The question being asked
            context: Available context
            
        Returns:
            Confidence score from 0.0 to 1.0
        """
        pass
    
    async def deliberate(self, 
                        topic: str,
                        query: str,
                        context: Dict[str, Any]) -> PersonaResponse:
        """
        Full deliberation process including blackboard interaction
        
        1. Read relevant entries from blackboard
        2. Analyze the situation
        3. Post insights to blackboard
        4. Return final response
        """
        if not self.blackboard:
            raise ValueError(f"{self.name} is not connected to blackboard")
        
        # Read relevant entries
        related_entries = await self.blackboard.read(topic=topic, limit=50)
        
        # Perform analysis
        response = await self.analyze(query, context, related_entries)
        
        # Post initial insights to blackboard
        insight_entry = BlackboardEntry(
            persona_id=self.persona_id,
            entry_type=EntryType.INSIGHT,
            content=response.reasoning,
            confidence=response.confidence,
            tags=response.tags,
            metadata={
                'persona_name': self.name,
                'priority': response.priority.value
            }
        )
        await self.blackboard.post(topic, insight_entry)
        
        # Post recommendation if confident enough
        if response.confidence >= 0.6:
            rec_entry = BlackboardEntry(
                persona_id=self.persona_id,
                entry_type=EntryType.RECOMMENDATION,
                content=response.recommendation,
                confidence=response.confidence,
                tags=response.tags,
                references=[insight_entry.id],
                metadata={
                    'persona_name': self.name,
                    'priority': response.priority.value
                }
            )
            await self.blackboard.post(topic, rec_entry)
        
        # Post concerns if any
        for concern in response.concerns:
            concern_entry = BlackboardEntry(
                persona_id=self.persona_id,
                entry_type=EntryType.CONCERN,
                content=concern,
                confidence=response.confidence,
                tags=response.tags,
                references=[insight_entry.id],
                metadata={'persona_name': self.name}
            )
            await self.blackboard.post(topic, concern_entry)
        
        # Store in decision history
        self.decision_history.append(response)
        
        return response
    
    def is_expert_in(self, domain: str) -> bool:
        """Check if this persona has expertise in a domain"""
        return any(domain.lower() in exp.lower() for exp in self.expertise_domains)
    
    def get_expertise_weight(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate expertise weight for weighted voting
        
        Returns a weight from 0.0 to 1.0 based on relevance
        """
        # Check for domain keyword matches
        query_lower = query.lower()
        weight = 0.0
        
        for domain in self.expertise_domains:
            if domain.lower() in query_lower:
                weight += 0.3
        
        # Check context tags if available
        if 'tags' in context:
            for tag in context['tags']:
                if self.is_expert_in(tag):
                    weight += 0.2
        
        # Personality traits can also influence weight
        # (e.g., Guardian persona has higher weight for security questions)
        if 'category' in context:
            category = context['category']
            if category in self.expertise_domains:
                weight += 0.5
        
        return min(weight, 1.0)  # Cap at 1.0
    
    async def reflect_on_consensus(self, 
                                   topic: str,
                                   final_decision: str,
                                   consensus_data: Dict[str, Any]):
        """
        Reflect on the final consensus decision
        
        Allows personas to learn and update their internal state
        """
        # Read the consensus trail
        trail = await self.blackboard.get_consensus_trail(topic)
        
        # Update memory with lessons learned
        self.memory[topic] = {
            'final_decision': final_decision,
            'my_recommendation': self.decision_history[-1].recommendation if self.decision_history else None,
            'consensus_confidence': consensus_data.get('confidence', 0),
            'timestamp': datetime.now()
        }
        
        # Post reflection if significantly different from consensus
        if self.decision_history:
            my_last = self.decision_history[-1]
            if my_last.recommendation != final_decision and my_last.confidence > 0.7:
                reflection = BlackboardEntry(
                    persona_id=self.persona_id,
                    entry_type=EntryType.INSIGHT,
                    content=f"Reflection: The consensus differed from my recommendation. "
                           f"I suggested '{my_last.recommendation}' with {my_last.confidence:.0%} confidence. "
                           f"Will incorporate this learning.",
                    confidence=0.5,
                    metadata={
                        'persona_name': self.name,
                        'type': 'reflection'
                    }
                )
                await self.blackboard.post(f"{topic}_reflections", reflection)
    
    def format_response_style(self, content: str) -> str:
        """
        Format response according to persona's communication style
        
        Override in subclasses for unique styles
        """
        return content
    
    def __repr__(self) -> str:
        return f"{self.name} ({self.persona_id}): {self.description[:50]}..."