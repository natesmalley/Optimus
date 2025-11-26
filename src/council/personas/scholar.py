"""
The Scholar - Learning, Education, and Knowledge Acquisition

Focuses on learning opportunities, knowledge expansion, educational value,
and intellectual growth. Prioritizes understanding, research, and wisdom-building.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class ScholarPersona(Persona):
    """
    The Scholar emphasizes learning, knowledge, and intellectual development
    
    Key traits:
    - Learning focus
    - Knowledge seeking
    - Research orientation
    - Educational value
    - Intellectual curiosity
    """
    
    def __init__(self):
        super().__init__(
            persona_id="scholar",
            name="The Scholar",
            description="Learning and knowledge expert focused on educational value and intellectual development",
            expertise_domains=[
                "learning theory",
                "knowledge acquisition",
                "research methodology",
                "educational design",
                "skill development",
                "intellectual growth",
                "knowledge sharing",
                "study techniques",
                "information synthesis",
                "critical thinking",
                "wisdom building",
                "continuous learning"
            ],
            personality_traits=[
                "curious",
                "analytical",
                "studious",
                "methodical",
                "knowledge-seeking"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from a learning and knowledge perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Learning analysis framework
        learning_opportunities = self._identify_learning_opportunities(query, context)
        knowledge_value = self._assess_knowledge_value(context)
        skill_development = self._evaluate_skill_development(context)
        educational_impact = self._measure_educational_impact(context)
        
        # Build recommendation
        recommendation = self._formulate_learning_guidance(
            query, learning_opportunities, knowledge_value, skill_development
        )
        
        # Identify learning concerns
        concerns = []
        if learning_opportunities.get('learning_curve_steep', False):
            concerns.append("Steep learning curve may require significant time investment")
        if knowledge_value.get('knowledge_obsolescence_risk', 0) > 0.6:
            concerns.append("Knowledge gained may become obsolete quickly")
        if skill_development.get('skill_gap_too_large', False):
            concerns.append("Skill gap may be too large to bridge effectively")
        if educational_impact.get('knowledge_fragmentation_risk', False):
            concerns.append("May lead to fragmented understanding rather than deep learning")
        
        # Identify learning opportunities
        opportunities = []
        if learning_opportunities.get('breakthrough_learning', False):
            opportunities.append("Potential for breakthrough learning and understanding")
        if knowledge_value.get('transferable_knowledge', False):
            opportunities.append("Knowledge gained will be transferable to other domains")
        if skill_development.get('skill_building_potential', 0) > 0.7:
            opportunities.append("Excellent opportunity for skill development")
        if educational_impact.get('teaching_opportunity', False):
            opportunities.append("Can create opportunities to teach and share knowledge")
        
        # Determine priority based on learning impact
        priority = self._determine_learning_priority(learning_opportunities, knowledge_value, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_learning_thinking(
                learning_opportunities, knowledge_value, skill_development, educational_impact
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'learning_potential': learning_opportunities.get('learning_potential', 0.5),
                'knowledge_depth': knowledge_value.get('depth_score', 0.5),
                'skill_growth': skill_development.get('skill_growth_score', 0.5),
                'educational_value': educational_impact.get('educational_value', 0.5),
                'learning_efficiency': learning_opportunities.get('efficiency_score', 0.5)
            },
            tags={'learning', 'knowledge', 'education', 'skills', 'growth'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on learning domain relevance
        """
        confidence = 0.7  # Good base confidence for learning aspects
        
        # Increase confidence for educational contexts
        if context.get('learning_opportunity') or context.get('skill_development'):
            confidence += 0.15
        
        # Increase if knowledge/research elements present
        if context.get('research_component') or context.get('new_knowledge'):
            confidence += 0.1
        
        # Increase if this involves learning domains
        query_lower = query.lower()
        learning_keywords = ['learn', 'study', 'research', 'understand', 'knowledge', 'skill', 'education']
        if any(keyword in query_lower for keyword in learning_keywords):
            confidence += 0.15
        
        return max(0.4, min(0.95, confidence))
    
    def _identify_learning_opportunities(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify learning opportunities and challenges"""
        opportunities = {
            'learning_potential': 0.5,
            'learning_curve_difficulty': 'medium',
            'efficiency_score': 0.6,
            'breadth_vs_depth': 'balanced',
            'practical_application': 0.5
        }
        
        # Analyze query for learning implications
        query_lower = query.lower()
        
        if 'new' in query_lower or 'learn' in query_lower or 'understand' in query_lower:
            opportunities['learning_potential'] = 0.8
            opportunities['practical_application'] = 0.7
        
        if 'complex' in query_lower or 'advanced' in query_lower:
            opportunities['learning_curve_difficulty'] = 'steep'
            opportunities['learning_curve_steep'] = True
            opportunities['breadth_vs_depth'] = 'depth'
        
        if 'simple' in query_lower or 'basic' in query_lower:
            opportunities['learning_curve_difficulty'] = 'gentle'
            opportunities['efficiency_score'] = 0.8
        
        if 'research' in query_lower or 'study' in query_lower:
            opportunities['learning_potential'] = 0.9
            opportunities['breadth_vs_depth'] = 'depth'
        
        # Check context for learning factors
        if context.get('new_technology', False):
            opportunities['learning_potential'] = 0.8
            opportunities['learning_curve_difficulty'] = 'steep'
        
        if context.get('builds_on_existing', False):
            opportunities['efficiency_score'] = 0.8
            opportunities['learning_curve_difficulty'] = 'gentle'
        
        if context.get('experimental_approach', False):
            opportunities['learning_potential'] = 0.9
            opportunities['breakthrough_learning'] = True
        
        if context.get('well_documented', False):
            opportunities['efficiency_score'] = 0.9
            opportunities['learning_curve_difficulty'] = 'gentle'
        
        if context.get('cutting_edge', False):
            opportunities['learning_potential'] = 0.9
            opportunities['learning_curve_difficulty'] = 'steep'
            opportunities['breakthrough_learning'] = True
        
        return opportunities
    
    def _assess_knowledge_value(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the value and durability of knowledge gained"""
        value = {
            'depth_score': 0.5,
            'breadth_score': 0.5,
            'durability': 0.6,
            'transferability': 0.5,
            'practical_relevance': 0.6
        }
        
        # Check context for knowledge value indicators
        if context.get('fundamental_concepts', False):
            value['depth_score'] = 0.9
            value['durability'] = 0.9
            value['transferability'] = 0.8
        
        if context.get('domain_specific', False):
            value['depth_score'] = 0.8
            value['breadth_score'] = 0.3
            value['transferability'] = 0.4
        
        if context.get('cross_disciplinary', False):
            value['breadth_score'] = 0.9
            value['transferability'] = 0.8
            value['transferable_knowledge'] = True
        
        if context.get('immediately_applicable', False):
            value['practical_relevance'] = 0.9
        
        if context.get('theoretical_focus', False):
            value['depth_score'] = 0.8
            value['practical_relevance'] = 0.4
        
        if context.get('rapidly_changing_field', False):
            value['durability'] = 0.3
            value['knowledge_obsolescence_risk'] = 0.7
        
        if context.get('timeless_principles', False):
            value['durability'] = 0.9
        
        return value
    
    def _evaluate_skill_development(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate skill development opportunities"""
        skills = {
            'skill_growth_score': 0.5,
            'skill_type': 'mixed',  # technical, soft, mixed
            'skill_level': 'intermediate',  # beginner, intermediate, advanced
            'skill_gap_size': 'moderate',
            'practice_opportunities': 0.5
        }
        
        # Check context for skill development factors
        if context.get('technical_skills', False):
            skills['skill_type'] = 'technical'
            skills['skill_growth_score'] = 0.7
        
        if context.get('soft_skills', False):
            skills['skill_type'] = 'soft'
            skills['skill_growth_score'] = 0.6
        
        if context.get('beginner_friendly', False):
            skills['skill_level'] = 'beginner'
            skills['skill_gap_size'] = 'small'
        
        if context.get('expert_level', False):
            skills['skill_level'] = 'advanced'
            skills['skill_gap_size'] = 'large'
            skills['skill_gap_too_large'] = True
        
        if context.get('hands_on_practice', False):
            skills['practice_opportunities'] = 0.9
            skills['skill_growth_score'] += 0.2
        
        if context.get('team_skill_building', False):
            skills['skill_building_potential'] = max(0.7, skills['skill_growth_score'])
        
        return skills
    
    def _measure_educational_impact(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Measure broader educational impact"""
        impact = {
            'educational_value': 0.5,
            'knowledge_sharing_potential': 0.4,
            'documentation_opportunity': 0.3,
            'mentoring_potential': 0.3
        }
        
        # Check context for educational impact factors
        if context.get('creates_documentation', False):
            impact['documentation_opportunity'] = 0.8
            impact['knowledge_sharing_potential'] = 0.7
        
        if context.get('team_learning', False):
            impact['educational_value'] = 0.8
            impact['knowledge_sharing_potential'] = 0.8
        
        if context.get('knowledge_base_contribution', False):
            impact['documentation_opportunity'] = 0.9
            impact['educational_value'] = 0.7
        
        if context.get('teaching_opportunity', False):
            impact['teaching_opportunity'] = True
            impact['mentoring_potential'] = 0.8
            impact['educational_value'] = 0.9
        
        if context.get('best_practices_development', False):
            impact['knowledge_sharing_potential'] = 0.8
            impact['educational_value'] = 0.8
        
        if context.get('fragmented_learning', False):
            impact['knowledge_fragmentation_risk'] = True
            impact['educational_value'] = 0.3
        
        return impact
    
    def _formulate_learning_guidance(self, 
                                   query: str,
                                   learning_opportunities: Dict[str, Any],
                                   knowledge_value: Dict[str, Any],
                                   skill_development: Dict[str, Any]) -> str:
        """Formulate learning-focused guidance"""
        
        learning_potential = learning_opportunities['learning_potential']
        knowledge_depth = knowledge_value['depth_score']
        skill_growth = skill_development['skill_growth_score']
        
        if learning_potential > 0.8 and knowledge_depth > 0.7:
            return (f"Exceptional learning opportunity: High learning potential ({learning_potential:.0%}) "
                   f"with deep knowledge value ({knowledge_depth:.0%}) - prioritize for intellectual growth")
        elif learning_opportunities.get('breakthrough_learning', False):
            return (f"Breakthrough learning potential: Pursue with dedicated study approach "
                   f"despite {learning_opportunities['learning_curve_difficulty']} learning curve")
        elif skill_growth > 0.7 and knowledge_value.get('transferable_knowledge', False):
            return (f"Skill-building focus: Strong skill development ({skill_growth:.0%}) "
                   f"with transferable knowledge - excellent for capability expansion")
        else:
            return (f"Balanced learning approach: Moderate learning value with "
                   f"{learning_opportunities['learning_curve_difficulty']} complexity - "
                   f"proceed with structured learning plan")
    
    def _explain_learning_thinking(self,
                                 learning_opportunities: Dict[str, Any],
                                 knowledge_value: Dict[str, Any],
                                 skill_development: Dict[str, Any],
                                 educational_impact: Dict[str, Any]) -> str:
        """Explain the learning-focused reasoning"""
        
        reasoning = f"From an educational perspective, this offers {learning_opportunities['learning_potential']:.0%} learning potential. "
        
        if learning_opportunities['learning_curve_difficulty'] == 'steep':
            reasoning += "The learning curve is challenging but potentially rewarding. "
        elif learning_opportunities['learning_curve_difficulty'] == 'gentle':
            reasoning += "The learning curve is manageable, allowing for efficient knowledge acquisition. "
        
        if knowledge_value['depth_score'] > 0.7:
            reasoning += f"Knowledge gained will be deep and substantial ({knowledge_value['depth_score']:.0%}). "
        
        if knowledge_value.get('transferable_knowledge', False):
            reasoning += "The knowledge is transferable across domains. "
        
        if skill_development['skill_growth_score'] > 0.6:
            reasoning += f"Significant skill development expected ({skill_development['skill_growth_score']:.0%}). "
        
        if educational_impact.get('teaching_opportunity', False):
            reasoning += "Creates opportunities to teach and mentor others. "
        
        if knowledge_value.get('knowledge_obsolescence_risk', 0) > 0.6:
            reasoning += "Consider the rapid evolution of this knowledge domain. "
        
        reasoning += "Approach with curiosity and systematic learning methodology."
        
        return reasoning
    
    def _determine_learning_priority(self, 
                                   learning_opportunities: Dict[str, Any],
                                   knowledge_value: Dict[str, Any],
                                   context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from learning perspective"""
        
        # Critical if fundamental learning gap or essential knowledge
        if context.get('essential_knowledge', False):
            return PersonaPriority.CRITICAL
        if learning_opportunities.get('breakthrough_learning', False):
            return PersonaPriority.CRITICAL
        
        # High if excellent learning opportunity or high knowledge value
        if learning_opportunities['learning_potential'] > 0.8:
            return PersonaPriority.HIGH
        if knowledge_value['depth_score'] > 0.8 and knowledge_value.get('transferable_knowledge', False):
            return PersonaPriority.HIGH
        
        # Low if minimal learning value
        if (learning_opportunities['learning_potential'] < 0.3 and 
            knowledge_value['depth_score'] < 0.3):
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in scholarly, educational style"""
        return f"From a learning perspective: {content} Knowledge is the foundation upon which all progress is built."