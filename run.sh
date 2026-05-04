#!/bin/bash
# ─────────────────────────────────────────────────────────
# CodeLens — Start Script
# Launches FastAPI backend + Streamlit frontend
# ─────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "🚀 Starting CodeLens..."
echo ""

# Start FastAPI backend in background
echo "⚙️  Backend → http://localhost:8000"
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

sleep 2  # Give backend a moment to start

# Start Streamlit frontend
echo "🌐 Frontend → http://localhost:8501"
streamlit run frontend/app.py --server.port 8501 --server.headless false

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null || true
