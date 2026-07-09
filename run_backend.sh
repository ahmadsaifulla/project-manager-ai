#!/bin/bash

echo "==========================================="
echo " Starting Project Manager Backend Cluster  "
echo "==========================================="

# Function to clean up background processes on exit
cleanup() {
    echo -e "\n🛑 SIGINT/SIGTERM caught. Shutting down all backend nodes..."
    # Kill all background jobs started by this script
    kill $(jobs -p) 2>/dev/null
    wait $(jobs -p) 2>/dev/null
    echo "✅ All nodes shut down gracefully."
    exit
}

# Trap termination signals
trap cleanup SIGINT SIGTERM

export PYTHONPATH=$(pwd)

echo "🚀 Booting Orchestrator Node (Port 8000)..."
./services/orchestrator/venv/bin/uvicorn services.orchestrator.app.main:app --host 127.0.0.1 --port 8000 --reload &

echo "🚀 Booting Chatbot Node (Port 8001)..."
PROJECT_BASE_DIR="workspace" ./services/chatbot/venv/bin/uvicorn services.chatbot.app.main:app --host 127.0.0.1 --port 8001 --reload &

echo "🚀 Booting Developer Node (Port 8002)..."
PROJECT_BASE_DIR="workspace" ./services/developer/venv/bin/uvicorn services.developer.app.main:app --host 127.0.0.1 --port 8002 --reload &

echo -e "\n🟢 Backend Cluster is online! Press Ctrl+C to terminate."
echo "--------------------------------------------------------"

# Keep the script running to catch signals and keep processes alive in background
wait
