-- =============================================================================
-- Optimus Database Setup Script
-- =============================================================================
-- This script sets up the Optimus database from scratch
-- Run as a PostgreSQL superuser or database owner

-- Database setup
\echo 'Creating Optimus database...'

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE optimus_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'optimus_db')\gexec

-- Connect to the database
\c optimus_db;

-- Enable required extensions
\echo 'Installing required extensions...'
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Check if tables already exist
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'projects') THEN
        RAISE NOTICE 'Database appears to already exist. Skipping table creation.';
        RAISE NOTICE 'To recreate the database, drop it first: DROP DATABASE optimus_db;';
    ELSE
        -- Execute the main schema file if tables don't exist
        RAISE NOTICE 'Creating database schema...';
    END IF;
END $$;

-- Load the main schema
\i schema.sql

-- Verify installation
\echo 'Verifying database installation...'

DO $$
DECLARE
    table_count INTEGER;
    view_count INTEGER;
    function_count INTEGER;
BEGIN
    -- Count tables
    SELECT COUNT(*) INTO table_count 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    -- Count views
    SELECT COUNT(*) INTO view_count 
    FROM information_schema.views 
    WHERE table_schema = 'public';
    
    -- Count functions/triggers
    SELECT COUNT(*) INTO function_count 
    FROM information_schema.routines 
    WHERE routine_schema = 'public';
    
    RAISE NOTICE 'Database setup complete!';
    RAISE NOTICE '  Tables: %', table_count;
    RAISE NOTICE '  Views: %', view_count;
    RAISE NOTICE '  Functions: %', function_count;
    
    -- Verify sample data
    IF EXISTS (SELECT 1 FROM projects WHERE name = 'Optimus') THEN
        RAISE NOTICE '  Sample data: Loaded successfully';
    ELSE
        RAISE NOTICE '  Sample data: Not found - may need to run separately';
    END IF;
END $$;

-- Show connection info
\echo ''
\echo 'Database: optimus_db'
\echo 'Schema: public'
\echo ''
\echo 'Next steps:'
\echo '1. Create application user: CREATE USER optimus_user WITH PASSWORD ''your_password'';'
\echo '2. Grant permissions: GRANT ALL ON ALL TABLES IN SCHEMA public TO optimus_user;'
\echo '3. Configure your application connection string'
\echo '4. Test the installation with: SELECT * FROM project_dashboard;'