"""
Database configuration for Optimus project orchestrator.

This module provides database connection settings and utilities for the Optimus platform.
Supports both development and production configurations.
"""

import os
from typing import Dict, Any
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

# Database configuration class
class DatabaseConfig:
    """Database configuration management for Optimus."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self._load_config()
    
    def _load_config(self):
        """Load database configuration based on environment."""
        if self.environment == "development":
            self.config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME", "optimus_db"),
                "username": os.getenv("DB_USER", "optimus_user"),
                "password": os.getenv("DB_PASSWORD", "optimus_dev_password"),
                "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                "echo": os.getenv("DB_ECHO", "false").lower() == "true",
            }
        elif self.environment == "production":
            self.config = {
                "host": os.getenv("DB_HOST"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME"),
                "username": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD"),
                "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "50")),
                "echo": False,
                "ssl_mode": os.getenv("DB_SSL_MODE", "require"),
            }
        else:
            raise ValueError(f"Unsupported environment: {self.environment}")
    
    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        password = quote_plus(self.config["password"])
        base_url = (
            f"postgresql://{self.config['username']}:{password}@"
            f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )
        
        if self.environment == "production" and "ssl_mode" in self.config:
            base_url += f"?sslmode={self.config['ssl_mode']}"
        
        return base_url
    
    @property
    def engine_kwargs(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration."""
        return {
            "pool_size": self.config["pool_size"],
            "max_overflow": self.config["max_overflow"],
            "echo": self.config["echo"],
            "pool_pre_ping": True,  # Verify connections before use
            "pool_recycle": 3600,   # Recycle connections after 1 hour
        }

# Global database setup
Base = declarative_base()

def create_database_engine(environment: str = None):
    """Create SQLAlchemy engine with proper configuration."""
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    db_config = DatabaseConfig(environment)
    
    try:
        engine = create_engine(
            db_config.connection_string,
            **db_config.engine_kwargs
        )
        logger.info(f"Database engine created for {environment} environment")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise

def create_session_factory(engine):
    """Create SQLAlchemy session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_database_connection(engine):
    """Verify database connection and schema."""
    try:
        with engine.connect() as conn:
            # Test basic connectivity
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            
            # Check if required tables exist
            required_tables = [
                "projects", "runtime_status", "analysis_results",
                "monetization_opportunities", "error_patterns", "project_metrics"
            ]
            
            for table in required_tables:
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = :table_name)"
                ), {"table_name": table})
                
                if not result.fetchone()[0]:
                    raise Exception(f"Required table '{table}' not found")
            
            logger.info("Database connection verified successfully")
            return True
            
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise

# Example usage and testing
def get_sample_queries():
    """Return sample queries for testing database functionality."""
    return {
        "project_count": "SELECT COUNT(*) FROM projects",
        "active_projects": "SELECT name, status FROM projects WHERE status = 'active'",
        "running_processes": """
            SELECT p.name, rs.process_name, rs.port 
            FROM runtime_status rs 
            JOIN projects p ON rs.project_id = p.id 
            WHERE rs.status = 'running'
        """,
        "recent_errors": """
            SELECT p.name, ep.error_type, ep.occurrence_count 
            FROM error_patterns ep 
            JOIN projects p ON ep.project_id = p.id 
            WHERE ep.last_seen > NOW() - INTERVAL '24 hours'
        """,
        "top_opportunities": """
            SELECT project_name, opportunity_type, potential_revenue 
            FROM monetization_ranking 
            ORDER BY opportunity_score DESC 
            LIMIT 5
        """
    }

# Database utilities
class DatabaseManager:
    """High-level database management utilities."""
    
    def __init__(self, environment: str = None):
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.engine = create_database_engine(self.environment)
        self.SessionLocal = create_session_factory(self.engine)
    
    def get_session(self):
        """Get database session with proper cleanup."""
        session = self.SessionLocal()
        try:
            return session
        except Exception:
            session.close()
            raise
    
    def execute_query(self, query: str, params: Dict = None):
        """Execute raw SQL query safely."""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return result.fetchall()
    
    def get_project_dashboard(self, project_name: str = None):
        """Get project dashboard data."""
        query = "SELECT * FROM project_dashboard"
        params = {}
        
        if project_name:
            query += " WHERE name = :project_name"
            params["project_name"] = project_name
        
        return self.execute_query(query, params)
    
    def get_error_summary(self, project_name: str = None, hours: int = 24):
        """Get error patterns summary."""
        query = """
            SELECT project_name, error_type, pattern_count, total_occurrences
            FROM error_patterns_summary
            WHERE most_recent_occurrence > NOW() - INTERVAL '%s hours'
        """ % hours
        
        if project_name:
            query += " AND project_name = :project_name"
        
        return self.execute_query(query, {"project_name": project_name} if project_name else {})
    
    def health_check(self):
        """Perform database health check."""
        try:
            verify_database_connection(self.engine)
            
            # Check recent activity
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM projects WHERE last_scanned > NOW() - INTERVAL '1 hour'"
                ))
                recent_scans = result.fetchone()[0]
                
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM runtime_status WHERE last_heartbeat > NOW() - INTERVAL '5 minutes'"
                ))
                recent_heartbeats = result.fetchone()[0]
            
            return {
                "status": "healthy",
                "recent_scans": recent_scans,
                "recent_heartbeats": recent_heartbeats,
                "environment": self.environment
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "environment": self.environment
            }

# Environment-specific configurations
ENVIRONMENT_CONFIGS = {
    "development": {
        "log_level": "DEBUG",
        "echo_sql": True,
        "auto_migrate": True,
    },
    "testing": {
        "log_level": "WARNING",
        "echo_sql": False,
        "auto_migrate": True,
        "database_suffix": "_test",
    },
    "production": {
        "log_level": "INFO",
        "echo_sql": False,
        "auto_migrate": False,
        "require_ssl": True,
    }
}

def setup_logging(environment: str):
    """Setup logging configuration for database operations."""
    config = ENVIRONMENT_CONFIGS.get(environment, ENVIRONMENT_CONFIGS["development"])
    
    logging.basicConfig(
        level=getattr(logging, config["log_level"]),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Reduce SQLAlchemy logging noise in production
    if environment == "production":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

if __name__ == "__main__":
    # Test database configuration
    import sys
    
    environment = sys.argv[1] if len(sys.argv) > 1 else "development"
    setup_logging(environment)
    
    try:
        db_manager = DatabaseManager(environment)
        health = db_manager.health_check()
        
        print(f"Database Health Check - Environment: {environment}")
        print(f"Status: {health['status']}")
        
        if health["status"] == "healthy":
            print(f"Recent scans: {health['recent_scans']}")
            print(f"Recent heartbeats: {health['recent_heartbeats']}")
            
            # Test sample queries
            print("\nSample Data:")
            projects = db_manager.get_project_dashboard()
            for project in projects:
                print(f"  Project: {project[1]} - Status: {project[4]}")
        else:
            print(f"Error: {health['error']}")
            
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)