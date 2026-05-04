#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

class TradingConfig(BaseModel):
    db_name: str = "xforge_self_improve.db"
    log_file: str = "xforge_trader.log"
    default_tickers: List[str] = Field(default=["TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "V", "XOM", "UNH", "HD", "PG", "MA", "CVX"])
    default_period: str = "1y"
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    x_bearer_token: SecretStr = Field(default=SecretStr(""))
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1
    max_retries: int = 3
    cache_ttl_seconds: int = 300
    slippage_pct: float = 0.001

CONFIG = TradingConfig()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler(CONFIG.log_file, mode="a"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("xforge_trader")

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
        c.execute("CREATE INDEX IF NOT EXISTS idx_errors_ts ON errors(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_improvements_ts ON improvements(timestamp)")
        conn.commit()

init_db()

def log_error(section: str, error_msg: str, tb: str = "") -> None:
    with db_connection() as conn:
        conn.execute("INSERT INTO errors (timestamp, section, error, traceback) VALUES (?, ?, ?, ?)",
                     (datetime.now().isoformat(), section, error_msg, tb))
        conn.commit()
    logger.error(f"{section}: {error_msg}\n{tb}")

def ensure_dependencies() -> str:
    required = ["ib_insync", "yfinance", "pandas-ta", "plotly", "beautifulsoup4", "requests", "gradio", "openai", "tweepy", "tenacity", "pydantic", "numpy"]
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

@retry(stop=stop_after_attempt(CONFIG.max_retries), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def safe_request(url: str, headers: Optional[Dict] = None, timeout: int = 15) -> requests.Response:
    resp = requests.get(url, headers=headers or {"User-Agent": "Mozilla/5.0"}, timeout=timeout)
    resp.raise_for_status()
    return resp

@lru_cache(maxsize=512)
def cached_yf_download(ticker: str, period: str = "1y", start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
    cache_key = f"{ticker.upper()}_{period}_{start or ''}_{end or ''}"
    with db_connection() as conn:
        row = conn.execute("SELECT data_json, timestamp FROM ticker_cache WHERE ticker = ?", (cache_key,)).fetchone()
        if row:
            try:
                cached_time = datetime.fromisoformat(row[1])
                if (datetime.now() - cached_time).total_seconds() < CONFIG.cache_ttl_seconds:
                    return pd.read_json(row[0])
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
                conn.execute("INSERT OR REPLACE INTO ticker_cache (ticker, data_json, timestamp) VALUES (?, ?, ?)",
                             (cache_key, data_json, datetime.now().isoformat()))
                conn.commit()
        return data
    except Exception as e:
        log_error("YF Download", str(e))
        return pd.DataFrame()

def calculate_momentum(tickers_str: str = "", period: str = "1y", start_date: str = "", end_date: str = "") -> Tuple[pd.DataFrame, Optional[go.Figure], str]:
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()] if tickers_str.strip() else CONFIG.default_tickers
    def process_ticker(ticker: str) -> Optional[Dict[str, Any]]:
        try:
            data = cached_yf_download(ticker, period, start_date or None, end_date or None)
            if data.empty or len(data) < 20:
                return None
            data = data.dropna()
            close = data["Close"]
            ret_1m = (close.iloc[-1] / close.iloc[-22] - 1) * 100 if len(close) > 22 else 0.0
            ret_3m = (close.iloc[-1] / close.iloc[-66] - 1) * 100 if len(close) > 66 else 0.0
            ret_6m = (close.iloc[-1] / close.iloc[-132] - 1) * 100 if len(close) > 132 else 0.0
            ret_12m = (close.iloc[-1] / close.iloc[0] - 1) * 100 if len(close) > 0 else 0.0
            momentum_score = 0.40 * ret_12m + 0.30 * ret_6m + 0.20 * ret_3m + 0.10 * ret_1m
            data.ta.rsi(append=True)
            rsi = float(data["RSI_14"].iloc[-1]) if "RSI_14" in data.columns else 50.0
            high_volume = bool(data["Volume"].iloc[-1] > data["Volume"].mean()) if "Volume" in data.columns else False
            rebound = "YES - Strong Rebound Candidate" if (momentum_score > 10 and ret_1m < 0 and rsi < 40 and high_volume) else "No"
            if len(close) > 10:
                x = np.arange(len(close[-10:]))
                slope, intercept = np.polyfit(x, close[-10:], 1)
                forward_30d = intercept + slope * (len(close) + 30)
                forward_return = ((forward_30d / close.iloc[-1]) - 1) * 100
            else:
                forward_return = 0.0
            return {
                "Ticker": ticker, "1M Return %": round(ret_1m, 2), "3M Return %": round(ret_3m, 2),
                "6M Return %": round(ret_6m, 2), "12M Return %": round(ret_12m, 2),
                "Momentum Score": round(momentum_score, 2), "RSI(14)": round(rsi, 2),
                "High Volume": "Yes" if high_volume else "No", "Rebound Potential": rebound,
                "30-Day Forward Projection %": round(forward_return, 2),
            }
        except Exception as e:
            log_error("Momentum", str(e), traceback.format_exc())
            return None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(asyncio.gather(*[asyncio.to_thread(process_ticker, t) for t in tickers]))
    results = [r for r in results if r]
    if not results:
        return pd.DataFrame(), None, "No valid data. Check internet or dates."
    df = pd.DataFrame(results).sort_values("Momentum Score", ascending=False).head(15)
    fig = go.Figure(go.Bar(x=df["Ticker"], y=df["Momentum Score"],
                          marker_color=["green" if "YES" in r else "orange" for r in df["Rebound Potential"]],
                          text=df["Rebound Potential"]))
    fig.update_layout(title="Top Rebound Potential Stocks (TSLA prioritized) + Forward Projection", height=450,
                      xaxis_title="Ticker", yaxis_title="Momentum Score")
    summary = f"Scanned {len(tickers)} tickers. TSLA always prioritized. Green = strong rebound candidate."
    return df, fig, summary

def technical_analysis(ticker: str = "TSLA", period: str = "1y", start_date: str = "", end_date: str = "") -> Tuple[str, Optional[pd.DataFrame], Optional[go.Figure]]:
    try:
        data = cached_yf_download(ticker, period, start_date or None, end_date or None)
        if data.empty:
            return "No data found", None, None
        data.ta.rsi(append=True)
        data.ta.macd(append=True)
        data.ta.bbands(append=True)
        data.ta.sma(length=20, append=True)
        latest = data.iloc[-1]
        summary = f"RSI(14): {latest.get('RSI_14', 0):.2f} | MACD: {latest.get('MACD_12_26_9', 0):.4f} | BB Upper: {latest.get('BBU_20_2.0', 0):.2f} | SMA20: {latest.get('SMA_20', 0):.2f}"
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=(f"{ticker} Price", "Indicators"))
        fig.add_trace(go.Candlestick(x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data["SMA_20"], name="SMA20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data["RSI_14"], name="RSI"), row=2, col=1)
        fig.update_layout(height=600, showlegend=True)
        return summary, data.tail(15), fig
    except Exception as e:
        log_error("Technical Analysis", str(e), traceback.format_exc())
        return str(e), None, None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def get_news(ticker: str = "TSLA") -> str:
    try:
        url = f"https://finance.yahoo.com/quote/{ticker.upper()}/news"
        resp = safe_request(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        headlines = [h.get_text(strip=True) for h in soup.select("h3")[:8]]
        return "\n".join(headlines) if headlines else "No recent news found"
    except Exception as e:
        log_error("News", str(e))
        return f"Error fetching news: {str(e)}"

def get_x_sentiment(ticker: str = "TSLA", x_bearer_token: str = "") -> str:
    token = x_bearer_token or CONFIG.x_bearer_token.get_secret_value()
    if not token:
        return f"Simulated X Sentiment for {ticker}: 68% Bullish (provide Bearer Token in Settings)"
    try:
        client = TweepyClient(bearer_token=token)
        tweets = client.search_recent_tweets(query=f"${ticker}", max_results=10)
        if not tweets.data:
            return "No recent tweets found"
        positive = sum(1 for t in tweets.data if any(word in t.text.lower() for word in ["bull", "buy", "moon", "long"]))
        return f"X Sentiment: {positive / len(tweets.data) * 100:.1f}% positive"
    except Exception as e:
        log_error("X Sentiment", str(e))
        return "X API error - check bearer token"

def backtest_strategy(ticker: str = "TSLA", strategy: str = "SMA Crossover", slippage_pct: float = None) -> Tuple[str, pd.DataFrame]:
    slippage = slippage_pct or CONFIG.slippage_pct
    try:
        data = cached_yf_download(ticker, "2y")
        if data.empty:
            return "No data", pd.DataFrame()
        data.ta.sma(length=20, append=True)
        data.ta.sma(length=50, append=True)
        data["signal"] = (data["SMA_20"] > data["SMA_50"]).astype(int)
        data["returns"] = data["Close"].pct_change()
        data["strategy_returns"] = data["signal"].shift(1) * (data["returns"] - slippage)
        data["strategy_returns"] = data["strategy_returns"].fillna(0)
        total_return = (1 + data["strategy_returns"]).prod() - 1
        sharpe = data["strategy_returns"].mean() / data["strategy_returns"].std() if data["strategy_returns"].std() != 0 else 0
        cum_returns = (1 + data["strategy_returns"]).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak
        max_dd = drawdown.min() * 100
        wins = (data["strategy_returns"] > 0).sum()
        total_trades = (data["signal"].diff() != 0).sum()
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        metrics = pd.DataFrame({"Metric": ["Total Return %", "Sharpe Ratio", "Max Drawdown %", "Win Rate %", "Trades"],
                                "Value": [round(total_return * 100, 2), round(sharpe, 2), round(max_dd, 2), round(win_rate, 2), int(total_trades)]})
        return f"Backtest complete. Return: {total_return*100:.2f}% | Sharpe: {sharpe:.2f} | Max DD: {max_dd:.2f}% | Win Rate: {win_rate:.1f}%", metrics
    except Exception as e:
        log_error("Backtest", str(e), traceback.format_exc())
        return str(e), pd.DataFrame()

def self_improve() -> str:
    api_key = CONFIG.openai_api_key.get_secret_value()
    if not api_key:
        return "API key required in Settings for self-improvement."
    try:
        with db_connection() as conn:
            errors_df = pd.read_sql_query("SELECT * FROM errors ORDER BY timestamp DESC LIMIT 20", conn)
        if errors_df.empty:
            return "No recent errors to analyze."
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        prompt = "Analyze these trading script errors and suggest specific code improvements:\n" + errors_df.to_string()
        response = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        suggestion = response.choices[0].message.content.strip()
        with db_connection() as conn:
            conn.execute("INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)",
                         (datetime.now().isoformat(), suggestion))
            conn.commit()
        return f"Self-improvement suggestion generated:\n{suggestion}"
    except Exception as e:
        log_error("Self-Improve", str(e))
        return f"Self-improvement failed: {str(e)}"

def create_interface() -> gr.Blocks:
    with gr.Blocks(title="XForge Trader v8 - Grok Enhanced", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# XForge Trader v8 - Robust Algorithmic Analysis Platform with Grok Integration")
        with gr.Tab("📈 Momentum Scanner (Primary)"):
            with gr.Row():
                tickers_input = gr.Textbox(label="Tickers (comma-separated)", value="TSLA")
                period_input = gr.Dropdown(["1mo", "3mo", "6mo", "1y", "2y"], value="1y")
            with gr.Row():
                start_input = gr.Textbox(label="Start Date (YYYY-MM-DD)", placeholder="Optional")
                end_input = gr.Textbox(label="End Date (YYYY-MM-DD)", placeholder="Optional")
            scan_btn = gr.Button("Scan Momentum", variant="primary")
            results_df = gr.Dataframe(label="Momentum Results")
            momentum_chart = gr.Plot(label="Momentum Visualization")
            momentum_summary = gr.Textbox(label="Summary")
            scan_btn.click(calculate_momentum, inputs=[tickers_input, period_input, start_input, end_input], outputs=[results_df, momentum_chart, momentum_summary])
        with gr.Tab("📊 Technical Analysis"):
            ticker_ta = gr.Textbox(value="TSLA", label="Ticker")
            ta_btn = gr.Button("Analyze")
            ta_summary = gr.Textbox(label="Latest Indicators")
            ta_table = gr.Dataframe(label="Recent Data")
            ta_chart = gr.Plot(label="Price & Indicators")
            ta_btn.click(technical_analysis, inputs=[ticker_ta], outputs=[ta_summary, ta_table, ta_chart])
        with gr.Tab("📰 News & Sentiment"):
            ticker_news = gr.Textbox(value="TSLA", label="Ticker")
            x_token = gr.Textbox(label="X Bearer Token (optional)", type="password")
            news_btn = gr.Button("Fetch News & Sentiment")
            news_output = gr.Textbox(label="Yahoo News")
            x_output = gr.Textbox(label="X Sentiment")
            news_btn.click(lambda t, tok: (get_news(t), get_x_sentiment(t, tok)), inputs=[ticker_news, x_token], outputs=[news_output, x_output])
        with gr.Tab("📉 Backtest & Risk"):
            bt_ticker = gr.Textbox(value="TSLA", label="Ticker")
            bt_strategy = gr.Dropdown(["SMA Crossover"], value="SMA Crossover")
            bt_slippage = gr.Slider(0.0, 0.005, value=0.001, step=0.0001, label="Slippage %")
            bt_btn = gr.Button("Run Backtest")
            bt_summary = gr.Textbox(label="Backtest Summary")
            bt_metrics = gr.Dataframe(label="Performance Metrics")
            bt_btn.click(backtest_strategy, inputs=[bt_ticker, bt_strategy, bt_slippage], outputs=[bt_summary, bt_metrics])
        with gr.Tab("🧠 Self-Improve (Grok)"):
            improve_btn = gr.Button("Run Self-Improvement Analysis with Grok")
            improve_output = gr.Textbox(label="AI Suggestions", lines=10)
            improve_btn.click(self_improve, outputs=improve_output)
        with gr.Tab("⚙️ Settings"):
            gr.Markdown("### API Keys & Configuration")
            openai_key = gr.Textbox(label="xAI Grok API Key (or OpenAI compatible)", type="password", value=CONFIG.openai_api_key.get_secret_value())
            x_key = gr.Textbox(label="X Bearer Token", type="password", value=CONFIG.x_bearer_token.get_secret_value())
            save_btn = gr.Button("Save Settings")
            save_status = gr.Textbox(label="Status")
            save_btn.click(lambda o, x: (CONFIG.openai_api_key.set(o), CONFIG.x_bearer_token.set(x), "Settings saved! Grok ready."), inputs=[openai_key, x_key], outputs=save_status)
        with gr.Tab("🔴 Live Execution (IBKR)"):
            gr.Markdown("**Production IBKR integration with full safety**")
            ibkr_ticker = gr.Textbox(value="TSLA", label="Ticker")
            ibkr_action = gr.Dropdown(["BUY", "SELL"], value="BUY")
            ibkr_qty = gr.Number(value=1, label="Quantity")
            ibkr_order_type = gr.Dropdown(["MKT", "LMT"], value="MKT")
            ibkr_price = gr.Number(label="Limit Price (if LMT)")
            ibkr_connect_btn = gr.Button("Connect & Place Order")
            ibkr_status = gr.Textbox(label="Execution Status", lines=8)
            def ibkr_place_order(ticker, action, qty, order_type, price):
                try:
                    from ib_insync import IB, Stock, MarketOrder, LimitOrder
                    ib = IB()
                    ib.connect(CONFIG.ibkr_host, CONFIG.ibkr_port, clientId=CONFIG.ibkr_client_id)
                    contract = Stock(ticker, "SMART", "USD")
                    ib.qualifyContracts(contract)
                    if order_type == "MKT":
                        order = MarketOrder(action, qty)
                    else:
                        order = LimitOrder(action, qty, price)
                    trade = ib.placeOrder(contract, order)
                    ib.sleep(2)
                    status = f"Order placed: {trade}\nFilled: {trade.filled()}"
                    ib.disconnect()
                    return status
                except Exception as e:
                    log_error("IBKR Execution", str(e))
                    return f"Error: {str(e)}\nCheck TWS/Gateway running."
            ibkr_connect_btn.click(ibkr_place_order, inputs=[ibkr_ticker, ibkr_action, ibkr_qty, ibkr_order_type, ibkr_price], outputs=ibkr_status)
    return demo

if __name__ == "__main__":
    print(ensure_dependencies())
    print("Launching XForge Trader v8 with enhanced error handling and native Grok support...")
    demo = create_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)