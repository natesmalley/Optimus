"""
Database Migration System

Comprehensive database migration framework for schema evolution,
data migration, and rollback capabilities for the Optimus system.
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
from abc import ABC, abstractmethod
import hashlib
import logging

from .config import get_database_manager, DatabaseManager
from .postgres_optimized import get_postgres_optimizer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


@dataclass
class MigrationInfo:
    """Migration metadata"""
    id: str
    name: str
    description: str
    version: str
    created_at: datetime
    checksum: str
    dependencies: List[str]
    rollback_sql: Optional[str] = None


class Migration(ABC):
    """Abstract base class for database migrations"""
    
    def __init__(self, migration_info: MigrationInfo):
        self.info = migration_info
        self.logger = logging.getLogger(f"migration.{migration_info.id}")
    
    @abstractmethod
    async def up(self, db_manager: DatabaseManager) -> bool:
        """Apply migration"""
        pass
    
    @abstractmethod
    async def down(self, db_manager: DatabaseManager) -> bool:
        """Rollback migration"""
        pass
    
    async def validate(self, db_manager: DatabaseManager) -> bool:
        """Validate migration can be applied"""
        return True


class PostgreSQLMigration(Migration):
    """PostgreSQL-specific migration"""
    
    def __init__(self, migration_info: MigrationInfo, sql_up: str, sql_down: Optional[str] = None):
        super().__init__(migration_info)
        self.sql_up = sql_up
        self.sql_down = sql_down
    
    async def up(self, db_manager: DatabaseManager) -> bool:
        """Apply PostgreSQL migration"""
        try:
            async with db_manager.get_postgres_session() as session:
                # Split and execute SQL statements
                statements = self._split_sql_statements(self.sql_up)
                
                for statement in statements:
                    if statement.strip():
                        self.logger.info(f"Executing: {statement[:100]}...")
                        await session.execute(text(statement))
                
                await session.commit()
                self.logger.info(f"Migration {self.info.id} applied successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Migration {self.info.id} failed: {e}")
            return False
    
    async def down(self, db_manager: DatabaseManager) -> bool:
        """Rollback PostgreSQL migration"""
        if not self.sql_down:
            self.logger.warning(f"No rollback SQL for migration {self.info.id}")
            return False
        
        try:
            async with db_manager.get_postgres_session() as session:
                statements = self._split_sql_statements(self.sql_down)
                
                for statement in statements:
                    if statement.strip():
                        self.logger.info(f"Rolling back: {statement[:100]}...")
                        await session.execute(text(statement))
                
                await session.commit()
                self.logger.info(f"Migration {self.info.id} rolled back successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Migration {self.info.id} rollback failed: {e}")
            return False
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into individual statements"""
        # Simple SQL statement splitter (can be enhanced for complex cases)
        statements = []
        current_statement = []
        
        for line in sql.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            current_statement.append(line)
            
            if line.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # Add remaining statement if not empty
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return statements


class SQLiteMigration(Migration):
    """SQLite-specific migration for Memory and Knowledge databases"""
    
    def __init__(self, migration_info: MigrationInfo, sql_up: str, sql_down: Optional[str] = None, db_type: str = "memory"):
        super().__init__(migration_info)
        self.sql_up = sql_up
        self.sql_down = sql_down
        self.db_type = db_type  # "memory" or "knowledge"
    
    async def up(self, db_manager: DatabaseManager) -> bool:
        """Apply SQLite migration"""
        try:
            if self.db_type == "memory":
                conn = db_manager.get_memory_connection()
            else:
                conn = db_manager.get_knowledge_connection()
            
            cursor = conn.cursor()
            
            # Execute SQL statements
            statements = self._split_sql_statements(self.sql_up)
            
            for statement in statements:
                if statement.strip():
                    self.logger.info(f"Executing: {statement[:100]}...")
                    cursor.execute(statement)
            
            conn.commit()
            
            if self.db_type == "memory":
                db_manager.return_memory_connection(conn)
            else:
                db_manager.return_knowledge_connection(conn)
            
            self.logger.info(f"SQLite migration {self.info.id} applied successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"SQLite migration {self.info.id} failed: {e}")
            return False
    
    async def down(self, db_manager: DatabaseManager) -> bool:
        """Rollback SQLite migration"""
        if not self.sql_down:
            self.logger.warning(f"No rollback SQL for SQLite migration {self.info.id}")
            return False
        
        try:
            if self.db_type == "memory":
                conn = db_manager.get_memory_connection()
            else:
                conn = db_manager.get_knowledge_connection()
            
            cursor = conn.cursor()
            
            statements = self._split_sql_statements(self.sql_down)
            
            for statement in statements:
                if statement.strip():
                    self.logger.info(f"Rolling back: {statement[:100]}...")
                    cursor.execute(statement)
            
            conn.commit()
            
            if self.db_type == "memory":
                db_manager.return_memory_connection(conn)
            else:
                db_manager.return_knowledge_connection(conn)
            
            self.logger.info(f"SQLite migration {self.info.id} rolled back successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"SQLite migration {self.info.id} rollback failed: {e}")
            return False
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into individual statements for SQLite"""
        statements = []
        current_statement = []
        
        for line in sql.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            current_statement.append(line)
            
            if line.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return statements


class DataMigration(Migration):
    """Custom data migration with Python code"""
    
    def __init__(self, migration_info: MigrationInfo, up_function: Callable, down_function: Optional[Callable] = None):
        super().__init__(migration_info)
        self.up_function = up_function
        self.down_function = down_function
    
    async def up(self, db_manager: DatabaseManager) -> bool:
        """Apply data migration"""
        try:
            result = await self.up_function(db_manager)
            self.logger.info(f"Data migration {self.info.id} completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Data migration {self.info.id} failed: {e}")
            return False
    
    async def down(self, db_manager: DatabaseManager) -> bool:
        """Rollback data migration"""
        if not self.down_function:
            self.logger.warning(f"No rollback function for data migration {self.info.id}")
            return False
        
        try:
            result = await self.down_function(db_manager)
            self.logger.info(f"Data migration {self.info.id} rolled back successfully")
            return result
        except Exception as e:
            self.logger.error(f"Data migration {self.info.id} rollback failed: {e}")
            return False


class MigrationRunner:
    """
    Database migration runner with dependency management,
    rollback capabilities, and migration tracking.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        self.migrations: Dict[str, Migration] = {}
        self.logger = logging.getLogger("migration_runner")
        self.migration_table_name = "schema_migrations"
    
    async def initialize(self):
        """Initialize migration tracking tables"""
        await self._create_migration_tables()
    
    async def _create_migration_tables(self):
        """Create migration tracking tables in all databases"""
        # PostgreSQL migration table
        try:
            async with self.db_manager.get_postgres_session() as session:
                await session.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.migration_table_name} (
                        id VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        version VARCHAR(50),
                        checksum VARCHAR(64),
                        applied_at TIMESTAMP DEFAULT NOW(),
                        execution_time_ms INTEGER,
                        status VARCHAR(20) DEFAULT 'applied'
                    )
                """))
                await session.commit()
        except Exception as e:
            self.logger.error(f"Failed to create PostgreSQL migration table: {e}")
        
        # SQLite migration tables (Memory DB)
        try:
            conn = self.db_manager.get_memory_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.migration_table_name} (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT,
                    checksum TEXT,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    status TEXT DEFAULT 'applied'
                )
            """)
            conn.commit()
            self.db_manager.return_memory_connection(conn)
        except Exception as e:
            self.logger.error(f"Failed to create Memory DB migration table: {e}")
        
        # SQLite migration tables (Knowledge DB)
        try:
            conn = self.db_manager.get_knowledge_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.migration_table_name} (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT,
                    checksum TEXT,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    status TEXT DEFAULT 'applied'
                )
            """)
            conn.commit()
            self.db_manager.return_knowledge_connection(conn)
        except Exception as e:
            self.logger.error(f"Failed to create Knowledge DB migration table: {e}")
    
    def register_migration(self, migration: Migration):
        """Register a migration"""
        self.migrations[migration.info.id] = migration
        self.logger.info(f"Registered migration: {migration.info.id} - {migration.info.name}")
    
    async def get_applied_migrations(self, db_type: str = "postgres") -> List[str]:
        """Get list of applied migration IDs"""
        applied = []
        
        try:
            if db_type == "postgres":
                async with self.db_manager.get_postgres_session() as session:
                    result = await session.execute(text(f"SELECT id FROM {self.migration_table_name} WHERE status = 'applied'"))
                    applied = [row[0] for row in result.fetchall()]
            elif db_type == "memory":
                conn = self.db_manager.get_memory_connection()
                cursor = conn.cursor()
                cursor.execute(f"SELECT id FROM {self.migration_table_name} WHERE status = 'applied'")
                applied = [row[0] for row in cursor.fetchall()]
                self.db_manager.return_memory_connection(conn)
            elif db_type == "knowledge":
                conn = self.db_manager.get_knowledge_connection()
                cursor = conn.cursor()
                cursor.execute(f"SELECT id FROM {self.migration_table_name} WHERE status = 'applied'")
                applied = [row[0] for row in cursor.fetchall()]
                self.db_manager.return_knowledge_connection(conn)
        
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations for {db_type}: {e}")
        
        return applied
    
    async def get_pending_migrations(self, db_type: str = "postgres") -> List[Migration]:
        """Get list of pending migrations in dependency order"""
        applied = await self.get_applied_migrations(db_type)
        pending = []
        
        # Filter migrations by type
        type_filter = {
            "postgres": PostgreSQLMigration,
            "memory": lambda m: isinstance(m, SQLiteMigration) and m.db_type == "memory",
            "knowledge": lambda m: isinstance(m, SQLiteMigration) and m.db_type == "knowledge"
        }
        
        for migration_id, migration in self.migrations.items():
            if migration_id not in applied:
                if db_type == "postgres" and isinstance(migration, PostgreSQLMigration):
                    pending.append(migration)
                elif db_type == "memory" and isinstance(migration, SQLiteMigration) and migration.db_type == "memory":
                    pending.append(migration)
                elif db_type == "knowledge" and isinstance(migration, SQLiteMigration) and migration.db_type == "knowledge":
                    pending.append(migration)
                elif isinstance(migration, DataMigration):  # Data migrations can apply to any DB
                    pending.append(migration)
        
        # Sort by dependencies (simple topological sort)
        return self._sort_by_dependencies(pending)
    
    def _sort_by_dependencies(self, migrations: List[Migration]) -> List[Migration]:
        """Sort migrations by dependencies"""
        sorted_migrations = []
        remaining = migrations.copy()
        
        while remaining:
            # Find migrations with no unresolved dependencies
            ready = []
            for migration in remaining:
                dependencies_satisfied = all(
                    dep_id in [m.info.id for m in sorted_migrations]
                    for dep_id in migration.info.dependencies
                )
                if dependencies_satisfied:
                    ready.append(migration)
            
            if not ready:
                # Circular dependency or missing dependency
                self.logger.error("Circular or missing dependencies detected")
                break
            
            # Add ready migrations
            for migration in ready:
                sorted_migrations.append(migration)
                remaining.remove(migration)
        
        return sorted_migrations
    
    async def run_migrations(self, db_type: str = "all") -> bool:
        """Run pending migrations for specified database type"""
        if db_type == "all":
            success = True
            for db_type_name in ["postgres", "memory", "knowledge"]:
                result = await self._run_migrations_for_db(db_type_name)
                success = success and result
            return success
        else:
            return await self._run_migrations_for_db(db_type)
    
    async def _run_migrations_for_db(self, db_type: str) -> bool:
        """Run migrations for a specific database type"""
        pending = await self.get_pending_migrations(db_type)
        
        if not pending:
            self.logger.info(f"No pending migrations for {db_type}")
            return True
        
        self.logger.info(f"Running {len(pending)} pending migrations for {db_type}")
        
        success = True
        for migration in pending:
            start_time = datetime.now()
            
            # Validate migration
            if not await migration.validate(self.db_manager):
                self.logger.error(f"Migration {migration.info.id} validation failed")
                success = False
                break
            
            # Apply migration
            self.logger.info(f"Applying migration: {migration.info.id} - {migration.info.name}")
            
            if await migration.up(self.db_manager):
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                await self._record_migration(migration, db_type, execution_time)
                self.logger.info(f"Migration {migration.info.id} completed in {execution_time}ms")
            else:
                self.logger.error(f"Migration {migration.info.id} failed")
                success = False
                break
        
        return success
    
    async def rollback_migration(self, migration_id: str, db_type: str) -> bool:
        """Rollback a specific migration"""
        if migration_id not in self.migrations:
            self.logger.error(f"Migration {migration_id} not found")
            return False
        
        migration = self.migrations[migration_id]
        
        # Check if migration is applied
        applied = await self.get_applied_migrations(db_type)
        if migration_id not in applied:
            self.logger.warning(f"Migration {migration_id} is not applied")
            return True
        
        self.logger.info(f"Rolling back migration: {migration_id}")
        
        if await migration.down(self.db_manager):
            await self._remove_migration_record(migration_id, db_type)
            self.logger.info(f"Migration {migration_id} rolled back successfully")
            return True
        else:
            self.logger.error(f"Migration {migration_id} rollback failed")
            return False
    
    async def _record_migration(self, migration: Migration, db_type: str, execution_time: int):
        """Record migration in the tracking table"""
        try:
            if db_type == "postgres":
                async with self.db_manager.get_postgres_session() as session:
                    await session.execute(text(f"""
                        INSERT INTO {self.migration_table_name} 
                        (id, name, description, version, checksum, execution_time_ms)
                        VALUES (:id, :name, :description, :version, :checksum, :execution_time)
                    """), {
                        'id': migration.info.id,
                        'name': migration.info.name,
                        'description': migration.info.description,
                        'version': migration.info.version,
                        'checksum': migration.info.checksum,
                        'execution_time': execution_time
                    })
                    await session.commit()
            else:
                if db_type == "memory":
                    conn = self.db_manager.get_memory_connection()
                else:
                    conn = self.db_manager.get_knowledge_connection()
                
                cursor = conn.cursor()
                cursor.execute(f"""
                    INSERT INTO {self.migration_table_name} 
                    (id, name, description, version, checksum, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    migration.info.id,
                    migration.info.name,
                    migration.info.description,
                    migration.info.version,
                    migration.info.checksum,
                    execution_time
                ))
                conn.commit()
                
                if db_type == "memory":
                    self.db_manager.return_memory_connection(conn)
                else:
                    self.db_manager.return_knowledge_connection(conn)
        
        except Exception as e:
            self.logger.error(f"Failed to record migration {migration.info.id}: {e}")
    
    async def _remove_migration_record(self, migration_id: str, db_type: str):
        """Remove migration record from tracking table"""
        try:
            if db_type == "postgres":
                async with self.db_manager.get_postgres_session() as session:
                    await session.execute(text(f"DELETE FROM {self.migration_table_name} WHERE id = :id"), {'id': migration_id})
                    await session.commit()
            else:
                if db_type == "memory":
                    conn = self.db_manager.get_memory_connection()
                else:
                    conn = self.db_manager.get_knowledge_connection()
                
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self.migration_table_name} WHERE id = ?", (migration_id,))
                conn.commit()
                
                if db_type == "memory":
                    self.db_manager.return_memory_connection(conn)
                else:
                    self.db_manager.return_knowledge_connection(conn)
        
        except Exception as e:
            self.logger.error(f"Failed to remove migration record {migration_id}: {e}")
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status"""
        status = {}
        
        for db_type in ["postgres", "memory", "knowledge"]:
            applied = await self.get_applied_migrations(db_type)
            pending = await self.get_pending_migrations(db_type)
            
            status[db_type] = {
                'applied_count': len(applied),
                'pending_count': len(pending),
                'applied_migrations': applied,
                'pending_migrations': [m.info.id for m in pending]
            }
        
        return status


def create_migration_id(name: str) -> str:
    """Create a unique migration ID based on timestamp and name"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"{timestamp}_{name_hash}"


def calculate_checksum(content: str) -> str:
    """Calculate checksum for migration content"""
    return hashlib.sha256(content.encode()).hexdigest()