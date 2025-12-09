#!/bin/bash
# Setup script for Optimus development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="Optimus"
PYTHON_VERSION="3.11"
NODE_VERSION="18"
REQUIRED_TOOLS=("docker" "docker-compose" "git" "curl")

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root"
        exit 1
    fi
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macOS"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        OS="windows"
        DISTRO="Windows"
    else
        error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log "Detected OS: $DISTRO"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    local missing_tools=()
    
    for tool in "${REQUIRED_TOOLS[@]}"; do
        if ! command_exists "$tool"; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        info "Please install the missing tools and run the setup again"
        
        if [[ "$OS" == "macos" ]]; then
            info "On macOS, you can install these using Homebrew:"
            for tool in "${missing_tools[@]}"; do
                echo "  brew install $tool"
            done
        elif [[ "$OS" == "linux" ]]; then
            info "On Ubuntu/Debian, you can install these using:"
            echo "  sudo apt-get update && sudo apt-get install ${missing_tools[*]}"
        fi
        
        exit 1
    fi
    
    log "All required tools are installed"
}

# Check Docker installation and status
check_docker() {
    log "Checking Docker installation..."
    
    if ! command_exists docker; then
        error "Docker is not installed"
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    log "Docker is installed and running"
}

# Check Python installation
check_python() {
    log "Checking Python installation..."
    
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        error "Python is not installed"
        exit 1
    fi
    
    CURRENT_PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    
    if [[ "$CURRENT_PYTHON_VERSION" < "$PYTHON_VERSION" ]]; then
        warn "Python version $CURRENT_PYTHON_VERSION is below recommended $PYTHON_VERSION"
    fi
    
    log "Python $CURRENT_PYTHON_VERSION is available"
}

# Check Node.js installation
check_node() {
    log "Checking Node.js installation..."
    
    if ! command_exists node; then
        error "Node.js is not installed"
        info "Please install Node.js $NODE_VERSION or later"
        exit 1
    fi
    
    CURRENT_NODE_VERSION=$(node --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    
    if [[ "$CURRENT_NODE_VERSION" < "$NODE_VERSION" ]]; then
        warn "Node.js version $CURRENT_NODE_VERSION is below recommended $NODE_VERSION"
    fi
    
    log "Node.js $CURRENT_NODE_VERSION is available"
}

# Create Python virtual environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        log "Virtual environment created"
    else
        log "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log "Python dependencies installed"
    else
        warn "requirements.txt not found"
    fi
}

# Setup frontend environment
setup_frontend_env() {
    log "Setting up frontend environment..."
    
    if [ -d "frontend" ]; then
        cd frontend
        
        if [ -f "package.json" ]; then
            npm install
            log "Frontend dependencies installed"
        else
            warn "package.json not found in frontend directory"
        fi
        
        cd ..
    else
        warn "Frontend directory not found"
    fi
}

# Create environment file
setup_env_file() {
    log "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log "Environment file created from .env.example"
        else
            # Create basic .env file
            cat > .env << EOF
# Optimus Environment Configuration
ENV=development
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://postgres:optimus123@localhost:5432/optimus_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=optimus123
POSTGRES_DB=optimus_db

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# API Configuration
API_PORT=8000
WORKERS=4
LOG_LEVEL=debug

# Security
JWT_SECRET=your-jwt-secret-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# AI Configuration (set your API keys)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Project Configuration
PROJECT_ROOT=$HOME/projects
SCAN_INTERVAL=300
EOF
            log "Basic environment file created"
        fi
        
        info "Please edit .env file with your specific configuration"
    else
        log "Environment file already exists"
    fi
}

# Setup Docker network
setup_docker_network() {
    log "Setting up Docker network..."
    
    if ! docker network ls | grep -q "optimus-network"; then
        docker network create optimus-network
        log "Docker network 'optimus-network' created"
    else
        log "Docker network 'optimus-network' already exists"
    fi
}

# Create necessary directories
create_directories() {
    log "Creating project directories..."
    
    local directories=(
        "data/memory"
        "data/knowledge"
        "logs"
        "config/environments"
        "scripts"
        "tests/integration"
        "tests/performance"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done
}

# Setup Git hooks (if in a Git repository)
setup_git_hooks() {
    if [ -d ".git" ]; then
        log "Setting up Git hooks..."
        
        # Pre-commit hook
        cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for Optimus

echo "Running pre-commit checks..."

# Check if virtual environment exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run linting
black --check src/ tests/ || exit 1
ruff check src/ tests/ || exit 1

# Run tests
pytest tests/ -x -q || exit 1

echo "Pre-commit checks passed!"
EOF
        
        chmod +x .git/hooks/pre-commit
        log "Git pre-commit hook installed"
    fi
}

# Test the installation
test_installation() {
    log "Testing installation..."
    
    # Test Python environment
    if source venv/bin/activate && python -c "import fastapi, sqlalchemy, redis" 2>/dev/null; then
        log "✓ Python dependencies are working"
    else
        warn "✗ Some Python dependencies may be missing"
    fi
    
    # Test Docker
    if docker run --rm hello-world >/dev/null 2>&1; then
        log "✓ Docker is working"
    else
        warn "✗ Docker test failed"
    fi
    
    # Test Docker Compose
    if docker-compose version >/dev/null 2>&1; then
        log "✓ Docker Compose is working"
    else
        warn "✗ Docker Compose test failed"
    fi
}

# Show next steps
show_next_steps() {
    echo ""
    echo -e "${GREEN}✓ Setup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Edit .env file with your configuration"
    echo "2. Start development environment: make dev"
    echo "3. Run tests: make test"
    echo "4. View application: http://localhost:3000"
    echo ""
    echo -e "${BLUE}Available commands:${NC}"
    echo "  make help          - Show all available commands"
    echo "  make dev           - Start development environment"
    echo "  make test          - Run tests"
    echo "  make build         - Build Docker images"
    echo "  make logs          - View application logs"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "  README.md          - Project overview"
    echo "  docs/              - Detailed documentation"
    echo ""
}

# Main setup function
main() {
    echo -e "${BLUE}$PROJECT_NAME Development Environment Setup${NC}"
    echo "========================================"
    echo ""
    
    check_root
    detect_os
    check_requirements
    check_docker
    check_python
    check_node
    
    setup_env_file
    create_directories
    setup_docker_network
    setup_python_env
    setup_frontend_env
    setup_git_hooks
    
    test_installation
    show_next_steps
}

# Handle script interruption
trap 'error "Setup interrupted"; exit 1' INT TERM

# Run main function
main "$@"