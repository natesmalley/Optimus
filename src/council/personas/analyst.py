"""
The Analyst - Data-Driven Insights and Metrics

Focuses on data analysis, metrics, patterns, and evidence-based decisions.
Provides quantitative backing for decisions.
"""

from typing import Dict, List, Any, Tuple
import statistics
from ..persona import Persona, PersonaResponse, PersonaPriority
from ..blackboard import BlackboardEntry


class AnalystPersona(Persona):
    """
    The Analyst provides data-driven insights and metrics
    
    Key traits:
    - Data-focused
    - Analytical
    - Evidence-based
    - Pattern recognition
    - Metrics-driven
    """
    
    def __init__(self):
        super().__init__(
            persona_id="analyst",
            name="The Analyst",
            description="Data analysis expert focused on metrics, patterns, and evidence-based insights",
            expertise_domains=[
                "data analysis",
                "metrics",
                "performance analysis",
                "trend analysis",
                "statistical analysis",
                "benchmarking",
                "kpi tracking",
                "predictive analytics"
            ],
            personality_traits=[
                "analytical",
                "methodical",
                "objective",
                "detail-oriented",
                "evidence-based"
            ]
        )
    
    async def analyze(self,
                     query: str,
                     context: Dict[str, Any],
                     related_entries: List[BlackboardEntry]) -> PersonaResponse:
        """Analyze from a data and metrics perspective"""
        
        confidence = self.calculate_confidence(query, context)
        
        # Data analysis
        metrics = self._analyze_metrics(context)
        patterns = self._identify_patterns(context)
        projections = self._calculate_projections(metrics, patterns)
        benchmarks = self._compare_benchmarks(metrics, context)
        
        # Build context-aware recommendation
        query_lower = query.lower()
        
        if 'microservice' in query_lower:
            team_size = context.get('team_size', 5)
            if team_size <= 3:
                recommendation = (f"Data analysis (limited {metrics['data_points']} metrics, {metrics['data_quality']:.0%} quality): "
                                f"Small team lacks observability infrastructure for microservices. "
                                f"Current monolith performance at {metrics['key_metric']:.1f}% is sufficient.")
            else:
                recommendation = (f"Metrics suggest complexity trade-off: Current performance {metrics['key_metric']:.1f}%. "
                                f"Microservices will initially reduce performance but improve team productivity.")
        elif metrics['data_quality'] < 0.3:
            recommendation = "Insufficient data for reliable analysis. Gather more metrics first"
        elif projections['trend'] == 'improving' and benchmarks['performance'] > 0.7:
            recommendation = f"Data supports proceeding: {metrics['key_metric']:.1f}% improvement projected"
        elif patterns['anomalies']:
            recommendation = f"Investigate anomalies first: {patterns['anomaly_description']}"
        else:
            recommendation = f"Based on {metrics['data_points']} data points: {self._get_data_recommendation(metrics, projections)}"
        
        concerns = []
        if metrics['data_quality'] < 0.5:
            concerns.append(f"Data quality concerns: {metrics['quality_issues']}")
        if patterns.get('negative_trend'):
            concerns.append(f"Negative trend detected in {patterns['trending_metric']}")
        if benchmarks['performance'] < 0.5:
            concerns.append("Below industry benchmarks")
        
        opportunities = []
        if patterns.get('positive_correlation'):
            opportunities.append(f"Strong correlation found: {patterns['correlation_insight']}")
        if projections['improvement_potential'] > 0.3:
            opportunities.append(f"{projections['improvement_potential']*100:.0f}% improvement potential identified")
        
        return PersonaResponse(
            persona_id=self.persona_id,
            persona_name=self.name,
            recommendation=recommendation,
            reasoning=self._explain_analytical_thinking(metrics, patterns, projections),
            confidence=confidence,
            priority=self._determine_analytical_priority(metrics, patterns),
            concerns=concerns,
            opportunities=opportunities,
            data_points={
                'metrics_analyzed': metrics['data_points'],
                'data_quality': metrics['data_quality'],
                'trend': projections['trend'],
                'confidence_interval': projections.get('confidence_interval', 'N/A'),
                'benchmark_comparison': benchmarks['performance']
            },
            tags={'data', 'metrics', 'analysis', 'evidence-based'}
        )
    
    def calculate_confidence(self, query: str, context: Dict[str, Any]) -> float:
        """Calculate confidence based on data availability and analytical relevance"""
        confidence = 0.5  # Start neutral
        
        # Check if query has analytical keywords that increase confidence
        query_lower = query.lower()
        analytical_keywords = ['data', 'metrics', 'performance', 'analyze', 'measure', 'statistics', 'numbers', 'evidence']
        if any(keyword in query_lower for keyword in analytical_keywords):
            confidence += 0.15
        
        # Architecture decisions often benefit from analytical perspective
        if any(term in query_lower for term in ['architecture', 'microservice', 'database', 'scale', 'optimize']):
            confidence += 0.1
        
        # Increase for data availability
        if context.get('metrics_available', 0) > 10:
            confidence += 0.2
        if context.get('historical_data'):
            confidence += 0.15
        if context.get('data_quality', 0.5) > 0.7:
            confidence += 0.15
        
        # Increase for common business context indicators
        if context.get('team_size') or context.get('budget') or context.get('timeline'):
            confidence += 0.1  # Basic business metrics available
        
        # Decrease for data issues (only if explicitly mentioned)
        if context.get('data_gaps') is True:
            confidence -= 0.15
        # Only penalize if explicitly stated as having very few metrics
        if context.get('metrics_available') is not None and context.get('metrics_available') < 3:
            confidence -= 0.2
            
        return max(0.3, min(0.9, confidence))
    
    def _analyze_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze available metrics"""
        # Use actual context data where available
        team_size = context.get('team_size', 5)
        startup_stage = context.get('startup_stage', 'unknown')
        current_arch = context.get('current_architecture', 'monolith')
        
        # Calculate metrics based on context
        metrics_count = 3 if startup_stage == 'early' else 8  # Early startups have fewer metrics
        data_quality = 0.4 if team_size <= 3 else 0.7  # Small teams have less instrumentation
        
        # Context-specific key metrics
        if current_arch == 'monolith':
            key_metric = 85.0  # Monoliths often have good performance initially
        else:
            key_metric = 65.0  # Microservices have complexity overhead
        
        quality_issues = []
        if team_size <= 3:
            quality_issues.append("limited instrumentation")
        if startup_stage == 'early':
            quality_issues.append("insufficient historical data")
        if data_quality < 0.5:
            quality_issues.append("incomplete data")
        
        return {
            'data_points': metrics_count,
            'data_quality': data_quality,
            'key_metric': key_metric,
            'quality_issues': ', '.join(quality_issues) if quality_issues else 'none',
            'statistical_significance': data_quality > 0.7 and metrics_count > 30
        }
    
    def _identify_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify patterns in data"""
        patterns = {
            'anomalies': context.get('anomalies_detected', False),
            'anomaly_description': context.get('anomaly_description', 'unusual spike in errors'),
            'negative_trend': context.get('negative_trend', False),
            'trending_metric': context.get('trending_metric', 'response time'),
            'positive_correlation': context.get('correlation_found', False),
            'correlation_insight': context.get('correlation_insight', 'code quality improves with test coverage')
        }
        return patterns
    
    def _calculate_projections(self, metrics: Dict[str, Any], patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate projections based on data"""
        trend = 'stable'
        if patterns.get('negative_trend'):
            trend = 'declining'
        elif metrics['key_metric'] > 80:
            trend = 'improving'
        
        improvement_potential = 0.2  # Default
        if metrics['data_quality'] > 0.7:
            improvement_potential = 0.4
        
        return {
            'trend': trend,
            'improvement_potential': improvement_potential,
            'confidence_interval': '95%' if metrics['statistical_significance'] else 'insufficient data'
        }
    
    def _compare_benchmarks(self, metrics: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Compare against benchmarks"""
        benchmark = context.get('industry_benchmark', 70)
        current = metrics['key_metric']
        
        performance = current / benchmark if benchmark > 0 else 0.5
        
        return {
            'performance': min(1.0, performance),
            'vs_benchmark': 'above' if performance > 1 else 'below',
            'gap': abs(current - benchmark)
        }
    
    def _get_data_recommendation(self, metrics: Dict[str, Any], projections: Dict[str, Any]) -> str:
        """Generate data-based recommendation"""
        if projections['trend'] == 'improving':
            return f"Continue current approach, metrics show positive trajectory"
        elif projections['trend'] == 'declining':
            return f"Intervention needed, metrics declining"
        else:
            return f"Monitor closely, metrics stable at {metrics['key_metric']:.1f}"
    
    def _explain_analytical_thinking(self, metrics, patterns, projections) -> str:
        """Explain analytical reasoning"""
        reasoning = f"Analysis based on {metrics['data_points']} data points "
        reasoning += f"with {metrics['data_quality']:.0%} data quality. "
        
        if patterns['anomalies']:
            reasoning += f"Anomalies detected: {patterns['anomaly_description']}. "
        
        reasoning += f"Trend analysis shows {projections['trend']} trajectory "
        reasoning += f"with {projections['improvement_potential']*100:.0f}% improvement potential. "
        
        if metrics['statistical_significance']:
            reasoning += "Results are statistically significant."
        else:
            reasoning += "More data needed for statistical significance."
        
        return reasoning
    
    def _determine_analytical_priority(self, metrics: Dict[str, Any], patterns: Dict[str, Any]) -> PersonaPriority:
        """Determine priority based on data analysis"""
        if patterns.get('anomalies') and metrics['data_quality'] > 0.7:
            return PersonaPriority.HIGH
        if metrics['data_quality'] < 0.3:
            return PersonaPriority.LOW
        if patterns.get('negative_trend'):
            return PersonaPriority.HIGH
        return PersonaPriority.MEDIUM