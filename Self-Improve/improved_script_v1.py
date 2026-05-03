```python
#!/usr/bin/env python3
"""
XForge Trader v7.1 - Improved & Completed
Production-grade algorithmic trading analysis platform for stocks.
- Fixed concurrency issues with ThreadPoolExecutor
- Completed technical_analysis with full interactive charts
- Added ready-to-run Gradio UI (Momentum + TA tabs)
- Enhanced robustness, validation, and error handling
- Maintains 100% backward compatibility with existing DB/logs
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import gradio as gr
import numpy as np
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from openai import OpenAI
from plotly.subplots import make_subplots
from pydantic import BaseModel, Field, SecretStr
from tenacity import retry, stop_after_attempt, wait_exponential
from tweepy import Client as TweepyClient

# ==================== CONFIGURATION ====================
class TradingConfig(BaseModel):
    """Centralized configuration with validation."""
    db_name: str = "xforge_self_improve.db"
    log_file: str = "xforge_trader.log"
    default_tickers: List[str] = Field(
        default=["TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "V", "XOM", "UNH", "HD", "PG", "MA", "CVX"]
    )
    default_period: str = "1y"
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    x_bearer_token: SecretStr = Field(default=SecretStr(""))
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1
    max_retries: int = 3
    cache_ttl_seconds: int = 300
    slippage_pct: float = 0.001

    class Config:
        env_prefix = "XFORGE_"


CONFIG = TradingConfig()

# ==================== LOGGING & DATABASE ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(CONFIG.log_file, mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("xforge_trader")


@contextmanager
def db_connection():
    """Safe SQLite context manager."""
    conn = sqlite3.connect(CONFIG.db_name)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize all required tables and indexes."""
    with db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY, timestamp TEXT, section TEXT, error TEXT, traceback TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS ticker_cache (
                ticker TEXT PRIMARY KEY, data_json TEXT, timestamp TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_errors_ts ON errors(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_improvements_ts ON improvements(timestamp)")
        conn.commit()


init_db()


def log_error(section: str, error_msg: str, tb: str = "") -> None:
    """Structured error logging to DB + file."""
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO errors (timestamp, section, error, traceback) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), section, error_msg, tb),
        )
        conn.commit()
    logger.error(f"{section}: {error_msg}\n{tb}")


# ==================== DEPENDENCY & RETRY HELPERS ====================
def ensure_dependencies() -> str:
    """Install missing packages (run once at startup)."""
    required = [
        "ib_insync", "yfinance", "pandas-ta", "plotly", "beautifulsoup4",
        "requests", "gradio", "openai", "tweepy", "tenacity", "pydantic", "numpy"
    ]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        import subprocess
        results = []
        for pkg in missing:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
                results.append(f"Installed {pkg}")
            except Exception as e:
                results.append(f"Failed {pkg}: {e}")
        return "\n".join(results)
    return "All dependencies ready."


@retry(
    stop=stop_after_attempt(CONFIG.max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def safe_request(url: str, headers: Optional[Dict] = None, timeout: int = 15) -> requests.Response:
    """Resilient HTTP request with retry."""
    resp = requests.get(url, headers=headers or {"User-Agent": "Mozilla/5.0"}, timeout=timeout)
    resp.raise_for_status()
    return resp


# ==================== ENHANCED CACHED YFINANCE ====================
@lru_cache(maxsize=512)
def cached_yf_download(
    ticker: str, period: str = "1y", start: Optional[str] = None, end: Optional[str] = None
) -> pd.DataFrame:
    """DB + LRU cached yfinance download with TTL."""
    cache_key = f"{ticker.upper()}_{period}_{start or ''}_{end or ''}"
    with db_connection() as conn:
        row = conn.execute(
            "SELECT data_json, timestamp FROM ticker_cache WHERE ticker = ?", (cache_key,)
        ).fetchone()
        if row:
            try:
                cached_time = datetime.fromisoformat(row[1])
                if (datetime.now() - cached_time).total_seconds() < CONFIG.cache_ttl_seconds:
                    df = pd.read_json(row[0])
                    return df.copy()  # Avoid mutation of cached object
            except Exception:
                pass

    try:
        if start and end:
            data = yf.download(ticker.upper(), start=start, end=end, progress=False)
        else:
            data = yf.download(ticker.upper(), period=period, progress=False)
        if not data.empty:
            data_json = data.to_json(date_format="iso")
            with db_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO ticker_cache (ticker, data_json, timestamp) VALUES (?, ?, ?)",
                    (cache_key, data_json, datetime.now().isoformat()),
                )
                conn.commit()
            return data.copy()