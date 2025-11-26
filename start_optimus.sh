#!/bin/bash

echo "🤖 Welcome to Optimus - AI-Powered Development Platform"
echo "========================================================"
echo ""
echo "Optimus is equipped with CoralCollective's 20+ AI agents"
echo "for accelerated development."
echo ""
echo "Available Commands:"
echo ""
echo "1. Interactive Workflow:"
echo "   ./coral workflow"
echo ""
echo "2. Quick Agent Execution:"
echo "   ./coral agent backend_developer 'Build REST API'"
echo ""
echo "3. Fast Optimized Execution:"
echo "   ./coral_fast run backend_developer 'Create authentication'"
echo ""
echo "4. Parallel Agent Execution:"
echo "   ./coral_fast parallel 'backend:API' 'frontend:UI' 'database:Schema'"
echo ""
echo "5. Initialize Project Architecture:"
echo "   ./coral_fast init"
echo ""
echo "6. List All Agents:"
echo "   ./coral list"
echo ""
echo "What would you like to do? (Enter number 1-6):"
read choice

case $choice in
  1)
    ./coral workflow
    ;;
  2)
    echo "Enter agent ID (e.g., backend_developer):"
    read agent_id
    echo "Enter task description:"
    read task
    ./coral agent "$agent_id" "$task"
    ;;
  3)
    echo "Enter agent ID:"
    read agent_id
    echo "Enter task description:"
    read task
    ./coral_fast run "$agent_id" "$task"
    ;;
  4)
    echo "Running parallel agents..."
    ./coral_fast parallel 'backend:Create core API' 'frontend:Build dashboard' 'database:Design schema'
    ;;
  5)
    ./coral_fast init
    ;;
  6)
    ./coral list
    ;;
  *)
    echo "Invalid choice. Starting interactive workflow..."
    ./coral workflow
    ;;
esac