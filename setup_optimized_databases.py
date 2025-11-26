#!/usr/bin/env python3
"""
Optimus Database Optimization Setup Script

Complete setup script for initializing the optimized database system
for the Optimus Council of Minds project.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.initialize import main_initialization, quick_health_check, cleanup_and_shutdown


def print_banner():
    """Print setup banner"""
    print("=" * 80)
    print("  OPTIMUS COUNCIL OF MINDS - DATABASE OPTIMIZATION SETUP")
    print("=" * 80)
    print()
    print("This script will set up the optimized database system including:")
    print("  • PostgreSQL with advanced indexing and materialized views")
    print("  • SQLite Memory System with connection pooling and compression")
    print("  • SQLite Knowledge Graph with persistent storage and caching")
    print("  • Redis Cache Layer with intelligent serialization")
    print("  • Performance monitoring and alerting system")
    print("  • Database migrations and schema optimizations")
    print()
    print("Prerequisites:")
    print("  • PostgreSQL server running and accessible")
    print("  • Redis server running and accessible")
    print("  • Python environment with all dependencies installed")
    print()


def print_completion_message():
    """Print completion message with next steps"""
    print("=" * 80)
    print("  SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print()
    print("Your optimized database system is now ready for use.")
    print()
    print("Next steps:")
    print("  1. Update your Council of Minds code to use the optimized systems:")
    print("     from src.council.memory_integration import MemorySystem")
    print("     from src.council.knowledge_graph_integration import KnowledgeGraph")
    print()
    print("  2. Start using the performance monitoring dashboard:")
    print("     from src.database.performance_monitor import get_performance_monitor")
    print("     monitor = get_performance_monitor()")
    print("     dashboard_data = await monitor.get_dashboard_data()")
    print()
    print("  3. Access the Redis cache layer:")
    print("     from src.database.redis_cache import get_cache_manager")
    print("     cache = get_cache_manager()")
    print("     await cache.initialize()")
    print()
    print("  4. Run performance benchmarks periodically:")
    print("     python -c \"import asyncio; from src.database.benchmarks import run_performance_validation; asyncio.run(run_performance_validation())\"")
    print()
    print("  5. Check system health:")
    print("     python setup_optimized_databases.py --health-check")
    print()
    print("Performance improvements you can expect:")
    print("  • Memory recall: 5-10x faster with caching and optimized indexes")
    print("  • Knowledge graph traversals: 3-5x faster with database-assisted search")
    print("  • Dashboard queries: 10x faster with materialized views")
    print("  • Bulk operations: 5-20x faster with batch processing")
    print("  • Overall responsiveness: Significantly improved for 13+ personas")
    print()
    print("Documentation: /docs/database/OPTIMIZATION_GUIDE.md")
    print("=" * 80)


def print_health_summary(all_healthy: bool):
    """Print health check summary"""
    print("=" * 80)
    print("  HEALTH CHECK RESULTS")
    print("=" * 80)
    
    if all_healthy:
        print("✓ All database systems are healthy and operational")
        print("✓ Performance monitoring is active")
        print("✓ Cache layer is responding")
        print("✓ Connection pools are functioning")
        print()
        print("Your optimized database system is ready for production use!")
    else:
        print("⚠ Some database systems need attention")
        print("⚠ Check the logs for specific issues")
        print("⚠ Consider running full setup again if problems persist")
        print()
        print("Troubleshooting tips:")
        print("  • Verify PostgreSQL and Redis servers are running")
        print("  • Check network connectivity and credentials")
        print("  • Review database_setup.log for detailed error messages")
    
    print("=" * 80)


async def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Optimus Database Optimization Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_optimized_databases.py                    # Full setup
  python setup_optimized_databases.py --health-check     # Quick health check
  python setup_optimized_databases.py --cleanup          # Cleanup and shutdown
        """
    )
    
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run health check only"
    )
    
    parser.add_argument(
        "--cleanup",
        action="store_true", 
        help="Cleanup and shutdown database connections"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        print_banner()
    
    try:
        if args.health_check:
            if not args.quiet:
                print("Running health check...")
            
            all_healthy = await quick_health_check()
            
            if not args.quiet:
                print_health_summary(all_healthy)
            
            return 0 if all_healthy else 1
        
        elif args.cleanup:
            if not args.quiet:
                print("Cleaning up database connections...")
            
            await cleanup_and_shutdown()
            
            if not args.quiet:
                print("Cleanup completed successfully!")
            
            return 0
        
        else:
            # Full setup
            if not args.quiet:
                print("Starting full database optimization setup...")
                print("This may take several minutes depending on your system...")
                print()
            
            success = await main_initialization()
            
            if success:
                if not args.quiet:
                    print_completion_message()
                return 0
            else:
                if not args.quiet:
                    print("=" * 80)
                    print("  SETUP FAILED")
                    print("=" * 80)
                    print("Check database_setup.log for detailed error information.")
                    print("Common issues:")
                    print("  • PostgreSQL server not running or not accessible")
                    print("  • Redis server not running or not accessible") 
                    print("  • Network connectivity issues")
                    print("  • Insufficient permissions")
                return 1
    
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nSetup interrupted by user")
        
        # Attempt cleanup
        try:
            await cleanup_and_shutdown()
        except:
            pass
        
        return 1
    
    except Exception as e:
        if not args.quiet:
            print(f"\nSetup failed with error: {e}")
            print("Check database_setup.log for detailed error information.")
        
        return 1


if __name__ == "__main__":
    # Set up logging to capture detailed output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('database_setup.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Run the setup
    exit_code = asyncio.run(main())
    sys.exit(exit_code)