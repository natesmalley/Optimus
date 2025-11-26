"""
The Socialite - Relationships, Networking, and Communication

Focuses on interpersonal dynamics, relationship building, communication 
effectiveness, and social impacts of decisions. Prioritizes connection and collaboration.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class SocialitePersona(Persona):
    """
    The Socialite emphasizes relationships, communication, and social dynamics
    
    Key traits:
    - Relationship focus
    - Communication excellence  
    - Social awareness
    - Collaboration emphasis
    - Network building
    """
    
    def __init__(self):
        super().__init__(
            persona_id="socialite",
            name="The Socialite",
            description="Relationships and communication expert focused on interpersonal dynamics and social impact",
            expertise_domains=[
                "interpersonal relationships",
                "communication skills",
                "team dynamics",
                "networking",
                "collaboration",
                "conflict resolution",
                "social impact",
                "community building", 
                "empathy",
                "influence",
                "cultural sensitivity",
                "feedback dynamics"
            ],
            personality_traits=[
                "outgoing",
                "empathetic",
                "diplomatic",
                "inclusive",
                "collaborative"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from a social and relationship perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Social analysis framework
        relationship_impact = self._assess_relationship_impact(query, context)
        communication_factors = self._evaluate_communication_aspects(query, context)
        social_dynamics = self._analyze_social_dynamics(context)
        networking_potential = self._identify_networking_opportunities(context)
        
        # Build recommendation
        recommendation = self._formulate_social_guidance(
            query, relationship_impact, communication_factors, social_dynamics
        )
        
        # Identify social concerns
        concerns = []
        if relationship_impact.get('conflict_risk', 0) > 0.6:
            concerns.append("High potential for interpersonal conflict")
        if communication_factors.get('misunderstanding_risk', 0) > 0.5:
            concerns.append("Risk of miscommunication or unclear expectations")
        if social_dynamics.get('exclusion_risk', False):
            concerns.append("May inadvertently exclude or alienate team members")
        if relationship_impact.get('trust_impact', 0) < -0.3:
            concerns.append("Could damage existing trust relationships")
        
        # Identify social opportunities
        opportunities = []
        if networking_potential.get('new_connections'):
            opportunities.append("Excellent opportunity for building new relationships")
        if communication_factors.get('skill_development'):
            opportunities.append("Can enhance team communication skills")
        if social_dynamics.get('team_bonding', False):
            opportunities.append("Strong potential for team building and bonding")
        if relationship_impact.get('mentorship_potential', False):
            opportunities.append("Opportunity for mentoring and knowledge sharing")
        
        # Determine priority based on social impact
        priority = self._determine_social_priority(relationship_impact, social_dynamics, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_social_thinking(
                relationship_impact, communication_factors, social_dynamics
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'relationship_impact_score': relationship_impact.get('overall_impact', 0.5),
                'communication_clarity': communication_factors.get('clarity_score', 0.7),
                'social_cohesion': social_dynamics.get('cohesion_impact', 0.5),
                'stakeholder_count': relationship_impact.get('stakeholder_count', 1),
                'collaboration_level': social_dynamics.get('collaboration_required', 'medium')
            },
            tags={'relationships', 'communication', 'social', 'collaboration', 'teamwork'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on social information availability
        """
        confidence = 0.6  # Good base confidence for social dynamics
        
        # Increase confidence for team/relationship contexts
        if context.get('team_composition_known'):
            confidence += 0.15
        
        # Increase if communication patterns are known
        if context.get('communication_history') or context.get('team_dynamics_info'):
            confidence += 0.15
        
        # Increase if this involves social domains
        query_lower = query.lower()
        social_keywords = ['team', 'collaborate', 'communicate', 'share', 'discuss', 'meeting', 'feedback']
        if any(keyword in query_lower for keyword in social_keywords):
            confidence += 0.2
        
        # Decrease if social complexity is very high
        if context.get('multi_cultural_team', False):
            confidence -= 0.05  # Slight decrease for complexity, not lack of expertise
        
        return max(0.3, min(0.9, confidence))
    
    def _assess_relationship_impact(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess impact on relationships and interpersonal dynamics"""
        impact = {
            'stakeholder_count': 1,
            'relationship_depth': 'surface',  # surface, working, deep
            'trust_impact': 0.0,  # -1 to 1
            'conflict_risk': 0.3,
            'collaboration_boost': 0.3,
            'overall_impact': 0.3
        }
        
        # Analyze query for relationship implications
        query_lower = query.lower()
        
        if 'team' in query_lower:
            impact['stakeholder_count'] = 5
            impact['relationship_depth'] = 'working'
            impact['collaboration_boost'] = 0.6
        
        if 'collaborate' in query_lower or 'together' in query_lower:
            impact['collaboration_boost'] = 0.8
            impact['relationship_depth'] = 'working'
        
        if 'feedback' in query_lower or 'review' in query_lower:
            impact['trust_impact'] = 0.4
            impact['conflict_risk'] = 0.4
        
        if 'share' in query_lower or 'communicate' in query_lower:
            impact['trust_impact'] = 0.3
            impact['relationship_depth'] = 'working'
        
        if 'urgent' in query_lower or 'pressure' in query_lower:
            impact['conflict_risk'] = 0.6
            impact['trust_impact'] = -0.1
        
        # Check context for relationship factors
        if context.get('involves_multiple_teams', False):
            impact['stakeholder_count'] = 10
            impact['conflict_risk'] += 0.2
        
        if context.get('requires_consensus', False):
            impact['collaboration_boost'] = 0.7
            impact['conflict_risk'] = 0.5
        
        if context.get('cross_functional', False):
            impact['stakeholder_count'] += 3
            impact['relationship_depth'] = 'deep'
        
        if context.get('mentorship_opportunity', False):
            impact['mentorship_potential'] = True
            impact['trust_impact'] = 0.5
        
        # Calculate overall relationship impact
        impact['overall_impact'] = (
            (impact['stakeholder_count'] / 10) * 0.3 +
            impact['collaboration_boost'] * 0.4 +
            abs(impact['trust_impact']) * 0.3
        )
        
        return impact
    
    def _evaluate_communication_aspects(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate communication requirements and challenges"""
        factors = {
            'complexity': 'medium',  # low, medium, high
            'clarity_required': 0.7,
            'frequency_needed': 'regular',  # minimal, regular, frequent
            'misunderstanding_risk': 0.3,
            'clarity_score': 0.7
        }
        
        # Analyze query
        query_lower = query.lower()
        
        if 'complex' in query_lower or 'technical' in query_lower:
            factors['complexity'] = 'high'
            factors['misunderstanding_risk'] = 0.6
            factors['clarity_required'] = 0.9
        
        if 'simple' in query_lower or 'basic' in query_lower:
            factors['complexity'] = 'low'
            factors['misunderstanding_risk'] = 0.1
        
        if 'urgent' in query_lower or 'quick' in query_lower:
            factors['frequency_needed'] = 'frequent'
            factors['misunderstanding_risk'] += 0.2
        
        if 'document' in query_lower or 'write' in query_lower:
            factors['clarity_score'] = 0.9
            factors['misunderstanding_risk'] -= 0.2
        
        # Check context
        if context.get('distributed_team', False):
            factors['misunderstanding_risk'] += 0.2
            factors['clarity_required'] = 0.9
        
        if context.get('different_time_zones', False):
            factors['frequency_needed'] = 'minimal'
            factors['clarity_required'] = 0.95
        
        if context.get('skill_development', False):
            factors['skill_development'] = True
        
        return factors
    
    def _analyze_social_dynamics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze social dynamics and group effects"""
        dynamics = {
            'cohesion_impact': 0.5,  # Impact on team cohesion
            'inclusion_score': 0.7,
            'collaboration_required': 'medium',  # low, medium, high
            'cultural_sensitivity': 0.5,
            'power_dynamics': 'neutral'  # negative, neutral, positive
        }
        
        # Check context for social factors
        if context.get('diverse_team', False):
            dynamics['cultural_sensitivity'] = 0.8
            dynamics['inclusion_score'] = 0.6
        
        if context.get('cross_functional', False):
            dynamics['collaboration_required'] = 'high'
            dynamics['cohesion_impact'] = 0.7
        
        if context.get('involves_leadership', False):
            dynamics['power_dynamics'] = 'positive'
            dynamics['cohesion_impact'] = 0.6
        
        if context.get('competitive_environment', False):
            dynamics['cohesion_impact'] = 0.3
            dynamics['power_dynamics'] = 'negative'
        
        if context.get('team_building_potential', False):
            dynamics['team_bonding'] = True
            dynamics['cohesion_impact'] = 0.8
        
        if context.get('excludes_stakeholders', False):
            dynamics['exclusion_risk'] = True
            dynamics['inclusion_score'] = 0.3
        
        return dynamics
    
    def _identify_networking_opportunities(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify networking and relationship building opportunities"""
        return {
            'new_connections': context.get('involves_new_people', False),
            'industry_exposure': context.get('external_visibility', False),
            'skill_sharing': context.get('knowledge_exchange', False),
            'mentorship_opportunities': context.get('mentorship_potential', False),
            'community_building': context.get('community_impact', False),
            'professional_growth': context.get('career_development', False)
        }
    
    def _formulate_social_guidance(self, 
                                 query: str,
                                 relationship_impact: Dict[str, Any],
                                 communication_factors: Dict[str, Any],
                                 social_dynamics: Dict[str, Any]) -> str:
        """Formulate socially-aware guidance"""
        
        if relationship_impact['conflict_risk'] > 0.7:
            return (f"Social-first approach: High conflict risk ({relationship_impact['conflict_risk']:.0%}) "
                   f"requires careful stakeholder management and clear communication protocols")
        elif social_dynamics['collaboration_required'] == 'high' and social_dynamics['cohesion_impact'] > 0.6:
            return (f"Collaborative excellence opportunity: High collaboration needs with "
                   f"strong cohesion potential - invest in relationship building")
        elif communication_factors['misunderstanding_risk'] > 0.5:
            return (f"Communication-focused approach: High misunderstanding risk "
                   f"({communication_factors['misunderstanding_risk']:.0%}) - prioritize clarity and feedback loops")
        else:
            return (f"Relationship-conscious execution: Moderate social impact with "
                   f"{relationship_impact['stakeholder_count']} stakeholders - maintain open communication")
    
    def _explain_social_thinking(self,
                               relationship_impact: Dict[str, Any],
                               communication_factors: Dict[str, Any],
                               social_dynamics: Dict[str, Any]) -> str:
        """Explain the social reasoning"""
        
        reasoning = f"From a social perspective, this involves {relationship_impact['stakeholder_count']} stakeholders. "
        
        if relationship_impact['collaboration_boost'] > 0.6:
            reasoning += f"Strong collaboration potential ({relationship_impact['collaboration_boost']:.0%}). "
        
        if communication_factors['complexity'] == 'high':
            reasoning += "Communication complexity requires extra attention to clarity. "
        
        if social_dynamics['cohesion_impact'] > 0.6:
            reasoning += "Positive impact on team cohesion expected. "
        elif social_dynamics['cohesion_impact'] < 0.4:
            reasoning += "May challenge team cohesion - proactive relationship management needed. "
        
        if relationship_impact['conflict_risk'] > 0.5:
            reasoning += "Moderate conflict risk requires diplomatic handling. "
        
        if social_dynamics.get('cultural_sensitivity', 0) > 0.7:
            reasoning += "Cultural sensitivity is important for success. "
        
        reasoning += "Success depends on maintaining strong relationships and clear communication."
        
        return reasoning
    
    def _determine_social_priority(self, 
                                 relationship_impact: Dict[str, Any],
                                 social_dynamics: Dict[str, Any],
                                 context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from social perspective"""
        
        # Critical if relationship damage or major conflict risk
        if relationship_impact['conflict_risk'] > 0.8:
            return PersonaPriority.CRITICAL
        if relationship_impact['trust_impact'] < -0.5:
            return PersonaPriority.CRITICAL
        
        # High if significant stakeholder impact or collaboration opportunity
        if relationship_impact['stakeholder_count'] > 8:
            return PersonaPriority.HIGH
        if social_dynamics['collaboration_required'] == 'high':
            return PersonaPriority.HIGH
        
        # Low if minimal social implications
        if relationship_impact['stakeholder_count'] <= 2 and relationship_impact['conflict_risk'] < 0.3:
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in warm, socially-aware style"""
        return f"From a relationships perspective: {content} Remember, our connections with others amplify our success."