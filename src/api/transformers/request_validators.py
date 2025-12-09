"""
Request Validation Layer
Comprehensive validation for API requests with custom validators and error handling.
"""

import re
import uuid
from typing import Dict, Any, List, Optional, Union, Type, Callable
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator, ValidationError as PydanticValidationError
from fastapi import HTTPException, status

from ...config import logger


class ValidationSeverity(str, Enum):
    """Validation error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationError(Exception):
    """Custom validation error with detailed information."""
    
    def __init__(self, message: str, field: str = None, code: str = None, 
                 severity: ValidationSeverity = ValidationSeverity.ERROR,
                 suggestions: List[str] = None):
        super().__init__(message)
        self.field = field
        self.code = code
        self.severity = severity
        self.suggestions = suggestions or []


class ValidationRule:
    """Custom validation rule."""
    
    def __init__(self, name: str, validator_func: Callable, 
                 severity: ValidationSeverity = ValidationSeverity.ERROR,
                 message: str = None):
        self.name = name
        self.validator_func = validator_func
        self.severity = severity
        self.message = message or f"Validation rule '{name}' failed"
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> bool:
        """Validate value against rule."""
        try:
            return self.validator_func(value, context or {})
        except Exception as e:
            logger.error(f"Validation rule {self.name} error: {e}")
            return False


class BaseValidator:
    """Base validator class with common validation methods."""
    
    def __init__(self):
        self.custom_rules: Dict[str, ValidationRule] = {}
        self.setup_rules()
    
    def setup_rules(self):
        """Setup custom validation rules. Override in subclasses."""
        pass
    
    def add_rule(self, rule: ValidationRule):
        """Add custom validation rule."""
        self.custom_rules[rule.name] = rule
    
    def validate_uuid(self, value: str, field: str = None) -> str:
        """Validate UUID format."""
        try:
            uuid.UUID(value)
            return value
        except (ValueError, TypeError):
            raise ValidationError(
                f"Invalid UUID format: {value}",
                field=field,
                code="INVALID_UUID",
                suggestions=["Use valid UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"]
            )
    
    def validate_email(self, value: str, field: str = None) -> str:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValidationError(
                f"Invalid email format: {value}",
                field=field,
                code="INVALID_EMAIL",
                suggestions=["Use format: user@domain.com"]
            )
        return value
    
    def validate_url(self, value: str, field: str = None, schemes: List[str] = None) -> str:
        """Validate URL format."""
        schemes = schemes or ["http", "https"]
        url_pattern = rf'^({"|".join(schemes)})://[^\s/$.?#].[^\s]*$'
        
        if not re.match(url_pattern, value, re.IGNORECASE):
            raise ValidationError(
                f"Invalid URL format: {value}",
                field=field,
                code="INVALID_URL",
                suggestions=[f"Use format: {schemes[0]}://domain.com/path"]
            )
        return value
    
    def validate_json(self, value: str, field: str = None) -> str:
        """Validate JSON format."""
        try:
            import json
            json.loads(value)
            return value
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"Invalid JSON format: {str(e)}",
                field=field,
                code="INVALID_JSON",
                suggestions=["Ensure valid JSON syntax with proper quotes and brackets"]
            )
    
    def validate_cron(self, value: str, field: str = None) -> str:
        """Validate cron expression format."""
        # Basic cron pattern validation (5 or 6 fields)
        cron_parts = value.split()
        if len(cron_parts) not in [5, 6]:
            raise ValidationError(
                f"Invalid cron expression: {value}",
                field=field,
                code="INVALID_CRON",
                suggestions=["Use format: '* * * * *' (minute hour day month weekday)"]
            )
        
        # Validate each part (basic validation)
        ranges = [
            (0, 59),   # minute
            (0, 23),   # hour
            (1, 31),   # day
            (1, 12),   # month
            (0, 6)     # weekday
        ]
        
        for i, (part, (min_val, max_val)) in enumerate(zip(cron_parts[:5], ranges)):
            if part != "*" and not part.isdigit():
                continue  # Skip complex expressions like */5, ranges, etc.
            
            if part.isdigit():
                val = int(part)
                if not (min_val <= val <= max_val):
                    raise ValidationError(
                        f"Cron field {i+1} value {val} out of range ({min_val}-{max_val})",
                        field=field,
                        code="INVALID_CRON_RANGE"
                    )
        
        return value
    
    def validate_custom(self, value: Any, rule_name: str, context: Dict[str, Any] = None) -> Any:
        """Validate using custom rule."""
        if rule_name not in self.custom_rules:
            raise ValidationError(
                f"Unknown validation rule: {rule_name}",
                code="UNKNOWN_RULE"
            )
        
        rule = self.custom_rules[rule_name]
        if not rule.validate(value, context):
            raise ValidationError(
                rule.message,
                code=rule.name.upper(),
                severity=rule.severity
            )
        
        return value


# Project validation models
class ProjectCreateRequest(BaseModel):
    """Project creation request validation."""
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=500, description="Project description")
    repository_url: Optional[str] = Field(None, description="Git repository URL")
    language: Optional[str] = Field(None, description="Primary programming language")
    framework: Optional[str] = Field(None, description="Framework used")
    environment_vars: Optional[Dict[str, str]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)
    
    @validator('name')
    def validate_name(cls, v):
        # Project name should be valid identifier
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError("Project name must start with letter and contain only letters, numbers, hyphens, and underscores")
        return v
    
    @validator('repository_url')
    def validate_repository_url(cls, v):
        if v:
            validator = BaseValidator()
            return validator.validate_url(v, schemes=["http", "https", "git", "ssh"])
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            for tag in v:
                if not re.match(r'^[a-zA-Z0-9_-]+$', tag):
                    raise ValueError(f"Invalid tag format: {tag}")
        return v


class ProjectUpdateRequest(BaseModel):
    """Project update request validation."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    repository_url: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    environment_vars: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v and not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError("Project name must start with letter and contain only letters, numbers, hyphens, and underscores")
        return v


# Council validation models
class CouncilDeliberationRequest(BaseModel):
    """Council deliberation request validation."""
    topic: str = Field(..., min_length=5, max_length=500, description="Deliberation topic")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    required_personas: Optional[List[str]] = Field(default_factory=list)
    priority: int = Field(5, ge=1, le=10, description="Priority level (1-10)")
    timeout_minutes: int = Field(30, ge=5, le=120, description="Timeout in minutes")
    require_consensus: bool = Field(True, description="Whether consensus is required")
    
    @validator('topic')
    def validate_topic(cls, v):
        # Topic should be a proper question or statement
        if not any(word in v.lower() for word in ['?', 'how', 'what', 'why', 'should', 'would', 'could']):
            raise ValueError("Topic should be phrased as a question or decision statement")
        return v
    
    @validator('required_personas')
    def validate_personas(cls, v):
        valid_personas = [
            'analyst', 'strategist', 'guardian', 'healer', 'innovator',
            'pragmatist', 'economist', 'architect', 'conductor'
        ]
        if v:
            for persona in v:
                if persona.lower() not in valid_personas:
                    raise ValueError(f"Invalid persona: {persona}. Valid personas: {valid_personas}")
        return v


# Orchestration validation models
class OrchestrationRequest(BaseModel):
    """Orchestration request validation."""
    project_id: str = Field(..., description="Target project ID")
    action: str = Field(..., description="Action to perform")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority: int = Field(5, ge=1, le=10)
    
    @validator('project_id')
    def validate_project_id(cls, v):
        validator = BaseValidator()
        return validator.validate_uuid(v)
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['start', 'stop', 'restart', 'deploy', 'scale', 'analyze', 'optimize']
        if v.lower() not in valid_actions:
            raise ValueError(f"Invalid action: {v}. Valid actions: {valid_actions}")
        return v.lower()
    
    @validator('params')
    def validate_params(cls, v, values):
        action = values.get('action')
        if not action:
            return v
        
        # Validate parameters based on action
        if action == 'scale' and 'replicas' in v:
            replicas = v['replicas']
            if not isinstance(replicas, int) or replicas < 0:
                raise ValueError("Replicas must be a non-negative integer")
        
        if action == 'deploy' and 'environment' in v:
            env = v['environment']
            valid_envs = ['development', 'staging', 'production']
            if env not in valid_envs:
                raise ValueError(f"Invalid environment: {env}. Valid: {valid_envs}")
        
        return v


# Deployment validation models
class DeploymentRequest(BaseModel):
    """Deployment request validation."""
    project_id: str = Field(..., description="Project to deploy")
    environment: str = Field(..., description="Target environment")
    strategy: str = Field("rolling", description="Deployment strategy")
    git_ref: Optional[str] = Field("main", description="Git reference")
    build_args: Optional[Dict[str, str]] = Field(default_factory=dict)
    environment_vars: Optional[Dict[str, str]] = Field(default_factory=dict)
    replicas: int = Field(1, ge=1, le=100, description="Number of replicas")
    health_check_url: Optional[str] = None
    rollback_on_failure: bool = Field(True)
    
    @validator('environment')
    def validate_environment(cls, v):
        valid_environments = ['development', 'staging', 'production', 'testing']
        if v.lower() not in valid_environments:
            raise ValueError(f"Invalid environment: {v}. Valid: {valid_environments}")
        return v.lower()
    
    @validator('strategy')
    def validate_strategy(cls, v):
        valid_strategies = ['blue_green', 'rolling', 'canary', 'recreate', 'immediate']
        if v.lower() not in valid_strategies:
            raise ValueError(f"Invalid strategy: {v}. Valid: {valid_strategies}")
        return v.lower()
    
    @validator('git_ref')
    def validate_git_ref(cls, v):
        if v:
            # Basic validation for git references
            if not re.match(r'^[a-zA-Z0-9._/-]+$', v):
                raise ValueError("Invalid git reference format")
        return v
    
    @validator('health_check_url')
    def validate_health_check_url(cls, v):
        if v:
            validator = BaseValidator()
            return validator.validate_url(v)
        return v


# User management validation models
class UserCreateRequest(BaseModel):
    """User creation request validation."""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field("viewer", description="User role")
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v:
            validator = BaseValidator()
            return validator.validate_email(v)
        return v
    
    @validator('password')
    def validate_password(cls, v):
        # Password strength validation
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        
        return v
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['admin', 'developer', 'viewer', 'api_user', 'guest']
        if v.lower() not in valid_roles:
            raise ValueError(f"Invalid role: {v}. Valid roles: {valid_roles}")
        return v.lower()


# Backup validation models
class BackupRequest(BaseModel):
    """Backup request validation."""
    project_id: Optional[str] = None
    backup_type: str = Field(..., description="Type of backup")
    include_patterns: List[str] = Field(default_factory=lambda: ["*"])
    exclude_patterns: List[str] = Field(default_factory=list)
    compression: bool = Field(True)
    encryption: bool = Field(False)
    retention_days: int = Field(30, ge=1, le=365)
    
    @validator('backup_type')
    def validate_backup_type(cls, v):
        valid_types = ['full', 'incremental', 'differential', 'database', 'files', 'config']
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid backup type: {v}. Valid types: {valid_types}")
        return v.lower()
    
    @validator('include_patterns', 'exclude_patterns')
    def validate_patterns(cls, v):
        for pattern in v:
            # Basic pattern validation
            if not isinstance(pattern, str) or len(pattern.strip()) == 0:
                raise ValueError("Patterns must be non-empty strings")
        return v


# Request validation functions
def validate_project_request(data: Dict[str, Any], update: bool = False) -> Dict[str, Any]:
    """Validate project request data."""
    try:
        if update:
            validated = ProjectUpdateRequest(**data)
        else:
            validated = ProjectCreateRequest(**data)
        return validated.dict(exclude_unset=True)
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )


def validate_council_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate council deliberation request."""
    try:
        validated = CouncilDeliberationRequest(**data)
        return validated.dict()
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )


def validate_orchestration_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate orchestration request."""
    try:
        validated = OrchestrationRequest(**data)
        return validated.dict()
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )


def validate_deployment_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate deployment request."""
    try:
        validated = DeploymentRequest(**data)
        return validated.dict()
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )


def validate_user_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate user creation request."""
    try:
        validated = UserCreateRequest(**data)
        return validated.dict()
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )


def validate_backup_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate backup request."""
    try:
        validated = BackupRequest(**data)
        return validated.dict()
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )


# Pagination validation
class PaginationParams(BaseModel):
    """Pagination parameters validation."""
    page: int = Field(1, ge=1, le=10000, description="Page number")
    size: int = Field(20, ge=1, le=1000, description="Page size")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("asc", regex="^(asc|desc)$", description="Sort order")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        if v:
            # Validate sort field contains only safe characters
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_.]*$', v):
                raise ValueError("Invalid sort field format")
        return v


def validate_pagination_params(page: int = 1, size: int = 20, 
                             sort_by: str = None, sort_order: str = "asc") -> Dict[str, Any]:
    """Validate pagination parameters."""
    try:
        validated = PaginationParams(
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return validated.dict()
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )


# Bulk validation utilities
def validate_batch_request(data: List[Dict[str, Any]], validator_func: Callable) -> List[Dict[str, Any]]:
    """Validate batch request with individual validation."""
    validated_items = []
    errors = []
    
    for i, item in enumerate(data):
        try:
            validated_items.append(validator_func(item))
        except HTTPException as e:
            errors.append({
                "index": i,
                "item": item,
                "errors": e.detail
            })
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Batch validation failed",
                "item_errors": errors,
                "valid_count": len(validated_items),
                "error_count": len(errors)
            }
        )
    
    return validated_items


# Custom validation rules setup
def setup_custom_validation_rules() -> BaseValidator:
    """Setup custom validation rules."""
    validator = BaseValidator()
    
    # Add custom rules
    validator.add_rule(ValidationRule(
        name="project_name_unique",
        validator_func=lambda value, context: True,  # Would check database
        severity=ValidationSeverity.ERROR,
        message="Project name must be unique"
    ))
    
    validator.add_rule(ValidationRule(
        name="deployment_environment_available", 
        validator_func=lambda value, context: value in context.get("available_environments", []),
        severity=ValidationSeverity.ERROR,
        message="Deployment environment not available"
    ))
    
    return validator