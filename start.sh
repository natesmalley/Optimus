#!/bin/bash

# Optimus Project Orchestrator - Startup Script
# =============================================

echo "🤖 Starting Optimus Project Orchestrator..."
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Start databases
echo "📦 Starting databases..."

# PostgreSQL
if docker ps | grep -q optimus-postgres; then
    echo -e "${GREEN}✓ PostgreSQL already running${NC}"
else
    echo "Starting PostgreSQL..."
    docker start optimus-postgres 2>/dev/null || \
    docker run -d --name optimus-postgres \
        -e POSTGRES_PASSWORD=optimus123 \
        -e POSTGRES_DB=optimus_db \
        -p 5432:5432 \
        postgres:15
    sleep 3
fi

# Redis
if check_port 6379; then
    echo -e "${GREEN}✓ Redis already running${NC}"
else
    echo "Starting Redis..."
    docker start optimus-redis 2>/dev/null || \
    docker start redis 2>/dev/null || \
    docker run -d --name optimus-redis \
        -p 6379:6379 \
        redis:7-alpine
fi

echo ""
echo "🔧 Starting backend server..."

# Check if backend is already running
if check_port 8000; then
    echo -e "${YELLOW}⚠ Backend already running on port 8000${NC}"
else
    # Start backend
    if [ -f "venv/bin/python" ]; then
        echo "Starting FastAPI backend..."
        ./venv/bin/python run_backend.py > backend.log 2>&1 &
        BACKEND_PID=$!
        echo "Backend PID: $BACKEND_PID"
        
        # Wait for backend to be ready
        echo -n "Waiting for backend to start"
        for i in {1..10}; do
            if curl -s http://localhost:8000/docs > /dev/null; then
                echo ""
                echo -e "${GREEN}✓ Backend started successfully${NC}"
                break
            fi
            echo -n "."
            sleep 1
        done
    else
        echo -e "${RED}❌ Python virtual environment not found. Run setup first.${NC}"
        exit 1
    fi
fi

echo ""
echo "🎨 Starting frontend..."

# Check if frontend is already running
if check_port 3000; then
    echo -e "${YELLOW}⚠ Frontend already running on port 3000${NC}"
else
    if [ -d "frontend/node_modules" ]; then
        echo "Starting React frontend..."
        cd frontend
        npm run dev > ../frontend.log 2>&1 &
        FRONTEND_PID=$!
        cd ..
        echo "Frontend PID: $FRONTEND_PID"
        
        # Wait for frontend to be ready
        echo -n "Waiting for frontend to start"
        for i in {1..15}; do
            if curl -s http://localhost:3000 > /dev/null; then
                echo ""
                echo -e "${GREEN}✓ Frontend started successfully${NC}"
                break
            fi
            echo -n "."
            sleep 1
        done
    else
        echo -e "${YELLOW}⚠ Frontend dependencies not installed. Installing now...${NC}"
        cd frontend && npm install && npm run dev > ../frontend.log 2>&1 &
        FRONTEND_PID=$!
        cd ..
    fi
fi

echo ""
echo "============================================"
echo -e "${GREEN}✅ Optimus is running!${NC}"
echo "============================================"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔧 API Docs:  http://localhost:8000/docs"
echo "🗄️  Database: localhost:5432 (postgres/optimus123)"
echo "💾 Cache:    localhost:6379 (Redis)"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop Optimus:"
echo "   ./stop.sh"
echo ""
echo "🪸 CoralCollective AI Agents available:"
echo "   ./coral list"
echo ""
echo "Enjoy using Optimus! 🚀"