"""
Knowledge Graph and Memory System Integration

Connects the Optimus knowledge graph with the memory system and orchestrator
to enable cross-project intelligence, pattern discovery, and enhanced decision support.
"""

import asyncio
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass

from .optimus_knowledge_graph import OptimusKnowledgeGraph, ProjectInsight, TechnologyMapping
from .graph_analytics import GraphAnalytics, PatternDetection, CommunityAnalysis
from .memory_integration import get_optimized_memory_system
from ..models.knowledge_graph import NodeTypeEnum, EdgeTypeEnum
from ..models.memory import DeliberationMemory, PersonaResponseMemory


@dataclass
class KnowledgeEnhancedContext:
    """Context enriched with knowledge graph insights"""
    original_context: Dict[str, Any]
    related_projects: List[str]
    similar_decisions: List[str]
    technology_recommendations: List[str]
    expertise_mapping: Dict[str, List[str]]
    cross_project_patterns: List[str]
    confidence_score: float


@dataclass
class LearningInsight:
    """Insight extracted from deliberation for knowledge graph"""
    insight_type: str
    title: str
    description: str
    entities: List[str]
    relationships: List[Tuple[str, str, str]]  # (source, relation, target)
    confidence: float
    source_deliberation_id: str


class KnowledgeMemoryIntegrator:
    """
    Integration layer that connects knowledge graph with memory system
    to provide enhanced context and continuous learning capabilities.
    """
    
    def __init__(self, db_manager=None):
        self.kg = OptimusKnowledgeGraph(db_manager)
        self.analytics = GraphAnalytics(self.kg)
        self.memory_system = get_optimized_memory_system()
        
        # Learning configuration
        self.auto_learning_enabled = True
        self.insight_threshold = 0.6
        self.pattern_detection_interval = 24 * 60 * 60  # 24 hours in seconds
        
    async def initialize(self):
        """Initialize the integrated system"""
        await self.kg.initialize()
        await self.memory_system.initialize()
    
    async def enhance_query_context(self, 
                                   query: str,
                                   context: Dict[str, Any]) -> KnowledgeEnhancedContext:
        """
        Enhance query context with knowledge graph insights
        
        Args:
            query: The deliberation query
            context: Original context from the request
            
        Returns:
            Enhanced context with related knowledge and recommendations
        """
        
        # Extract entities and concepts from query and context
        entities = await self._extract_entities(query, context)
        
        # Find related projects based on entities
        related_projects = []
        technology_recommendations = []
        
        for entity in entities:
            if entity.get('type') in ['technology', 'skill', 'concept']:
                # Find projects using this technology/skill
                project_insights = await self.kg.find_related_projects(entity['name'])
                for insight in project_insights:
                    related_projects.extend(insight.related_projects)
                    technology_recommendations.extend(insight.recommendations)
        
        # Find similar past decisions
        similar_decisions = await self._find_similar_decisions(query, context)
        
        # Get expertise mapping for relevant personas
        expertise_mapping = await self.kg.calculate_persona_expertise()
        
        # Identify cross-project patterns
        cross_project_patterns = await self._identify_patterns_for_query(query, entities)
        
        # Calculate confidence score
        confidence_score = self._calculate_context_confidence(
            related_projects, similar_decisions, technology_recommendations
        )
        
        return KnowledgeEnhancedContext(
            original_context=context,
            related_projects=list(set(related_projects)),
            similar_decisions=similar_decisions,
            technology_recommendations=list(set(technology_recommendations)),
            expertise_mapping=expertise_mapping,
            cross_project_patterns=cross_project_patterns,
            confidence_score=confidence_score
        )
    
    async def learn_from_deliberation(self, 
                                    deliberation_result: DeliberationMemory,
                                    persona_responses: List[PersonaResponseMemory]) -> List[LearningInsight]:
        """
        Extract learning insights from a completed deliberation
        and update the knowledge graph accordingly.
        """
        
        if not self.auto_learning_enabled:
            return []
        
        insights = []
        
        try:
            # Extract decision node
            decision_insight = await self._extract_decision_insight(
                deliberation_result, persona_responses
            )
            if decision_insight:
                insights.append(decision_insight)
            
            # Extract technology insights
            tech_insights = await self._extract_technology_insights(
                deliberation_result, persona_responses
            )
            insights.extend(tech_insights)
            
            # Extract persona expertise insights
            expertise_insights = await self._extract_expertise_insights(
                persona_responses
            )
            insights.extend(expertise_insights)
            
            # Extract relationship insights
            relationship_insights = await self._extract_relationship_insights(
                deliberation_result, persona_responses
            )
            insights.extend(relationship_insights)
            
            # Apply insights to knowledge graph
            for insight in insights:
                if insight.confidence >= self.insight_threshold:
                    await self._apply_insight_to_graph(insight)
            
            return insights
            
        except Exception as e:
            print(f"Error learning from deliberation: {e}")
            return []
    
    async def _extract_entities(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities and concepts from query and context"""
        entities = []
        
        # Simple entity extraction - could be enhanced with NLP
        text_to_analyze = f"{query} {' '.join(str(v) for v in context.values())}"
        text_lower = text_to_analyze.lower()
        
        # Extract technology entities
        tech_keywords = [
            'python', 'javascript', 'react', 'nodejs', 'docker', 'kubernetes',
            'postgresql', 'redis', 'mongodb', 'aws', 'azure', 'gcp',
            'django', 'flask', 'fastapi', 'express', 'vue', 'angular',
            'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy'
        ]
        
        for tech in tech_keywords:
            if tech in text_lower:
                entities.append({
                    'name': tech,
                    'type': 'technology',
                    'confidence': 0.8
                })
        
        # Extract project entities (from context)
        if 'project' in context:
            entities.append({
                'name': str(context['project']),
                'type': 'project',
                'confidence': 0.9
            })
        
        # Extract skill entities
        skill_keywords = [
            'development', 'design', 'architecture', 'testing', 'deployment',
            'security', 'performance', 'optimization', 'scalability', 'monitoring'
        ]
        
        for skill in skill_keywords:
            if skill in text_lower:
                entities.append({
                    'name': skill,
                    'type': 'skill',
                    'confidence': 0.6
                })
        
        return entities
    
    async def _find_similar_decisions(self, query: str, context: Dict[str, Any]) -> List[str]:
        """Find similar past decisions from memory system"""
        
        try:
            # Query memory system for similar deliberations
            similar_memories = await self.memory_system.search_similar_queries(
                query, limit=5, similarity_threshold=0.7
            )
            
            return [str(memory.id) for memory in similar_memories]
            
        except Exception as e:
            print(f"Error finding similar decisions: {e}")
            return []
    
    async def _identify_patterns_for_query(self, 
                                         query: str, 
                                         entities: List[Dict[str, Any]]) -> List[str]:
        """Identify relevant patterns from graph analytics for the query"""
        
        try:
            # Get comprehensive pattern analysis
            patterns = await self.analytics.detect_patterns()
            
            relevant_patterns = []
            query_lower = query.lower()
            
            for pattern in patterns:
                # Check if pattern is relevant to query entities or content
                relevance_score = 0
                
                # Check entity relevance
                for entity in entities:
                    if entity['name'].lower() in pattern.description.lower():
                        relevance_score += entity['confidence']
                
                # Check query keyword relevance
                pattern_keywords = pattern.description.lower().split()
                query_keywords = query_lower.split()
                
                common_keywords = set(pattern_keywords) & set(query_keywords)
                relevance_score += len(common_keywords) * 0.1
                
                if relevance_score > 0.3:
                    relevant_patterns.append(pattern.pattern_name)
            
            return relevant_patterns
            
        except Exception as e:
            print(f"Error identifying patterns: {e}")
            return []
    
    def _calculate_context_confidence(self, 
                                    related_projects: List[str],
                                    similar_decisions: List[str],
                                    tech_recommendations: List[str]) -> float:
        """Calculate confidence score for enhanced context"""
        
        # Base confidence
        confidence = 0.5
        
        # Boost confidence based on available information
        confidence += min(len(related_projects) * 0.1, 0.3)
        confidence += min(len(similar_decisions) * 0.15, 0.3)
        confidence += min(len(tech_recommendations) * 0.05, 0.2)
        
        return min(confidence, 1.0)
    
    async def _extract_decision_insight(self, 
                                      deliberation: DeliberationMemory,
                                      responses: List[PersonaResponseMemory]) -> Optional[LearningInsight]:
        """Extract decision-making insight from deliberation"""
        
        try:
            # Create decision node insight
            decision_title = f"Decision: {deliberation.query[:50]}..."
            
            # Extract entities from decision context
            entities = []
            relationships = []
            
            # Add decision node
            entities.append(decision_title)
            
            # Connect to personas that participated
            for response in responses:
                relationships.append((
                    response.persona_name,
                    "influences",
                    decision_title
                ))
            
            # Extract context entities
            if deliberation.context:
                for key, value in deliberation.context.items():
                    if isinstance(value, str) and len(value) < 100:
                        entities.append(value)
                        relationships.append((
                            value,
                            "relates_to",
                            decision_title
                        ))
            
            return LearningInsight(
                insight_type="decision_making",
                title=f"Decision Pattern: {deliberation.topic or 'General'}",
                description=f"Decision made with {len(responses)} personas, confidence {deliberation.consensus_confidence}",
                entities=entities,
                relationships=relationships,
                confidence=deliberation.consensus_confidence,
                source_deliberation_id=str(deliberation.id)
            )
            
        except Exception as e:
            print(f"Error extracting decision insight: {e}")
            return None
    
    async def _extract_technology_insights(self, 
                                         deliberation: DeliberationMemory,
                                         responses: List[PersonaResponseMemory]) -> List[LearningInsight]:
        """Extract technology usage insights from deliberation"""
        
        insights = []
        
        try:
            # Look for technology mentions in responses
            tech_mentions = {}
            
            for response in responses:
                text = f"{response.response} {response.reasoning}"
                text_lower = text.lower()
                
                # Simple technology detection
                technologies = ['python', 'javascript', 'react', 'docker', 'kubernetes']
                for tech in technologies:
                    if tech in text_lower:
                        tech_mentions[tech] = tech_mentions.get(tech, 0) + 1
            
            # Create insights for frequently mentioned technologies
            for tech, count in tech_mentions.items():
                if count >= 2:  # Mentioned by multiple personas
                    insight = LearningInsight(
                        insight_type="technology_usage",
                        title=f"Technology Discussion: {tech}",
                        description=f"{tech} mentioned by {count} personas in decision context",
                        entities=[tech, deliberation.topic or "decision"],
                        relationships=[(deliberation.topic or "decision", "uses", tech)],
                        confidence=min(count / len(responses), 1.0),
                        source_deliberation_id=str(deliberation.id)
                    )
                    insights.append(insight)
            
            return insights
            
        except Exception as e:
            print(f"Error extracting technology insights: {e}")
            return []
    
    async def _extract_expertise_insights(self, 
                                        responses: List[PersonaResponseMemory]) -> List[LearningInsight]:
        """Extract persona expertise insights from responses"""
        
        insights = []
        
        try:
            for response in responses:
                # Analyze tools used and confidence level
                if response.tools_used and response.confidence > 0.7:
                    for tool in response.tools_used:
                        insight = LearningInsight(
                            insight_type="expertise_mapping",
                            title=f"Expertise: {response.persona_name} uses {tool}",
                            description=f"{response.persona_name} effectively used {tool} with confidence {response.confidence}",
                            entities=[response.persona_name, tool],
                            relationships=[(response.persona_name, "uses", tool)],
                            confidence=response.confidence,
                            source_deliberation_id=str(response.deliberation_id)
                        )
                        insights.append(insight)
            
            return insights
            
        except Exception as e:
            print(f"Error extracting expertise insights: {e}")
            return []
    
    async def _extract_relationship_insights(self, 
                                           deliberation: DeliberationMemory,
                                           responses: List[PersonaResponseMemory]) -> List[LearningInsight]:
        """Extract relationship insights between concepts"""
        
        insights = []
        
        try:
            # Analyze agreement patterns between personas
            high_agreement_pairs = []
            
            for i, resp1 in enumerate(responses):
                for resp2 in responses[i+1:]:
                    # Simple agreement detection based on confidence similarity
                    conf_diff = abs(resp1.confidence - resp2.confidence)
                    if conf_diff < 0.2:  # Similar confidence levels
                        high_agreement_pairs.append((resp1.persona_name, resp2.persona_name))
            
            # Create insights for persona collaboration patterns
            for persona1, persona2 in high_agreement_pairs:
                insight = LearningInsight(
                    insight_type="collaboration_pattern",
                    title=f"Collaboration: {persona1} & {persona2}",
                    description=f"{persona1} and {persona2} showed high agreement in decision",
                    entities=[persona1, persona2],
                    relationships=[(persona1, "collaborates_with", persona2)],
                    confidence=0.7,
                    source_deliberation_id=str(deliberation.id)
                )
                insights.append(insight)
            
            return insights
            
        except Exception as e:
            print(f"Error extracting relationship insights: {e}")
            return []
    
    async def _apply_insight_to_graph(self, insight: LearningInsight):
        """Apply a learning insight to the knowledge graph"""
        
        try:
            # Create nodes for entities
            nodes = {}
            
            for entity in insight.entities:
                # Determine node type
                node_type = self._determine_node_type(entity, insight.insight_type)
                
                node = await self.kg.add_node(
                    name=entity,
                    node_type=node_type,
                    attributes={
                        "source": "deliberation_learning",
                        "insight_type": insight.insight_type,
                        "source_deliberation": insight.source_deliberation_id,
                        "learned_at": datetime.now().isoformat()
                    },
                    importance=insight.confidence
                )
                
                nodes[entity] = node
            
            # Create edges for relationships
            for source, relation, target in insight.relationships:
                if source in nodes and target in nodes:
                    edge_type = self._determine_edge_type(relation)
                    
                    await self.kg.add_edge(
                        source_id=nodes[source].id,
                        target_id=nodes[target].id,
                        edge_type=edge_type,
                        weight=insight.confidence,
                        confidence=insight.confidence,
                        attributes={
                            "source": "deliberation_learning",
                            "insight_type": insight.insight_type,
                            "learned_at": datetime.now().isoformat()
                        }
                    )
            
        except Exception as e:
            print(f"Error applying insight to graph: {e}")
    
    def _determine_node_type(self, entity: str, insight_type: str) -> NodeTypeEnum:
        """Determine appropriate node type for an entity"""
        
        entity_lower = entity.lower()
        
        # Technology nodes
        tech_indicators = ['python', 'javascript', 'react', 'docker', 'kubernetes', 'api', 'database']
        if any(tech in entity_lower for tech in tech_indicators):
            return NodeTypeEnum.TECHNOLOGY
        
        # Persona nodes
        persona_indicators = ['analyst', 'strategist', 'guardian', 'innovator', 'pragmatist']
        if any(persona in entity_lower for persona in persona_indicators):
            return NodeTypeEnum.PERSONA
        
        # Decision nodes
        if insight_type == "decision_making":
            return NodeTypeEnum.DECISION
        
        # Skill nodes
        skill_indicators = ['development', 'testing', 'design', 'analysis', 'management']
        if any(skill in entity_lower for skill in skill_indicators):
            return NodeTypeEnum.SKILL
        
        # Default to concept
        return NodeTypeEnum.CONCEPT
    
    def _determine_edge_type(self, relation: str) -> EdgeTypeEnum:
        """Determine appropriate edge type for a relationship"""
        
        relation_mapping = {
            "uses": EdgeTypeEnum.USES,
            "influences": EdgeTypeEnum.INFLUENCES,
            "relates_to": EdgeTypeEnum.RELATES_TO,
            "depends_on": EdgeTypeEnum.DEPENDS_ON,
            "supports": EdgeTypeEnum.SUPPORTS,
            "collaborates_with": EdgeTypeEnum.SUPPORTS,
            "solved_by": EdgeTypeEnum.SOLVED_BY,
            "recommends": EdgeTypeEnum.RECOMMENDS
        }
        
        return relation_mapping.get(relation, EdgeTypeEnum.RELATES_TO)
    
    async def get_deliberation_insights(self, 
                                      query: str,
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive insights for a deliberation request"""
        
        try:
            # Enhance context
            enhanced_context = await self.enhance_query_context(query, context)
            
            # Get cross-project insights
            project_insights = await self.kg.get_cross_project_insights(limit=10)
            
            # Get analytics insights
            comprehensive_analysis = await self.analytics.get_comprehensive_analysis()
            
            return {
                "enhanced_context": enhanced_context.__dict__,
                "project_insights": [insight.__dict__ for insight in project_insights],
                "analytics_summary": {
                    "total_communities": len(comprehensive_analysis.get("community_analysis", {}).get("communities", [])),
                    "top_patterns": comprehensive_analysis.get("pattern_detection", {}).get("high_confidence_patterns", []),
                    "trend_summary": comprehensive_analysis.get("trend_analysis", {}).get("trends_identified", 0)
                },
                "recommendations": comprehensive_analysis.get("recommendations", [])
            }
            
        except Exception as e:
            print(f"Error getting deliberation insights: {e}")
            return {"error": str(e)}
    
    async def update_project_knowledge(self, 
                                     project_name: str,
                                     project_data: Dict[str, Any]):
        """Update knowledge graph with project information"""
        
        try:
            technologies = project_data.get('technologies', [])
            project_path = project_data.get('path', '')
            status = project_data.get('status', 'active')
            
            # Add project node and relationships
            await self.kg.add_project_node(
                project_name=project_name,
                project_path=project_path,
                technologies=technologies,
                status=status,
                attributes=project_data
            )
            
        except Exception as e:
            print(f"Error updating project knowledge: {e}")
    
    async def get_technology_insights(self, technology: str) -> Dict[str, Any]:
        """Get insights about a specific technology"""
        
        try:
            # Find related projects
            related_projects = await self.kg.find_related_projects(technology)
            
            # Get technology patterns
            tech_patterns = await self.kg.discover_technology_patterns()
            relevant_patterns = [p for p in tech_patterns if p.technology.lower() == technology.lower()]
            
            return {
                "technology": technology,
                "related_projects": [insight.__dict__ for insight in related_projects],
                "usage_patterns": [pattern.__dict__ for pattern in relevant_patterns],
                "recommendations": []
            }
            
        except Exception as e:
            print(f"Error getting technology insights: {e}")
            return {"error": str(e)}


# Global instance for system-wide access
_knowledge_memory_integrator = None


def get_knowledge_memory_integrator() -> KnowledgeMemoryIntegrator:
    """Get the global knowledge-memory integrator instance"""
    global _knowledge_memory_integrator
    if _knowledge_memory_integrator is None:
        _knowledge_memory_integrator = KnowledgeMemoryIntegrator()
    return _knowledge_memory_integrator