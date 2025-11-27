"""
Solution Library
===============

Pre-built solutions for common development issues with proven fixes and
verification steps. The library contains curated solutions for various
programming languages, frameworks, and platforms.

Each solution includes:
- Fix commands with proper error handling
- Verification commands to ensure the fix worked
- Rollback commands for safe recovery
- Risk assessment and approval requirements
- Success rate tracking and context-specific effectiveness
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ..models.troubleshooting import Solution, SolutionCategory

logger = logging.getLogger("optimus.solution_library")


class SolutionLibrary:
    """
    Manages the library of pre-built solutions for common development issues.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def initialize_default_solutions(self) -> None:
        """Initialize the solution library with default solutions."""
        logger.info("Initializing solution library with default solutions")
        
        solutions = self._get_default_solutions()
        
        for solution_data in solutions:
            await self._create_or_update_solution(solution_data)
        
        await self.session.commit()
        logger.info(f"Initialized {len(solutions)} default solutions")
    
    def _get_default_solutions(self) -> List[Dict[str, Any]]:
        """Get the list of default solutions to initialize."""
        return [
            # Python dependency issues
            {
                'title': 'Fix Python ModuleNotFoundError',
                'description': 'Install missing Python module using pip',
                'category': SolutionCategory.DEPENDENCY,
                'language': 'python',
                'fix_commands': [
                    'pip install {module_name}',
                    'pip install --upgrade pip'
                ],
                'verification_commands': [
                    'python -c "import {module_name}; print(f\"{module_name} imported successfully\")"'
                ],
                'rollback_commands': [
                    'pip uninstall -y {module_name}'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['python', 'pip']
            },
            {
                'title': 'Fix Python ImportError with requirements.txt',
                'description': 'Install all missing dependencies from requirements.txt',
                'category': SolutionCategory.DEPENDENCY,
                'language': 'python',
                'fix_commands': [
                    'pip install --upgrade pip',
                    'pip install -r requirements.txt'
                ],
                'verification_commands': [
                    'python -m pip check',
                    'python -c "import pkg_resources; print(\"All packages installed successfully\")"'
                ],
                'rollback_commands': [
                    'pip freeze > installed_before_fix.txt',
                    '# Manual rollback required - check installed_before_fix.txt'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['requirements.txt', 'pip']
            },
            
            # Node.js dependency issues  
            {
                'title': 'Fix Node.js missing module',
                'description': 'Install missing Node.js module using npm',
                'category': SolutionCategory.DEPENDENCY,
                'language': 'javascript',
                'fix_commands': [
                    'npm install {module_name}',
                    'npm audit fix'
                ],
                'verification_commands': [
                    'node -e "require(\'{module_name}\'); console.log(\'{module_name} loaded successfully\')"',
                    'npm list {module_name}'
                ],
                'rollback_commands': [
                    'npm uninstall {module_name}'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['npm', 'package.json']
            },
            {
                'title': 'Fix npm install issues with clean install',
                'description': 'Clean install npm dependencies to fix corrupted node_modules',
                'category': SolutionCategory.DEPENDENCY,
                'language': 'javascript',
                'fix_commands': [
                    'rm -rf node_modules package-lock.json',
                    'npm cache clean --force',
                    'npm install'
                ],
                'verification_commands': [
                    'npm list --depth=0',
                    'node -e "console.log(\'Node modules installed successfully\')"'
                ],
                'rollback_commands': [
                    '# Restore from backup if available',
                    'git checkout package-lock.json || true'
                ],
                'risk_level': 'medium',
                'requires_approval': True,
                'is_destructive': True,
                'prerequisites': ['npm', 'package.json']
            },
            
            # Port conflicts
            {
                'title': 'Fix port already in use (kill process)',
                'description': 'Kill the process using the conflicting port',
                'category': SolutionCategory.PROCESS,
                'language': None,  # Generic
                'fix_commands': [
                    'lsof -ti:{port} | xargs kill -9 || true',
                    'netstat -tulpn | grep :{port} || echo "Port {port} is now free"'
                ],
                'verification_commands': [
                    'lsof -i:{port} || echo "Port {port} is available"',
                    'netstat -tulpn | grep :{port} && echo "Port still in use" || echo "Port available"'
                ],
                'rollback_commands': [
                    '# No rollback needed - process was terminated'
                ],
                'risk_level': 'medium',
                'requires_approval': True,
                'is_destructive': True,
                'prerequisites': ['lsof', 'kill']
            },
            {
                'title': 'Fix port conflict by changing configuration',
                'description': 'Change application port to an available one',
                'category': SolutionCategory.CONFIGURATION,
                'language': None,
                'fix_commands': [
                    'export PORT={new_port}',
                    'sed -i.bak "s/:{old_port}/:{new_port}/g" {config_file} || true'
                ],
                'verification_commands': [
                    'lsof -i:{new_port} || echo "New port {new_port} is available"',
                    'grep "{new_port}" {config_file} || echo "Configuration updated"'
                ],
                'rollback_commands': [
                    'mv {config_file}.bak {config_file} || true',
                    'unset PORT'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['sed']
            },
            
            # File permission issues
            {
                'title': 'Fix file permission denied errors',
                'description': 'Set appropriate file permissions for project files',
                'category': SolutionCategory.PERMISSION,
                'language': None,
                'fix_commands': [
                    'chmod 755 {file_path}',
                    'chown $USER:$USER {file_path} || true'
                ],
                'verification_commands': [
                    'ls -la {file_path}',
                    'test -r {file_path} && test -w {file_path} && echo "Permissions fixed"'
                ],
                'rollback_commands': [
                    'chmod 644 {file_path}',
                    '# Original permissions may need manual restoration'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['chmod']
            },
            {
                'title': 'Fix executable permission for scripts',
                'description': 'Make scripts executable',
                'category': SolutionCategory.PERMISSION,
                'language': None,
                'fix_commands': [
                    'chmod +x {script_path}',
                    'ls -la {script_path}'
                ],
                'verification_commands': [
                    'test -x {script_path} && echo "Script is now executable"',
                    '{script_path} --help || echo "Script can be executed"'
                ],
                'rollback_commands': [
                    'chmod -x {script_path}'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['chmod']
            },
            
            # Memory issues
            {
                'title': 'Fix memory issues by restarting service',
                'description': 'Restart the service to free memory',
                'category': SolutionCategory.RESOURCE,
                'language': None,
                'fix_commands': [
                    'sudo systemctl restart {service_name} || true',
                    'pkill -f {process_name} && sleep 5 || true',
                    'nohup {start_command} > /dev/null 2>&1 &'
                ],
                'verification_commands': [
                    'ps aux | grep {process_name} | grep -v grep',
                    'curl -f {health_check_url} || echo "Service restarted"'
                ],
                'rollback_commands': [
                    '# Service restart is not easily reversible',
                    'sudo systemctl status {service_name}'
                ],
                'risk_level': 'medium',
                'requires_approval': True,
                'is_destructive': True,
                'prerequisites': ['systemctl or process management']
            },
            {
                'title': 'Fix memory issues by increasing heap size',
                'description': 'Increase JVM heap size for Java applications',
                'category': SolutionCategory.RESOURCE,
                'language': 'java',
                'fix_commands': [
                    'export JAVA_OPTS="$JAVA_OPTS -Xmx{heap_size}m"',
                    'export MAVEN_OPTS="$MAVEN_OPTS -Xmx{heap_size}m"'
                ],
                'verification_commands': [
                    'echo $JAVA_OPTS | grep "Xmx{heap_size}m"',
                    'java -XX:+PrintFlagsFinal -version | grep MaxHeapSize'
                ],
                'rollback_commands': [
                    'export JAVA_OPTS="${JAVA_OPTS/-Xmx{heap_size}m/}"',
                    'export MAVEN_OPTS="${MAVEN_OPTS/-Xmx{heap_size}m/}"'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['java']
            },
            
            # Database connection issues
            {
                'title': 'Fix database connection timeout',
                'description': 'Restart database service and check connectivity',
                'category': SolutionCategory.DATABASE,
                'language': None,
                'fix_commands': [
                    'sudo systemctl restart postgresql || brew services restart postgresql || true',
                    'sudo systemctl restart mysql || brew services restart mysql || true',
                    'sleep 10'
                ],
                'verification_commands': [
                    'pg_isready -h {db_host} -p {db_port} || echo "PostgreSQL check"',
                    'mysqladmin ping -h {db_host} -P {db_port} || echo "MySQL check"',
                    'telnet {db_host} {db_port} < /dev/null || echo "Connection test"'
                ],
                'rollback_commands': [
                    '# Database restart is not easily reversible',
                    'sudo systemctl status postgresql mysql || true'
                ],
                'risk_level': 'high',
                'requires_approval': True,
                'is_destructive': True,
                'prerequisites': ['database service']
            },
            
            # Build and compilation issues
            {
                'title': 'Fix Python package build issues',
                'description': 'Install system dependencies for Python package building',
                'category': SolutionCategory.DEPENDENCY,
                'language': 'python',
                'fix_commands': [
                    'sudo apt-get update && sudo apt-get install -y python3-dev gcc || brew install python3',
                    'pip install --upgrade setuptools wheel',
                    'pip install {package_name}'
                ],
                'verification_commands': [
                    'python3-config --cflags || python-config --cflags',
                    'gcc --version',
                    'python -c "import {package_name}; print(\'{package_name} installed\')"'
                ],
                'rollback_commands': [
                    'pip uninstall -y {package_name}',
                    '# System packages installed will remain'
                ],
                'risk_level': 'medium',
                'requires_approval': True,
                'is_destructive': False,
                'prerequisites': ['apt-get or brew', 'sudo access']
            },
            {
                'title': 'Fix npm build issues with node-gyp',
                'description': 'Install build tools for native Node.js modules',
                'category': SolutionCategory.DEPENDENCY,
                'language': 'javascript',
                'fix_commands': [
                    'npm install -g node-gyp',
                    'npm config set python /usr/bin/python3 || true',
                    'sudo apt-get install -y build-essential || xcode-select --install || true',
                    'npm rebuild'
                ],
                'verification_commands': [
                    'node-gyp --version',
                    'npm list node-gyp',
                    'npm run build || npm run compile || echo "Build tools ready"'
                ],
                'rollback_commands': [
                    'npm uninstall -g node-gyp',
                    '# System build tools will remain installed'
                ],
                'risk_level': 'medium',
                'requires_approval': True,
                'is_destructive': False,
                'prerequisites': ['npm', 'system package manager']
            },
            
            # Network connectivity issues
            {
                'title': 'Fix network connectivity by resetting DNS',
                'description': 'Reset DNS cache to fix connectivity issues',
                'category': SolutionCategory.NETWORK,
                'language': None,
                'fix_commands': [
                    'sudo dscacheutil -flushcache || true',  # macOS
                    'sudo systemctl restart systemd-resolved || true',  # Linux
                    'ipconfig /flushdns || true',  # Windows
                    'ping -c 1 8.8.8.8'
                ],
                'verification_commands': [
                    'nslookup google.com',
                    'ping -c 3 google.com',
                    'curl -I https://google.com'
                ],
                'rollback_commands': [
                    '# DNS flush is not reversible but harmless'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['network access']
            },
            
            # Git repository issues
            {
                'title': 'Fix git repository corruption',
                'description': 'Repair corrupted git repository',
                'category': SolutionCategory.CODE,
                'language': None,
                'fix_commands': [
                    'git fsck --full',
                    'git gc --prune=now',
                    'git repack -A -d'
                ],
                'verification_commands': [
                    'git status',
                    'git log --oneline -n 5',
                    'git fsck || echo "Repository repaired"'
                ],
                'rollback_commands': [
                    '# Repository repair operations are generally safe',
                    'git reflog || true'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['git']
            },
            {
                'title': 'Fix git merge conflicts',
                'description': 'Reset to last known good state and re-merge',
                'category': SolutionCategory.CODE,
                'language': None,
                'fix_commands': [
                    'git status',
                    'git reset --hard HEAD',
                    'git clean -fd'
                ],
                'verification_commands': [
                    'git status',
                    'git log --oneline -n 3'
                ],
                'rollback_commands': [
                    'git reflog',
                    '# Use git reflog to find previous state if needed'
                ],
                'risk_level': 'high',
                'requires_approval': True,
                'is_destructive': True,
                'prerequisites': ['git']
            },
            
            # Docker issues
            {
                'title': 'Fix Docker daemon not running',
                'description': 'Start Docker daemon and verify containers',
                'category': SolutionCategory.PROCESS,
                'language': None,
                'fix_commands': [
                    'sudo systemctl start docker || open -a Docker || true',
                    'sleep 5',
                    'docker ps'
                ],
                'verification_commands': [
                    'docker --version',
                    'docker ps',
                    'docker system info | head -n 10'
                ],
                'rollback_commands': [
                    'sudo systemctl stop docker || killall Docker || true'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['docker']
            },
            {
                'title': 'Fix Docker disk space issues',
                'description': 'Clean up Docker images and containers',
                'category': SolutionCategory.RESOURCE,
                'language': None,
                'fix_commands': [
                    'docker system prune -f',
                    'docker image prune -a -f',
                    'docker volume prune -f'
                ],
                'verification_commands': [
                    'docker system df',
                    'df -h | grep docker || echo "Docker cleanup completed"'
                ],
                'rollback_commands': [
                    '# Cleanup operations are not reversible',
                    '# Images will need to be re-downloaded'
                ],
                'risk_level': 'medium',
                'requires_approval': True,
                'is_destructive': True,
                'prerequisites': ['docker']
            },
            
            # Environment variable issues
            {
                'title': 'Fix missing environment variables',
                'description': 'Set required environment variables from .env file',
                'category': SolutionCategory.ENVIRONMENT,
                'language': None,
                'fix_commands': [
                    'test -f .env && source .env || echo "No .env file found"',
                    'test -f .env.example && cp .env.example .env || echo "No .env.example found"',
                    'export {var_name}={var_value}'
                ],
                'verification_commands': [
                    'echo ${var_name}',
                    'env | grep {var_name}',
                    'test -n "${var_name}" && echo "Variable set" || echo "Variable not set"'
                ],
                'rollback_commands': [
                    'unset {var_name}'
                ],
                'risk_level': 'low',
                'requires_approval': False,
                'is_destructive': False,
                'prerequisites': ['shell access']
            },
            
            # SSL/TLS certificate issues
            {
                'title': 'Fix SSL certificate errors',
                'description': 'Update certificate bundle and ignore SSL for development',
                'category': SolutionCategory.SECURITY,
                'language': None,
                'fix_commands': [
                    'sudo apt-get update && sudo apt-get install ca-certificates || brew install ca-certificates || true',
                    'export PYTHONHTTPSVERIFY=0',
                    'export NODE_TLS_REJECT_UNAUTHORIZED=0',
                    'pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org {package_name} || true'
                ],
                'verification_commands': [
                    'curl -I https://pypi.org',
                    'openssl version',
                    'python -m pip --version'
                ],
                'rollback_commands': [
                    'unset PYTHONHTTPSVERIFY',
                    'unset NODE_TLS_REJECT_UNAUTHORIZED'
                ],
                'risk_level': 'medium',
                'requires_approval': True,
                'is_destructive': False,
                'prerequisites': ['openssl', 'curl']
            }
        ]
    
    async def _create_or_update_solution(self, solution_data: Dict[str, Any]) -> None:
        """Create or update a solution in the database."""
        try:
            # Check if solution already exists
            stmt = select(Solution).where(Solution.title == solution_data['title'])
            result = await self.session.execute(stmt)
            existing = result.scalars().first()
            
            if existing:
                # Update existing solution
                for key, value in solution_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new solution
                solution = Solution(
                    id=uuid.uuid4(),
                    **solution_data
                )
                self.session.add(solution)
            
        except Exception as e:
            logger.error(f"Error creating/updating solution '{solution_data.get('title', 'unknown')}': {e}")
    
    async def add_custom_solution(
        self,
        title: str,
        description: str,
        category: str,
        fix_commands: List[str],
        verification_commands: List[str] = None,
        rollback_commands: List[str] = None,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        risk_level: str = "medium",
        requires_approval: bool = True,
        prerequisites: List[str] = None
    ) -> str:
        """
        Add a custom solution to the library.
        
        Returns:
            The ID of the created solution
        """
        try:
            solution = Solution(
                id=uuid.uuid4(),
                title=title,
                description=description,
                category=category,
                language=language,
                framework=framework,
                fix_commands=fix_commands,
                verification_commands=verification_commands or [],
                rollback_commands=rollback_commands or [],
                risk_level=risk_level,
                requires_approval=requires_approval,
                prerequisites=prerequisites or [],
                source="custom"
            )
            
            self.session.add(solution)
            await self.session.commit()
            
            logger.info(f"Added custom solution: {title}")
            return str(solution.id)
            
        except Exception as e:
            logger.error(f"Error adding custom solution: {e}")
            await self.session.rollback()
            raise
    
    async def get_solutions_by_category(self, category: str) -> List[Solution]:
        """Get all solutions for a specific category."""
        try:
            stmt = select(Solution).where(
                Solution.category == category
            ).order_by(Solution.success_rate.desc())
            
            result = await self.session.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting solutions for category {category}: {e}")
            return []
    
    async def get_solutions_by_language(self, language: str) -> List[Solution]:
        """Get all solutions for a specific programming language."""
        try:
            stmt = select(Solution).where(
                (Solution.language == language) | (Solution.language.is_(None))
            ).order_by(Solution.success_rate.desc())
            
            result = await self.session.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting solutions for language {language}: {e}")
            return []
    
    async def search_solutions(self, query: str) -> List[Solution]:
        """Search solutions by title and description."""
        try:
            search_term = f"%{query.lower()}%"
            stmt = select(Solution).where(
                (Solution.title.ilike(search_term)) |
                (Solution.description.ilike(search_term))
            ).order_by(Solution.success_rate.desc())
            
            result = await self.session.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error searching solutions for '{query}': {e}")
            return []
    
    async def get_top_solutions(self, limit: int = 10) -> List[Solution]:
        """Get top-performing solutions by success rate."""
        try:
            stmt = select(Solution).order_by(
                Solution.success_rate.desc(),
                (Solution.success_count + Solution.failure_count).desc()
            ).limit(limit)
            
            result = await self.session.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting top solutions: {e}")
            return []
    
    async def get_solution_statistics(self) -> Dict[str, Any]:
        """Get statistics about the solution library."""
        try:
            from sqlalchemy import func
            
            # Total solutions by category
            category_stmt = select(
                Solution.category,
                func.count(Solution.id).label('count'),
                func.avg(Solution.success_rate).label('avg_success_rate')
            ).group_by(Solution.category)
            
            category_result = await self.session.execute(category_stmt)
            category_stats = {
                row.category: {
                    'count': row.count,
                    'avg_success_rate': float(row.avg_success_rate or 0)
                }
                for row in category_result.fetchall()
            }
            
            # Language distribution
            language_stmt = select(
                Solution.language,
                func.count(Solution.id).label('count')
            ).where(
                Solution.language.is_not(None)
            ).group_by(Solution.language)
            
            language_result = await self.session.execute(language_stmt)
            language_stats = {
                row.language: row.count
                for row in language_result.fetchall()
            }
            
            # Overall stats
            overall_stmt = select(
                func.count(Solution.id).label('total'),
                func.avg(Solution.success_rate).label('avg_success_rate'),
                func.sum(Solution.success_count + Solution.failure_count).label('total_usage')
            )
            
            overall_result = await self.session.execute(overall_stmt)
            overall = overall_result.first()
            
            return {
                'total_solutions': overall.total or 0,
                'average_success_rate': float(overall.avg_success_rate or 0),
                'total_usage_count': overall.total_usage or 0,
                'by_category': category_stats,
                'by_language': language_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting solution statistics: {e}")
            return {}
    
    async def export_solutions(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Export all solutions to a JSON structure for backup/sharing."""
        try:
            stmt = select(Solution).order_by(Solution.category, Solution.title)
            result = await self.session.execute(stmt)
            solutions = result.scalars().all()
            
            exported_data = {
                'exported_at': datetime.utcnow().isoformat(),
                'total_solutions': len(solutions),
                'solutions': [
                    {
                        'title': sol.title,
                        'description': sol.description,
                        'category': sol.category,
                        'language': sol.language,
                        'framework': sol.framework,
                        'fix_commands': sol.fix_commands,
                        'verification_commands': sol.verification_commands,
                        'rollback_commands': sol.rollback_commands,
                        'risk_level': sol.risk_level,
                        'requires_approval': sol.requires_approval,
                        'prerequisites': sol.prerequisites,
                        'success_rate': float(sol.success_rate),
                        'usage_count': sol.success_count + sol.failure_count
                    }
                    for sol in solutions
                ]
            }
            
            if filename:
                import json
                with open(filename, 'w') as f:
                    json.dump(exported_data, f, indent=2)
                logger.info(f"Exported {len(solutions)} solutions to {filename}")
            
            return exported_data
            
        except Exception as e:
            logger.error(f"Error exporting solutions: {e}")
            return {}