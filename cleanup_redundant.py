#!/usr/bin/env python3
"""
XForge Trader v9.2 – Cleanup Redundant Files Script
Run this from the repository root to remove duplicates and nested copies.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
FORGE = ROOT / "FORGE"

print("🧹 Starting cleanup of redundant files...\n")

# Files/folders to delete inside FORGE/
to_remove = [
    FORGE / "launcher.py",
    FORGE / "launch.command",
    FORGE / "run_xforge.command",
    FORGE / ".gitattributes",
    FORGE / ".gitignore",
    FORGE / ".github",
    FORGE / "modules",
    FORGE / "Self-Improve",
    FORGE / "SMI-LOGO.jpeg",
]

for item in to_remove:
    if item.exists():
        if item.is_dir():
            shutil.rmtree(item)
            print(f"🗑️  Removed directory: {item.relative_to(ROOT)}")
        else:
            item.unlink()
            print(f"🗑️  Removed file: {item.relative_to(ROOT)}")
    else:
        print(f"✅ Already clean: {item.relative_to(ROOT)}")

print("\n✅ Cleanup complete!")
print("Recommended next steps:")
print("1. Delete any remaining duplicate files in root if you want (e.g. run_xforge.command)")
print("2. Run: git add . && git commit -m 'chore: clean up redundant files and nested folders'")
print("3. git push")
