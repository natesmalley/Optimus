"""
The Pragmatist - Practical Implementation Focus

Focuses on what's realistic, achievable, and delivers immediate value.
Balances idealism with real-world constraints.
"""

from typing import Dict, List, Any
from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry


class PragmatistPersona(Persona):
    """
    The Pragmatist focuses on practical, implementable solutions
    
    Key traits:
    - Results-oriented
    - Resource-conscious
    - Timeline-aware
    - Risk-averse
    - Implementation-focused
    """
    
    def __init__(self):
        super().__init__(
            persona_id="pragmatist",
            name="The Pragmatist",
            description="Practical implementation expert focused on deliverable solutions within constraints",
            expertise_domains=[
                "implementation",
                "resource management",
                "timeline planning", 
                "risk mitigation",
                "cost-benefit analysis",
                "feasibility assessment",
                "incremental improvement",
                "technical debt"
            ],
            personality_traits=[
                "practical",
                "realistic",
                "efficient",
                "cautious",
                "results-driven"
            ]
        )
    
    async def analyze(self,
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """Analyze from a practical implementation perspective"""
        
        confidence = self.calculate_confidence(query, context)
        
        # Practical assessment
        feasibility = self._assess_feasibility(query, context)
        resource_needs = self._calculate_resource_needs(context)
        timeline = self._estimate_timeline(context)
        risks = self._identify_practical_risks(context)
        
        # Build recommendation with context awareness
        query_lower = query.lower()
        
        if 'microservice' in query_lower:
            team_size = context.get('team_size', 5)
            if team_size <= 3:
                recommendation = ("Not practical for 3-person team: Microservices add operational complexity, "
                                "deployment overhead, and debugging challenges that will slow development. "
                                "Stick with monolith until team grows to 8+ developers.")
            elif feasibility['score'] > 0.7:
                recommendation = f"Practical with caveats: Start with modular monolith, extract services gradually over {timeline['duration']}"
            else:
                recommendation = "Microservices feasible but complex. Consider service boundaries carefully and start with 2-3 services max"
        else:
            # General recommendations
            if feasibility['score'] > 0.7 and resource_needs['available']:
                recommendation = f"Practical approach: Implement in {timeline['phases']} phases over {timeline['duration']}"
            elif feasibility['score'] > 0.5:
                recommendation = f"Conditionally feasible: Address {feasibility['main_blocker']} first, then proceed incrementally"
            else:
                recommendation = f"Not practical currently: {feasibility['main_blocker']}. Consider simpler alternatives"
        
        concerns = []
        if resource_needs['shortage']:
            concerns.append(f"Resource constraint: {resource_needs['shortage_type']}")
        if timeline['duration'] > "3 months":
            concerns.append("Extended timeline increases risk of scope creep")
        if risks['technical_risk'] > 0.6:
            concerns.append("High technical complexity requires experienced team")
        
        opportunities = []
        if feasibility.get('quick_wins'):
            opportunities.append("Quick wins available for immediate value")
        if resource_needs.get('reusable'):
            opportunities.append("Solution components reusable for future projects")
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_practical_thinking(feasibility, resource_needs, timeline),
            confidence=confidence,
            priority=self._determine_practical_priority(feasibility, context),
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'feasibility_score': feasibility['score'],
                'estimated_timeline': timeline['duration'],
                'resource_availability': resource_needs['available'],
                'implementation_complexity': feasibility.get('complexity', 'medium')
            },
            tags={'practical', 'implementation', 'feasibility', 'resources'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """Calculate confidence based on practical information availability"""
        confidence = 0.6  # Pragmatists start moderately confident
        
        if context.get('clear_requirements'):
            confidence += 0.15
        if context.get('team_experience'):
            confidence += 0.1
        if context.get('similar_projects_done'):
            confidence += 0.15
        if context.get('unknown_factors', 0) > 3:
            confidence -= 0.2
            
        return max(0.2, min(0.9, confidence))
    
    def _assess_feasibility(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess practical feasibility"""
        score = 0.5
        main_blocker = "unclear requirements"
        complexity = "medium"
        
        # Analyze query
        query_lower = query.lower()
        
        # Specific analysis for microservices
        if 'microservice' in query_lower:
            team_size = context.get('team_size', 5)
            startup_stage = context.get('startup_stage', 'unknown')
            
            if team_size <= 3:
                score = 0.2  # Very low feasibility
                complexity = "high"
                main_blocker = "team too small for microservices operational overhead"
            elif team_size >= 8:
                score = 0.7  # Good feasibility
                complexity = "medium"
                main_blocker = None
            
            if startup_stage == 'early':
                score -= 0.2  # Early startups need speed, not complexity
                if not main_blocker:
                    main_blocker = "early startup should focus on product-market fit"
        
        if 'simple' in query_lower or 'basic' in query_lower:
            score += 0.2
            complexity = "low"
        elif 'complex' in query_lower or 'advanced' in query_lower:
            score -= 0.1
            complexity = "high"
        
        # Check context
        if context.get('clear_requirements'):
            score += 0.2
            if main_blocker == "unclear requirements":
                main_blocker = None
        if context.get('existing_infrastructure'):
            score += 0.1
        if context.get('team_bandwidth', 1.0) < 0.5:
            score -= 0.2
            main_blocker = "insufficient team bandwidth"
        
        return {
            'score': min(1.0, max(0.0, score)),
            'main_blocker': main_blocker,
            'complexity': complexity,
            'quick_wins': score > 0.6 and complexity == "low"
        }
    
    def _calculate_resource_needs(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate required resources"""
        return {
            'available': context.get('team_bandwidth', 0.5) > 0.3,
            'shortage': context.get('team_bandwidth', 0.5) < 0.3,
            'shortage_type': 'developer time' if context.get('team_bandwidth', 0.5) < 0.3 else None,
            'reusable': context.get('creates_reusable_components', False)
        }
    
    def _estimate_timeline(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate realistic timeline"""
        complexity = context.get('complexity', 'medium')
        timeline_map = {
            'low': '1-2 weeks',
            'medium': '3-6 weeks', 
            'high': '2-3 months',
            'very_high': '3-6 months'
        }
        
        phases = 2 if complexity in ['medium', 'high'] else 1
        if complexity == 'very_high':
            phases = 3
            
        return {
            'duration': timeline_map.get(complexity, '1 month'),
            'phases': phases
        }
    
    def _identify_practical_risks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify practical implementation risks"""
        return {
            'technical_risk': context.get('technical_complexity', 0.5),
            'timeline_risk': context.get('deadline_pressure', 0.3),
            'resource_risk': 0.7 if context.get('team_bandwidth', 1.0) < 0.5 else 0.3
        }
    
    def _explain_practical_thinking(self, feasibility, resource_needs, timeline) -> str:
        """Explain practical reasoning"""
        reasoning = f"Feasibility assessment: {feasibility['score']:.0%}. "
        reasoning += f"Expected timeline: {timeline['duration']} in {timeline['phases']} phase(s). "
        
        if resource_needs['available']:
            reasoning += "Resources are available. "
        else:
            reasoning += f"Resource constraint identified: {resource_needs['shortage_type']}. "
            
        if feasibility.get('quick_wins'):
            reasoning += "Quick wins possible for early value delivery. "
            
        return reasoning
    
    def _determine_practical_priority(self, feasibility: Dict[str, Any], context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from practical perspective"""
        if context.get('blocking_issue'):
            return PersonaPriority.CRITICAL
        if feasibility['score'] > 0.8 and feasibility.get('quick_wins'):
            return PersonaPriority.HIGH
        if feasibility['score'] < 0.3:
            return PersonaPriority.LOW
        return PersonaPriority.MEDIUM