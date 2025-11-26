"""
Configuration management for Optimus backend.
Handles environment variables, database connections, and application settings.
"""

import logging
import os
from functools import lru_cache
from typing import Optional

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings
import redis.asyncio as redis


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    app_name: str = "Optimus Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # API settings
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Database settings
    database_url: Optional[PostgresDsn] = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "optimus_db"
    database_user: str = "postgres"
    database_password: str = "password"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis settings
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # Scanning settings
    projects_base_path: str = os.path.expanduser("~/projects")
    scan_interval: int = 300  # 5 minutes
    max_scan_depth: int = 3
    excluded_directories: list[str] = [
        ".git", "__pycache__", "node_modules", ".venv", "venv", 
        ".pytest_cache", ".mypy_cache", "dist", "build"
    ]
    
    # Monitoring settings
    monitor_interval: int = 30  # 30 seconds
    process_timeout: int = 120  # 2 minutes
    heartbeat_threshold: int = 180  # 3 minutes
    
    # Logging settings
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = "optimus.log"
    
    @field_validator("database_url", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        """Assemble database URL from individual components if not provided."""
        if isinstance(v, str):
            # If it starts with postgresql://, convert it to async
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://")
            return v
        values = info.data if info else {}
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=values.get("database_user"),
            password=values.get("database_password"),
            host=values.get("database_host"),
            port=str(values.get("database_port")),
            path=f"/{values.get('database_name') or ''}",
        )
    
    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self.session_factory = None
    
    async def initialize(self):
        """Initialize database engine and session factory."""
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        
        self.engine = create_async_engine(
            str(self.settings.database_url),
            pool_size=self.settings.database_pool_size,
            max_overflow=self.settings.database_max_overflow,
            echo=self.settings.debug,
            future=True,
        )
        
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    
    async def get_session(self):
        """Get database session."""
        if not self.session_factory:
            await self.initialize()
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()


class RedisManager:
    """Redis connection and operations management."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_pool = None
    
    async def initialize(self):
        """Initialize Redis connection pool."""
        self.redis_pool = redis.ConnectionPool.from_url(
            self.settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
    
    async def get_client(self) -> redis.Redis:
        """Get Redis client."""
        if not self.redis_pool:
            await self.initialize()
        return redis.Redis(connection_pool=self.redis_pool)
    
    async def close(self):
        """Close Redis connections."""
        if self.redis_pool:
            await self.redis_pool.disconnect()


def setup_logging(settings: Settings) -> logging.Logger:
    """Set up application logging configuration."""
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler(),
        ]
    )
    
    # Configure specific loggers
    logger = logging.getLogger("optimus")
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Reduce noise from external libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return logger


# Global instances
settings = get_settings()
db_manager = DatabaseManager(settings)
redis_manager = RedisManager(settings)
logger = setup_logging(settings)