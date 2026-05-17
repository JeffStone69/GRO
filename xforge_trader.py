#!/usr/bin/env python3
# xforge_trader.py - XForge Trader Consolidated Superscript (Production v3.1)
# Single-file master app with shared DBs, live updates, and Gradio tabs

import argparse
import sqlite3
import logging
import threading
import time
import sys
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import gradio as gr

# ========================= CONFIG =========================
ROOT = Path(__file__).parent
DB_HISTORY = ROOT / "xforge_history.db"
LOG_FILE = ROOT / "xforge.log"

DEFAULT_TICKERS = ["TSLA", "AAPL", "NVDA", "GOOGL", "MSFT"]

# ========================= LOGGING =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("XForge")

# ========================= DB =========================
class XForgeDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_HISTORY)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS price_history (
                ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                PRIMARY KEY (ticker, date)
            );
        """)
        self.conn.commit()

    def backfill(self, tickers):
        for t in tickers:
            try:
                df = yf.download(t, period="2y", progress=False)
                for _, row in df.iterrows():
                    self.conn.execute("INSERT OR REPLACE INTO price_history VALUES (?,?,?,?,?,?,?)",
                        (t, row.name.strftime("%Y-%m-%d"), float(row['Open']), float(row['High']),
                         float(row['Low']), float(row['Close']), int(row['Volume'])))
                self.conn.commit()
                logger.info(f"Backfilled {t}")
            except Exception as e:
                logger.error(f"Backfill error {t}: {e}")

db = XForgeDB()

# ========================= LIVE THREAD =========================
live_data = {"tickers": {}, "last_update": ""}

def live_update_loop():
    while True:
        try:
            for t in DEFAULT_TICKERS:
                data = yf.Ticker(t).info
                live_data["tickers"][t] = {
                    "price": data.get("regularMarketPrice") or data.get("currentPrice"),
                    "change": data.get("regularMarketChangePercent")
                }
            live_data["last_update"] = datetime.now().strftime("%H:%M:%S")
            time.sleep(30)
        except:
            time.sleep(60)

threading.Thread(target=live_update_loop, daemon=True).start()

# ========================= TABS =========================
def dashboard():
    lines = [f"{t}: ${d.get('price')} ({d.get('change'):+.2f}%)" for t, d in live_data["tickers"].items()]
    return "\n".join(lines) + f"\n\nLast update: {live_data['last_update']}"

def backfill_tab(tickers_str):
    tickers = [x.strip().upper() for x in tickers_str.split(",")]
    db.backfill(tickers)
    return "✅ Backfill complete. Check logs."

def sim_tab(prompt):
    return f"🧠 Self-improvement triggered with prompt:\n{prompt}\n\n(Real xAI integration coming next iteration)"

# ========================= GRADIO UI =========================
with gr.Blocks(title="XForge Trader", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🚀 XForge Trader • Consolidated")
    with gr.Tabs():
        with gr.Tab("📊 Live Dashboard"):
            gr.Textbox(label="Live Prices", value=dashboard, every=5)
            gr.Button("Refresh").click(dashboard, outputs=gr.Textbox(label="Live Prices"))
        
        with gr.Tab("📥 Backfill Data"):
            t_input = gr.Textbox(value="TSLA,AAPL,NVDA", label="Tickers (comma separated)")
            gr.Button("Backfill").click(backfill_tab, inputs=t_input, outputs=gr.Textbox())
        
        with gr.Tab("🧠 Self-Improvement"):
            prompt = gr.Textbox(lines=3, placeholder="Optimize momentum strategy...")
            gr.Button("Run SIM").click(sim_tab, inputs=prompt, outputs=gr.Textbox())
        
        with gr.Tab("📜 Logs"):
            gr.Textbox(label="Recent Logs", value=lambda: Path(LOG_FILE).read_text()[-3000:] if Path(LOG_FILE).exists() else "No logs", lines=20)

app.launch(server_name="127.0.0.1", server_port=7860, share=False)