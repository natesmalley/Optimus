#!/usr/bin/env python3
"""
Database setup script for Optimus Memory System.
Creates all necessary tables and indexes for the memory system to function.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.config import get_database_manager
from src.models import Base
from sqlalchemy import text


async def create_memory_tables():
    """Create all memory system tables"""
    print("🗄️  Setting up Optimus Memory System Database...")
    print("=" * 60)
    
    try:
        # Get database manager
        db_manager = get_database_manager()
        await db_manager.initialize()
        
        print("✅ Database manager initialized")
        
        # Create all tables using the async engine
        async with db_manager._postgres_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        print("✅ All memory system tables created successfully")
        
        # Create additional indexes for performance
        async with db_manager.get_postgres_session() as session:
            # Text search indexes
            await session.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deliberation_query_tsvector 
                ON deliberation_memories 
                USING GIN (to_tsvector('english', query));
            """))
            
            await session.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_persona_response_tsvector 
                ON persona_response_memories 
                USING GIN (to_tsvector('english', response || ' ' || reasoning));
            """))
            
            # Composite indexes for common queries
            await session.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deliberation_importance_created
                ON deliberation_memories (importance_score DESC, created_at DESC);
            """))
            
            await session.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_persona_confidence_created
                ON persona_response_memories (persona_name, confidence DESC, created_at DESC);
            """))
            
            await session.commit()
            
        print("✅ Performance indexes created successfully")
        
        # Verify table creation
        async with db_manager.get_postgres_session() as session:
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%memor%'
                ORDER BY table_name;
            """))
            
            tables = result.fetchall()
            
        print(f"✅ Verified {len(tables)} memory tables created:")
        for table in tables:
            print(f"   • {table[0]}")
            
        print("\n🎉 Memory system database setup completed successfully!")
        print("\nThe following components are now ready:")
        print("• DeliberationMemory - stores complete deliberation sessions")
        print("• PersonaResponseMemory - stores individual persona responses")
        print("• ContextMemory - stores contextual information")
        print("• PersonaLearningPattern - tracks learning patterns")
        print("• MemoryAssociation - links related memories")
        print("• MemoryMetrics - performance monitoring")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_memory_system():
    """Verify that the memory system can initialize with the new tables"""
    print("\n🧠 Verifying Memory System Integration...")
    
    try:
        from src.council.memory_system import get_memory_system
        
        # Initialize memory system
        memory_system = await get_memory_system()
        print("✅ Memory system initialized successfully")
        
        # Run health check
        health = await memory_system.health_check()
        print(f"✅ Memory system health: {health}")
        
        if health.get("status") == "healthy":
            print("✅ Memory system is fully operational!")
            return True
        else:
            print("⚠️ Memory system health check indicates issues")
            return False
            
    except Exception as e:
        print(f"❌ Memory system verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main setup function"""
    print("🚀 Optimus Memory System Database Setup")
    print("=" * 70)
    
    # Step 1: Create tables
    setup_success = await create_memory_tables()
    if not setup_success:
        print("❌ Database setup failed. Please check your PostgreSQL configuration.")
        return False
    
    # Step 2: Verify memory system
    verify_success = await verify_memory_system()
    if not verify_success:
        print("❌ Memory system verification failed.")
        return False
    
    print("\n" + "=" * 70)
    print("🎊 SUCCESS! Optimus Memory System is ready for use.")
    print("\n📋 Next Steps:")
    print("1. Start the Optimus backend: python src/main.py")
    print("2. Run deliberations using the Council of Minds")
    print("3. Watch as memories accumulate and enhance responses")
    print("4. Monitor performance through memory metrics")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)