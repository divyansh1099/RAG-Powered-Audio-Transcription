#!/bin/bash

# Start FastAPI backend
echo "🚀 Starting FastAPI backend on http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Wait a few seconds to ensure the backend starts before frontend
sleep 3

# Start Streamlit frontend
echo "🎙️ Starting Streamlit frontend on http://localhost:8501"
streamlit run app/app.py
