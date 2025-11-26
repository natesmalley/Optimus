"""
The Creator - Artistic Expression and Innovation

Focuses on creativity, artistic expression, aesthetic considerations, and 
innovative approaches. Brings beauty, inspiration, and creative thinking to solutions.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class CreatorPersona(Persona):
    """
    The Creator emphasizes creativity, aesthetics, and innovative expression
    
    Key traits:
    - Creative thinking
    - Aesthetic awareness
    - Innovation focus
    - Artistic expression
    - Inspirational approach
    """
    
    def __init__(self):
        super().__init__(
            persona_id="creator",
            name="The Creator",
            description="Creativity and artistic expression expert focused on innovative solutions and aesthetic excellence",
            expertise_domains=[
                "creative thinking",
                "artistic expression",
                "aesthetic design",
                "innovation",
                "visual appeal",
                "user experience",
                "creative problem solving",
                "inspiration",
                "beauty",
                "originality",
                "artistic vision",
                "creative process"
            ],
            personality_traits=[
                "imaginative",
                "artistic",
                "innovative",
                "expressive",
                "inspirational"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from a creative and artistic perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Creative analysis framework
        creative_potential = self._assess_creative_potential(query, context)
        aesthetic_considerations = self._evaluate_aesthetic_aspects(context)
        innovation_opportunities = self._identify_innovation_opportunities(query, context)
        inspiration_factor = self._measure_inspiration_factor(context)
        
        # Build recommendation
        recommendation = self._formulate_creative_guidance(
            query, creative_potential, aesthetic_considerations, innovation_opportunities
        )
        
        # Identify creative concerns
        concerns = []
        if aesthetic_considerations.get('aesthetic_conflict', False):
            concerns.append("Potential aesthetic conflicts with existing design principles")
        if creative_potential.get('creativity_constraints', 0) > 0.6:
            concerns.append("Significant constraints may limit creative expression")
        if innovation_opportunities.get('innovation_risk', 0) > 0.7:
            concerns.append("High innovation risk - may be too avant-garde for context")
        if aesthetic_considerations.get('user_confusion_risk', False):
            concerns.append("Creative approach might confuse or alienate users")
        
        # Identify creative opportunities
        opportunities = []
        if creative_potential.get('high_creative_potential', False):
            opportunities.append("Exceptional opportunity for creative breakthrough")
        if innovation_opportunities.get('trendsetting_potential', False):
            opportunities.append("Potential to set new trends and inspire others")
        if aesthetic_considerations.get('aesthetic_enhancement', 0) > 0.7:
            opportunities.append("Significant aesthetic improvement possible")
        if inspiration_factor > 0.7:
            opportunities.append("High potential to inspire and motivate team/users")
        
        # Determine priority based on creative impact
        priority = self._determine_creative_priority(creative_potential, aesthetic_considerations, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_creative_thinking(
                creative_potential, aesthetic_considerations, innovation_opportunities, inspiration_factor
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'creative_potential_score': creative_potential.get('overall_potential', 0.5),
                'aesthetic_impact': aesthetic_considerations.get('aesthetic_impact', 0.5),
                'innovation_level': innovation_opportunities.get('innovation_level', 'moderate'),
                'inspiration_factor': inspiration_factor,
                'artistic_complexity': creative_potential.get('complexity', 'medium')
            },
            tags={'creativity', 'art', 'aesthetics', 'innovation', 'inspiration'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on creative domain relevance
        """
        confidence = 0.6  # Good base confidence for creative insights
        
        # Increase confidence for creative contexts
        if context.get('design_involved') or context.get('user_interface'):
            confidence += 0.2
        
        # Increase if artistic elements present
        if context.get('visual_elements') or context.get('user_experience'):
            confidence += 0.15
        
        # Increase if this involves creative domains
        query_lower = query.lower()
        creative_keywords = ['design', 'create', 'art', 'beauty', 'visual', 'aesthetic', 'innovative', 'inspire']
        if any(keyword in query_lower for keyword in creative_keywords):
            confidence += 0.2
        
        # Decrease if purely technical with no creative elements
        if context.get('purely_technical', False) and not context.get('user_facing', False):
            confidence -= 0.15
        
        return max(0.3, min(0.9, confidence))
    
    def _assess_creative_potential(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess creative potential and opportunities"""
        potential = {
            'overall_potential': 0.5,
            'originality_opportunity': 0.4,
            'creative_freedom': 0.5,
            'creativity_constraints': 0.4,
            'complexity': 'medium',
            'artistic_elements': 0.3
        }
        
        # Analyze query for creative implications
        query_lower = query.lower()
        
        if 'new' in query_lower or 'create' in query_lower or 'design' in query_lower:
            potential['overall_potential'] = 0.8
            potential['originality_opportunity'] = 0.8
            potential['creative_freedom'] = 0.7
        
        if 'innovative' in query_lower or 'unique' in query_lower:
            potential['originality_opportunity'] = 0.9
            potential['complexity'] = 'high'
        
        if 'improve' in query_lower or 'enhance' in query_lower:
            potential['overall_potential'] = 0.6
            potential['artistic_elements'] = 0.6
        
        if 'standard' in query_lower or 'conventional' in query_lower:
            potential['originality_opportunity'] = 0.2
            potential['creative_freedom'] = 0.3
        
        # Check context for creative factors
        if context.get('user_facing', False):
            potential['artistic_elements'] = 0.7
            potential['overall_potential'] += 0.2
        
        if context.get('visual_component', False):
            potential['artistic_elements'] = 0.9
            potential['creative_freedom'] = 0.8
        
        if context.get('strict_requirements', False):
            potential['creativity_constraints'] = 0.8
            potential['creative_freedom'] = 0.3
        
        if context.get('open_ended', False):
            potential['creative_freedom'] = 0.9
            potential['overall_potential'] += 0.2
        
        if context.get('brand_guidelines', False):
            potential['creativity_constraints'] += 0.2
        
        # Determine high creative potential
        if (potential['overall_potential'] > 0.7 and 
            potential['creative_freedom'] > 0.6 and 
            potential['creativity_constraints'] < 0.5):
            potential['high_creative_potential'] = True
        
        return potential
    
    def _evaluate_aesthetic_aspects(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate aesthetic considerations and visual impact"""
        aesthetics = {
            'aesthetic_impact': 0.4,
            'visual_importance': 0.3,
            'beauty_factor': 0.3,
            'harmony_considerations': 0.5,
            'aesthetic_consistency': 0.6
        }
        
        # Check context for aesthetic factors
        if context.get('user_interface', False):
            aesthetics['aesthetic_impact'] = 0.9
            aesthetics['visual_importance'] = 0.9
            aesthetics['beauty_factor'] = 0.7
        
        if context.get('public_facing', False):
            aesthetics['aesthetic_impact'] = 0.8
            aesthetics['beauty_factor'] = 0.6
        
        if context.get('brand_representation', False):
            aesthetics['aesthetic_consistency'] = 0.9
            aesthetics['harmony_considerations'] = 0.8
        
        if context.get('artistic_project', False):
            aesthetics['beauty_factor'] = 0.9
            aesthetics['aesthetic_impact'] = 0.9
        
        if context.get('functional_only', False):
            aesthetics['aesthetic_impact'] = 0.2
            aesthetics['beauty_factor'] = 0.1
        
        # Check for potential aesthetic conflicts
        if context.get('conflicting_styles', False):
            aesthetics['aesthetic_conflict'] = True
            aesthetics['harmony_considerations'] = 0.3
        
        # Check for user confusion risk
        if context.get('complex_interface', False) and aesthetics['aesthetic_impact'] > 0.8:
            aesthetics['user_confusion_risk'] = True
        
        # Calculate aesthetic enhancement potential
        if aesthetics['aesthetic_impact'] > 0.6 and aesthetics['beauty_factor'] > 0.5:
            aesthetics['aesthetic_enhancement'] = max(aesthetics['aesthetic_impact'], aesthetics['beauty_factor'])
        
        return aesthetics
    
    def _identify_innovation_opportunities(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify innovation and trendsetting opportunities"""
        innovation = {
            'innovation_level': 'moderate',
            'breakthrough_potential': 0.3,
            'trendsetting_potential': False,
            'innovation_risk': 0.4,
            'market_readiness': 0.6
        }
        
        # Analyze query for innovation indicators
        query_lower = query.lower()
        
        if 'revolutionary' in query_lower or 'breakthrough' in query_lower:
            innovation['innovation_level'] = 'high'
            innovation['breakthrough_potential'] = 0.9
            innovation['innovation_risk'] = 0.8
            innovation['trendsetting_potential'] = True
        
        if 'innovative' in query_lower or 'cutting-edge' in query_lower:
            innovation['innovation_level'] = 'high'
            innovation['breakthrough_potential'] = 0.7
            innovation['innovation_risk'] = 0.6
        
        if 'experimental' in query_lower or 'prototype' in query_lower:
            innovation['innovation_risk'] = 0.7
            innovation['market_readiness'] = 0.3
        
        # Check context for innovation factors
        if context.get('emerging_technology', False):
            innovation['innovation_level'] = 'high'
            innovation['breakthrough_potential'] = 0.8
            innovation['trendsetting_potential'] = True
        
        if context.get('first_of_kind', False):
            innovation['trendsetting_potential'] = True
            innovation['innovation_risk'] = 0.8
        
        if context.get('conservative_audience', False):
            innovation['innovation_risk'] += 0.3
            innovation['market_readiness'] = 0.4
        
        if context.get('early_adopters', False):
            innovation['market_readiness'] = 0.8
            innovation['innovation_risk'] -= 0.2
        
        return innovation
    
    def _measure_inspiration_factor(self, context: Dict[str, Any]) -> float:
        """Measure potential to inspire and motivate"""
        inspiration = 0.3  # Base level
        
        # Positive inspiration factors
        if context.get('meaningful_purpose', False):
            inspiration += 0.3
        if context.get('helps_people', False):
            inspiration += 0.2
        if context.get('artistic_expression', False):
            inspiration += 0.3
        if context.get('creative_breakthrough', False):
            inspiration += 0.4
        if context.get('beautiful_outcome', False):
            inspiration += 0.2
        
        # Context factors
        if context.get('visible_impact', False):
            inspiration += 0.1
        if context.get('team_pride_potential', False):
            inspiration += 0.1
        
        return min(1.0, inspiration)
    
    def _formulate_creative_guidance(self, 
                                   query: str,
                                   creative_potential: Dict[str, Any],
                                   aesthetics: Dict[str, Any],
                                   innovation: Dict[str, Any]) -> str:
        """Formulate creatively-inspired guidance"""
        
        if creative_potential.get('high_creative_potential', False) and aesthetics['aesthetic_impact'] > 0.7:
            return (f"Embrace creative excellence: Exceptional creative potential "
                   f"({creative_potential['overall_potential']:.0%}) with strong aesthetic impact - "
                   f"pursue artistic vision boldly")
        elif innovation['trendsetting_potential'] and innovation['innovation_risk'] < 0.6:
            return (f"Pioneer creative innovation: Trendsetting opportunity with manageable "
                   f"risk - lead with creative courage and artistic integrity")
        elif aesthetics['aesthetic_impact'] > 0.6 and creative_potential['creative_freedom'] > 0.6:
            return (f"Cultivate aesthetic beauty: Good creative freedom ({creative_potential['creative_freedom']:.0%}) "
                   f"with aesthetic importance - focus on harmonious, beautiful design")
        else:
            return (f"Apply creative thinking: Moderate creative potential with "
                   f"{innovation['innovation_level']} innovation level - balance creativity with practicality")
    
    def _explain_creative_thinking(self,
                                 creative_potential: Dict[str, Any],
                                 aesthetics: Dict[str, Any],
                                 innovation: Dict[str, Any],
                                 inspiration_factor: float) -> str:
        """Explain the creative reasoning"""
        
        reasoning = f"From a creative perspective, this has {creative_potential['overall_potential']:.0%} creative potential. "
        
        if aesthetics['aesthetic_impact'] > 0.6:
            reasoning += f"Aesthetic impact is significant ({aesthetics['aesthetic_impact']:.0%}), "
            reasoning += f"offering opportunities for beautiful, engaging solutions. "
        
        if innovation['innovation_level'] == 'high':
            reasoning += f"High innovation potential with {innovation['innovation_level']} breakthrough possibilities. "
        
        if creative_potential['creative_freedom'] > 0.6:
            reasoning += "Good creative freedom allows for artistic expression. "
        elif creative_potential['creativity_constraints'] > 0.6:
            reasoning += "Creative constraints require thoughtful, innovative solutions within boundaries. "
        
        if inspiration_factor > 0.6:
            reasoning += f"Strong inspiration factor ({inspiration_factor:.0%}) can motivate and uplift. "
        
        if innovation.get('trendsetting_potential', False):
            reasoning += "Potential to set new creative trends and inspire others. "
        
        reasoning += "Success lies in balancing artistic vision with practical implementation."
        
        return reasoning
    
    def _determine_creative_priority(self, 
                                   creative_potential: Dict[str, Any],
                                   aesthetics: Dict[str, Any],
                                   context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from creative perspective"""
        
        # Critical if creative excellence is essential to success
        if context.get('creative_critical', False):
            return PersonaPriority.CRITICAL
        if context.get('brand_defining', False) and aesthetics['aesthetic_impact'] > 0.8:
            return PersonaPriority.CRITICAL
        
        # High if significant creative opportunity or aesthetic importance
        if creative_potential.get('high_creative_potential', False):
            return PersonaPriority.HIGH
        if aesthetics['aesthetic_impact'] > 0.8:
            return PersonaPriority.HIGH
        
        # Low if minimal creative elements
        if (aesthetics['aesthetic_impact'] < 0.3 and 
            creative_potential['overall_potential'] < 0.3):
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in inspiring, artistic style"""
        return f"With creative vision: {content} Let beauty and innovation guide us to extraordinary solutions."