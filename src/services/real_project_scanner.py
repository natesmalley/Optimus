"""
Real Project Scanner - Scans actual projects from filesystem
Detects tech stack, dependencies, and project status
"""

import os
import json
import subprocess
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import git
import psutil
import toml
import yaml

class RealProjectScanner:
    """Scans real projects from the filesystem and analyzes them."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.path.expanduser("~/projects"))
        self.db_url = "postgresql://nathanial.smalley@localhost:5432/optimus_db"
        
    async def scan_all_projects(self) -> List[Dict[str, Any]]:
        """Scan all projects in the base directory."""
        projects = []
        
        if not self.base_path.exists():
            return projects
            
        # Get all subdirectories (each is potentially a project)
        for proj_path in self.base_path.iterdir():
            if proj_path.is_dir() and not proj_path.name.startswith('.'):
                try:
                    project_info = await self.scan_project(proj_path)
                    if project_info:
                        projects.append(project_info)
                except Exception as e:
                    print(f"Error scanning {proj_path}: {e}")
                    
        return projects
    
    async def scan_project(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """Scan a single project directory."""
        project = {
            "name": project_path.name,
            "path": str(project_path),
            "tech_stack": {},
            "dependencies": {},
            "status": "discovered",
            "git_info": {},
            "files": {},
            "runtime": {}
        }
        
        # Detect tech stack
        project["tech_stack"] = self.detect_tech_stack(project_path)
        
        # Get dependencies
        project["dependencies"] = self.get_dependencies(project_path)
        
        # Get Git info
        project["git_info"] = self.get_git_info(project_path)
        
        # Analyze file structure
        project["files"] = self.analyze_files(project_path)
        
        # Check if project is running
        project["runtime"] = await self.check_runtime_status(project_path)
        
        # Determine overall status
        if project["runtime"].get("is_running"):
            project["status"] = "running"
        elif project["git_info"].get("has_uncommitted_changes"):
            project["status"] = "active"
        else:
            project["status"] = "idle"
            
        return project
    
    def detect_tech_stack(self, project_path: Path) -> Dict[str, Any]:
        """Detect the technology stack of a project."""
        tech_stack = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": []
        }
        
        files = list(project_path.glob("*")) + list(project_path.glob(".*"))
        
        # Language detection
        if (project_path / "package.json").exists():
            tech_stack["languages"].append("JavaScript/TypeScript")
            pkg = self.read_json(project_path / "package.json")
            
            # Framework detection from package.json
            if pkg:
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps:
                    tech_stack["frameworks"].append("React")
                if "vue" in deps:
                    tech_stack["frameworks"].append("Vue")
                if "angular" in deps:
                    tech_stack["frameworks"].append("Angular")
                if "express" in deps:
                    tech_stack["frameworks"].append("Express")
                if "next" in deps:
                    tech_stack["frameworks"].append("Next.js")
                    
        if (project_path / "requirements.txt").exists() or (project_path / "setup.py").exists():
            tech_stack["languages"].append("Python")
            
            # Check for Python frameworks
            req_file = project_path / "requirements.txt"
            if req_file.exists():
                requirements = req_file.read_text()
                if "django" in requirements.lower():
                    tech_stack["frameworks"].append("Django")
                if "flask" in requirements.lower():
                    tech_stack["frameworks"].append("Flask")
                if "fastapi" in requirements.lower():
                    tech_stack["frameworks"].append("FastAPI")
                    
        if (project_path / "go.mod").exists():
            tech_stack["languages"].append("Go")
            
        if (project_path / "Cargo.toml").exists():
            tech_stack["languages"].append("Rust")
            
        if (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
            tech_stack["languages"].append("Java")
            
        # Database detection
        if (project_path / "docker-compose.yml").exists():
            compose = self.read_yaml(project_path / "docker-compose.yml")
            if compose and "services" in compose:
                for service in compose["services"].values():
                    image = service.get("image", "")
                    if "postgres" in image:
                        tech_stack["databases"].append("PostgreSQL")
                    if "mysql" in image or "mariadb" in image:
                        tech_stack["databases"].append("MySQL")
                    if "mongo" in image:
                        tech_stack["databases"].append("MongoDB")
                    if "redis" in image:
                        tech_stack["databases"].append("Redis")
                        
        # Tool detection
        if (project_path / "Dockerfile").exists():
            tech_stack["tools"].append("Docker")
        if (project_path / ".github" / "workflows").exists():
            tech_stack["tools"].append("GitHub Actions")
        if (project_path / ".gitlab-ci.yml").exists():
            tech_stack["tools"].append("GitLab CI")
        if (project_path / "Makefile").exists():
            tech_stack["tools"].append("Make")
            
        return tech_stack
    
    def get_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """Extract project dependencies."""
        deps = {}
        
        # Node.js dependencies
        if (project_path / "package.json").exists():
            pkg = self.read_json(project_path / "package.json")
            if pkg:
                deps["npm"] = {
                    "dependencies": list(pkg.get("dependencies", {}).keys()),
                    "devDependencies": list(pkg.get("devDependencies", {}).keys()),
                    "count": len(pkg.get("dependencies", {})) + len(pkg.get("devDependencies", {}))
                }
                
        # Python dependencies
        if (project_path / "requirements.txt").exists():
            req_file = project_path / "requirements.txt"
            requirements = req_file.read_text().split("\n")
            deps["pip"] = {
                "packages": [r.split("==")[0] for r in requirements if r and not r.startswith("#")],
                "count": len([r for r in requirements if r and not r.startswith("#")])
            }
            
        # Go dependencies
        if (project_path / "go.mod").exists():
            go_mod = (project_path / "go.mod").read_text()
            deps["go"] = {
                "modules": len([line for line in go_mod.split("\n") if line.strip().startswith("require")]),
                "count": go_mod.count("require")
            }
            
        return deps
    
    def get_git_info(self, project_path: Path) -> Dict[str, Any]:
        """Get Git repository information."""
        git_info = {
            "is_git_repo": False,
            "branch": None,
            "last_commit": None,
            "has_uncommitted_changes": False,
            "remote_url": None
        }
        
        try:
            repo = git.Repo(project_path)
            git_info["is_git_repo"] = True
            git_info["branch"] = repo.active_branch.name
            
            if repo.head.commit:
                git_info["last_commit"] = {
                    "hash": repo.head.commit.hexsha[:8],
                    "message": repo.head.commit.message.strip(),
                    "date": datetime.fromtimestamp(repo.head.commit.committed_date).isoformat(),
                    "author": str(repo.head.commit.author)
                }
                
            git_info["has_uncommitted_changes"] = repo.is_dirty()
            
            if repo.remotes:
                git_info["remote_url"] = repo.remotes.origin.url
                
        except:
            pass
            
        return git_info
    
    def analyze_files(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project file structure."""
        file_stats = {
            "total_files": 0,
            "total_size": 0,
            "languages": {},
            "largest_files": []
        }
        
        extensions = {}
        all_files = []
        
        for root, dirs, files in os.walk(project_path):
            # Skip hidden and vendor directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'vendor', 'dist', 'build']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = Path(root) / file
                try:
                    size = file_path.stat().st_size
                    file_stats["total_files"] += 1
                    file_stats["total_size"] += size
                    
                    ext = file_path.suffix.lower()
                    if ext:
                        extensions[ext] = extensions.get(ext, 0) + 1
                        
                    all_files.append((file_path, size))
                except:
                    pass
                    
        # Language mapping
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React',
            '.tsx': 'React',
            '.go': 'Go',
            '.rs': 'Rust',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin'
        }
        
        for ext, count in extensions.items():
            lang = lang_map.get(ext, ext)
            file_stats["languages"][lang] = file_stats["languages"].get(lang, 0) + count
            
        # Get largest files
        all_files.sort(key=lambda x: x[1], reverse=True)
        file_stats["largest_files"] = [
            {"name": f.name, "size": s, "path": str(f.relative_to(project_path))}
            for f, s in all_files[:5]
        ]
        
        return file_stats
    
    async def check_runtime_status(self, project_path: Path) -> Dict[str, Any]:
        """Check if the project is currently running."""
        runtime = {
            "is_running": False,
            "processes": [],
            "ports": [],
            "cpu_usage": 0,
            "memory_usage": 0
        }
        
        project_name = project_path.name.lower()
        
        # Check running processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                cmdline = " ".join(proc.info.get('cmdline', []))
                if project_name in cmdline.lower() or str(project_path) in cmdline:
                    runtime["is_running"] = True
                    runtime["processes"].append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu": proc.cpu_percent(),
                        "memory": proc.info['memory_info'].rss // 1024 // 1024  # MB
                    })
                    runtime["cpu_usage"] += proc.cpu_percent()
                    runtime["memory_usage"] += proc.info['memory_info'].rss // 1024 // 1024
                    
                    # Check ports
                    connections = proc.connections()
                    for conn in connections:
                        if conn.status == 'LISTEN':
                            runtime["ports"].append(conn.laddr.port)
            except:
                pass
                
        return runtime
    
    def read_json(self, file_path: Path) -> Optional[Dict]:
        """Safely read JSON file."""
        try:
            return json.loads(file_path.read_text())
        except:
            return None
            
    def read_yaml(self, file_path: Path) -> Optional[Dict]:
        """Safely read YAML file."""
        try:
            return yaml.safe_load(file_path.read_text())
        except:
            return None
    
    async def save_to_database(self, projects: List[Dict[str, Any]]):
        """Save scanned projects to database."""
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # Clear old project data
            await conn.execute("DELETE FROM projects")
            
            # Insert new projects
            for project in projects:
                await conn.execute("""
                    INSERT INTO projects 
                    (name, path, description, tech_stack, dependencies, status, 
                     git_url, last_commit_hash, language_stats, last_scanned)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                """,
                    project['name'],
                    project['path'],
                    f"Project: {project['name']}",
                    json.dumps(project['tech_stack']),
                    json.dumps(project['dependencies']),
                    project['status'],
                    project['git_info'].get('remote_url'),
                    project['git_info'].get('last_commit', {}).get('hash'),
                    json.dumps(project['files'].get('languages', {}))
                )
                
                # Add runtime status if running
                if project['runtime']['is_running']:
                    project_id = await conn.fetchval(
                        "SELECT id FROM projects WHERE path = $1",
                        project['path']
                    )
                    
                    for proc in project['runtime']['processes']:
                        await conn.execute("""
                            INSERT INTO runtime_status 
                            (project_id, process_name, pid, port, status, 
                             cpu_usage, memory_usage, started_at)
                            VALUES ($1, $2, $3, $4, 'running', $5, $6, NOW())
                        """,
                            project_id,
                            proc['name'],
                            proc['pid'],
                            project['runtime']['ports'][0] if project['runtime']['ports'] else None,
                            proc['cpu'],
                            proc['memory'] * 1024 * 1024  # Convert MB to bytes
                        )
                        
        finally:
            await conn.close()


# API endpoint functions for FastAPI
async def scan_projects_endpoint():
    """API endpoint to trigger project scanning."""
    scanner = RealProjectScanner()
    projects = await scanner.scan_all_projects()
    await scanner.save_to_database(projects)
    return {
        "status": "success",
        "projects_scanned": len(projects),
        "projects": projects
    }

async def get_real_projects():
    """Get real projects from database."""
    conn = await asyncpg.connect("postgresql://nathanial.smalley@localhost:5432/optimus_db")
    
    try:
        rows = await conn.fetch("""
            SELECT p.*, 
                   COUNT(DISTINCT r.id) as runtime_count,
                   MAX(r.cpu_usage) as current_cpu,
                   MAX(r.memory_usage) as current_memory
            FROM projects p
            LEFT JOIN runtime_status r ON p.id = r.project_id AND r.status = 'running'
            GROUP BY p.id
            ORDER BY p.last_scanned DESC
        """)
        
        projects = []
        for row in rows:
            projects.append({
                "id": str(row['id']),
                "name": row['name'],
                "path": row['path'],
                "tech_stack": json.loads(row['tech_stack']) if row['tech_stack'] else {},
                "dependencies": json.loads(row['dependencies']) if row['dependencies'] else {},
                "status": "running" if row['runtime_count'] > 0 else row['status'],
                "cpu_usage": float(row['current_cpu'] or 0),
                "memory_usage": int(row['current_memory'] or 0),
                "git_url": row['git_url'],
                "last_commit": row['last_commit_hash'],
                "language_stats": json.loads(row['language_stats']) if row['language_stats'] else {},
                "last_scanned": row['last_scanned'].isoformat() if row['last_scanned'] else None
            })
            
        return projects
        
    finally:
        await conn.close()