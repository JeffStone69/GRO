#!/bin/bash
# Finder-launchable macOS command file
# Double-click in Finder to launch with splash screen
cd "$(dirname "$0")"
chmod +x launcher.py
python3 launcher.py
