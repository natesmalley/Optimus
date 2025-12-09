"""
Enhanced API Gateway with unified routing, rate limiting, and middleware.
Provides centralized API management with performance monitoring and security.
"""

import time
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Request, Response, HTTPException, Depends
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from redis.asyncio import Redis

from ..config import get_settings, redis_manager, logger


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    requests_per_minute: int
    requests_per_hour: int
    burst_size: int = 10
    key_func: Optional[Callable[[Request], str]] = None


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    request_timeout: int = 30


class CircuitBreakerState:
    """Circuit breaker state management."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
        self.half_open_requests = 0
    
    def can_request(self) -> bool:
        """Check if request can proceed."""
        current_time = time.time()
        
        if self.state == "closed":
            return True
        elif self.state == "open":
            if current_time - self.last_failure_time > self.config.recovery_timeout:
                self.state = "half_open"
                self.half_open_requests = 0
                return True
            return False
        else:  # half_open
            return self.half_open_requests < 3
    
    def on_success(self):
        """Record successful request."""
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)
    
    def on_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "half_open":
            self.state = "open"
        elif self.failure_count >= self.config.failure_threshold:
            self.state = "open"


class RateLimiter:
    """Redis-based rate limiter with sliding window."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.local_cache: Dict[str, deque] = defaultdict(lambda: deque())
        self.cache_ttl = 300  # 5 minutes local cache
    
    async def is_allowed(self, key: str, rule: RateLimitRule) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit."""
        current_time = time.time()
        
        try:
            # Use Redis for distributed rate limiting
            return await self._redis_check(key, rule, current_time)
        except Exception as e:
            logger.warning(f"Redis rate limiting failed, using local fallback: {e}")
            return self._local_check(key, rule, current_time)
    
    async def _redis_check(self, key: str, rule: RateLimitRule, current_time: float) -> tuple[bool, Dict[str, Any]]:
        """Redis-based rate limit check."""
        minute_key = f"rate_limit:{key}:minute:{int(current_time // 60)}"
        hour_key = f"rate_limit:{key}:hour:{int(current_time // 3600)}"
        
        pipe = self.redis.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 120)  # 2 minutes TTL
        pipe.incr(hour_key)
        pipe.expire(hour_key, 7200)  # 2 hours TTL
        pipe.get(minute_key)
        pipe.get(hour_key)
        
        results = await pipe.execute()
        minute_count = int(results[4] or 0)
        hour_count = int(results[5] or 0)
        
        allowed = (
            minute_count <= rule.requests_per_minute and
            hour_count <= rule.requests_per_hour
        )
        
        return allowed, {
            "minute_count": minute_count,
            "hour_count": hour_count,
            "minute_limit": rule.requests_per_minute,
            "hour_limit": rule.requests_per_hour,
            "reset_time": int((current_time // 60 + 1) * 60)
        }
    
    def _local_check(self, key: str, rule: RateLimitRule, current_time: float) -> tuple[bool, Dict[str, Any]]:
        """Local fallback rate limit check."""
        requests = self.local_cache[key]
        
        # Remove old requests
        while requests and requests[0] < current_time - 3600:  # 1 hour window
            requests.popleft()
        
        minute_count = sum(1 for t in requests if t > current_time - 60)
        hour_count = len(requests)
        
        allowed = (
            minute_count < rule.requests_per_minute and
            hour_count < rule.requests_per_hour
        )
        
        if allowed:
            requests.append(current_time)
        
        return allowed, {
            "minute_count": minute_count,
            "hour_count": hour_count,
            "minute_limit": rule.requests_per_minute,
            "hour_limit": rule.requests_per_hour,
            "reset_time": int((current_time // 60 + 1) * 60)
        }


class APIMetrics:
    """API metrics collector."""
    
    def __init__(self):
        self.request_count: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.error_count: Dict[str, int] = defaultdict(int)
        self.active_requests = 0
        self.start_time = time.time()
    
    def record_request(self, path: str, method: str, duration: float, status_code: int):
        """Record request metrics."""
        key = f"{method}:{path}"
        self.request_count[key] += 1
        self.response_times[key].append(duration)
        
        if status_code >= 400:
            self.error_count[key] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics."""
        total_requests = sum(self.request_count.values())
        total_errors = sum(self.error_count.values())
        uptime = time.time() - self.start_time
        
        avg_response_times = {}
        for key, times in self.response_times.items():
            if times:
                avg_response_times[key] = sum(times) / len(times)
        
        return {
            "uptime": uptime,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / total_requests if total_requests > 0 else 0,
            "active_requests": self.active_requests,
            "request_count": dict(self.request_count),
            "error_count": dict(self.error_count),
            "avg_response_times": avg_response_times
        }


class APIGatewayMiddleware(BaseHTTPMiddleware):
    """API Gateway middleware for request processing."""
    
    def __init__(self, app, config: Dict[str, Any]):
        super().__init__(app)
        self.config = config
        self.rate_limiter = RateLimiter(redis_manager.client)
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.metrics = APIMetrics()
        self.rate_limit_rules = self._setup_rate_limits()
        
    def _setup_rate_limits(self) -> Dict[str, RateLimitRule]:
        """Setup rate limiting rules for different endpoints."""
        return {
            "/api/v1/projects": RateLimitRule(
                requests_per_minute=100,
                requests_per_hour=1000
            ),
            "/api/v1/council": RateLimitRule(
                requests_per_minute=30,
                requests_per_hour=300
            ),
            "/api/v1/scanner": RateLimitRule(
                requests_per_minute=20,
                requests_per_hour=100
            ),
            "default": RateLimitRule(
                requests_per_minute=60,
                requests_per_hour=600
            )
        }
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key for request."""
        # Use IP address as default, can be extended with user ID
        client_ip = request.client.host if request.client else "unknown"
        user_id = request.headers.get("X-User-ID", client_ip)
        return f"user:{user_id}"
    
    def _get_circuit_breaker(self, service: str) -> CircuitBreakerState:
        """Get or create circuit breaker for service."""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreakerState(
                CircuitBreakerConfig()
            )
        return self.circuit_breakers[service]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request through middleware pipeline."""
        start_time = time.time()
        self.metrics.active_requests += 1
        
        try:
            # Extract path and method
            path = request.url.path
            method = request.method
            
            # Skip middleware for health checks and static files
            if path in ["/health", "/docs", "/redoc", "/openapi.json"]:
                response = await call_next(request)
                return response
            
            # Rate limiting
            rate_limit_key = self._get_rate_limit_key(request)
            rule = self._get_rate_limit_rule(path)
            
            allowed, rate_info = await self.rate_limiter.is_allowed(rate_limit_key, rule)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "details": rate_info
                    },
                    headers={
                        "X-RateLimit-Limit-Minute": str(rule.requests_per_minute),
                        "X-RateLimit-Limit-Hour": str(rule.requests_per_hour),
                        "X-RateLimit-Remaining-Minute": str(
                            max(0, rule.requests_per_minute - rate_info["minute_count"])
                        ),
                        "X-RateLimit-Reset": str(rate_info["reset_time"])
                    }
                )
            
            # Circuit breaker check
            service = self._extract_service(path)
            circuit_breaker = self._get_circuit_breaker(service)
            
            if not circuit_breaker.can_request():
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Service temporarily unavailable",
                        "service": service,
                        "retry_after": circuit_breaker.config.recovery_timeout
                    }
                )
            
            # Add request context headers
            request.headers.__dict__.setdefault("_list", []).extend([
                (b"x-request-id", str(int(time.time() * 1000)).encode()),
                (b"x-gateway-version", "1.0".encode())
            ])
            
            # Process request
            try:
                response = await asyncio.wait_for(
                    call_next(request),
                    timeout=circuit_breaker.config.request_timeout
                )
                
                # Record success
                circuit_breaker.on_success()
                
                # Add response headers
                response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
                response.headers["X-Gateway-Version"] = "1.0"
                
                return response
                
            except asyncio.TimeoutError:
                circuit_breaker.on_failure()
                return JSONResponse(
                    status_code=504,
                    content={
                        "error": "Gateway timeout",
                        "timeout": circuit_breaker.config.request_timeout
                    }
                )
            except Exception as e:
                circuit_breaker.on_failure()
                logger.error(f"Request processing error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal gateway error"}
                )
        
        finally:
            # Record metrics
            duration = time.time() - start_time
            self.metrics.active_requests -= 1
            
            # This will be recorded after response is created
            asyncio.create_task(
                self._record_metrics(path, method, duration, 200)  # Default status
            )
    
    def _get_rate_limit_rule(self, path: str) -> RateLimitRule:
        """Get rate limit rule for path."""
        for rule_path, rule in self.rate_limit_rules.items():
            if rule_path != "default" and path.startswith(rule_path):
                return rule
        return self.rate_limit_rules["default"]
    
    def _extract_service(self, path: str) -> str:
        """Extract service name from path."""
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "api" and parts[1].startswith("v"):
            return parts[2]
        return "default"
    
    async def _record_metrics(self, path: str, method: str, duration: float, status_code: int):
        """Record request metrics."""
        self.metrics.record_request(path, method, duration, status_code)


class APIVersionManager:
    """API version management."""
    
    def __init__(self):
        self.versions = {
            "v1": {
                "supported": True,
                "deprecated": False,
                "sunset_date": None
            },
            "v2": {
                "supported": True,
                "deprecated": False,
                "sunset_date": None
            }
        }
    
    def get_version_from_request(self, request: Request) -> str:
        """Extract API version from request."""
        # Check header first
        version = request.headers.get("X-API-Version")
        if version:
            return version
        
        # Check path
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "api" and path_parts[1].startswith("v"):
            return path_parts[1]
        
        # Default to v1
        return "v1"
    
    def is_version_supported(self, version: str) -> bool:
        """Check if version is supported."""
        return self.versions.get(version, {}).get("supported", False)


# Global instances
api_metrics = APIMetrics()
version_manager = APIVersionManager()


def get_api_metrics() -> APIMetrics:
    """Get API metrics instance."""
    return api_metrics


def get_version_manager() -> APIVersionManager:
    """Get version manager instance."""
    return version_manager


def create_gateway_middleware(config: Dict[str, Any] = None) -> APIGatewayMiddleware:
    """Create API gateway middleware."""
    if config is None:
        settings = get_settings()
        config = {
            "rate_limiting": True,
            "circuit_breaker": True,
            "metrics": True,
            "debug": settings.debug
        }
    
    return APIGatewayMiddleware(None, config)


# Dependency functions
async def validate_api_version(request: Request):
    """Validate API version dependency."""
    version = version_manager.get_version_from_request(request)
    if not version_manager.is_version_supported(version):
        raise HTTPException(
            status_code=400,
            detail=f"API version {version} is not supported"
        )
    return version


async def get_request_context(request: Request) -> Dict[str, Any]:
    """Get request context information."""
    return {
        "request_id": request.headers.get("X-Request-ID"),
        "user_agent": request.headers.get("User-Agent"),
        "client_ip": request.client.host if request.client else None,
        "api_version": version_manager.get_version_from_request(request),
        "timestamp": time.time()
    }