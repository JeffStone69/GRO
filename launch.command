#!/bin/bash
# XForge Trader - macOS Launcher (python3 explicit)

cd "$(dirname "$0")"

echo "============================================"
echo "🚀 XForge Trader Consolidated Starting..."
echo "============================================"

# Use python3 explicitly (macOS default)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ python3 not found. Please install Python 3."
    exit 1
fi

# Optional: Run cleanup first
read -p "Run repo cleanup before launch? (y/n): " choice
if [[ "$choice" =~ ^[Yy]$ ]]; then
    echo "🧹 Running cleanup..."
    $PYTHON_CMD repo_cleanup.py --reset-logs
fi

echo "🌐 Launching XForge Trader (Gradio UI)..."
$PYTHON_CMD launcher.py --clean

read -p "Press Enter to close this window..."