# ============================================================
# cleanup_forge.py — Smart Directory Cleanup Module v1
# Analyses clutter, logs valuable assets/data to DB, removes non-essentials
# Call this from xforge_trader.py or run standalone
# ============================================================

from pathlib import Path
import sqlite3
from datetime import datetime
import shutil
import os

DB_PATH = Path("xforge_self_improve.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS error_reports (
            id INTEGER PRIMARY KEY, timestamp TEXT, tab TEXT, ticker TEXT, description TEXT
        );
        CREATE TABLE IF NOT EXISTS improvements (
            id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT
        );
        CREATE TABLE IF NOT EXISTS stock_data (
            id INTEGER PRIMARY KEY, ticker TEXT, timestamp TEXT, open REAL, high REAL,
            low REAL, close REAL, volume INTEGER, source TEXT,
            UNIQUE(ticker, timestamp)
        );
    """)
    conn.commit()
    conn.close()

init_db()

def log_cleanup(message):
    """Log valuable assets or removal actions into the improvements table."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)",
                 (datetime.now().isoformat(), f"[CLEANUP v1] {message}"))
    conn.commit()
    conn.close()

def run_cleanup():
    """Main cleanup function — safe, logged, and reversible in spirit."""
    base = Path(".")
    removed = []
    valuable = []

    # 1. Recursively remove all .DS_Store (macOS clutter)
    for ds in base.rglob(".DS_Store"):
        try:
            ds.unlink()
            removed.append(str(ds.relative_to(base)))
        except Exception as e:
            pass

    # 2. Remove old superseded script (valuable code already in current version)
    old_script = base / "xforge_trader.old.py"
    if old_script.exists():
        valuable.append(
            "Archived xforge_trader.old.py — contained full modular v7 Gradio app, "
            "self-improvement loop, Grok prompts, IBKR lazy import, error logging system, "
            "and complete scanner/backtester logic."
        )
        old_script.unlink()
        removed.append("xforge_trader.old.py")

    # 3. Prune old backup subfolders (keep only the 3 most recent)
    backups_dir = base / "backups"
    if backups_dir.exists():
        backup_folders = sorted(
            [f for f in backups_dir.iterdir() if f.is_dir()],
            key=lambda x: x.stat().st_mtime, reverse=True
        )
        for old_bak in backup_folders[3:]:
            valuable.append(f"Archived & removed old backup: {old_bak.name}")
            try:
                shutil.rmtree(old_bak)
                removed.append(str(old_bak.relative_to(base)))
            except Exception:
                pass

    # 4. Remove empty versions/ folder
    versions_dir = base / "versions"
    if versions_dir.exists() and not any(versions_dir.iterdir()):
        versions_dir.rmdir()
        removed.append("versions/ (empty folder)")

    # 5. Log everything to the main DB
    for v in valuable:
        log_cleanup(v)
    if removed:
        log_cleanup(f"Removed clutter items: {', '.join(removed)}")

    # Final summary
    summary = "✅ Cleanup complete!\n\n"
    if removed:
        summary += f"🗑️ Removed: {', '.join(removed)}\n\n"
    if valuable:
        summary += "📜 Valuable assets logged to DB:\n" + "\n".join(valuable) + "\n\n"
    summary += "Essential files/folders now only:\n"
    summary += "• xforge_trader.py, multi_tws_connector.py\n"
    summary += "• requirements.txt, Run-xForgeTrader.command\n"
    summary += "• README.md, DEVELOPMENT_HISTORY.md, xforge_self_improve.db\n"
    summary += "• .gitattributes, .gitignore\n"
    summary += "• Folders: .gradio, backups, data_cache (if present)\n"

    return summary
