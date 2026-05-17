#!/usr/bin/env python3
# launcher.py - XForge Official Launcher (Consolidated Era)
# Starts cleanup → setup → consolidated xforge_trader.py

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
os.chdir(ROOT)

def run_command(cmd: list, desc: str):
    print(f"🚀 {desc}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print(f"⚠️  {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed {desc}: {e}")
        print(e.stderr)
        return False

def main():
    print("="*60)
    print("🚀 XForge Trader Consolidated Launcher")
    print("   Elite Self-Improving Quant Workstation")
    print("="*60)

    # 1. Cleanup
    if "--clean" in sys.argv or input("Run repo cleanup? (y/n): ").lower() == "y":
        run_command([sys.executable, "repo_cleanup.py", "--reset-logs"], "Repo Cleanup")

    # 2. Install / Update deps
    if "--install" in sys.argv:
        run_command([sys.executable, "-m", "pip", "install", "-e", "."], "Dependencies")

    # 3. Launch Consolidated App
    print("\n🌐 Launching XForge Trader (Gradio Multi-Tab UI)...")
    try:
        subprocess.run([
            sys.executable, 
            "xforge_trader.py", 
            "--host", "127.0.0.1", 
            "--port", "7860"
        ])
    except FileNotFoundError:
        print("❌ xforge_trader.py not found. Please ensure it's in the root.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested. Goodbye!")
    except Exception as e:
        print(f"💥 Launch error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()