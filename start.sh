#!/bin/bash

# Go to the project root directory
cd /Users/divyanshgupta/MSIT/AP1 || exit 1

# Start FastAPI backend
echo "🚀 Starting FastAPI backend on http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Wait for backend to be ready
sleep 3

# Start Streamlit frontend
echo "🎙️ Starting Streamlit frontend on http://localhost:8501"
streamlit run app/home.py
