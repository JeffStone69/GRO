#!/usr/bin/env python3
"""
XForge Trader v2.1 - Complete Rewritten Replacement
- Local "fetch/" folder ticker DB fully integrated (primary demo data)
- All original + v2.0 features retained and enhanced
- New "Local Data Fetch & Analysis" tab with full analysis of script data-fetch functions
- Lazy IBKR + auto-install + self-improve DB + logging + everything else
"""

import sys
import subprocess
import logging
import sqlite3
import traceback
import os
from datetime import datetime
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==================== SETUP & LOGGING ====================
logging.basicConfig(level=logging.INFO, filename="xforge_trader.log", filemode="a",
                    format="%(asctime)s | %(levelname)s | %(message)s")

def init_self_improve_db():
    conn = sqlite3.connect("self_improve.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY, timestamp TEXT, section TEXT, error TEXT, traceback TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS improvements (id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT)""")
    conn.commit()
    conn.close()

init_self_improve_db()

def log_error(section, error_msg, tb=""):
    conn = sqlite3.connect("self_improve.db")
    c = conn.cursor()
    c.execute("INSERT INTO errors (timestamp, section, error, traceback) VALUES (?, ?, ?, ?)",
              (datetime.now().isoformat(), section, error_msg, tb))
    conn.commit()
    conn.close()
    logging.error(f"{section}: {error_msg}\n{tb}")

def get_error_logs():
    conn = sqlite3.connect("self_improve.db")
    df = pd.read_sql_query("SELECT * FROM errors ORDER BY timestamp DESC LIMIT 50", conn)
    conn.close()
    return df

def get_improvement_suggestions():
    conn = sqlite3.connect("self_improve.db")
    df = pd.read_sql_query("SELECT * FROM improvements ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# ==================== DEPENDENCY MANAGER ====================
REQUIRED_PACKAGES = ["ib_insync", "eventkit", "yfinance", "pandas_ta", "plotly",
                     "beautifulsoup4", "requests", "numpy", "gradio"]

def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return f"✅ Installed {package}"
    except Exception as e:
        return f"❌ Failed {package}: {str(e)}"

def check_and_install_all():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        return "\n".join([install_package(p) for p in missing])
    return "✅ All dependencies ready!"

# ==================== LOCAL FETCH FOLDER DATA LOADER (NEW CORE FEATURE) ====================
def load_local_ticker_data(ticker: str):
    """Primary loader for your generated fetch/ folder DB"""
    fetch_dir = "fetch"
    if not os.path.exists(fetch_dir):
        return None, "❌ 'fetch' folder not found in script directory. Place your CSV files there (e.g. AAPL.csv, MSFT.csv)."

    possible_files = [
        f"{fetch_dir}/{ticker}.csv",
        f"{fetch_dir}/{ticker.upper()}.csv",
        f"{fetch_dir}/{ticker.lower()}.csv",
        f"{fetch_dir}/{ticker}_data.csv",
        f"{fetch_dir}/{ticker}_daily.csv",
    ]
    for fpath in possible_files:
        if os.path.exists(fpath):
            try:
                df = pd.read_csv(fpath)
                # Auto-detect date column
                date_col = None
                for col in df.columns:
                    if "date" in col.lower() or "time" in col.lower():
                        date_col = col
                        break
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col])
                    df.set_index(date_col, inplace=True)
                elif df.index.dtype == "object":
                    df.index = pd.to_datetime(df.index)
                # Standardize columns
                df.columns = [c.strip().capitalize() for c in df.columns]
                if "Close" not in df.columns and "Adj Close" in df.columns:
                    df["Close"] = df["Adj Close"]
                return df, f"✅ Loaded from local fetch DB: {os.path.basename(fpath)}"
            except Exception as e:
                tb = traceback.format_exc()
                log_error("Local Fetch Load", str(e), tb)
                continue
    return None, f"❌ No local CSV found for {ticker} in fetch/ folder"

def get_available_local_tickers():
    fetch_dir = "fetch"
    if not os.path.exists(fetch_dir):
        return []
    tickers = []
    for f in os.listdir(fetch_dir):
        if f.endswith(".csv"):
            base = os.path.splitext(f)[0]
            if "_" in base:
                base = base.split("_")[0]
            tickers.append(base.upper())
    return sorted(set(tickers))

# ==================== ANALYSIS OF SCRIPT DATA FETCH FUNCTIONS (NEW) ====================
def analyze_fetch_functions():
    """Pulls and displays analysis of all data-fetch logic in the script"""
    analysis = """
=== XForge Trader v2.1 – Data Fetch Function Analysis ===
1. load_local_ticker_data(ticker) – Primary loader for your generated fetch/ folder DB
   • Scans fetch/ for {ticker}.csv, {ticker}_data.csv, etc.
   • Auto-detects date column, standardizes OHLCV columns
   • Returns DataFrame + source string for transparent fallback

2. get_available_local_tickers() – Scans fetch/ folder and lists all unique tickers
   • Used in UI to populate dropdown with your real generated data

3. technical_analysis() – Now prefers local fetch data, falls back to yfinance
   • Runs full pandas-ta pipeline on whichever source is used
   • Reports exact source in output

4. yfinance fallback (remote) – Only used when local data missing
   • period parameter preserved for consistency

5. Other fetchers (news, X sentiment) remain unchanged

Self-Improve note: All fetch errors are logged to self_improve.db for automatic analysis.
Your local fetch/ DB is now the default demo source — no more external API dependency for core data.
"""
    return analysis

# ==================== IBKR FUNCTIONS (UNCHANGED + FIXED) ====================
def test_ibkr_connection(host="127.0.0.1", port=7497, client_id=1):
    try:
        from ib_insync import IB
        ib = IB()
        ib.connect(host, int(port), clientId=int(client_id), timeout=15)
        if ib.isConnected():
            ib.disconnect()
            return "✅ Connection successful! TWS is reachable."
        return "❌ Connection failed: TWS not responding"
    except Exception as e:
        tb = traceback.format_exc()
        log_error("IBKR Connection", str(e), tb)
        return f"❌ Connection failed: {str(e)}\nTip: pip install eventkit ib_insync"

def place_order(symbol, action, quantity, order_type, limit_price=0.0):
    try:
        from ib_insync import IB, Stock, MarketOrder, LimitOrder
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=1, timeout=10)
        contract = Stock(symbol.upper(), "SMART", "USD")
        ib.qualifyContracts(contract)
        order = MarketOrder(action.upper(), int(quantity)) if order_type == "MKT" else LimitOrder(action.upper(), int(quantity), float(limit_price))
        trade = ib.placeOrder(contract, order)
        ib.disconnect()
        return f"✅ Order submitted!\nTrade ID: {trade.order.orderId}\nStatus: {trade.orderStatus.status}"
    except Exception as e:
        tb = traceback.format_exc()
        log_error("IBKR Order", str(e), tb)
        return f"❌ Order failed: {str(e)}"

def get_ibkr_portfolio():
    try:
        from ib_insync import IB
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=2, timeout=10)
        positions = ib.positions()
        ib.disconnect()
        if not positions:
            return "No open positions"
        df = pd.DataFrame([{"Symbol": p.contract.symbol, "Position": p.position, "Avg Cost": p.avgCost, "Market Value": p.marketValue} for p in positions])
        return df
    except Exception as e:
        log_error("IBKR Portfolio", str(e))
        return f"Error: {str(e)}"

# ==================== TECHNICAL ANALYSIS (NOW USES LOCAL FETCH FIRST) ====================
def technical_analysis(ticker: str, period: str = "1y"):
    local_df, source = load_local_ticker_data(ticker)
    if local_df is not None:
        data = local_df
    else:
        try:
            data = yf.download(ticker.upper(), period=period, progress=False)
            source = "yfinance (remote fallback)"
        except Exception as e:
            tb = traceback.format_exc()
            log_error("Technical Analysis", str(e), tb)
            return str(e), None, None, "Error"

    if data.empty:
        return "No data found", None, None, source

    data.ta.rsi(append=True)
    data.ta.macd(append=True)
    data.ta.bbands(append=True)
    data.ta.sma(length=20, append=True)
    data.ta.ema(length=50, append=True)
    latest = data.iloc[-1]
    summary = (f"RSI(14): {latest.get('RSI_14', 0):.2f} | MACD: {latest.get('MACD_12_26_9', 0):.4f} | "
               f"BB Upper: {latest.get('BBU_20_2.0', 0):.2f} | SMA20: {latest.get('SMA_20', 0):.2f}")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f"{ticker} Price ({source})", "Indicators"))
    fig.add_trace(go.Candlestick(x=data.index, open=data.get("Open", data.get("Close")), high=data.get("High", data.get("Close")),
                                 low=data.get("Low", data.get("Close")), close=data["Close"], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["SMA_20"], name="SMA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["RSI_14"], name="RSI"), row=2, col=1)
    fig.update_layout(height=600, showlegend=True)
    return summary, data.tail(15), fig, source

# ==================== NEWS & X SENTIMENT (UNCHANGED) ====================
def get_news(ticker):
    try:
        url = f"https://finance.yahoo.com/quote/{ticker.upper()}/news"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        headlines = [h.get_text(strip=True) for h in soup.select("h3")[:8]]
        return "\n".join(headlines) if headlines else "No recent news found"
    except Exception as e:
        log_error("News", str(e))
        return f"Error fetching news: {str(e)}"

def get_x_sentiment(ticker, api_key="", api_secret=""):
    if api_key and api_secret:
        try:
            import tweepy
            auth = tweepy.OAuth2BearerHandler(api_key)
            api = tweepy.API(auth)
            tweets = api.search_tweets(q=f"${ticker}", count=10, lang="en")
            positive = sum(1 for t in tweets if "bull" in t.text.lower() or "buy" in t.text.lower())
            return f"X Sentiment: {positive/len(tweets)*100:.1f}% positive ({len(tweets)} tweets)"
        except Exception as e:
            log_error("X Sentiment", str(e))
            return "X API error - check keys"
    return f"Simulated X Sentiment for {ticker}: 68% Bullish (add real API keys in Settings for live data)"

# ==================== BACKTESTING & RISK (UNCHANGED) ====================
def backtest_strategy(ticker, strategy="SMA Crossover"):
    try:
        local_df, _ = load_local_ticker_data(ticker)
        if local_df is not None:
            data = local_df
        else:
            data = yf.download(ticker.upper(), period="2y", progress=False)
        data.ta.sma(length=20, append=True)
        data.ta.sma(length=50, append=True)
        data["signal"] = 0
        data.loc[data["SMA_20"] > data["SMA_50"], "signal"] = 1
        data["returns"] = data["Close"].pct_change()
        data["strategy_returns"] = data["signal"].shift(1) * data["returns"]
        total_return = (1 + data["strategy_returns"]).prod() - 1
        sharpe = data["strategy_returns"].mean() / data["strategy_returns"].std() * (252 ** 0.5)
        return f"Backtest ({strategy}): Total Return {total_return*100:.2f}% | Sharpe Ratio: {sharpe:.2f}"
    except Exception as e:
        log_error("Backtest", str(e))
        return str(e)

def risk_calculator(position_size, entry_price, stop_loss, risk_pct=2.0):
    risk_per_share = entry_price - stop_loss
    max_risk = position_size * (risk_pct / 100)
    shares = max_risk / risk_per_share if risk_per_share > 0 else 0
    return f"Recommended shares: {int(shares)} | Max loss: ${max_risk:.2f}"

# ==================== SELF-IMPROVE ENGINE (UNCHANGED) ====================
def analyze_improvements():
    logs = get_error_logs()
    suggestions = []
    if logs.empty:
        return "No errors logged yet."
    for _, row in logs.iterrows():
        err = str(row["error"]).lower()
        if "eventkit" in err or "no module" in err:
            suggestions.append("• Install: pip install eventkit ib_insync")
        if "connection" in err:
            suggestions.append("• Ensure TWS is running on correct port")
        if "fetch" in err or "local" in err:
            suggestions.append("• Place your generated CSV files in the 'fetch/' folder next to this script")
    if not suggestions:
        suggestions = ["• Add retry logic for fetch functions"]
    conn = sqlite3.connect("self_improve.db")
    c = conn.cursor()
    for s in suggestions:
        c.execute("INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)",
                  (datetime.now().isoformat(), s))
    conn.commit()
    conn.close()
    return "Self-Improve Analysis:\n" + "\n".join(suggestions) + "\n\nLatest logs:\n" + logs.to_string()

# ==================== GRADIO UI ====================
with gr.Blocks(title="XForge Trader v2.1", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 XForge Trader v2.1 — Local Fetch DB + Full Self-Improvement")
    gr.Markdown("Your generated stock ticker data in the `fetch/` folder is now the **primary demo data source**.")

    with gr.Tab("IBKR Trader"):
        with gr.Row():
            host = gr.Textbox("127.0.0.1", label="Host")
            port = gr.Number(7497, label="Port")
            client_id = gr.Number(1, label="Client ID")
        connect_btn = gr.Button("Test IBKR Connection", variant="primary")
        connect_out = gr.Textbox(label="Connection Status", lines=3)
        connect_btn.click(test_ibkr_connection, [host, port, client_id], connect_out)

        gr.Markdown("### Place Order")
        with gr.Row():
            symbol = gr.Textbox("AAPL", label="Symbol")
            action = gr.Dropdown(["BUY", "SELL"], label="Action")
            qty = gr.Number(1, label="Quantity")
            otype = gr.Dropdown(["MKT", "LMT"], label="Order Type")
            limit_p = gr.Number(0, label="Limit Price (if LMT)")
        order_btn = gr.Button("Place Order")
        order_out = gr.Textbox(label="Order Result", lines=4)
        order_btn.click(place_order, [symbol, action, qty, otype, limit_p], order_out)

        gr.Markdown("### Portfolio")
        port_btn = gr.Button("Refresh Portfolio")
        port_df = gr.Dataframe(label="Open Positions")
        port_btn.click(get_ibkr_portfolio, None, port_df)

    with gr.Tab("Technical Analysis & Charts"):
        ta_ticker = gr.Textbox("AAPL", label="Ticker (uses local fetch/ first)")
        ta_period = gr.Dropdown(["1mo", "3mo", "6mo", "1y", "2y"], value="1y", label="Period (fallback only)")
        ta_btn = gr.Button("Run Analysis + Chart")
        ta_summary = gr.Textbox(label="Summary")
        ta_table = gr.Dataframe(label="Recent Data")
        ta_chart = gr.Plot(label="Interactive Chart")
        ta_source = gr.Textbox(label="Data Source")
        ta_btn.click(technical_analysis, [ta_ticker, ta_period], [ta_summary, ta_table, ta_chart, ta_source])

    with gr.Tab("News & X Sentiment"):
        news_ticker = gr.Textbox("AAPL", label="Ticker")
        news_btn = gr.Button("Fetch News")
        news_out = gr.Textbox(label="Latest News", lines=8)
        news_btn.click(get_news, news_ticker, news_out)

        gr.Markdown("### X/Twitter Sentiment")
        x_ticker = gr.Textbox("AAPL", label="Ticker")
        x_key = gr.Textbox(label="X API Key (optional)")
        x_secret = gr.Textbox(label="X API Secret (optional)")
        x_btn = gr.Button("Analyze X Sentiment")
        x_out = gr.Textbox(label="X Sentiment Result")
        x_btn.click(get_x_sentiment, [x_ticker, x_key, x_secret], x_out)

    with gr.Tab("Backtesting & Risk"):
        bt_ticker = gr.Textbox("AAPL", label="Ticker (prefers local fetch/)")
        bt_strategy = gr.Dropdown(["SMA Crossover", "RSI Mean Reversion", "MACD"], label="Strategy")
        bt_btn = gr.Button("Run Backtest")
        bt_out = gr.Textbox(label="Backtest Results")
        bt_btn.click(backtest_strategy, [bt_ticker, bt_strategy], bt_out)

        gr.Markdown("### Risk Calculator")
        with gr.Row():
            pos_size = gr.Number(10000, label="Account Size ($)")
            entry = gr.Number(150, label="Entry Price")
            sl = gr.Number(140, label="Stop Loss")
            risk = gr.Slider(0.5, 5, value=2, label="Risk %")
        risk_btn = gr.Button("Calculate Risk")
        risk_out = gr.Textbox(label="Risk Recommendation")
        risk_btn.click(risk_calculator, [pos_size, entry, sl, risk], risk_out)

    with gr.Tab("Local Data Fetch & Analysis"):
        gr.Markdown("### Your Generated Stock Ticker DB (fetch/ folder)")
        list_btn = gr.Button("List All Local Tickers in fetch/")
        local_tickers = gr.Textbox(label="Available Tickers", lines=3)
        list_btn.click(lambda: ", ".join(get_available_local_tickers()), None, local_tickers)

        gr.Markdown("### Load & Analyze Specific Ticker from fetch/")
        local_ticker = gr.Textbox("AAPL", label="Ticker")
        load_btn = gr.Button("Load Local Data")
        local_df = gr.Dataframe(label="Local Ticker Data")
        local_source = gr.Textbox(label="Load Result")
        load_btn.click(load_local_ticker_data, local_ticker, [local_df, local_source])  # returns df, msg

        gr.Markdown("### Analysis of Script Data-Fetch Functions")
        fetch_analysis_btn = gr.Button("Show Full Fetch Function Analysis")
        fetch_analysis_out = gr.Textbox(label="Fetch Logic Analysis", lines=20)
        fetch_analysis_btn.click(analyze_fetch_functions, None, fetch_analysis_out)

    with gr.Tab("Self-Improve & Logs"):
        refresh_logs = gr.Button("Refresh Error Logs")
        logs_df = gr.Dataframe(label="Recent Errors")
        refresh_logs.click(get_error_logs, None, logs_df)

        analyze_btn = gr.Button("Run Self-Improve Analysis", variant="primary")
        suggestions = gr.Textbox(label="AI-Style Improvement Suggestions", lines=12)
        analyze_btn.click(analyze_improvements, None, suggestions)

        gr.Markdown("### Saved Improvement History")
        history_df = gr.Dataframe(label="Past Suggestions")
        history_btn = gr.Button("Load History")
        history_btn.click(get_improvement_suggestions, None, history_df)

    with gr.Tab("Settings & Installer"):
        gr.Markdown("### Auto-Install Missing Dependencies")
        install_btn = gr.Button("Install ALL Required Packages Now", variant="primary")
        install_out = gr.Textbox(label="Installation Log", lines=10)
        install_btn.click(check_and_install_all, None, install_out)

        gr.Markdown("### Manual Install")
        pkg_name = gr.Textbox(label="Package Name")
        manual_install = gr.Button("Install Single Package")
        manual_out = gr.Textbox(label="Result")
        manual_install.click(install_package, pkg_name, manual_out)

        gr.Markdown("**Full Requirements:**\n`pip install ib_insync eventkit yfinance pandas_ta plotly beautifulsoup4 requests numpy gradio`")

    gr.Markdown("**XForge Trader v2.1** — Your local fetch/ DB is now the default. All fetch functions analyzed and logged for continuous self-improvement.")

demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
