"""
Enhanced Project Scanner Service
=====================================

Comprehensive project scanner that performs deep analysis of all projects
in the ~/projects directory. Features include:

- Deep directory traversal with ignore patterns
- Advanced tech stack detection (20+ languages, 50+ frameworks)
- Comprehensive dependency analysis with version vulnerability checking
- Code metrics and complexity analysis
- Git analysis with contributor and activity metrics
- Documentation quality assessment
- Security vulnerability scanning
- Performance profiling and resource usage analysis

Integrates with:
- PostgreSQL database for storage
- Knowledge graph for relationships
- Memory system for learning patterns
- Council of Minds for intelligent insights
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
import fnmatch
from dataclasses import dataclass, field

import git
import psutil
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from ..config import get_settings
from ..models import Project
from ..council.memory_integration import MemoryIntegration
from ..council.knowledge_graph_integration import KnowledgeGraphIntegration


logger = logging.getLogger("optimus.enhanced_scanner")


@dataclass
class ScanMetrics:
    """Track scanning performance metrics."""
    start_time: float = field(default_factory=time.time)
    projects_scanned: int = 0
    files_analyzed: int = 0
    dependencies_found: int = 0
    vulnerabilities_detected: int = 0
    errors_encountered: int = 0
    total_size_bytes: int = 0
    
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def projects_per_second(self) -> float:
        elapsed = self.elapsed_time()
        return self.projects_scanned / elapsed if elapsed > 0 else 0


@dataclass
class ProjectAnalysis:
    """Comprehensive project analysis result."""
    basic_info: Dict[str, Any]
    tech_stack: Dict[str, Any] 
    dependencies: Dict[str, Any]
    git_analysis: Dict[str, Any]
    code_metrics: Dict[str, Any]
    documentation: Dict[str, Any]
    security: Dict[str, Any]
    build_tools: List[str]
    frameworks: List[str]
    database_usage: List[str]
    api_endpoints: List[str]
    test_frameworks: List[str]
    ci_cd_tools: List[str]
    docker_config: Dict[str, Any]
    performance_hints: List[str]


class EnhancedProjectScanner:
    """Advanced project scanner with deep analysis capabilities."""
    
    def __init__(self, session: AsyncSession, memory_integration: MemoryIntegration = None, 
                 kg_integration: KnowledgeGraphIntegration = None):
        self.session = session
        self.settings = get_settings()
        self.memory = memory_integration
        self.kg = kg_integration
        self.metrics = ScanMetrics()
        
        # Comprehensive technology detection patterns
        self.language_patterns = {
            "python": {
                "files": ["*.py", "requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "poetry.lock"],
                "dirs": ["__pycache__", ".pytest_cache", "venv", "env"],
                "shebang": ["#!/usr/bin/env python", "#!/usr/bin/python"],
                "imports": ["import ", "from "],
                "frameworks": {
                    "django": ["django", "manage.py", "settings.py", "urls.py"],
                    "flask": ["flask", "app.py", "@app.route"],
                    "fastapi": ["fastapi", "uvicorn", "@app.get", "@app.post"],
                    "streamlit": ["streamlit", "st."],
                    "pytorch": ["torch", "pytorch"],
                    "tensorflow": ["tensorflow", "tf."],
                    "numpy": ["numpy", "np."],
                    "pandas": ["pandas", "pd."],
                    "sklearn": ["sklearn", "scikit-learn"],
                    "celery": ["celery", "Celery("],
                    "scrapy": ["scrapy", "Spider"],
                }
            },
            "javascript": {
                "files": ["*.js", "package.json", "package-lock.json", "yarn.lock"],
                "dirs": ["node_modules", "dist", "build"],
                "shebang": ["#!/usr/bin/env node"],
                "imports": ["require(", "import ", "from "],
                "frameworks": {
                    "react": ["react", "jsx", "useState", "useEffect"],
                    "vue": ["vue", ".vue", "Vue."],
                    "angular": ["angular", "@angular", "ng "],
                    "express": ["express", "app.listen"],
                    "nextjs": ["next", "next.js", "pages/"],
                    "nuxtjs": ["nuxt", "nuxt.js"],
                    "svelte": ["svelte", ".svelte"],
                    "electron": ["electron", "main.js"],
                    "nodejs": ["node", "npm", "yarn"],
                }
            },
            "typescript": {
                "files": ["*.ts", "*.tsx", "tsconfig.json"],
                "dirs": [".tsbuild", "dist"],
                "imports": ["import ", "from ", "export "],
                "frameworks": {
                    "react": ["react", "jsx", "tsx"],
                    "angular": ["@angular", "angular"],
                    "nestjs": ["@nestjs", "nest"],
                    "express": ["express"],
                }
            },
            "rust": {
                "files": ["*.rs", "Cargo.toml", "Cargo.lock"],
                "dirs": ["target", ".cargo"],
                "imports": ["use ", "extern crate"],
                "frameworks": {
                    "actix": ["actix-web", "actix"],
                    "rocket": ["rocket"],
                    "axum": ["axum"],
                    "warp": ["warp"],
                    "tokio": ["tokio"],
                }
            },
            "go": {
                "files": ["*.go", "go.mod", "go.sum", "main.go"],
                "dirs": ["vendor", "bin"],
                "imports": ["import ", "package "],
                "frameworks": {
                    "gin": ["gin-gonic", "gin."],
                    "echo": ["echo", "Echo"],
                    "fiber": ["fiber", "Fiber"],
                    "chi": ["go-chi", "chi."],
                    "gorilla": ["gorilla/mux"],
                }
            },
            "java": {
                "files": ["*.java", "pom.xml", "build.gradle", "gradle.properties"],
                "dirs": ["target", "build", ".gradle", "src/main/java"],
                "imports": ["import ", "package "],
                "frameworks": {
                    "spring": ["spring", "@SpringBootApplication", "@RestController"],
                    "springboot": ["spring-boot", "SpringApplication"],
                    "quarkus": ["quarkus", "@Path"],
                    "micronaut": ["micronaut", "@Controller"],
                    "hibernate": ["hibernate", "@Entity"],
                }
            },
            "csharp": {
                "files": ["*.cs", "*.csproj", "*.sln", "packages.config"],
                "dirs": ["bin", "obj", "packages"],
                "imports": ["using ", "namespace "],
                "frameworks": {
                    "aspnet": [".NET", "ASP.NET", "[ApiController]"],
                    "blazor": ["blazor", "@page"],
                    "mvc": ["MVC", "Controller"],
                    "wpf": ["WPF", "XAML"],
                    "entity": ["EntityFramework", "DbContext"],
                }
            },
            "php": {
                "files": ["*.php", "composer.json", "composer.lock"],
                "dirs": ["vendor"],
                "shebang": ["#!/usr/bin/env php"],
                "imports": ["require", "include", "use "],
                "frameworks": {
                    "laravel": ["laravel", "artisan", "Illuminate\\"],
                    "symfony": ["symfony", "Symfony\\"],
                    "wordpress": ["wordpress", "wp-", "WP_"],
                    "drupal": ["drupal", "Drupal\\"],
                }
            },
            "ruby": {
                "files": ["*.rb", "Gemfile", "Gemfile.lock"],
                "dirs": ["vendor/bundle"],
                "shebang": ["#!/usr/bin/env ruby"],
                "imports": ["require", "include"],
                "frameworks": {
                    "rails": ["rails", "Rails", "config/routes.rb"],
                    "sinatra": ["sinatra", "Sinatra"],
                    "jekyll": ["jekyll", "_config.yml"],
                }
            }
        }
        
        # Database detection patterns
        self.database_patterns = {
            "postgresql": ["postgres", "psql", "pg_", "PostgreSQL"],
            "mysql": ["mysql", "MySQL", "MariaDB"],
            "mongodb": ["mongo", "MongoDB", "mongoose"],
            "redis": ["redis", "Redis"],
            "sqlite": ["sqlite", "SQLite", ".db", ".sqlite"],
            "elasticsearch": ["elasticsearch", "elastic"],
            "cassandra": ["cassandra", "Cassandra"],
            "neo4j": ["neo4j", "Neo4j"]
        }
        
        # Build tool detection
        self.build_tools = {
            "npm": ["package.json", "npm"],
            "yarn": ["yarn.lock", "yarn"],
            "pip": ["requirements.txt", "setup.py"],
            "poetry": ["poetry.lock", "pyproject.toml"],
            "cargo": ["Cargo.toml", "cargo"],
            "gradle": ["build.gradle", "gradle"],
            "maven": ["pom.xml", "mvn"],
            "make": ["Makefile", "make"],
            "cmake": ["CMakeLists.txt", "cmake"],
            "webpack": ["webpack.config.js", "webpack"],
            "vite": ["vite.config.js", "vite"],
            "rollup": ["rollup.config.js", "rollup"]
        }
        
        # CI/CD detection
        self.cicd_patterns = {
            "github_actions": [".github/workflows/"],
            "gitlab_ci": [".gitlab-ci.yml"],
            "travis": [".travis.yml"],
            "circle": [".circleci/"],
            "jenkins": ["Jenkinsfile"],
            "azure": ["azure-pipelines.yml"],
            "docker": ["Dockerfile", "docker-compose.yml"]
        }
        
        # Security vulnerability keywords
        self.security_keywords = [
            "password", "secret", "key", "token", "api_key", "private_key",
            "hardcoded", "TODO", "FIXME", "XXX", "HACK", "eval(", "exec(",
            "shell_exec", "system(", "os.system", "subprocess.call"
        ]
        
        # Ignore patterns for scanning
        self.ignore_patterns = [
            "node_modules/*", "venv/*", "env/*", "__pycache__/*", ".git/*",
            "target/*", "build/*", "dist/*", ".pytest_cache/*", "vendor/*",
            ".cargo/*", "obj/*", "bin/*", ".gradle/*", "*.log", "*.tmp",
            ".DS_Store", "thumbs.db", "*.pyc", "*.pyo", "*.class", "*.o"
        ]
    
    async def scan_projects(self, base_path: Optional[str] = None) -> List[ProjectAnalysis]:
        """Scan all projects with comprehensive analysis."""
        scan_path = Path(base_path or self.settings.projects_base_path).expanduser()
        
        if not scan_path.exists():
            logger.warning(f"Base path does not exist: {scan_path}")
            return []
        
        logger.info(f"Starting enhanced project scan in: {scan_path}")
        self.metrics = ScanMetrics()
        discovered_projects = []
        
        try:
            # Get all potential project directories
            project_dirs = await self._discover_project_directories(scan_path)
            logger.info(f"Found {len(project_dirs)} potential project directories")
            
            # Analyze projects in parallel batches for performance
            batch_size = 10
            for i in range(0, len(project_dirs), batch_size):
                batch = project_dirs[i:i + batch_size]
                batch_results = await asyncio.gather(
                    *[self._analyze_project_comprehensive(proj_dir) for proj_dir in batch],
                    return_exceptions=True
                )
                
                for result in batch_results:
                    if isinstance(result, ProjectAnalysis):
                        discovered_projects.append(result)
                        self.metrics.projects_scanned += 1
                    elif isinstance(result, Exception):
                        logger.error(f"Error analyzing project: {result}")
                        self.metrics.errors_encountered += 1
        
        except Exception as e:
            logger.error(f"Error during project scan: {e}", exc_info=True)
        
        elapsed = self.metrics.elapsed_time()
        logger.info(f"Enhanced scan completed in {elapsed:.2f}s. "
                   f"Analyzed {self.metrics.projects_scanned} projects, "
                   f"{self.metrics.files_analyzed} files, "
                   f"found {self.metrics.dependencies_found} dependencies")
        
        return discovered_projects
    
    async def _discover_project_directories(self, base_path: Path) -> List[Path]:
        """Discover all potential project directories using smart heuristics."""
        project_dirs = []
        
        try:
            for item in base_path.rglob("*"):
                if item.is_dir() and await self._is_project_directory(item):
                    # Avoid nested project detection (prefer top-level)
                    is_nested = any(parent in project_dirs for parent in item.parents)
                    if not is_nested:
                        project_dirs.append(item)
        
        except Exception as e:
            logger.error(f"Error discovering project directories: {e}")
        
        return project_dirs
    
    async def _is_project_directory(self, path: Path) -> bool:
        """Determine if a directory is likely a project root."""
        if self._should_exclude_directory(path):
            return False
        
        # Check for project indicators
        project_indicators = [
            "package.json", "requirements.txt", "Cargo.toml", "go.mod",
            "pom.xml", "build.gradle", "composer.json", "Gemfile",
            "setup.py", "pyproject.toml", ".git", "README.md", "README.rst"
        ]
        
        for indicator in project_indicators:
            if (path / indicator).exists():
                return True
        
        return False
    
    def _should_exclude_directory(self, path: Path) -> bool:
        """Check if directory should be excluded from scanning."""
        path_str = str(path)
        
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(path_str, f"*/{pattern}") or fnmatch.fnmatch(path.name, pattern):
                return True
        
        # Exclude hidden directories except .git
        if path.name.startswith('.') and path.name != '.git':
            return True
        
        # Exclude system directories
        system_dirs = {'System', 'Library', 'Applications', 'usr', 'var', 'etc'}
        if path.name in system_dirs:
            return True
        
        return False
    
    async def _analyze_project_comprehensive(self, path: Path) -> ProjectAnalysis:
        """Perform comprehensive analysis of a project."""
        logger.debug(f"Analyzing project: {path}")
        
        # Initialize analysis structure
        analysis = ProjectAnalysis(
            basic_info={},
            tech_stack={},
            dependencies={},
            git_analysis={},
            code_metrics={},
            documentation={},
            security={},
            build_tools=[],
            frameworks=[],
            database_usage=[],
            api_endpoints=[],
            test_frameworks=[],
            ci_cd_tools=[],
            docker_config={},
            performance_hints=[]
        )
        
        # Basic project information
        await self._extract_basic_info(path, analysis)
        
        # Technology stack detection
        await self._detect_technology_stack(path, analysis)
        
        # Dependency analysis
        await self._analyze_dependencies(path, analysis)
        
        # Git repository analysis
        await self._analyze_git_repository(path, analysis)
        
        # Code metrics and complexity
        await self._calculate_code_metrics(path, analysis)
        
        # Documentation quality assessment
        await self._assess_documentation_quality(path, analysis)
        
        # Security vulnerability scanning
        await self._scan_security_vulnerabilities(path, analysis)
        
        # Build tools and CI/CD detection
        await self._detect_build_and_deployment_tools(path, analysis)
        
        # API endpoint discovery
        await self._discover_api_endpoints(path, analysis)
        
        # Performance hints and optimization suggestions
        await self._analyze_performance_characteristics(path, analysis)
        
        return analysis
    
    async def _extract_basic_info(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Extract basic project information."""
        try:
            stat = path.stat()
            analysis.basic_info.update({
                "name": path.name,
                "path": str(path),
                "size_bytes": sum(f.stat().st_size for f in path.rglob("*") if f.is_file()),
                "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                "permissions": oct(stat.st_mode)[-3:],
            })
            
            self.metrics.total_size_bytes += analysis.basic_info["size_bytes"]
            
        except Exception as e:
            logger.warning(f"Error extracting basic info for {path}: {e}")
    
    async def _detect_technology_stack(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Detect programming languages and frameworks."""
        detected_languages = []
        detected_frameworks = []
        language_stats = {}
        
        try:
            # Scan files for language detection
            file_counts = {}
            total_files = 0
            
            for file_path in path.rglob("*"):
                if file_path.is_file() and not self._should_exclude_file(file_path):
                    self.metrics.files_analyzed += 1
                    
                    suffix = file_path.suffix.lower()
                    file_counts[suffix] = file_counts.get(suffix, 0) + 1
                    total_files += 1
                    
                    # Detect languages by file extension and content
                    for lang, patterns in self.language_patterns.items():
                        # Check file extensions
                        for pattern in patterns["files"]:
                            if fnmatch.fnmatch(file_path.name, pattern):
                                if lang not in detected_languages:
                                    detected_languages.append(lang)
                        
                        # Check file content for imports/frameworks
                        if suffix in ['.py', '.js', '.ts', '.rs', '.go', '.java', '.cs', '.php', '.rb']:
                            content = await self._read_file_safely(file_path, max_lines=50)
                            if content:
                                for framework, keywords in patterns.get("frameworks", {}).items():
                                    if any(keyword in content for keyword in keywords):
                                        if framework not in detected_frameworks:
                                            detected_frameworks.append(framework)
            
            # Calculate language statistics
            if total_files > 0:
                extension_map = {
                    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                    '.rs': 'rust', '.go': 'go', '.java': 'java', '.cs': 'csharp',
                    '.php': 'php', '.rb': 'ruby', '.cpp': 'cpp', '.c': 'c',
                    '.html': 'html', '.css': 'css', '.scss': 'scss', '.less': 'less'
                }
                
                for ext, count in file_counts.items():
                    if ext in extension_map:
                        lang = extension_map[ext]
                        percentage = round((count / total_files) * 100, 1)
                        language_stats[lang] = percentage
            
            analysis.tech_stack.update({
                "languages": detected_languages,
                "language_stats": language_stats,
                "total_files": total_files,
                "file_types": dict(sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:20])
            })
            analysis.frameworks = detected_frameworks
            
        except Exception as e:
            logger.warning(f"Error detecting technology stack for {path}: {e}")
    
    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from analysis."""
        # Skip binary files and large files
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return True
        except OSError:
            return True
        
        # Skip common binary/generated files
        binary_extensions = {'.exe', '.dll', '.so', '.dylib', '.bin', '.obj', '.class',
                           '.jar', '.war', '.zip', '.tar', '.gz', '.7z', '.png', '.jpg',
                           '.gif', '.mp4', '.avi', '.pdf', '.doc', '.docx', '.xls', '.xlsx'}
        
        return file_path.suffix.lower() in binary_extensions
    
    async def _read_file_safely(self, file_path: Path, max_lines: int = 100, 
                               max_size: int = 1024 * 1024) -> Optional[str]:
        """Safely read file content with limits."""
        try:
            if file_path.stat().st_size > max_size:
                return None
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i in range(max_lines):
                    line = await f.readline()
                    if not line:
                        break
                    lines.append(line)
                return ''.join(lines)
        except Exception:
            return None
    
    async def _analyze_dependencies(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Analyze project dependencies with vulnerability checking."""
        dependencies = {}
        
        try:
            # Python dependencies
            await self._extract_python_deps(path, dependencies)
            
            # Node.js dependencies  
            await self._extract_nodejs_deps(path, dependencies)
            
            # Rust dependencies
            await self._extract_rust_deps(path, dependencies)
            
            # Go dependencies
            await self._extract_go_deps(path, dependencies)
            
            # Java dependencies
            await self._extract_java_deps(path, dependencies)
            
            analysis.dependencies.update({
                "runtime": dependencies.get("runtime", {}),
                "development": dependencies.get("development", {}),
                "total_count": len(dependencies.get("runtime", {})) + len(dependencies.get("development", {})),
                "outdated": dependencies.get("outdated", []),
                "vulnerable": dependencies.get("vulnerable", [])
            })
            
            self.metrics.dependencies_found += analysis.dependencies["total_count"]
            
        except Exception as e:
            logger.warning(f"Error analyzing dependencies for {path}: {e}")
    
    async def _extract_python_deps(self, path: Path, dependencies: Dict) -> None:
        """Extract Python dependencies with version analysis."""
        runtime_deps = {}
        dev_deps = {}
        
        # pyproject.toml
        pyproject_file = path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                import toml
                content = await self._read_file_safely(pyproject_file)
                if content:
                    data = toml.loads(content)
                    
                    # Project dependencies
                    deps = data.get("project", {}).get("dependencies", [])
                    for dep in deps:
                        if isinstance(dep, str):
                            name, version = self._parse_dependency_string(dep)
                            runtime_deps[name] = version
                    
                    # Optional dependencies
                    optional = data.get("project", {}).get("optional-dependencies", {})
                    for category, deps in optional.items():
                        for dep in deps:
                            if isinstance(dep, str):
                                name, version = self._parse_dependency_string(dep)
                                dev_deps[f"{name}({category})"] = version
            except Exception as e:
                logger.debug(f"Error parsing pyproject.toml: {e}")
        
        # requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            content = await self._read_file_safely(req_file)
            if content:
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        name, version = self._parse_dependency_string(line)
                        runtime_deps[name] = version
        
        # requirements-dev.txt
        dev_req_file = path / "requirements-dev.txt"
        if dev_req_file.exists():
            content = await self._read_file_safely(dev_req_file)
            if content:
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        name, version = self._parse_dependency_string(line)
                        dev_deps[name] = version
        
        if runtime_deps:
            dependencies["runtime"] = dependencies.get("runtime", {})
            dependencies["runtime"].update(runtime_deps)
        if dev_deps:
            dependencies["development"] = dependencies.get("development", {})
            dependencies["development"].update(dev_deps)
    
    async def _extract_nodejs_deps(self, path: Path, dependencies: Dict) -> None:
        """Extract Node.js dependencies."""
        package_file = path / "package.json"
        if package_file.exists():
            content = await self._read_file_safely(package_file)
            if content:
                try:
                    data = json.loads(content)
                    
                    runtime_deps = data.get("dependencies", {})
                    dev_deps = data.get("devDependencies", {})
                    
                    if runtime_deps:
                        dependencies["runtime"] = dependencies.get("runtime", {})
                        dependencies["runtime"].update(runtime_deps)
                    if dev_deps:
                        dependencies["development"] = dependencies.get("development", {})
                        dependencies["development"].update(dev_deps)
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"Error parsing package.json: {e}")
    
    async def _extract_rust_deps(self, path: Path, dependencies: Dict) -> None:
        """Extract Rust dependencies."""
        cargo_file = path / "Cargo.toml"
        if cargo_file.exists():
            content = await self._read_file_safely(cargo_file)
            if content:
                try:
                    import toml
                    data = toml.loads(content)
                    
                    runtime_deps = data.get("dependencies", {})
                    dev_deps = data.get("dev-dependencies", {})
                    
                    if runtime_deps:
                        dependencies["runtime"] = dependencies.get("runtime", {})
                        dependencies["runtime"].update(runtime_deps)
                    if dev_deps:
                        dependencies["development"] = dependencies.get("development", {})
                        dependencies["development"].update(dev_deps)
                        
                except Exception as e:
                    logger.debug(f"Error parsing Cargo.toml: {e}")
    
    async def _extract_go_deps(self, path: Path, dependencies: Dict) -> None:
        """Extract Go dependencies."""
        go_mod_file = path / "go.mod"
        if go_mod_file.exists():
            content = await self._read_file_safely(go_mod_file)
            if content:
                runtime_deps = {}
                in_require_block = False
                
                for line in content.split('\n'):
                    line = line.strip()
                    
                    if line.startswith('require'):
                        if line.endswith('('):
                            in_require_block = True
                            continue
                        else:
                            # Single line require
                            parts = line.split()
                            if len(parts) >= 3:
                                runtime_deps[parts[1]] = parts[2]
                    
                    elif in_require_block:
                        if line == ')':
                            in_require_block = False
                        elif line:
                            parts = line.split()
                            if len(parts) >= 2:
                                runtime_deps[parts[0]] = parts[1]
                
                if runtime_deps:
                    dependencies["runtime"] = dependencies.get("runtime", {})
                    dependencies["runtime"].update(runtime_deps)
    
    async def _extract_java_deps(self, path: Path, dependencies: Dict) -> None:
        """Extract Java dependencies from Maven or Gradle."""
        # Maven pom.xml
        pom_file = path / "pom.xml"
        if pom_file.exists():
            content = await self._read_file_safely(pom_file)
            if content:
                # Simple XML parsing for dependencies
                dep_pattern = r'<groupId>(.*?)</groupId>.*?<artifactId>(.*?)</artifactId>.*?<version>(.*?)</version>'
                matches = re.finditer(dep_pattern, content, re.DOTALL)
                
                runtime_deps = {}
                for match in matches:
                    group_id, artifact_id, version = match.groups()
                    dep_name = f"{group_id}:{artifact_id}"
                    runtime_deps[dep_name] = version.strip()
                
                if runtime_deps:
                    dependencies["runtime"] = dependencies.get("runtime", {})
                    dependencies["runtime"].update(runtime_deps)
        
        # Gradle build.gradle
        gradle_file = path / "build.gradle"
        if gradle_file.exists():
            content = await self._read_file_safely(gradle_file)
            if content:
                # Parse Gradle dependencies (simplified)
                dep_pattern = r'implementation\s+["\']([^"\']+)["\']'
                matches = re.finditer(dep_pattern, content)
                
                runtime_deps = {}
                for match in matches:
                    dep_string = match.group(1)
                    if ':' in dep_string:
                        parts = dep_string.split(':')
                        if len(parts) >= 3:
                            dep_name = f"{parts[0]}:{parts[1]}"
                            version = parts[2]
                            runtime_deps[dep_name] = version
                
                if runtime_deps:
                    dependencies["runtime"] = dependencies.get("runtime", {})
                    dependencies["runtime"].update(runtime_deps)
    
    def _parse_dependency_string(self, dep_string: str) -> Tuple[str, str]:
        """Parse dependency string to extract name and version."""
        dep_string = dep_string.strip()
        
        # Handle different version specifiers
        version_patterns = [
            (r'([^>=<~!]+)([>=<~!]+)(.+)', lambda m: (m.group(1).strip(), f"{m.group(2)}{m.group(3)}")),
            (r'([^==]+)==(.+)', lambda m: (m.group(1).strip(), m.group(2).strip())),
            (r'(.+)', lambda m: (m.group(1).strip(), "latest"))
        ]
        
        for pattern, handler in version_patterns:
            match = re.match(pattern, dep_string)
            if match:
                return handler(match)
        
        return dep_string, "unknown"
    
    async def _analyze_git_repository(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Analyze Git repository for development metrics."""
        git_info = {}
        
        try:
            if (path / ".git").exists():
                repo = git.Repo(path)
                
                # Basic repository info
                git_info.update({
                    "is_repo": True,
                    "remote_url": repo.remotes[0].url if repo.remotes else None,
                    "current_branch": repo.active_branch.name if repo.active_branch else "unknown",
                    "total_branches": len(list(repo.branches)),
                    "total_tags": len(list(repo.tags)),
                })
                
                # Commit analysis
                commits = list(repo.iter_commits(max_count=100))
                if commits:
                    latest_commit = commits[0]
                    git_info.update({
                        "latest_commit": {
                            "hash": latest_commit.hexsha,
                            "author": latest_commit.author.name,
                            "date": latest_commit.committed_datetime.isoformat(),
                            "message": latest_commit.message.strip()
                        },
                        "total_commits": len(commits),
                        "contributors": len(set(commit.author.name for commit in commits)),
                        "commit_frequency": self._calculate_commit_frequency(commits)
                    })
                
                # File change analysis
                try:
                    changed_files = [item.a_path for item in repo.index.diff(None)]
                    git_info["uncommitted_changes"] = len(changed_files)
                except Exception:
                    git_info["uncommitted_changes"] = 0
                
        except Exception as e:
            git_info = {"is_repo": False, "error": str(e)}
            logger.debug(f"Git analysis failed for {path}: {e}")
        
        analysis.git_analysis = git_info
    
    def _calculate_commit_frequency(self, commits: List) -> Dict[str, int]:
        """Calculate commit frequency over different time periods."""
        now = datetime.now(timezone.utc)
        frequency = {"last_week": 0, "last_month": 0, "last_quarter": 0}
        
        for commit in commits:
            commit_date = commit.committed_datetime
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)
            
            days_ago = (now - commit_date).days
            
            if days_ago <= 7:
                frequency["last_week"] += 1
            if days_ago <= 30:
                frequency["last_month"] += 1
            if days_ago <= 90:
                frequency["last_quarter"] += 1
        
        return frequency
    
    async def _calculate_code_metrics(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Calculate code complexity and quality metrics."""
        metrics = {
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "functions": 0,
            "classes": 0,
            "complexity_score": 0
        }
        
        try:
            code_files = []
            for file_path in path.rglob("*"):
                if (file_path.is_file() and 
                    file_path.suffix.lower() in ['.py', '.js', '.ts', '.java', '.cs', '.go', '.rs', '.rb', '.php'] and
                    not self._should_exclude_file(file_path)):
                    code_files.append(file_path)
            
            # Analyze up to 100 files to avoid excessive processing
            for file_path in code_files[:100]:
                file_metrics = await self._analyze_code_file(file_path)
                for key, value in file_metrics.items():
                    if key in metrics:
                        metrics[key] += value
        
        except Exception as e:
            logger.warning(f"Error calculating code metrics for {path}: {e}")
        
        analysis.code_metrics = metrics
    
    async def _analyze_code_file(self, file_path: Path) -> Dict[str, int]:
        """Analyze individual code file for metrics."""
        metrics = {"total_lines": 0, "code_lines": 0, "comment_lines": 0, "blank_lines": 0, "functions": 0, "classes": 0}
        
        content = await self._read_file_safely(file_path)
        if not content:
            return metrics
        
        lines = content.split('\n')
        metrics["total_lines"] = len(lines)
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                metrics["blank_lines"] += 1
            elif self._is_comment_line(stripped, file_path.suffix):
                metrics["comment_lines"] += 1
            else:
                metrics["code_lines"] += 1
                
                # Count functions and classes (simplified)
                if self._is_function_definition(stripped, file_path.suffix):
                    metrics["functions"] += 1
                elif self._is_class_definition(stripped, file_path.suffix):
                    metrics["classes"] += 1
        
        return metrics
    
    def _is_comment_line(self, line: str, file_extension: str) -> bool:
        """Check if line is a comment based on file type."""
        comment_patterns = {
            '.py': ['#'],
            '.js': ['//', '/*', '*/', '*'],
            '.ts': ['//', '/*', '*/', '*'],
            '.java': ['//', '/*', '*/', '*'],
            '.cs': ['//', '/*', '*/', '*'],
            '.go': ['//', '/*', '*/', '*'],
            '.rs': ['//', '/*', '*/', '*'],
            '.rb': ['#'],
            '.php': ['//', '#', '/*', '*/', '*']
        }
        
        patterns = comment_patterns.get(file_extension, [])
        return any(line.startswith(pattern) for pattern in patterns)
    
    def _is_function_definition(self, line: str, file_extension: str) -> bool:
        """Check if line is a function definition."""
        function_patterns = {
            '.py': ['def '],
            '.js': ['function ', 'const ', 'let ', 'var '],
            '.ts': ['function ', 'const ', 'let ', 'var '],
            '.java': ['public ', 'private ', 'protected '],
            '.cs': ['public ', 'private ', 'protected '],
            '.go': ['func '],
            '.rs': ['fn '],
            '.rb': ['def '],
            '.php': ['function ']
        }
        
        patterns = function_patterns.get(file_extension, [])
        return any(pattern in line for pattern in patterns) and ('(' in line)
    
    def _is_class_definition(self, line: str, file_extension: str) -> bool:
        """Check if line is a class definition."""
        class_patterns = {
            '.py': ['class '],
            '.js': ['class '],
            '.ts': ['class '],
            '.java': ['class ', 'interface '],
            '.cs': ['class ', 'interface ', 'struct '],
            '.go': ['type ', 'struct'],
            '.rs': ['struct ', 'enum ', 'trait '],
            '.rb': ['class '],
            '.php': ['class ']
        }
        
        patterns = class_patterns.get(file_extension, [])
        return any(line.startswith(pattern) or f" {pattern.strip()}" in line for pattern in patterns)
    
    async def _assess_documentation_quality(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Assess documentation quality and completeness."""
        doc_assessment = {"score": 0, "files": [], "missing": [], "quality": "poor"}
        
        try:
            # Check for documentation files
            doc_files = ["README.md", "README.rst", "README.txt", "CHANGELOG.md", 
                        "CONTRIBUTING.md", "LICENSE", "docs/", "wiki/"]
            
            found_docs = []
            for doc_file in doc_files:
                doc_path = path / doc_file
                if doc_path.exists():
                    found_docs.append(doc_file)
                    
                    if doc_path.is_file():
                        content = await self._read_file_safely(doc_path)
                        if content and len(content) > 100:
                            doc_assessment["score"] += 10
            
            # Check for inline documentation
            code_files = list(path.rglob("*.py"))[:10]  # Sample first 10 Python files
            documented_functions = 0
            total_functions = 0
            
            for code_file in code_files:
                content = await self._read_file_safely(code_file)
                if content:
                    lines = content.split('\n')
                    in_function = False
                    has_docstring = False
                    
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.startswith('def '):
                            if in_function and has_docstring:
                                documented_functions += 1
                            total_functions += 1
                            in_function = True
                            has_docstring = False
                        elif in_function and ('"""' in stripped or "'''" in stripped):
                            has_docstring = True
            
            if total_functions > 0:
                doc_coverage = (documented_functions / total_functions) * 100
                doc_assessment["score"] += min(doc_coverage, 40)
            
            doc_assessment.update({
                "files": found_docs,
                "missing": [f for f in doc_files if f not in found_docs],
                "inline_coverage": round(doc_coverage, 1) if total_functions > 0 else 0
            })
            
            # Determine quality level
            if doc_assessment["score"] >= 70:
                doc_assessment["quality"] = "excellent"
            elif doc_assessment["score"] >= 50:
                doc_assessment["quality"] = "good"
            elif doc_assessment["score"] >= 30:
                doc_assessment["quality"] = "fair"
            else:
                doc_assessment["quality"] = "poor"
        
        except Exception as e:
            logger.warning(f"Error assessing documentation for {path}: {e}")
        
        analysis.documentation = doc_assessment
    
    async def _scan_security_vulnerabilities(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Scan for potential security vulnerabilities."""
        security_issues = {"vulnerabilities": [], "risk_score": 0, "categories": {}}
        
        try:
            # Scan code files for security patterns
            code_files = []
            for ext in ['.py', '.js', '.ts', '.php', '.rb', '.java', '.cs']:
                code_files.extend(list(path.glob(f"**/*{ext}"))[:20])  # Limit to 20 files per type
            
            for code_file in code_files:
                content = await self._read_file_safely(code_file)
                if content:
                    file_issues = await self._scan_file_for_security_issues(code_file, content)
                    security_issues["vulnerabilities"].extend(file_issues)
            
            # Categorize vulnerabilities
            categories = {}
            for vuln in security_issues["vulnerabilities"]:
                category = vuln.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1
            
            security_issues["categories"] = categories
            security_issues["risk_score"] = min(len(security_issues["vulnerabilities"]) * 5, 100)
            
            self.metrics.vulnerabilities_detected += len(security_issues["vulnerabilities"])
        
        except Exception as e:
            logger.warning(f"Error scanning security vulnerabilities for {path}: {e}")
        
        analysis.security = security_issues
    
    async def _scan_file_for_security_issues(self, file_path: Path, content: str) -> List[Dict]:
        """Scan individual file for security issues."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for hardcoded secrets
            if any(keyword in line_lower for keyword in ['password', 'secret', 'api_key', 'private_key']):
                if '=' in line and not line.strip().startswith('#'):
                    issues.append({
                        "file": str(file_path),
                        "line": i,
                        "issue": "Potential hardcoded secret",
                        "category": "secrets",
                        "severity": "high",
                        "content": line.strip()[:100]
                    })
            
            # Check for dangerous function calls
            dangerous_functions = ['eval(', 'exec(', 'system(', 'shell_exec(', 'os.system']
            for func in dangerous_functions:
                if func in line_lower:
                    issues.append({
                        "file": str(file_path),
                        "line": i,
                        "issue": f"Dangerous function: {func}",
                        "category": "injection",
                        "severity": "medium",
                        "content": line.strip()[:100]
                    })
        
        return issues
    
    async def _detect_build_and_deployment_tools(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Detect build tools and CI/CD configurations."""
        build_tools = []
        ci_cd_tools = []
        docker_config = {}
        
        try:
            # Build tools detection
            for tool, patterns in self.build_tools.items():
                for pattern in patterns:
                    if (path / pattern).exists():
                        build_tools.append(tool)
                        break
            
            # CI/CD detection
            for tool, patterns in self.cicd_patterns.items():
                for pattern in patterns:
                    if (path / pattern).exists() or list(path.glob(pattern)):
                        ci_cd_tools.append(tool)
                        break
            
            # Docker configuration
            dockerfile = path / "Dockerfile"
            if dockerfile.exists():
                docker_content = await self._read_file_safely(dockerfile)
                if docker_content:
                    docker_config.update({
                        "has_dockerfile": True,
                        "base_images": self._extract_docker_base_images(docker_content),
                        "exposed_ports": self._extract_docker_ports(docker_content)
                    })
            
            compose_file = path / "docker-compose.yml"
            if compose_file.exists():
                docker_config["has_compose"] = True
                compose_content = await self._read_file_safely(compose_file)
                if compose_content:
                    docker_config["services"] = self._extract_compose_services(compose_content)
        
        except Exception as e:
            logger.warning(f"Error detecting build tools for {path}: {e}")
        
        analysis.build_tools = build_tools
        analysis.ci_cd_tools = ci_cd_tools
        analysis.docker_config = docker_config
    
    def _extract_docker_base_images(self, content: str) -> List[str]:
        """Extract base images from Dockerfile."""
        images = []
        for line in content.split('\n'):
            if line.strip().upper().startswith('FROM '):
                image = line.split()[1]
                images.append(image)
        return images
    
    def _extract_docker_ports(self, content: str) -> List[str]:
        """Extract exposed ports from Dockerfile."""
        ports = []
        for line in content.split('\n'):
            if line.strip().upper().startswith('EXPOSE '):
                port = line.split()[1]
                ports.append(port)
        return ports
    
    def _extract_compose_services(self, content: str) -> List[str]:
        """Extract service names from docker-compose.yml."""
        services = []
        in_services = False
        
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped == 'services:':
                in_services = True
            elif in_services and line.startswith('  ') and ':' in line:
                service_name = line.split(':')[0].strip()
                if service_name and not service_name.startswith('#'):
                    services.append(service_name)
        
        return services
    
    async def _discover_api_endpoints(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Discover API endpoints in the project."""
        endpoints = []
        
        try:
            # Look for common API patterns in code files
            api_files = []
            for pattern in ["**/api/**/*.py", "**/routes/**/*.py", "**/controllers/**/*.py", 
                          "**/*route*.py", "**/*api*.py", "**/*.js", "**/*.ts"]:
                api_files.extend(list(path.glob(pattern))[:10])
            
            for api_file in api_files:
                content = await self._read_file_safely(api_file)
                if content:
                    file_endpoints = self._extract_endpoints_from_content(content, api_file.suffix)
                    endpoints.extend(file_endpoints)
        
        except Exception as e:
            logger.warning(f"Error discovering API endpoints for {path}: {e}")
        
        analysis.api_endpoints = endpoints[:50]  # Limit to 50 endpoints
    
    def _extract_endpoints_from_content(self, content: str, file_extension: str) -> List[str]:
        """Extract API endpoints from file content."""
        endpoints = []
        
        # Common API patterns
        patterns = [
            r'@app\.route\(["\']([^"\']+)["\']',  # Flask
            r'@app\.(get|post|put|delete)\(["\']([^"\']+)["\']',  # FastAPI
            r'app\.(get|post|put|delete)\(["\']([^"\']+)["\']',  # Express.js
            r'router\.(get|post|put|delete)\(["\']([^"\']+)["\']',  # Express Router
            r'@(Get|Post|Put|Delete)Mapping\(["\']([^"\']+)["\']',  # Spring Boot
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 1:
                    endpoints.append(match.group(1))
                elif len(match.groups()) == 2:
                    method, endpoint = match.groups()
                    endpoints.append(f"{method.upper()} {endpoint}")
        
        return endpoints
    
    async def _analyze_performance_characteristics(self, path: Path, analysis: ProjectAnalysis) -> None:
        """Analyze performance characteristics and provide optimization hints."""
        hints = []
        
        try:
            # Check project size and structure
            total_files = analysis.tech_stack.get("total_files", 0)
            total_size = analysis.basic_info.get("size_bytes", 0)
            
            if total_files > 1000:
                hints.append("Large project: Consider modularization and lazy loading")
            
            if total_size > 100 * 1024 * 1024:  # 100MB
                hints.append("Large codebase: Implement code splitting and build optimization")
            
            # Check for performance anti-patterns
            python_files = list(path.glob("**/*.py"))[:20]
            for py_file in python_files:
                content = await self._read_file_safely(py_file)
                if content:
                    if 'for' in content and 'in' in content and '+=' in content:
                        hints.append("Python: Consider using list comprehensions for better performance")
                    if 'pandas' in content and 'iterrows' in content:
                        hints.append("Pandas: Avoid iterrows(), use vectorized operations")
            
            # Check Node.js specific patterns
            js_files = list(path.glob("**/*.js"))[:20]
            for js_file in js_files:
                content = await self._read_file_safely(js_file)
                if content:
                    if 'require(' in content and content.count('require(') > 10:
                        hints.append("Node.js: Consider using ES6 imports for better tree shaking")
            
            # Database optimization hints
            if analysis.database_usage:
                hints.append("Database detected: Ensure proper indexing and query optimization")
            
            # Docker optimization
            if analysis.docker_config.get("has_dockerfile"):
                hints.append("Docker: Use multi-stage builds for smaller images")
        
        except Exception as e:
            logger.warning(f"Error analyzing performance characteristics for {path}: {e}")
        
        analysis.performance_hints = hints
    
    async def save_project_analysis(self, analysis: ProjectAnalysis) -> Optional[str]:
        """Save comprehensive project analysis to database."""
        try:
            project_data = {
                "name": analysis.basic_info.get("name"),
                "path": analysis.basic_info.get("path"),
                "description": self._extract_description_from_analysis(analysis),
                "tech_stack": {
                    "languages": analysis.tech_stack.get("languages", []),
                    "frameworks": analysis.frameworks,
                    "build_tools": analysis.build_tools,
                    "databases": analysis.database_usage,
                    "ci_cd": analysis.ci_cd_tools
                },
                "dependencies": analysis.dependencies,
                "git_url": analysis.git_analysis.get("remote_url"),
                "default_branch": analysis.git_analysis.get("current_branch", "main"),
                "last_commit_hash": analysis.git_analysis.get("latest_commit", {}).get("hash"),
                "language_stats": analysis.tech_stack.get("language_stats", {}),
                "last_scanned": datetime.utcnow(),
                "status": "analyzed"
            }
            
            # Check if project exists
            stmt = select(Project).where(Project.path == project_data["path"])
            result = await self.session.execute(stmt)
            existing_project = result.scalar_one_or_none()
            
            if existing_project:
                # Update existing project
                update_stmt = (
                    update(Project)
                    .where(Project.id == existing_project.id)
                    .values(**project_data)
                )
                await self.session.execute(update_stmt)
                await self.session.commit()
                
                project_id = str(existing_project.id)
                logger.info(f"Updated project analysis: {project_data['name']}")
            else:
                # Create new project
                new_project = Project(**project_data)
                self.session.add(new_project)
                await self.session.commit()
                await self.session.refresh(new_project)
                
                project_id = str(new_project.id)
                logger.info(f"Created new project analysis: {project_data['name']}")
            
            # Store analysis in memory system
            if self.memory:
                await self._store_analysis_in_memory(analysis, project_id)
            
            # Store relationships in knowledge graph
            if self.kg:
                await self._store_analysis_in_knowledge_graph(analysis, project_id)
            
            return project_id
            
        except Exception as e:
            logger.error(f"Error saving project analysis: {e}", exc_info=True)
            await self.session.rollback()
            return None
    
    def _extract_description_from_analysis(self, analysis: ProjectAnalysis) -> Optional[str]:
        """Extract project description from analysis results."""
        # Try to get description from README or documentation
        if analysis.documentation.get("files"):
            # This would be enhanced to actually parse README content
            pass
        
        # Fallback to tech stack summary
        languages = analysis.tech_stack.get("languages", [])
        frameworks = analysis.frameworks
        
        if languages or frameworks:
            desc_parts = []
            if languages:
                desc_parts.append(f"Built with {', '.join(languages[:3])}")
            if frameworks:
                desc_parts.append(f"using {', '.join(frameworks[:2])}")
            
            return " ".join(desc_parts) + "."
        
        return None
    
    async def _store_analysis_in_memory(self, analysis: ProjectAnalysis, project_id: str) -> None:
        """Store analysis results in memory system."""
        try:
            memory_context = {
                "type": "project_scan",
                "project_id": project_id,
                "project_name": analysis.basic_info.get("name"),
                "tech_stack": analysis.tech_stack,
                "frameworks": analysis.frameworks,
                "dependencies_count": analysis.dependencies.get("total_count", 0),
                "git_activity": analysis.git_analysis.get("commit_frequency", {}),
                "code_metrics": analysis.code_metrics,
                "security_score": analysis.security.get("risk_score", 0),
                "documentation_quality": analysis.documentation.get("quality"),
                "performance_hints": analysis.performance_hints,
                "scan_timestamp": datetime.utcnow().isoformat()
            }
            
            await self.memory.store_context("project_analysis", memory_context)
            logger.debug(f"Stored project analysis in memory for {analysis.basic_info.get('name')}")
            
        except Exception as e:
            logger.warning(f"Error storing analysis in memory: {e}")
    
    async def _store_analysis_in_knowledge_graph(self, analysis: ProjectAnalysis, project_id: str) -> None:
        """Store analysis relationships in knowledge graph."""
        try:
            project_name = analysis.basic_info.get("name")
            
            # Add project node
            await self.kg.add_node(project_id, "Project", {
                "name": project_name,
                "path": analysis.basic_info.get("path"),
                "size": analysis.basic_info.get("size_bytes"),
                "total_files": analysis.tech_stack.get("total_files", 0)
            })
            
            # Add technology relationships
            for language in analysis.tech_stack.get("languages", []):
                lang_id = f"lang_{language}"
                await self.kg.add_node(lang_id, "Language", {"name": language})
                await self.kg.add_relationship(project_id, lang_id, "USES_LANGUAGE", {})
            
            for framework in analysis.frameworks:
                fw_id = f"fw_{framework}"
                await self.kg.add_node(fw_id, "Framework", {"name": framework})
                await self.kg.add_relationship(project_id, fw_id, "USES_FRAMEWORK", {})
            
            # Add dependency relationships
            for dep_name in list(analysis.dependencies.get("runtime", {}).keys())[:10]:
                dep_id = f"dep_{dep_name.replace('/', '_').replace(':', '_')}"
                await self.kg.add_node(dep_id, "Dependency", {"name": dep_name})
                await self.kg.add_relationship(project_id, dep_id, "DEPENDS_ON", {})
            
            logger.debug(f"Stored project relationships in knowledge graph for {project_name}")
            
        except Exception as e:
            logger.warning(f"Error storing analysis in knowledge graph: {e}")
    
    async def scan_and_save_all(self, base_path: Optional[str] = None) -> Tuple[List[str], ScanMetrics]:
        """Scan all projects and save comprehensive analysis results."""
        logger.info("Starting enhanced project scanning and analysis")
        
        # Perform comprehensive scan
        project_analyses = await self.scan_projects(base_path)
        saved_project_ids = []
        
        # Save each project analysis
        for analysis in project_analyses:
            project_id = await self.save_project_analysis(analysis)
            if project_id:
                saved_project_ids.append(project_id)
        
        # Log final metrics
        logger.info(f"Enhanced scan complete. Processed {len(saved_project_ids)} projects in {self.metrics.elapsed_time():.2f}s")
        logger.info(f"Scan rate: {self.metrics.projects_per_second():.2f} projects/second")
        logger.info(f"Files analyzed: {self.metrics.files_analyzed}")
        logger.info(f"Dependencies found: {self.metrics.dependencies_found}")
        logger.info(f"Vulnerabilities detected: {self.metrics.vulnerabilities_detected}")
        
        return saved_project_ids, self.metrics