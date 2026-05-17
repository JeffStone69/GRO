#!/usr/bin/env python3
# repo_cleanup.py - FINAL Aggressive Cleanup (Zero Bloat Mode)

import shutil
from pathlib import Path

ROOT = Path(__file__).parent

KEEP = {
    ".git", ".github", ".env", ".gitignore", ".gitattributes",
    "xforge_trader.py", "launcher.py", "launch.command", "repo_cleanup.py",
    "requirements.txt", "pyproject.toml", "README.md", "readme.md",
    "SMI-LOGO.jpeg", "logo.jpg", "xforge_history.db", "xforge.log"
}

def clean():
    print("🧹 Starting ZERO-BLOAT cleanup...")
    removed = 0
    
    for item in ROOT.iterdir():
        if item.name in KEEP or item.name.startswith("."):
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                print(f"🗑️  Removed folder: {item.name}")
            else:
                item.unlink(missing_ok=True)
                print(f"🗑️  Removed file: {item.name}")
            removed += 1
        except Exception as e:
            print(f"⚠️  Skip {item.name}: {e}")
    
    print(f"\n✅ Cleanup complete. {removed} items removed.")
    print("Final structure: Only core files + .git + logos + DBs")

if __name__ == "__main__":
    confirm = input("This will DELETE Modules/, core/, and all old files. Type YES to continue: ")
    if confirm == "YES":
        clean()
    else:
        print("Aborted.")