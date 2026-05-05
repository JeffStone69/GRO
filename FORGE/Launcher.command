#!/bin/bash
# =============================================================================
# XForge Trader v8.0 - Official Launcher (macOS)
# =============================================================================

cd "$(dirname "$0")" || { echo "ERROR: Cannot access FORGE folder"; exit 1; }

echo "=== XForge Trader v8.0 - Reset & Launch ==="

# Full reset of broken files
rm -f xforge_self_improve.db xforge_trader.log xforge_historical.db
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Venv setup
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing / updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Fallback install for critical packages
pip install gradio yfinance pandas-ta plotly openai pydantic pillow requests --upgrade

echo "🚀 Launching XForge Trader v8.0..."
python3 launcher.py

exec "$SHELL"