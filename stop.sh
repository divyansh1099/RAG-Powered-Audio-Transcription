#!/bin/bash

echo "🛑 Stopping FastAPI backend on port 8000"
kill $(lsof -t -i:8000) 2>/dev/null || echo "Port 8000 already free."

echo "🛑 Stopping Streamlit frontend on port 8501"
kill $(lsof -t -i:8501) 2>/dev/null || echo "Port 8501 already free."

echo "🧼 Cleaning up lingering Whisper/multiprocessing jobs"
pkill -f "multiprocessing.spawn" 2>/dev/null || echo "No Whisper subprocesses found."

echo "🧼 Killing orphaned uvicorn processes (if any)"
pkill -f "uvicorn" 2>/dev/null || echo "No uvicorn process found."

echo "✅ All services stopped cleanly."
