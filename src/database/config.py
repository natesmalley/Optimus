"""
Unified Database Configuration

Centralized database configuration and connection management
for all database systems used in Optimus Council of Minds.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
import sqlite3
import threading
from queue import Queue, Empty


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    
    # PostgreSQL settings
    postgres_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/optimus_db"
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 30
    postgres_pool_timeout: int = 30
    postgres_pool_recycle: int = 3600
    
    # SQLite settings for Memory and Knowledge Graph
    memory_db_path: str = "data/memory/optimus_memory.db"
    knowledge_db_path: str = "data/knowledge/optimus_knowledge.db"
    sqlite_pool_size: int = 10
    sqlite_timeout: int = 30
    
    # Redis settings for caching
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    
    # Performance settings
    enable_query_logging: bool = False
    enable_metrics_collection: bool = True
    cache_ttl: int = 300  # 5 minutes default
    
    # Connection retry settings
    max_retries: int = 3
    retry_delay: int = 1
    
    def __post_init__(self):
        """Initialize paths and validate configuration"""
        # Create data directories
        Path(self.memory_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.knowledge_db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Load from environment if available
        self.postgres_url = os.getenv("DATABASE_URL", self.postgres_url)
        self.redis_url = os.getenv("REDIS_URL", self.redis_url)


class SQLiteConnectionPool:
    """
    SQLite connection pool for thread-safe database operations.
    Addresses SQLite's threading limitations while providing connection reuse.
    """
    
    def __init__(self, db_path: str, pool_size: int = 10, timeout: int = 30):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created_connections = 0
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        for _ in range(self.pool_size):
            self._create_connection()
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with optimized settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            isolation_level=None,  # autocommit mode
            check_same_thread=False
        )
        
        # Optimize SQLite settings for performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB
        conn.execute("PRAGMA optimize")
        
        self._created_connections += 1
        self._pool.put(conn)
        return conn
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool"""
        try:
            return self._pool.get(timeout=self.timeout)
        except Empty:
            # Pool exhausted, create new connection if under limit
            with self._lock:
                if self._created_connections < self.pool_size * 2:
                    return self._create_connection()
                else:
                    raise RuntimeError("Connection pool exhausted")
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool"""
        if conn:
            try:
                self._pool.put(conn, block=False)
            except:
                # Pool full, close connection
                conn.close()
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


class DatabaseManager:
    """
    Unified database manager for all database operations.
    Provides connection pooling, caching, and performance optimization.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._postgres_engine = None
        self._postgres_session_maker = None
        self._redis_pool = None
        self._memory_pool = None
        self._knowledge_pool = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all database connections and pools"""
        if self._initialized:
            return
        
        # Initialize PostgreSQL async engine  
        self._postgres_engine = create_async_engine(
            self.config.postgres_url,
            pool_size=self.config.postgres_pool_size,
            max_overflow=self.config.postgres_max_overflow,
            pool_timeout=self.config.postgres_pool_timeout,
            pool_recycle=self.config.postgres_pool_recycle,
            echo=self.config.enable_query_logging,
            future=True
        )
        
        self._postgres_session_maker = async_sessionmaker(
            bind=self._postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Initialize Redis connection pool
        self._redis_pool = redis.ConnectionPool.from_url(
            self.config.redis_url,
            max_connections=self.config.redis_max_connections,
            socket_timeout=self.config.redis_socket_timeout,
            socket_connect_timeout=self.config.redis_socket_connect_timeout,
            retry_on_timeout=True
        )
        
        # Initialize SQLite connection pools
        self._memory_pool = SQLiteConnectionPool(
            self.config.memory_db_path,
            self.config.sqlite_pool_size,
            self.config.sqlite_timeout
        )
        
        self._knowledge_pool = SQLiteConnectionPool(
            self.config.knowledge_db_path,
            self.config.sqlite_pool_size,
            self.config.sqlite_timeout
        )
        
        self._initialized = True
    
    async def get_postgres_session(self) -> AsyncSession:
        """Get a PostgreSQL async session"""
        if not self._initialized:
            await self.initialize()
        return self._postgres_session_maker()
    
    async def get_redis_client(self) -> redis.Redis:
        """Get a Redis async client"""
        if not self._initialized:
            await self.initialize()
        return redis.Redis(connection_pool=self._redis_pool)
    
    def get_memory_connection(self) -> sqlite3.Connection:
        """Get a Memory System SQLite connection"""
        if not self._initialized:
            # Initialize sync for SQLite
            self._memory_pool = SQLiteConnectionPool(
                self.config.memory_db_path,
                self.config.sqlite_pool_size,
                self.config.sqlite_timeout
            )
        return self._memory_pool.get_connection()
    
    def return_memory_connection(self, conn: sqlite3.Connection):
        """Return a Memory System SQLite connection"""
        self._memory_pool.return_connection(conn)
    
    def get_knowledge_connection(self) -> sqlite3.Connection:
        """Get a Knowledge Graph SQLite connection"""
        if not self._initialized:
            # Initialize sync for SQLite
            self._knowledge_pool = SQLiteConnectionPool(
                self.config.knowledge_db_path,
                self.config.sqlite_pool_size,
                self.config.sqlite_timeout
            )
        return self._knowledge_pool.get_connection()
    
    def return_knowledge_connection(self, conn: sqlite3.Connection):
        """Return a Knowledge Graph SQLite connection"""
        self._knowledge_pool.return_connection(conn)
    
    async def close(self):
        """Close all database connections"""
        if self._postgres_engine:
            await self._postgres_engine.dispose()
        
        if self._redis_pool:
            await self._redis_pool.disconnect()
        
        if self._memory_pool:
            self._memory_pool.close_all()
        
        if self._knowledge_pool:
            self._knowledge_pool.close_all()
        
        self._initialized = False
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all database connections"""
        health = {
            "postgres": False,
            "redis": False,
            "memory_db": False,
            "knowledge_db": False
        }
        
        # Check PostgreSQL
        try:
            async with self.get_postgres_session() as session:
                await session.execute("SELECT 1")
            health["postgres"] = True
        except Exception:
            pass
        
        # Check Redis
        try:
            redis_client = await self.get_redis_client()
            await redis_client.ping()
            await redis_client.close()
            health["redis"] = True
        except Exception:
            pass
        
        # Check Memory DB
        try:
            conn = self.get_memory_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            self.return_memory_connection(conn)
            health["memory_db"] = True
        except Exception:
            pass
        
        # Check Knowledge DB
        try:
            conn = self.get_knowledge_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            self.return_knowledge_connection(conn)
            health["knowledge_db"] = True
        except Exception:
            pass
        
        return health


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def initialize_databases():
    """Initialize all database connections"""
    db_manager = get_database_manager()
    await db_manager.initialize()


async def close_databases():
    """Close all database connections"""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None