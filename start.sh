#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting PayRoute AI Production Services"
echo "=========================================================="

# 1. Resolve Project Root Directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-detect if project files are inside a nested subfolder (e.g. payroute-ai/)
if [ ! -d "api" ]; then
    if [ -d "payroute-ai/api" ]; then
        echo "-> [Notice] Found nested payroute-ai/ directory. Entering payroute-ai..."
        cd payroute-ai
    else
        FOUND_DIR=$(find . -maxdepth 3 -type d -name "api" 2>/dev/null | head -n 1)
        if [ -n "$FOUND_DIR" ]; then
            TARGET_DIR=$(dirname "$FOUND_DIR")
            echo "-> [Notice] Located API package in $TARGET_DIR. Switching directory..."
            cd "$TARGET_DIR"
        fi
    fi
fi

PROJECT_ROOT="$(pwd)"
echo "-> Working directory: $PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# 2. Initialize Database Schema
echo "-> [1/3] Initializing Database Schema..."
if [ -f "database/init_db.py" ]; then
    python database/init_db.py || true
else
    echo "-> Notice: database/init_db.py not found at $PROJECT_ROOT, utilizing auto-schema bootstrap."
fi

# 3. Start FastAPI Backend in background
echo "-> [2/3] Launching FastAPI Backend on 0.0.0.0:8000..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 4. Wait for FastAPI backend to respond
echo "-> Waiting for backend to respond..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health | grep -q '"status":"healthy"'; then
        echo "✓ FastAPI Backend is healthy and ready!"
        break
    fi
    sleep 1
done

# 5. Start Streamlit Frontend
echo "-> [3/3] Launching Streamlit Customer Shield Dashboard on port ${PORT:-8501}..."
export PAYROUTE_API_URL="http://localhost:8000"
python -m streamlit run dashboard/app.py \
    --server.port ${PORT:-8501} \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false &
STREAMLIT_PID=$!

# Trap termination signals for graceful shutdown
trap 'echo "Stopping PayRoute AI..."; kill $BACKEND_PID $STREAMLIT_PID 2>/dev/null || true; exit 0' SIGTERM SIGINT

# Wait for background processes
wait -n $BACKEND_PID $STREAMLIT_PID
