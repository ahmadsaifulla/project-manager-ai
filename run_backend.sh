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

echo "🚀 Booting Orchestrator Node (Port 8000)..."
(cd services/orchestrator && source venv/bin/activate && uvicorn app.main:app --port 8000 --reload) &

echo "🚀 Booting Chatbot Node (Port 8001)..."
(cd services/chatbot && source venv/bin/activate && PROJECT_BASE_DIR="../../workspace" uvicorn app.main:app --port 8001 --reload) &

echo "🚀 Booting Developer Node (Port 8002)..."
(cd services/developer && source venv/bin/activate && PROJECT_BASE_DIR="../../workspace" uvicorn app.main:app --port 8002 --reload) &

echo -e "\n🟢 Backend Cluster is online! Press Ctrl+C to terminate."
echo "--------------------------------------------------------"

# Keep the script running to catch signals and keep processes alive in background
wait
