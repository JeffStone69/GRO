#!/usr/bin/env python3
# launcher.py - Minimal Clean Launcher

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

def main():
    py = sys.executable
    print("🚀 XForge Trader Clean Launch")
    
    if "--clean" in sys.argv:
        subprocess.run([py, "repo_cleanup.py"])
    
    print("🌐 Starting Gradio UI (all tabs active)...")
    subprocess.run([py, "xforge_trader.py"])

if __name__ == "__main__":
    main()