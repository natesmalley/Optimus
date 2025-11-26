"""
The Mentor - Teaching, Guidance, and Leadership

Focuses on teaching opportunities, guidance provision, leadership development,
and wisdom sharing. Prioritizes growth of others and knowledge transfer.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class MentorPersona(Persona):
    """
    The Mentor emphasizes teaching, guidance, and developing others
    
    Key traits:
    - Teaching focus
    - Wisdom sharing
    - Leadership development
    - Guidance provision
    - Others' growth priority
    """
    
    def __init__(self):
        super().__init__(
            persona_id="mentor",
            name="The Mentor",
            description="Teaching and leadership expert focused on guidance, wisdom sharing, and developing others",
            expertise_domains=[
                "teaching",
                "mentoring",
                "leadership development",
                "guidance",
                "wisdom sharing",
                "coaching",
                "skill transfer",
                "team development",
                "knowledge sharing",
                "personal development",
                "leadership",
                "empowerment"
            ],
            personality_traits=[
                "wise",
                "patient",
                "supportive",
                "encouraging", 
                "development-focused"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from a teaching and mentorship perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Mentorship analysis framework
        teaching_opportunities = self._identify_teaching_opportunities(query, context)
        leadership_development = self._assess_leadership_development(context)
        guidance_needs = self._evaluate_guidance_needs(context)
        knowledge_transfer = self._analyze_knowledge_transfer(context)
        
        # Build recommendation
        recommendation = self._formulate_mentoring_guidance(
            query, teaching_opportunities, leadership_development, guidance_needs
        )
        
        # Identify mentoring concerns
        concerns = []
        if guidance_needs.get('overwhelming_complexity', False):
            concerns.append("Complexity may overwhelm rather than educate")
        if teaching_opportunities.get('insufficient_teaching_time', False):
            concerns.append("Insufficient time allocated for proper teaching and guidance")
        if leadership_development.get('leadership_readiness_low', False):
            concerns.append("Team may not be ready for increased leadership responsibility")
        if knowledge_transfer.get('knowledge_retention_risk', 0) > 0.6:
            concerns.append("Risk of poor knowledge retention without proper reinforcement")
        
        # Identify mentoring opportunities
        opportunities = []
        if teaching_opportunities.get('excellent_teaching_moment', False):
            opportunities.append("Excellent teaching moment for skill and wisdom transfer")
        if leadership_development.get('leadership_growth_potential', 0) > 0.7:
            opportunities.append("Strong opportunity for leadership development")
        if knowledge_transfer.get('sustainable_knowledge_sharing', False):
            opportunities.append("Can create sustainable knowledge sharing systems")
        if guidance_needs.get('high_impact_guidance', False):
            opportunities.append("Guidance can have significant positive impact")
        
        # Determine priority based on mentoring impact
        priority = self._determine_mentoring_priority(teaching_opportunities, guidance_needs, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_mentoring_thinking(
                teaching_opportunities, leadership_development, guidance_needs, knowledge_transfer
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'teaching_value': teaching_opportunities.get('teaching_value', 0.5),
                'leadership_growth': leadership_development.get('leadership_growth_potential', 0.5),
                'guidance_impact': guidance_needs.get('guidance_impact_score', 0.5),
                'knowledge_transfer_effectiveness': knowledge_transfer.get('transfer_effectiveness', 0.5),
                'mentorship_readiness': guidance_needs.get('mentorship_readiness', 0.5)
            },
            tags={'mentoring', 'teaching', 'leadership', 'guidance', 'development'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on mentoring domain relevance
        """
        confidence = 0.7  # Good base confidence for guidance aspects
        
        # Increase confidence for teaching/mentoring contexts
        if context.get('team_development') or context.get('skill_building'):
            confidence += 0.15
        
        # Increase if leadership elements present
        if context.get('leadership_opportunity') or context.get('guidance_needed'):
            confidence += 0.15
        
        # Increase if this involves mentoring domains
        query_lower = query.lower()
        mentoring_keywords = ['teach', 'guide', 'mentor', 'lead', 'develop', 'coach', 'train', 'share']
        if any(keyword in query_lower for keyword in mentoring_keywords):
            confidence += 0.15
        
        return max(0.4, min(0.95, confidence))
    
    def _identify_teaching_opportunities(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify teaching and learning opportunities"""
        opportunities = {
            'teaching_value': 0.5,
            'teaching_complexity': 'medium',
            'learning_audience': 'mixed',  # individual, small_group, team, organization
            'teaching_method': 'hands_on',  # lecture, hands_on, project_based, mentoring
            'skill_transfer_potential': 0.5
        }
        
        # Analyze query for teaching implications
        query_lower = query.lower()
        
        if 'teach' in query_lower or 'show' in query_lower or 'explain' in query_lower:
            opportunities['teaching_value'] = 0.9
            opportunities['teaching_method'] = 'mentoring'
        
        if 'complex' in query_lower or 'advanced' in query_lower:
            opportunities['teaching_complexity'] = 'high'
            opportunities['teaching_value'] = 0.8
        
        if 'simple' in query_lower or 'basic' in query_lower:
            opportunities['teaching_complexity'] = 'low'
            opportunities['skill_transfer_potential'] = 0.8
        
        if 'new' in query_lower or 'learn' in query_lower:
            opportunities['teaching_value'] = 0.8
            opportunities['teaching_method'] = 'hands_on'
        
        # Check context for teaching factors
        if context.get('team_learning_opportunity', False):
            opportunities['learning_audience'] = 'team'
            opportunities['teaching_value'] = 0.8
            opportunities['teaching_method'] = 'project_based'
        
        if context.get('individual_mentoring', False):
            opportunities['learning_audience'] = 'individual'
            opportunities['teaching_method'] = 'mentoring'
            opportunities['skill_transfer_potential'] = 0.9
        
        if context.get('knowledge_documentation', False):
            opportunities['teaching_value'] = 0.7
            opportunities['sustainable_teaching'] = True
        
        if context.get('rushed_timeline', False):
            opportunities['insufficient_teaching_time'] = True
            opportunities['teaching_value'] = 0.3
        
        if context.get('perfect_learning_scenario', False):
            opportunities['excellent_teaching_moment'] = True
            opportunities['teaching_value'] = 0.9
        
        return opportunities
    
    def _assess_leadership_development(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess leadership development opportunities"""
        development = {
            'leadership_growth_potential': 0.4,
            'leadership_skills_needed': [],
            'delegation_opportunities': 0.3,
            'decision_making_practice': 0.3,
            'team_building_potential': 0.4
        }
        
        # Check context for leadership factors
        if context.get('leadership_opportunity', False):
            development['leadership_growth_potential'] = 0.8
            development['decision_making_practice'] = 0.7
        
        if context.get('team_coordination_needed', False):
            development['team_building_potential'] = 0.8
            development['leadership_skills_needed'].append('coordination')
        
        if context.get('delegation_possible', False):
            development['delegation_opportunities'] = 0.8
            development['leadership_skills_needed'].append('delegation')
        
        if context.get('conflict_resolution_needed', False):
            development['leadership_skills_needed'].append('conflict_resolution')
            development['leadership_growth_potential'] = 0.7
        
        if context.get('junior_team_members', False):
            development['leadership_growth_potential'] = 0.6
            development['team_building_potential'] = 0.7
        
        if context.get('high_stakes_situation', False):
            development['leadership_readiness_low'] = True
            development['leadership_growth_potential'] = 0.3
        
        if context.get('safe_practice_environment', False):
            development['leadership_growth_potential'] = 0.9
        
        return development
    
    def _evaluate_guidance_needs(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate guidance needs and impact potential"""
        guidance = {
            'guidance_impact_score': 0.5,
            'guidance_urgency': 'moderate',  # low, moderate, high, critical
            'guidance_type': 'general',  # technical, personal, career, general
            'mentorship_readiness': 0.6,
            'support_level_needed': 'moderate'
        }
        
        # Check context for guidance factors
        if context.get('struggling_team_member', False):
            guidance['guidance_urgency'] = 'high'
            guidance['guidance_impact_score'] = 0.8
            guidance['support_level_needed'] = 'high'
        
        if context.get('career_development', False):
            guidance['guidance_type'] = 'career'
            guidance['guidance_impact_score'] = 0.7
            guidance['mentorship_readiness'] = 0.8
        
        if context.get('technical_guidance_needed', False):
            guidance['guidance_type'] = 'technical'
            guidance['guidance_impact_score'] = 0.6
        
        if context.get('personal_development', False):
            guidance['guidance_type'] = 'personal'
            guidance['guidance_impact_score'] = 0.8
            guidance['mentorship_readiness'] = 0.7
        
        if context.get('crisis_situation', False):
            guidance['guidance_urgency'] = 'critical'
            guidance['support_level_needed'] = 'high'
        
        if context.get('receptive_to_guidance', False):
            guidance['mentorship_readiness'] = 0.9
            guidance['guidance_impact_score'] += 0.2
        
        if context.get('resistant_to_help', False):
            guidance['mentorship_readiness'] = 0.2
            guidance['guidance_impact_score'] = 0.3
        
        # Determine high impact guidance
        if (guidance['guidance_impact_score'] > 0.7 and 
            guidance['mentorship_readiness'] > 0.6):
            guidance['high_impact_guidance'] = True
        
        if context.get('overwhelming_complexity', False):
            guidance['overwhelming_complexity'] = True
        
        return guidance
    
    def _analyze_knowledge_transfer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze knowledge transfer effectiveness"""
        transfer = {
            'transfer_effectiveness': 0.5,
            'knowledge_complexity': 'medium',
            'retention_factors': 0.5,
            'practical_application': 0.5,
            'documentation_quality': 0.4
        }
        
        # Check context for knowledge transfer factors
        if context.get('hands_on_learning', False):
            transfer['transfer_effectiveness'] = 0.8
            transfer['retention_factors'] = 0.8
            transfer['practical_application'] = 0.9
        
        if context.get('theoretical_only', False):
            transfer['transfer_effectiveness'] = 0.4
            transfer['practical_application'] = 0.2
        
        if context.get('well_documented', False):
            transfer['documentation_quality'] = 0.9
            transfer['retention_factors'] = 0.7
        
        if context.get('complex_knowledge', False):
            transfer['knowledge_complexity'] = 'high'
            transfer['transfer_effectiveness'] -= 0.2
        
        if context.get('simple_concepts', False):
            transfer['knowledge_complexity'] = 'low'
            transfer['transfer_effectiveness'] = 0.8
        
        if context.get('immediate_application', False):
            transfer['practical_application'] = 0.9
            transfer['retention_factors'] = 0.8
        
        if context.get('creates_knowledge_system', False):
            transfer['sustainable_knowledge_sharing'] = True
            transfer['transfer_effectiveness'] = 0.8
        
        if context.get('poor_follow_up', False):
            transfer['knowledge_retention_risk'] = 0.8
        
        return transfer
    
    def _formulate_mentoring_guidance(self, 
                                    query: str,
                                    teaching_opportunities: Dict[str, Any],
                                    leadership_development: Dict[str, Any],
                                    guidance_needs: Dict[str, Any]) -> str:
        """Formulate mentoring-focused guidance"""
        
        teaching_value = teaching_opportunities['teaching_value']
        leadership_potential = leadership_development['leadership_growth_potential']
        guidance_impact = guidance_needs['guidance_impact_score']
        
        if teaching_opportunities.get('excellent_teaching_moment', False):
            return (f"Seize this teaching opportunity: Exceptional learning moment "
                   f"with {teaching_value:.0%} teaching value - invest in knowledge transfer and growth")
        elif guidance_needs.get('high_impact_guidance', False):
            return (f"Prioritize mentoring impact: High-impact guidance opportunity "
                   f"({guidance_impact:.0%}) with {guidance_needs['guidance_urgency']} urgency - "
                   f"focus on supportive development")
        elif leadership_potential > 0.7:
            return (f"Cultivate leadership: Strong leadership development potential "
                   f"({leadership_potential:.0%}) - create safe practice opportunities")
        else:
            return (f"Apply mentoring wisdom: Moderate teaching value with "
                   f"{guidance_needs['guidance_type']} guidance needs - balance support with growth challenge")
    
    def _explain_mentoring_thinking(self,
                                  teaching_opportunities: Dict[str, Any],
                                  leadership_development: Dict[str, Any],
                                  guidance_needs: Dict[str, Any],
                                  knowledge_transfer: Dict[str, Any]) -> str:
        """Explain the mentoring-focused reasoning"""
        
        reasoning = f"From a mentoring perspective, this presents {teaching_opportunities['teaching_value']:.0%} teaching value. "
        
        if guidance_needs['guidance_urgency'] in ['high', 'critical']:
            reasoning += f"Guidance urgency is {guidance_needs['guidance_urgency']}, requiring immediate attention. "
        
        if leadership_development['leadership_growth_potential'] > 0.6:
            reasoning += f"Strong leadership development opportunity ({leadership_development['leadership_growth_potential']:.0%}). "
        
        if knowledge_transfer['transfer_effectiveness'] > 0.7:
            reasoning += f"Knowledge transfer effectiveness is high ({knowledge_transfer['transfer_effectiveness']:.0%}). "
        elif knowledge_transfer['transfer_effectiveness'] < 0.4:
            reasoning += "Knowledge transfer may be challenging - consider alternative approaches. "
        
        if guidance_needs['mentorship_readiness'] > 0.7:
            reasoning += "High readiness for mentorship creates excellent learning conditions. "
        
        if teaching_opportunities.get('sustainable_teaching', False):
            reasoning += "Can create sustainable knowledge sharing systems. "
        
        if guidance_needs.get('overwhelming_complexity', False):
            reasoning += "Complexity needs careful management to avoid overwhelming learners. "
        
        reasoning += "Success comes through patient guidance, wise counsel, and empowering others to grow."
        
        return reasoning
    
    def _determine_mentoring_priority(self, 
                                    teaching_opportunities: Dict[str, Any],
                                    guidance_needs: Dict[str, Any],
                                    context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from mentoring perspective"""
        
        # Critical if urgent guidance needed or crisis mentoring
        if guidance_needs['guidance_urgency'] == 'critical':
            return PersonaPriority.CRITICAL
        if context.get('mentoring_crisis', False):
            return PersonaPriority.CRITICAL
        
        # High if excellent teaching moment or high-impact guidance
        if teaching_opportunities.get('excellent_teaching_moment', False):
            return PersonaPriority.HIGH
        if guidance_needs.get('high_impact_guidance', False):
            return PersonaPriority.HIGH
        
        # Low if minimal teaching/mentoring value
        if (teaching_opportunities['teaching_value'] < 0.3 and 
            guidance_needs['guidance_impact_score'] < 0.3):
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in wise, supportive mentoring style"""
        return f"With mentoring wisdom: {content} Our greatest legacy lies in the growth we nurture in others."