"""
Environment Manager Service

Manages environment configurations, variable handling, and environment switching
for projects across development, staging, and production environments.
"""

import os
import json
import yaml
import logging
import hashlib
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EnvironmentType(Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"
    LOCAL = "local"


@dataclass
class EnvironmentVariable:
    """Represents an environment variable with metadata."""
    key: str
    value: str
    is_secret: bool = False
    description: Optional[str] = None
    required: bool = True
    default_value: Optional[str] = None
    validation_pattern: Optional[str] = None


@dataclass
class Environment:
    """Complete environment configuration."""
    name: str
    type: EnvironmentType
    variables: Dict[str, EnvironmentVariable] = field(default_factory=dict)
    config_files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    active: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert environment to dictionary format."""
        return {
            "name": self.name,
            "type": self.type.value,
            "variables": {k: {
                "value": "***REDACTED***" if v.is_secret else v.value,
                "is_secret": v.is_secret,
                "description": v.description,
                "required": v.required,
                "default_value": v.default_value,
                "validation_pattern": v.validation_pattern
            } for k, v in self.variables.items()},
            "config_files": list(self.config_files.keys()),
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "description": self.description
        }


@dataclass
class EnvironmentTemplate:
    """Template for creating new environments."""
    name: str
    description: str
    variables: List[EnvironmentVariable]
    config_files: Dict[str, str] = field(default_factory=dict)
    target_types: List[EnvironmentType] = field(default_factory=list)


class EnvironmentManager:
    """
    Manages project environments including variable handling, configuration files,
    and environment switching with proper secret management.
    """
    
    def __init__(self, base_projects_path: str = "/Users/nathanial.smalley/projects"):
        """
        Initialize the EnvironmentManager.
        
        Args:
            base_projects_path: Base directory containing all projects
        """
        self.base_projects_path = Path(base_projects_path)
        self.environments_cache: Dict[str, Dict[str, Environment]] = {}  # project_id -> env_name -> Environment
        
        # Secret management
        self.secret_patterns = [
            "password", "secret", "key", "token", "api", "auth",
            "credential", "private", "cert", "ssl", "jwt"
        ]
        
        # Environment templates
        self.templates: Dict[str, EnvironmentTemplate] = {}
        self._load_default_templates()
        
        logger.info(f"EnvironmentManager initialized with base path: {self.base_projects_path}")
    
    async def switch_environment(self, project_id: str, environment_name: str) -> bool:
        """
        Switch a project to a different environment.
        
        Args:
            project_id: Project identifier
            environment_name: Target environment name
            
        Returns:
            bool: True if successfully switched
        """
        logger.info(f"Switching project {project_id} to environment {environment_name}")
        
        try:
            project_path = await self._find_project_path(project_id)
            environments = await self._load_project_environments(project_id)
            
            if environment_name not in environments:
                raise ValueError(f"Environment '{environment_name}' not found for project {project_id}")
            
            target_env = environments[environment_name]
            
            # Deactivate current environment
            for env_name, env in environments.items():
                if env.active and env_name != environment_name:
                    env.active = False
                    await self._save_environment_config(project_id, env_name, env)
            
            # Activate target environment
            target_env.active = True
            target_env.last_modified = datetime.now()
            
            # Apply environment variables
            await self._apply_environment_variables(project_path, target_env)
            
            # Apply configuration files
            await self._apply_config_files(project_path, target_env)
            
            # Save updated configuration
            await self._save_environment_config(project_id, environment_name, target_env)
            
            # Update cache
            self.environments_cache[project_id][environment_name] = target_env
            
            logger.info(f"Successfully switched {project_id} to {environment_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch environment for {project_id}: {str(e)}")
            return False
    
    async def load_env_file(self, project_id: str, env_file_path: str) -> Dict[str, str]:
        """
        Load environment variables from a file.
        
        Args:
            project_id: Project identifier
            env_file_path: Path to environment file
            
        Returns:
            Dict[str, str]: Environment variables
        """
        logger.info(f"Loading environment file {env_file_path} for project {project_id}")
        
        try:
            project_path = await self._find_project_path(project_id)
            full_path = project_path / env_file_path
            
            if not full_path.exists():
                logger.warning(f"Environment file {full_path} not found")
                return {}
            
            variables = {}
            
            with open(full_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse variable assignment
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        variables[key] = value
                    else:
                        logger.warning(f"Invalid line {line_num} in {env_file_path}: {line}")
            
            logger.info(f"Loaded {len(variables)} variables from {env_file_path}")
            return variables
            
        except Exception as e:
            logger.error(f"Failed to load environment file {env_file_path}: {str(e)}")
            return {}
    
    async def set_variables(self, project_id: str, variables: Dict[str, str], environment_name: str = "development") -> bool:
        """
        Set environment variables for a project.
        
        Args:
            project_id: Project identifier
            variables: Variables to set
            environment_name: Target environment name
            
        Returns:
            bool: True if successfully set
        """
        logger.info(f"Setting {len(variables)} variables for {project_id} in {environment_name}")
        
        try:
            environments = await self._load_project_environments(project_id)
            
            # Get or create environment
            if environment_name not in environments:
                environment = Environment(
                    name=environment_name,
                    type=EnvironmentType(environment_name) if environment_name in [e.value for e in EnvironmentType] else EnvironmentType.DEVELOPMENT
                )
                environments[environment_name] = environment
            else:
                environment = environments[environment_name]
            
            # Process and set variables
            for key, value in variables.items():
                is_secret = await self._is_secret_variable(key, value)
                
                env_var = EnvironmentVariable(
                    key=key,
                    value=value,
                    is_secret=is_secret,
                    description=f"Set via API at {datetime.now().isoformat()}"
                )
                
                environment.variables[key] = env_var
                
                if not is_secret:
                    logger.debug(f"Set variable {key}={value}")
                else:
                    logger.debug(f"Set secret variable {key}=***")
            
            environment.last_modified = datetime.now()
            
            # Save configuration
            await self._save_environment_config(project_id, environment_name, environment)
            
            # Update cache
            if project_id not in self.environments_cache:
                self.environments_cache[project_id] = {}
            self.environments_cache[project_id][environment_name] = environment
            
            logger.info(f"Successfully set variables for {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set variables for {project_id}: {str(e)}")
            return False
    
    async def get_environment(self, project_id: str, environment_name: str = None) -> Optional[Environment]:
        """
        Get environment configuration for a project.
        
        Args:
            project_id: Project identifier
            environment_name: Environment name (if None, returns active environment)
            
        Returns:
            Optional[Environment]: Environment configuration
        """
        try:
            environments = await self._load_project_environments(project_id)
            
            if environment_name:
                return environments.get(environment_name)
            else:
                # Return active environment
                for env in environments.values():
                    if env.active:
                        return env
                
                # If no active environment, return development if it exists
                return environments.get("development")
        
        except Exception as e:
            logger.error(f"Failed to get environment for {project_id}: {str(e)}")
            return None
    
    async def create_env_template(self, project_id: str, template_name: str = "default") -> str:
        """
        Create an environment template file for a project.
        
        Args:
            project_id: Project identifier
            template_name: Name of template to use
            
        Returns:
            str: Path to created template file
        """
        logger.info(f"Creating environment template for {project_id} using {template_name}")
        
        try:
            project_path = await self._find_project_path(project_id)
            
            # Get template
            if template_name not in self.templates:
                template_name = "default"
            
            template = self.templates[template_name]
            
            # Create .env.example file
            env_example_path = project_path / ".env.example"
            
            with open(env_example_path, 'w') as f:
                f.write(f"# Environment configuration for {project_id}\n")
                f.write(f"# Generated by Optimus on {datetime.now().isoformat()}\n")
                f.write(f"# Template: {template.name}\n\n")
                
                if template.description:
                    f.write(f"# {template.description}\n\n")
                
                for var in template.variables:
                    if var.description:
                        f.write(f"# {var.description}\n")
                    
                    if var.required:
                        f.write(f"# Required: Yes\n")
                    
                    if var.default_value:
                        f.write(f"# Default: {var.default_value}\n")
                    
                    if var.validation_pattern:
                        f.write(f"# Pattern: {var.validation_pattern}\n")
                    
                    if var.is_secret:
                        f.write(f"{var.key}=your_secret_here\n\n")
                    else:
                        value = var.default_value or "your_value_here"
                        f.write(f"{var.key}={value}\n\n")
            
            # Create configuration files from template
            for filename, content in template.config_files.items():
                config_path = project_path / filename
                config_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(config_path, 'w') as f:
                    f.write(content)
            
            logger.info(f"Created environment template at {env_example_path}")
            return str(env_example_path)
            
        except Exception as e:
            logger.error(f"Failed to create environment template for {project_id}: {str(e)}")
            raise
    
    async def list_environments(self, project_id: str) -> List[Environment]:
        """
        List all environments for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List[Environment]: All environments
        """
        try:
            environments = await self._load_project_environments(project_id)
            return list(environments.values())
        except Exception as e:
            logger.error(f"Failed to list environments for {project_id}: {str(e)}")
            return []
    
    async def delete_environment(self, project_id: str, environment_name: str) -> bool:
        """
        Delete an environment configuration.
        
        Args:
            project_id: Project identifier
            environment_name: Environment to delete
            
        Returns:
            bool: True if successfully deleted
        """
        logger.info(f"Deleting environment {environment_name} for project {project_id}")
        
        try:
            project_path = await self._find_project_path(project_id)
            env_config_path = project_path / ".optimus" / "environments" / f"{environment_name}.yml"
            
            if env_config_path.exists():
                env_config_path.unlink()
                logger.info(f"Deleted environment config file {env_config_path}")
            
            # Remove from cache
            if project_id in self.environments_cache and environment_name in self.environments_cache[project_id]:
                del self.environments_cache[project_id][environment_name]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete environment {environment_name}: {str(e)}")
            return False
    
    async def validate_environment(self, project_id: str, environment_name: str) -> Dict[str, Any]:
        """
        Validate an environment configuration.
        
        Args:
            project_id: Project identifier
            environment_name: Environment to validate
            
        Returns:
            Dict[str, Any]: Validation results
        """
        logger.info(f"Validating environment {environment_name} for project {project_id}")
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "missing_files": []
        }
        
        try:
            environment = await self.get_environment(project_id, environment_name)
            
            if not environment:
                results["valid"] = False
                results["errors"].append(f"Environment '{environment_name}' not found")
                return results
            
            # Validate required variables
            for var in environment.variables.values():
                if var.required and not var.value:
                    results["missing_required"].append(var.key)
                    results["valid"] = False
                
                # Validate patterns
                if var.validation_pattern and var.value:
                    import re
                    if not re.match(var.validation_pattern, var.value):
                        results["errors"].append(f"Variable {var.key} doesn't match pattern {var.validation_pattern}")
                        results["valid"] = False
            
            # Check for missing configuration files
            project_path = await self._find_project_path(project_id)
            for filename in environment.config_files:
                file_path = project_path / filename
                if not file_path.exists():
                    results["missing_files"].append(filename)
                    results["warnings"].append(f"Configuration file {filename} not found")
            
            # Check for potential security issues
            for var in environment.variables.values():
                if not var.is_secret and await self._is_secret_variable(var.key, var.value):
                    results["warnings"].append(f"Variable {var.key} might be a secret but not marked as such")
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Validation error: {str(e)}")
        
        return results
    
    # Private helper methods
    
    async def _find_project_path(self, project_id: str) -> Path:
        """Find the filesystem path for a project."""
        project_path = self.base_projects_path / project_id
        if project_path.exists():
            return project_path
        
        # Search for project in subdirectories
        for item in self.base_projects_path.iterdir():
            if item.is_dir() and item.name.lower() == project_id.lower():
                return item
        
        raise ValueError(f"Project {project_id} not found in {self.base_projects_path}")
    
    async def _load_project_environments(self, project_id: str) -> Dict[str, Environment]:
        """Load all environments for a project."""
        if project_id in self.environments_cache:
            return self.environments_cache[project_id]
        
        project_path = await self._find_project_path(project_id)
        environments = {}
        
        # Load from .optimus/environments/ directory
        env_dir = project_path / ".optimus" / "environments"
        if env_dir.exists():
            for env_file in env_dir.glob("*.yml"):
                try:
                    with open(env_file) as f:
                        env_data = yaml.safe_load(f)
                    
                    environment = await self._parse_environment_data(env_data)
                    environments[environment.name] = environment
                    
                except Exception as e:
                    logger.warning(f"Failed to load environment file {env_file}: {e}")
        
        # Load from legacy .env files
        await self._load_legacy_env_files(project_path, environments)
        
        # Cache and return
        self.environments_cache[project_id] = environments
        return environments
    
    async def _parse_environment_data(self, data: Dict[str, Any]) -> Environment:
        """Parse environment data from configuration file."""
        environment = Environment(
            name=data.get("name", "unknown"),
            type=EnvironmentType(data.get("type", "development")),
            description=data.get("description"),
            active=data.get("active", False),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_modified=datetime.fromisoformat(data.get("last_modified", datetime.now().isoformat()))
        )
        
        # Parse variables
        variables_data = data.get("variables", {})
        for key, var_data in variables_data.items():
            if isinstance(var_data, str):
                # Simple string value
                is_secret = await self._is_secret_variable(key, var_data)
                env_var = EnvironmentVariable(key=key, value=var_data, is_secret=is_secret)
            else:
                # Full variable definition
                env_var = EnvironmentVariable(
                    key=key,
                    value=var_data.get("value", ""),
                    is_secret=var_data.get("is_secret", False),
                    description=var_data.get("description"),
                    required=var_data.get("required", True),
                    default_value=var_data.get("default_value"),
                    validation_pattern=var_data.get("validation_pattern")
                )
            
            environment.variables[key] = env_var
        
        # Parse config files
        environment.config_files = data.get("config_files", {})
        
        return environment
    
    async def _load_legacy_env_files(self, project_path: Path, environments: Dict[str, Environment]):
        """Load environments from legacy .env files."""
        env_files = [
            (".env", "development"),
            (".env.development", "development"),
            (".env.staging", "staging"),
            (".env.production", "production"),
            (".env.test", "testing"),
            (".env.local", "local")
        ]
        
        for filename, env_name in env_files:
            env_file = project_path / filename
            if env_file.exists() and env_name not in environments:
                variables_dict = await self.load_env_file("temp", filename)
                
                if variables_dict:
                    environment = Environment(
                        name=env_name,
                        type=EnvironmentType(env_name) if env_name in [e.value for e in EnvironmentType] else EnvironmentType.DEVELOPMENT,
                        active=(env_name == "development")
                    )
                    
                    for key, value in variables_dict.items():
                        is_secret = await self._is_secret_variable(key, value)
                        env_var = EnvironmentVariable(
                            key=key,
                            value=value,
                            is_secret=is_secret,
                            description=f"Loaded from {filename}"
                        )
                        environment.variables[key] = env_var
                    
                    environments[env_name] = environment
    
    async def _save_environment_config(self, project_id: str, environment_name: str, environment: Environment):
        """Save environment configuration to file."""
        project_path = await self._find_project_path(project_id)
        env_dir = project_path / ".optimus" / "environments"
        env_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = env_dir / f"{environment_name}.yml"
        
        # Prepare data for saving
        config_data = {
            "name": environment.name,
            "type": environment.type.value,
            "description": environment.description,
            "active": environment.active,
            "created_at": environment.created_at.isoformat(),
            "last_modified": environment.last_modified.isoformat(),
            "variables": {},
            "config_files": environment.config_files
        }
        
        # Save variables (excluding secret values for security)
        for key, var in environment.variables.items():
            if var.is_secret:
                config_data["variables"][key] = {
                    "is_secret": True,
                    "description": var.description,
                    "required": var.required,
                    "validation_pattern": var.validation_pattern,
                    "value_hash": hashlib.sha256(var.value.encode()).hexdigest()[:16]
                }
            else:
                config_data["variables"][key] = {
                    "value": var.value,
                    "is_secret": var.is_secret,
                    "description": var.description,
                    "required": var.required,
                    "default_value": var.default_value,
                    "validation_pattern": var.validation_pattern
                }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=True)
    
    async def _apply_environment_variables(self, project_path: Path, environment: Environment):
        """Apply environment variables to .env file."""
        env_file = project_path / ".env"
        
        # Backup existing .env
        if env_file.exists():
            backup_path = project_path / f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy(env_file, backup_path)
        
        # Write new .env file
        with open(env_file, 'w') as f:
            f.write(f"# Environment: {environment.name}\n")
            f.write(f"# Last updated: {datetime.now().isoformat()}\n")
            f.write(f"# Managed by Optimus EnvironmentManager\n\n")
            
            for var in environment.variables.values():
                if var.description:
                    f.write(f"# {var.description}\n")
                f.write(f"{var.key}={var.value}\n")
                f.write("\n")
    
    async def _apply_config_files(self, project_path: Path, environment: Environment):
        """Apply configuration files for the environment."""
        for filename, content in environment.config_files.items():
            config_path = project_path / filename
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file
            if config_path.exists():
                backup_path = config_path.parent / f"{config_path.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy(config_path, backup_path)
            
            # Write new configuration
            with open(config_path, 'w') as f:
                f.write(content)
    
    async def _is_secret_variable(self, key: str, value: str) -> bool:
        """Determine if a variable should be treated as a secret."""
        key_lower = key.lower()
        
        # Check against known secret patterns
        for pattern in self.secret_patterns:
            if pattern in key_lower:
                return True
        
        # Check value patterns
        if len(value) > 20 and any(c in value for c in ['_', '-', '=']):
            # Looks like an encoded secret
            return True
        
        return False
    
    def _load_default_templates(self):
        """Load default environment templates."""
        # Web application template
        web_template = EnvironmentTemplate(
            name="web_application",
            description="Standard web application environment",
            variables=[
                EnvironmentVariable("PORT", "3000", description="Server port"),
                EnvironmentVariable("HOST", "localhost", description="Server host"),
                EnvironmentVariable("NODE_ENV", "development", description="Node.js environment"),
                EnvironmentVariable("DATABASE_URL", "", is_secret=True, required=True, description="Database connection string"),
                EnvironmentVariable("JWT_SECRET", "", is_secret=True, required=True, description="JWT signing secret"),
                EnvironmentVariable("API_KEY", "", is_secret=True, required=False, description="External API key")
            ],
            target_types=[EnvironmentType.DEVELOPMENT, EnvironmentType.STAGING, EnvironmentType.PRODUCTION]
        )
        
        # API service template
        api_template = EnvironmentTemplate(
            name="api_service",
            description="REST API service environment",
            variables=[
                EnvironmentVariable("API_PORT", "8000", description="API server port"),
                EnvironmentVariable("API_HOST", "0.0.0.0", description="API server host"),
                EnvironmentVariable("DEBUG", "true", description="Debug mode"),
                EnvironmentVariable("LOG_LEVEL", "INFO", description="Logging level"),
                EnvironmentVariable("DATABASE_URL", "", is_secret=True, required=True, description="Database URL"),
                EnvironmentVariable("REDIS_URL", "", is_secret=True, required=False, description="Redis URL"),
                EnvironmentVariable("SECRET_KEY", "", is_secret=True, required=True, description="Application secret key")
            ],
            target_types=[EnvironmentType.DEVELOPMENT, EnvironmentType.STAGING, EnvironmentType.PRODUCTION]
        )
        
        # Default template
        default_template = EnvironmentTemplate(
            name="default",
            description="Basic environment template",
            variables=[
                EnvironmentVariable("APP_NAME", "my_app", description="Application name"),
                EnvironmentVariable("APP_ENV", "development", description="Application environment"),
                EnvironmentVariable("DEBUG", "true", description="Debug mode")
            ],
            target_types=[EnvironmentType.DEVELOPMENT]
        )
        
        self.templates = {
            "web_application": web_template,
            "api_service": api_template,
            "default": default_template
        }