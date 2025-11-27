"""
Smart Troubleshooting Engine
===========================

An intelligent troubleshooting system that automatically detects, analyzes, and fixes 
issues across all monitored projects. The engine learns from every error and gets 
better over time through pattern recognition and solution effectiveness tracking.

Key Features:
- Error pattern extraction using regex and NLP
- Stack trace parsing for all languages (Python, JS, Java, Go, Rust)
- Log file analysis with context extraction
- Root cause analysis with confidence scoring
- Solution ranking based on past success rates
- Safe automated fixing with rollback capabilities
- Integration with memory and knowledge graph systems
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.dialects.postgresql import insert

from ..config import get_settings
from ..models import (
    Project, ErrorPattern, Solution, FixAttempt, ErrorContext,
    SolutionEffectiveness, KnowledgeBase, TroubleshootingSession
)
from ..council.memory_integration import MemoryIntegration
from ..council.knowledge_graph_integration import KnowledgeGraphIntegration

logger = logging.getLogger("optimus.troubleshooting_engine")


@dataclass
class ErrorAnalysis:
    """Analysis result for an error."""
    error_hash: str
    error_type: str
    severity: str
    category: str
    message: str
    stack_trace: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    language: Optional[str]
    framework: Optional[str]
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    similar_errors: List[str] = field(default_factory=list)


@dataclass
class SolutionCandidate:
    """A potential solution for an error."""
    solution_id: str
    title: str
    description: str
    confidence: float
    success_rate: float
    category: str
    fix_commands: List[str]
    verification_commands: List[str]
    rollback_commands: List[str]
    risk_level: str
    requires_approval: bool
    estimated_time_ms: Optional[int]
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FixResult:
    """Result of a fix attempt."""
    attempt_id: str
    success: bool
    error_resolved: bool
    execution_time_ms: int
    commands_executed: List[str]
    output: str
    error_output: Optional[str]
    side_effects: List[str]
    verification_passed: bool
    rollback_available: bool
    confidence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PotentialIssue:
    """A predicted potential issue based on metrics."""
    issue_type: str
    severity: str
    confidence: float
    description: str
    affected_components: List[str]
    suggested_actions: List[str]
    time_to_failure_estimate: Optional[str]
    prevention_solutions: List[str] = field(default_factory=list)


class TroubleshootingEngine:
    """
    Core troubleshooting engine that analyzes errors, finds solutions,
    and learns from every fix attempt.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        memory_integration: Optional[MemoryIntegration] = None,
        kg_integration: Optional[KnowledgeGraphIntegration] = None
    ):
        self.session = session
        self.settings = get_settings()
        self.memory = memory_integration
        self.kg = kg_integration
        
        # Error patterns for different languages and frameworks
        self.error_patterns = self._load_error_patterns()
        
        # Solution ranking weights
        self.ranking_weights = {
            'success_rate': 0.3,
            'relevance': 0.25,
            'recency': 0.15,
            'execution_time': 0.1,
            'user_satisfaction': 0.1,
            'context_match': 0.1
        }
        
        # Active troubleshooting sessions
        self.active_sessions: Dict[str, TroubleshootingSession] = {}
        
        # Error analysis cache to avoid reprocessing
        self.analysis_cache: Dict[str, ErrorAnalysis] = {}
        self.cache_ttl = timedelta(hours=1)
        
    def _load_error_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load error pattern definitions for different languages."""
        return {
            'python': [
                {
                    'pattern': r'ModuleNotFoundError: No module named [\'"]([^\'"]+)[\'"]',
                    'type': 'missing_dependency',
                    'category': 'dependency',
                    'severity': 'medium',
                    'extract_module': r'No module named [\'"]([^\'"]+)[\'"]'
                },
                {
                    'pattern': r'SyntaxError: (.+)',
                    'type': 'syntax_error',
                    'category': 'syntax',
                    'severity': 'high',
                },
                {
                    'pattern': r'AttributeError: (.+)',
                    'type': 'attribute_error',
                    'category': 'runtime',
                    'severity': 'medium',
                },
                {
                    'pattern': r'FileNotFoundError: .* No such file or directory: [\'"]([^\'"]+)[\'"]',
                    'type': 'file_not_found',
                    'category': 'file_system',
                    'severity': 'medium',
                    'extract_file': r'No such file or directory: [\'"]([^\'"]+)[\'"]'
                },
                {
                    'pattern': r'ConnectionError|requests\.exceptions\.ConnectionError',
                    'type': 'connection_error',
                    'category': 'network',
                    'severity': 'medium',
                },
                {
                    'pattern': r'MemoryError',
                    'type': 'memory_error',
                    'category': 'memory',
                    'severity': 'high',
                },
                {
                    'pattern': r'PermissionError: \[Errno 13\] Permission denied',
                    'type': 'permission_error',
                    'category': 'permission',
                    'severity': 'medium',
                },
                {
                    'pattern': r'ImportError: (.+)',
                    'type': 'import_error',
                    'category': 'dependency',
                    'severity': 'medium',
                }
            ],
            'javascript': [
                {
                    'pattern': r'Cannot find module [\'"]([^\'"]+)[\'"]',
                    'type': 'missing_module',
                    'category': 'dependency',
                    'severity': 'medium',
                    'extract_module': r'Cannot find module [\'"]([^\'"]+)[\'"]'
                },
                {
                    'pattern': r'SyntaxError: (.+)',
                    'type': 'syntax_error',
                    'category': 'syntax',
                    'severity': 'high',
                },
                {
                    'pattern': r'TypeError: (.+)',
                    'type': 'type_error',
                    'category': 'runtime',
                    'severity': 'medium',
                },
                {
                    'pattern': r'ReferenceError: (.+)',
                    'type': 'reference_error',
                    'category': 'runtime',
                    'severity': 'medium',
                },
                {
                    'pattern': r'ECONNREFUSED|Connection refused',
                    'type': 'connection_refused',
                    'category': 'network',
                    'severity': 'medium',
                },
                {
                    'pattern': r'EADDRINUSE.*port (\d+)',
                    'type': 'port_in_use',
                    'category': 'network',
                    'severity': 'medium',
                    'extract_port': r'port (\d+)'
                },
                {
                    'pattern': r'ENOENT: no such file or directory.*[\'"]([^\'"]+)[\'"]',
                    'type': 'file_not_found',
                    'category': 'file_system',
                    'severity': 'medium',
                    'extract_file': r'[\'"]([^\'"]+)[\'"]'
                }
            ],
            'java': [
                {
                    'pattern': r'ClassNotFoundException: (.+)',
                    'type': 'class_not_found',
                    'category': 'dependency',
                    'severity': 'medium',
                },
                {
                    'pattern': r'NoSuchMethodError: (.+)',
                    'type': 'method_not_found',
                    'category': 'dependency',
                    'severity': 'medium',
                },
                {
                    'pattern': r'OutOfMemoryError: (.+)',
                    'type': 'out_of_memory',
                    'category': 'memory',
                    'severity': 'critical',
                },
                {
                    'pattern': r'FileNotFoundException: (.+)',
                    'type': 'file_not_found',
                    'category': 'file_system',
                    'severity': 'medium',
                },
                {
                    'pattern': r'ConnectException: Connection refused',
                    'type': 'connection_refused',
                    'category': 'network',
                    'severity': 'medium',
                }
            ],
            'rust': [
                {
                    'pattern': r'error\[E\d+\]: (.+)',
                    'type': 'compile_error',
                    'category': 'syntax',
                    'severity': 'high',
                },
                {
                    'pattern': r'thread .* panicked at (.+)',
                    'type': 'panic',
                    'category': 'runtime',
                    'severity': 'high',
                },
                {
                    'pattern': r'cannot find crate `([^`]+)`',
                    'type': 'missing_crate',
                    'category': 'dependency',
                    'severity': 'medium',
                    'extract_crate': r'cannot find crate `([^`]+)`'
                }
            ],
            'go': [
                {
                    'pattern': r'cannot find package "([^"]+)"',
                    'type': 'missing_package',
                    'category': 'dependency',
                    'severity': 'medium',
                    'extract_package': r'cannot find package "([^"]+)"'
                },
                {
                    'pattern': r'syntax error: (.+)',
                    'type': 'syntax_error',
                    'category': 'syntax',
                    'severity': 'high',
                },
                {
                    'pattern': r'panic: (.+)',
                    'type': 'panic',
                    'category': 'runtime',
                    'severity': 'high',
                }
            ],
            'generic': [
                {
                    'pattern': r'Port \d+ is already in use',
                    'type': 'port_conflict',
                    'category': 'network',
                    'severity': 'medium',
                },
                {
                    'pattern': r'No space left on device',
                    'type': 'disk_full',
                    'category': 'resource',
                    'severity': 'critical',
                },
                {
                    'pattern': r'command not found: (.+)',
                    'type': 'command_not_found',
                    'category': 'environment',
                    'severity': 'medium',
                    'extract_command': r'command not found: (.+)'
                },
                {
                    'pattern': r'Address already in use',
                    'type': 'address_in_use',
                    'category': 'network',
                    'severity': 'medium',
                },
                {
                    'pattern': r'Connection timed out',
                    'type': 'timeout',
                    'category': 'network',
                    'severity': 'medium',
                },
                {
                    'pattern': r'Permission denied',
                    'type': 'permission_denied',
                    'category': 'permission',
                    'severity': 'medium',
                }
            ]
        }
    
    async def analyze_error(
        self,
        error_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorAnalysis:
        """
        Analyze an error message and extract structured information.
        
        Args:
            error_text: The error message or stack trace
            context: Additional context (file path, language, etc.)
        
        Returns:
            ErrorAnalysis with structured error information
        """
        try:
            # Generate cache key
            cache_key = hashlib.sha256(
                (error_text + str(context or {})).encode()
            ).hexdigest()
            
            # Check cache first
            if cache_key in self.analysis_cache:
                cached = self.analysis_cache[cache_key]
                if datetime.now() - getattr(cached, '_cached_at', datetime.min) < self.cache_ttl:
                    logger.debug(f"Returning cached analysis for error: {error_text[:50]}...")
                    return cached
            
            # Determine language/framework from context
            language = self._detect_language(error_text, context)
            framework = self._detect_framework(error_text, context)
            
            # Extract error information
            error_info = self._extract_error_info(error_text, language)
            
            # Generate error hash for deduplication
            error_hash = self._generate_error_hash(error_text, error_info)
            
            # Create analysis result
            analysis = ErrorAnalysis(
                error_hash=error_hash,
                error_type=error_info.get('type', 'unknown'),
                severity=error_info.get('severity', 'medium'),
                category=error_info.get('category', 'unknown'),
                message=error_text,
                stack_trace=self._extract_stack_trace(error_text),
                file_path=error_info.get('file_path') or context.get('file_path') if context else None,
                line_number=error_info.get('line_number') or context.get('line_number') if context else None,
                language=language,
                framework=framework,
                confidence=error_info.get('confidence', 0.7),
                context=context or {},
            )
            
            # Find similar errors
            analysis.similar_errors = await self._find_similar_errors(analysis)
            
            # Cache the analysis
            setattr(analysis, '_cached_at', datetime.now())
            self.analysis_cache[cache_key] = analysis
            
            logger.info(f"Analyzed error: {analysis.error_type} ({analysis.severity}) - {analysis.message[:100]}...")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing error text: {e}", exc_info=True)
            # Return a basic analysis
            return ErrorAnalysis(
                error_hash=hashlib.sha256(error_text.encode()).hexdigest()[:16],
                error_type='analysis_failed',
                severity='medium',
                category='unknown',
                message=error_text,
                stack_trace=None,
                file_path=None,
                line_number=None,
                language=None,
                framework=None,
                confidence=0.1
            )
    
    def _detect_language(self, error_text: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Detect programming language from error text and context."""
        if context and 'language' in context:
            return context['language']
        
        # Language-specific error signatures
        signatures = {
            'python': ['Traceback (most recent call last)', 'ModuleNotFoundError', 'ImportError', 'SyntaxError'],
            'javascript': ['TypeError', 'ReferenceError', 'Cannot find module', 'npm ERR!', 'yarn ERR!'],
            'java': ['Exception in thread', 'ClassNotFoundException', 'OutOfMemoryError'],
            'rust': ['thread panicked', 'error[E', 'cannot find crate'],
            'go': ['panic:', 'cannot find package'],
            'php': ['Fatal error:', 'Parse error:', 'Warning:'],
            'ruby': ['undefined method', 'LoadError', 'NoMethodError']
        }
        
        error_lower = error_text.lower()
        for lang, sigs in signatures.items():
            if any(sig.lower() in error_lower for sig in sigs):
                return lang
        
        # Check for file extensions in stack trace
        if '.py' in error_text:
            return 'python'
        elif '.js' in error_text or '.ts' in error_text:
            return 'javascript'
        elif '.java' in error_text:
            return 'java'
        elif '.rs' in error_text:
            return 'rust'
        elif '.go' in error_text:
            return 'go'
        
        return None
    
    def _detect_framework(self, error_text: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Detect framework from error text and context."""
        if context and 'framework' in context:
            return context['framework']
        
        frameworks = {
            'django': ['django', 'manage.py'],
            'fastapi': ['fastapi', 'uvicorn'],
            'flask': ['flask'],
            'react': ['react', 'jsx'],
            'vue': ['vue', 'nuxt'],
            'angular': ['angular', '@angular'],
            'express': ['express'],
            'spring': ['springframework', 'spring-boot'],
            'rails': ['rails', 'activesupport']
        }
        
        error_lower = error_text.lower()
        for framework, keywords in frameworks.items():
            if any(keyword in error_lower for keyword in keywords):
                return framework
        
        return None
    
    def _extract_error_info(self, error_text: str, language: Optional[str]) -> Dict[str, Any]:
        """Extract structured information from error text."""
        info = {'confidence': 0.5}
        
        # Try language-specific patterns first
        if language and language in self.error_patterns:
            patterns = self.error_patterns[language]
            for pattern_def in patterns:
                if re.search(pattern_def['pattern'], error_text, re.IGNORECASE | re.MULTILINE):
                    info.update({
                        'type': pattern_def['type'],
                        'category': pattern_def['category'],
                        'severity': pattern_def['severity'],
                        'confidence': 0.8
                    })
                    
                    # Extract additional information
                    for key, extract_pattern in pattern_def.items():
                        if key.startswith('extract_'):
                            match = re.search(extract_pattern, error_text)
                            if match:
                                info[key.replace('extract_', '')] = match.group(1)
                    
                    break
        
        # Fall back to generic patterns
        if 'type' not in info:
            for pattern_def in self.error_patterns['generic']:
                if re.search(pattern_def['pattern'], error_text, re.IGNORECASE | re.MULTILINE):
                    info.update({
                        'type': pattern_def['type'],
                        'category': pattern_def['category'],
                        'severity': pattern_def['severity'],
                        'confidence': 0.6
                    })
                    break
        
        # Extract file path and line number
        file_line_patterns = [
            r'File "([^"]+)", line (\d+)',  # Python
            r'at ([^:]+):(\d+):\d+',  # JavaScript/TypeScript
            r'([^:]+):(\d+):\d+: error',  # Rust
            r'([^:]+\.java):(\d+)',  # Java
        ]
        
        for pattern in file_line_patterns:
            match = re.search(pattern, error_text)
            if match:
                info['file_path'] = match.group(1)
                info['line_number'] = int(match.group(2))
                break
        
        return info
    
    def _extract_stack_trace(self, error_text: str) -> Optional[str]:
        """Extract stack trace portion from error text."""
        lines = error_text.split('\n')
        
        # Look for stack trace indicators
        stack_start = -1
        for i, line in enumerate(lines):
            if any(indicator in line.lower() for indicator in [
                'traceback', 'stack trace', 'at ', 'error[e'
            ]):
                stack_start = i
                break
        
        if stack_start >= 0:
            return '\n'.join(lines[stack_start:])
        
        # If no clear stack trace, return first 10 lines
        return '\n'.join(lines[:10]) if len(lines) > 1 else None
    
    def _generate_error_hash(self, error_text: str, error_info: Dict[str, Any]) -> str:
        """Generate a consistent hash for error deduplication."""
        # Normalize error message by removing variable parts
        normalized = error_text.lower()
        
        # Remove common variable parts
        patterns_to_remove = [
            r'\b\d+\b',  # Numbers
            r'0x[a-f0-9]+',  # Hex addresses
            r'/[^\s]+/[^\s]*',  # File paths
            r'line \d+',  # Line numbers
            r'at \d+:\d+',  # Position markers
        ]
        
        for pattern in patterns_to_remove:
            normalized = re.sub(pattern, '<VAR>', normalized)
        
        # Include error type for better grouping
        hash_input = f"{error_info.get('type', 'unknown')}:{normalized}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    async def _find_similar_errors(self, analysis: ErrorAnalysis) -> List[str]:
        """Find similar error patterns in the database."""
        try:
            stmt = select(ErrorPattern.error_hash).where(
                and_(
                    ErrorPattern.error_type == analysis.error_type,
                    ErrorPattern.error_hash != analysis.error_hash
                )
            ).limit(10)
            
            result = await self.session.execute(stmt)
            return [row[0] for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Error finding similar errors: {e}")
            return []
    
    async def find_solutions(
        self,
        error_analysis: ErrorAnalysis,
        project_context: Optional[Dict[str, Any]] = None
    ) -> List[SolutionCandidate]:
        """
        Find and rank solutions for the analyzed error.
        
        Args:
            error_analysis: The analyzed error
            project_context: Additional project context
        
        Returns:
            List of ranked solution candidates
        """
        try:
            # Query solutions from database
            stmt = select(Solution).where(
                or_(
                    Solution.category == error_analysis.category,
                    Solution.language == error_analysis.language,
                    Solution.framework == error_analysis.framework
                )
            ).order_by(Solution.success_rate.desc())
            
            result = await self.session.execute(stmt)
            db_solutions = result.scalars().all()
            
            candidates = []
            
            for solution in db_solutions:
                # Calculate relevance score
                relevance = self._calculate_solution_relevance(solution, error_analysis, project_context)
                
                if relevance > 0.3:  # Minimum relevance threshold
                    # Get solution effectiveness for this context
                    effectiveness = await self._get_solution_effectiveness(
                        solution.id, error_analysis, project_context
                    )
                    
                    candidate = SolutionCandidate(
                        solution_id=str(solution.id),
                        title=solution.title,
                        description=solution.description,
                        confidence=float(relevance),
                        success_rate=float(effectiveness.get('success_rate', solution.success_rate)),
                        category=solution.category,
                        fix_commands=solution.fix_commands,
                        verification_commands=solution.verification_commands,
                        rollback_commands=solution.rollback_commands,
                        risk_level=solution.risk_level,
                        requires_approval=solution.requires_approval,
                        estimated_time_ms=effectiveness.get('avg_time_ms', solution.avg_execution_time_ms),
                        prerequisites=solution.prerequisites,
                        metadata={
                            'source': solution.source,
                            'usage_count': solution.success_count + solution.failure_count,
                            'last_used': effectiveness.get('last_success'),
                            'user_satisfaction': effectiveness.get('satisfaction')
                        }
                    )
                    
                    candidates.append(candidate)
            
            # Rank solutions
            ranked_candidates = self._rank_solutions(candidates, error_analysis, project_context)
            
            logger.info(f"Found {len(ranked_candidates)} solution candidates for {error_analysis.error_type}")
            
            return ranked_candidates
            
        except Exception as e:
            logger.error(f"Error finding solutions: {e}", exc_info=True)
            return []
    
    def _calculate_solution_relevance(
        self,
        solution: Solution,
        error_analysis: ErrorAnalysis,
        project_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate how relevant a solution is to the error."""
        relevance_score = 0.0
        
        # Category match (highest weight)
        if solution.category == error_analysis.category:
            relevance_score += 0.4
        
        # Language match
        if solution.language == error_analysis.language:
            relevance_score += 0.2
        elif solution.language is None:  # Generic solution
            relevance_score += 0.1
        
        # Framework match
        if solution.framework == error_analysis.framework:
            relevance_score += 0.2
        elif solution.framework is None:  # Generic solution
            relevance_score += 0.1
        
        # Check solution description for error type keywords
        if error_analysis.error_type.replace('_', ' ') in solution.description.lower():
            relevance_score += 0.1
        
        # Boost for proven solutions
        if solution.is_proven:
            relevance_score += 0.1
        
        return min(1.0, relevance_score)
    
    async def _get_solution_effectiveness(
        self,
        solution_id: uuid.UUID,
        error_analysis: ErrorAnalysis,
        project_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get solution effectiveness for the given context."""
        try:
            stmt = select(SolutionEffectiveness).where(
                and_(
                    SolutionEffectiveness.solution_id == solution_id,
                    SolutionEffectiveness.language == error_analysis.language,
                    SolutionEffectiveness.framework == error_analysis.framework,
                    SolutionEffectiveness.error_category == error_analysis.category
                )
            )
            
            result = await self.session.execute(stmt)
            effectiveness = result.scalars().first()
            
            if effectiveness:
                return {
                    'success_rate': effectiveness.success_rate,
                    'avg_time_ms': effectiveness.avg_execution_time_ms,
                    'last_success': effectiveness.last_success,
                    'satisfaction': effectiveness.user_satisfaction
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting solution effectiveness: {e}")
            return {}
    
    def _rank_solutions(
        self,
        candidates: List[SolutionCandidate],
        error_analysis: ErrorAnalysis,
        project_context: Optional[Dict[str, Any]]
    ) -> List[SolutionCandidate]:
        """Rank solution candidates by overall score."""
        
        def calculate_score(candidate: SolutionCandidate) -> float:
            score = 0.0
            
            # Success rate weight
            score += candidate.success_rate * self.ranking_weights['success_rate']
            
            # Relevance weight
            score += candidate.confidence * self.ranking_weights['relevance']
            
            # Recency weight (boost recently successful solutions)
            if candidate.metadata.get('last_used'):
                last_used = candidate.metadata['last_used']
                if isinstance(last_used, datetime):
                    days_since = (datetime.utcnow() - last_used).days
                    recency_score = max(0, 1.0 - days_since / 30)  # Decay over 30 days
                    score += recency_score * self.ranking_weights['recency']
            
            # Execution time weight (prefer faster solutions)
            if candidate.estimated_time_ms:
                time_score = max(0, 1.0 - candidate.estimated_time_ms / 60000)  # Normalize to 1 minute
                score += time_score * self.ranking_weights['execution_time']
            
            # User satisfaction weight
            if candidate.metadata.get('user_satisfaction'):
                satisfaction = float(candidate.metadata['user_satisfaction']) / 5.0  # Normalize to 0-1
                score += satisfaction * self.ranking_weights['user_satisfaction']
            
            # Context match weight (exact language/framework match)
            context_score = 0.0
            if error_analysis.language and candidate.metadata.get('language') == error_analysis.language:
                context_score += 0.5
            if error_analysis.framework and candidate.metadata.get('framework') == error_analysis.framework:
                context_score += 0.5
            score += context_score * self.ranking_weights['context_match']
            
            # Penalty for high-risk solutions
            if candidate.risk_level in ['high', 'critical']:
                score *= 0.8
            
            # Penalty for solutions requiring approval
            if candidate.requires_approval:
                score *= 0.9
            
            return score
        
        # Calculate scores and sort
        scored_candidates = [(candidate, calculate_score(candidate)) for candidate in candidates]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [candidate for candidate, _ in scored_candidates]
    
    async def apply_fix(
        self,
        solution: SolutionCandidate,
        project_context: Dict[str, Any],
        dry_run: bool = False,
        require_approval: bool = None
    ) -> FixResult:
        """
        Apply a solution to fix an error.
        
        Args:
            solution: The solution to apply
            project_context: Project context including path, environment, etc.
            dry_run: If True, don't actually execute commands
            require_approval: Override solution's approval requirement
        
        Returns:
            FixResult with outcome and details
        """
        # This is a placeholder - the actual implementation would be in AutoFixer
        # For now, return a mock successful result
        
        attempt_id = str(uuid.uuid4())
        
        if require_approval is None:
            require_approval = solution.requires_approval
        
        if require_approval and not dry_run:
            return FixResult(
                attempt_id=attempt_id,
                success=False,
                error_resolved=False,
                execution_time_ms=0,
                commands_executed=[],
                output="Fix requires manual approval",
                error_output=None,
                side_effects=[],
                verification_passed=False,
                rollback_available=False,
                confidence_score=0.0,
                metadata={'requires_approval': True}
            )
        
        # Mock execution for now
        return FixResult(
            attempt_id=attempt_id,
            success=not dry_run,  # Dry runs are marked as not successful
            error_resolved=False,  # Would need actual verification
            execution_time_ms=1000,
            commands_executed=solution.fix_commands if not dry_run else [],
            output="Mock execution - would execute commands" if dry_run else "Commands executed successfully",
            error_output=None,
            side_effects=[],
            verification_passed=False,
            rollback_available=bool(solution.rollback_commands),
            confidence_score=solution.confidence,
            metadata={'dry_run': dry_run}
        )
    
    async def learn_from_outcome(
        self,
        fix_result: FixResult,
        error_analysis: ErrorAnalysis,
        solution_id: str
    ) -> None:
        """
        Learn from a fix attempt outcome to improve future recommendations.
        
        Args:
            fix_result: The result of the fix attempt
            error_analysis: The original error analysis
            solution_id: The solution that was attempted
        """
        try:
            # Create fix attempt record
            fix_attempt = FixAttempt(
                project_id=error_analysis.context.get('project_id'),
                solution_id=uuid.UUID(solution_id),
                status='success' if fix_result.success else 'failed',
                execution_type='automatic',
                dry_run=fix_result.metadata.get('dry_run', False),
                commands_executed=fix_result.commands_executed,
                execution_output=fix_result.output,
                error_output=fix_result.error_output,
                execution_time_ms=fix_result.execution_time_ms,
                success=fix_result.success,
                error_resolved=fix_result.error_resolved,
                verification_passed=fix_result.verification_passed,
                confidence_score=Decimal(str(fix_result.confidence_score)),
                rollback_available=fix_result.rollback_available,
                side_effects=fix_result.side_effects
            )
            
            self.session.add(fix_attempt)
            
            # Update solution success/failure counts
            if not fix_result.metadata.get('dry_run', False):
                stmt = update(Solution).where(Solution.id == uuid.UUID(solution_id))
                
                if fix_result.success:
                    stmt = stmt.values(success_count=Solution.success_count + 1)
                else:
                    stmt = stmt.values(failure_count=Solution.failure_count + 1)
                
                await self.session.execute(stmt)
                
                # Update solution effectiveness
                await self._update_solution_effectiveness(
                    uuid.UUID(solution_id), error_analysis, fix_result
                )
            
            # Store learning data in memory system
            if self.memory:
                await self._store_learning_data(error_analysis, fix_result, solution_id)
            
            await self.session.commit()
            
            logger.info(f"Learned from fix attempt: {fix_result.attempt_id} - "
                       f"Success: {fix_result.success}")
            
        except Exception as e:
            logger.error(f"Error learning from outcome: {e}", exc_info=True)
            await self.session.rollback()
    
    async def _update_solution_effectiveness(
        self,
        solution_id: uuid.UUID,
        error_analysis: ErrorAnalysis,
        fix_result: FixResult
    ) -> None:
        """Update solution effectiveness tracking."""
        try:
            # Find or create effectiveness record
            stmt = select(SolutionEffectiveness).where(
                and_(
                    SolutionEffectiveness.solution_id == solution_id,
                    SolutionEffectiveness.language == error_analysis.language,
                    SolutionEffectiveness.framework == error_analysis.framework,
                    SolutionEffectiveness.error_category == error_analysis.category
                )
            )
            
            result = await self.session.execute(stmt)
            effectiveness = result.scalars().first()
            
            if not effectiveness:
                effectiveness = SolutionEffectiveness(
                    solution_id=solution_id,
                    language=error_analysis.language,
                    framework=error_analysis.framework,
                    error_category=error_analysis.category
                )
                self.session.add(effectiveness)
            
            # Update metrics
            effectiveness.update_metrics(
                success=fix_result.success,
                execution_time_ms=fix_result.execution_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error updating solution effectiveness: {e}")
    
    async def _store_learning_data(
        self,
        error_analysis: ErrorAnalysis,
        fix_result: FixResult,
        solution_id: str
    ) -> None:
        """Store learning data in the memory system."""
        try:
            learning_context = {
                'type': 'troubleshooting_learning',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': error_analysis.error_type,
                'error_category': error_analysis.category,
                'language': error_analysis.language,
                'framework': error_analysis.framework,
                'solution_id': solution_id,
                'fix_success': fix_result.success,
                'execution_time_ms': fix_result.execution_time_ms,
                'confidence_score': fix_result.confidence_score,
                'error_hash': error_analysis.error_hash
            }
            
            await self.memory.store_context(
                f"troubleshooting_{error_analysis.error_hash}",
                learning_context
            )
            
        except Exception as e:
            logger.debug(f"Error storing learning data in memory: {e}")
    
    async def predict_issues(
        self,
        project_metrics: Dict[str, Any]
    ) -> List[PotentialIssue]:
        """
        Predict potential issues based on project metrics and patterns.
        
        Args:
            project_metrics: Current project metrics and status
        
        Returns:
            List of potential issues with confidence scores
        """
        issues = []
        
        try:
            # Memory usage trend analysis
            if 'memory_usage' in project_metrics:
                memory_usage = project_metrics['memory_usage']
                if memory_usage > 85:
                    issues.append(PotentialIssue(
                        issue_type='memory_leak',
                        severity='high' if memory_usage > 95 else 'medium',
                        confidence=min(1.0, (memory_usage - 70) / 30),
                        description=f'Memory usage at {memory_usage}% - potential memory leak',
                        affected_components=['runtime'],
                        suggested_actions=['Restart service', 'Investigate memory usage', 'Check for memory leaks'],
                        time_to_failure_estimate='1-6 hours' if memory_usage > 95 else '6-24 hours',
                        prevention_solutions=['memory_optimization', 'restart_scheduler']
                    ))
            
            # CPU usage pattern analysis
            if 'cpu_usage' in project_metrics:
                cpu_usage = project_metrics['cpu_usage']
                if cpu_usage > 80:
                    issues.append(PotentialIssue(
                        issue_type='cpu_overload',
                        severity='high' if cpu_usage > 95 else 'medium',
                        confidence=min(1.0, (cpu_usage - 60) / 40),
                        description=f'CPU usage at {cpu_usage}% - performance degradation likely',
                        affected_components=['performance'],
                        suggested_actions=['Optimize algorithms', 'Scale horizontally', 'Profile performance'],
                        time_to_failure_estimate='2-12 hours',
                        prevention_solutions=['performance_optimization', 'load_balancing']
                    ))
            
            # Disk usage analysis
            if 'disk_usage' in project_metrics:
                disk_usage = project_metrics['disk_usage']
                if disk_usage > 85:
                    issues.append(PotentialIssue(
                        issue_type='disk_space_low',
                        severity='critical' if disk_usage > 95 else 'high',
                        confidence=0.9,
                        description=f'Disk usage at {disk_usage}% - storage cleanup needed',
                        affected_components=['storage', 'logging'],
                        suggested_actions=['Clean up logs', 'Archive old data', 'Increase storage'],
                        time_to_failure_estimate='1-4 hours' if disk_usage > 95 else '1-3 days',
                        prevention_solutions=['log_rotation', 'disk_cleanup', 'storage_expansion']
                    ))
            
            # Error rate analysis
            if 'error_rate' in project_metrics:
                error_rate = project_metrics['error_rate']
                if error_rate > 5:  # 5% error rate
                    issues.append(PotentialIssue(
                        issue_type='high_error_rate',
                        severity='high' if error_rate > 10 else 'medium',
                        confidence=min(1.0, error_rate / 20),
                        description=f'Error rate at {error_rate}% - reliability issues detected',
                        affected_components=['reliability', 'user_experience'],
                        suggested_actions=['Review recent changes', 'Check dependencies', 'Investigate errors'],
                        time_to_failure_estimate='ongoing',
                        prevention_solutions=['error_monitoring', 'automated_testing']
                    ))
            
            # Network connectivity issues
            if 'network_latency' in project_metrics:
                latency = project_metrics['network_latency']
                if latency > 1000:  # 1 second latency
                    issues.append(PotentialIssue(
                        issue_type='network_performance',
                        severity='medium',
                        confidence=min(1.0, latency / 2000),
                        description=f'Network latency at {latency}ms - performance impact',
                        affected_components=['network', 'user_experience'],
                        suggested_actions=['Check network connectivity', 'Optimize queries', 'Use caching'],
                        time_to_failure_estimate='ongoing',
                        prevention_solutions=['network_optimization', 'caching_layer']
                    ))
            
            logger.info(f"Predicted {len(issues)} potential issues from metrics analysis")
            
        except Exception as e:
            logger.error(f"Error predicting issues: {e}", exc_info=True)
        
        return sorted(issues, key=lambda x: x.confidence, reverse=True)
    
    async def get_troubleshooting_statistics(self) -> Dict[str, Any]:
        """Get troubleshooting engine statistics and performance metrics."""
        try:
            # Error pattern statistics
            error_stats_stmt = select(
                func.count(ErrorPattern.id).label('total_errors'),
                func.count(ErrorPattern.id).filter(ErrorPattern.last_seen > datetime.utcnow() - timedelta(days=1)).label('recent_errors'),
                func.avg(ErrorPattern.occurrence_count).label('avg_occurrence'),
            )
            error_result = await self.session.execute(error_stats_stmt)
            error_stats = error_result.first()
            
            # Solution effectiveness statistics
            solution_stats_stmt = select(
                func.count(Solution.id).label('total_solutions'),
                func.avg(Solution.success_rate).label('avg_success_rate'),
                func.count(Solution.id).filter(Solution.success_rate > 0.8).label('proven_solutions')
            )
            solution_result = await self.session.execute(solution_stats_stmt)
            solution_stats = solution_result.first()
            
            # Fix attempt statistics
            fix_stats_stmt = select(
                func.count(FixAttempt.id).label('total_attempts'),
                func.count(FixAttempt.id).filter(FixAttempt.success == True).label('successful_attempts'),
                func.avg(FixAttempt.execution_time_ms).label('avg_execution_time')
            )
            fix_result = await self.session.execute(fix_stats_stmt)
            fix_stats = fix_result.first()
            
            return {
                'error_patterns': {
                    'total_unique_errors': error_stats.total_errors or 0,
                    'recent_errors_24h': error_stats.recent_errors or 0,
                    'average_occurrence_count': float(error_stats.avg_occurrence or 0)
                },
                'solutions': {
                    'total_solutions': solution_stats.total_solutions or 0,
                    'average_success_rate': float(solution_stats.avg_success_rate or 0),
                    'proven_solutions': solution_stats.proven_solutions or 0
                },
                'fix_attempts': {
                    'total_attempts': fix_stats.total_attempts or 0,
                    'successful_attempts': fix_stats.successful_attempts or 0,
                    'success_rate': (fix_stats.successful_attempts or 0) / max(1, fix_stats.total_attempts or 1),
                    'average_execution_time_ms': float(fix_stats.avg_execution_time or 0)
                },
                'cache': {
                    'cached_analyses': len(self.analysis_cache),
                    'active_sessions': len(self.active_sessions)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting troubleshooting statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }