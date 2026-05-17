#!/usr/bin/env python3
"""
XForge Trader v9.2 Beta – Database Connection Utility
"""
import sqlite3
from pathlib import Path

def get_connection(db_name: str = "xforge_historical.db"):
    """Return a connection to the specified SQLite database."""
    db_path = Path(__file__).parent.parent / db_name
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
