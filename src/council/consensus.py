"""
Consensus Engine - Weighted Voting and Decision Making

Aggregates persona responses, applies weighted voting based on expertise,
and produces final consensus decisions with confidence scores.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import statistics

from .persona import PersonaResponse, PersonaPriority
from .blackboard import Blackboard, BlackboardEntry, EntryType

logger = logging.getLogger(__name__)


class ConsensusMethod(Enum):
    """Methods for reaching consensus"""
    WEIGHTED_MAJORITY = "weighted_majority"    # Weighted voting based on expertise
    SUPERMAJORITY = "supermajority"           # Requires 66% agreement
    UNANIMOUS = "unanimous"                    # Requires 100% agreement
    CONFIDENCE_WEIGHTED = "confidence_weighted" # Weight by confidence scores
    HYBRID = "hybrid"                          # Combine multiple methods


@dataclass
class ConsensusResult:
    """Result of consensus process"""
    decision: str                          # Final decision/recommendation
    confidence: float                       # Overall confidence (0-1)
    method_used: ConsensusMethod           # How consensus was reached
    agreement_level: float                 # Percentage of agreement
    supporting_personas: List[str]          # Personas supporting decision
    dissenting_personas: List[str]         # Personas disagreeing
    alternative_views: Dict[str, str]      # Alternative recommendations
    rationale: str                         # Explanation of consensus
    priority: PersonaPriority              # Consensus priority level
    data_summary: Dict[str, Any]          # Aggregated data points
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'decision': self.decision,
            'confidence': self.confidence,
            'method': self.method_used.value,
            'agreement_level': self.agreement_level,
            'supporting_personas': self.supporting_personas,
            'dissenting_personas': self.dissenting_personas,
            'alternative_views': self.alternative_views,
            'rationale': self.rationale,
            'priority': self.priority.value,
            'data_summary': self.data_summary,
            'timestamp': self.timestamp.isoformat()
        }


class ConsensusEngine:
    """
    Engine for reaching consensus among multiple personas
    
    Features:
    - Multiple consensus methods
    - Weighted voting based on expertise
    - Confidence aggregation
    - Conflict resolution
    - Minority opinion tracking
    """
    
    def __init__(self, 
                 blackboard: Blackboard,
                 default_method: ConsensusMethod = ConsensusMethod.HYBRID):
        """
        Initialize consensus engine
        
        Args:
            blackboard: Shared blackboard for recording consensus
            default_method: Default consensus method to use
        """
        self.blackboard = blackboard
        self.default_method = default_method
        self.consensus_history: List[ConsensusResult] = []
        
    async def reach_consensus(self,
                             topic: str,
                             responses: List[PersonaResponse],
                             weights: Optional[Dict[str, float]] = None,
                             method: Optional[ConsensusMethod] = None) -> ConsensusResult:
        """
        Process persona responses and reach consensus
        
        Args:
            topic: The topic being decided
            responses: List of persona responses
            weights: Optional expertise weights for each persona
            method: Consensus method to use (defaults to engine default)
            
        Returns:
            ConsensusResult with final decision
        """
        if not responses:
            raise ValueError("No responses to process for consensus")
        
        method = method or self.default_method
        
        # Calculate weights if not provided
        if weights is None:
            weights = self._calculate_default_weights(responses)
        
        # Apply consensus method
        if method == ConsensusMethod.WEIGHTED_MAJORITY:
            result = await self._weighted_majority_consensus(responses, weights)
        elif method == ConsensusMethod.SUPERMAJORITY:
            result = await self._supermajority_consensus(responses)
        elif method == ConsensusMethod.UNANIMOUS:
            result = await self._unanimous_consensus(responses)
        elif method == ConsensusMethod.CONFIDENCE_WEIGHTED:
            result = await self._confidence_weighted_consensus(responses)
        else:  # HYBRID
            result = await self._hybrid_consensus(responses, weights)
        
        # Record to blackboard
        await self._record_consensus(topic, result)
        
        # Store in history
        self.consensus_history.append(result)
        
        return result
    
    async def _weighted_majority_consensus(self, 
                                          responses: List[PersonaResponse],
                                          weights: Dict[str, float]) -> ConsensusResult:
        """
        Reach consensus through weighted majority voting
        """
        # Group recommendations
        recommendation_votes = {}
        for response in responses:
            rec = response.recommendation
            if rec not in recommendation_votes:
                recommendation_votes[rec] = {
                    'weight': 0,
                    'supporters': [],
                    'confidence_sum': 0
                }
            
            weight = weights.get(response.persona_id, 1.0) * response.confidence
            recommendation_votes[rec]['weight'] += weight
            recommendation_votes[rec]['supporters'].append(response.persona_id)
            recommendation_votes[rec]['confidence_sum'] += response.confidence
        
        # Find winner
        winner = max(recommendation_votes.items(), key=lambda x: x[1]['weight'])
        decision = winner[0]
        support_data = winner[1]
        
        # Calculate agreement level
        total_weight = sum(v['weight'] for v in recommendation_votes.values())
        agreement = support_data['weight'] / total_weight if total_weight > 0 else 0
        
        # Identify dissenters
        dissenters = []
        alternatives = {}
        for rec, data in recommendation_votes.items():
            if rec != decision:
                for persona in data['supporters']:
                    dissenters.append(persona)
                    alternatives[persona] = rec
        
        # Calculate overall confidence
        avg_confidence = support_data['confidence_sum'] / len(support_data['supporters'])
        
        # Don't just multiply by agreement - that penalizes thoughtful disagreement
        # Instead, weight by the strength of the leading recommendation
        if agreement >= 0.6:
            # High agreement: full confidence
            overall_confidence = avg_confidence
        elif agreement >= 0.4:
            # Moderate agreement: slight reduction
            overall_confidence = avg_confidence * 0.85
        elif agreement >= 0.2:
            # Low agreement but still a clear leader: moderate confidence
            overall_confidence = avg_confidence * 0.7
        else:
            # Very low agreement: significant reduction
            overall_confidence = avg_confidence * 0.5
        
        # Determine priority
        priority = self._determine_consensus_priority(responses, agreement)
        
        return ConsensusResult(
            decision=decision,
            confidence=overall_confidence,
            method_used=ConsensusMethod.WEIGHTED_MAJORITY,
            agreement_level=agreement,
            supporting_personas=support_data['supporters'],
            dissenting_personas=dissenters,
            alternative_views=alternatives,
            rationale=self._generate_rationale(decision, agreement, support_data['supporters']),
            priority=priority,
            data_summary=self._aggregate_data_points(responses)
        )
    
    async def _supermajority_consensus(self, responses: List[PersonaResponse]) -> ConsensusResult:
        """
        Require 66% agreement for consensus
        """
        # Count recommendations
        recommendation_counts = {}
        for response in responses:
            rec = response.recommendation
            if rec not in recommendation_counts:
                recommendation_counts[rec] = []
            recommendation_counts[rec].append(response.persona_id)
        
        total = len(responses)
        supermajority_threshold = total * 0.66
        
        # Find if any recommendation has supermajority
        for rec, supporters in recommendation_counts.items():
            if len(supporters) >= supermajority_threshold:
                agreement = len(supporters) / total
                dissenters = [r.persona_id for r in responses if r.persona_id not in supporters]
                
                return ConsensusResult(
                    decision=rec,
                    confidence=agreement * 0.85,  # High confidence for supermajority
                    method_used=ConsensusMethod.SUPERMAJORITY,
                    agreement_level=agreement,
                    supporting_personas=supporters,
                    dissenting_personas=dissenters,
                    alternative_views={p: r.recommendation for r in responses for p in [r.persona_id] if p in dissenters},
                    rationale=f"Supermajority consensus ({agreement:.0%}) reached",
                    priority=self._determine_consensus_priority(responses, agreement),
                    data_summary=self._aggregate_data_points(responses)
                )
        
        # No supermajority - fall back to plurality
        winner = max(recommendation_counts.items(), key=lambda x: len(x[1]))
        return await self._weighted_majority_consensus(responses, {r.persona_id: 1.0 for r in responses})
    
    async def _unanimous_consensus(self, responses: List[PersonaResponse]) -> ConsensusResult:
        """
        Require unanimous agreement
        """
        recommendations = set(r.recommendation for r in responses)
        
        if len(recommendations) == 1:
            # Unanimous!
            decision = recommendations.pop()
            return ConsensusResult(
                decision=decision,
                confidence=0.95,  # Very high confidence for unanimity
                method_used=ConsensusMethod.UNANIMOUS,
                agreement_level=1.0,
                supporting_personas=[r.persona_id for r in responses],
                dissenting_personas=[],
                alternative_views={},
                rationale="Unanimous consensus achieved",
                priority=PersonaPriority.CRITICAL,  # Unanimous = important
                data_summary=self._aggregate_data_points(responses)
            )
        else:
            # No unanimity - note disagreement
            return await self._weighted_majority_consensus(responses, {r.persona_id: 1.0 for r in responses})
    
    async def _confidence_weighted_consensus(self, responses: List[PersonaResponse]) -> ConsensusResult:
        """
        Weight purely by confidence scores
        """
        weights = {r.persona_id: r.confidence for r in responses}
        return await self._weighted_majority_consensus(responses, weights)
    
    async def _hybrid_consensus(self, 
                               responses: List[PersonaResponse],
                               weights: Dict[str, float]) -> ConsensusResult:
        """
        Hybrid approach combining multiple methods
        """
        # Try unanimous first
        recommendations = set(r.recommendation for r in responses)
        if len(recommendations) == 1:
            return await self._unanimous_consensus(responses)
        
        # Check for supermajority
        rec_counts = {}
        for r in responses:
            rec_counts[r.recommendation] = rec_counts.get(r.recommendation, 0) + 1
        
        max_count = max(rec_counts.values())
        if max_count >= len(responses) * 0.66:
            return await self._supermajority_consensus(responses)
        
        # Fall back to weighted majority with confidence
        combined_weights = {}
        for response in responses:
            expertise_weight = weights.get(response.persona_id, 1.0)
            confidence_weight = response.confidence
            combined_weights[response.persona_id] = (expertise_weight + confidence_weight) / 2
        
        return await self._weighted_majority_consensus(responses, combined_weights)
    
    def _calculate_default_weights(self, responses: List[PersonaResponse]) -> Dict[str, float]:
        """
        Calculate default weights based on response characteristics
        """
        weights = {}
        for response in responses:
            # Base weight of 1.0
            weight = 1.0
            
            # Adjust for priority
            if response.priority == PersonaPriority.CRITICAL:
                weight *= 1.5
            elif response.priority == PersonaPriority.HIGH:
                weight *= 1.2
            elif response.priority == PersonaPriority.LOW:
                weight *= 0.8
            
            weights[response.persona_id] = weight
        
        return weights
    
    def _determine_consensus_priority(self, 
                                     responses: List[PersonaResponse],
                                     agreement: float) -> PersonaPriority:
        """
        Determine overall priority from responses
        """
        # Count priority levels
        priority_counts = {}
        for response in responses:
            p = response.priority
            priority_counts[p] = priority_counts.get(p, 0) + 1
        
        # If any critical, consensus is critical
        if PersonaPriority.CRITICAL in priority_counts:
            return PersonaPriority.CRITICAL
        
        # If majority high priority and high agreement
        if priority_counts.get(PersonaPriority.HIGH, 0) > len(responses) / 2 and agreement > 0.7:
            return PersonaPriority.HIGH
        
        # If low agreement, reduce priority
        if agreement < 0.5:
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def _aggregate_data_points(self, responses: List[PersonaResponse]) -> Dict[str, Any]:
        """
        Aggregate data points from all responses
        """
        aggregated = {
            'total_personas': len(responses),
            'avg_confidence': statistics.mean(r.confidence for r in responses),
            'concerns_raised': sum(len(r.concerns) for r in responses),
            'opportunities_identified': sum(len(r.opportunities) for r in responses),
        }
        
        # Collect all unique tags
        all_tags = set()
        for response in responses:
            all_tags.update(response.tags)
        aggregated['tags'] = list(all_tags)
        
        # Priority distribution
        priority_dist = {}
        for response in responses:
            p = response.priority.value
            priority_dist[p] = priority_dist.get(p, 0) + 1
        aggregated['priority_distribution'] = priority_dist
        
        return aggregated
    
    def _generate_rationale(self, decision: str, agreement: float, supporters: List[str]) -> str:
        """
        Generate explanation for the consensus
        """
        if agreement >= 0.9:
            return f"Strong consensus ({agreement:.0%}) among {', '.join(supporters)}"
        elif agreement >= 0.66:
            return f"Clear majority ({agreement:.0%}) supports this decision"
        elif agreement >= 0.5:
            return f"Moderate agreement ({agreement:.0%}) with some dissent"
        else:
            return f"Weak consensus ({agreement:.0%}) - significant disagreement exists"
    
    async def _record_consensus(self, topic: str, result: ConsensusResult):
        """
        Record consensus result to blackboard
        """
        consensus_entry = BlackboardEntry(
            persona_id="consensus_engine",
            entry_type=EntryType.CONSENSUS,
            content=result.decision,
            confidence=result.confidence,
            metadata={
                'agreement_level': result.agreement_level,
                'method': result.method_used.value,
                'supporters': result.supporting_personas,
                'dissenters': result.dissenting_personas,
                'priority': result.priority.value
            },
            tags={'consensus', 'decision', 'final'}
        )
        
        await self.blackboard.post(topic, consensus_entry)
        
        # Post rationale
        rationale_entry = BlackboardEntry(
            persona_id="consensus_engine",
            entry_type=EntryType.INSIGHT,
            content=result.rationale,
            confidence=result.confidence,
            references=[consensus_entry.id],
            metadata={'type': 'consensus_rationale'},
            tags={'consensus', 'rationale'}
        )
        
        await self.blackboard.post(topic, rationale_entry)