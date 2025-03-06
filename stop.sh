#!/bin/bash

echo "🛑 Stopping FastAPI backend on port 8000"
kill $(lsof -t -i:8000)

echo "🛑 Stopping Streamlit frontend on port 8501"
kill $(lsof -t -i:8501)
