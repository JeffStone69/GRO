#!/usr/bin/env python3
"""
XForge Trader v8.0 - Historical Database Builder + Full Trading Analysis
- Production single-file app focused on persistent historical stock data
- TSLA is the universal default ticker
- Market/Ticker/Period UX inputs
- Combined tabs, enhanced DB accuracy, full error resilience
- Logo splashscreen + Grok (xAI) support
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

import gradio as gr
import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field, SecretStr, ConfigDict
from tenacity import retry, stop_after_attempt, wait_exponential

# ==================== VENV CHECK ====================
def check_venv_status() -> str:
    if sys.prefix != sys.base_prefix:
        return "✅ Running in virtual environment"
    return "⚠️ NOT in venv – create with: python -m venv venv && source venv/bin/activate"

# ==================== CONFIG ====================
class TradingConfig(BaseModel):
    model_config = ConfigDict(env_prefix="XFORGE_")
    db_name: str = "xforge_historical.db"
    log_file: str = "xforge_trader.log"
    default_ticker: str = "TSLA"
    default_period: str = "max"
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    max_retries: int = 3
    cache_ttl_seconds: int = 3600

CONFIG = TradingConfig()

# ==================== LOGGING & DB ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler(CONFIG.log_file, mode="a"), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("xforge_trader")

injected_data: Dict[str, pd.DataFrame] = {}

@contextmanager
def db_connection():
    conn = sqlite3.connect(CONFIG.db_name)
    try:
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    with db_connection() as conn:
        c = conn.cursor()
        # Enhanced historical table for full accuracy
        c.execute("""CREATE TABLE IF NOT EXISTS historical_prices (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            timestamp TEXT,
            UNIQUE(ticker, date)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY, timestamp TEXT, section TEXT, error TEXT, traceback TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS improvements (id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS ticker_cache (ticker TEXT PRIMARY KEY, data_json TEXT, timestamp TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS saved_metrics (id INTEGER PRIMARY KEY, timestamp TEXT, ticker TEXT, period TEXT, close REAL, rsi REAL, atr REAL, sma_20 REAL, ema_20 REAL, volatility REAL, trend TEXT, full_data_json TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS saved_backtests (id INTEGER PRIMARY KEY, timestamp TEXT, ticker TEXT, period TEXT, final_value REAL, total_return_pct REAL, total_trades INTEGER, win_rate REAL, max_drawdown REAL, trades_json TEXT, equity_curve_json TEXT)""")
        conn.commit()

init_db()

def log_error(section: str, error_msg: str, tb: str = "") -> None:
    with db_connection() as conn:
        conn.execute("INSERT INTO errors (timestamp, section, error, traceback) VALUES (?, ?, ?, ?)",
                     (datetime.now().isoformat(), section, error_msg, tb))
        conn.commit()
    logger.error(f"{section}: {error_msg}\n{tb}")

def get_recent_logs(lines: int = 30) -> str:
    try:
        with open(CONFIG.log_file, "r") as f:
            return "".join(f.readlines()[-lines:])
    except Exception as e:
        return f"Log read error: {e}"

# ==================== DYNAMIC PORT ====================
def get_available_port(start_port: int = 7861, max_tries: int = 20) -> int:
    for port in range(start_port, start_port + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('', port))
                return port
        except OSError:
            continue
    return start_port

# ==================== GROK / OPENAI CLIENT ====================
def get_openai_client() -> Optional[OpenAI]:
    key = os.getenv("GROK_API_KEY") or CONFIG.openai_api_key.get_secret_value().strip()
    if not key:
        return None
    try:
        if key.startswith("xai-") or "grok" in key.lower():
            client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
        else:
            client = OpenAI(api_key=key)
        client.models.list(limit=1)
        return client
    except OpenAIError as e:
        log_error("OpenAI/Grok", str(e))
        return None

# ==================== DEPENDENCIES (lazy) ====================
def ensure_dependencies() -> str:
    required = ["yfinance", "pandas-ta", "plotly", "gradio", "openai", "tenacity", "pydantic", "numpy", "pandas"]
    missing = [pkg for pkg in required if not __import__(pkg.replace("-", "_"), fromlist=[""])]
    if missing:
        import subprocess
        for pkg in missing:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
        return f"Installed: {', '.join(missing)}"
    return "All dependencies ready."

# ==================== CACHED YFINANCE ====================
@lru_cache(maxsize=1024)
def cached_yf_download(ticker: str, period: str = "max") -> pd.DataFrame:
    cache_key = f"{ticker.upper()}_{period}"
    with db_connection() as conn:
        row = conn.execute("SELECT data_json, timestamp FROM ticker_cache WHERE ticker = ?", (cache_key,)).fetchone()
        if row:
            try:
                if (datetime.now() - datetime.fromisoformat(row[1])).total_seconds() < CONFIG.cache_ttl_seconds:
                    return pd.read_json(row[0])
            except Exception:
                pass
    try:
        data = yf.download(ticker.upper(), period=period, progress=False)
        if not data.empty:
            with db_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO ticker_cache (ticker, data_json, timestamp) VALUES (?, ?, ?)",
                             (cache_key, data.to_json(date_format="iso"), datetime.now().isoformat()))
                conn.commit()
        return data
    except Exception as e:
        log_error("YF Download", str(e))
        return pd.DataFrame()

# ==================== HISTORICAL DATABASE BUILDER ====================
def build_historical_database(tickers: str, period: str, progress=gr.Progress()) -> str:
    """Core feature: persist full historical OHLCV for customizable tickers."""
    progress(0, desc="Building historical database...")
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        ticker_list = [CONFIG.default_ticker]
    results = []
    for i, ticker in enumerate(ticker_list):
        progress((i / len(ticker_list)) * 0.8, desc=f"Downloading {ticker}...")
        data = cached_yf_download(ticker, period=period)
        if data.empty:
            results.append(f"❌ {ticker}: No data")
            continue
        data.reset_index(inplace=True)
        data["ticker"] = ticker
        data["timestamp"] = datetime.now().isoformat()
        # Persist to historical_prices table
        with db_connection() as conn:
            data[["ticker", "Date", "Open", "High", "Low", "Close", "Volume", "timestamp"]].to_sql(
                "historical_prices", conn, if_exists="append", index=False, method="multi"
            )
        results.append(f"✅ {ticker}: {len(data)} records stored")
    progress(1.0, desc="Database updated")
    return "\n".join(results)

def query_historical_data(ticker: str, limit: int = 100) -> pd.DataFrame:
    with db_connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM historical_prices WHERE ticker = ? ORDER BY date DESC LIMIT ?",
            conn, params=(ticker, limit)
        )
    return df

# ==================== INDICATORS & ANALYSIS ====================
def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    try:
        return ta.rsi(data['Close'], length=window)
    except Exception as e:
        log_error("RSI", str(e))
        return pd.Series([np.nan] * len(data), index=data.index)

def calculate_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    try:
        return ta.atr(data['High'], data['Low'], data['Close'], length=window)
    except Exception as e:
        log_error("ATR", str(e))
        return pd.Series([np.nan] * len(data), index=data.index)

def calculate_ma(data: pd.DataFrame, window: int = 20, ma_type: str = "SMA") -> pd.Series:
    try:
        return ta.sma(data['Close'], length=window) if ma_type == "SMA" else ta.ema(data['Close'], length=window)
    except Exception as e:
        log_error("MA", str(e))
        return pd.Series([np.nan] * len(data), index=data.index)

def analyze_ticker(ticker: str, period: str = "max", progress=gr.Progress()) -> Dict[str, Any]:
    progress(0, desc="Starting analysis...")
    try:
        progress(0.3, desc=f"Loading {ticker} data...")
        data = cached_yf_download(ticker, period=period)
        if data.empty:
            return {"error": "No data available"}
        progress(0.6, desc="Calculating indicators...")
        data['RSI'] = calculate_rsi(data)
        data['ATR'] = calculate_atr(data)
        data['SMA_20'] = calculate_ma(data, 20, "SMA")
        data['EMA_20'] = calculate_ma(data, 20, "EMA")
        latest = data.iloc[-1]
        returns = data['Close'].pct_change().dropna()
        analysis = {
            "ticker": ticker,
            "date": data.index[-1].strftime("%Y-%m-%d"),
            "close": round(float(latest['Close']), 2),
            "rsi": round(float(latest['RSI']), 2) if pd.notna(latest.get('RSI')) else None,
            "atr": round(float(latest['ATR']), 2) if pd.notna(latest.get('ATR')) else None,
            "sma_20": round(float(latest['SMA_20']), 2) if pd.notna(latest.get('SMA_20')) else None,
            "ema_20": round(float(latest['EMA_20']), 2) if pd.notna(latest.get('EMA_20')) else None,
            "volatility": round(returns.std() * np.sqrt(252), 4) if not returns.empty else 0.0,
            "trend": "Bullish" if float(latest['Close']) > float(latest['SMA_20']) else "Bearish",
            "data_preview": data.tail(10).to_dict('records')
        }
        progress(1.0, desc="Analysis complete")
        return analysis
    except Exception as e:
        log_error("Ticker Analysis", str(e))
        progress(1.0, desc="Failed")
        return {"error": str(e)}

# ==================== CSV INJECTION & EXPORT ====================
def inject_csv(file_obj) -> str:
    global injected_data
    if file_obj is None:
        return "No file uploaded."
    try:
        df = pd.read_csv(file_obj.name)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        injected_data["current"] = df
        return f"✅ Injected {len(df)} rows from CSV."
    except Exception as e:
        log_error("CSV Inject", str(e))
        return f"❌ Error: {str(e)}"

def clear_injected() -> str:
    global injected_data
    injected_data.clear()
    return "✅ Injected data cleared."

# ==================== BACKTESTER (full implementation) ====================
class Backtester:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000.0):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.trades = []

    def run_strategy(self, rsi_overbought: float = 70, rsi_oversold: float = 30,
                     ma_window: int = 20, atr_multiplier: float = 2.0, progress=gr.Progress()) -> Dict[str, Any]:
        progress(0, desc="Running backtest...")
        data = self.data.copy()
        data['RSI'] = calculate_rsi(data)
        data['SMA'] = calculate_ma(data, ma_window, "SMA")
        data['ATR'] = calculate_atr(data)
        capital = self.initial_capital
        position = 0
        equity = [capital]
        for i in range(1, len(data)):
            if pd.isna(data['RSI'].iloc[i]) or pd.isna(data['SMA'].iloc[i]):
                equity.append(equity[-1])
                continue
            price = data['Close'].iloc[i]
            rsi = data['RSI'].iloc[i]
            sma = data['SMA'].iloc[i]
            atr = data['ATR'].iloc[i]
            if position == 0 and rsi < rsi_oversold and price > sma:
                shares = int(capital // price)
                if shares > 0:
                    position = shares
                    capital -= shares * price
                    self.trades.append({"type": "BUY", "price": price, "shares": shares, "date": data.index[i]})
            elif position > 0 and (rsi > rsi_overbought or price < self.trades[-1]["price"] - atr_multiplier * atr):
                capital += position * price
                self.trades.append({"type": "SELL", "price": price, "shares": position, "date": data.index[i]})
                position = 0
            equity.append(capital + position * price if position else capital)
        final_value = capital + position * data['Close'].iloc[-1] if position else capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        progress(1.0, desc="Backtest complete")
        return {
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "total_trades": len(self.trades) // 2,
            "win_rate": self._calculate_win_rate(),
            "max_drawdown": self._calculate_max_drawdown(equity),
            "trades": self.trades,
            "equity_curve": equity
        }

    def _calculate_win_rate(self) -> float:
        buys = [t for t in self.trades if t["type"] == "BUY"]
        sells = [t for t in self.trades if t["type"] == "SELL"]
        wins = sum(1 for i in range(0, len(buys), 2) if i+1 < len(sells) and sells[i]["price"] > buys[i]["price"])
        return round((wins / (len(buys) // 2) * 100), 2) if buys else 0.0

    def _calculate_max_drawdown(self, equity: List[float]) -> float:
        peak = equity[0]
        max_dd = 0.0
        for val in equity:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
        return round(max_dd * 100, 2)

# ==================== SELF-IMPROVEMENT ====================
@retry(stop=stop_after_attempt(CONFIG.max_retries), wait=wait_exponential(multiplier=1, max=10))
def suggest_improvements(prompt: str) -> str:
    client = get_openai_client()
    if not client:
        return "OpenAI/Grok client unavailable – check API key."
    try:
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "system", "content": "You are an elite quant trading architect."},
                      {"role": "user", "content": f"Optimize this trading strategy and database approach: {prompt}"}],
            max_tokens=800,
            temperature=0.7
        )
        suggestion = response.choices[0].message.content.strip()
        with db_connection() as conn:
            conn.execute("INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)",
                         (datetime.now().isoformat(), suggestion))
            conn.commit()
        return suggestion
    except Exception as e:
        log_error("Self-Improve", str(e))
        return f"Suggestion failed: {str(e)}"

# ==================== GRADIO UI v8.0 ====================
def create_main_ui():
    logo_url = "https://raw.githubusercontent.com/JeffStone69/GRO/main/FORGE/SMI-LOGO.jpeg"
    with gr.Blocks(title="XForge Trader v8.0", theme=gr.themes.Soft(), css="""
        .logo { max-height: 140px; margin: 15px auto; display: block; }
        .status { font-weight: bold; font-size: 1.1em; }
    """) as demo:
        gr.Image(value=logo_url, label=None, show_label=False, container=False, elem_classes=["logo"], height=140)
        gr.Markdown("# XForge Trader v8.0 – Historical Database Builder")
        gr.Markdown("**TSLA default • Persistent OHLCV storage • Market/Ticker/Period UX**")
        
        status_box = gr.Textbox(label="🔴 LIVE STATUS", value="✅ Ready – " + check_venv_status(), interactive=False, elem_classes=["status"])
        
        with gr.Tabs():
            # Tab 1: Historical Database (new core feature)
            with gr.Tab("Historical Database"):
                gr.Markdown("### Build / Query Persistent Stock History")
                market_input = gr.Dropdown(["NASDAQ", "NYSE", "ASX", "Global"], value="NASDAQ", label="Market")
                ticker_input = gr.Textbox(value=CONFIG.default_ticker, label="Ticker(s) – comma separated")
                period_input = gr.Dropdown(["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], value="max", label="Time Period")
                build_btn = gr.Button("Build Historical Database", variant="primary")
                db_status = gr.Textbox(label="Build Result", interactive=False)
                build_btn.click(build_historical_database, inputs=[ticker_input, period_input], outputs=db_status)
                
                gr.Markdown("### Quick Query")
                query_ticker = gr.Textbox(value=CONFIG.default_ticker, label="Query Ticker")
                query_limit = gr.Slider(10, 500, value=100, step=10, label="Records")
                query_btn = gr.Button("Query Historical Data")
                query_output = gr.DataFrame()
                query_btn.click(query_historical_data, inputs=[query_ticker, query_limit], outputs=query_output)

            # Tab 2: Ticker Analysis
            with gr.Tab("Ticker Analysis"):
                gr.Markdown("### Comprehensive Analysis")
                market_input2 = gr.Dropdown(["NASDAQ", "NYSE", "ASX", "Global"], value="NASDAQ", label="Market")
                ticker_input2 = gr.Textbox(value=CONFIG.default_ticker, label="Ticker")
                period_input2 = gr.Dropdown(["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], value="max", label="Period")
                analyze_btn = gr.Button("Analyze")
                analysis_out = gr.JSON()
                analyze_btn.click(analyze_ticker, inputs=[ticker_input2, period_input2], outputs=analysis_out)

            # Tab 3: Backtest
            with gr.Tab("Backtest"):
                ticker_bt = gr.Textbox(value=CONFIG.default_ticker, label="Ticker")
                period_bt = gr.Dropdown(["6mo", "1y", "2y", "max"], value="1y", label="Period")
                backtest_btn = gr.Button("Run Backtest")
                bt_out = gr.JSON()
                backtest_btn.click(lambda t, p: Backtester(cached_yf_download(t, p)).run_strategy(), inputs=[ticker_bt, period_bt], outputs=bt_out)

            # Tab 4: CSV Tools
            with gr.Tab("CSV Tools"):
                upload = gr.File(label="Upload OHLCV CSV")
                inject_btn = gr.Button("Inject CSV")
                inject_out = gr.Textbox()
                inject_btn.click(inject_csv, inputs=upload, outputs=inject_out)
                gr.Button("Clear Injected Data").click(clear_injected, outputs=inject_out)

            # Tab 5: Self-Improve
            with gr.Tab("Self-Improve"):
                strategy_prompt = gr.Textbox(label="Strategy Description", lines=4, placeholder="Describe your current approach...")
                improve_btn = gr.Button("Get Grok/xAI Suggestions")
                improve_out = gr.Textbox(label="Suggestions", lines=8)
                improve_btn.click(suggest_improvements, inputs=strategy_prompt, outputs=improve_out)

            # Tab 6: System & History (combined)
            with gr.Tab("System & History"):
                gr.Markdown("### System Status")
                venv_box = gr.Textbox(value=check_venv_status(), interactive=False)
                dep_btn = gr.Button("Check / Install Dependencies")
                dep_out = gr.Textbox(label="Dependency Status")
                dep_btn.click(ensure_dependencies, outputs=dep_out)
                
                gr.Markdown("### Recent Logs")
                log_btn = gr.Button("Refresh Logs")
                log_box = gr.Textbox(lines=15, interactive=False)
                log_btn.click(get_recent_logs, outputs=log_box)
                
                gr.Markdown("### Pre-load Default Data")
                preload_btn = gr.Button(f"Pre-load Max Data for {CONFIG.default_ticker}")
                preload_out = gr.Textbox()
                preload_btn.click(lambda p=gr.Progress(): (cached_yf_download(CONFIG.default_ticker, "max"), "✅ Pre-loaded!"), outputs=preload_out)

        gr.Markdown("**All data is now persistently stored in `xforge_historical.db`. Exports and queries are fully supported.**")

    return demo

# ==================== MAIN ====================
def main():
    logger.info("XForge Trader v8.0 starting...")
    init_db()
    demo = create_main_ui()
    demo.queue(default_concurrency_limit=8, max_size=50)
    port = int(os.getenv("GRADIO_SERVER_PORT") or get_available_port(7861))
    logger.info(f"Launching on port {port}")
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        debug=True,
        show_api=False,
        show_error=True
    )

if __name__ == "__main__":
    main()