"""
The Explorer - Adventure, Experiences, and Personal Growth

Focuses on new experiences, adventure, personal growth opportunities,
and stepping outside comfort zones. Embraces uncertainty and discovery.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class ExplorerPersona(Persona):
    """
    The Explorer seeks adventure, growth, and new experiences
    
    Key traits:
    - Adventure seeking
    - Growth mindset
    - Comfort zone expansion
    - Discovery orientation
    - Experience valuation
    """
    
    def __init__(self):
        super().__init__(
            persona_id="explorer",
            name="The Explorer",
            description="Adventure and personal growth expert focused on new experiences and comfort zone expansion",
            expertise_domains=[
                "personal growth",
                "adventure planning",
                "experience design",
                "comfort zone expansion",
                "discovery",
                "resilience building",
                "adaptability",
                "risk taking",
                "exploration",
                "growth mindset",
                "life experiences",
                "personal development"
            ],
            personality_traits=[
                "adventurous",
                "curious",
                "bold",
                "resilient",
                "growth-minded"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from an adventure and growth perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Exploration analysis framework
        growth_potential = self._assess_growth_potential(query, context)
        adventure_value = self._evaluate_adventure_value(query, context)
        comfort_zone_expansion = self._measure_comfort_zone_expansion(context)
        experience_richness = self._assess_experience_richness(context)
        
        # Build recommendation
        recommendation = self._formulate_exploration_guidance(
            query, growth_potential, adventure_value, comfort_zone_expansion
        )
        
        # Identify exploration concerns
        concerns = []
        if growth_potential.get('overwhelm_risk', 0) > 0.6:
            concerns.append("Risk of overwhelm from too much change too quickly")
        if adventure_value.get('safety_concerns', False):
            concerns.append("Safety considerations require careful planning")
        if comfort_zone_expansion.get('stretch_too_far', False):
            concerns.append("May stretch beyond productive comfort zone expansion")
        if experience_richness.get('shallow_experience_risk', False):
            concerns.append("Risk of superficial rather than meaningful experience")
        
        # Identify exploration opportunities
        opportunities = []
        if growth_potential.get('breakthrough_growth', False):
            opportunities.append("Potential for breakthrough personal growth")
        if adventure_value.get('memorable_experience', False):
            opportunities.append("Opportunity for memorable, life-enriching experience")
        if comfort_zone_expansion.get('resilience_building', False):
            opportunities.append("Can build resilience and adaptability")
        if experience_richness.get('unique_perspective', False):
            opportunities.append("Will provide unique perspectives and insights")
        
        # Determine priority based on growth impact
        priority = self._determine_exploration_priority(growth_potential, adventure_value, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_exploration_thinking(
                growth_potential, adventure_value, comfort_zone_expansion, experience_richness
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'growth_potential_score': growth_potential.get('overall_growth', 0.5),
                'adventure_level': adventure_value.get('adventure_level', 'moderate'),
                'comfort_stretch': comfort_zone_expansion.get('stretch_level', 0.5),
                'experience_depth': experience_richness.get('depth_score', 0.5),
                'learning_adventure': growth_potential.get('learning_component', 0.5)
            },
            tags={'growth', 'adventure', 'exploration', 'experience', 'development'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on exploration domain relevance
        """
        confidence = 0.6  # Good base confidence for growth aspects
        
        # Increase confidence for growth/adventure contexts
        if context.get('personal_growth') or context.get('new_experience'):
            confidence += 0.2
        
        # Increase if challenge/adventure elements present
        if context.get('challenging') or context.get('unfamiliar'):
            confidence += 0.15
        
        # Increase if this involves exploration domains
        query_lower = query.lower()
        exploration_keywords = ['new', 'explore', 'try', 'adventure', 'challenge', 'grow', 'experience']
        if any(keyword in query_lower for keyword in exploration_keywords):
            confidence += 0.15
        
        return max(0.3, min(0.9, confidence))
    
    def _assess_growth_potential(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess personal growth and development potential"""
        potential = {
            'overall_growth': 0.5,
            'skill_expansion': 0.4,
            'mindset_shift': 0.3,
            'confidence_building': 0.4,
            'learning_component': 0.5,
            'growth_type': 'moderate'  # minimal, moderate, significant, transformative
        }
        
        # Analyze query for growth implications
        query_lower = query.lower()
        
        if 'new' in query_lower or 'first time' in query_lower:
            potential['overall_growth'] = 0.8
            potential['confidence_building'] = 0.7
            potential['growth_type'] = 'significant'
        
        if 'challenging' in query_lower or 'difficult' in query_lower:
            potential['skill_expansion'] = 0.8
            potential['confidence_building'] = 0.9
            potential['growth_type'] = 'significant'
        
        if 'learn' in query_lower or 'understand' in query_lower:
            potential['learning_component'] = 0.8
            potential['skill_expansion'] = 0.7
        
        if 'change' in query_lower or 'different' in query_lower:
            potential['mindset_shift'] = 0.7
            potential['overall_growth'] = 0.7
        
        # Check context for growth factors
        if context.get('requires_new_skills', False):
            potential['skill_expansion'] = 0.9
            potential['learning_component'] = 0.8
        
        if context.get('unfamiliar_territory', False):
            potential['overall_growth'] = 0.8
            potential['confidence_building'] = 0.7
            potential['growth_type'] = 'significant'
        
        if context.get('paradigm_shift', False):
            potential['mindset_shift'] = 0.9
            potential['growth_type'] = 'transformative'
            potential['breakthrough_growth'] = True
        
        if context.get('too_much_too_fast', False):
            potential['overwhelm_risk'] = 0.8
        
        if context.get('life_changing_potential', False):
            potential['growth_type'] = 'transformative'
            potential['breakthrough_growth'] = True
        
        return potential
    
    def _evaluate_adventure_value(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate adventure and excitement value"""
        value = {
            'adventure_level': 'moderate',  # low, moderate, high, extreme
            'novelty_score': 0.5,
            'excitement_factor': 0.5,
            'story_value': 0.4,
            'uniqueness': 0.4
        }
        
        # Analyze query for adventure implications
        query_lower = query.lower()
        
        if 'adventure' in query_lower or 'exciting' in query_lower:
            value['adventure_level'] = 'high'
            value['excitement_factor'] = 0.8
            value['story_value'] = 0.7
        
        if 'unique' in query_lower or 'unusual' in query_lower:
            value['novelty_score'] = 0.8
            value['uniqueness'] = 0.8
            value['story_value'] = 0.7
        
        if 'extreme' in query_lower or 'intense' in query_lower:
            value['adventure_level'] = 'extreme'
            value['excitement_factor'] = 0.9
            value['safety_concerns'] = True
        
        # Check context for adventure factors
        if context.get('once_in_lifetime', False):
            value['uniqueness'] = 0.9
            value['story_value'] = 0.9
            value['memorable_experience'] = True
        
        if context.get('off_beaten_path', False):
            value['novelty_score'] = 0.8
            value['adventure_level'] = 'high'
        
        if context.get('safe_exploration', False):
            value['adventure_level'] = 'moderate'
            value['safety_concerns'] = False
        
        if context.get('high_risk', False):
            value['adventure_level'] = 'extreme'
            value['safety_concerns'] = True
        
        if context.get('shareable_experience', False):
            value['story_value'] = 0.8
        
        return value
    
    def _measure_comfort_zone_expansion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Measure how much this expands comfort zone"""
        expansion = {
            'stretch_level': 0.5,  # 0-1 scale
            'comfort_zone_type': 'mixed',  # social, technical, physical, emotional, mixed
            'expansion_pace': 'gradual',  # gentle, gradual, significant, dramatic
            'support_available': 0.5
        }
        
        # Check context for comfort zone factors
        if context.get('social_challenge', False):
            expansion['comfort_zone_type'] = 'social'
            expansion['stretch_level'] += 0.3
        
        if context.get('technical_challenge', False):
            expansion['comfort_zone_type'] = 'technical'
            expansion['stretch_level'] += 0.2
        
        if context.get('physical_challenge', False):
            expansion['comfort_zone_type'] = 'physical'
            expansion['stretch_level'] += 0.4
        
        if context.get('emotional_challenge', False):
            expansion['comfort_zone_type'] = 'emotional'
            expansion['stretch_level'] += 0.5
        
        # Determine expansion pace
        if expansion['stretch_level'] > 0.8:
            expansion['expansion_pace'] = 'dramatic'
            expansion['stretch_too_far'] = True
        elif expansion['stretch_level'] > 0.6:
            expansion['expansion_pace'] = 'significant'
        elif expansion['stretch_level'] < 0.3:
            expansion['expansion_pace'] = 'gentle'
        
        # Check for support systems
        if context.get('mentorship_available', False):
            expansion['support_available'] = 0.8
        if context.get('team_support', False):
            expansion['support_available'] += 0.2
        if context.get('isolated_challenge', False):
            expansion['support_available'] = 0.2
        
        # Determine if good stretch
        if 0.4 <= expansion['stretch_level'] <= 0.7 and expansion['support_available'] > 0.5:
            expansion['optimal_stretch'] = True
        
        if expansion['stretch_level'] > 0.6:
            expansion['resilience_building'] = True
        
        return expansion
    
    def _assess_experience_richness(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess richness and depth of experience"""
        richness = {
            'depth_score': 0.5,
            'breadth_score': 0.4,
            'sensory_richness': 0.4,
            'emotional_impact': 0.4,
            'memory_formation': 0.5
        }
        
        # Check context for experience richness factors
        if context.get('multi_sensory', False):
            richness['sensory_richness'] = 0.8
            richness['memory_formation'] = 0.7
        
        if context.get('emotionally_engaging', False):
            richness['emotional_impact'] = 0.8
            richness['memory_formation'] = 0.8
        
        if context.get('deep_immersion', False):
            richness['depth_score'] = 0.9
            richness['memory_formation'] = 0.8
        
        if context.get('varied_activities', False):
            richness['breadth_score'] = 0.8
        
        if context.get('meaningful_connections', False):
            richness['emotional_impact'] = 0.7
            richness['depth_score'] = 0.7
        
        if context.get('rushed_experience', False):
            richness['depth_score'] = 0.2
            richness['shallow_experience_risk'] = True
        
        if context.get('unique_perspective_gained', False):
            richness['unique_perspective'] = True
            richness['depth_score'] = 0.8
        
        return richness
    
    def _formulate_exploration_guidance(self, 
                                      query: str,
                                      growth_potential: Dict[str, Any],
                                      adventure_value: Dict[str, Any],
                                      comfort_zone_expansion: Dict[str, Any]) -> str:
        """Formulate exploration-focused guidance"""
        
        growth_score = growth_potential['overall_growth']
        adventure_level = adventure_value['adventure_level']
        stretch_level = comfort_zone_expansion['stretch_level']
        
        if growth_potential.get('breakthrough_growth', False) and comfort_zone_expansion.get('optimal_stretch', False):
            return (f"Embrace this transformative adventure: Breakthrough growth potential "
                   f"with optimal comfort zone expansion - this could be life-changing")
        elif adventure_value.get('memorable_experience', False) and growth_score > 0.7:
            return (f"Seize this adventure: {adventure_level} adventure level with "
                   f"excellent growth potential ({growth_score:.0%}) - create lasting memories")
        elif comfort_zone_expansion.get('stretch_too_far', False):
            return (f"Approach with caution: High stretch level may exceed comfortable growth - "
                   f"consider building up gradually or ensuring strong support systems")
        else:
            return (f"Pursue with adventurous spirit: {adventure_level} adventure with "
                   f"{growth_potential['growth_type']} growth potential - step boldly forward")
    
    def _explain_exploration_thinking(self,
                                    growth_potential: Dict[str, Any],
                                    adventure_value: Dict[str, Any],
                                    comfort_zone_expansion: Dict[str, Any],
                                    experience_richness: Dict[str, Any]) -> str:
        """Explain the exploration-focused reasoning"""
        
        reasoning = f"From an exploration perspective, this offers {growth_potential['growth_type']} growth potential. "
        
        if adventure_value['adventure_level'] in ['high', 'extreme']:
            reasoning += f"The {adventure_value['adventure_level']} adventure level promises excitement and novelty. "
        
        if comfort_zone_expansion['stretch_level'] > 0.6:
            reasoning += f"Significant comfort zone expansion ({comfort_zone_expansion['stretch_level']:.0%}) "
            reasoning += f"at a {comfort_zone_expansion['expansion_pace']} pace. "
        
        if experience_richness['depth_score'] > 0.6:
            reasoning += f"Rich, deep experience expected ({experience_richness['depth_score']:.0%}). "
        
        if growth_potential.get('breakthrough_growth', False):
            reasoning += "Potential for breakthrough personal transformation. "
        
        if adventure_value.get('safety_concerns', False):
            reasoning += "Safety considerations require careful planning and preparation. "
        
        if comfort_zone_expansion.get('support_available', 0) > 0.6:
            reasoning += "Good support systems available to aid the journey. "
        
        reasoning += "Growth happens outside our comfort zone - embrace the adventure."
        
        return reasoning
    
    def _determine_exploration_priority(self, 
                                      growth_potential: Dict[str, Any],
                                      adventure_value: Dict[str, Any],
                                      context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from exploration perspective"""
        
        # Critical if once-in-lifetime opportunity or breakthrough growth
        if context.get('once_in_lifetime', False):
            return PersonaPriority.CRITICAL
        if growth_potential.get('breakthrough_growth', False):
            return PersonaPriority.CRITICAL
        
        # High if significant growth or unique adventure
        if growth_potential['overall_growth'] > 0.8:
            return PersonaPriority.HIGH
        if adventure_value.get('memorable_experience', False):
            return PersonaPriority.HIGH
        
        # Low if minimal growth or adventure value
        if (growth_potential['overall_growth'] < 0.3 and 
            adventure_value['adventure_level'] == 'low'):
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in adventurous, inspiring style"""
        return f"With an explorer's spirit: {content} Life's greatest treasures await beyond our comfort zone."