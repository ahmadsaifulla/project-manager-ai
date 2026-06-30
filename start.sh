#!/bin/bash

echo "==========================================="
echo " Starting Dockerized Backend Cluster       "
echo "==========================================="

# The public port for the orchestrator provided by the host (Render/Railway defaults)
# Default to 8000 if not provided
ORCHESTRATOR_PORT=${PORT:-8000}

echo "🚀 Booting Chatbot Node (Internal Port 8001)..."
# Start chatbot node in the background
cd /app/services/chatbot && PROJECT_BASE_DIR="/app/workspace" uvicorn app.main:app --host 127.0.0.1 --port 8001 &

echo "🚀 Booting Developer Node (Internal Port 8002)..."
# Start developer node in the background
cd /app/services/developer && PROJECT_BASE_DIR="/app/workspace" uvicorn app.main:app --host 127.0.0.1 --port 8002 &

echo "🚀 Booting Orchestrator API Gateway (Public Port $ORCHESTRATOR_PORT)..."
# Start orchestrator in the foreground, binding to 0.0.0.0 so it's accessible externally
cd /app/services/orchestrator && uvicorn app.main:app --host 0.0.0.0 --port $ORCHESTRATOR_PORT
