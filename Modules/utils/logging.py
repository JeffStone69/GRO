#!/usr/bin/env python3
"""
XForge Trader v9.2 Beta – Centralized Logging Module
Logs all events to daily files + console for beta testing
"""
import logging
from pathlib import Path
from datetime import datetime

def setup_logging(name: str = "XForge"):
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"xforge_events_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)
