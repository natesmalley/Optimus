"""
The Economist - Financial Planning and Resource Management

Focuses on financial implications, resource allocation, cost-benefit analysis,
and long-term economic sustainability. Optimizes for financial health and efficiency.
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry

logger = logging.getLogger(__name__)


class EconomistPersona(Persona):
    """
    The Economist evaluates financial impact and resource optimization
    
    Key traits:
    - Financial analysis
    - Resource efficiency  
    - Cost-benefit focus
    - Investment thinking
    - Economic sustainability
    """
    
    def __init__(self):
        super().__init__(
            persona_id="economist",
            name="The Economist",
            description="Financial planning and resource management expert focused on economic optimization and sustainability",
            expertise_domains=[
                "financial planning",
                "cost-benefit analysis",
                "resource allocation", 
                "budget management",
                "investment analysis",
                "economic efficiency",
                "revenue optimization",
                "financial sustainability",
                "opportunity cost",
                "risk assessment",
                "cash flow management",
                "value creation"
            ],
            personality_traits=[
                "analytical",
                "pragmatic",
                "strategic",
                "efficiency-focused",
                "value-conscious"
            ]
        )
    
    async def analyze(self, 
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """
        Analyze from a financial and resource perspective
        """
        confidence = self.calculate_confidence(query, context)
        
        # Economic analysis framework
        cost_analysis = self._perform_cost_analysis(query, context)
        benefit_analysis = self._perform_benefit_analysis(context)
        resource_efficiency = self._assess_resource_efficiency(context)
        financial_sustainability = self._evaluate_financial_sustainability(context)
        
        # Build recommendation
        recommendation = self._formulate_economic_guidance(
            query, cost_analysis, benefit_analysis, resource_efficiency, financial_sustainability
        )
        
        # Identify financial concerns
        concerns = []
        if cost_analysis.get('high_cost_risk', False):
            concerns.append("High cost implications require budget review")
        if financial_sustainability < 0.4:
            concerns.append("Financial sustainability concerns - may impact long-term viability")
        if cost_analysis.get('hidden_costs', 0) > 0.5:
            concerns.append("Significant hidden costs may emerge during implementation")
        if benefit_analysis.get('roi_uncertainty', 0) > 0.6:
            concerns.append("Return on investment is highly uncertain")
        
        # Identify financial opportunities
        opportunities = []
        if benefit_analysis.get('high_roi_potential', False):
            opportunities.append("Excellent return on investment potential")
        if resource_efficiency > 0.7:
            opportunities.append("High resource efficiency gains possible")
        if cost_analysis.get('cost_reduction_potential', 0) > 0.5:
            opportunities.append("Significant cost reduction opportunities identified")
        if benefit_analysis.get('revenue_potential', 0) > 0.6:
            opportunities.append("Strong revenue generation potential")
        
        # Determine priority based on financial impact
        priority = self._determine_financial_priority(cost_analysis, benefit_analysis, context)
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_economic_thinking(
                cost_analysis, benefit_analysis, resource_efficiency, financial_sustainability
            ),
            confidence=confidence,
            priority=priority,
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'cost_impact': cost_analysis.get('total_cost_impact', 0.5),
                'benefit_score': benefit_analysis.get('total_benefit_score', 0.5),
                'roi_estimate': benefit_analysis.get('roi_estimate', 'unknown'),
                'resource_efficiency': resource_efficiency,
                'financial_sustainability': financial_sustainability,
                'payback_period': cost_analysis.get('payback_period', 'unknown')
            },
            tags={'financial', 'economics', 'cost-benefit', 'resources', 'roi'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """
        Calculate confidence based on financial information availability
        """
        confidence = 0.5  # Base confidence for economic analysis
        
        # Increase confidence for financial data availability
        if context.get('budget_info'):
            confidence += 0.2
        
        # Increase if cost/benefit data available
        if context.get('cost_estimates') or context.get('benefit_projections'):
            confidence += 0.15
        
        # Increase if this involves financial domains
        query_lower = query.lower()
        financial_keywords = ['cost', 'budget', 'money', 'price', 'invest', 'save', 'profit', 'revenue']
        if any(keyword in query_lower for keyword in financial_keywords):
            confidence += 0.25
        
        # Increase for historical financial data
        if context.get('historical_costs') or context.get('past_performance'):
            confidence += 0.1
        
        return max(0.2, min(0.9, confidence))
    
    def _perform_cost_analysis(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive cost analysis"""
        analysis = {
            'direct_costs': 0.5,
            'indirect_costs': 0.3,
            'opportunity_costs': 0.3,
            'hidden_costs': 0.2,
            'total_cost_impact': 0.4,
            'cost_certainty': 0.6,
            'payback_period': 'medium-term'
        }
        
        # Analyze query for cost implications
        query_lower = query.lower()
        
        if 'expensive' in query_lower or 'costly' in query_lower:
            analysis['direct_costs'] = 0.8
            analysis['total_cost_impact'] = 0.7
        
        if 'cheap' in query_lower or 'low-cost' in query_lower:
            analysis['direct_costs'] = 0.2
            analysis['total_cost_impact'] = 0.3
        
        if 'complex' in query_lower or 'difficult' in query_lower:
            analysis['hidden_costs'] = 0.6
            analysis['indirect_costs'] = 0.7
            analysis['cost_certainty'] = 0.4
        
        if 'urgent' in query_lower or 'rush' in query_lower:
            analysis['direct_costs'] += 0.3
            analysis['opportunity_costs'] = 0.6
        
        if 'optimize' in query_lower or 'efficient' in query_lower:
            analysis['cost_reduction_potential'] = 0.7
        
        # Check context for cost factors
        if context.get('requires_new_infrastructure', False):
            analysis['direct_costs'] = 0.8
            analysis['hidden_costs'] = 0.5
        
        if context.get('team_training_needed', False):
            analysis['indirect_costs'] += 0.3
            analysis['opportunity_costs'] += 0.2
        
        if context.get('ongoing_maintenance', False):
            analysis['hidden_costs'] += 0.3
            analysis['payback_period'] = 'long-term'
        
        if context.get('one_time_effort', False):
            analysis['hidden_costs'] = 0.1
            analysis['payback_period'] = 'short-term'
        
        # Check for high cost risk
        total_cost = (analysis['direct_costs'] + analysis['indirect_costs'] + 
                     analysis['opportunity_costs'] + analysis['hidden_costs']) / 4
        analysis['high_cost_risk'] = total_cost > 0.7
        analysis['total_cost_impact'] = total_cost
        
        return analysis
    
    def _perform_benefit_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive benefit analysis"""
        analysis = {
            'immediate_benefits': 0.4,
            'long_term_benefits': 0.5,
            'revenue_potential': 0.3,
            'cost_savings': 0.3,
            'efficiency_gains': 0.4,
            'total_benefit_score': 0.4,
            'roi_uncertainty': 0.4,
            'roi_estimate': 'moderate'
        }
        
        # Check context for benefit indicators
        if context.get('saves_time', False):
            analysis['efficiency_gains'] = 0.7
            analysis['cost_savings'] = 0.5
        
        if context.get('increases_revenue', False):
            analysis['revenue_potential'] = 0.8
            analysis['long_term_benefits'] = 0.7
        
        if context.get('improves_user_experience', False):
            analysis['long_term_benefits'] = 0.6
            analysis['revenue_potential'] = 0.5
        
        if context.get('reduces_costs', False):
            analysis['cost_savings'] = 0.8
            analysis['immediate_benefits'] = 0.6
        
        if context.get('scalability_benefits', False):
            analysis['long_term_benefits'] = 0.8
        
        if context.get('competitive_advantage', False):
            analysis['revenue_potential'] = 0.7
            analysis['long_term_benefits'] = 0.8
        
        if context.get('measurable_outcomes', False):
            analysis['roi_uncertainty'] = 0.2
        else:
            analysis['roi_uncertainty'] = 0.6
        
        # Calculate total benefit score
        total_benefits = (analysis['immediate_benefits'] + analysis['long_term_benefits'] + 
                         analysis['revenue_potential'] + analysis['cost_savings'] + 
                         analysis['efficiency_gains']) / 5
        analysis['total_benefit_score'] = total_benefits
        
        # Determine ROI estimate
        if total_benefits > 0.7 and analysis['roi_uncertainty'] < 0.4:
            analysis['roi_estimate'] = 'high'
            analysis['high_roi_potential'] = True
        elif total_benefits < 0.3 or analysis['roi_uncertainty'] > 0.7:
            analysis['roi_estimate'] = 'low'
        
        return analysis
    
    def _assess_resource_efficiency(self, context: Dict[str, Any]) -> float:
        """Assess resource utilization efficiency"""
        efficiency = 0.5  # Base efficiency
        
        # Positive efficiency factors
        if context.get('leverages_existing_resources', False):
            efficiency += 0.2
        if context.get('automates_processes', False):
            efficiency += 0.3
        if context.get('reduces_manual_work', False):
            efficiency += 0.2
        if context.get('reuses_components', False):
            efficiency += 0.15
        
        # Negative efficiency factors
        if context.get('duplicates_effort', False):
            efficiency -= 0.3
        if context.get('requires_specialized_skills', False):
            efficiency -= 0.1
        if context.get('resource_intensive', False):
            efficiency -= 0.2
        
        return max(0.0, min(1.0, efficiency))
    
    def _evaluate_financial_sustainability(self, context: Dict[str, Any]) -> float:
        """Evaluate long-term financial sustainability"""
        sustainability = 0.5  # Neutral default
        
        # Positive sustainability factors
        if context.get('recurring_value', False):
            sustainability += 0.3
        if context.get('scalable_solution', False):
            sustainability += 0.2
        if context.get('low_maintenance_cost', False):
            sustainability += 0.2
        
        # Negative sustainability factors
        if context.get('high_ongoing_costs', False):
            sustainability -= 0.3
        if context.get('requires_continuous_investment', False):
            sustainability -= 0.2
        if context.get('market_uncertainty', False):
            sustainability -= 0.1
        
        return max(0.0, min(1.0, sustainability))
    
    def _formulate_economic_guidance(self, 
                                   query: str,
                                   cost_analysis: Dict[str, Any],
                                   benefit_analysis: Dict[str, Any],
                                   resource_efficiency: float,
                                   financial_sustainability: float) -> str:
        """Formulate economically-sound guidance"""
        
        cost_impact = cost_analysis['total_cost_impact']
        benefit_score = benefit_analysis['total_benefit_score']
        
        if benefit_score > 0.7 and cost_impact < 0.5:
            return (f"Economically excellent: High benefits ({benefit_score:.0%}) with "
                   f"manageable costs ({cost_impact:.0%}) - strong ROI expected")
        elif benefit_score > cost_impact + 0.2:
            return (f"Financially favorable: Benefits ({benefit_score:.0%}) outweigh "
                   f"costs ({cost_impact:.0%}) with {benefit_analysis['roi_estimate']} ROI")
        elif cost_impact > 0.7 and benefit_score < 0.5:
            return (f"Economic caution advised: High costs ({cost_impact:.0%}) versus "
                   f"low benefits ({benefit_score:.0%}) - consider alternatives")
        else:
            return (f"Balanced economic approach: Moderate cost-benefit ratio requires "
                   f"careful monitoring and phased implementation")
    
    def _explain_economic_thinking(self,
                                 cost_analysis: Dict[str, Any],
                                 benefit_analysis: Dict[str, Any],
                                 resource_efficiency: float,
                                 financial_sustainability: float) -> str:
        """Explain the economic reasoning"""
        
        reasoning = f"Economic analysis shows {cost_analysis['total_cost_impact']:.0%} cost impact. "
        
        if benefit_analysis['total_benefit_score'] > 0.6:
            reasoning += f"Benefits are substantial ({benefit_analysis['total_benefit_score']:.0%}) with "
            reasoning += f"{benefit_analysis['roi_estimate']} ROI potential. "
        else:
            reasoning += f"Benefits are moderate ({benefit_analysis['total_benefit_score']:.0%}). "
        
        if resource_efficiency > 0.6:
            reasoning += f"Resource efficiency is good ({resource_efficiency:.0%}). "
        else:
            reasoning += f"Resource efficiency needs attention ({resource_efficiency:.0%}). "
        
        if financial_sustainability > 0.6:
            reasoning += "Long-term financial sustainability is positive. "
        else:
            reasoning += "Financial sustainability requires monitoring. "
        
        if cost_analysis.get('hidden_costs', 0) > 0.5:
            reasoning += "Hidden costs may emerge during implementation. "
        
        if cost_analysis['payback_period'] == 'long-term':
            reasoning += "Extended payback period requires patience and commitment. "
        
        return reasoning
    
    def _determine_financial_priority(self, 
                                    cost_analysis: Dict[str, Any],
                                    benefit_analysis: Dict[str, Any],
                                    context: Dict[str, Any]) -> PersonaPriority:
        """Determine priority from financial perspective"""
        
        # Critical if major financial implications
        if cost_analysis['high_cost_risk'] and benefit_analysis['total_benefit_score'] < 0.3:
            return PersonaPriority.CRITICAL
        if context.get('budget_critical', False):
            return PersonaPriority.CRITICAL
        
        # High if excellent ROI or significant cost savings
        if benefit_analysis.get('high_roi_potential', False):
            return PersonaPriority.HIGH
        if cost_analysis.get('cost_reduction_potential', 0) > 0.7:
            return PersonaPriority.HIGH
        
        # Low if minimal financial impact
        if (cost_analysis['total_cost_impact'] < 0.3 and 
            benefit_analysis['total_benefit_score'] < 0.3):
            return PersonaPriority.LOW
        
        return PersonaPriority.MEDIUM
    
    def format_response_style(self, content: str) -> str:
        """Format response in analytical, value-focused style"""
        return f"From a financial perspective: {content} Optimal resource allocation drives sustainable success."