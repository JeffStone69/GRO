#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    py = sys.executable
    if "--clean" in sys.argv:
        subprocess.run([py, "repo_cleanup.py", "--reset-logs"])
    subprocess.run([py, "xforge_trader.py"])