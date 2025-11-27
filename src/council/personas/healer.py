"""
The Healer - Physical and Mental Health and Wellness

Focuses on health implications, wellness considerations, self-care practices,
and holistic wellbeing. Promotes sustainable, healthy approaches to life and work.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class HealerPersona(Persona):
    """
    The Healer prioritizes health, wellness, and sustainable practices
    
    Key traits:
    - Holistic health perspective
    - Sustainability focus
    - Stress awareness
    - Work-life balance
    - Prevention mindset
    """
    
    def __init__(self):
        super().__init__(
            persona_id="healer",
            name="The Healer",
            description="Health and wellness expert focused on sustainable practices and holistic wellbeing",
            expertise_domains=[
                "mental health",
                "physical wellness", 
                "work-life balance",
                "stress management",
                "sustainable practices",
                "ergonomics",
                "burnout prevention",
                "team wellbeing",
                "healthy habits",
                "recovery practices",
                "mindfulness",
                "energy management"
            ],
            personality_traits=[
                "caring",
                "holistic", 
                "preventive",
                "nurturing",
                "balanced"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from a health and wellness perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Wellness analysis framework
        health_impact = self._assess_health_impact(query, context)
        sustainability_score = self._evaluate_sustainability(context)
        stress_factors = self._identify_stress_factors(query, context)
        wellness_opportunities = self._find_wellness_opportunities(context)
        
        # Build recommendation
        recommendation = self._formulate_wellness_guidance(
            query, health_impact, sustainability_score, stress_factors, context
        )
        
        # Identify health concerns
        concerns = []
        if stress_factors.get('high_stress_risk', False):
            concerns.append("High stress potential - implement stress mitigation strategies")
        if health_impact.get('physical_strain', 0) > 0.6:
            concerns.append("Physical strain concerns - consider ergonomic improvements")
        if sustainability_score < 0.4:
            concerns.append("Unsustainable pace - risk of burnout")
        if health_impact.get('sleep_disruption', False):
            concerns.append("May disrupt healthy sleep patterns")
        
        # Identify wellness opportunities
        opportunities = []
        if wellness_opportunities.get('skill_building'):
            opportunities.append("Opportunity to develop healthy coping skills")
        if wellness_opportunities.get('team_bonding'):
            opportunities.append("Can strengthen team relationships and support")
        if sustainability_score > 0.7:
            opportunities.append("Sustainable approach that promotes long-term wellbeing")
        if wellness_opportunities.get('mindfulness_potential'):
            opportunities.append("Good opportunity for mindful practice")
        
        # Determine priority based on health impact
        priority = self._determine_wellness_priority(health_impact, stress_factors, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_wellness_thinking(
                health_impact, sustainability_score, stress_factors
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'health_impact_score': health_impact.get('overall_impact', 0.5),
                'sustainability_score': sustainability_score,
                'stress_level': stress_factors.get('stress_level', 'medium'),
                'physical_demands': health_impact.get('physical_strain', 0),
                'mental_load': health_impact.get('cognitive_load', 0.5)
            },
            tags={'health', 'wellness', 'sustainability', 'balance', 'self-care'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on wellness information availability
        """
        confidence = 0.7  # Start high for universal health principles
        
        # Increase confidence for health-related contexts
        if context.get('team_health_data'):
            confidence += 0.1
        
        # Increase if workload/stress information available
        if context.get('workload_info') or context.get('deadline_pressure'):
            confidence += 0.15
        
        # Increase if this involves wellness domains
        query_lower = query.lower()
        wellness_keywords = ['stress', 'workload', 'time', 'pressure', 'deadline', 'health', 'balance']
        if any(keyword in query_lower for keyword in wellness_keywords):
            confidence += 0.15
        
        return max(0.3, min(0.95, confidence))
    
    def _assess_health_impact(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess health and wellness impact"""
        impact = {
            'physical_strain': 0.3,
            'cognitive_load': 0.5,
            'emotional_impact': 0.4,
            'social_impact': 0.3,
            'overall_impact': 0.4,
            'recovery_time': 'normal'
        }
        
        # Analyze query for health implications
        query_lower = query.lower()
        
        if 'urgent' in query_lower or 'rush' in query_lower or 'emergency' in query_lower:
            impact['physical_strain'] = 0.7
            impact['cognitive_load'] = 0.8
            impact['emotional_impact'] = 0.7
            impact['recovery_time'] = 'extended'
        
        if 'complex' in query_lower or 'difficult' in query_lower:
            impact['cognitive_load'] = 0.8
            impact['emotional_impact'] = 0.6
        
        if 'team' in query_lower or 'collaboration' in query_lower:
            impact['social_impact'] = 0.6
        
        if 'late' in query_lower or 'overtime' in query_lower:
            impact['sleep_disruption'] = True
            impact['physical_strain'] = 0.7
        
        # Check context for workload indicators
        if context.get('deadline_pressure', 0) > 0.7:
            impact['emotional_impact'] = 0.8
            impact['cognitive_load'] = 0.7
        
        if context.get('requires_deep_focus', False):
            impact['cognitive_load'] = 0.7
        
        if context.get('long_duration', False):
            impact['physical_strain'] += 0.2
            impact['recovery_time'] = 'extended'
        
        # Calculate overall impact
        impact['overall_impact'] = (
            impact['physical_strain'] * 0.25 +
            impact['cognitive_load'] * 0.3 +
            impact['emotional_impact'] * 0.25 +
            impact['social_impact'] * 0.2
        )
        
        return impact
    
    def _evaluate_sustainability(self, context: Dict[str, Any]) -> float:
        """Evaluate long-term sustainability"""
        sustainability = 0.5  # Neutral default
        
        # Positive sustainability factors
        if context.get('reasonable_timeline', False):
            sustainability += 0.2
        if context.get('adequate_resources', False):
            sustainability += 0.2
        if context.get('promotes_learning', False):
            sustainability += 0.1
        if context.get('team_support', False):
            sustainability += 0.15
        
        # Negative sustainability factors  
        if context.get('deadline_pressure', 0) > 0.7:
            sustainability -= 0.3
        if context.get('resource_shortage', False):
            sustainability -= 0.2
        if context.get('requires_overtime', False):
            sustainability -= 0.25
        if context.get('high_stress_environment', False):
            sustainability -= 0.2
        
        return max(0.0, min(1.0, sustainability))
    
    def _identify_stress_factors(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify stress and pressure factors"""
        stress_factors = {
            'time_pressure': context.get('deadline_pressure', 0.3),
            'complexity_stress': 0.3,
            'uncertainty_stress': 0.3,
            'social_pressure': 0.2,
            'stress_level': 'medium',
            'high_stress_risk': False
        }
        
        # Analyze query for stress indicators
        query_lower = query.lower()
        stress_words = ['urgent', 'critical', 'emergency', 'asap', 'immediately']
        if any(word in query_lower for word in stress_words):
            stress_factors['time_pressure'] = 0.9
            stress_factors['stress_level'] = 'high'
            stress_factors['high_stress_risk'] = True
        
        if 'complex' in query_lower or 'difficult' in query_lower:
            stress_factors['complexity_stress'] = 0.7
        
        if 'unknown' in query_lower or 'unclear' in query_lower:
            stress_factors['uncertainty_stress'] = 0.6
        
        # Check context
        if context.get('high_visibility', False):
            stress_factors['social_pressure'] = 0.7
        
        if context.get('mission_critical', False):
            stress_factors['social_pressure'] = 0.8
            stress_factors['high_stress_risk'] = True
        
        # Calculate overall stress level
        avg_stress = (
            stress_factors['time_pressure'] + 
            stress_factors['complexity_stress'] + 
            stress_factors['uncertainty_stress'] + 
            stress_factors['social_pressure']
        ) / 4
        
        if avg_stress > 0.7:
            stress_factors['stress_level'] = 'high'
            stress_factors['high_stress_risk'] = True
        elif avg_stress < 0.4:
            stress_factors['stress_level'] = 'low'
        
        return stress_factors
    
    def _find_wellness_opportunities(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Find opportunities to enhance wellness"""
        return {
            'skill_building': context.get('learning_opportunity', False),
            'team_bonding': context.get('collaborative_work', False),
            'mindfulness_potential': context.get('allows_focused_work', False),
            'creativity_outlet': context.get('creative_aspects', False),
            'autonomy_increase': context.get('increases_independence', False),
            'accomplishment_potential': context.get('meaningful_outcome', False)
        }
    
    def _formulate_wellness_guidance(self, 
                                   query: str,
                                   health_impact: Dict[str, Any],
                                   sustainability: float,
                                   stress_factors: Dict[str, Any],
                                   context: Dict[str, Any]) -> str:
        """Formulate wellness-focused guidance"""
        
        query_lower = query.lower()
        
        # Specific health guidance for car seats
        if 'car seat' in query_lower or 'carseat' in query_lower or 'baby seat' in query_lower:
            if 'second hand' in query_lower or 'used' in query_lower:
                return ("Health perspective: New parent stress is real - prioritize peace of mind. "
                       "New car seats eliminate worry about hidden issues, provide clear instructions, "
                       "and reduce decision fatigue. The mental health benefit of knowing your child "
                       "has maximum protection can outweigh cost savings, supporting family wellbeing.")
            else:
                return ("Wellbeing focus: Choose based on ease of use to reduce daily stress. "
                       "Features like easy installation, washable covers, and clear indicators "
                       "support parent wellness by minimizing frustration and uncertainty.")
        
        # General wellness guidance
        if stress_factors['high_stress_risk'] and sustainability < 0.4:
            return (f"Health-first approach needed: Current stress level ({stress_factors['stress_level']}) "
                   f"and low sustainability ({sustainability:.0%}) require immediate wellbeing interventions")
        elif health_impact['overall_impact'] > 0.7:
            return (f"Implement with wellness safeguards: High health impact detected "
                   f"({health_impact['overall_impact']:.0%}). Plan for adequate recovery and support")
        elif sustainability > 0.7 and stress_factors['stress_level'] == 'low':
            return (f"Wellness-positive path: Good sustainability ({sustainability:.0%}) "
                   f"with manageable stress. Proceed with self-care practices")
        else:
            return (f"Balanced approach with wellness monitoring: Moderate health impact "
                   f"requires ongoing attention to stress and recovery")
    
    def _explain_wellness_thinking(self,
                                 health_impact: Dict[str, Any],
                                 sustainability: float,
                                 stress_factors: Dict[str, Any]) -> str:
        """Explain the wellness reasoning"""
        
        reasoning = f"From a wellness perspective, this involves {stress_factors['stress_level']} stress levels. "
        
        if health_impact['overall_impact'] > 0.6:
            reasoning += f"Health impact is significant ({health_impact['overall_impact']:.0%}), requiring careful attention. "
        
        if sustainability < 0.5:
            reasoning += f"Sustainability is concerning ({sustainability:.0%}) - risk of burnout if not managed properly. "
        else:
            reasoning += f"Sustainability looks good ({sustainability:.0%}) for long-term wellbeing. "
        
        if health_impact.get('recovery_time') == 'extended':
            reasoning += "Extended recovery time will be needed after completion. "
        
        if stress_factors['high_stress_risk']:
            reasoning += "High stress risk requires proactive stress management strategies. "
        
        reasoning += "Prioritize sustainable pace, adequate support, and regular wellness check-ins."
        
        return reasoning
    
    def _determine_wellness_priority(self, 
                                   health_impact: Dict[str, Any],
                                   stress_factors: Dict[str, Any],
                                   context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from wellness perspective"""
        
        # Critical if severe health risks
        if stress_factors['high_stress_risk'] and health_impact['overall_impact'] > 0.8:
            return PersonaPriority.CRITICAL
        if context.get('burnout_risk', False):
            return PersonaPriority.CRITICAL
        
        # High if significant health impact or wellness opportunity
        if health_impact['overall_impact'] > 0.7:
            return PersonaPriority.HIGH
        if stress_factors['high_stress_risk']:
            return PersonaPriority.HIGH
        
        # Low if minimal health implications
        if health_impact['overall_impact'] < 0.3 and stress_factors['stress_level'] == 'low':
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in caring, supportive style"""
        return f"With care for your wellbeing: {content} Remember, sustainable health practices are essential for long-term success."