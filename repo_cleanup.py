#!/usr/bin/env python3
# repo_cleanup.py - Elite Repo-Wide Cleanup Utility for XForge/GRO
# Production-safe: Preserves ALL source, configs, DBs (opt-in reset), logos, .git
# Analyzed against launcher.py, SIM.py, xforge_trader.py, Modules structure

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Set

# ========================= CONFIG =========================
ROOT_DIR = Path(__file__).parent
PRESERVE_PATTERNS: Set[str] = {
    ".env", ".git", ".github", "Modules", "core", "FORGE", "Self-Improve", "utils",
    "*.py", "*.md", "*.toml", "*.txt", "*.command", "*.sh",
    "SMI-LOGO.jpeg", "logo.jpg", "LOGO-SIM.jpeg", "SIM-LOGO.jpeg",
    "pyproject.toml", "requirements.txt", ".gitignore", ".gitattributes",
    "PROJECT_BLUEPRINT.md", "README.md", "readme.md"
}

# Default: PROTECT user data
RESET_DBS = False      # --reset-dbs to enable
RESET_LOGS = False     # --reset-logs
DRY_RUN = False

CLEAN_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc", "**/*.pyo", "**/*.pyd",
    "**/.pytest_cache", "**/.coverage", "**/htmlcov",
    "**/*.egg-info", "**/build", "**/dist",
    "**/.DS_Store",
    "**/tmp", "**/temp",
    # Conditional
    "**/*.log" if False else None,           # controlled by flag
    "**/*.db" if False else None,            # controlled by flag
    "data/__pycache__", "logs/__pycache__",
]

def should_preserve(path: Path) -> bool:
    """Robust preservation check."""
    if any(p in str(path) for p in [".git", ".env"]):
        return True
    name = path.name
    for pat in PRESERVE_PATTERNS:
        if pat.startswith("*") and name.endswith(pat[1:]):
            return True
        if name == pat or path.match(pat) or any(d in path.parts for d in ["Modules", "core"]):
            return True
    return False

def cleanup() -> List[str]:
    removed = []
    for pattern in CLEAN_PATTERNS:
        if not pattern:
            continue
        for item in ROOT_DIR.glob(pattern):
            if should_preserve(item) or item == Path(__file__):
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
    global DRY_RUN, RESET_DBS, RESET_LOGS
    parser = argparse.ArgumentParser(description="XForge/GRO Repo Cleanup Utility")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--reset-dbs", action="store_true", help="Delete ALL .db files (history data)")
    parser.add_argument("--reset-logs", action="store_true", help="Delete log files")
    parser.add_argument("--target", type=str, default=".", help="Target subdir")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    RESET_DBS = args.reset_dbs
    RESET_LOGS = args.reset_logs

    # Dynamic patterns
    global CLEAN_PATTERNS
    if RESET_LOGS:
        CLEAN_PATTERNS = [p for p in CLEAN_PATTERNS if p] + ["**/*.log"]
    if RESET_DBS:
        CLEAN_PATTERNS = [p for p in CLEAN_PATTERNS if p] + ["**/*.db"]

    target = ROOT_DIR / args.target
    print(f"🚀 XForge Repo Cleanup — Target: {target} | Dry-run: {DRY_RUN} | Reset DBs: {RESET_DBS} | Reset Logs: {RESET_LOGS}")
    print("⚠️  Source code, .env, Modules/, images, and .git are ALWAYS protected.")

    removed = cleanup()
    
    print(f"\n✅ Cleanup complete. {len(removed)} items processed.")
    if DRY_RUN:
        print("💡 Run without --dry-run to execute.")
    else:
        print("🔄 Repo is clean. Ready for: python -m pip install -e . && python launcher.py")

if __name__ == "__main__":
    main()