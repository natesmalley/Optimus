"""
The Innovator - Creative Solutions and New Approaches

Focuses on novel solutions, emerging technologies, and breakthrough thinking.
Challenges assumptions and explores unconventional paths.
"""

from typing import Dict, List, Any
from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry


class InnovatorPersona(Persona):
    """
    The Innovator seeks creative and novel solutions
    
    Key traits:
    - Creative thinking
    - Technology exploration
    - Pattern breaking
    - Experimental mindset
    - Future-focused
    """
    
    def __init__(self):
        super().__init__(
            persona_id="innovator",
            name="The Innovator",
            description="Creative problem-solver focused on breakthrough solutions and emerging technologies",
            expertise_domains=[
                "innovation",
                "emerging technology",
                "creative solutions",
                "experimentation",
                "paradigm shifts",
                "ai/ml integration",
                "automation",
                "next-gen architecture"
            ],
            personality_traits=[
                "creative",
                "curious",
                "experimental",
                "optimistic",
                "unconventional"
            ]
        )
    
    async def analyze(self,
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """Analyze from an innovation perspective"""
        
        confidence = self.calculate_confidence(query, context)
        
        # Innovation assessment
        innovation_opportunities = self._identify_innovation_opportunities(query, context)
        creative_solutions = self._generate_creative_solutions(query, context)
        tech_leverage = self._assess_technology_leverage(context)
        
        # Build recommendation
        if innovation_opportunities['breakthrough_potential'] > 0.7:
            recommendation = f"Breakthrough opportunity: {creative_solutions['top_solution']}"
        elif tech_leverage['emerging_tech_fit'] > 0.6:
            recommendation = f"Leverage {tech_leverage['best_tech']}: {creative_solutions['tech_enabled_solution']}"
        else:
            recommendation = f"Incremental innovation: {creative_solutions['practical_innovation']}"
        
        concerns = []
        if innovation_opportunities.get('high_risk'):
            concerns.append("Innovation risk: Requires experimentation and iteration")
        if tech_leverage.get('learning_curve'):
            concerns.append("Team may need upskilling for new technology")
        
        opportunities = []
        if innovation_opportunities['breakthrough_potential'] > 0.5:
            opportunities.append("Potential for industry-leading solution")
        if tech_leverage['automation_potential'] > 0.6:
            opportunities.append(f"Automation could reduce effort by {tech_leverage['automation_potential']*100:.0f}%")
        if creative_solutions.get('patent_potential'):
            opportunities.append("Innovative approach may be patentable")
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_innovative_thinking(innovation_opportunities, tech_leverage),
            confidence=confidence,
            priority=self._determine_innovation_priority(innovation_opportunities),
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'breakthrough_potential': innovation_opportunities['breakthrough_potential'],
                'automation_potential': tech_leverage['automation_potential'],
                'innovation_type': innovation_opportunities['type'],
                'suggested_technologies': tech_leverage.get('suggested_tech', [])
            },
            tags={'innovation', 'creative', 'breakthrough', 'emerging-tech'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """Calculate confidence for innovative solutions"""
        confidence = 0.6  # Innovators are generally optimistic
        
        if 'new' in query.lower() or 'innovative' in query.lower():
            confidence += 0.15
        if context.get('open_to_experimentation'):
            confidence += 0.15
        if context.get('conservative_environment'):
            confidence -= 0.2
        if context.get('emerging_tech_available'):
            confidence += 0.1
            
        return max(0.3, min(0.95, confidence))
    
    def _identify_innovation_opportunities(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify opportunities for innovation"""
        breakthrough_potential = 0.5
        innovation_type = "incremental"
        
        query_lower = query.lower()
        if any(word in query_lower for word in ['automate', 'ai', 'ml', 'transform']):
            breakthrough_potential = 0.8
            innovation_type = "transformative"
        elif 'optimize' in query_lower or 'improve' in query_lower:
            breakthrough_potential = 0.6
            innovation_type = "optimization"
        
        return {
            'breakthrough_potential': breakthrough_potential,
            'type': innovation_type,
            'high_risk': breakthrough_potential > 0.7
        }
    
    def _generate_creative_solutions(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate creative solution approaches"""
        return {
            'top_solution': "AI-powered automation with self-learning capabilities",
            'tech_enabled_solution': "Cloud-native microservices with event-driven architecture",
            'practical_innovation': "Modular design with plugin architecture for extensibility",
            'patent_potential': context.get('novel_approach', False)
        }
    
    def _assess_technology_leverage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how emerging tech can be leveraged"""
        return {
            'emerging_tech_fit': 0.7,
            'best_tech': "AI/ML automation",
            'automation_potential': 0.6,
            'learning_curve': True,
            'suggested_tech': ["AI/ML", "Cloud-native", "Event-driven", "Microservices"]
        }
    
    def _explain_innovative_thinking(self, opportunities, tech_leverage) -> str:
        """Explain innovative reasoning"""
        reasoning = f"Innovation analysis reveals {opportunities['type']} opportunity "
        reasoning += f"with {opportunities['breakthrough_potential']:.0%} breakthrough potential. "
        
        if tech_leverage['automation_potential'] > 0.5:
            reasoning += f"Automation could deliver {tech_leverage['automation_potential']*100:.0f}% efficiency gains. "
        
        reasoning += "This represents a chance to leapfrog conventional approaches."
        return reasoning
    
    def _determine_innovation_priority(self, opportunities: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from innovation perspective"""
        if opportunities['breakthrough_potential'] > 0.8:
            return PersonaPriority.HIGH
        if opportunities['breakthrough_potential'] < 0.3:
            return PersonaPriority.LOW
        return PersonaPriority.MEDIUM