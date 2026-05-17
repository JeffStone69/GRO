#!/usr/bin/env python3
# xforge_trader.py - XForge Trader Consolidated (v3.2) with Charts & Options

import argparse
import sqlite3
import logging
import threading
import time
import sys
import webbrowser
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import gradio as gr
import plotly.graph_objects as go

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
                df = yf.download(t, period="1y", progress=False)
                for idx, row in df.iterrows():
                    self.conn.execute("INSERT OR REPLACE INTO price_history VALUES (?,?,?,?,?,?,?)",
                        (t, idx.strftime("%Y-%m-%d"), float(row['Open']), float(row['High']),
                         float(row['Low']), float(row['Close']), int(row['Volume'])))
                self.conn.commit()
                logger.info(f"✅ Backfilled {t}")
            except Exception as e:
                logger.error(f"Backfill {t}: {e}")

db = XForgeDB()

# ========================= LIVE DATA =========================
live_data = {"tickers": {}, "last_update": ""}

def live_update_loop():
    while True:
        try:
            for t in DEFAULT_TICKERS:
                tk = yf.Ticker(t)
                info = tk.info
                live_data["tickers"][t] = {
                    "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                    "change": info.get("regularMarketChangePercent")
                }
            live_data["last_update"] = datetime.now().strftime("%H:%M:%S")
            time.sleep(30)
        except:
            time.sleep(60)

threading.Thread(target=live_update_loop, daemon=True).start()

# ========================= CHARTS & OPTIONS =========================
def get_candlestick(ticker="TSLA"):
    df = yf.download(ticker, period="3mo", interval="1d", progress=False)
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='green', decreasing_line_color='red'
    )])
    fig.update_layout(title=f"{ticker} Candlestick Chart", xaxis_title="Date", yaxis_title="Price", height=600)
    return fig

def get_options_chain(ticker="TSLA"):
    try:
        tk = yf.Ticker(ticker)
        expirations = tk.options[:3]
        chains = []
        for exp in expirations:
            opt = tk.option_chain(exp)
            calls = opt.calls[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest']].head(10)
            puts = opt.puts[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest']].head(10)
            chains.append(f"### {exp}\n**Calls:**\n{calls.to_string(index=False)}\n\n**Puts:**\n{puts.to_string(index=False)}\n---")
        return "\n\n".join(chains)
    except Exception as e:
        return f"Options data unavailable: {e}"

# ========================= GRADIO UI =========================
with gr.Blocks(title="XForge Trader", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🚀 **XForge Trader** — Consolidated Self-Improving Quant Platform")
    gr.Markdown("**Live • Interactive Charts • Options Chain • Self-Improvement**")

    with gr.Tabs():
        with gr.Tab("📊 Live Dashboard"):
            gr.Markdown("### Real-time Prices & Interactive Candlestick")
            with gr.Row():
                ticker_select = gr.Dropdown(DEFAULT_TICKERS, value="TSLA", label="Select Ticker")
                refresh_btn = gr.Button("🔄 Refresh All", variant="primary")
            live_text = gr.Textbox(label="Live Prices", lines=8)
            chart = gr.Plot(label="Candlestick Chart")
            
            def refresh_dashboard(tkr):
                prices = "\n".join([f"{t}: ${d.get('price')} ({d.get('change'):+.2f}%)" 
                                  for t, d in live_data["tickers"].items()])
                return prices, get_candlestick(tkr)
            
            refresh_btn.click(refresh_dashboard, inputs=ticker_select, outputs=[live_text, chart])
            ticker_select.change(get_candlestick, inputs=ticker_select, outputs=chart)

        with gr.Tab("📋 Options Chain"):
            opt_ticker = gr.Dropdown(DEFAULT_TICKERS, value="TSLA", label="Ticker")
            opt_btn = gr.Button("Load Options Chain")
            options_output = gr.Markdown()
            opt_btn.click(get_options_chain, inputs=opt_ticker, outputs=options_output)

        with gr.Tab("📥 Historical Data"):
            tickers_input = gr.Textbox(value="TSLA,AAPL,NVDA", label="Tickers (comma separated)")
            backfill_btn = gr.Button("Backfill Data")
            backfill_output = gr.Textbox()
            backfill_btn.click(lambda x: db.backfill([t.strip().upper() for t in x.split(",") if t.strip()]), 
                             inputs=tickers_input, outputs=backfill_output)

        with gr.Tab("🧠 Self-Improvement"):
            prompt = gr.Textbox(lines=4, placeholder="Add real-time chart updates every 10s...")
            sim_btn = gr.Button("Trigger Self-Improvement")
            sim_output = gr.Textbox()
            sim_btn.click(lambda p: f"✅ SIM cycle started:\n{p}", inputs=prompt, outputs=sim_output)

        with gr.Tab("📜 Logs"):
            logs_box = gr.Textbox(label="Recent Logs", lines=15, value=lambda: Path(LOG_FILE).read_text()[-4000:] if Path(LOG_FILE).exists() else "No logs yet")
            gr.Button("Refresh Logs").click(lambda: Path(LOG_FILE).read_text()[-4000:] if Path(LOG_FILE).exists() else "No logs", outputs=logs_box)

    gr.Markdown("--- **Live updates active • Browser auto-open enabled**")

# ========================= LAUNCH =========================
if __name__ == "__main__":
    logger.info("🚀 Starting XForge Trader v3.2 with Charts & Options...")
    print("🌐 Opening XForge Trader in your default browser...")
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,      # ← Auto opens browser
        share=False,
        quiet=True
    )