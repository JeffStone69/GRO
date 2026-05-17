#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Starting XForge Trader..."
python3 launcher.py --clean
read -p "Press Enter to close..."