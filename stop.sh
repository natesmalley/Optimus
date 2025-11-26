#!/bin/bash

# Optimus Project Orchestrator - Stop Script
# ==========================================

echo "🛑 Stopping Optimus Project Orchestrator..."
echo "==========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Stop backend
echo "Stopping backend..."
if pgrep -f "run_backend.py" > /dev/null; then
    pkill -f "run_backend.py"
    echo -e "${GREEN}✓ Backend stopped${NC}"
else
    echo -e "${YELLOW}Backend was not running${NC}"
fi

# Stop frontend
echo "Stopping frontend..."
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null; then
    kill $(lsof -Pi :3000 -sTCP:LISTEN -t) 2>/dev/null
    echo -e "${GREEN}✓ Frontend stopped${NC}"
else
    echo -e "${YELLOW}Frontend was not running${NC}"
fi

# Optional: Stop databases (uncomment if you want to stop databases too)
read -p "Stop databases too? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping PostgreSQL..."
    docker stop optimus-postgres 2>/dev/null
    echo -e "${GREEN}✓ PostgreSQL stopped${NC}"
    
    echo "Stopping Redis..."
    docker stop optimus-redis 2>/dev/null || docker stop redis 2>/dev/null
    echo -e "${GREEN}✓ Redis stopped${NC}"
fi

echo ""
echo -e "${GREEN}✅ Optimus has been stopped${NC}"
echo ""
echo "To restart: ./start.sh"