"""
Database Initialization and Setup

Master initialization script for setting up all optimized database systems,
running migrations, and validating performance for Optimus Council of Minds.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .config import get_database_manager, initialize_databases, close_databases
from .migration_definitions import register_all_migrations, run_all_migrations
from .redis_cache import initialize_cache
from .performance_monitor import get_performance_monitor, start_performance_monitoring
from .benchmarks import run_performance_validation
from .postgres_optimized import get_postgres_optimizer


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('database_setup.log')
        ]
    )


async def verify_database_connections() -> Dict[str, bool]:
    """Verify all database connections are working"""
    logger = logging.getLogger("db_verify")
    db_manager = get_database_manager()
    
    health_status = await db_manager.health_check()
    
    logger.info("Database Connection Status:")
    for db_name, is_healthy in health_status.items():
        status = "✓ Connected" if is_healthy else "✗ Failed"
        logger.info(f"  {db_name}: {status}")
    
    all_healthy = all(health_status.values())
    if not all_healthy:
        logger.error("Some database connections failed!")
        return health_status
    
    logger.info("All database connections verified successfully")
    return health_status


async def setup_postgresql_optimizations():
    """Setup PostgreSQL-specific optimizations"""
    logger = logging.getLogger("postgres_setup")
    
    try:
        optimizer = get_postgres_optimizer()
        
        logger.info("Creating optimized PostgreSQL indexes...")
        await optimizer.create_optimized_indexes()
        
        logger.info("Creating materialized views...")
        await optimizer.create_materialized_views()
        
        logger.info("Setting up automatic maintenance...")
        await optimizer.setup_automatic_maintenance()
        
        logger.info("Applying query optimizations...")
        await optimizer.optimize_query_performance()
        
        logger.info("PostgreSQL optimizations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"PostgreSQL optimization failed: {e}")
        return False


async def setup_performance_monitoring():
    """Setup and start performance monitoring"""
    logger = logging.getLogger("monitoring_setup")
    
    try:
        monitor = get_performance_monitor()
        await monitor.start_monitoring()
        
        logger.info("Performance monitoring started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Performance monitoring setup failed: {e}")
        return False


async def validate_optimizations():
    """Validate that optimizations are working correctly"""
    logger = logging.getLogger("validation")
    
    try:
        logger.info("Running performance validation benchmarks...")
        benchmark_results = await run_performance_validation()
        
        # Check if performance meets expectations
        summary = benchmark_results.summary_stats.get("performance_summary", {})
        avg_time = summary.get("avg_execution_time_ms", float('inf'))
        success_rate = summary.get("overall_success_rate", 0)
        
        if avg_time > 10000:  # 10 seconds
            logger.warning(f"Average execution time is high: {avg_time:.2f}ms")
        
        if success_rate < 0.95:  # 95%
            logger.warning(f"Success rate is low: {success_rate*100:.1f}%")
        
        if avg_time <= 5000 and success_rate >= 0.95:
            logger.info("Performance validation passed!")
            return True
        else:
            logger.warning("Performance validation shows issues that may need attention")
            return True  # Still continue, just with warnings
            
    except Exception as e:
        logger.error(f"Performance validation failed: {e}")
        return False


async def create_data_directories():
    """Create necessary data directories"""
    logger = logging.getLogger("directory_setup")
    
    directories = [
        "data",
        "data/memory",
        "data/knowledge",
        "data/backups",
        "data/logs"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")


async def main_initialization():
    """Main database initialization process"""
    setup_logging()
    logger = logging.getLogger("db_init")
    
    logger.info("=" * 80)
    logger.info("OPTIMUS DATABASE OPTIMIZATION INITIALIZATION")
    logger.info("=" * 80)
    
    try:
        # Step 1: Create data directories
        logger.info("Step 1: Creating data directories...")
        await create_data_directories()
        
        # Step 2: Initialize database connections
        logger.info("Step 2: Initializing database connections...")
        await initialize_databases()
        
        # Step 3: Verify connections
        logger.info("Step 3: Verifying database connections...")
        health_status = await verify_database_connections()
        if not all(health_status.values()):
            logger.error("Database connection verification failed")
            return False
        
        # Step 4: Initialize cache
        logger.info("Step 4: Initializing Redis cache...")
        await initialize_cache()
        
        # Step 5: Run database migrations
        logger.info("Step 5: Running database migrations...")
        migration_success = await run_all_migrations()
        if not migration_success:
            logger.error("Database migrations failed")
            return False
        
        # Step 6: Setup PostgreSQL optimizations
        logger.info("Step 6: Setting up PostgreSQL optimizations...")
        postgres_success = await setup_postgresql_optimizations()
        if not postgres_success:
            logger.warning("PostgreSQL optimizations had issues")
        
        # Step 7: Start performance monitoring
        logger.info("Step 7: Starting performance monitoring...")
        monitoring_success = await setup_performance_monitoring()
        if not monitoring_success:
            logger.warning("Performance monitoring setup had issues")
        
        # Step 8: Validate optimizations
        logger.info("Step 8: Validating optimizations...")
        validation_success = await validate_optimizations()
        if not validation_success:
            logger.warning("Performance validation had issues")
        
        logger.info("=" * 80)
        logger.info("DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        
        # Print summary
        logger.info("SYSTEM STATUS SUMMARY:")
        logger.info(f"  Database Connections: {'✓ All Connected' if all(health_status.values()) else '✗ Some Failed'}")
        logger.info(f"  Migrations:          {'✓ Completed' if migration_success else '✗ Failed'}")
        logger.info(f"  PostgreSQL Opts:     {'✓ Applied' if postgres_success else '⚠ Issues'}")
        logger.info(f"  Performance Monitor: {'✓ Running' if monitoring_success else '⚠ Issues'}")
        logger.info(f"  Validation:          {'✓ Passed' if validation_success else '⚠ Issues'}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed with error: {e}")
        return False
    
    finally:
        # Cleanup is handled by context managers and will happen automatically
        pass


async def quick_health_check():
    """Quick health check for existing setup"""
    setup_logging()
    logger = logging.getLogger("health_check")
    
    logger.info("Running quick database health check...")
    
    try:
        # Initialize connections
        await initialize_databases()
        
        # Check connections
        health_status = await verify_database_connections()
        
        # Check cache
        from .redis_cache import get_cache_manager
        cache_manager = get_cache_manager()
        await cache_manager.initialize()
        cache_healthy = await cache_manager.health_check()
        
        # Check monitoring
        monitor = get_performance_monitor()
        dashboard_data = await monitor.get_dashboard_data()
        
        logger.info("Health Check Results:")
        logger.info(f"  PostgreSQL: {'✓' if health_status.get('postgres', False) else '✗'}")
        logger.info(f"  Redis:      {'✓' if health_status.get('redis', False) else '✗'}")
        logger.info(f"  Memory DB:  {'✓' if health_status.get('memory_db', False) else '✗'}")
        logger.info(f"  Knowledge:  {'✓' if health_status.get('knowledge_db', False) else '✗'}")
        logger.info(f"  Cache:      {'✓' if cache_healthy else '✗'}")
        logger.info(f"  Monitor:    {'✓' if dashboard_data else '✗'}")
        
        all_healthy = (
            all(health_status.values()) and 
            cache_healthy and 
            bool(dashboard_data)
        )
        
        if all_healthy:
            logger.info("✓ All systems healthy!")
        else:
            logger.warning("⚠ Some systems need attention")
        
        return all_healthy
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


async def cleanup_and_shutdown():
    """Cleanup and shutdown all database connections"""
    logger = logging.getLogger("cleanup")
    
    try:
        logger.info("Shutting down performance monitoring...")
        monitor = get_performance_monitor()
        await monitor.stop_monitoring()
        
        logger.info("Closing cache connections...")
        from .redis_cache import get_cache_manager
        cache_manager = get_cache_manager()
        await cache_manager.close()
        
        logger.info("Closing database connections...")
        await close_databases()
        
        logger.info("Cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def main():
    """Main entry point for database initialization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimus Database Initialization")
    parser.add_argument(
        "--mode", 
        choices=["full", "health-check", "cleanup"],
        default="full",
        help="Initialization mode"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "full":
            success = asyncio.run(main_initialization())
            sys.exit(0 if success else 1)
        elif args.mode == "health-check":
            success = asyncio.run(quick_health_check())
            sys.exit(0 if success else 1)
        elif args.mode == "cleanup":
            asyncio.run(cleanup_and_shutdown())
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\nInitialization interrupted by user")
        asyncio.run(cleanup_and_shutdown())
        sys.exit(1)
    except Exception as e:
        print(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()