#!/bin/bash
# XForge Trading Script - Single File Launcher for Apple macOS
# Version incorporating all chat history updates and fixes as of May 2026:
# - Full Gradio UI with restored tabs: Profit Scanner, Technical Chart, Backtester, Forward Walking Predictor, Grok + Self-Improve, IBKR Integration, Strategy Optimizer & Paper Trader
# - Real-time data feeds, dynamic tab loading, lazy IBKR imports (ib_insync, eventkit)
# - Grok xAI API integration with key support via .env
# - Plotly dependency fix (no 'lotly' typo)
# - Enhanced database handling (xforge_historical.db, xforge_self_improve.db)
# - Self-improvement logging, error reports, DEVELOPMENT_HISTORY.md tracking
# - Virtual environment setup, dependency management from requirements.txt
# - Clean installation: rewrites directory structure, regenerates data files, removes broken caches
#
# This launcher ensures a clean, fresh installation every time it is executed.
# Double-click in Finder or run via Terminal: open launch.command

echo "XForge Trading Script Launcher - Clean Installation Mode"
echo "Executing at: $(date -u)"

# Set working directory to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo "Repository root set to: $SCRIPT_DIR"

# Rewrite directory structure for standardized clean installation
echo "Rewriting directory structure..."
mkdir -p FORGE/data FORGE/logs FORGE/modules FORGE/Export FORGE/.github/workflows

# Ensure essential files are present (repo clone assumed)
if [ ! -d "FORGE" ]; then
  echo "Error: FORGE directory not found. Please clone the full repository first."
  exit 1
fi

# Clean up broken or temporary files for fresh state
echo "Cleaning temporary and broken files..."
rm -rf venv __pycache__ "FORGE/__pycache__" "FORGE/*.pyc" "*.log" "FORGE/*.log" 2>/dev/null || true

# Regenerate required data files (backup DB if exists, recreate fresh structure)
if [ -f "FORGE/xforge_historical.db" ]; then
  mv "FORGE/xforge_historical.db" "FORGE/xforge_historical.db.bak" 2>/dev/null || true
  echo "Backed up and regenerating historical database for clean install."
fi
if [ -f "FORGE/xforge_self_improve.db" ]; then
  mv "FORGE/xforge_self_improve.db" "FORGE/xforge_self_improve.db.bak" 2>/dev/null || true
  echo "Backed up self-improvement database."
fi
# Create fresh empty DB placeholders (Python script will populate schema on launch)
touch "FORGE/xforge_historical.db" "FORGE/xforge_self_improve.db" || true
echo "Data files regenerated for clean XForge installation."

# Setup virtual environment
echo "Creating clean Python virtual environment..."
rm -rf venv 2>/dev/null || true
python3 -m venv venv --clear
if [ $? -ne 0 ]; then
  echo "Error: Virtual environment creation failed. Verify Python 3.10+ is installed via 'python3 --version'."
  exit 1
fi
source venv/bin/activate
echo "Virtual environment activated."

# Install dependencies
echo "Installing and updating required packages with latest fixes..."
pip install --upgrade pip setuptools wheel
if [ -f "FORGE/requirements.txt" ]; then
  pip install -r FORGE/requirements.txt --upgrade
  echo "Installed from requirements.txt (includes latest: gradio, ib_insync, plotly, python-dotenv, etc.)."
else
  echo "Warning: requirements.txt missing. Installing core packages from history..."
  pip install gradio pandas numpy yfinance plotly ib_insync python-dotenv requests scipy matplotlib streamlit
fi

# Launch the main XForge script
echo "Launching XForge Trading script with all incorporated updates..."
MAIN_SCRIPT="FORGE/xforge_trader.py"
if [ -f "$MAIN_SCRIPT" ]; then
  python "$MAIN_SCRIPT"
elif [ -f "FORGE/launcher.py" ]; then
  python "FORGE/launcher.py"
else
  echo "Error: Core XForge script (xforge_trader.py or launcher.py) not found in FORGE/."
  echo "Please ensure full repository clone and retry."
  exit 1
fi

# Cleanup
deactivate

echo ""
echo "XForge Trading script execution completed."
echo "For repeated clean installs, re-execute this launch.command file."
echo "Grok xAI API key: Ensure .env file exists in root with GROK_API_KEY=sk-... for full self-improve and chat features."
echo "IBKR TWS: Ensure Trader Workstation is running with API enabled on port 7496/7497 as per previous setup instructions."