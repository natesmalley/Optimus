"""
API Monitoring and Analytics System
Provides comprehensive monitoring, metrics collection, and performance analytics.
"""

import time
import asyncio
import psutil
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from redis.asyncio import Redis

from ..config import get_settings, redis_manager, logger


# Prometheus metrics
REQUEST_COUNT = Counter(
    'optimus_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'optimus_api_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'optimus_api_active_requests',
    'Number of active requests'
)

ERROR_RATE = Gauge(
    'optimus_api_error_rate',
    'Current error rate (errors per minute)'
)

RESPONSE_SIZE = Histogram(
    'optimus_api_response_size_bytes',
    'Response size in bytes',
    ['endpoint']
)

# System metrics
CPU_USAGE = Gauge('optimus_system_cpu_usage_percent', 'System CPU usage percentage')
MEMORY_USAGE = Gauge('optimus_system_memory_usage_percent', 'System memory usage percentage')
DISK_USAGE = Gauge('optimus_system_disk_usage_percent', 'System disk usage percentage')


@dataclass
class RequestMetrics:
    """Individual request metrics."""
    method: str
    endpoint: str
    status_code: int
    duration: float
    timestamp: datetime
    response_size: int
    user_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class PerformanceStats:
    """Performance statistics."""
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    requests_per_minute: float = 0.0
    error_rate: float = 0.0
    active_connections: int = 0


@dataclass
class EndpointStats:
    """Endpoint-specific statistics."""
    endpoint: str
    method: str
    total_requests: int = 0
    avg_response_time: float = 0.0
    error_count: int = 0
    last_request: Optional[datetime] = None
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))


class APIMonitoring:
    """Comprehensive API monitoring system."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or redis_manager.client
        self.settings = get_settings()
        
        # Metrics storage
        self.recent_requests: deque = deque(maxlen=10000)  # Last 10k requests
        self.endpoint_stats: Dict[str, EndpointStats] = defaultdict(
            lambda: EndpointStats(endpoint="", method="")
        )
        self.error_tracking: deque = deque(maxlen=1000)  # Last 1k errors
        
        # Performance tracking
        self.active_requests_count = 0
        self.start_time = datetime.now()
        
        # Alerting thresholds
        self.alert_thresholds = {
            "response_time_p95": 2.0,  # 2 seconds
            "error_rate": 0.05,  # 5%
            "requests_per_minute": 1000,  # 1k rpm
            "cpu_usage": 80.0,  # 80%
            "memory_usage": 85.0,  # 85%
        }
        
        # Background monitoring
        self._monitoring_task = None
        
    async def start_monitoring(self):
        """Start background monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("API monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("API monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await self._collect_system_metrics()
                await self._check_alert_conditions()
                await self._cleanup_old_data()
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def record_request(self, request: Request, response: Response, 
                           duration: float, request_id: str = None):
        """Record request metrics."""
        # Extract endpoint info
        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method
        status_code = response.status_code
        response_size = int(response.headers.get("content-length", 0))
        
        # Create metrics record
        metrics = RequestMetrics(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration=duration,
            timestamp=datetime.now(),
            response_size=response_size,
            request_id=request_id
        )
        
        # Store in recent requests
        self.recent_requests.append(metrics)
        
        # Update endpoint stats
        endpoint_key = f"{method}:{endpoint}"
        stats = self.endpoint_stats[endpoint_key]
        stats.endpoint = endpoint
        stats.method = method
        stats.total_requests += 1
        stats.last_request = metrics.timestamp
        stats.response_times.append(duration)
        
        # Calculate running average
        if stats.total_requests == 1:
            stats.avg_response_time = duration
        else:
            stats.avg_response_time = (
                (stats.avg_response_time * (stats.total_requests - 1) + duration) /
                stats.total_requests
            )
        
        # Track errors
        if status_code >= 400:
            stats.error_count += 1
            self.error_tracking.append({
                "timestamp": metrics.timestamp,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration": duration
            })
        
        # Update Prometheus metrics
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if response_size > 0:
            RESPONSE_SIZE.labels(endpoint=endpoint).observe(response_size)
        
        # Store in Redis for persistence
        await self._store_metrics_in_redis(metrics)
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for consistent tracking."""
        # Replace path parameters with placeholders
        import re
        
        # Common patterns to normalize
        patterns = [
            (r'/\d+', '/{id}'),  # Numeric IDs
            (r'/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '/{uuid}'),  # UUIDs
            (r'/[a-f0-9]{32,}', '/{hash}'),  # Long hex strings
        ]
        
        normalized_path = path
        for pattern, replacement in patterns:
            normalized_path = re.sub(pattern, replacement, normalized_path)
        
        return normalized_path
    
    async def _store_metrics_in_redis(self, metrics: RequestMetrics):
        """Store metrics in Redis for persistence."""
        try:
            # Store daily metrics
            date_key = metrics.timestamp.strftime('%Y%m%d')
            metrics_key = f"api_metrics:{date_key}"
            
            metrics_data = {
                "method": metrics.method,
                "endpoint": metrics.endpoint,
                "status_code": metrics.status_code,
                "duration": metrics.duration,
                "timestamp": metrics.timestamp.isoformat(),
                "response_size": metrics.response_size
            }
            
            await self.redis.lpush(metrics_key, str(metrics_data))
            await self.redis.ltrim(metrics_key, 0, 9999)  # Keep last 10k per day
            await self.redis.expire(metrics_key, 86400 * 30)  # Keep for 30 days
            
        except Exception as e:
            logger.warning(f"Failed to store metrics in Redis: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            CPU_USAGE.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            MEMORY_USAGE.set(memory.percent)
            
            # Disk usage (root partition)
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            DISK_USAGE.set(disk_percent)
            
            # Update other metrics
            ACTIVE_REQUESTS.set(self.active_requests_count)
            
            # Calculate error rate
            recent_errors = len([
                e for e in self.error_tracking
                if e["timestamp"] > datetime.now() - timedelta(minutes=1)
            ])
            recent_total = len([
                r for r in self.recent_requests
                if r.timestamp > datetime.now() - timedelta(minutes=1)
            ])
            
            error_rate = recent_errors / recent_total if recent_total > 0 else 0
            ERROR_RATE.set(error_rate)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _check_alert_conditions(self):
        """Check for alert conditions."""
        try:
            current_stats = await self.get_performance_stats()
            alerts = []
            
            # Check response time
            if current_stats.p95_response_time > self.alert_thresholds["response_time_p95"]:
                alerts.append({
                    "type": "high_response_time",
                    "value": current_stats.p95_response_time,
                    "threshold": self.alert_thresholds["response_time_p95"],
                    "severity": "warning"
                })
            
            # Check error rate
            if current_stats.error_rate > self.alert_thresholds["error_rate"]:
                alerts.append({
                    "type": "high_error_rate",
                    "value": current_stats.error_rate,
                    "threshold": self.alert_thresholds["error_rate"],
                    "severity": "critical"
                })
            
            # Check system resources
            cpu_usage = psutil.cpu_percent()
            if cpu_usage > self.alert_thresholds["cpu_usage"]:
                alerts.append({
                    "type": "high_cpu_usage",
                    "value": cpu_usage,
                    "threshold": self.alert_thresholds["cpu_usage"],
                    "severity": "warning"
                })
            
            memory_usage = psutil.virtual_memory().percent
            if memory_usage > self.alert_thresholds["memory_usage"]:
                alerts.append({
                    "type": "high_memory_usage",
                    "value": memory_usage,
                    "threshold": self.alert_thresholds["memory_usage"],
                    "severity": "critical"
                })
            
            # Process alerts
            for alert in alerts:
                await self._process_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
    
    async def _process_alert(self, alert: Dict[str, Any]):
        """Process and potentially send an alert."""
        # Log the alert
        logger.warning(f"Alert triggered: {alert['type']} - "
                      f"Value: {alert['value']}, Threshold: {alert['threshold']}")
        
        # In a real implementation, you would send notifications here
        # (email, Slack, PagerDuty, etc.)
        
        # Store alert in Redis
        try:
            alert_data = {
                **alert,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis.lpush("api_alerts", str(alert_data))
            await self.redis.ltrim("api_alerts", 0, 999)  # Keep last 1000 alerts
            await self.redis.expire("api_alerts", 86400 * 7)  # Keep for 7 days
            
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Clean recent requests
            while (self.recent_requests and 
                   self.recent_requests[0].timestamp < cutoff_time):
                self.recent_requests.popleft()
            
            # Clean error tracking
            while (self.error_tracking and 
                   self.error_tracking[0]["timestamp"] < cutoff_time):
                self.error_tracking.popleft()
            
            # Clean endpoint response times
            for stats in self.endpoint_stats.values():
                # Keep only recent response times (this is approximate)
                if len(stats.response_times) > 100:
                    # Keep last 100 response times
                    new_deque = deque(list(stats.response_times)[-100:], maxlen=1000)
                    stats.response_times = new_deque
                    
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    async def get_performance_stats(self, timeframe_minutes: int = 5) -> PerformanceStats:
        """Get current performance statistics."""
        cutoff_time = datetime.now() - timedelta(minutes=timeframe_minutes)
        
        # Filter recent requests
        recent_requests = [
            r for r in self.recent_requests
            if r.timestamp > cutoff_time
        ]
        
        if not recent_requests:
            return PerformanceStats()
        
        # Calculate response time percentiles
        response_times = sorted([r.duration for r in recent_requests])
        count = len(response_times)
        
        avg_response_time = sum(response_times) / count
        p50_response_time = response_times[int(count * 0.5)]
        p95_response_time = response_times[int(count * 0.95)]
        p99_response_time = response_times[int(count * 0.99)]
        
        # Calculate requests per minute
        requests_per_minute = len(recent_requests) / timeframe_minutes
        
        # Calculate error rate
        error_count = sum(1 for r in recent_requests if r.status_code >= 400)
        error_rate = error_count / len(recent_requests)
        
        return PerformanceStats(
            avg_response_time=avg_response_time,
            p50_response_time=p50_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_minute=requests_per_minute,
            error_rate=error_rate,
            active_connections=self.active_requests_count
        )
    
    async def get_endpoint_analytics(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get analytics for top endpoints."""
        # Sort endpoints by total requests
        sorted_endpoints = sorted(
            self.endpoint_stats.items(),
            key=lambda x: x[1].total_requests,
            reverse=True
        )
        
        analytics = []
        for endpoint_key, stats in sorted_endpoints[:limit]:
            error_rate = stats.error_count / stats.total_requests if stats.total_requests > 0 else 0
            
            # Calculate response time percentiles
            response_times = sorted(list(stats.response_times))
            if response_times:
                p95 = response_times[int(len(response_times) * 0.95)]
                p99 = response_times[int(len(response_times) * 0.99)]
            else:
                p95 = p99 = 0
            
            analytics.append({
                "endpoint": stats.endpoint,
                "method": stats.method,
                "total_requests": stats.total_requests,
                "avg_response_time": stats.avg_response_time,
                "p95_response_time": p95,
                "p99_response_time": p99,
                "error_count": stats.error_count,
                "error_rate": error_rate,
                "last_request": stats.last_request.isoformat() if stats.last_request else None
            })
        
        return analytics
    
    async def get_slow_endpoints(self, min_response_time: float = 1.0) -> List[Dict[str, Any]]:
        """Get endpoints with slow response times."""
        slow_endpoints = []
        
        for endpoint_key, stats in self.endpoint_stats.items():
            if stats.avg_response_time >= min_response_time:
                slow_endpoints.append({
                    "endpoint": stats.endpoint,
                    "method": stats.method,
                    "avg_response_time": stats.avg_response_time,
                    "total_requests": stats.total_requests,
                    "last_request": stats.last_request.isoformat() if stats.last_request else None
                })
        
        # Sort by response time (slowest first)
        slow_endpoints.sort(key=lambda x: x["avg_response_time"], reverse=True)
        return slow_endpoints
    
    async def get_error_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error analytics."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter recent errors
        recent_errors = [
            e for e in self.error_tracking
            if e["timestamp"] > cutoff_time
        ]
        
        if not recent_errors:
            return {"total_errors": 0}
        
        # Group errors by status code
        errors_by_status = defaultdict(int)
        errors_by_endpoint = defaultdict(int)
        errors_by_hour = defaultdict(int)
        
        for error in recent_errors:
            errors_by_status[error["status_code"]] += 1
            errors_by_endpoint[error["endpoint"]] += 1
            
            # Group by hour
            hour_key = error["timestamp"].replace(minute=0, second=0, microsecond=0)
            errors_by_hour[hour_key] += 1
        
        return {
            "total_errors": len(recent_errors),
            "errors_by_status_code": dict(errors_by_status),
            "errors_by_endpoint": dict(errors_by_endpoint),
            "errors_by_hour": {k.isoformat(): v for k, v in errors_by_hour.items()},
            "error_rate": len(recent_errors) / len(self.recent_requests) if self.recent_requests else 0
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            # System resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate uptime
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            # Get performance stats
            perf_stats = await self.get_performance_stats()
            
            # Determine health status
            health_score = 100
            status_issues = []
            
            if cpu_percent > 80:
                health_score -= 20
                status_issues.append("High CPU usage")
            
            if memory.percent > 85:
                health_score -= 20
                status_issues.append("High memory usage")
            
            if perf_stats.p95_response_time > 2.0:
                health_score -= 15
                status_issues.append("Slow response times")
            
            if perf_stats.error_rate > 0.05:
                health_score -= 25
                status_issues.append("High error rate")
            
            # Determine status
            if health_score >= 90:
                status = "healthy"
            elif health_score >= 70:
                status = "degraded"
            elif health_score >= 50:
                status = "unhealthy"
            else:
                status = "critical"
            
            return {
                "status": status,
                "health_score": health_score,
                "issues": status_issues,
                "uptime_seconds": uptime_seconds,
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "active_requests": self.active_requests_count
                },
                "performance": perf_stats.__dict__,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "unknown",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics."""
        return generate_latest()
    
    def increment_active_requests(self):
        """Increment active request counter."""
        self.active_requests_count += 1
        ACTIVE_REQUESTS.set(self.active_requests_count)
    
    def decrement_active_requests(self):
        """Decrement active request counter."""
        self.active_requests_count = max(0, self.active_requests_count - 1)
        ACTIVE_REQUESTS.set(self.active_requests_count)
    
    async def update_alert_thresholds(self, thresholds: Dict[str, float]):
        """Update alert thresholds."""
        self.alert_thresholds.update(thresholds)
        logger.info(f"Updated alert thresholds: {thresholds}")


# Global monitoring instance
api_monitoring = APIMonitoring()


# Convenience functions
async def record_api_request(request: Request, response: Response, 
                           duration: float, request_id: str = None):
    """Record API request metrics."""
    await api_monitoring.record_request(request, response, duration, request_id)


def increment_active_requests():
    """Increment active request counter."""
    api_monitoring.increment_active_requests()


def decrement_active_requests():
    """Decrement active request counter."""
    api_monitoring.decrement_active_requests()


def get_monitoring() -> APIMonitoring:
    """Get global monitoring instance."""
    return api_monitoring