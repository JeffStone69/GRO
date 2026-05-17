#!/usr/bin/env python3
# cleanup_init.py - Elite Target Directory Cleanup for XForge Initialisation
# Safe, configurable, dry-run supported. Preserves: .env, *.py, *.md, logos, DBs (optional reset)

import argparse
import shutil
import sys
from pathlib import Path
from typing import List

# ========================= CONFIG =========================
ROOT_DIR = Path(__file__).parent
PRESERVE_PATTERNS = {".env", ".git", ".github", "FORGE", "Self-Improve", "*.py", "*.md", "*.toml", "*.txt", "SMI-LOGO.jpeg", "logo.jpg", "launch.command"}
RESET_DBS = False  # Set True to nuke history/unified DBs on full reset
DRY_RUN = False

CLEAN_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    "**/.pytest_cache",
    "**/.coverage",
    "**/htmlcov",
    "**/*.egg-info",
    "**/build",
    "**/dist",
    "**/*.log",          # xforge.log, XForge_Beta.log etc.
    "**/*.db" if RESET_DBS else None,  # Conditional
    "**/.DS_Store",
    "**/tmp",
    "**/temp",
]

def should_preserve(path: Path) -> bool:
    """Check against preserve list."""
    name = path.name
    for pat in PRESERVE_PATTERNS:
        if pat.startswith("*") and name.endswith(pat[1:]):
            return True
        if name == pat or path.match(pat):
            return True
    return False

def cleanup() -> List[str]:
    removed = []
    for pattern in CLEAN_PATTERNS:
        if not pattern:
            continue
        for item in ROOT_DIR.glob(pattern):
            if should_preserve(item):
                continue
            try:
                if DRY_RUN:
                    print(f"[DRY] Would remove: {item}")
                    removed.append(str(item))
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                removed.append(str(item))
                print(f"🗑️  Removed: {item}")
            except Exception as e:
                print(f"⚠️  Failed {item}: {e}")
    return removed

# ========================= CLI =========================
def main():
    global DRY_RUN, RESET_DBS
    parser = argparse.ArgumentParser(description="XForge Target Directory Cleanup for Init")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--reset-dbs", action="store_true", help="Also delete .db files")
    parser.add_argument("--target", type=str, default=".", help="Target subdir (default root)")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    RESET_DBS = args.reset_dbs
    target = ROOT_DIR / args.target

    print(f"🚀 XForge Cleanup Init — Target: {target} | Dry-run: {DRY_RUN} | Reset DBs: {RESET_DBS}")
    removed = cleanup()
    
    print(f"\n✅ Cleanup complete. {len(removed)} items processed.")
    if DRY_RUN:
        print("💡 Run without --dry-run to execute.")
    else:
        print("🔄 Ready for: python setup.py  (or launcher.py)")

if __name__ == "__main__":
    main()