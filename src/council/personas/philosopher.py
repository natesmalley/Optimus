"""
The Philosopher - Ethics, Meaning, and Purpose

Focuses on ethical implications, moral considerations, meaning-making, and 
philosophical underpinnings of decisions. Asks the deeper "why" questions.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class PhilosopherPersona(Persona):
    """
    The Philosopher examines ethical dimensions and deeper meaning
    
    Key traits:
    - Ethical reasoning
    - Value alignment
    - Meaning exploration
    - Moral considerations
    - Purpose clarification
    """
    
    def __init__(self):
        super().__init__(
            persona_id="philosopher",
            name="The Philosopher",
            description="Ethics and meaning expert focused on moral implications and purpose-driven decisions",
            expertise_domains=[
                "ethics",
                "moral philosophy",
                "value systems",
                "meaning making",
                "purpose alignment",
                "existential questions",
                "social responsibility", 
                "wisdom traditions",
                "human dignity",
                "moral reasoning"
            ],
            personality_traits=[
                "contemplative",
                "principled",
                "questioning",
                "wise",
                "value-driven"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from an ethical and philosophical perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Philosophical analysis framework
        ethical_dimensions = self._examine_ethical_dimensions(query, context)
        value_alignment = self._assess_value_alignment(context)
        meaning_significance = self._evaluate_meaning_significance(query, context)
        moral_imperatives = self._identify_moral_imperatives(context)
        
        # Build recommendation
        recommendation = self._formulate_philosophical_guidance(
            query, ethical_dimensions, value_alignment, meaning_significance
        )
        
        # Identify ethical concerns
        concerns = []
        if ethical_dimensions.get('harm_potential', 0) > 0.5:
            concerns.append("Potential for unintended harm to stakeholders")
        if value_alignment < 0.4:
            concerns.append("May conflict with core human values")
        if ethical_dimensions.get('autonomy_threat', False):
            concerns.append("Could undermine human autonomy or dignity")
        if moral_imperatives.get('justice_issues'):
            concerns.append("May create or perpetuate injustice")
        
        # Identify philosophical opportunities
        opportunities = []
        if meaning_significance > 0.7:
            opportunities.append("Significant potential for meaningful impact")
        if ethical_dimensions.get('virtue_enhancement', False):
            opportunities.append("Opportunity to cultivate positive virtues")
        if value_alignment > 0.8:
            opportunities.append("Strong alignment with human flourishing")
        if moral_imperatives.get('beneficence_potential'):
            opportunities.append("Potential to actively promote wellbeing")
        
        # Determine priority based on ethical importance
        priority = self._determine_moral_priority(ethical_dimensions, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_philosophical_thinking(
                ethical_dimensions, value_alignment, meaning_significance
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'value_alignment_score': value_alignment,
                'meaning_significance': meaning_significance,
                'ethical_complexity': ethical_dimensions.get('complexity', 'medium'),
                'moral_weight': ethical_dimensions.get('moral_weight', 0.5),
                'stakeholder_impact': ethical_dimensions.get('stakeholder_count', 0)
            },
            tags={'ethics', 'philosophy', 'values', 'meaning', 'morality'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on philosophical clarity
        """
        confidence = 0.6  # Base confidence for value-based reasoning
        
        # Increase confidence for clear ethical dimensions
        if context.get('stakeholders_identified'):
            confidence += 0.15
        
        # Increase if values are explicitly stated
        if context.get('stated_values') or context.get('ethical_framework'):
            confidence += 0.15
        
        # Increase if this involves philosophical domains
        query_lower = query.lower()
        philosophical_keywords = ['ethics', 'moral', 'values', 'purpose', 'meaning', 'right', 'should']
        if any(keyword in query_lower for keyword in philosophical_keywords):
            confidence += 0.2
        
        # Decrease if ethical complexity is very high
        if context.get('ethical_dilemma', False):
            confidence -= 0.1
        
        return max(0.2, min(0.9, confidence))
    
    def _examine_ethical_dimensions(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Examine ethical dimensions of the decision"""
        dimensions = {
            'harm_potential': 0.2,  # Potential for harm
            'benefit_potential': 0.5,  # Potential for benefit
            'autonomy_impact': 0.5,  # Impact on autonomy
            'justice_considerations': 0.5,  # Fairness implications
            'complexity': 'medium',
            'moral_weight': 0.5,
            'stakeholder_count': 1
        }
        
        # Analyze query for ethical implications
        query_lower = query.lower()
        
        if 'privacy' in query_lower or 'surveillance' in query_lower:
            dimensions['autonomy_impact'] = 0.8
            dimensions['complexity'] = 'high'
            dimensions['moral_weight'] = 0.8
        
        if 'ai' in query_lower or 'artificial intelligence' in query_lower:
            dimensions['complexity'] = 'high'
            dimensions['autonomy_impact'] = 0.7
            dimensions['moral_weight'] = 0.9
        
        if 'delete' in query_lower or 'remove' in query_lower:
            dimensions['harm_potential'] = 0.6
        
        if 'share' in query_lower or 'public' in query_lower:
            dimensions['stakeholder_count'] = 5
            dimensions['justice_considerations'] = 0.7
        
        # Check context for stakeholder information
        if context.get('affects_users', False):
            dimensions['stakeholder_count'] += 3
            dimensions['moral_weight'] += 0.2
        
        if context.get('involves_personal_data', False):
            dimensions['autonomy_impact'] = max(dimensions['autonomy_impact'], 0.8)
            dimensions['complexity'] = 'high'
        
        return dimensions
    
    def _assess_value_alignment(self, context: Dict[str, Any]) -> float:
        """Assess alignment with fundamental human values"""
        alignment = 0.5  # Neutral default
        
        # Core values: autonomy, beneficence, justice, dignity
        if context.get('promotes_autonomy', False):
            alignment += 0.2
        if context.get('promotes_wellbeing', False):
            alignment += 0.2
        if context.get('promotes_fairness', False):
            alignment += 0.2
        if context.get('respects_dignity', True):  # Default to true unless specified
            alignment += 0.1
        
        # Negative indicators
        if context.get('reduces_autonomy', False):
            alignment -= 0.3
        if context.get('causes_harm', False):
            alignment -= 0.4
        if context.get('creates_inequality', False):
            alignment -= 0.2
        
        return max(0.0, min(1.0, alignment))
    
    def _evaluate_meaning_significance(self, query: str, context: Dict[str, Any]) -> float:
        """Evaluate how meaningful this decision is"""
        significance = 0.3  # Base level
        
        # Check for impact scale
        user_count = context.get('user_count', 0)
        if user_count > 1000:
            significance += 0.3
        elif user_count > 100:
            significance += 0.2
        elif user_count > 10:
            significance += 0.1
        
        # Check for personal growth/development
        if context.get('promotes_growth', False):
            significance += 0.2
        
        # Check for solving meaningful problems
        if context.get('addresses_real_need', False):
            significance += 0.2
        
        # Check for creative/expressive elements
        query_lower = query.lower()
        if any(word in query_lower for word in ['create', 'express', 'art', 'beauty']):
            significance += 0.2
        
        return min(1.0, significance)
    
    def _identify_moral_imperatives(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify moral imperatives (duties, obligations)"""
        return {
            'do_no_harm': context.get('harm_risk', 0) > 0.5,
            'promote_good': context.get('benefit_potential', 0) > 0.6,
            'respect_autonomy': context.get('affects_user_choice', False),
            'ensure_justice': context.get('fairness_implications', False),
            'maintain_integrity': context.get('involves_trust', False),
            'justice_issues': context.get('creates_inequality', False),
            'beneficence_potential': context.get('benefit_potential', 0) > 0.7
        }
    
    def _formulate_philosophical_guidance(self, 
                                        query: str,
                                        dimensions: Dict[str, Any],
                                        alignment: float,
                                        significance: float) -> str:
        """Formulate philosophical guidance"""
        
        if alignment > 0.8 and significance > 0.7:
            return (f"Ethically commendable path - strong value alignment "
                   f"({alignment:.0%}) with meaningful significance. This serves human flourishing.")
        elif alignment > 0.6 and dimensions['harm_potential'] < 0.3:
            return (f"Morally sound approach with good value alignment ({alignment:.0%}). "
                   f"Proceed with attention to stakeholder wellbeing.")
        elif alignment < 0.4 or dimensions['harm_potential'] > 0.6:
            return (f"Ethical concerns warrant careful consideration. Value alignment "
                   f"is {alignment:.0%}. Consider alternative approaches that better honor human dignity.")
        else:
            return (f"Morally neutral decision requiring ethical safeguards. "
                   f"Implement with clear principles and ongoing reflection.")
    
    def _explain_philosophical_thinking(self,
                                      dimensions: Dict[str, Any],
                                      alignment: float,
                                      significance: float) -> str:
        """Explain the philosophical reasoning"""
        
        reasoning = f"From an ethical standpoint, this decision carries {dimensions['complexity']} moral complexity. "
        
        if alignment > 0.6:
            reasoning += f"It aligns well with core human values ({alignment:.0%}). "
        else:
            reasoning += f"Value alignment is concerning ({alignment:.0%}), requiring careful consideration. "
        
        if significance > 0.6:
            reasoning += f"The decision has significant meaning for those affected. "
        
        if dimensions['harm_potential'] > 0.5:
            reasoning += "There's notable potential for harm that must be carefully mitigated. "
        
        if dimensions['stakeholder_count'] > 3:
            reasoning += "Multiple stakeholders are impacted, requiring inclusive consideration. "
        
        reasoning += "The path forward should honor human dignity, promote flourishing, and uphold justice."
        
        return reasoning
    
    def _determine_moral_priority(self, 
                                dimensions: Dict[str, Any],
                                context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from moral perspective"""
        
        # Critical if high harm potential or major ethical violation
        if dimensions['harm_potential'] > 0.7:
            return PersonaPriority.CRITICAL
        if context.get('violates_core_values', False):
            return PersonaPriority.CRITICAL
        
        # High if affects many people or has strong moral weight
        if dimensions['stakeholder_count'] > 5 or dimensions['moral_weight'] > 0.8:
            return PersonaPriority.HIGH
        
        # Low if minimal ethical implications
        if dimensions['moral_weight'] < 0.3 and dimensions['stakeholder_count'] < 2:
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in contemplative philosophical style"""
        return f"Upon reflection: {content} Let us consider the deeper implications and ensure our path honors wisdom."