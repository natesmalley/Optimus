#!/usr/bin/env python
"""
Life Assistant Migration Script
Creates all tables and initial data for the personal assistant features
"""

import os
import sys
from pathlib import Path
import asyncio
import asyncpg
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:optimus123@localhost:5433/optimus_db")

async def run_migration():
    """Execute the migration."""
    print("🚀 Starting Life Assistant Migration...")
    
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Read the schema file
        schema_path = Path(__file__).parent.parent / "docs" / "database" / "life_assistant_schema.sql"
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema
        print("📝 Creating tables and initial data...")
        await conn.execute(schema_sql)
        
        # Verify tables were created
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'users', 'life_contexts', 'goals', 'habits', 
                'events', 'tasks', 'interactions', 'suggestions',
                'assistant_interactions', 'time_blocks', 'life_metrics',
                'relationships'
            )
            ORDER BY table_name;
        """)
        
        print("\n✅ Successfully created tables:")
        for table in tables:
            print(f"   • {table['table_name']}")
        
        # Check if default user was created
        user = await conn.fetchrow("SELECT * FROM users WHERE email = 'user@optimus.local'")
        if user:
            print(f"\n👤 Default user created: {user['name']} ({user['email']})")
            
            # Check contexts
            contexts = await conn.fetch("""
                SELECT code, name, icon 
                FROM life_contexts 
                WHERE user_id = $1 
                ORDER BY code
            """, user['id'])
            
            print("\n🎯 Life contexts initialized:")
            for ctx in contexts:
                print(f"   {ctx['icon']} {ctx['name']} ({ctx['code']})")
        
        print("\n✨ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

async def rollback_migration():
    """Rollback the migration if needed."""
    print("⏮️ Rolling back Life Assistant Migration...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Drop tables in reverse dependency order
        tables_to_drop = [
            'assistant_interactions',
            'suggestions',
            'interactions',
            'relationships',
            'life_metrics',
            'time_blocks',
            'tasks',
            'events',
            'habits',
            'goals',
            'life_contexts',
            'users'
        ]
        
        for table in tables_to_drop:
            await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print(f"   • Dropped {table}")
        
        # Drop views
        await conn.execute("DROP VIEW IF EXISTS today_agenda CASCADE;")
        await conn.execute("DROP VIEW IF EXISTS active_goals_summary CASCADE;")
        
        print("\n✅ Rollback completed")
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        raise
    finally:
        await conn.close()

async def check_status():
    """Check migration status."""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'life_contexts', 'goals', 'events', 'tasks')
        """)
        
        if tables:
            print("✅ Life Assistant tables are installed")
            
            # Get user count
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            print(f"   • Users: {user_count}")
            
            # Get other counts
            for table in ['goals', 'events', 'tasks', 'suggestions']:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"   • {table.capitalize()}: {count}")
        else:
            print("⚠️ Life Assistant tables not found - migration needed")
    
    finally:
        await conn.close()

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Life Assistant Database Migration")
    parser.add_argument("command", choices=["up", "down", "status"], 
                      help="Migration command to run")
    
    args = parser.parse_args()
    
    if args.command == "up":
        asyncio.run(run_migration())
    elif args.command == "down":
        confirm = input("⚠️ This will DELETE all life assistant data. Continue? (yes/no): ")
        if confirm.lower() == "yes":
            asyncio.run(rollback_migration())
        else:
            print("Rollback cancelled")
    elif args.command == "status":
        asyncio.run(check_status())

if __name__ == "__main__":
    main()