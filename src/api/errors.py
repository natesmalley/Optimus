"""
Comprehensive Error Handling System
Provides standardized error responses, tracking, and graceful degradation.
"""

import traceback
import asyncio
from typing import Dict, Any, List, Optional, Type
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from redis.asyncio import Redis

from ..config import get_settings, redis_manager, logger


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RESOURCE_NOT_FOUND = "resource_not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorMetrics:
    """Error metrics tracking."""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = None
    errors_by_endpoint: Dict[str, int] = None
    errors_by_status_code: Dict[int, int] = None
    recent_errors: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors_by_category is None:
            self.errors_by_category = {}
        if self.errors_by_endpoint is None:
            self.errors_by_endpoint = {}
        if self.errors_by_status_code is None:
            self.errors_by_status_code = {}
        if self.recent_errors is None:
            self.recent_errors = []


class ErrorDetails(BaseModel):
    """Standardized error response."""
    error: str
    error_code: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    help_url: Optional[str] = None
    retry_after: Optional[int] = None


class RetryConfig(BaseModel):
    """Retry configuration for failed operations."""
    max_attempts: int = 3
    base_delay: float = 1.0
    exponential_base: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True


class CircuitBreakerState:
    """Circuit breaker for external services."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
    
    def should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        current_time = datetime.now().timestamp()
        
        if self.state == "closed":
            return True
        elif self.state == "open":
            if current_time - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        else:  # half_open
            return True
    
    def on_success(self):
        """Record successful request."""
        self.failure_count = 0
        if self.state == "half_open":
            self.state = "closed"
    
    def on_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class ErrorHandler:
    """Comprehensive error handling system."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or redis_manager.client
        self.settings = get_settings()
        self.metrics = ErrorMetrics()
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.dead_letter_queue: List[Dict[str, Any]] = []
        
        # Error mappings
        self.error_mappings = {
            ValidationError: {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY
            },
            AuthenticationError: {
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "status_code": status.HTTP_401_UNAUTHORIZED
            },
            AuthorizationError: {
                "category": ErrorCategory.AUTHORIZATION,
                "severity": ErrorSeverity.MEDIUM,
                "status_code": status.HTTP_403_FORBIDDEN
            },
            ResourceNotFoundError: {
                "category": ErrorCategory.RESOURCE_NOT_FOUND,
                "severity": ErrorSeverity.LOW,
                "status_code": status.HTTP_404_NOT_FOUND
            },
            BusinessLogicError: {
                "category": ErrorCategory.BUSINESS_LOGIC,
                "severity": ErrorSeverity.MEDIUM,
                "status_code": status.HTTP_400_BAD_REQUEST
            },
            ExternalServiceError: {
                "category": ErrorCategory.EXTERNAL_SERVICE,
                "severity": ErrorSeverity.HIGH,
                "status_code": status.HTTP_502_BAD_GATEWAY
            },
            RateLimitError: {
                "category": ErrorCategory.RATE_LIMIT,
                "severity": ErrorSeverity.LOW,
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS
            },
            TimeoutError: {
                "category": ErrorCategory.TIMEOUT,
                "severity": ErrorSeverity.MEDIUM,
                "status_code": status.HTTP_504_GATEWAY_TIMEOUT
            },
            DatabaseError: {
                "category": ErrorCategory.DATABASE_ERROR,
                "severity": ErrorSeverity.HIGH,
                "status_code": status.HTTP_503_SERVICE_UNAVAILABLE
            },
            ConfigurationError: {
                "category": ErrorCategory.CONFIGURATION_ERROR,
                "severity": ErrorSeverity.CRITICAL,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        }
        
        # Help URLs for common errors
        self.help_urls = {
            ErrorCategory.VALIDATION: "/docs/api/validation-errors",
            ErrorCategory.AUTHENTICATION: "/docs/api/authentication",
            ErrorCategory.AUTHORIZATION: "/docs/api/permissions",
            ErrorCategory.RATE_LIMIT: "/docs/api/rate-limits"
        }
    
    async def handle_error(self, request: Request, error: Exception) -> JSONResponse:
        """Handle and format error response."""
        error_info = self._classify_error(error)
        request_id = getattr(request.state, "request_id", None)
        
        # Record error metrics
        await self._record_error(request, error, error_info)
        
        # Create error response
        error_details = ErrorDetails(
            error=str(error),
            error_code=error_info["error_code"],
            category=error_info["category"],
            severity=error_info["severity"],
            timestamp=datetime.now(),
            request_id=request_id,
            details=error_info.get("details"),
            help_url=self.help_urls.get(error_info["category"]),
            retry_after=error_info.get("retry_after")
        )
        
        # Log error based on severity
        log_message = f"API Error: {error_details.error_code} - {str(error)}"
        
        if error_details.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={
                "request_id": request_id,
                "category": error_details.category,
                "endpoint": str(request.url),
                "method": request.method
            })
        elif error_details.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={
                "request_id": request_id,
                "category": error_details.category
            })
        elif error_details.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={"request_id": request_id})
        else:
            logger.info(log_message, extra={"request_id": request_id})
        
        # Return appropriate HTTP response
        response_content = error_details.dict()
        
        # Remove sensitive information in production
        if not self.settings.debug:
            if "details" in response_content:
                response_content["details"] = self._sanitize_details(
                    response_content["details"]
                )
        
        return JSONResponse(
            status_code=error_info["status_code"],
            content=response_content,
            headers=self._get_error_headers(error_details)
        )
    
    def _classify_error(self, error: Exception) -> Dict[str, Any]:
        """Classify error and determine response."""
        error_type = type(error)
        
        # Check custom error mappings
        for error_class, mapping in self.error_mappings.items():
            if isinstance(error, error_class):
                return {
                    "error_code": f"{mapping['category'].value.upper()}_{error_class.__name__.upper()}",
                    "category": mapping["category"],
                    "severity": mapping["severity"],
                    "status_code": mapping["status_code"],
                    "details": self._extract_error_details(error)
                }
        
        # Handle FastAPI validation errors
        if isinstance(error, RequestValidationError):
            return {
                "error_code": "VALIDATION_ERROR",
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": {"validation_errors": error.errors()}
            }
        
        # Handle HTTP exceptions
        if isinstance(error, (HTTPException, StarletteHTTPException)):
            category = self._categorize_http_error(error.status_code)
            return {
                "error_code": f"HTTP_{error.status_code}",
                "category": category,
                "severity": self._determine_severity(category, error.status_code),
                "status_code": error.status_code,
                "details": {"detail": error.detail}
            }
        
        # Handle standard Python exceptions
        if isinstance(error, asyncio.TimeoutError):
            return {
                "error_code": "TIMEOUT_ERROR",
                "category": ErrorCategory.TIMEOUT,
                "severity": ErrorSeverity.MEDIUM,
                "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
                "retry_after": 30
            }
        
        if isinstance(error, ConnectionError):
            return {
                "error_code": "CONNECTION_ERROR",
                "category": ErrorCategory.NETWORK_ERROR,
                "severity": ErrorSeverity.HIGH,
                "status_code": status.HTTP_502_BAD_GATEWAY,
                "retry_after": 60
            }
        
        # Default internal server error
        return {
            "error_code": "INTERNAL_SERVER_ERROR",
            "category": ErrorCategory.INTERNAL_ERROR,
            "severity": ErrorSeverity.CRITICAL,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "details": {"exception_type": error_type.__name__}
        }
    
    def _categorize_http_error(self, status_code: int) -> ErrorCategory:
        """Categorize HTTP status codes."""
        if status_code == 401:
            return ErrorCategory.AUTHENTICATION
        elif status_code == 403:
            return ErrorCategory.AUTHORIZATION
        elif status_code == 404:
            return ErrorCategory.RESOURCE_NOT_FOUND
        elif status_code == 422:
            return ErrorCategory.VALIDATION
        elif status_code == 429:
            return ErrorCategory.RATE_LIMIT
        elif 400 <= status_code < 500:
            return ErrorCategory.BUSINESS_LOGIC
        elif 500 <= status_code < 600:
            return ErrorCategory.INTERNAL_ERROR
        else:
            return ErrorCategory.INTERNAL_ERROR
    
    def _determine_severity(self, category: ErrorCategory, status_code: int) -> ErrorSeverity:
        """Determine error severity."""
        if category in [ErrorCategory.CONFIGURATION_ERROR]:
            return ErrorSeverity.CRITICAL
        elif category in [ErrorCategory.EXTERNAL_SERVICE, ErrorCategory.DATABASE_ERROR]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION, 
                         ErrorCategory.BUSINESS_LOGIC, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """Extract additional details from error."""
        details = {}
        
        if hasattr(error, "details"):
            details["details"] = error.details
        
        if hasattr(error, "field"):
            details["field"] = error.field
        
        if hasattr(error, "code"):
            details["code"] = error.code
        
        if self.settings.debug:
            details["traceback"] = traceback.format_exc()
        
        return details
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize error details for production."""
        sanitized = {}
        
        # Only include safe fields
        safe_fields = ["field", "code", "validation_errors", "detail"]
        for field in safe_fields:
            if field in details:
                sanitized[field] = details[field]
        
        return sanitized
    
    def _get_error_headers(self, error_details: ErrorDetails) -> Dict[str, str]:
        """Get appropriate response headers for error."""
        headers = {
            "X-Error-Code": error_details.error_code,
            "X-Error-Category": error_details.category.value,
            "X-Request-ID": error_details.request_id or "unknown"
        }
        
        if error_details.retry_after:
            headers["Retry-After"] = str(error_details.retry_after)
        
        if error_details.help_url:
            headers["X-Help-URL"] = error_details.help_url
        
        return headers
    
    async def _record_error(self, request: Request, error: Exception, error_info: Dict[str, Any]):
        """Record error metrics and tracking."""
        try:
            # Update metrics
            self.metrics.total_errors += 1
            
            category = error_info["category"].value
            if category not in self.metrics.errors_by_category:
                self.metrics.errors_by_category[category] = 0
            self.metrics.errors_by_category[category] += 1
            
            endpoint = str(request.url.path)
            if endpoint not in self.metrics.errors_by_endpoint:
                self.metrics.errors_by_endpoint[endpoint] = 0
            self.metrics.errors_by_endpoint[endpoint] += 1
            
            status_code = error_info["status_code"]
            if status_code not in self.metrics.errors_by_status_code:
                self.metrics.errors_by_status_code[status_code] = 0
            self.metrics.errors_by_status_code[status_code] += 1
            
            # Add to recent errors (keep last 100)
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "error_code": error_info["error_code"],
                "category": category,
                "severity": error_info["severity"].value,
                "endpoint": endpoint,
                "method": request.method,
                "status_code": status_code,
                "message": str(error)
            }
            
            self.metrics.recent_errors.append(error_record)
            if len(self.metrics.recent_errors) > 100:
                self.metrics.recent_errors = self.metrics.recent_errors[-100:]
            
            # Store in Redis for persistence
            await self._store_error_in_redis(error_record)
            
        except Exception as e:
            logger.error(f"Failed to record error metrics: {e}")
    
    async def _store_error_in_redis(self, error_record: Dict[str, Any]):
        """Store error record in Redis."""
        try:
            error_key = f"error:{datetime.now().strftime('%Y%m%d')}"
            await self.redis.lpush(error_key, str(error_record))
            await self.redis.ltrim(error_key, 0, 999)  # Keep last 1000 errors per day
            await self.redis.expire(error_key, 86400 * 7)  # Keep for 7 days
        except Exception as e:
            logger.warning(f"Failed to store error in Redis: {e}")
    
    async def get_error_metrics(self, days: int = 1) -> Dict[str, Any]:
        """Get error metrics for specified period."""
        try:
            # Get errors from Redis
            all_errors = []
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
                error_key = f"error:{date}"
                errors = await self.redis.lrange(error_key, 0, -1)
                all_errors.extend([eval(error.decode()) for error in errors])
            
            # Calculate metrics
            total_errors = len(all_errors)
            errors_by_category = {}
            errors_by_endpoint = {}
            errors_by_status = {}
            
            for error in all_errors:
                category = error.get("category", "unknown")
                endpoint = error.get("endpoint", "unknown")
                status_code = error.get("status_code", 0)
                
                errors_by_category[category] = errors_by_category.get(category, 0) + 1
                errors_by_endpoint[endpoint] = errors_by_endpoint.get(endpoint, 0) + 1
                errors_by_status[status_code] = errors_by_status.get(status_code, 0) + 1
            
            return {
                "period_days": days,
                "total_errors": total_errors,
                "errors_by_category": errors_by_category,
                "errors_by_endpoint": errors_by_endpoint,
                "errors_by_status_code": errors_by_status,
                "current_metrics": {
                    "total_errors": self.metrics.total_errors,
                    "recent_errors_count": len(self.metrics.recent_errors),
                    "errors_by_category": dict(self.metrics.errors_by_category),
                    "errors_by_endpoint": dict(self.metrics.errors_by_endpoint)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get error metrics: {e}")
            return {"error": "Failed to retrieve metrics"}
    
    async def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for all services."""
        status = {}
        
        for service, breaker in self.circuit_breakers.items():
            status[service] = {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time,
                "failure_threshold": breaker.failure_threshold,
                "recovery_timeout": breaker.recovery_timeout
            }
        
        return status
    
    def get_circuit_breaker(self, service: str) -> CircuitBreakerState:
        """Get or create circuit breaker for service."""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreakerState()
        return self.circuit_breakers[service]
    
    async def add_to_dead_letter_queue(self, operation: Dict[str, Any]):
        """Add failed operation to dead letter queue."""
        operation["failed_at"] = datetime.now().isoformat()
        operation["retry_count"] = operation.get("retry_count", 0) + 1
        
        self.dead_letter_queue.append(operation)
        
        # Keep only last 1000 items
        if len(self.dead_letter_queue) > 1000:
            self.dead_letter_queue = self.dead_letter_queue[-1000:]
        
        logger.warning(f"Operation added to dead letter queue: {operation.get('operation_type')}")
    
    async def retry_operation(self, operation: Dict[str, Any], retry_config: RetryConfig = None) -> bool:
        """Retry failed operation with exponential backoff."""
        if retry_config is None:
            retry_config = RetryConfig()
        
        retry_count = operation.get("retry_count", 0)
        
        if retry_count >= retry_config.max_attempts:
            await self.add_to_dead_letter_queue(operation)
            return False
        
        # Calculate delay with exponential backoff
        delay = min(
            retry_config.base_delay * (retry_config.exponential_base ** retry_count),
            retry_config.max_delay
        )
        
        if retry_config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        await asyncio.sleep(delay)
        
        # This would typically call the actual operation
        # For now, we'll just simulate success/failure
        return True
    
    async def clear_old_errors(self, days: int = 7):
        """Clear old error records from Redis."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for i in range(days, days + 30):  # Check 30 more days back
                date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
                error_key = f"error:{date}"
                await self.redis.delete(error_key)
            
            logger.info(f"Cleared error records older than {days} days")
            
        except Exception as e:
            logger.error(f"Failed to clear old errors: {e}")


# Custom exception classes
class ValidationError(Exception):
    """Validation error."""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.field = field
        self.details = details or {}


class AuthenticationError(Exception):
    """Authentication error."""
    pass


class AuthorizationError(Exception):
    """Authorization error."""
    def __init__(self, message: str, required_permission: str = None):
        super().__init__(message)
        self.required_permission = required_permission


class ResourceNotFoundError(Exception):
    """Resource not found error."""
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


class BusinessLogicError(Exception):
    """Business logic error."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ExternalServiceError(Exception):
    """External service error."""
    def __init__(self, message: str, service: str = None, status_code: int = None):
        super().__init__(message)
        self.service = service
        self.status_code = status_code


class RateLimitError(Exception):
    """Rate limit exceeded error."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class DatabaseError(Exception):
    """Database operation error."""
    pass


class ConfigurationError(Exception):
    """Configuration error."""
    pass


# Global error handler instance
error_handler = ErrorHandler()


# Convenience functions
async def handle_api_error(request: Request, error: Exception) -> JSONResponse:
    """Handle API error using global error handler."""
    return await error_handler.handle_error(request, error)


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    return error_handler