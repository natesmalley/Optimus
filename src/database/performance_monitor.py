"""
Database Performance Monitoring System

Comprehensive performance monitoring, alerting, and optimization
recommendations for all database systems in Optimus.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import logging
from collections import defaultdict, deque
import psutil

from .config import get_database_manager, DatabaseManager
from .postgres_optimized import get_postgres_optimizer
from .redis_cache import get_cache_manager


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class MetricType(Enum):
    """Types of performance metrics"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    CONNECTION_POOL = "connection_pool"
    QUERY_PERFORMANCE = "query_performance"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"


@dataclass
class PerformanceMetric:
    """Single performance metric data point"""
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    database: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    metric_type: MetricType
    current_value: float
    threshold: float
    database: str
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class MonitorConfig:
    """Monitoring configuration"""
    enabled: bool = True
    collection_interval: int = 30  # seconds
    retention_period: int = 7200   # 2 hours in minutes
    alert_thresholds: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default alert thresholds"""
        if not self.alert_thresholds:
            self.alert_thresholds = {
                'postgres': {
                    'response_time_ms': 5000,     # 5 seconds
                    'cpu_usage_percent': 80,      # 80%
                    'memory_usage_percent': 85,   # 85%
                    'connection_usage_percent': 90, # 90%
                    'cache_hit_ratio_min': 0.85,  # 85%
                    'disk_usage_percent': 90      # 90%
                },
                'redis': {
                    'response_time_ms': 100,      # 100ms
                    'memory_usage_mb': 1000,      # 1GB
                    'eviction_rate': 1000,        # keys per minute
                    'connection_usage_percent': 80
                },
                'sqlite': {
                    'response_time_ms': 1000,     # 1 second
                    'lock_wait_time_ms': 5000,    # 5 seconds
                    'file_size_mb': 5000,         # 5GB
                    'fragmentation_percent': 30   # 30%
                }
            }


class DatabaseMonitor:
    """Individual database monitor"""
    
    def __init__(self, database_name: str, db_manager: DatabaseManager):
        self.database_name = database_name
        self.db_manager = db_manager
        self.metrics_history: Dict[MetricType, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.query_stats: Dict[str, List[float]] = defaultdict(list)
        self.logger = logging.getLogger(f"monitor.{database_name}")
    
    async def collect_metrics(self) -> List[PerformanceMetric]:
        """Collect performance metrics for this database"""
        metrics = []
        
        if self.database_name == "postgres":
            metrics.extend(await self._collect_postgres_metrics())
        elif self.database_name == "redis":
            metrics.extend(await self._collect_redis_metrics())
        elif self.database_name in ["memory", "knowledge"]:
            metrics.extend(await self._collect_sqlite_metrics())
        
        # Store metrics in history
        for metric in metrics:
            self.metrics_history[metric.metric_type].append(metric)
        
        return metrics
    
    async def _collect_postgres_metrics(self) -> List[PerformanceMetric]:
        """Collect PostgreSQL-specific metrics"""
        metrics = []
        timestamp = datetime.now()
        
        try:
            optimizer = get_postgres_optimizer()
            
            # Database statistics
            db_stats = await optimizer.get_database_statistics()
            
            # Connection statistics
            for conn_stat in db_stats.get('connection_stats', []):
                metrics.append(PerformanceMetric(
                    metric_type=MetricType.CONNECTION_POOL,
                    value=conn_stat['connection_count'],
                    unit="connections",
                    timestamp=timestamp,
                    database="postgres",
                    context={'state': conn_stat['state']}
                ))
            
            # Cache hit ratios
            for cache_stat in db_stats.get('cache_stats', []):
                if cache_stat['hit_ratio']:
                    metrics.append(PerformanceMetric(
                        metric_type=MetricType.CACHE_HIT_RATIO,
                        value=cache_stat['hit_ratio'],
                        unit="percent",
                        timestamp=timestamp,
                        database="postgres",
                        context={'cache_type': cache_stat['cache_type']}
                    ))
            
            # Table sizes and performance
            for table_stat in db_stats.get('table_stats', [])[:10]:  # Top 10 tables
                metrics.append(PerformanceMetric(
                    metric_type=MetricType.MEMORY_USAGE,
                    value=table_stat['size_bytes'],
                    unit="bytes",
                    timestamp=timestamp,
                    database="postgres",
                    context={'table': table_stat['tablename'], 'type': 'table_size'}
                ))
            
            # Query performance (slow queries)
            slow_queries = await optimizer.analyze_slow_queries()
            for query in slow_queries[:5]:  # Top 5 slow queries
                metrics.append(PerformanceMetric(
                    metric_type=MetricType.QUERY_PERFORMANCE,
                    value=query['mean_exec_time'],
                    unit="milliseconds",
                    timestamp=timestamp,
                    database="postgres",
                    context={'query_hash': hash(query['query'][:100])}
                ))
            
        except Exception as e:
            self.logger.error(f"Error collecting PostgreSQL metrics: {e}")
        
        return metrics
    
    async def _collect_redis_metrics(self) -> List[PerformanceMetric]:
        """Collect Redis-specific metrics"""
        metrics = []
        timestamp = datetime.now()
        
        try:
            cache_manager = get_cache_manager()
            cache_info = await cache_manager.get_comprehensive_stats()
            
            # Cache performance metrics
            stats = cache_info.get('stats', {})
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.CACHE_HIT_RATIO,
                value=stats.get('hit_ratio', 0) * 100,
                unit="percent",
                timestamp=timestamp,
                database="redis"
            ))
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.RESPONSE_TIME,
                value=stats.get('avg_response_time_ms', 0),
                unit="milliseconds",
                timestamp=timestamp,
                database="redis"
            ))
            
            # Redis server metrics
            redis_info = cache_info.get('redis_info', {})
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.MEMORY_USAGE,
                value=redis_info.get('used_memory', 0),
                unit="bytes",
                timestamp=timestamp,
                database="redis"
            ))
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.CONNECTION_POOL,
                value=redis_info.get('connected_clients', 0),
                unit="connections",
                timestamp=timestamp,
                database="redis"
            ))
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.THROUGHPUT,
                value=redis_info.get('total_commands_processed', 0),
                unit="commands",
                timestamp=timestamp,
                database="redis"
            ))
            
        except Exception as e:
            self.logger.error(f"Error collecting Redis metrics: {e}")
        
        return metrics
    
    async def _collect_sqlite_metrics(self) -> List[PerformanceMetric]:
        """Collect SQLite-specific metrics"""
        metrics = []
        timestamp = datetime.now()
        
        try:
            if self.database_name == "memory":
                conn = self.db_manager.get_memory_connection()
            else:  # knowledge
                conn = self.db_manager.get_knowledge_connection()
            
            cursor = conn.cursor()
            
            # Database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size = page_count * page_size
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.MEMORY_USAGE,
                value=db_size,
                unit="bytes",
                timestamp=timestamp,
                database=self.database_name,
                context={'type': 'database_size'}
            ))
            
            # Fragmentation
            cursor.execute("PRAGMA freelist_count")
            free_pages = cursor.fetchone()[0]
            fragmentation = (free_pages / max(page_count, 1)) * 100
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.DISK_IO,
                value=fragmentation,
                unit="percent",
                timestamp=timestamp,
                database=self.database_name,
                context={'type': 'fragmentation'}
            ))
            
            # Cache statistics
            cursor.execute("PRAGMA cache_size")
            cache_size = cursor.fetchone()[0]
            
            metrics.append(PerformanceMetric(
                metric_type=MetricType.CACHE_HIT_RATIO,
                value=abs(cache_size),  # SQLite returns negative values for KB
                unit="pages",
                timestamp=timestamp,
                database=self.database_name,
                context={'type': 'cache_size'}
            ))
            
            if self.database_name == "memory":
                self.db_manager.return_memory_connection(conn)
            else:
                self.db_manager.return_knowledge_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error collecting SQLite metrics for {self.database_name}: {e}")
        
        return metrics
    
    def get_metric_trend(self, metric_type: MetricType, minutes: int = 30) -> Optional[float]:
        """Get trend for a specific metric (positive = increasing, negative = decreasing)"""
        if metric_type not in self.metrics_history:
            return None
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics_history[metric_type]
            if m.timestamp >= cutoff_time
        ]
        
        if len(recent_metrics) < 2:
            return None
        
        # Calculate simple linear trend
        values = [m.value for m in recent_metrics]
        x_values = list(range(len(values)))
        
        if len(values) > 1:
            # Simple linear regression slope
            n = len(values)
            sum_x = sum(x_values)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(x_values, values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            return slope
        
        return None
    
    def get_metric_statistics(self, metric_type: MetricType, minutes: int = 60) -> Dict[str, float]:
        """Get statistical summary of a metric over time"""
        if metric_type not in self.metrics_history:
            return {}
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_values = [
            m.value for m in self.metrics_history[metric_type]
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_values:
            return {}
        
        return {
            'mean': statistics.mean(recent_values),
            'median': statistics.median(recent_values),
            'std_dev': statistics.stdev(recent_values) if len(recent_values) > 1 else 0,
            'min': min(recent_values),
            'max': max(recent_values),
            'count': len(recent_values)
        }


class PerformanceMonitor:
    """
    Comprehensive database performance monitoring system with:
    - Multi-database monitoring
    - Real-time alerting
    - Trend analysis
    - Performance recommendations
    - Automated optimization triggers
    """
    
    def __init__(self, config: Optional[MonitorConfig] = None, db_manager: Optional[DatabaseManager] = None):
        self.config = config or MonitorConfig()
        self.db_manager = db_manager or get_database_manager()
        
        # Initialize database monitors
        self.monitors = {
            'postgres': DatabaseMonitor('postgres', self.db_manager),
            'redis': DatabaseMonitor('redis', self.db_manager),
            'memory': DatabaseMonitor('memory', self.db_manager),
            'knowledge': DatabaseMonitor('knowledge', self.db_manager)
        }
        
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Performance tracking
        self.system_metrics: deque = deque(maxlen=1000)
        self.recommendations: List[Dict[str, Any]] = []
        
        self.logger = logging.getLogger("performance_monitor")
        self.monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self):
        """Start continuous performance monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.logger.warning("Monitoring already running")
            return
        
        self.logger.info("Starting performance monitoring")
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                # Collect metrics from all databases
                await self._collect_all_metrics()
                
                # Analyze metrics and generate alerts
                await self._analyze_performance()
                
                # Generate recommendations
                await self._generate_recommendations()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(self.config.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.config.collection_interval)
    
    async def _collect_all_metrics(self):
        """Collect metrics from all database monitors"""
        all_metrics = []
        
        for db_name, monitor in self.monitors.items():
            try:
                metrics = await monitor.collect_metrics()
                all_metrics.extend(metrics)
            except Exception as e:
                self.logger.error(f"Error collecting metrics from {db_name}: {e}")
        
        # Collect system-level metrics
        system_metrics = await self._collect_system_metrics()
        all_metrics.extend(system_metrics)
        
        self.logger.debug(f"Collected {len(all_metrics)} metrics")
    
    async def _collect_system_metrics(self) -> List[PerformanceMetric]:
        """Collect system-level performance metrics"""
        metrics = []
        timestamp = datetime.now()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(PerformanceMetric(
                metric_type=MetricType.RESOURCE_USAGE,
                value=cpu_percent,
                unit="percent",
                timestamp=timestamp,
                database="system",
                context={'resource': 'cpu'}
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.append(PerformanceMetric(
                metric_type=MetricType.RESOURCE_USAGE,
                value=memory.percent,
                unit="percent",
                timestamp=timestamp,
                database="system",
                context={'resource': 'memory'}
            ))
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics.append(PerformanceMetric(
                    metric_type=MetricType.DISK_IO,
                    value=disk_io.read_bytes + disk_io.write_bytes,
                    unit="bytes",
                    timestamp=timestamp,
                    database="system",
                    context={'type': 'total_io'}
                ))
            
            # Network I/O
            net_io = psutil.net_io_counters()
            if net_io:
                metrics.append(PerformanceMetric(
                    metric_type=MetricType.NETWORK_IO,
                    value=net_io.bytes_sent + net_io.bytes_recv,
                    unit="bytes",
                    timestamp=timestamp,
                    database="system",
                    context={'type': 'total_network'}
                ))
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
        
        return metrics
    
    async def _analyze_performance(self):
        """Analyze metrics and generate alerts"""
        for db_name, monitor in self.monitors.items():
            thresholds = self.config.alert_thresholds.get(db_name, {})
            
            # Check each metric type against thresholds
            for metric_type in MetricType:
                stats = monitor.get_metric_statistics(metric_type, minutes=10)
                
                if not stats:
                    continue
                
                current_value = stats['mean']
                alert_generated = False
                
                # Check various threshold conditions
                for threshold_key, threshold_value in thresholds.items():
                    if self._should_alert(metric_type, current_value, threshold_key, threshold_value):
                        alert = self._create_alert(
                            db_name, metric_type, current_value, threshold_value, threshold_key
                        )
                        await self._handle_alert(alert)
                        alert_generated = True
                
                # Check for positive trends in error metrics
                trend = monitor.get_metric_trend(metric_type, minutes=15)
                if trend and trend > 0.1:  # Significant positive trend
                    if metric_type in [MetricType.ERROR_RATE, MetricType.RESPONSE_TIME]:
                        alert = Alert(
                            alert_id=f"trend_{db_name}_{metric_type.value}_{int(time.time())}",
                            level=AlertLevel.WARNING,
                            title=f"Increasing {metric_type.value} trend in {db_name}",
                            description=f"Detected increasing trend in {metric_type.value} over the last 15 minutes",
                            metric_type=metric_type,
                            current_value=current_value,
                            threshold=0,
                            database=db_name,
                            timestamp=datetime.now()
                        )
                        await self._handle_alert(alert)
    
    def _should_alert(self, metric_type: MetricType, current_value: float, threshold_key: str, threshold_value: float) -> bool:
        """Determine if an alert should be generated"""
        if metric_type == MetricType.RESPONSE_TIME and threshold_key == 'response_time_ms':
            return current_value > threshold_value
        elif metric_type == MetricType.RESOURCE_USAGE and 'cpu_usage_percent' in threshold_key:
            return current_value > threshold_value
        elif metric_type == MetricType.RESOURCE_USAGE and 'memory_usage_percent' in threshold_key:
            return current_value > threshold_value
        elif metric_type == MetricType.CACHE_HIT_RATIO and threshold_key == 'cache_hit_ratio_min':
            return current_value < threshold_value
        elif metric_type == MetricType.CONNECTION_POOL and 'connection_usage_percent' in threshold_key:
            return current_value > threshold_value
        
        return False
    
    def _create_alert(self, database: str, metric_type: MetricType, current_value: float, 
                     threshold_value: float, threshold_key: str) -> Alert:
        """Create a performance alert"""
        alert_level = AlertLevel.WARNING
        
        # Determine alert level based on how much threshold is exceeded
        if metric_type == MetricType.RESPONSE_TIME:
            if current_value > threshold_value * 2:
                alert_level = AlertLevel.CRITICAL
            elif current_value > threshold_value * 1.5:
                alert_level = AlertLevel.ERROR
        elif metric_type == MetricType.RESOURCE_USAGE:
            if current_value > 95:
                alert_level = AlertLevel.CRITICAL
            elif current_value > 90:
                alert_level = AlertLevel.ERROR
        
        return Alert(
            alert_id=f"threshold_{database}_{metric_type.value}_{int(time.time())}",
            level=alert_level,
            title=f"{database} {metric_type.value} threshold exceeded",
            description=f"{metric_type.value} is {current_value:.2f}, exceeding threshold of {threshold_value}",
            metric_type=metric_type,
            current_value=current_value,
            threshold=threshold_value,
            database=database,
            timestamp=datetime.now()
        )
    
    async def _handle_alert(self, alert: Alert):
        """Handle a generated alert"""
        # Check if similar alert is already active
        existing_alert_id = None
        for alert_id, existing_alert in self.active_alerts.items():
            if (existing_alert.database == alert.database and 
                existing_alert.metric_type == alert.metric_type and
                not existing_alert.resolved):
                existing_alert_id = alert_id
                break
        
        if existing_alert_id:
            # Update existing alert
            self.active_alerts[existing_alert_id] = alert
            self.logger.info(f"Updated existing alert: {alert.title}")
        else:
            # New alert
            self.active_alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            self.logger.warning(f"New alert: {alert.title}")
            
            # Trigger automated responses for critical alerts
            if alert.level == AlertLevel.CRITICAL:
                await self._handle_critical_alert(alert)
    
    async def _handle_critical_alert(self, alert: Alert):
        """Handle critical alerts with automated responses"""
        if alert.database == "postgres" and alert.metric_type == MetricType.CONNECTION_POOL:
            # Auto-scale connection pool if possible
            self.logger.warning("Critical PostgreSQL connection pool usage - consider scaling")
        
        elif alert.database == "redis" and alert.metric_type == MetricType.MEMORY_USAGE:
            # Trigger cache cleanup
            try:
                cache_manager = get_cache_manager()
                await cache_manager.cache.invalidate_pattern("temp:*")
                self.logger.info("Triggered cache cleanup due to high Redis memory usage")
            except Exception as e:
                self.logger.error(f"Failed to cleanup cache: {e}")
    
    async def _generate_recommendations(self):
        """Generate performance optimization recommendations"""
        new_recommendations = []
        
        for db_name, monitor in self.monitors.items():
            # Analyze recent metrics for optimization opportunities
            
            # High response time recommendation
            response_stats = monitor.get_metric_statistics(MetricType.RESPONSE_TIME, minutes=30)
            if response_stats and response_stats['mean'] > 1000:  # > 1 second
                new_recommendations.append({
                    'database': db_name,
                    'type': 'performance',
                    'priority': 'high',
                    'title': f'High response time in {db_name}',
                    'description': f'Average response time is {response_stats["mean"]:.2f}ms',
                    'recommendations': [
                        'Review slow queries and add appropriate indexes',
                        'Consider increasing connection pool size',
                        'Check for resource contention'
                    ],
                    'timestamp': datetime.now()
                })
            
            # Low cache hit ratio recommendation
            cache_stats = monitor.get_metric_statistics(MetricType.CACHE_HIT_RATIO, minutes=30)
            if cache_stats and cache_stats['mean'] < 0.8:  # < 80%
                new_recommendations.append({
                    'database': db_name,
                    'type': 'caching',
                    'priority': 'medium',
                    'title': f'Low cache hit ratio in {db_name}',
                    'description': f'Cache hit ratio is {cache_stats["mean"]*100:.1f}%',
                    'recommendations': [
                        'Increase cache size if memory allows',
                        'Review cache configuration and TTL settings',
                        'Analyze query patterns for optimization'
                    ],
                    'timestamp': datetime.now()
                })
        
        # Add new recommendations
        self.recommendations.extend(new_recommendations)
        
        # Keep only recent recommendations
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.recommendations = [
            rec for rec in self.recommendations 
            if rec['timestamp'] > cutoff_time
        ]
    
    async def _cleanup_old_data(self):
        """Clean up old metrics and alerts"""
        cutoff_time = datetime.now() - timedelta(minutes=self.config.retention_period)
        
        # Clean up metric history
        for monitor in self.monitors.values():
            for metric_type in monitor.metrics_history:
                metrics = monitor.metrics_history[metric_type]
                while metrics and metrics[0].timestamp < cutoff_time:
                    metrics.popleft()
        
        # Resolve old alerts
        for alert_id, alert in list(self.active_alerts.items()):
            if alert.timestamp < cutoff_time:
                alert.resolved = True
                alert.resolution_time = datetime.now()
                del self.active_alerts[alert_id]
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        dashboard = {
            'summary': {
                'active_alerts': len(self.active_alerts),
                'critical_alerts': len([a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL]),
                'databases_monitored': len(self.monitors),
                'recommendations': len(self.recommendations)
            },
            'alerts': [alert.__dict__ for alert in self.active_alerts.values()],
            'recommendations': self.recommendations,
            'metrics': {}
        }
        
        # Get current metrics for each database
        for db_name, monitor in self.monitors.items():
            db_metrics = {}
            for metric_type in MetricType:
                stats = monitor.get_metric_statistics(metric_type, minutes=10)
                if stats:
                    trend = monitor.get_metric_trend(metric_type, minutes=30)
                    db_metrics[metric_type.value] = {
                        'current': stats['mean'],
                        'trend': trend,
                        'min': stats['min'],
                        'max': stats['max'],
                        'std_dev': stats['std_dev']
                    }
            dashboard['metrics'][db_name] = db_metrics
        
        return dashboard
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall database health status"""
        health = {
            'overall_status': 'healthy',
            'databases': {},
            'issues': [],
            'uptime_check': datetime.now().isoformat()
        }
        
        has_critical_issues = False
        has_warnings = False
        
        for db_name, monitor in self.monitors.items():
            db_health = {
                'status': 'healthy',
                'response_time': None,
                'resource_usage': None,
                'cache_performance': None,
                'issues': []
            }
            
            # Check response time
            response_stats = monitor.get_metric_statistics(MetricType.RESPONSE_TIME, minutes=5)
            if response_stats:
                db_health['response_time'] = response_stats['mean']
                if response_stats['mean'] > 5000:  # 5 seconds
                    db_health['status'] = 'critical'
                    db_health['issues'].append('High response time')
                    has_critical_issues = True
                elif response_stats['mean'] > 2000:  # 2 seconds
                    db_health['status'] = 'warning'
                    db_health['issues'].append('Elevated response time')
                    has_warnings = True
            
            # Check cache performance
            cache_stats = monitor.get_metric_statistics(MetricType.CACHE_HIT_RATIO, minutes=5)
            if cache_stats:
                db_health['cache_performance'] = cache_stats['mean'] * 100
                if cache_stats['mean'] < 0.7:  # 70%
                    if db_health['status'] != 'critical':
                        db_health['status'] = 'warning'
                    db_health['issues'].append('Low cache hit ratio')
                    has_warnings = True
            
            health['databases'][db_name] = db_health
        
        # Set overall status
        if has_critical_issues:
            health['overall_status'] = 'critical'
        elif has_warnings:
            health['overall_status'] = 'warning'
        
        # Add system-wide issues
        if len(self.active_alerts) > 10:
            health['issues'].append('High number of active alerts')
        
        return health


# Global monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


async def start_performance_monitoring():
    """Start the global performance monitoring"""
    monitor = get_performance_monitor()
    await monitor.start_monitoring()


async def stop_performance_monitoring():
    """Stop the global performance monitoring"""
    global _performance_monitor
    if _performance_monitor:
        await _performance_monitor.stop_monitoring()
        _performance_monitor = None