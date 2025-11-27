"""
The Strategist - Long-term Vision and Planning

Focuses on strategic implications, long-term consequences, and alignment 
with overarching goals. Thinks in quarters and years, not days.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class StrategistPersona(Persona):
    """
    The Strategist sees the big picture and long-term implications
    
    Key traits:
    - Visionary thinking
    - Pattern recognition across time
    - Goal alignment focus
    - Risk/opportunity balance
    - Strategic positioning
    """
    
    def __init__(self):
        super().__init__(
            persona_id="strategist",
            name="The Strategist",
            description="Long-term vision and strategic planning expert focused on sustainable growth and positioning",
            expertise_domains=[
                "strategic planning",
                "long-term vision",
                "goal alignment",
                "market positioning",
                "competitive advantage",
                "scalability",
                "sustainability",
                "roadmap planning"
            ],
            personality_traits=[
                "visionary",
                "analytical",
                "patient",
                "systematic",
                "forward-thinking"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from a strategic perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Strategic analysis framework
        strategic_factors = self._assess_strategic_factors(query, context)
        long_term_impacts = self._evaluate_long_term_impacts(context)
        alignment_score = self._check_goal_alignment(context)
        
        # Build recommendation
        recommendation = self._formulate_strategic_recommendation(
            query, strategic_factors, long_term_impacts, alignment_score
        )
        
        # Identify strategic concerns
        concerns = []
        if alignment_score < 0.5:
            concerns.append("This may not align well with long-term strategic goals")
        if strategic_factors.get('technical_debt_risk', 0) > 0.7:
            concerns.append("High technical debt could impede future strategic initiatives")
        if strategic_factors.get('scalability_issues', False):
            concerns.append("Scalability concerns could limit future growth potential")
        
        # Identify strategic opportunities
        opportunities = []
        if strategic_factors.get('market_advantage', 0) > 0.6:
            opportunities.append("This could provide significant competitive advantage")
        if strategic_factors.get('platform_potential', False):
            opportunities.append("Potential to evolve into a platform play")
        if long_term_impacts.get('compound_benefits', False):
            opportunities.append("Benefits will compound over time")
        
        # Determine priority based on strategic importance
        priority = self._determine_strategic_priority(strategic_factors, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_strategic_thinking(
                strategic_factors, long_term_impacts, alignment_score
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'strategic_alignment': alignment_score,
                'time_horizon': strategic_factors.get('time_horizon', 'medium'),
                'roi_projection': strategic_factors.get('roi_projection', 'unknown'),
                'strategic_factors': strategic_factors,
                'long_term_impacts': long_term_impacts
            },
            tags={'strategic', 'long-term', 'vision', 'planning'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on available strategic information
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence if we have good historical data
        if context.get('historical_data'):
            confidence += 0.15
        
        # Increase if we have clear goals defined
        if context.get('project_goals') or context.get('business_objectives'):
            confidence += 0.15
        
        # Increase if this is in our domain
        query_lower = query.lower()
        strategic_keywords = ['long-term', 'strategy', 'roadmap', 'vision', 'future', 'scale', 'growth']
        if any(keyword in query_lower for keyword in strategic_keywords):
            confidence += 0.2
        
        # Decrease if situation is highly volatile
        if context.get('high_uncertainty', False):
            confidence -= 0.15
        
        return max(0.1, min(0.95, confidence))
    
    def _assess_strategic_factors(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess key strategic factors"""
        factors = {
            'time_horizon': 'medium',  # short, medium, long
            'scalability_impact': 0.5,
            'technical_debt_risk': 0.3,
            'market_advantage': 0.4,
            'resource_intensity': 0.5,
        }
        
        # Analyze query for strategic implications
        query_lower = query.lower()
        
        # Specific analysis for microservices question
        if 'microservice' in query_lower:
            team_size = context.get('team_size', 5)
            startup_stage = context.get('startup_stage', 'unknown')
            
            if team_size <= 3:
                factors['resource_intensity'] = 0.8  # High overhead for small team
                factors['technical_debt_risk'] = 0.7  # Adds complexity
                factors['scalability_impact'] = 0.3  # Premature optimization
                factors['time_horizon'] = 'short'  # Focus on speed to market
            elif team_size >= 10:
                factors['scalability_impact'] = 0.8  # Good for large teams
                factors['resource_intensity'] = 0.4  # Team can handle complexity
                factors['time_horizon'] = 'long'
            
            if startup_stage == 'early':
                factors['market_advantage'] = 0.2  # Focus should be on product-market fit
                factors['time_horizon'] = 'short'
        
        if 'refactor' in query_lower or 'rewrite' in query_lower:
            factors['technical_debt_risk'] = 0.2  # Reduces debt
            factors['time_horizon'] = 'long'
            factors['scalability_impact'] = 0.8
        
        if 'new feature' in query_lower or 'add' in query_lower:
            factors['market_advantage'] = 0.7
            factors['time_horizon'] = 'medium'
        
        if 'optimize' in query_lower or 'performance' in query_lower:
            factors['scalability_impact'] = 0.9
            factors['resource_intensity'] = 0.3
        
        # Check context for project maturity
        if context.get('project_age_days', 0) > 365:
            factors['platform_potential'] = True
        
        if context.get('user_count', 0) > 1000:
            factors['scalability_issues'] = context.get('performance_issues', False)
        
        return factors
    
    def _evaluate_long_term_impacts(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate long-term impacts of the decision"""
        return {
            'compound_benefits': context.get('recurring_value', False),
            'maintenance_burden': context.get('complexity_increase', 0.5),
            'ecosystem_effects': context.get('affects_other_projects', False),
            'skill_development': context.get('team_learning', False),
            'market_positioning': context.get('competitive_advantage', 0.5)
        }
    
    def _check_goal_alignment(self, context: Dict[str, Any]) -> float:
        """Check alignment with strategic goals"""
        alignment = 0.5  # Neutral default
        
        # Check against stated goals
        if 'project_goals' in context:
            # Simple keyword matching for demonstration
            goals = context['project_goals']
            if isinstance(goals, list):
                alignment = 0.7  # Assume reasonable alignment if goals exist
        
        # Check against business objectives
        if context.get('revenue_impact', 0) > 0:
            alignment += 0.2
        
        if context.get('user_satisfaction_impact', 0) > 0:
            alignment += 0.1
        
        return min(1.0, alignment)
    
    def _formulate_strategic_recommendation(self, 
                                           query: str,
                                           factors: Dict[str, Any],
                                           impacts: Dict[str, Any],
                                           alignment: float) -> str:
        """Formulate the strategic recommendation"""
        
        # Specific recommendations for microservices
        if 'microservice' in query.lower():
            if factors['resource_intensity'] > 0.7:  # Small team scenario
                return ("Strategic recommendation: Avoid microservices now. "
                       "Focus on monolithic architecture for speed and simplicity. "
                       "Consider microservices when team grows beyond 8-10 developers.")
            elif factors['scalability_impact'] > 0.7:  # Large team scenario
                return ("Strategic recommendation: Microservices architecture aligns with growth strategy. "
                       "Implement gradually starting with bounded contexts.")
        
        # General recommendations
        if alignment > 0.7 and factors['scalability_impact'] > 0.7:
            return (f"Strongly recommend proceeding - high strategic alignment "
                   f"({alignment:.0%}) with significant scalability benefits")
        elif alignment > 0.5 and impacts['compound_benefits']:
            return (f"Recommend proceeding with phased approach to maximize "
                   f"compound benefits over {factors['time_horizon']}-term")
        elif alignment < 0.3:
            return (f"Recommend deferring or reconsidering - low strategic "
                   f"alignment ({alignment:.0%}) suggests better alternatives exist")
        else:
            return (f"Proceed with caution - moderate strategic value with "
                   f"{factors['time_horizon']}-term horizon. Monitor outcomes closely")
    
    def _explain_strategic_thinking(self,
                                   factors: Dict[str, Any],
                                   impacts: Dict[str, Any],
                                   alignment: float) -> str:
        """Explain the strategic reasoning"""
        
        reasoning = f"From a strategic perspective, this decision involves {factors['time_horizon']}-term planning. "
        
        if alignment > 0.6:
            reasoning += f"It aligns well with strategic objectives ({alignment:.0%}). "
        else:
            reasoning += f"Strategic alignment is moderate ({alignment:.0%}), suggesting careful consideration needed. "
        
        if factors['scalability_impact'] > 0.7:
            reasoning += "This will significantly improve scalability. "
        
        if impacts['compound_benefits']:
            reasoning += "The benefits will compound over time, increasing long-term value. "
        
        if factors.get('technical_debt_risk', 0) < 0.3:
            reasoning += "This helps reduce technical debt, enabling future agility. "
        
        return reasoning
    
    def _determine_strategic_priority(self, 
                                     factors: Dict[str, Any],
                                     context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from strategic perspective"""
        
        # Critical if it affects core strategic objectives
        if context.get('blocks_strategic_initiative', False):
            return PersonaPriority.CRITICAL
        
        # High if strong alignment and scalability impact
        if factors['scalability_impact'] > 0.8 or factors.get('market_advantage', 0) > 0.8:
            return PersonaPriority.HIGH
        
        # Low if poor alignment
        alignment = context.get('strategic_alignment', 0.5)
        if alignment < 0.3:
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM