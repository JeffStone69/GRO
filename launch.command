#!/bin/bash
# XForge Trader v9.2 Beta – Silent macOS Launcher
# Completely hides the Terminal window

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Silent launch (no Terminal window appears)
osascript -e 'tell application "Terminal" to close (do script "cd '"$SCRIPT_DIR"' && python3 launcher.py; exit")' 2>/dev/null &

# Fallback: run in background with no output
python3 launcher.py > /dev/null 2>&1 &
