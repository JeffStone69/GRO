#!/usr/bin/env python3
# launcher.py - Clean XForge Launcher

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
print(f"🚀 XForge Launcher starting from: {ROOT}")

def main():
    py = sys.executable

    # Optional cleanup
    if "--clean" in sys.argv:
        subprocess.run([py, "repo_cleanup.py", "--reset-logs"])

    print("🌐 Launching XForge Trader Gradio UI...")
    try:
        subprocess.run([py, "xforge_trader.py"])
    except KeyboardInterrupt:
        print("👋 Shutdown.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()