#!/bin/bash
cd "$(dirname "$0")"

# Activate your virtual environment (adjust path if needed)
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "⚠️ venv not found — using system Python"
fi

echo "🚀 Starting XForge Trader v8.0 from Finder..."
python3 launcher.py
