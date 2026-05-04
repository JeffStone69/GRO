#!/usr/bin/env python3
"""
XForge Trader v7.4 - Final Next Iteration
- Fixed "truth value of a Series is ambiguous" error (safe scalar extraction)
- CSV injection (upload any OHLCV CSV) + full extraction (export to CSV)
- Visible live status bar + progress bars + .queue() (no stalls)
- VENV status + full error logging + preload button
- Grok (xAI) API key support via launcher
- All previous features (TSLA/NVDA max history, self-improve, backtester, simulated TWS, saved DB)
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
    return "⚠️ NOT in venv – create with: python -m venv venv && activate"

# ==================== CONFIG ====================
class TradingConfig(BaseModel):
    model_config = ConfigDict(env_prefix="XFORGE_")
    db_name: str = "xforge_self_improve.db"
    log_file: str = "xforge_trader.log"
    default_tickers: List[str] = Field(default=["TSLA", "NVDA"])
    default_period: str = "max"
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    max_retries: int = 3
    cache_ttl_seconds: int = 300

CONFIG = TradingConfig()

# ==================== LOGGING & DB ====================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    handlers=[logging.FileHandler(CONFIG.log_file, mode="a"), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("xforge_trader")

injected_data: Dict[str, pd.DataFrame] = {}  # Global for CSV injection

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

def get_recent_logs(lines: int = 25) -> str:
    try:
        with open(CONFIG.log_file, "r") as f:
            return "".join(f.readlines()[-lines:])
    except Exception as e:
        return f"Log error: {e}"

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

# ==================== GROK / OPENAI CLIENT (supports Grok API key) ====================
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

# ==================== DEPENDENCIES ====================
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
@lru_cache(maxsize=512)
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

# ==================== INDICATORS ====================
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

# ==================== TICKER ANALYSIS (FIXED SERIES ERROR + CSV SUPPORT) ====================
def analyze_ticker(ticker: str, period: str = "max", use_injected: bool = False, progress=gr.Progress()) -> Dict[str, Any]:
    progress(0, desc="Starting analysis...")
    try:
        progress(0.2, desc=f"Loading data for {ticker}...")
        if use_injected and "current" in injected_data:
            data = injected_data["current"].copy()
        else:
            data = cached_yf_download(ticker, period=period)

        if data.empty:
            return {"error": "No data available"}

        progress(0.4, desc="Calculating indicators...")
        data['RSI'] = calculate_rsi(data)
        data['ATR'] = calculate_atr(data)
        data['SMA_20'] = calculate_ma(data, 20, "SMA")
        data['EMA_20'] = calculate_ma(data, 20, "EMA")

        latest = data.iloc[-1]
        returns = data['Close'].pct_change().dropna()

        # SAFE SCALAR EXTRACTION – fixes "truth value of a Series is ambiguous"
        close_val = float(latest['Close']) if pd.notna(latest.get('Close')) else 0.0
        sma_val = float(latest['SMA_20']) if pd.notna(latest.get('SMA_20')) else 0.0
        rsi_val = float(latest['RSI']) if pd.notna(latest.get('RSI')) else None
        atr_val = float(latest['ATR']) if pd.notna(latest.get('ATR')) else None
        ema_val = float(latest['EMA_20']) if pd.notna(latest.get('EMA_20')) else None
        vol_val = round(returns.std() * np.sqrt(252), 4) if not returns.empty else 0.0

        analysis = {
            "ticker": ticker,
            "date": data.index[-1].strftime("%Y-%m-%d"),
            "close": round(close_val, 2),
            "rsi": round(rsi_val, 2) if rsi_val is not None else None,
            "atr": round(atr_val, 2) if atr_val is not None else None,
            "sma_20": round(sma_val, 2) if sma_val else None,
            "ema_20": round(ema_val, 2) if ema_val else None,
            "volatility": vol_val,
            "trend": "Bullish" if close_val > sma_val else "Bearish",
            "data": data.tail(10).to_dict('records')
        }
        progress(1.0, desc="Analysis complete!")
        return analysis
    except Exception as e:
        log_error("Ticker Analysis", str(e))
        progress(1.0, desc="Analysis failed")
        return {"error": str(e)}

# ==================== CSV INJECTION / EXTRACTION ====================
def inject_csv(file_obj) -> str:
    global injected_data
    if file_obj is None:
        return "No file uploaded."
    try:
        df = pd.read_csv(file_obj.name)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        # Standardize columns
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col not in df.columns and col.lower() in [c.lower() for c in df.columns]:
                df[col] = df[[c for c in df.columns if c.lower() == col.lower()][0]]
        injected_data["current"] = df
        return f"✅ Injected {len(df)} rows from CSV. Analysis & backtests will now use this data."
    except Exception as e:
        log_error("CSV Inject", str(e))
        return f"❌ Error: {str(e)}"

def clear_injected() -> str:
    global injected_data
    injected_data.clear()
    return "✅ Injected CSV data cleared. Back to yfinance."

def export_analysis_to_csv(analysis: dict) -> str:
    if not analysis or "error" in analysis:
        return "No analysis to export."
    try:
        df = pd.DataFrame([analysis])
        path = f"analysis_{analysis.get('ticker', 'data')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(path, index=False)
        return f"✅ Exported to {path} (download below)"
    except Exception as e:
        return f"❌ Export failed: {str(e)}"

def export_saved_metrics_to_csv() -> str:
    try:
        df = pd.read_sql_query("SELECT * FROM saved_metrics ORDER BY timestamp DESC", db_connection().__enter__())
        path = f"saved_metrics_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(path, index=False)
        return path
    except Exception as e:
        log_error("Export Metrics", str(e))
        return ""

# ==================== BACKTESTER (same safe logic) ====================
class Backtester:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.trades = []

    def run_strategy(self, rsi_overbought: float = 70, rsi_oversold: float = 30,
                     ma_window: int = 20, atr_multiplier: float = 2.0, progress=gr.Progress()) -> Dict[str, Any]:
        progress(0, desc="Starting backtest...")
        try:
            data = self.data.copy()
            data['RSI'] = calculate_rsi(data, 14)
            data['SMA'] = calculate_ma(data, ma_window, "SMA")
            data['ATR'] = calculate_atr(data, 14)

            capital = self.initial_capital
            position = 0
            equity = [capital]
            total_steps = len(data)

            for i in range(1, total_steps):
                progress((i / total_steps) * 0.85, desc=f"Processing bar {i}/{total_steps}...")
                if pd.isna(data['RSI'].iloc[i]) or pd.isna(data['SMA'].iloc[i]):
                    continue
                price = float(data['Close'].iloc[i])
                rsi = float(data['RSI'].iloc[i])
                sma = float(data['SMA'].iloc[i])
                atr = float(data['ATR'].iloc[i])

                if position == 0:
                    if rsi < rsi_oversold and price > sma:
                        shares = int(capital // price)
                        if shares > 0:
                            position = shares
                            capital -= shares * price
                            self.trades.append({"type": "BUY", "price": price, "shares": shares, "date": str(data.index[i])})
                elif position > 0:
                    entry_price = self.trades[-1]['price']
                    if rsi > rsi_overbought or price < entry_price - atr_multiplier * atr:
                        capital += position * price
                        self.trades.append({"type": "SELL", "price": price, "shares": position, "date": str(data.index[i])})
                        position = 0
                equity.append(capital + position * price if position > 0 else capital)

            final_value = capital + position * float(data['Close'].iloc[-1]) if position > 0 else capital
            total_return = (final_value - self.initial_capital) / self.initial_capital * 100

            result = {
                "final_value": round(final_value, 2),
                "total_return_pct": round(total_return, 2),
                "total_trades": len(self.trades) // 2,
                "win_rate": self._calculate_win_rate(),
                "max_drawdown": self._calculate_max_drawdown(equity),
                "equity_curve": equity,
                "trades": self.trades
            }
            progress(1.0, desc="Backtest complete!")
            return result
        except Exception as e:
            log_error("Backtester", str(e))
            progress(1.0, desc="Backtest failed")
            return {"error": str(e)}

    def _calculate_win_rate(self) -> float:
        buys = [t for t in self.trades if t['type'] == 'BUY']
        sells = [t for t in self.trades if t['type'] == 'SELL']
        wins = sum(1 for i in range(0, len(buys), 2) if i+1 < len(sells) and sells[i]['price'] > buys[i]['price'])
        return round((wins / (len(buys)//2) * 100), 2) if buys else 0.0

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        return round(max_dd * 100, 2)

# ==================== SAVE & LOAD ====================
def save_analysis(analysis: dict, period: str = "max") -> str:
    if not analysis or "error" in analysis:
        return "No valid analysis to save."
    try:
        with db_connection() as conn:
            conn.execute("""INSERT INTO saved_metrics (timestamp, ticker, period, close, rsi, atr, sma_20, ema_20, volatility, trend, full_data_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (datetime.now().isoformat(), analysis.get("ticker"), period, analysis.get("close"),
                          analysis.get("rsi"), analysis.get("atr"), analysis.get("sma_20"), analysis.get("ema_20"),
                          analysis.get("volatility"), analysis.get("trend"), json.dumps(analysis.get("data", []))))
            conn.commit()
        return "✅ Metrics saved to database!"
    except Exception as e:
        log_error("Save Analysis", str(e))
        return f"❌ Save failed: {str(e)}"

def save_backtest(results: dict, ticker: str, period: str = "max") -> str:
    if not results or "error" in results:
        return "No valid backtest."
    try:
        with db_connection() as conn:
            conn.execute("""INSERT INTO saved_backtests (timestamp, ticker, period, final_value, total_return_pct, total_trades, win_rate, max_drawdown, trades_json, equity_curve_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (datetime.now().isoformat(), ticker, period, results.get("final_value"), results.get("total_return_pct"),
                          results.get("total_trades"), results.get("win_rate"), results.get("max_drawdown"),
                          json.dumps(results.get("trades", [])), json.dumps(results.get("equity_curve", []))))
            conn.commit()
        return "✅ Backtest saved to database!"
    except Exception as e:
        log_error("Save Backtest", str(e))
        return f"❌ Save failed: {str(e)}"

def load_saved_metrics() -> pd.DataFrame:
    try:
        with db_connection() as conn:
            return pd.read_sql_query("SELECT * FROM saved_metrics ORDER BY timestamp DESC LIMIT 100", conn)
    except Exception as e:
        log_error("Load Metrics", str(e))
        return pd.DataFrame()

def load_saved_backtests() -> pd.DataFrame:
    try:
        with db_connection() as conn:
            return pd.read_sql_query("SELECT * FROM saved_backtests ORDER BY timestamp DESC LIMIT 100", conn)
    except Exception as e:
        log_error("Load Backtests", str(e))
        return pd.DataFrame()

# ==================== SELF-IMPROVE ====================
@retry(stop=stop_after_attempt(CONFIG.max_retries), wait=wait_exponential(multiplier=1, max=10))
def suggest_improvements(prompt: str, progress=gr.Progress()) -> Optional[str]:
    progress(0, desc="Contacting Grok/xAI...")
    client = get_openai_client()
    if not client:
        return "Grok/OpenAI client not available. Check API key in launcher."
    try:
        progress(0.4, desc="Generating improvements...")
        response = client.chat.completions.create(
            model="grok-beta" if os.getenv("GROK_API_KEY") else "gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a trading expert for TSLA and NVDA."},
                      {"role": "user", "content": f"Improve this strategy: {prompt}"}],
            max_tokens=600, temperature=0.7
        )
        suggestion = response.choices[0].message.content.strip()
        with db_connection() as conn:
            conn.execute("INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)",
                         (datetime.now().isoformat(), suggestion))
            conn.commit()
        progress(1.0, desc="Suggestions ready!")
        return suggestion
    except Exception as e:
        log_error("Self-Improve", str(e))
        return f"Failed: {str(e)}"

# ==================== GRADIO UI ====================
def create_main_ui():
    with gr.Blocks(title="XForge Trader v7.4") as demo:
        status_box = gr.Textbox(label="🔴 LIVE STATUS BAR", value="✅ Ready – " + check_venv_status(), interactive=False)

        gr.Markdown("# XForge Trader v7.4 – TSLA/NVDA Max History + CSV Support")

        with gr.Tabs():
            # Analysis Tab with CSV
            with gr.Tab("Ticker Analysis"):
                ticker = gr.Textbox(label="Ticker", value="TSLA")
                period = gr.Dropdown(["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], value="max", label="Period")
                use_csv = gr.Checkbox(label="Use Injected CSV Data", value=False)
                analyze_btn = gr.Button("Analyze")
                analysis_out = gr.JSON(label="Results")

                def wrapped_analyze(t, p, u, progress=gr.Progress()):
                    status_box.value = f"🔄 Analyzing {t}..."
                    res = analyze_ticker(t, p, u, progress)
                    status_box.value = "✅ Analysis complete"
                    return res

                analyze_btn.click(wrapped_analyze, [ticker, period, use_csv], analysis_out)

                # CSV Injection
                csv_file = gr.File(label="Upload CSV (Date,Open,High,Low,Close,Volume)", file_types=[".csv"])
                inject_btn = gr.Button("Inject CSV Data")
                inject_status = gr.Textbox(label="Injection Status", interactive=False)
                inject_btn.click(inject_csv, csv_file, inject_status)

                clear_csv_btn = gr.Button("Clear Injected CSV")
                clear_csv_btn.click(clear_injected, outputs=inject_status)

                # Export
                export_btn = gr.Button("Export Current Analysis to CSV")
                export_status = gr.Textbox(label="Export Status", interactive=False)
                export_btn.click(export_analysis_to_csv, analysis_out, export_status)

                save_btn = gr.Button("Save Metrics to DB")
                save_status = gr.Textbox(label="DB Save Status", interactive=False)
                save_btn.click(save_analysis, [analysis_out, period], save_status)

            # Backtest Tab
            with gr.Tab("Backtest"):
                t_b = gr.Textbox(label="Ticker", value="TSLA")
                p_b = gr.Dropdown(["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], value="max")
                back_btn = gr.Button("Run Backtest")
                back_out = gr.JSON()

                def wrapped_back(t, p, progress=gr.Progress()):
                    status_box.value = f"🔄 Backtesting {t}..."
                    data = injected_data.get("current", cached_yf_download(t, p))
                    res = Backtester(data).run_strategy(progress=progress)
                    status_box.value = "✅ Backtest complete"
                    return res

                back_btn.click(wrapped_back, [t_b, p_b], back_out)

                save_b_btn = gr.Button("Save Backtest to DB")
                save_b_status = gr.Textbox(interactive=False)
                save_b_btn.click(save_backtest, [back_out, t_b, p_b], save_b_status)

            # Self-Improve
            with gr.Tab("Self-Improve"):
                strat = gr.Textbox(value="RSI(14) + SMA(20) crossover on TSLA/NVDA with max history", lines=3)
                improve_btn = gr.Button("Get Grok Improvements")
                improve_out = gr.Textbox(lines=12)
                improve_btn.click(suggest_improvements, strat, improve_out)

            # Saved Data + Export
            with gr.Tab("Saved Data"):
                gr.Markdown("### Saved Metrics")
                load_m = gr.Button("Load Saved Metrics")
                clear_m = gr.Button("Clear Saved Metrics")
                metrics_df = gr.Dataframe(interactive=False)
                load_m.click(load_saved_metrics, outputs=metrics_df)
                clear_m.click(lambda: (pd.DataFrame(), "Cleared"), outputs=[metrics_df])

                export_m_btn = gr.Button("Export Saved Metrics to CSV")
                export_m_file = gr.File(label="Download CSV", interactive=False)
                export_m_btn.click(export_saved_metrics_to_csv, outputs=export_m_file)

                gr.Markdown("### Saved Backtests")
                load_b = gr.Button("Load Saved Backtests")
                back_df = gr.Dataframe(interactive=False)
                load_b.click(load_saved_backtests, outputs=back_df)

            # Status & Logs
            with gr.Tab("Status & Logs"):
                gr.Markdown("### System Status")
                venv_box = gr.Textbox(value=check_venv_status(), interactive=False)
                sys_json = gr.JSON(lambda: {"dependencies": ensure_dependencies(), "database": "Ready", "log_file": CONFIG.log_file})
                gr.Markdown("### Recent Logs (Errors & Activity)")
                log_btn = gr.Button("Refresh Logs")
                log_box = gr.Textbox(lines=15, interactive=False)
                log_btn.click(get_recent_logs, outputs=log_box)

                preload_btn = gr.Button("Pre-load Max Data for TSLA & NVDA")
                preload_out = gr.Textbox(interactive=False)
                preload_btn.click(lambda progress=gr.Progress(): (cached_yf_download("TSLA", "max"), cached_yf_download("NVDA", "max"), "✅ Pre-loaded!"), outputs=preload_out)

        gr.Markdown("**Tip:** Use launcher.py for splash + Grok key. All CSV exports are downloadable.")

    return demo

# ==================== MAIN ====================
def main():
    logger.info("XForge Trader v7.4 starting...")
    init_db()
    ensure_dependencies()

    demo = create_main_ui()
    demo.queue()

    port = int(os.getenv("GRADIO_SERVER_PORT") or get_available_port(7861))
    logger.info(f"Launching on port {port}")
    demo.launch(server_name="0.0.0.0", server_port=port, share=False, debug=False)

if __name__ == "__main__":
    main()
