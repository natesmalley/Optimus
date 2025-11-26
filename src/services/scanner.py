"""
Project scanner service for discovering and analyzing projects.
Scans directories recursively to detect projects and extract metadata.
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

import git
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from ..config import get_settings
from ..models import Project


logger = logging.getLogger("optimus.scanner")


class ProjectScanner:
    """Scan and analyze projects in the file system."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        
        # Project type detection patterns
        self.project_patterns = {
            "python": {
                "files": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "poetry.lock"],
                "dirs": ["__pycache__", ".pytest_cache"],
                "frameworks": {
                    "fastapi": ["fastapi", "uvicorn"],
                    "django": ["django", "manage.py"],
                    "flask": ["flask", "app.py"],
                    "streamlit": ["streamlit"],
                    "jupyter": [".ipynb"]
                }
            },
            "nodejs": {
                "files": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
                "dirs": ["node_modules", ".next", ".nuxt"],
                "frameworks": {
                    "react": ["react", "next.js", "@next/"],
                    "vue": ["vue", "nuxt"],
                    "express": ["express"],
                    "nestjs": ["@nestjs/"]
                }
            },
            "rust": {
                "files": ["Cargo.toml", "Cargo.lock"],
                "dirs": ["target"],
                "frameworks": {
                    "actix": ["actix"],
                    "rocket": ["rocket"],
                    "axum": ["axum"]
                }
            },
            "go": {
                "files": ["go.mod", "go.sum", "main.go"],
                "dirs": ["vendor"],
                "frameworks": {
                    "gin": ["gin-gonic"],
                    "echo": ["echo"],
                    "gorilla": ["gorilla/mux"]
                }
            },
            "java": {
                "files": ["pom.xml", "build.gradle", "gradle.properties", "mvnw"],
                "dirs": ["target", "build", ".gradle"],
                "frameworks": {
                    "spring": ["spring-boot", "springframework"],
                    "quarkus": ["quarkus"],
                    "micronaut": ["micronaut"]
                }
            },
            "csharp": {
                "files": [".csproj", ".sln", "packages.config"],
                "dirs": ["bin", "obj", "packages"],
                "frameworks": {
                    "aspnet": ["Microsoft.AspNetCore"],
                    "blazor": ["Microsoft.AspNetCore.Blazor"],
                    "mvc": ["Microsoft.AspNetCore.Mvc"]
                }
            }
        }
    
    async def scan_projects(self, base_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Scan for projects in the specified directory."""
        scan_path = Path(base_path or self.settings.projects_base_path).expanduser()
        
        if not scan_path.exists():
            logger.warning(f"Base path does not exist: {scan_path}")
            return []
        
        logger.info(f"Starting project scan in: {scan_path}")
        discovered_projects = []
        
        try:
            for item in scan_path.iterdir():
                if item.is_dir() and not self._should_exclude_directory(item):
                    project_info = await self._analyze_directory(item)
                    if project_info:
                        discovered_projects.append(project_info)
                        logger.info(f"Discovered project: {project_info['name']} at {project_info['path']}")
        
        except Exception as e:
            logger.error(f"Error scanning projects: {e}", exc_info=True)
        
        logger.info(f"Scan completed. Found {len(discovered_projects)} projects.")
        return discovered_projects
    
    def _should_exclude_directory(self, path: Path) -> bool:
        """Check if directory should be excluded from scanning."""
        return (
            path.name.startswith('.') or
            path.name in self.settings.excluded_directories or
            path.name.startswith('__pycache__')
        )
    
    async def _analyze_directory(self, path: Path, depth: int = 0) -> Optional[Dict[str, Any]]:
        """Analyze a directory to determine if it's a project."""
        if depth > self.settings.max_scan_depth:
            return None
        
        project_info = {
            "name": path.name,
            "path": str(path),
            "description": None,
            "tech_stack": {},
            "dependencies": {},
            "language_stats": {},
            "git_url": None,
            "default_branch": "main",
            "last_commit_hash": None,
        }
        
        # Detect project type
        project_type = await self._detect_project_type(path)
        if not project_type:
            # Check subdirectories for projects
            for subdir in path.iterdir():
                if subdir.is_dir() and not self._should_exclude_directory(subdir):
                    subproject = await self._analyze_directory(subdir, depth + 1)
                    if subproject:
                        return subproject
            return None
        
        project_info["tech_stack"]["language"] = project_type
        
        # Extract additional metadata
        await self._extract_dependencies(path, project_info, project_type)
        await self._extract_git_info(path, project_info)
        await self._calculate_language_stats(path, project_info)
        await self._detect_frameworks(path, project_info, project_type)
        await self._extract_description(path, project_info)
        
        return project_info
    
    async def _detect_project_type(self, path: Path) -> Optional[str]:
        """Detect the primary project type based on files and directories."""
        for project_type, patterns in self.project_patterns.items():
            # Check for characteristic files
            for file_pattern in patterns["files"]:
                if any(path.glob(file_pattern)):
                    return project_type
            
            # Check for characteristic directories
            for dir_pattern in patterns["dirs"]:
                if (path / dir_pattern).exists():
                    return project_type
        
        return None
    
    async def _extract_dependencies(self, path: Path, project_info: Dict, project_type: str) -> None:
        """Extract project dependencies based on project type."""
        try:
            if project_type == "python":
                await self._extract_python_dependencies(path, project_info)
            elif project_type == "nodejs":
                await self._extract_nodejs_dependencies(path, project_info)
            elif project_type == "rust":
                await self._extract_rust_dependencies(path, project_info)
            elif project_type == "go":
                await self._extract_go_dependencies(path, project_info)
        except Exception as e:
            logger.warning(f"Error extracting dependencies for {path}: {e}")
    
    async def _extract_python_dependencies(self, path: Path, project_info: Dict) -> None:
        """Extract Python project dependencies."""
        # pyproject.toml
        pyproject_file = path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                import toml
                with open(pyproject_file, "r") as f:
                    data = toml.load(f)
                    
                deps = data.get("project", {}).get("dependencies", [])
                project_info["dependencies"] = {
                    dep.split(">=")[0].split("==")[0]: dep.split(">=")[1] if ">=" in dep else "latest"
                    for dep in deps if isinstance(dep, str)
                }
            except Exception as e:
                logger.warning(f"Error parsing pyproject.toml: {e}")
        
        # requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if "==" in line:
                                name, version = line.split("==", 1)
                                project_info["dependencies"][name] = version
                            elif ">=" in line:
                                name, version = line.split(">=", 1)
                                project_info["dependencies"][name] = f">={version}"
                            else:
                                project_info["dependencies"][line] = "latest"
            except Exception as e:
                logger.warning(f"Error parsing requirements.txt: {e}")
    
    async def _extract_nodejs_dependencies(self, path: Path, project_info: Dict) -> None:
        """Extract Node.js project dependencies."""
        package_file = path / "package.json"
        if package_file.exists():
            try:
                with open(package_file, "r") as f:
                    data = json.load(f)
                    
                project_info["description"] = data.get("description")
                
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))
                project_info["dependencies"] = deps
                
                # Extract framework info
                if "scripts" in data:
                    project_info["tech_stack"]["scripts"] = data["scripts"]
                
            except Exception as e:
                logger.warning(f"Error parsing package.json: {e}")
    
    async def _extract_rust_dependencies(self, path: Path, project_info: Dict) -> None:
        """Extract Rust project dependencies."""
        cargo_file = path / "Cargo.toml"
        if cargo_file.exists():
            try:
                import toml
                with open(cargo_file, "r") as f:
                    data = toml.load(f)
                
                project_info["description"] = data.get("package", {}).get("description")
                project_info["dependencies"] = data.get("dependencies", {})
                
            except Exception as e:
                logger.warning(f"Error parsing Cargo.toml: {e}")
    
    async def _extract_go_dependencies(self, path: Path, project_info: Dict) -> None:
        """Extract Go project dependencies."""
        go_mod_file = path / "go.mod"
        if go_mod_file.exists():
            try:
                with open(go_mod_file, "r") as f:
                    content = f.read()
                
                # Parse go.mod file (simplified)
                dependencies = {}
                for line in content.split("\n"):
                    if line.strip().startswith("require"):
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            dep_name = parts[1]
                            version = parts[2]
                            dependencies[dep_name] = version
                
                project_info["dependencies"] = dependencies
                
            except Exception as e:
                logger.warning(f"Error parsing go.mod: {e}")
    
    async def _extract_git_info(self, path: Path, project_info: Dict) -> None:
        """Extract Git repository information."""
        try:
            if (path / ".git").exists():
                repo = git.Repo(path)
                
                # Get remote URL
                if repo.remotes:
                    project_info["git_url"] = repo.remotes[0].url
                
                # Get default branch
                try:
                    project_info["default_branch"] = repo.active_branch.name
                except:
                    project_info["default_branch"] = "main"
                
                # Get last commit hash
                try:
                    project_info["last_commit_hash"] = repo.head.commit.hexsha
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"Git info extraction failed for {path}: {e}")
    
    async def _calculate_language_stats(self, path: Path, project_info: Dict) -> None:
        """Calculate programming language statistics."""
        try:
            # Use file extensions to estimate language distribution
            language_counts = {}
            total_files = 0
            
            for file_path in path.rglob("*"):
                if (file_path.is_file() and 
                    not any(excluded in str(file_path) for excluded in self.settings.excluded_directories)):
                    
                    suffix = file_path.suffix.lower()
                    if suffix in ['.py', '.js', '.ts', '.rs', '.go', '.java', '.cs', '.cpp', '.c', '.rb', '.php']:
                        language_map = {
                            '.py': 'python',
                            '.js': 'javascript',
                            '.ts': 'typescript',
                            '.rs': 'rust',
                            '.go': 'go',
                            '.java': 'java',
                            '.cs': 'csharp',
                            '.cpp': 'cpp',
                            '.c': 'c',
                            '.rb': 'ruby',
                            '.php': 'php'
                        }
                        
                        lang = language_map.get(suffix, 'other')
                        language_counts[lang] = language_counts.get(lang, 0) + 1
                        total_files += 1
            
            # Convert to percentages
            if total_files > 0:
                language_stats = {
                    lang: round((count / total_files) * 100, 1)
                    for lang, count in language_counts.items()
                }
                project_info["language_stats"] = language_stats
                
        except Exception as e:
            logger.warning(f"Error calculating language stats for {path}: {e}")
    
    async def _detect_frameworks(self, path: Path, project_info: Dict, project_type: str) -> None:
        """Detect frameworks used in the project."""
        try:
            frameworks = []
            patterns = self.project_patterns.get(project_type, {}).get("frameworks", {})
            
            for framework, keywords in patterns.items():
                # Check dependencies
                deps_str = json.dumps(project_info.get("dependencies", {})).lower()
                if any(keyword.lower() in deps_str for keyword in keywords):
                    frameworks.append(framework)
                
                # Check files
                for keyword in keywords:
                    if any(path.rglob(f"*{keyword}*")):
                        frameworks.append(framework)
                        break
            
            if frameworks:
                project_info["tech_stack"]["frameworks"] = frameworks
                
        except Exception as e:
            logger.warning(f"Error detecting frameworks for {path}: {e}")
    
    async def _extract_description(self, path: Path, project_info: Dict) -> None:
        """Extract project description from README or other sources."""
        if project_info.get("description"):
            return
            
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        for readme_name in readme_files:
            readme_path = path / readme_name
            if readme_path.exists():
                try:
                    with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # Extract first paragraph as description
                        lines = content.split("\n")
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith("#") and len(line) > 20:
                                project_info["description"] = line[:500]
                                break
                    break
                except Exception as e:
                    logger.debug(f"Error reading README {readme_path}: {e}")
    
    async def save_project(self, project_info: Dict[str, Any]) -> Optional[str]:
        """Save or update project information in the database."""
        try:
            # Check if project already exists
            stmt = select(Project).where(Project.path == project_info["path"])
            result = await self.session.execute(stmt)
            existing_project = result.scalar_one_or_none()
            
            if existing_project:
                # Update existing project
                update_stmt = (
                    update(Project)
                    .where(Project.id == existing_project.id)
                    .values(
                        name=project_info["name"],
                        description=project_info.get("description"),
                        tech_stack=project_info.get("tech_stack", {}),
                        dependencies=project_info.get("dependencies", {}),
                        git_url=project_info.get("git_url"),
                        default_branch=project_info.get("default_branch", "main"),
                        last_commit_hash=project_info.get("last_commit_hash"),
                        language_stats=project_info.get("language_stats", {}),
                        last_scanned=datetime.utcnow(),
                        status="active"
                    )
                )
                await self.session.execute(update_stmt)
                await self.session.commit()
                
                logger.info(f"Updated project: {project_info['name']}")
                return str(existing_project.id)
            
            else:
                # Create new project
                new_project = Project(
                    name=project_info["name"],
                    path=project_info["path"],
                    description=project_info.get("description"),
                    tech_stack=project_info.get("tech_stack", {}),
                    dependencies=project_info.get("dependencies", {}),
                    git_url=project_info.get("git_url"),
                    default_branch=project_info.get("default_branch", "main"),
                    last_commit_hash=project_info.get("last_commit_hash"),
                    language_stats=project_info.get("language_stats", {}),
                    last_scanned=datetime.utcnow(),
                    status="discovered"
                )
                
                self.session.add(new_project)
                await self.session.commit()
                await self.session.refresh(new_project)
                
                logger.info(f"Created new project: {project_info['name']}")
                return str(new_project.id)
                
        except Exception as e:
            logger.error(f"Error saving project {project_info['name']}: {e}", exc_info=True)
            await self.session.rollback()
            return None
    
    async def scan_and_save_all(self, base_path: Optional[str] = None) -> List[str]:
        """Scan for projects and save them to the database."""
        discovered_projects = await self.scan_projects(base_path)
        saved_project_ids = []
        
        for project_info in discovered_projects:
            project_id = await self.save_project(project_info)
            if project_id:
                saved_project_ids.append(project_id)
        
        logger.info(f"Scan complete. Saved {len(saved_project_ids)} projects.")
        return saved_project_ids