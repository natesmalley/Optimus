"""
Troubleshooting Integration Service
==================================

Integrates the Smart Troubleshooting Engine with Optimus's existing
memory system and knowledge graph to provide intelligent, context-aware
error resolution that learns from past decisions and project relationships.

Key Features:
- Memory integration for storing troubleshooting patterns
- Knowledge graph integration for cross-project learning
- Context-aware solution recommendations
- Learning from Council of Minds deliberations
- Pattern recognition across project ecosystems
- Intelligent solution ranking based on project history
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ..models import Project, ErrorPattern, Solution, FixAttempt
from ..models.troubleshooting import TroubleshootingSession
from ..council.memory_integration import MemoryIntegration
from ..council.knowledge_graph_integration import KnowledgeGraphIntegration
from .troubleshooting_engine import TroubleshootingEngine, ErrorAnalysis, SolutionCandidate
from .runtime_monitor import RuntimeMonitor

logger = logging.getLogger("optimus.troubleshooting_integration")


@dataclass
class TroubleshootingContext:
    """Rich context for troubleshooting decisions."""
    project_id: str
    project_name: str
    project_type: str
    tech_stack: Dict[str, Any]
    recent_changes: List[str]
    similar_projects: List[str]
    team_expertise: List[str]
    historical_patterns: List[str]
    current_system_state: Dict[str, Any]
    related_issues: List[str]


@dataclass
class LearningPattern:
    """Pattern learned from troubleshooting activities."""
    pattern_id: str
    pattern_type: str  # error_solution, context_dependency, team_preference
    conditions: Dict[str, Any]
    outcomes: Dict[str, Any]
    confidence: float
    usage_count: int
    success_rate: float
    last_used: datetime
    metadata: Dict[str, Any]


class TroubleshootingIntegrationService:
    """
    Service that integrates troubleshooting with memory and knowledge systems.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        memory_integration: MemoryIntegration,
        kg_integration: KnowledgeGraphIntegration,
        troubleshooting_engine: TroubleshootingEngine,
        runtime_monitor: Optional[RuntimeMonitor] = None
    ):
        self.session = session
        self.memory = memory_integration
        self.kg = kg_integration
        self.engine = troubleshooting_engine
        self.runtime_monitor = runtime_monitor
        
        # Learning configuration
        self.learning_weights = {
            'solution_success': 0.3,
            'team_preference': 0.2,
            'project_similarity': 0.2,
            'temporal_relevance': 0.15,
            'complexity_match': 0.15
        }
        
        # Context cache for performance
        self.context_cache: Dict[str, TroubleshootingContext] = {}
        self.cache_ttl = timedelta(minutes=30)
    
    async def analyze_error_with_context(
        self,
        error_message: str,
        project_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ErrorAnalysis, TroubleshootingContext]:
        """
        Analyze an error with full project and historical context.
        
        Args:
            error_message: The error message to analyze
            project_id: ID of the project where error occurred
            additional_context: Additional context information
        
        Returns:
            Tuple of (error analysis, troubleshooting context)
        """
        try:
            logger.info(f"Analyzing error with context for project {project_id}")
            
            # Build troubleshooting context
            context = await self._build_troubleshooting_context(project_id)
            
            # Enhance base error analysis with context
            base_context = {
                "project_id": project_id,
                "project_name": context.project_name,
                "tech_stack": context.tech_stack,
                "language": self._extract_primary_language(context.tech_stack),
                "framework": self._extract_primary_framework(context.tech_stack),
                **(additional_context or {})
            }
            
            # Analyze error with enhanced context
            analysis = await self.engine.analyze_error(error_message, base_context)
            
            # Enhance analysis with memory insights
            await self._enhance_analysis_with_memory(analysis, context)
            
            # Store analysis context in knowledge graph
            await self._store_analysis_in_knowledge_graph(analysis, context)
            
            return analysis, context
            
        except Exception as e:
            logger.error(f"Error analyzing error with context: {e}", exc_info=True)
            # Return basic analysis if context enrichment fails
            basic_analysis = await self.engine.analyze_error(error_message)
            basic_context = TroubleshootingContext(
                project_id=project_id,
                project_name="Unknown",
                project_type="Unknown",
                tech_stack={},
                recent_changes=[],
                similar_projects=[],
                team_expertise=[],
                historical_patterns=[],
                current_system_state={},
                related_issues=[]
            )
            return basic_analysis, basic_context
    
    async def find_context_aware_solutions(
        self,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext
    ) -> List[SolutionCandidate]:
        """
        Find solutions enhanced with project context and historical learning.
        
        Args:
            analysis: The error analysis
            context: The troubleshooting context
        
        Returns:
            List of context-aware solution candidates
        """
        try:
            # Get base solutions from engine
            base_solutions = await self.engine.find_solutions(analysis, asdict(context))
            
            # Enhance solutions with memory and knowledge graph insights
            enhanced_solutions = []
            
            for solution in base_solutions:
                enhanced_solution = await self._enhance_solution_with_context(
                    solution, analysis, context
                )
                enhanced_solutions.append(enhanced_solution)
            
            # Find additional solutions from memory patterns
            memory_solutions = await self._find_solutions_from_memory(analysis, context)
            enhanced_solutions.extend(memory_solutions)
            
            # Find solutions from similar projects via knowledge graph
            kg_solutions = await self._find_solutions_from_knowledge_graph(analysis, context)
            enhanced_solutions.extend(kg_solutions)
            
            # Re-rank solutions with context-aware scoring
            ranked_solutions = await self._rank_solutions_with_context(
                enhanced_solutions, analysis, context
            )
            
            logger.info(f"Found {len(ranked_solutions)} context-aware solutions for {analysis.error_type}")
            
            return ranked_solutions
            
        except Exception as e:
            logger.error(f"Error finding context-aware solutions: {e}", exc_info=True)
            return await self.engine.find_solutions(analysis)
    
    async def learn_from_troubleshooting_session(
        self,
        session_id: str,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext,
        solutions_tried: List[SolutionCandidate],
        successful_solution: Optional[SolutionCandidate],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Learn from a complete troubleshooting session.
        
        Args:
            session_id: ID of the troubleshooting session
            analysis: The error analysis
            context: The troubleshooting context
            solutions_tried: All solutions that were attempted
            successful_solution: The solution that worked (if any)
            user_feedback: User feedback on the troubleshooting process
        """
        try:
            logger.info(f"Learning from troubleshooting session: {session_id}")
            
            # Create learning patterns
            patterns = await self._extract_learning_patterns(
                analysis, context, solutions_tried, successful_solution, user_feedback
            )
            
            # Store patterns in memory
            for pattern in patterns:
                await self._store_learning_pattern(pattern)
            
            # Update knowledge graph relationships
            await self._update_knowledge_graph_from_session(
                analysis, context, successful_solution
            )
            
            # Store session summary for future reference
            await self._store_session_summary(
                session_id, analysis, context, solutions_tried, successful_solution, user_feedback
            )
            
            logger.info(f"Learning completed for session {session_id}: {len(patterns)} patterns extracted")
            
        except Exception as e:
            logger.error(f"Error learning from troubleshooting session: {e}", exc_info=True)
    
    async def get_predictive_insights(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Get predictive insights about potential issues for a project.
        
        Args:
            project_id: ID of the project to analyze
        
        Returns:
            Dictionary containing predictive insights
        """
        try:
            context = await self._build_troubleshooting_context(project_id)
            
            # Get runtime metrics for prediction
            system_metrics = {}
            if self.runtime_monitor:
                runtime_status = await self.runtime_monitor.get_project_runtime_status(project_id)
                if runtime_status.get("processes"):
                    # Extract metrics from processes
                    total_cpu = sum(p.get("cpu_percent", 0) for p in runtime_status["processes"])
                    total_memory = sum(p.get("memory_percent", 0) for p in runtime_status["processes"])
                    system_metrics = {
                        "cpu_usage": total_cpu,
                        "memory_usage": total_memory,
                        "process_count": len(runtime_status["processes"])
                    }
            
            # Predict potential issues
            potential_issues = await self.engine.predict_issues(system_metrics)
            
            # Enhance predictions with memory insights
            memory_insights = await self._get_memory_insights_for_prediction(context)
            
            # Get knowledge graph insights
            kg_insights = await self._get_kg_insights_for_prediction(context)
            
            # Historical pattern analysis
            historical_patterns = await self._analyze_historical_patterns(project_id)
            
            return {
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "potential_issues": [asdict(issue) for issue in potential_issues],
                "memory_insights": memory_insights,
                "knowledge_graph_insights": kg_insights,
                "historical_patterns": historical_patterns,
                "recommendations": await self._generate_proactive_recommendations(
                    context, potential_issues, memory_insights, kg_insights
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting predictive insights: {e}", exc_info=True)
            return {
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def _build_troubleshooting_context(self, project_id: str) -> TroubleshootingContext:
        """Build comprehensive troubleshooting context for a project."""
        # Check cache first
        cache_key = f"context_{project_id}"
        if cache_key in self.context_cache:
            cached_context = self.context_cache[cache_key]
            if datetime.now() - getattr(cached_context, '_cached_at', datetime.min) < self.cache_ttl:
                return cached_context
        
        try:
            # Get project information
            stmt = select(Project).where(Project.id == uuid.UUID(project_id))
            result = await self.session.execute(stmt)
            project = result.scalars().first()
            
            if not project:
                raise ValueError(f"Project not found: {project_id}")
            
            # Get recent error patterns
            recent_patterns_stmt = select(ErrorPattern).where(
                and_(
                    ErrorPattern.project_id == uuid.UUID(project_id),
                    ErrorPattern.last_seen > datetime.utcnow() - timedelta(days=30)
                )
            ).order_by(ErrorPattern.last_seen.desc()).limit(10)
            
            result = await self.session.execute(recent_patterns_stmt)
            recent_patterns = result.scalars().all()
            
            # Get similar projects from knowledge graph
            similar_projects = await self._get_similar_projects(project)
            
            # Get team expertise from memory
            team_expertise = await self._get_team_expertise(project_id)
            
            # Get recent changes (simplified - could integrate with git)
            recent_changes = await self._get_recent_changes(project_id)
            
            # Get current system state
            current_state = {}
            if self.runtime_monitor:
                current_state = await self.runtime_monitor.get_project_runtime_status(project_id)
            
            # Get related issues
            related_issues = [pattern.error_hash for pattern in recent_patterns]
            
            context = TroubleshootingContext(
                project_id=project_id,
                project_name=project.name,
                project_type=self._determine_project_type(project.tech_stack),
                tech_stack=project.tech_stack or {},
                recent_changes=recent_changes,
                similar_projects=similar_projects,
                team_expertise=team_expertise,
                historical_patterns=[pattern.error_type for pattern in recent_patterns],
                current_system_state=current_state,
                related_issues=related_issues
            )
            
            # Cache the context
            setattr(context, '_cached_at', datetime.now())
            self.context_cache[cache_key] = context
            
            return context
            
        except Exception as e:
            logger.error(f"Error building troubleshooting context: {e}")
            # Return minimal context
            return TroubleshootingContext(
                project_id=project_id,
                project_name="Unknown",
                project_type="Unknown",
                tech_stack={},
                recent_changes=[],
                similar_projects=[],
                team_expertise=[],
                historical_patterns=[],
                current_system_state={},
                related_issues=[]
            )
    
    def _extract_primary_language(self, tech_stack: Dict[str, Any]) -> Optional[str]:
        """Extract primary programming language from tech stack."""
        if not tech_stack:
            return None
        
        # Look for explicit language specification
        if "language" in tech_stack:
            return tech_stack["language"]
        
        # Infer from framework
        framework_language_map = {
            "django": "python",
            "flask": "python",
            "fastapi": "python",
            "react": "javascript",
            "vue": "javascript",
            "angular": "javascript",
            "express": "javascript",
            "spring": "java",
            "rails": "ruby",
            "laravel": "php"
        }
        
        framework = tech_stack.get("framework", "").lower()
        return framework_language_map.get(framework)
    
    def _extract_primary_framework(self, tech_stack: Dict[str, Any]) -> Optional[str]:
        """Extract primary framework from tech stack."""
        if not tech_stack:
            return None
        
        return tech_stack.get("framework")
    
    def _determine_project_type(self, tech_stack: Dict[str, Any]) -> str:
        """Determine the type of project based on tech stack."""
        if not tech_stack:
            return "unknown"
        
        # Simple heuristics for project type detection
        framework = tech_stack.get("framework", "").lower()
        language = tech_stack.get("language", "").lower()
        
        if framework in ["react", "vue", "angular"]:
            return "frontend"
        elif framework in ["django", "flask", "fastapi", "express", "spring"]:
            return "backend"
        elif framework in ["react-native", "flutter"]:
            return "mobile"
        elif language in ["python"] and "jupyter" in str(tech_stack):
            return "data_science"
        elif language in ["rust", "go", "c", "cpp"]:
            return "systems"
        else:
            return "web_application"
    
    async def _enhance_analysis_with_memory(
        self,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext
    ) -> None:
        """Enhance error analysis with insights from memory system."""
        try:
            # Get related memories
            memory_key = f"error_analysis_{analysis.error_type}_{context.project_type}"
            memories = await self.memory.recall_context(memory_key)
            
            if memories:
                # Extract insights from memories
                similar_contexts = []
                for memory in memories:
                    if isinstance(memory, dict) and memory.get("type") == "error_analysis":
                        similar_contexts.append(memory.get("context", {}))
                
                # Update analysis confidence based on historical data
                if similar_contexts:
                    historical_confidence = sum(
                        ctx.get("confidence", 0.5) for ctx in similar_contexts
                    ) / len(similar_contexts)
                    
                    # Blend historical confidence with current confidence
                    analysis.confidence = (analysis.confidence + historical_confidence) / 2
            
        except Exception as e:
            logger.debug(f"Error enhancing analysis with memory: {e}")
    
    async def _store_analysis_in_knowledge_graph(
        self,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext
    ) -> None:
        """Store error analysis in the knowledge graph."""
        try:
            # Create nodes and relationships for the error
            error_node_data = {
                "type": "error",
                "error_type": analysis.error_type,
                "severity": analysis.severity,
                "category": analysis.category,
                "language": analysis.language,
                "framework": analysis.framework,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            project_node_data = {
                "type": "project",
                "project_id": context.project_id,
                "project_name": context.project_name,
                "project_type": context.project_type
            }
            
            # Store in knowledge graph
            error_node_id = await self.kg.add_node("error", error_node_data)
            project_node_id = await self.kg.add_node("project", project_node_data)
            
            # Create relationship
            await self.kg.add_edge(
                project_node_id,
                error_node_id,
                "experienced_error",
                {"timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
        except Exception as e:
            logger.debug(f"Error storing analysis in knowledge graph: {e}")
    
    async def _enhance_solution_with_context(
        self,
        solution: SolutionCandidate,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext
    ) -> SolutionCandidate:
        """Enhance a solution candidate with context-specific information."""
        try:
            # Get historical success rate for this solution in similar contexts
            memory_key = f"solution_{solution.solution_id}_{context.project_type}"
            memories = await self.memory.recall_context(memory_key)
            
            historical_success_rate = solution.success_rate
            if memories:
                success_rates = [
                    memory.get("success_rate", 0.5) 
                    for memory in memories 
                    if isinstance(memory, dict) and "success_rate" in memory
                ]
                if success_rates:
                    historical_success_rate = sum(success_rates) / len(success_rates)
            
            # Adjust confidence based on context match
            context_confidence_boost = 0.0
            
            # Boost for language match
            if solution.metadata.get("language") == analysis.language:
                context_confidence_boost += 0.1
            
            # Boost for framework match
            if solution.metadata.get("framework") == analysis.framework:
                context_confidence_boost += 0.1
            
            # Boost for project type match
            if context.project_type in solution.metadata.get("project_types", []):
                context_confidence_boost += 0.05
            
            # Create enhanced solution
            enhanced_solution = SolutionCandidate(
                solution_id=solution.solution_id,
                title=solution.title,
                description=solution.description,
                confidence=min(1.0, solution.confidence + context_confidence_boost),
                success_rate=historical_success_rate,
                category=solution.category,
                fix_commands=solution.fix_commands,
                verification_commands=solution.verification_commands,
                rollback_commands=solution.rollback_commands,
                risk_level=solution.risk_level,
                requires_approval=solution.requires_approval,
                estimated_time_ms=solution.estimated_time_ms,
                prerequisites=solution.prerequisites,
                metadata={
                    **solution.metadata,
                    "context_enhanced": True,
                    "historical_success_rate": historical_success_rate,
                    "context_confidence_boost": context_confidence_boost
                }
            )
            
            return enhanced_solution
            
        except Exception as e:
            logger.debug(f"Error enhancing solution with context: {e}")
            return solution
    
    async def _find_solutions_from_memory(
        self,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext
    ) -> List[SolutionCandidate]:
        """Find solutions from memory patterns."""
        solutions = []
        
        try:
            # Search for similar error patterns in memory
            memory_key = f"successful_fixes_{analysis.error_type}"
            memories = await self.memory.recall_context(memory_key)
            
            for memory in memories:
                if isinstance(memory, dict) and memory.get("type") == "successful_fix":
                    # Convert memory to solution candidate
                    solution = SolutionCandidate(
                        solution_id=f"memory_{memory.get('id', uuid.uuid4())}",
                        title=f"Memory-based fix for {analysis.error_type}",
                        description=memory.get("description", "Solution from past success"),
                        confidence=memory.get("confidence", 0.6),
                        success_rate=memory.get("success_rate", 0.7),
                        category=analysis.category,
                        fix_commands=memory.get("commands", []),
                        verification_commands=memory.get("verification", []),
                        rollback_commands=memory.get("rollback", []),
                        risk_level="medium",
                        requires_approval=True,  # Memory solutions should be reviewed
                        estimated_time_ms=memory.get("execution_time_ms", 10000),
                        metadata={
                            "source": "memory",
                            "original_context": memory.get("context", {}),
                            "memory_id": memory.get("id")
                        }
                    )
                    solutions.append(solution)
            
        except Exception as e:
            logger.debug(f"Error finding solutions from memory: {e}")
        
        return solutions
    
    async def _find_solutions_from_knowledge_graph(
        self,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext
    ) -> List[SolutionCandidate]:
        """Find solutions from knowledge graph patterns."""
        solutions = []
        
        try:
            # Find similar projects that had this error type
            similar_project_fixes = await self.kg.query_patterns(
                "project -> experienced_error -> error",
                {"error_type": analysis.error_type}
            )
            
            for fix_pattern in similar_project_fixes:
                if fix_pattern.get("solution_used"):
                    solution_data = fix_pattern["solution_used"]
                    
                    solution = SolutionCandidate(
                        solution_id=f"kg_{solution_data.get('id', uuid.uuid4())}",
                        title=f"Cross-project solution for {analysis.error_type}",
                        description=solution_data.get("description", "Solution from similar project"),
                        confidence=solution_data.get("confidence", 0.5),
                        success_rate=solution_data.get("success_rate", 0.6),
                        category=analysis.category,
                        fix_commands=solution_data.get("commands", []),
                        verification_commands=solution_data.get("verification", []),
                        rollback_commands=solution_data.get("rollback", []),
                        risk_level="medium",
                        requires_approval=True,  # Cross-project solutions should be reviewed
                        estimated_time_ms=solution_data.get("execution_time_ms", 15000),
                        metadata={
                            "source": "knowledge_graph",
                            "source_project": fix_pattern.get("project_name"),
                            "pattern_id": fix_pattern.get("id")
                        }
                    )
                    solutions.append(solution)
            
        except Exception as e:
            logger.debug(f"Error finding solutions from knowledge graph: {e}")
        
        return solutions
    
    async def _rank_solutions_with_context(
        self,
        solutions: List[SolutionCandidate],
        analysis: ErrorAnalysis,
        context: TroubleshootingContext
    ) -> List[SolutionCandidate]:
        """Rank solutions using context-aware scoring."""
        
        def calculate_context_score(solution: SolutionCandidate) -> float:
            score = solution.confidence
            
            # Team expertise bonus
            if solution.metadata.get("language") in context.team_expertise:
                score += 0.1
            
            # Similar project success bonus
            if any(proj in context.similar_projects for proj in solution.metadata.get("successful_projects", [])):
                score += 0.15
            
            # Historical pattern match bonus
            if solution.category in context.historical_patterns:
                score += 0.05
            
            # Recent success bonus
            last_success = solution.metadata.get("last_success_time")
            if last_success:
                try:
                    last_success_dt = datetime.fromisoformat(last_success)
                    days_ago = (datetime.now() - last_success_dt).days
                    if days_ago < 7:  # Last week
                        score += 0.1
                    elif days_ago < 30:  # Last month
                        score += 0.05
                except:
                    pass
            
            # Project type affinity
            if context.project_type in solution.metadata.get("preferred_project_types", []):
                score += 0.08
            
            return min(1.0, score)
        
        # Calculate scores and sort
        scored_solutions = [(solution, calculate_context_score(solution)) for solution in solutions]
        scored_solutions.sort(key=lambda x: x[1], reverse=True)
        
        return [solution for solution, _ in scored_solutions]
    
    async def _get_similar_projects(self, project: Project) -> List[str]:
        """Get similar projects from knowledge graph."""
        try:
            # Simple similarity based on tech stack
            similar_projects = []
            
            if project.tech_stack:
                language = project.tech_stack.get("language")
                framework = project.tech_stack.get("framework")
                
                # Find projects with similar tech stack
                stmt = select(Project.name).where(
                    and_(
                        Project.id != project.id,
                        Project.tech_stack.contains({"language": language}) if language else True,
                        Project.tech_stack.contains({"framework": framework}) if framework else True
                    )
                ).limit(5)
                
                result = await self.session.execute(stmt)
                similar_projects = [name for (name,) in result.fetchall()]
            
            return similar_projects
            
        except Exception as e:
            logger.debug(f"Error getting similar projects: {e}")
            return []
    
    async def _get_team_expertise(self, project_id: str) -> List[str]:
        """Get team expertise from memory system."""
        try:
            memory_key = f"team_expertise_{project_id}"
            memories = await self.memory.recall_context(memory_key)
            
            expertise = set()
            for memory in memories:
                if isinstance(memory, dict) and "expertise" in memory:
                    expertise.update(memory["expertise"])
            
            return list(expertise)
            
        except Exception as e:
            logger.debug(f"Error getting team expertise: {e}")
            return []
    
    async def _get_recent_changes(self, project_id: str) -> List[str]:
        """Get recent changes to the project."""
        try:
            # This would integrate with git or other version control
            # For now, return placeholder
            return [
                "Updated dependencies",
                "Modified configuration",
                "Added new feature"
            ]
            
        except Exception as e:
            logger.debug(f"Error getting recent changes: {e}")
            return []
    
    async def _extract_learning_patterns(
        self,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext,
        solutions_tried: List[SolutionCandidate],
        successful_solution: Optional[SolutionCandidate],
        user_feedback: Optional[Dict[str, Any]]
    ) -> List[LearningPattern]:
        """Extract learning patterns from a troubleshooting session."""
        patterns = []
        
        try:
            # Pattern: Error-Solution mapping
            if successful_solution:
                pattern = LearningPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type="error_solution",
                    conditions={
                        "error_type": analysis.error_type,
                        "language": analysis.language,
                        "framework": analysis.framework,
                        "project_type": context.project_type
                    },
                    outcomes={
                        "solution_id": successful_solution.solution_id,
                        "solution_category": successful_solution.category,
                        "execution_time_ms": successful_solution.estimated_time_ms
                    },
                    confidence=successful_solution.confidence,
                    usage_count=1,
                    success_rate=1.0,
                    last_used=datetime.now(timezone.utc),
                    metadata={
                        "session_context": asdict(context),
                        "user_feedback": user_feedback
                    }
                )
                patterns.append(pattern)
            
            # Pattern: Team preference
            if user_feedback and user_feedback.get("preferred_solution"):
                preferred_solution_id = user_feedback["preferred_solution"]
                preferred_solution = next(
                    (s for s in solutions_tried if s.solution_id == preferred_solution_id), 
                    None
                )
                
                if preferred_solution:
                    pattern = LearningPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type="team_preference",
                        conditions={
                            "project_id": context.project_id,
                            "error_category": analysis.category
                        },
                        outcomes={
                            "preferred_solution_type": preferred_solution.category,
                            "preferred_risk_level": preferred_solution.risk_level
                        },
                        confidence=0.8,
                        usage_count=1,
                        success_rate=1.0 if successful_solution and preferred_solution.solution_id == successful_solution.solution_id else 0.5,
                        last_used=datetime.now(timezone.utc),
                        metadata={"feedback": user_feedback}
                    )
                    patterns.append(pattern)
            
        except Exception as e:
            logger.debug(f"Error extracting learning patterns: {e}")
        
        return patterns
    
    async def _store_learning_pattern(self, pattern: LearningPattern) -> None:
        """Store a learning pattern in the memory system."""
        try:
            memory_key = f"learning_pattern_{pattern.pattern_type}_{pattern.pattern_id}"
            await self.memory.store_context(memory_key, asdict(pattern))
            
        except Exception as e:
            logger.debug(f"Error storing learning pattern: {e}")
    
    async def _update_knowledge_graph_from_session(
        self,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext,
        successful_solution: Optional[SolutionCandidate]
    ) -> None:
        """Update knowledge graph with session learnings."""
        try:
            if successful_solution:
                # Create solution node and link to error and project
                solution_node_data = {
                    "type": "solution",
                    "solution_id": successful_solution.solution_id,
                    "category": successful_solution.category,
                    "success_rate": successful_solution.success_rate,
                    "risk_level": successful_solution.risk_level
                }
                
                solution_node_id = await self.kg.add_node("solution", solution_node_data)
                
                # Find error node (should exist from earlier)
                error_nodes = await self.kg.find_nodes(
                    "error",
                    {"error_type": analysis.error_type, "language": analysis.language}
                )
                
                if error_nodes:
                    await self.kg.add_edge(
                        error_nodes[0]["id"],
                        solution_node_id,
                        "solved_by",
                        {"timestamp": datetime.now(timezone.utc).isoformat()}
                    )
            
        except Exception as e:
            logger.debug(f"Error updating knowledge graph from session: {e}")
    
    async def _store_session_summary(
        self,
        session_id: str,
        analysis: ErrorAnalysis,
        context: TroubleshootingContext,
        solutions_tried: List[SolutionCandidate],
        successful_solution: Optional[SolutionCandidate],
        user_feedback: Optional[Dict[str, Any]]
    ) -> None:
        """Store a summary of the troubleshooting session."""
        try:
            session_data = {
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_analysis": asdict(analysis),
                "context": asdict(context),
                "solutions_tried_count": len(solutions_tried),
                "successful_solution_id": successful_solution.solution_id if successful_solution else None,
                "user_satisfaction": user_feedback.get("satisfaction") if user_feedback else None,
                "resolution_time": user_feedback.get("resolution_time_minutes") if user_feedback else None
            }
            
            memory_key = f"troubleshooting_session_{session_id}"
            await self.memory.store_context(memory_key, session_data)
            
        except Exception as e:
            logger.debug(f"Error storing session summary: {e}")
    
    async def _get_memory_insights_for_prediction(self, context: TroubleshootingContext) -> Dict[str, Any]:
        """Get memory insights for predictive analysis."""
        try:
            insights = {
                "recurring_patterns": [],
                "seasonal_trends": {},
                "team_learning_curve": {}
            }
            
            # Get recurring error patterns
            pattern_key = f"recurring_errors_{context.project_id}"
            memories = await self.memory.recall_context(pattern_key)
            
            for memory in memories:
                if isinstance(memory, dict) and "pattern" in memory:
                    insights["recurring_patterns"].append(memory["pattern"])
            
            return insights
            
        except Exception as e:
            logger.debug(f"Error getting memory insights for prediction: {e}")
            return {}
    
    async def _get_kg_insights_for_prediction(self, context: TroubleshootingContext) -> Dict[str, Any]:
        """Get knowledge graph insights for predictive analysis."""
        try:
            insights = {
                "cross_project_patterns": [],
                "dependency_risks": {},
                "technology_stability": {}
            }
            
            # This would query the knowledge graph for patterns
            # Simplified for this implementation
            
            return insights
            
        except Exception as e:
            logger.debug(f"Error getting KG insights for prediction: {e}")
            return {}
    
    async def _analyze_historical_patterns(self, project_id: str) -> Dict[str, Any]:
        """Analyze historical error patterns for a project."""
        try:
            # Get error patterns from last 90 days
            since_date = datetime.utcnow() - timedelta(days=90)
            
            stmt = select(
                ErrorPattern.error_type,
                func.count(ErrorPattern.id).label('count'),
                func.sum(ErrorPattern.occurrence_count).label('total_occurrences'),
                func.max(ErrorPattern.last_seen).label('most_recent')
            ).where(
                and_(
                    ErrorPattern.project_id == uuid.UUID(project_id),
                    ErrorPattern.last_seen > since_date
                )
            ).group_by(ErrorPattern.error_type)
            
            result = await self.session.execute(stmt)
            patterns = result.fetchall()
            
            return {
                "total_unique_errors": len(patterns),
                "most_common_errors": [
                    {
                        "error_type": pattern.error_type,
                        "pattern_count": pattern.count,
                        "total_occurrences": pattern.total_occurrences,
                        "most_recent": pattern.most_recent.isoformat() if pattern.most_recent else None
                    }
                    for pattern in sorted(patterns, key=lambda x: x.total_occurrences, reverse=True)[:5]
                ],
                "error_frequency": sum(pattern.total_occurrences for pattern in patterns),
                "analysis_period_days": 90
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing historical patterns: {e}")
            return {}
    
    async def _generate_proactive_recommendations(
        self,
        context: TroubleshootingContext,
        potential_issues: List,
        memory_insights: Dict[str, Any],
        kg_insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate proactive recommendations based on all insights."""
        recommendations = []
        
        try:
            # Recommendations based on potential issues
            for issue in potential_issues:
                if issue.issue_type == "memory_leak":
                    recommendations.append({
                        "type": "proactive_action",
                        "priority": "high",
                        "title": "Monitor Memory Usage",
                        "description": "Set up memory monitoring and alerts",
                        "actions": ["Install memory profiler", "Set up alerts at 80% usage", "Schedule regular restarts"]
                    })
                
                elif issue.issue_type == "disk_space_low":
                    recommendations.append({
                        "type": "proactive_action",
                        "priority": "critical",
                        "title": "Clean Up Disk Space",
                        "description": "Free up disk space before system failure",
                        "actions": ["Clean log files", "Archive old data", "Add more storage"]
                    })
            
            # Recommendations based on historical patterns
            common_errors = memory_insights.get("recurring_patterns", [])
            for pattern in common_errors[:3]:  # Top 3 recurring patterns
                recommendations.append({
                    "type": "pattern_prevention",
                    "priority": "medium",
                    "title": f"Prevent {pattern.get('error_type', 'Unknown')} errors",
                    "description": "Based on recurring patterns in your project",
                    "actions": pattern.get("prevention_actions", [])
                })
            
            # Team learning recommendations
            if context.team_expertise:
                missing_expertise = set(["python", "javascript", "docker", "git"]) - set(context.team_expertise)
                if missing_expertise:
                    recommendations.append({
                        "type": "team_development",
                        "priority": "low",
                        "title": "Expand Team Expertise",
                        "description": f"Consider training in: {', '.join(missing_expertise)}",
                        "actions": [f"Schedule training for {skill}" for skill in missing_expertise]
                    })
            
        except Exception as e:
            logger.debug(f"Error generating proactive recommendations: {e}")
        
        return recommendations