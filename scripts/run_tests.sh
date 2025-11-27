#!/bin/bash
# Comprehensive test runner for Optimus Council of Minds
# Supports different test types, coverage reporting, and CI/CD integration

set -e

# Default configuration
TEST_TYPE="all"
COVERAGE=true
VERBOSE=false
PARALLEL=false
JUNIT_XML=false
PERFORMANCE=false
BENCHMARK=false
TIMEOUT=300
MAX_FAILURES=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
show_help() {
    cat << EOF
Optimus Council of Minds Test Runner

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE         Test type: unit, integration, performance, all (default: all)
    -c, --coverage          Generate coverage report (default: true)
    -v, --verbose           Verbose output
    -p, --parallel          Run tests in parallel
    -j, --junit            Generate JUnit XML output
    -b, --benchmark        Run performance benchmarks
    -f, --max-failures NUM Maximum failures before stopping (default: 10)
    -T, --timeout SEC      Test timeout in seconds (default: 300)
    --no-coverage          Disable coverage reporting
    --fast                  Skip slow tests
    --stress               Include stress tests
    -h, --help             Show this help message

Examples:
    $0                      # Run all tests with coverage
    $0 -t unit -v           # Run unit tests verbosely
    $0 -t performance -b    # Run performance tests with benchmarks
    $0 --parallel --fast    # Run tests in parallel, skip slow tests
    $0 -t integration -j    # Run integration tests with JUnit output

Environment Variables:
    PYTEST_ARGS           Additional pytest arguments
    TEST_DATABASE_URL     Test database URL
    TEST_REDIS_URL        Test Redis URL
    CI                    Set to 'true' for CI mode
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -j|--junit)
            JUNIT_XML=true
            shift
            ;;
        -b|--benchmark)
            BENCHMARK=true
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        --stress)
            STRESS=true
            shift
            ;;
        -f|--max-failures)
            MAX_FAILURES="$2"
            shift 2
            ;;
        -T|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in CI mode
if [[ "${CI}" == "true" ]]; then
    log_info "Running in CI mode"
    VERBOSE=true
    JUNIT_XML=true
    COVERAGE=true
fi

# Validate test environment
validate_environment() {
    log_info "Validating test environment..."
    
    # Check Python version
    if ! python --version | grep -q "Python 3\.[8-9]\|Python 3\.1[0-9]"; then
        log_error "Python 3.8 or higher required"
        exit 1
    fi
    
    # Check required packages
    if ! pip show pytest >/dev/null 2>&1; then
        log_error "pytest not installed. Run: pip install -e .[dev]"
        exit 1
    fi
    
    # Check test dependencies
    if [[ "$COVERAGE" == "true" ]] && ! pip show pytest-cov >/dev/null 2>&1; then
        log_warning "pytest-cov not installed. Coverage reporting disabled."
        COVERAGE=false
    fi
    
    if [[ "$PARALLEL" == "true" ]] && ! pip show pytest-xdist >/dev/null 2>&1; then
        log_warning "pytest-xdist not installed. Parallel execution disabled."
        PARALLEL=false
    fi
    
    # Check database connectivity if running integration tests
    if [[ "$TEST_TYPE" == "integration" || "$TEST_TYPE" == "all" ]]; then
        if [[ -n "$TEST_DATABASE_URL" ]]; then
            log_info "Testing database connectivity..."
            python -c "
import asyncpg
import asyncio
import sys
import os

async def test_db():
    try:
        conn = await asyncpg.connect(os.getenv('TEST_DATABASE_URL'))
        await conn.close()
        print('Database connection successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(test_db())
" || exit 1
        fi
        
        if [[ -n "$TEST_REDIS_URL" ]]; then
            log_info "Testing Redis connectivity..."
            python -c "
import redis
import sys
import os

try:
    r = redis.from_url(os.getenv('TEST_REDIS_URL'))
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
    sys.exit(1)
" || exit 1
        fi
    fi
    
    log_success "Environment validation passed"
}

# Build pytest command
build_pytest_command() {
    local cmd="pytest"
    
    # Test paths based on type
    case $TEST_TYPE in
        unit)
            cmd="$cmd tests/unit/"
            ;;
        integration)
            cmd="$cmd tests/integration/"
            ;;
        performance)
            cmd="$cmd tests/performance/"
            ;;
        all)
            cmd="$cmd tests/"
            ;;
        *)
            log_error "Invalid test type: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # Coverage options
    if [[ "$COVERAGE" == "true" ]]; then
        cmd="$cmd --cov=src --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-report=term-missing --cov-fail-under=85"
    fi
    
    # Verbose output
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd -v"
    else
        cmd="$cmd -q"
    fi
    
    # Parallel execution
    if [[ "$PARALLEL" == "true" ]]; then
        local num_cpus=$(nproc 2>/dev/null || echo "2")
        cmd="$cmd -n $num_cpus"
    fi
    
    # JUnit XML output
    if [[ "$JUNIT_XML" == "true" ]]; then
        cmd="$cmd --junit-xml=junit-${TEST_TYPE}.xml"
    fi
    
    # Test selection markers
    local markers=""
    case $TEST_TYPE in
        unit)
            markers="unit"
            ;;
        integration)
            markers="integration"
            ;;
        performance)
            markers="performance"
            ;;
    esac
    
    # Add fast/slow test filtering
    if [[ "$FAST" == "true" ]]; then
        markers="${markers} and not slow"
    fi
    
    # Add stress test inclusion
    if [[ "$STRESS" == "true" ]]; then
        markers="${markers} or stress"
    fi
    
    # Add benchmark inclusion
    if [[ "$BENCHMARK" == "true" ]]; then
        markers="${markers} or benchmark"
    fi
    
    if [[ -n "$markers" ]]; then
        cmd="$cmd -m \"$markers\""
    fi
    
    # Additional options
    cmd="$cmd --timeout=$TIMEOUT --maxfail=$MAX_FAILURES --strict-markers --tb=short"
    
    # Add any additional pytest arguments from environment
    if [[ -n "$PYTEST_ARGS" ]]; then
        cmd="$cmd $PYTEST_ARGS"
    fi
    
    echo "$cmd"
}

# Run pre-test setup
pre_test_setup() {
    log_info "Running pre-test setup..."
    
    # Clean up previous test artifacts
    rm -rf htmlcov/ .coverage coverage.xml junit-*.xml .pytest_cache/
    
    # Create test directories if they don't exist
    mkdir -p tests/unit tests/integration tests/performance
    
    # Set up test environment variables
    export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/src"
    export TESTING=true
    
    # Initialize test database if needed
    if [[ "$TEST_TYPE" == "integration" || "$TEST_TYPE" == "all" ]] && [[ -n "$TEST_DATABASE_URL" ]]; then
        log_info "Initializing test database..."
        python -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from database.initialize import initialize_test_database

async def setup():
    try:
        await initialize_test_database()
        print('Test database initialized')
    except Exception as e:
        print(f'Test database setup failed: {e}')
        sys.exit(1)

asyncio.run(setup())
"
    fi
    
    log_success "Pre-test setup completed"
}

# Run post-test cleanup
post_test_cleanup() {
    log_info "Running post-test cleanup..."
    
    # Generate coverage report summary
    if [[ "$COVERAGE" == "true" ]] && [[ -f "coverage.xml" ]]; then
        log_info "Coverage report generated: htmlcov/index.html"
        
        # Extract coverage percentage
        if command -v grep >/dev/null 2>&1; then
            local coverage_pct=$(grep -o 'line-rate="[^"]*"' coverage.xml | head -1 | grep -o '[0-9.]*' | head -1)
            if [[ -n "$coverage_pct" ]]; then
                coverage_pct=$(echo "$coverage_pct * 100" | bc -l 2>/dev/null || echo "0")
                coverage_pct=$(printf "%.1f" "$coverage_pct")
                log_success "Coverage: ${coverage_pct}%"
            fi
        fi
    fi
    
    # Performance report summary
    if [[ "$TEST_TYPE" == "performance" || "$BENCHMARK" == "true" ]]; then
        log_info "Performance test results available in test output"
    fi
    
    # Clean up temporary files
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    log_success "Post-test cleanup completed"
}

# Main execution
main() {
    log_info "Starting Optimus Council of Minds test suite"
    log_info "Test type: $TEST_TYPE"
    log_info "Coverage: $COVERAGE"
    log_info "Verbose: $VERBOSE"
    log_info "Parallel: $PARALLEL"
    log_info "Benchmark: $BENCHMARK"
    
    # Validate environment
    validate_environment
    
    # Setup tests
    pre_test_setup
    
    # Build and run pytest command
    local pytest_cmd=$(build_pytest_command)
    log_info "Running: $pytest_cmd"
    
    # Execute tests
    local start_time=$(date +%s)
    if eval "$pytest_cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "Tests completed successfully in ${duration}s"
        local exit_code=0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_error "Tests failed after ${duration}s"
        local exit_code=1
    fi
    
    # Cleanup
    post_test_cleanup
    
    exit $exit_code
}

# Run main function
main "$@"