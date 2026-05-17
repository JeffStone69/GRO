#!/usr/bin/env python3
"""
XForge Trader v9.2 Beta – Minimal Configuration Module
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "xforge_historical.db"
SIM_DB_PATH = BASE_DIR / "xforge_self_improve.db"

# API keys (loaded from environment or .env)
XAI_API_KEY = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

# Default Gradio settings
DEFAULT_SERVER_NAME = "127.0.0.1"
DEFAULT_SERVER_PORT = 7860
