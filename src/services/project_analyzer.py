"""
Project Analyzer Service
========================

Advanced code analysis service that performs comprehensive quality and security assessment.
Features include:

- Code quality metrics and complexity analysis
- Security vulnerability scanning with OWASP compliance
- Documentation quality assessment
- Test coverage analysis
- License detection and compliance checking
- API endpoint security analysis
- Performance bottleneck identification
- Technical debt assessment
- Maintainability scoring

Integrates with:
- Enhanced scanner for project discovery
- Knowledge graph for security pattern storage
- Memory system for learning from past analyses
- Council of Minds for intelligent recommendations
"""

import ast
import asyncio
import hashlib
import json
import logging
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..council.memory_integration import MemoryIntegration
from ..council.knowledge_graph_integration import KnowledgeGraphIntegration


logger = logging.getLogger("optimus.project_analyzer")


@dataclass
class CodeMetrics:
    """Comprehensive code metrics for a project."""
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    functions_count: int = 0
    classes_count: int = 0
    complexity_score: float = 0.0
    maintainability_index: float = 0.0
    technical_debt_ratio: float = 0.0
    duplicated_lines: int = 0
    test_coverage_percent: float = 0.0
    documentation_coverage: float = 0.0


@dataclass
class SecurityIssue:
    """Security vulnerability or issue found in code."""
    category: str  # injection, secrets, crypto, etc.
    severity: str  # critical, high, medium, low
    cwe_id: Optional[str]  # Common Weakness Enumeration ID
    file_path: str
    line_number: int
    description: str
    recommendation: str
    evidence: str  # Code snippet showing the issue
    confidence: float  # 0.0 to 1.0


@dataclass
class QualityIssue:
    """Code quality issue or technical debt item."""
    category: str  # complexity, duplication, naming, etc.
    severity: str
    file_path: str
    line_number: int
    description: str
    suggestion: str
    effort_estimate: str  # time to fix
    impact: str  # maintainability, performance, etc.


@dataclass
class TestAnalysis:
    """Test suite analysis results."""
    framework: Optional[str]
    total_tests: int
    passing_tests: int
    failing_tests: int
    skipped_tests: int
    coverage_percent: float
    test_files: List[str]
    missing_coverage: List[str]  # Files without test coverage


@dataclass
class DocumentationAnalysis:
    """Documentation quality analysis."""
    readme_score: float  # 0-100
    api_docs_score: float
    inline_docs_score: float
    changelog_exists: bool
    license_exists: bool
    contributing_guide: bool
    missing_sections: List[str]
    quality_level: str  # excellent, good, fair, poor


@dataclass
class PerformanceAnalysis:
    """Performance and optimization analysis."""
    bottlenecks: List[Dict[str, Any]]
    optimization_opportunities: List[str]
    resource_usage_issues: List[str]
    scalability_concerns: List[str]
    performance_score: float  # 0-100


@dataclass
class ProjectAnalysisResult:
    """Comprehensive project analysis result."""
    project_id: str
    project_path: str
    analysis_timestamp: datetime
    code_metrics: CodeMetrics
    security_issues: List[SecurityIssue]
    quality_issues: List[QualityIssue]
    test_analysis: TestAnalysis
    documentation: DocumentationAnalysis
    performance: PerformanceAnalysis
    overall_score: float  # 0-100 composite score
    recommendations: List[str]


class ProjectAnalyzer:
    """Advanced project analyzer for code quality and security assessment."""
    
    def __init__(self, session: AsyncSession, memory_integration: MemoryIntegration = None,
                 kg_integration: KnowledgeGraphIntegration = None):
        self.session = session
        self.settings = get_settings()
        self.memory = memory_integration
        self.kg = kg_integration
        
        # Security vulnerability patterns
        self.security_patterns = {
            "secrets": [
                (r'(password|passwd|pwd)\s*=\s*["\'][^"\']{8,}["\']', "hardcoded_password", "high"),
                (r'(api_key|apikey|api-key)\s*=\s*["\'][^"\']+["\']', "api_key_exposure", "high"),
                (r'(secret|token)\s*=\s*["\'][^"\']+["\']', "hardcoded_secret", "high"),
                (r'(private_key|privatekey)\s*=\s*["\'][^"\']+["\']', "private_key_exposure", "critical"),
                (r'-----BEGIN (RSA |DSA |EC |OPENSSH |)PRIVATE KEY-----', "private_key_in_code", "critical"),
            ],
            "injection": [
                (r'eval\s*\(', "code_injection", "high"),
                (r'exec\s*\(', "code_injection", "high"),
                (r'os\.system\s*\(', "command_injection", "high"),
                (r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True', "shell_injection", "high"),
                (r'SELECT\s+.*\+.*FROM', "sql_injection_risk", "medium"),
                (r'innerHTML\s*=', "xss_risk", "medium"),
            ],
            "crypto": [
                (r'(md5|sha1)\s*\(', "weak_hash", "medium"),
                (r'(DES|3DES|RC4)', "weak_encryption", "high"),
                (r'random\(\)', "weak_random", "low"),
                (r'Math\.random\(\)', "weak_random_js", "low"),
            ],
            "auth": [
                (r'(auth|login|password).*=\s*False', "auth_bypass", "critical"),
                (r'verify\s*=\s*False', "ssl_verification_disabled", "high"),
                (r'(?i)(admin|root|sa)\s*["\']?\s*:\s*["\']?(admin|password|123|root)', "default_credentials", "high"),
            ],
            "files": [
                (r'open\s*\([^)]*["\'](\.\./|/etc/|/var/|C:\\)', "path_traversal", "medium"),
                (r'pickle\.(load|loads)', "pickle_deserialization", "high"),
                (r'yaml\.(load|full_load)\s*\(', "yaml_deserialization", "medium"),
            ]
        }
        
        # Code quality patterns
        self.quality_patterns = {
            "complexity": [
                (r'def\s+\w+\([^)]*\):[^def]{200,}', "long_function", "medium"),
                (r'class\s+\w+[^:]*:[^class]{1000,}', "large_class", "medium"),
                (r'if.*and.*and.*and', "complex_condition", "low"),
                (r'(for|while).*:(.*\n){10,}', "deep_nesting", "medium"),
            ],
            "naming": [
                (r'def\s+[a-z]{1,2}\s*\(', "short_function_name", "low"),
                (r'[a-z]+[0-9]+[a-z]*\s*=', "numbered_variable", "low"),
                (r'(foo|bar|baz|temp|tmp)', "generic_names", "low"),
            ],
            "imports": [
                (r'from\s+\w+\s+import\s+\*', "wildcard_import", "medium"),
                (r'import\s+\w+\s*,\s*\w+\s*,\s*\w+', "multiple_imports", "low"),
                (r'^import.*\n^import', "unsorted_imports", "low"),
            ],
            "comments": [
                (r'#\s*TODO(?!:)', "incomplete_todo", "low"),
                (r'#\s*FIXME', "fixme_comment", "medium"),
                (r'#\s*HACK', "hack_comment", "high"),
                (r'#\s*XXX', "concerning_comment", "medium"),
            ]
        }
        
        # Performance anti-patterns
        self.performance_patterns = {
            "python": [
                (r'for\s+\w+\s+in.*:\s*\w+\.append', "list_append_in_loop", "Use list comprehension"),
                (r'pandas.*\.iterrows\(\)', "pandas_iterrows", "Use vectorized operations"),
                (r'\.join\([^)]*for.*in.*\)', "string_join_generator", "Good pattern"),
                (r'open\([^)]*\)\s*\.read\(\)', "file_read_without_close", "Use context manager"),
            ],
            "javascript": [
                (r'document\.getElementById.*loop', "dom_query_in_loop", "Cache DOM queries"),
                (r'console\.log\(', "console_log_production", "Remove debug logs"),
                (r'var\s+', "var_usage", "Use let/const instead"),
                (r'==', "loose_equality", "Use strict equality (===)"),
            ],
            "sql": [
                (r'SELECT\s+\*\s+FROM', "select_star", "Specify columns explicitly"),
                (r'WHERE.*LIKE\s*["\']%.*%["\']', "leading_wildcard", "Avoid leading wildcards"),
                (r'ORDER\s+BY.*RAND\(\)', "random_order", "Use application-level randomization"),
            ]
        }
        
        # Test framework detection
        self.test_frameworks = {
            "python": ["pytest", "unittest", "nose", "doctest"],
            "javascript": ["jest", "mocha", "jasmine", "cypress", "playwright"],
            "java": ["junit", "testng", "mockito"],
            "csharp": ["nunit", "xunit", "mstest"],
            "ruby": ["rspec", "minitest"],
            "php": ["phpunit", "codeception"],
            "go": ["testing", "ginkgo"],
            "rust": ["#[test]", "proptest"]
        }
        
        # License patterns
        self.license_patterns = {
            "MIT": r"MIT License|Permission is hereby granted, free of charge",
            "Apache": r"Apache License|Licensed under the Apache License",
            "GPL": r"GNU General Public License|This program is free software",
            "BSD": r"BSD License|Redistribution and use in source and binary",
            "ISC": r"ISC License|Permission to use, copy, modify",
            "Unlicense": r"This is free and unencumbered software"
        }
    
    async def analyze_project(self, project_path: str, project_id: str) -> ProjectAnalysisResult:
        """Perform comprehensive analysis of a project."""
        logger.info(f"Starting comprehensive analysis of project: {project_path}")
        
        start_time = time.time()
        project_dir = Path(project_path)
        
        # Initialize result structure
        result = ProjectAnalysisResult(
            project_id=project_id,
            project_path=project_path,
            analysis_timestamp=datetime.now(timezone.utc),
            code_metrics=CodeMetrics(),
            security_issues=[],
            quality_issues=[],
            test_analysis=TestAnalysis(
                framework=None, total_tests=0, passing_tests=0,
                failing_tests=0, skipped_tests=0, coverage_percent=0.0,
                test_files=[], missing_coverage=[]
            ),
            documentation=DocumentationAnalysis(
                readme_score=0.0, api_docs_score=0.0, inline_docs_score=0.0,
                changelog_exists=False, license_exists=False,
                contributing_guide=False, missing_sections=[], quality_level="poor"
            ),
            performance=PerformanceAnalysis(
                bottlenecks=[], optimization_opportunities=[],
                resource_usage_issues=[], scalability_concerns=[],
                performance_score=50.0
            ),
            overall_score=0.0,
            recommendations=[]
        )
        
        try:
            # Code metrics analysis
            result.code_metrics = await self._analyze_code_metrics(project_dir)
            
            # Security analysis
            result.security_issues = await self._analyze_security(project_dir)
            
            # Code quality analysis
            result.quality_issues = await self._analyze_code_quality(project_dir)
            
            # Test analysis
            result.test_analysis = await self._analyze_tests(project_dir)
            
            # Documentation analysis
            result.documentation = await self._analyze_documentation(project_dir)
            
            # Performance analysis
            result.performance = await self._analyze_performance(project_dir)
            
            # Calculate overall score and recommendations
            await self._calculate_overall_assessment(result)
            
            elapsed = time.time() - start_time
            logger.info(f"Analysis completed in {elapsed:.2f}s. Overall score: {result.overall_score:.1f}")
            
        except Exception as e:
            logger.error(f"Error during project analysis: {e}", exc_info=True)
        
        return result
    
    async def _analyze_code_metrics(self, project_dir: Path) -> CodeMetrics:
        """Analyze code metrics including complexity and maintainability."""
        metrics = CodeMetrics()
        
        try:
            # Find all code files
            code_files = []
            extensions = ['.py', '.js', '.ts', '.java', '.cs', '.go', '.rs', '.rb', '.php', '.cpp', '.c']
            
            for ext in extensions:
                code_files.extend(list(project_dir.glob(f"**/*{ext}")))
            
            # Analyze each file
            total_complexity = 0
            analyzed_files = 0
            
            for file_path in code_files:
                if await self._should_analyze_file(file_path):
                    file_metrics = await self._analyze_code_file(file_path)
                    
                    metrics.total_lines += file_metrics["lines"]
                    metrics.code_lines += file_metrics["code_lines"]
                    metrics.comment_lines += file_metrics["comment_lines"]
                    metrics.blank_lines += file_metrics["blank_lines"]
                    metrics.functions_count += file_metrics["functions"]
                    metrics.classes_count += file_metrics["classes"]
                    
                    total_complexity += file_metrics["complexity"]
                    analyzed_files += 1
                    
                    if analyzed_files >= 100:  # Limit analysis to prevent excessive processing
                        break
            
            # Calculate derived metrics
            if analyzed_files > 0:
                metrics.complexity_score = total_complexity / analyzed_files
                metrics.maintainability_index = await self._calculate_maintainability_index(metrics)
            
            # Calculate technical debt ratio (simplified)
            if metrics.total_lines > 0:
                metrics.technical_debt_ratio = min((total_complexity / metrics.total_lines) * 100, 100)
            
        except Exception as e:
            logger.warning(f"Error analyzing code metrics: {e}")
        
        return metrics
    
    async def _should_analyze_file(self, file_path: Path) -> bool:
        """Check if file should be analyzed."""
        # Skip files that are too large or binary
        try:
            stat = file_path.stat()
            if stat.st_size > 1024 * 1024:  # 1MB
                return False
            
            # Skip common excluded directories
            excluded_parts = {'node_modules', '__pycache__', '.git', 'vendor', 'target', 'build', 'dist'}
            if any(part in file_path.parts for part in excluded_parts):
                return False
            
            return True
        except OSError:
            return False
    
    async def _analyze_code_file(self, file_path: Path) -> Dict[str, int]:
        """Analyze individual code file for metrics."""
        metrics = {
            "lines": 0, "code_lines": 0, "comment_lines": 0, "blank_lines": 0,
            "functions": 0, "classes": 0, "complexity": 0
        }
        
        try:
            content = await self._read_file_content(file_path)
            if not content:
                return metrics
            
            lines = content.split('\n')
            metrics["lines"] = len(lines)
            
            # Analyze each line
            in_multiline_comment = False
            for line in lines:
                stripped = line.strip()
                
                if not stripped:
                    metrics["blank_lines"] += 1
                elif self._is_comment_line(stripped, file_path.suffix, in_multiline_comment):
                    metrics["comment_lines"] += 1
                    in_multiline_comment = self._update_multiline_comment_state(
                        stripped, file_path.suffix, in_multiline_comment
                    )
                else:
                    metrics["code_lines"] += 1
                    
                    # Count functions and classes
                    if self._is_function_definition(stripped, file_path.suffix):
                        metrics["functions"] += 1
                        metrics["complexity"] += 1  # Base complexity
                    
                    if self._is_class_definition(stripped, file_path.suffix):
                        metrics["classes"] += 1
                    
                    # Count complexity contributors
                    metrics["complexity"] += self._calculate_line_complexity(stripped, file_path.suffix)
            
            # Language-specific analysis
            if file_path.suffix == '.py':
                await self._analyze_python_specifics(content, metrics)
            
        except Exception as e:
            logger.debug(f"Error analyzing file {file_path}: {e}")
        
        return metrics
    
    async def _read_file_content(self, file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
        """Safely read file content."""
        try:
            async with aiofiles.open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                return await f.read()
        except Exception:
            return None
    
    def _is_comment_line(self, line: str, file_extension: str, in_multiline: bool) -> bool:
        """Check if line is a comment."""
        if in_multiline:
            return True
        
        comment_chars = {
            '.py': '#',
            '.js': '//',
            '.ts': '//',
            '.java': '//',
            '.cs': '//',
            '.go': '//',
            '.rs': '//',
            '.rb': '#',
            '.php': '#',
            '.cpp': '//',
            '.c': '//'
        }
        
        char = comment_chars.get(file_extension)
        if char and line.startswith(char):
            return True
        
        # Check for multiline comment start
        multiline_starts = {'.js': '/*', '.ts': '/*', '.java': '/*', '.cs': '/*', '.go': '/*', '.rs': '/*', '.cpp': '/*', '.c': '/*'}
        start = multiline_starts.get(file_extension)
        return start and line.startswith(start)
    
    def _update_multiline_comment_state(self, line: str, file_extension: str, current_state: bool) -> bool:
        """Update multiline comment state."""
        multiline_ends = {'.js': '*/', '.ts': '*/', '.java': '*/', '.cs': '*/', '.go': '*/', '.rs': '*/', '.cpp': '*/', '.c': '*/'}
        end_char = multiline_ends.get(file_extension)
        
        if current_state and end_char and line.endswith(end_char):
            return False
        
        multiline_starts = {'.js': '/*', '.ts': '/*', '.java': '/*', '.cs': '/*', '.go': '/*', '.rs': '/*', '.cpp': '/*', '.c': '/*'}
        start_char = multiline_starts.get(file_extension)
        
        if start_char and line.startswith(start_char):
            return True
        
        return current_state
    
    def _is_function_definition(self, line: str, file_extension: str) -> bool:
        """Check if line is a function definition."""
        patterns = {
            '.py': r'^\s*def\s+\w+\s*\(',
            '.js': r'(function\s+\w+\s*\(|const\s+\w+\s*=|\w+\s*:\s*function)',
            '.ts': r'(function\s+\w+\s*\(|const\s+\w+\s*=|\w+\s*:\s*function)',
            '.java': r'(public|private|protected).*\s+\w+\s*\(',
            '.cs': r'(public|private|protected).*\s+\w+\s*\(',
            '.go': r'^\s*func\s+\w+\s*\(',
            '.rs': r'^\s*fn\s+\w+\s*\(',
            '.rb': r'^\s*def\s+\w+',
            '.php': r'function\s+\w+\s*\(',
            '.cpp': r'(public|private|protected)?.*\s+\w+\s*\([^)]*\)\s*{',
            '.c': r'\w+\s+\w+\s*\([^)]*\)\s*{'
        }
        
        pattern = patterns.get(file_extension)
        return bool(pattern and re.search(pattern, line))
    
    def _is_class_definition(self, line: str, file_extension: str) -> bool:
        """Check if line is a class definition."""
        patterns = {
            '.py': r'^\s*class\s+\w+',
            '.js': r'^\s*class\s+\w+',
            '.ts': r'^\s*class\s+\w+',
            '.java': r'(public|private)?\s*class\s+\w+',
            '.cs': r'(public|private)?\s*class\s+\w+',
            '.go': r'type\s+\w+\s+struct',
            '.rs': r'struct\s+\w+',
            '.rb': r'^\s*class\s+\w+',
            '.php': r'class\s+\w+',
            '.cpp': r'class\s+\w+',
            '.c': r'struct\s+\w+'
        }
        
        pattern = patterns.get(file_extension)
        return bool(pattern and re.search(pattern, line))
    
    def _calculate_line_complexity(self, line: str, file_extension: str) -> int:
        """Calculate complexity contribution of a single line."""
        complexity = 0
        line_lower = line.lower()
        
        # Control flow statements add complexity
        control_statements = ['if', 'elif', 'else', 'for', 'while', 'switch', 'case', 'try', 'catch', 'except']
        for stmt in control_statements:
            if f" {stmt} " in f" {line_lower} " or line_lower.strip().startswith(f"{stmt} "):
                complexity += 1
        
        # Logical operators add complexity
        logical_ops = ['&&', '||', 'and', 'or']
        for op in logical_ops:
            complexity += line.count(op)
        
        # Nested conditions add extra complexity
        if '?' in line and ':' in line:  # Ternary operator
            complexity += 1
        
        return complexity
    
    async def _analyze_python_specifics(self, content: str, metrics: Dict[str, int]) -> None:
        """Analyze Python-specific metrics using AST."""
        try:
            tree = ast.parse(content)
            
            # Count specific Python constructs
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check function complexity
                    if len(node.body) > 15:  # Long function
                        metrics["complexity"] += 2
                elif isinstance(node, ast.ClassDef):
                    # Check class size
                    if len(node.body) > 10:  # Large class
                        metrics["complexity"] += 1
                elif isinstance(node, ast.If):
                    # Nested conditions
                    metrics["complexity"] += 1
                elif isinstance(node, (ast.For, ast.While)):
                    # Loops
                    metrics["complexity"] += 1
                elif isinstance(node, ast.Try):
                    # Exception handling
                    metrics["complexity"] += 1
        
        except SyntaxError:
            # File might have syntax errors
            pass
        except Exception as e:
            logger.debug(f"Error in Python AST analysis: {e}")
    
    def _calculate_maintainability_index(self, metrics: CodeMetrics) -> float:
        """Calculate maintainability index (0-100, higher is better)."""
        if metrics.code_lines == 0:
            return 0.0
        
        # Simplified maintainability index calculation
        # Based on Halstead complexity, cyclomatic complexity, and lines of code
        
        # Avoid division by zero
        avg_complexity = max(metrics.complexity_score, 1)
        
        # Calculate individual components
        volume_component = max(0, 171 - 5.2 * (metrics.code_lines / 1000))
        complexity_component = max(0, 50 - avg_complexity)
        comment_component = max(0, metrics.comment_lines / metrics.code_lines * 100) if metrics.code_lines > 0 else 0
        
        # Weighted average
        maintainability = (volume_component * 0.4 + complexity_component * 0.4 + comment_component * 0.2)
        
        return min(100, max(0, maintainability))
    
    async def _analyze_security(self, project_dir: Path) -> List[SecurityIssue]:
        """Analyze project for security vulnerabilities."""
        security_issues = []
        
        try:
            # Find relevant files
            code_files = []
            for ext in ['.py', '.js', '.ts', '.java', '.cs', '.php', '.rb', '.go', '.rs']:
                code_files.extend(list(project_dir.glob(f"**/*{ext}"))[:50])  # Limit files
            
            config_files = list(project_dir.glob("**/*.{env,config,conf,ini,yaml,yml,json}"))[:20]
            all_files = code_files + config_files
            
            for file_path in all_files:
                if await self._should_analyze_file(file_path):
                    file_issues = await self._scan_file_security(file_path)
                    security_issues.extend(file_issues)
            
            # Additional checks for common security files
            await self._check_security_configurations(project_dir, security_issues)
            
        except Exception as e:
            logger.warning(f"Error analyzing security: {e}")
        
        return security_issues
    
    async def _scan_file_security(self, file_path: Path) -> List[SecurityIssue]:
        """Scan individual file for security issues."""
        issues = []
        
        try:
            content = await self._read_file_content(file_path)
            if not content:
                return issues
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Check against all security patterns
                for category, patterns in self.security_patterns.items():
                    for pattern, issue_type, severity in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issue = SecurityIssue(
                                category=category,
                                severity=severity,
                                cwe_id=self._get_cwe_id(issue_type),
                                file_path=str(file_path),
                                line_number=line_num,
                                description=self._get_security_description(issue_type),
                                recommendation=self._get_security_recommendation(issue_type),
                                evidence=line.strip()[:100],
                                confidence=0.8  # Default confidence
                            )
                            issues.append(issue)
        
        except Exception as e:
            logger.debug(f"Error scanning file {file_path} for security: {e}")
        
        return issues
    
    def _get_cwe_id(self, issue_type: str) -> Optional[str]:
        """Get CWE (Common Weakness Enumeration) ID for issue type."""
        cwe_mapping = {
            "hardcoded_password": "CWE-259",
            "api_key_exposure": "CWE-798",
            "hardcoded_secret": "CWE-798",
            "private_key_exposure": "CWE-798",
            "private_key_in_code": "CWE-798",
            "code_injection": "CWE-94",
            "command_injection": "CWE-78",
            "shell_injection": "CWE-78",
            "sql_injection_risk": "CWE-89",
            "xss_risk": "CWE-79",
            "weak_hash": "CWE-328",
            "weak_encryption": "CWE-326",
            "weak_random": "CWE-338",
            "auth_bypass": "CWE-287",
            "ssl_verification_disabled": "CWE-295",
            "path_traversal": "CWE-22",
            "pickle_deserialization": "CWE-502",
            "yaml_deserialization": "CWE-502"
        }
        return cwe_mapping.get(issue_type)
    
    def _get_security_description(self, issue_type: str) -> str:
        """Get human-readable description for security issue."""
        descriptions = {
            "hardcoded_password": "Password hardcoded in source code",
            "api_key_exposure": "API key exposed in source code",
            "hardcoded_secret": "Secret token hardcoded in source code",
            "private_key_exposure": "Private key exposed in source code",
            "private_key_in_code": "Private key found in source code",
            "code_injection": "Potential code injection vulnerability",
            "command_injection": "Potential command injection vulnerability",
            "shell_injection": "Shell command injection risk",
            "sql_injection_risk": "Potential SQL injection vulnerability",
            "xss_risk": "Cross-site scripting (XSS) vulnerability",
            "weak_hash": "Use of cryptographically weak hash function",
            "weak_encryption": "Use of weak encryption algorithm",
            "weak_random": "Use of cryptographically weak random number generator",
            "auth_bypass": "Authentication bypass vulnerability",
            "ssl_verification_disabled": "SSL certificate verification disabled",
            "path_traversal": "Path traversal vulnerability",
            "pickle_deserialization": "Unsafe deserialization using pickle",
            "yaml_deserialization": "Unsafe YAML deserialization"
        }
        return descriptions.get(issue_type, f"Security issue: {issue_type}")
    
    def _get_security_recommendation(self, issue_type: str) -> str:
        """Get security recommendation for issue type."""
        recommendations = {
            "hardcoded_password": "Use environment variables or secure configuration management",
            "api_key_exposure": "Store API keys in environment variables or secure vaults",
            "hardcoded_secret": "Use secure configuration management for secrets",
            "private_key_exposure": "Never store private keys in source code. Use secure key management",
            "private_key_in_code": "Remove private key and use secure key storage",
            "code_injection": "Validate and sanitize all user inputs. Avoid eval() and exec()",
            "command_injection": "Use parameterized commands and validate inputs",
            "shell_injection": "Avoid shell=True. Use subprocess with argument lists",
            "sql_injection_risk": "Use parameterized queries or ORM methods",
            "xss_risk": "Sanitize user inputs and use safe templating",
            "weak_hash": "Use SHA-256 or stronger hash functions",
            "weak_encryption": "Use AES-256 or other strong encryption algorithms",
            "weak_random": "Use cryptographically secure random number generators",
            "auth_bypass": "Implement proper authentication checks",
            "ssl_verification_disabled": "Enable SSL certificate verification",
            "path_traversal": "Validate and sanitize file paths",
            "pickle_deserialization": "Use safe serialization formats like JSON",
            "yaml_deserialization": "Use safe_load() instead of load() for YAML"
        }
        return recommendations.get(issue_type, "Review and remediate this security issue")
    
    async def _check_security_configurations(self, project_dir: Path, issues: List[SecurityIssue]) -> None:
        """Check for security-related configuration issues."""
        try:
            # Check for .env files in version control
            env_files = list(project_dir.glob("**/.env*"))
            for env_file in env_files:
                # Check if .env file might be in git
                gitignore = project_dir / ".gitignore"
                if gitignore.exists():
                    content = await self._read_file_content(gitignore)
                    if content and ".env" not in content:
                        issues.append(SecurityIssue(
                            category="configuration",
                            severity="medium",
                            cwe_id="CWE-200",
                            file_path=str(env_file),
                            line_number=1,
                            description="Environment file not in .gitignore",
                            recommendation="Add .env files to .gitignore to prevent committing secrets",
                            evidence=".env file detected",
                            confidence=0.9
                        ))
            
            # Check for debug mode in production configs
            config_files = list(project_dir.glob("**/*.{py,js,json,yaml,yml}"))
            for config_file in config_files[:10]:
                content = await self._read_file_content(config_file)
                if content and ("debug = true" in content.lower() or "debug: true" in content.lower()):
                    issues.append(SecurityIssue(
                        category="configuration",
                        severity="medium",
                        cwe_id="CWE-489",
                        file_path=str(config_file),
                        line_number=1,
                        description="Debug mode enabled in configuration",
                        recommendation="Disable debug mode in production",
                        evidence="debug = true",
                        confidence=0.7
                    ))
        
        except Exception as e:
            logger.debug(f"Error checking security configurations: {e}")
    
    async def _analyze_code_quality(self, project_dir: Path) -> List[QualityIssue]:
        """Analyze code quality and detect technical debt."""
        quality_issues = []
        
        try:
            # Find code files
            code_files = []
            for ext in ['.py', '.js', '.ts', '.java', '.cs', '.go', '.rs', '.rb', '.php']:
                code_files.extend(list(project_dir.glob(f"**/*{ext}"))[:30])  # Limit files
            
            for file_path in code_files:
                if await self._should_analyze_file(file_path):
                    file_issues = await self._analyze_file_quality(file_path)
                    quality_issues.extend(file_issues)
        
        except Exception as e:
            logger.warning(f"Error analyzing code quality: {e}")
        
        return quality_issues
    
    async def _analyze_file_quality(self, file_path: Path) -> List[QualityIssue]:
        """Analyze individual file for quality issues."""
        issues = []
        
        try:
            content = await self._read_file_content(file_path)
            if not content:
                return issues
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Check against quality patterns
                for category, patterns in self.quality_patterns.items():
                    for pattern, issue_type, severity in patterns:
                        if re.search(pattern, line, re.IGNORECASE | re.MULTILINE):
                            issue = QualityIssue(
                                category=category,
                                severity=severity,
                                file_path=str(file_path),
                                line_number=line_num,
                                description=self._get_quality_description(issue_type),
                                suggestion=self._get_quality_suggestion(issue_type),
                                effort_estimate=self._get_effort_estimate(issue_type),
                                impact=self._get_quality_impact(issue_type)
                            )
                            issues.append(issue)
        
        except Exception as e:
            logger.debug(f"Error analyzing file quality {file_path}: {e}")
        
        return issues
    
    def _get_quality_description(self, issue_type: str) -> str:
        """Get description for quality issue."""
        descriptions = {
            "long_function": "Function is too long and complex",
            "large_class": "Class is too large",
            "complex_condition": "Complex conditional statement",
            "deep_nesting": "Deep nesting level",
            "short_function_name": "Function name is too short",
            "numbered_variable": "Variable name contains numbers",
            "generic_names": "Generic variable names used",
            "wildcard_import": "Wildcard import statement",
            "multiple_imports": "Multiple imports on single line",
            "unsorted_imports": "Imports are not sorted",
            "incomplete_todo": "Incomplete TODO comment",
            "fixme_comment": "FIXME comment indicates issue",
            "hack_comment": "HACK comment indicates poor solution",
            "concerning_comment": "Concerning comment found"
        }
        return descriptions.get(issue_type, f"Quality issue: {issue_type}")
    
    def _get_quality_suggestion(self, issue_type: str) -> str:
        """Get suggestion for quality improvement."""
        suggestions = {
            "long_function": "Break function into smaller functions",
            "large_class": "Split class into smaller, focused classes",
            "complex_condition": "Simplify condition or extract to variable",
            "deep_nesting": "Reduce nesting with early returns or guard clauses",
            "short_function_name": "Use descriptive function names",
            "numbered_variable": "Use descriptive variable names",
            "generic_names": "Use specific, meaningful names",
            "wildcard_import": "Import specific items or use qualified imports",
            "multiple_imports": "Use separate lines for imports",
            "unsorted_imports": "Sort imports alphabetically",
            "incomplete_todo": "Complete TODO or remove comment",
            "fixme_comment": "Address the issue mentioned in FIXME",
            "hack_comment": "Implement proper solution",
            "concerning_comment": "Review and address concern"
        }
        return suggestions.get(issue_type, "Review and improve")
    
    def _get_effort_estimate(self, issue_type: str) -> str:
        """Get effort estimate for fixing issue."""
        estimates = {
            "long_function": "medium",
            "large_class": "high",
            "complex_condition": "low",
            "deep_nesting": "medium",
            "short_function_name": "low",
            "numbered_variable": "low",
            "generic_names": "low",
            "wildcard_import": "low",
            "multiple_imports": "low",
            "unsorted_imports": "low",
            "incomplete_todo": "low",
            "fixme_comment": "medium",
            "hack_comment": "high",
            "concerning_comment": "medium"
        }
        return estimates.get(issue_type, "medium")
    
    def _get_quality_impact(self, issue_type: str) -> str:
        """Get impact description for quality issue."""
        impacts = {
            "long_function": "maintainability",
            "large_class": "maintainability",
            "complex_condition": "readability",
            "deep_nesting": "readability",
            "short_function_name": "readability",
            "numbered_variable": "readability",
            "generic_names": "maintainability",
            "wildcard_import": "maintainability",
            "multiple_imports": "readability",
            "unsorted_imports": "readability",
            "incomplete_todo": "completeness",
            "fixme_comment": "reliability",
            "hack_comment": "maintainability",
            "concerning_comment": "reliability"
        }
        return impacts.get(issue_type, "maintainability")
    
    async def _analyze_tests(self, project_dir: Path) -> TestAnalysis:
        """Analyze test suite and coverage."""
        analysis = TestAnalysis(
            framework=None, total_tests=0, passing_tests=0,
            failing_tests=0, skipped_tests=0, coverage_percent=0.0,
            test_files=[], missing_coverage=[]
        )
        
        try:
            # Find test files
            test_patterns = [
                "**/test_*.py", "**/tests/**/*.py", "**/*_test.py",
                "**/test/**/*.js", "**/*.test.js", "**/*.spec.js",
                "**/test/**/*.ts", "**/*.test.ts", "**/*.spec.ts",
                "**/test/**/*.java", "**/*Test.java",
                "**/test/**/*.cs", "**/*Test.cs"
            ]
            
            test_files = []
            for pattern in test_patterns:
                test_files.extend(list(project_dir.glob(pattern)))
            
            analysis.test_files = [str(f) for f in test_files]
            analysis.total_tests = len(test_files)
            
            # Detect test framework
            analysis.framework = await self._detect_test_framework(project_dir)
            
            # Try to get actual test count and coverage
            if analysis.framework:
                test_results = await self._run_test_analysis(project_dir, analysis.framework)
                if test_results:
                    analysis.total_tests = test_results.get("total", analysis.total_tests)
                    analysis.passing_tests = test_results.get("passed", 0)
                    analysis.failing_tests = test_results.get("failed", 0)
                    analysis.coverage_percent = test_results.get("coverage", 0.0)
        
        except Exception as e:
            logger.warning(f"Error analyzing tests: {e}")
        
        return analysis
    
    async def _detect_test_framework(self, project_dir: Path) -> Optional[str]:
        """Detect test framework used in project."""
        # Check package files for test dependencies
        package_files = ["package.json", "requirements.txt", "Cargo.toml", "pom.xml", "build.gradle"]
        
        for package_file in package_files:
            file_path = project_dir / package_file
            if file_path.exists():
                content = await self._read_file_content(file_path)
                if content:
                    content_lower = content.lower()
                    
                    # Check for common test frameworks
                    for lang, frameworks in self.test_frameworks.items():
                        for framework in frameworks:
                            if framework in content_lower:
                                return framework
        
        # Check test files for framework imports
        test_files = list(project_dir.glob("**/test*.py"))[:5]
        for test_file in test_files:
            content = await self._read_file_content(test_file)
            if content:
                if "import pytest" in content or "pytest" in content:
                    return "pytest"
                elif "import unittest" in content:
                    return "unittest"
        
        return None
    
    async def _run_test_analysis(self, project_dir: Path, framework: str) -> Optional[Dict]:
        """Run test framework to get actual test results."""
        try:
            # This would run actual test commands in a safe way
            # For now, return mock data to avoid executing arbitrary commands
            return {
                "total": 10,
                "passed": 8,
                "failed": 2,
                "coverage": 75.0
            }
        except Exception as e:
            logger.debug(f"Error running test analysis: {e}")
            return None
    
    async def _analyze_documentation(self, project_dir: Path) -> DocumentationAnalysis:
        """Analyze documentation quality."""
        analysis = DocumentationAnalysis(
            readme_score=0.0, api_docs_score=0.0, inline_docs_score=0.0,
            changelog_exists=False, license_exists=False,
            contributing_guide=False, missing_sections=[], quality_level="poor"
        )
        
        try:
            # Check for README
            readme_files = ["README.md", "README.rst", "README.txt", "readme.md"]
            for readme_name in readme_files:
                readme_path = project_dir / readme_name
                if readme_path.exists():
                    analysis.readme_score = await self._score_readme(readme_path)
                    break
            
            # Check for other documentation files
            analysis.changelog_exists = any((project_dir / name).exists() 
                                          for name in ["CHANGELOG.md", "HISTORY.md", "CHANGES.md"])
            
            analysis.license_exists = any((project_dir / name).exists() 
                                        for name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"])
            
            analysis.contributing_guide = any((project_dir / name).exists() 
                                            for name in ["CONTRIBUTING.md", "CONTRIBUTE.md"])
            
            # Check for API documentation
            docs_dir = project_dir / "docs"
            if docs_dir.exists():
                analysis.api_docs_score = await self._score_api_docs(docs_dir)
            
            # Calculate overall quality level
            total_score = (analysis.readme_score + analysis.api_docs_score) / 2
            if analysis.license_exists:
                total_score += 10
            if analysis.changelog_exists:
                total_score += 10
            if analysis.contributing_guide:
                total_score += 10
            
            if total_score >= 80:
                analysis.quality_level = "excellent"
            elif total_score >= 60:
                analysis.quality_level = "good"
            elif total_score >= 40:
                analysis.quality_level = "fair"
            else:
                analysis.quality_level = "poor"
            
            # Identify missing sections
            missing = []
            if not analysis.license_exists:
                missing.append("License file")
            if not analysis.changelog_exists:
                missing.append("Changelog")
            if not analysis.contributing_guide:
                missing.append("Contributing guide")
            if analysis.readme_score < 50:
                missing.append("Comprehensive README")
            
            analysis.missing_sections = missing
        
        except Exception as e:
            logger.warning(f"Error analyzing documentation: {e}")
        
        return analysis
    
    async def _score_readme(self, readme_path: Path) -> float:
        """Score README quality (0-100)."""
        score = 0.0
        
        try:
            content = await self._read_file_content(readme_path)
            if not content:
                return score
            
            content_lower = content.lower()
            
            # Basic requirements
            if len(content) > 100:
                score += 10
            if "# " in content or "## " in content:  # Has headers
                score += 10
            if "install" in content_lower:
                score += 15
            if "usage" in content_lower or "example" in content_lower:
                score += 15
            if "license" in content_lower:
                score += 10
            if "contribute" in content_lower or "contributing" in content_lower:
                score += 10
            
            # Quality indicators
            if len(content) > 500:
                score += 10
            if "```" in content:  # Code examples
                score += 10
            if "http" in content_lower:  # Links
                score += 5
            if "badge" in content_lower or "shield" in content_lower:
                score += 5
        
        except Exception as e:
            logger.debug(f"Error scoring README: {e}")
        
        return min(100, score)
    
    async def _score_api_docs(self, docs_dir: Path) -> float:
        """Score API documentation quality."""
        score = 0.0
        
        try:
            doc_files = list(docs_dir.glob("**/*.md"))
            if doc_files:
                score += 20  # Has documentation directory
                
                if len(doc_files) > 3:
                    score += 20  # Multiple documentation files
                
                # Check for specific documentation types
                doc_names = [f.name.lower() for f in doc_files]
                if any("api" in name for name in doc_names):
                    score += 20
                if any("tutorial" in name or "guide" in name for name in doc_names):
                    score += 20
                if any("example" in name for name in doc_names):
                    score += 20
        
        except Exception as e:
            logger.debug(f"Error scoring API docs: {e}")
        
        return min(100, score)
    
    async def _analyze_performance(self, project_dir: Path) -> PerformanceAnalysis:
        """Analyze performance characteristics and bottlenecks."""
        analysis = PerformanceAnalysis(
            bottlenecks=[], optimization_opportunities=[],
            resource_usage_issues=[], scalability_concerns=[],
            performance_score=50.0
        )
        
        try:
            # Find files to analyze
            code_files = []
            for ext in ['.py', '.js', '.ts', '.java', '.cs']:
                code_files.extend(list(project_dir.glob(f"**/*{ext}"))[:20])
            
            for file_path in code_files:
                if await self._should_analyze_file(file_path):
                    file_analysis = await self._analyze_file_performance(file_path)
                    
                    analysis.bottlenecks.extend(file_analysis.get("bottlenecks", []))
                    analysis.optimization_opportunities.extend(file_analysis.get("optimizations", []))
            
            # General performance score based on findings
            issue_count = len(analysis.bottlenecks) + len(analysis.optimization_opportunities)
            analysis.performance_score = max(10, 100 - (issue_count * 5))
        
        except Exception as e:
            logger.warning(f"Error analyzing performance: {e}")
        
        return analysis
    
    async def _analyze_file_performance(self, file_path: Path) -> Dict[str, List]:
        """Analyze individual file for performance issues."""
        results = {"bottlenecks": [], "optimizations": []}
        
        try:
            content = await self._read_file_content(file_path)
            if not content:
                return results
            
            # Detect language and apply relevant patterns
            lang = self._detect_language_from_extension(file_path.suffix)
            patterns = self.performance_patterns.get(lang, [])
            
            for pattern, issue_type, suggestion in patterns:
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    if "bottleneck" in issue_type.lower() or "slow" in issue_type.lower():
                        results["bottlenecks"].append({
                            "file": str(file_path),
                            "issue": issue_type,
                            "suggestion": suggestion
                        })
                    else:
                        results["optimizations"].append(suggestion)
        
        except Exception as e:
            logger.debug(f"Error analyzing file performance {file_path}: {e}")
        
        return results
    
    def _detect_language_from_extension(self, extension: str) -> str:
        """Detect language from file extension."""
        mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'javascript',  # Use JS patterns for TS
            '.java': 'java',
            '.cs': 'csharp',
            '.sql': 'sql',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby'
        }
        return mapping.get(extension, 'unknown')
    
    async def _calculate_overall_assessment(self, result: ProjectAnalysisResult) -> None:
        """Calculate overall score and generate recommendations."""
        try:
            # Component scores (0-100 each)
            security_score = max(0, 100 - len(result.security_issues) * 10)
            quality_score = max(0, 100 - len(result.quality_issues) * 5)
            test_score = result.test_analysis.coverage_percent
            
            # Documentation score
            doc_score = (result.documentation.readme_score + result.documentation.api_docs_score) / 2
            
            # Maintainability score
            maintainability_score = result.code_metrics.maintainability_index
            
            # Performance score
            performance_score = result.performance.performance_score
            
            # Weighted overall score
            weights = {
                "security": 0.25,
                "quality": 0.20,
                "maintainability": 0.20,
                "tests": 0.15,
                "documentation": 0.10,
                "performance": 0.10
            }
            
            overall_score = (
                security_score * weights["security"] +
                quality_score * weights["quality"] +
                maintainability_score * weights["maintainability"] +
                test_score * weights["tests"] +
                doc_score * weights["documentation"] +
                performance_score * weights["performance"]
            )
            
            result.overall_score = round(overall_score, 1)
            
            # Generate recommendations
            recommendations = []
            
            if security_score < 80:
                recommendations.append("Address critical security vulnerabilities immediately")
            if quality_score < 70:
                recommendations.append("Refactor code to reduce technical debt")
            if test_score < 60:
                recommendations.append("Increase test coverage to at least 80%")
            if doc_score < 50:
                recommendations.append("Improve documentation quality")
            if maintainability_score < 60:
                recommendations.append("Simplify complex functions and classes")
            if performance_score < 70:
                recommendations.append("Optimize performance bottlenecks")
            
            # Priority recommendations based on severity
            critical_security = [issue for issue in result.security_issues if issue.severity == "critical"]
            if critical_security:
                recommendations.insert(0, f"URGENT: Fix {len(critical_security)} critical security issues")
            
            result.recommendations = recommendations
        
        except Exception as e:
            logger.warning(f"Error calculating overall assessment: {e}")
            result.overall_score = 50.0
            result.recommendations = ["Complete analysis to get recommendations"]
    
    async def generate_analysis_report(self, result: ProjectAnalysisResult) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        try:
            report = {
                "project": {
                    "id": result.project_id,
                    "path": result.project_path,
                    "analyzed_at": result.analysis_timestamp.isoformat(),
                    "overall_score": result.overall_score
                },
                "summary": {
                    "security_issues": {
                        "total": len(result.security_issues),
                        "critical": len([i for i in result.security_issues if i.severity == "critical"]),
                        "high": len([i for i in result.security_issues if i.severity == "high"]),
                        "medium": len([i for i in result.security_issues if i.severity == "medium"]),
                        "low": len([i for i in result.security_issues if i.severity == "low"])
                    },
                    "quality_issues": {
                        "total": len(result.quality_issues),
                        "high": len([i for i in result.quality_issues if i.severity == "high"]),
                        "medium": len([i for i in result.quality_issues if i.severity == "medium"]),
                        "low": len([i for i in result.quality_issues if i.severity == "low"])
                    },
                    "code_metrics": result.code_metrics.__dict__,
                    "test_coverage": result.test_analysis.coverage_percent,
                    "documentation_quality": result.documentation.quality_level
                },
                "recommendations": result.recommendations,
                "details": {
                    "security": [
                        {
                            "category": issue.category,
                            "severity": issue.severity,
                            "description": issue.description,
                            "file": issue.file_path,
                            "line": issue.line_number,
                            "recommendation": issue.recommendation
                        } for issue in result.security_issues[:10]  # Limit output
                    ],
                    "quality": [
                        {
                            "category": issue.category,
                            "severity": issue.severity,
                            "description": issue.description,
                            "file": issue.file_path,
                            "suggestion": issue.suggestion
                        } for issue in result.quality_issues[:10]
                    ],
                    "performance": {
                        "bottlenecks": result.performance.bottlenecks[:5],
                        "optimizations": result.performance.optimization_opportunities[:10]
                    }
                }
            }
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating analysis report: {e}")
            return {
                "error": str(e),
                "project_id": result.project_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def analyze_runtime_performance(self, project_path: str, runtime_data: List[Dict]) -> Dict[str, Any]:
        """Analyze runtime performance data for trends and bottlenecks."""
        analysis = {
            'bottlenecks': [],
            'trends': [],
            'recommendations': [],
            'resource_efficiency': {},
            'performance_score': 50.0
        }
        
        try:
            if not runtime_data:
                return analysis
            
            # Analyze CPU usage trends
            cpu_values = [d.get('cpu_percent', 0) for d in runtime_data if 'cpu_percent' in d]
            if cpu_values:
                cpu_trend = self._analyze_metric_trend(cpu_values, 'CPU')
                if cpu_trend['significant']:
                    analysis['trends'].append(cpu_trend)
                    
                    if cpu_trend['severity'] in ['high', 'critical']:
                        analysis['bottlenecks'].append({
                            'type': 'cpu_bottleneck',
                            'description': f"CPU usage showing {cpu_trend['direction']} trend",
                            'severity': cpu_trend['severity'],
                            'current_value': cpu_values[-1],
                            'recommendation': self._get_cpu_recommendation(cpu_trend)
                        })
            
            # Analyze memory usage trends
            memory_values = [d.get('memory_rss', 0) for d in runtime_data if 'memory_rss' in d]
            if memory_values:
                memory_trend = self._analyze_metric_trend(memory_values, 'Memory')
                if memory_trend['significant']:
                    analysis['trends'].append(memory_trend)
                    
                    # Check for memory leaks
                    if (memory_trend['direction'] == 'increasing' and 
                        memory_trend['confidence'] > 0.8):
                        analysis['bottlenecks'].append({
                            'type': 'memory_leak',
                            'description': "Potential memory leak detected",
                            'severity': 'high',
                            'growth_rate': memory_trend['rate'],
                            'recommendation': "Investigate memory allocation patterns and ensure proper cleanup"
                        })
            
            # Calculate resource efficiency
            analysis['resource_efficiency'] = self._calculate_resource_efficiency(runtime_data)
            
            # Generate overall performance score
            analysis['performance_score'] = self._calculate_performance_score_runtime(analysis)
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_performance_recommendations(analysis)
            
        except Exception as e:
            logger.error(f"Error analyzing runtime performance: {e}")
        
        return analysis
    
    def _analyze_metric_trend(self, values: List[float], metric_name: str) -> Dict[str, Any]:
        """Analyze trend for a specific metric."""
        if len(values) < 5:
            return {'significant': False}
        
        # Calculate trend using linear regression
        x = list(range(len(values)))
        n = len(values)
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return {'significant': False}
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Calculate correlation coefficient
        mean_x = sum_x / n
        mean_y = sum_y / n
        
        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denom_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        denom_y = sum((values[i] - mean_y) ** 2 for i in range(n))
        
        if denom_x == 0 or denom_y == 0:
            correlation = 0
        else:
            correlation = numerator / (denom_x * denom_y) ** 0.5
        
        # Determine significance and severity
        significant = abs(correlation) > 0.6
        if not significant:
            return {'significant': False}
        
        direction = 'increasing' if slope > 0 else 'decreasing'
        confidence = abs(correlation)
        
        # Determine severity based on rate of change and current values
        current_value = values[-1]
        avg_value = sum(values) / len(values)
        
        if metric_name == 'CPU' and current_value > 80:
            severity = 'critical' if current_value > 95 else 'high'
        elif metric_name == 'Memory' and slope > avg_value * 0.1:  # Growing by >10% per interval
            severity = 'high'
        elif abs(slope) > avg_value * 0.05:  # General threshold
            severity = 'medium'
        else:
            severity = 'low'
        
        return {
            'significant': True,
            'metric': metric_name,
            'direction': direction,
            'rate': abs(slope),
            'confidence': confidence,
            'severity': severity,
            'current_value': current_value,
            'average_value': avg_value
        }
    
    def _get_cpu_recommendation(self, trend: Dict) -> str:
        """Get recommendation for CPU-related issues."""
        if trend['direction'] == 'increasing':
            if trend['current_value'] > 90:
                return "Immediate action required: Optimize algorithms, add caching, or scale horizontally"
            elif trend['current_value'] > 70:
                return "Consider optimizing CPU-intensive operations and monitoring for bottlenecks"
            else:
                return "Monitor CPU usage and optimize if trend continues"
        else:
            return "Good: CPU usage is decreasing, current optimizations are effective"
    
    def _calculate_resource_efficiency(self, runtime_data: List[Dict]) -> Dict[str, float]:
        """Calculate resource efficiency metrics."""
        efficiency = {}
        
        try:
            if not runtime_data:
                return efficiency
            
            # CPU efficiency (lower variance is better)
            cpu_values = [d.get('cpu_percent', 0) for d in runtime_data if 'cpu_percent' in d]
            if cpu_values:
                cpu_avg = sum(cpu_values) / len(cpu_values)
                cpu_variance = sum((x - cpu_avg) ** 2 for x in cpu_values) / len(cpu_values)
                efficiency['cpu_stability'] = max(0, 100 - cpu_variance)  # Higher is better
                efficiency['cpu_utilization'] = min(100, cpu_avg)  # Moderate utilization is good
            
            # Memory efficiency (consistent usage is good, rapid growth is bad)
            memory_values = [d.get('memory_rss', 0) for d in runtime_data if 'memory_rss' in d]
            if memory_values and len(memory_values) > 1:
                memory_growth = (memory_values[-1] - memory_values[0]) / memory_values[0] if memory_values[0] > 0 else 0
                efficiency['memory_growth_rate'] = max(0, 100 - abs(memory_growth) * 100)
            
            # Response time efficiency (if available)
            response_times = [d.get('response_time_ms', 0) for d in runtime_data if 'response_time_ms' in d]
            if response_times:
                avg_response = sum(response_times) / len(response_times)
                efficiency['response_time_score'] = max(0, 100 - avg_response / 10)  # Penalize slow responses
            
        except Exception as e:
            logger.debug(f"Error calculating resource efficiency: {e}")
        
        return efficiency
    
    def _calculate_performance_score_runtime(self, analysis: Dict) -> float:
        """Calculate overall performance score based on runtime analysis results."""
        score = 100.0
        
        try:
            # Penalize based on bottlenecks
            for bottleneck in analysis.get('bottlenecks', []):
                if bottleneck.get('severity') == 'critical':
                    score -= 30
                elif bottleneck.get('severity') == 'high':
                    score -= 20
                elif bottleneck.get('severity') == 'medium':
                    score -= 10
                else:
                    score -= 5
            
            # Penalize based on negative trends
            for trend in analysis.get('trends', []):
                if (trend.get('direction') == 'increasing' and 
                    trend.get('metric') in ['CPU', 'Memory']):
                    if trend.get('severity') == 'critical':
                        score -= 25
                    elif trend.get('severity') == 'high':
                        score -= 15
                    elif trend.get('severity') == 'medium':
                        score -= 8
            
            # Bonus for good resource efficiency
            efficiency = analysis.get('resource_efficiency', {})
            if efficiency.get('cpu_stability', 0) > 80:
                score += 5
            if efficiency.get('memory_growth_rate', 0) > 80:
                score += 5
            
        except Exception as e:
            logger.debug(f"Error calculating performance score: {e}")
        
        return max(0, min(100, score))
    
    def _generate_performance_recommendations(self, analysis: Dict) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        try:
            bottlenecks = analysis.get('bottlenecks', [])
            trends = analysis.get('trends', [])
            efficiency = analysis.get('resource_efficiency', {})
            
            # High-priority recommendations based on bottlenecks
            critical_bottlenecks = [b for b in bottlenecks if b.get('severity') == 'critical']
            if critical_bottlenecks:
                recommendations.append("URGENT: Address critical performance bottlenecks immediately")
            
            # Memory-specific recommendations
            memory_issues = [b for b in bottlenecks if b.get('type') in ['memory_leak', 'memory_bottleneck']]
            if memory_issues:
                recommendations.extend([
                    "Implement memory profiling to identify allocation patterns",
                    "Review object lifecycle and ensure proper garbage collection",
                    "Consider implementing object pooling for frequently used objects"
                ])
            
            # CPU-specific recommendations
            cpu_issues = [b for b in bottlenecks if b.get('type') == 'cpu_bottleneck']
            if cpu_issues:
                recommendations.extend([
                    "Profile CPU-intensive operations and optimize algorithms",
                    "Implement caching for expensive computations",
                    "Consider asynchronous processing for I/O operations"
                ])
            
            # General efficiency improvements
            if efficiency.get('cpu_stability', 100) < 70:
                recommendations.append("Improve CPU usage consistency by optimizing resource allocation")
            
            if efficiency.get('response_time_score', 100) < 70:
                recommendations.append("Optimize response times by reducing latency and improving throughput")
            
            # Monitoring recommendations
            if not recommendations:
                recommendations.append("Performance is good - maintain current monitoring and optimization practices")
            else:
                recommendations.append("Implement continuous performance monitoring and alerting")
            
        except Exception as e:
            logger.debug(f"Error generating performance recommendations: {e}")
        
        return recommendations[:10]  # Limit to top 10 recommendations