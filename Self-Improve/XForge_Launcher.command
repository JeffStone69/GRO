#!/bin/bash

# ============================================================
# XForge Self-Improvement - macOS Double-Click Launcher
# Futuristic & Secure
# ============================================================

# Get the directory where this .command file lives
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Clear terminal and show futuristic header
clear
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    X F O R G E                               ║"
echo "║              Self-Improvement Module                         ║"
echo "║                   macOS Launcher                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Starting secure environment..."
echo ""

# Run the Python launcher (this handles splash, API key, dependencies & SIM.py)
python3 XForge_Launcher.py

# Keep the window open after completion so user can see any messages
echo ""
echo "✅ XForge session finished."
echo "   You can close this Terminal window."
echo ""
read -n 1 -s -r -p "Press any key to close..."
