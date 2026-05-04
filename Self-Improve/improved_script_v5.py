#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from typing import Any, List, Tuple

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from openai import OpenAI
from plotly.subplots import make_subplots
from pydantic import BaseModel, Field, SecretStr

class TradingConfig(BaseModel):
    db_name: str = "xforge_self_improve.db"
    log_file: str = "xforge_trader.log"
    default_tickers: List[str] = Field(default_factory=lambda: ["TSLA", "AAPL", "MSFT", "NVDA"])
    openai_api_key: SecretStr = Field(default=SecretStr(""))

CONFIG = TradingConfig()
API_KEY_FILE = "xai_api_key.json"
API_KEY = ""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(CONFIG.log_file, mode="a"), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("xforge_trader")

@contextmanager
def db_connection():
    import sqlite3
    conn = sqlite3.connect(CONFIG.db_name)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with db_connection() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS errors (timestamp TEXT, section TEXT, error TEXT)""")
        conn.commit()

init_db()

def log_error(section: str, error: str):
    with db_connection() as conn:
        conn.execute("INSERT INTO errors (timestamp, section, error) VALUES (?, ?, ?)",
                     (datetime.now().isoformat(), section, error))
        conn.commit()
    logger.error(f"{section}: {error}")

def ensure_dependencies():
    required = ["gradio", "yfinance", "plotly", "openai", "pandas"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Installing missing packages: {missing}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade"] + missing)
            print("All dependencies installed successfully.")
        except Exception as e:
            print(f"Failed to install some packages: {e}")
            sys.exit(1)
    else:
        print("All dependencies are ready.")

def load_api_key():
    global API_KEY
    try:
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, "r") as f:
                data = json.load(f)
                API_KEY = data.get("api_key", "")
                if API_KEY:
                    CONFIG.openai_api_key = SecretStr(API_KEY)
    except Exception as e:
        logger.warning(f"Could not load API key from file: {e}")

def save_api_key(key: str):
    global API_KEY
    if not key or not key.strip():
        return "❌ API key cannot be empty."
    key = key.strip()
    if not key.startswith("gsk_") and len(key) < 20:
        return "⚠️ API key format looks invalid. xAI keys usually start with 'gsk_'."
    API_KEY = key
    CONFIG.openai_api_key = SecretStr(API_KEY)
    try:
        with open(API_KEY_FILE, "w") as f:
            json.dump({"api_key": API_KEY}, f)
        return "✅ Grok API key saved successfully and persisted!"
    except Exception as e:
        return f"❌ Failed to save key: {str(e)}"

@lru_cache(maxsize=100)
def cached_yf_download(ticker: str, period: str = "1y"):
    try:
        return yf.download(ticker.upper(), period=period, progress=False, auto_adjust=True)
    except Exception as e:
        log_error("YF Download", str(e))
        return pd.DataFrame()

def calculate_momentum(tickers_str: str = "TSLA", period: str = "1y"):
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
    results = []
    for ticker in tickers:
        data = cached_yf_download(ticker, period)
        if data.empty:
            continue
        close = data["Close"]
        ret = (close.iloc[-1] / close.iloc[0] - 1) * 100 if len(close) > 0 else 0
        results.append({"Ticker": ticker, "Return %": round(ret, 2)})
    df = pd.DataFrame(results)
    fig = go.Figure(go.Bar(x=df["Ticker"], y=df["Return %"], text=df["Return %"]))
    fig.update_layout(title="Momentum Scanner", height=400)
    return df, fig, f"Scanned {len(tickers)} tickers."

def self_improve():
    key = API_KEY or CONFIG.openai_api_key.get_secret_value()
    if not key:
        return "Please enter and save your xAI Grok API key in the Settings tab."
    try:
        client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": "Give one practical improvement suggestion for this trading scanner."}],
            max_tokens=500
        )
        return resp.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        log_error("Self-Improve", error_msg)
        if "403" in error_msg or "blocked" in error_msg.lower() or "permission" in error_msg.lower():
            return "Error: Your xAI API key is currently blocked or lacks permission. Please verify your account status on the xAI platform, ensure the key is active, or generate a new one."
        elif "401" in error_msg or "invalid" in error_msg.lower():
            return "Error: Invalid API key. Please check and re-enter your xAI Grok API key."
        else:
            return f"Grok API Error: {error_msg[:250]}"

def create_interface():
    with gr.Blocks(title="XForge Trader v8 - Grok Edition") as demo:
        gr.Markdown("# XForge Trader v8\nGrok-Powered Trading Scanner")
        
        with gr.Tab("Momentum Scanner"):
            tickers = gr.Textbox(value="TSLA,NVDA,AAPL", label="Tickers (comma separated)")
            period = gr.Dropdown(["1mo","3mo","6mo","1y"], value="1y", label="Period")
            btn = gr.Button("Run Momentum Scan", variant="primary")
            df_out = gr.Dataframe()
            plot_out = gr.Plot()
            summary_out = gr.Textbox()
            btn.click(calculate_momentum, inputs=[tickers, period], outputs=[df_out, plot_out, summary_out])

        with gr.Tab("Self-Improve (Grok)"):
            improve_btn = gr.Button("Ask Grok for Improvements", variant="primary")
            improve_out = gr.Textbox(lines=12, label="Grok Suggestions")
            improve_btn.click(self_improve, outputs=improve_out)

        with gr.Tab("Settings