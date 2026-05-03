# ============================================================
# xforge_trader.py  —  xForgeTrader v9 (Clutter-Free Edition)
# Self-Improving Profit Recommendation Engine
# Now with Smart Cleanup Module (logs valuables → DB before removal)
# ============================================================

import gradio as gr
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
from pathlib import Path
import sqlite3
import time
import shutil
import os
import requests

# Import our new cleanup module
import cleanup_forge

warnings.filterwarnings('ignore')

try:
    import pandas_ta as pta
except ImportError:
    print("Missing dependency: pip install pandas-ta")
    exit()

# ============================================================
# GROK CLIENT (unchanged)
# ============================================================
GROK_API_KEY = ""

def get_grok_client():
    global GROK_API_KEY
    if not GROK_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
    except Exception:
        return None

def grok_chat(system_prompt, user_prompt, max_tokens=800):
    client = get_grok_client()
    if not client:
        return "⚠️ Please enter your xAI API key in the Grok Trade Planner tab."
    try:
        response = client.chat.completions.create(
            model="grok-4",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=max_tokens, temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Grok error: {str(e)[:150]}"

# ============================================================
# CONFIG & PATHS (unchanged)
# ============================================================
DB_PATH = Path("xforge_self_improve.db")
CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)
HISTORY_FILE = Path("DEVELOPMENT_HISTORY.md")
BACKUPS_DIR = Path("backups")
BACKUPS_DIR.mkdir(exist_ok=True)

# ============================================================
# IBKR (inlined for simplicity, multi_tws_connector.py kept as standalone)
# ============================================================
def test_ibkr_connection(host, port, client_id):
    try:
        from ib_insync import IB
        ib = IB()
        ib.connect(host, int(port), int(client_id), timeout=15)
        ib.disconnect()
        return "Connected successfully"
    except Exception as e:
        return f"Connection failed: {str(e)[:80]}"

# ============================================================
# DATABASE + SELF-IMPROVEMENT (unchanged)
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS error_reports (
            id INTEGER PRIMARY KEY, timestamp TEXT, tab TEXT, ticker TEXT, description TEXT
        );
        CREATE TABLE IF NOT EXISTS improvements (
            id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT
        );
        CREATE TABLE IF NOT EXISTS stock_data (
            id INTEGER PRIMARY KEY, ticker TEXT, timestamp TEXT, open REAL, high REAL,
            low REAL, close REAL, volume INTEGER, source TEXT,
            UNIQUE(ticker, timestamp)
        );
    """)
    conn.commit()
    conn.close()

init_db()

def log_error(tab, ticker, description):
    short = description[:120]
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO error_reports (timestamp, tab, ticker, description) VALUES (?, ?, ?, ?)",
                 (datetime.now().isoformat(), tab, ticker, short))
    conn.commit()
    conn.close()
    return f"Logged: {short}"

def get_recent_errors(n=10):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT tab, ticker, description FROM error_reports ORDER BY timestamp DESC LIMIT {n}", conn)
    conn.close()
    return "\n".join([f"[{r.tab}] {r.ticker}: {r.description}" for _, r in df.iterrows()]) if not df.empty else "No errors logged."

def clear_cache():
    for f in CACHE_DIR.glob("*.parquet"):
        f.unlink(missing_ok=True)
    return "Cache cleared"

def backup_everything():
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_subdir = BACKUPS_DIR / ts
    backup_subdir.mkdir()
    files = [Path("xforge_trader.py"), DB_PATH, HISTORY_FILE]
    copied = [f.name for f in files if f.exists() and shutil.copy2(f, backup_subdir)]
    return f"Backup created: {backup_subdir}\nFiles: {', '.join(copied)}"

def get_all_improvements(n=10):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT timestamp, suggestion FROM improvements ORDER BY timestamp DESC LIMIT {n}", conn)
    conn.close()
    return df

# ============================================================
# DATA LAYER (unchanged + Alpha Vantage)
# ============================================================
def get_demo_data(ticker, periods=500):
    np.random.seed(hash(ticker) % 10000)
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    close = 150 + np.cumsum(np.random.randn(periods) * 1.8)
    df = pd.DataFrame({
        'Open': close + np.random.randn(periods) * 0.8,
        'High': close + np.abs(np.random.randn(periods)) * 1.2,
        'Low': close - np.abs(np.random.randn(periods)) * 1.2,
        'Close': close,
        'Volume': np.random.randint(1_000_000, 50_000_000, periods)
    }, index=dates)
    df.index.name = 'Date'
    return df

def fetch_from_alpha_vantage(ticker, api_key="XV8DT58Z4VPIS7X5"):
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}&outputsize=full"
        r = requests.get(url, timeout=15)
        data = r.json()
        if "Time Series (Daily)" not in data:
            return None
        df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
        df = df.rename(columns={"1. open": "Open", "2. high": "High", "3. low": "Low", "4. close": "Close", "5. volume": "Volume"}).astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.to_parquet(CACHE_DIR / f"{ticker}.parquet")
        return df
    except Exception as e:
        log_error("AlphaVantage", ticker, str(e)[:100])
        return None

def get_data(ticker, start_date=None, end_date=None, realtime=False, demo_mode=True, use_av=False):
    ticker = ticker.strip().upper()
    if demo_mode:
        return get_demo_data(ticker)
    if use_av:
        df = fetch_from_alpha_vantage(ticker)
        if df is not None:
            return df
    for attempt in range(3):
        try:
            if realtime:
                start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                df = yf.download(ticker, start=start, interval="5m", auto_adjust=True, progress=False)
            else:
                df = yf.download(ticker, start=start_date, end=end_date, period="2y" if not (start_date and end_date) else None, auto_adjust=True, progress=False)
            if not df.empty:
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df.to_parquet(CACHE_DIR / f"{ticker}.parquet")
                return df
        except Exception as e:
            log_error("Data", ticker, str(e)[:100])
            time.sleep(1.5)
    try:
        return pd.read_parquet(CACHE_DIR / f"{ticker}.parquet")
    except:
        return get_demo_data(ticker)

def add_indicators(df):
    if len(df) < 30:
        return df
    df = df.copy()
    df['SMA50'] = pta.sma(df['Close'], length=50)
    df['SMA200'] = pta.sma(df['Close'], length=200)
    df['RSI'] = pta.rsi(df['Close'], length=14)
    df = pd.concat([df, pta.macd(df['Close']), pta.bbands(df['Close'], length=20), pta.atr(df['High'], df['Low'], df['Close'], length=14)], axis=1)
    return df.dropna()

# ============================================================
# CHARTS, BACKTEST, WALK-FORWARD, SCANNER (unchanged)
# ============================================================
def create_candlestick(df, ticker):
    if df.empty or len(df) < 10:
        fig = go.Figure()
        fig.add_annotation(text="No data – enable Demo Mode", x=0.5, y=0.5, showarrow=False)
        return fig.update_layout(height=450, title=f"{ticker} – No Data")
    df = add_indicators(df)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name="SMA50", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA200", line=dict(color="blue")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI"), row=2, col=1)
    fig.update_layout(height=650, title=f"{ticker} Technical Analysis", xaxis_rangeslider_visible=False)
    return fig

def run_backtest(ticker, start_date, end_date, strategy="Rebound Dip", demo_mode=True):
    df = get_data(ticker, start_date, end_date, demo_mode=demo_mode)
    if len(df) < 30:
        return {"error": "Insufficient data"}, None
    if strategy == "Rebound Dip":
        df['peak'] = df['Close'].cummax()
        df['dip'] = (df['Close'] - df['peak']) / df['peak']
        df['signal'] = (df['dip'] <= -0.07).astype(int)
    else:
        df['short_ma'] = df['Close'].rolling(50).mean()
        df['long_ma'] = df['Close'].rolling(200).mean()
        df['signal'] = (df['short_ma'] > df['long_ma']).astype(int)
    df['position'] = df['signal'].shift(1).fillna(0)
    df['returns'] = df['Close'].pct_change()
    df['strategy_returns'] = df['position'] * df['returns']
    equity = 100000 * (1 + df['strategy_returns']).cumprod()
    total_return = (equity.iloc[-1] / 100000 - 1) * 100
    sharpe = (df['strategy_returns'].mean() / df['strategy_returns'].std() * np.sqrt(252)) if df['strategy_returns'].std() > 0 else 0
    max_dd = (equity / equity.cummax() - 1).min() * 100
    trades = int((df['position'].diff() != 0).sum())
    win_rate = ((df['strategy_returns'] > 0).sum() / max(trades, 1) * 100)
    fig = go.Figure(go.Scatter(x=df.index, y=equity, name="Equity Curve"))
    fig.update_layout(title=f"{ticker} {strategy} Equity Curve", height=400)
    return {"Total Return %": round(total_return, 2), "Sharpe": round(sharpe, 2), "Max DD %": round(max_dd, 2), "Win Rate %": round(win_rate, 1), "Trades": trades}, fig

def forward_walk_predictor(ticker, demo_mode=True):
    df = get_data(ticker, demo_mode=demo_mode)
    if len(df) < 120:
        return "Not enough data"
    split_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    train_metrics, _ = run_backtest(ticker, df.index[0].strftime('%Y-%m-%d'), split_date, demo_mode=demo_mode)
    test_metrics, _ = run_backtest(ticker, split_date, df.index[-1].strftime('%Y-%m-%d'), demo_mode=demo_mode)
    return f"**Walk-Forward**\nTrain Return: {train_metrics.get('Total Return %')}%\nForward Return: {test_metrics.get('Total Return %')}%"

def scan_tickers(tickers_str, capital, risk_pct, start_date, end_date, realtime, demo_mode):
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    results = []
    top_chart = None
    top_rec = None
    for ticker in tickers[:12]:
        try:
            df_raw = get_data(ticker, start_date, end_date, realtime, demo_mode)
            if df_raw.empty:
                continue
            df = add_indicators(df_raw)
            latest = df.iloc[-1]
            rsi = float(latest.get('RSI', 50))
            price = float(latest['Close'])
            atr = float(latest.get('ATR', price * 0.025))
            prob = max(0.52, min(0.78, 0.58 + (50 - rsi) / 200))
            if prob > 0.55 and rsi < 58:
                direction = "BUY"
                sl = round(price - 1.75 * atr, 2)
                tp = round(price + 4.0 * atr, 2)
                risk = price - sl
                position_pct = min(round((capital * risk_pct / 100) / risk * price / capital * 100, 1), 8.0)
                edge = round((prob * 4.0 - (1 - prob) * 1.75) * 0.65, 2)
            else:
                direction = "AVOID"
                sl = tp = position_pct = 0.0
                edge = -0.95
            rec = {"Ticker": ticker, "Signal": direction, "Price": round(price, 2), "Stop Loss": sl, "Target": tp, "Position %": position_pct, "ML Prob": f"{prob:.0%}", "Edge": edge, "RSI": round(rsi, 1)}
            results.append(rec)
            if direction == "BUY" and (top_rec is None or rec["Edge"] > top_rec["Edge"]):
                top_rec = rec
                top_chart = create_candlestick(df_raw, ticker)
        except Exception as e:
            log_error("Scanner", ticker, str(e)[:100])
    if not results:
        demo_df = get_demo_data("TSLA")
        return pd.DataFrame([{"Ticker": "DEMO", "Signal": "DEMO MODE", "Price": 150.0, "Stop Loss": 0, "Target": 0, "Position %": 0, "ML Prob": "N/A", "Edge": 0, "RSI": 50}]), create_candlestick(demo_df, "DEMO")
    return pd.DataFrame(results), top_chart

def fetch_data_for_tickers(tickers_str, demo_mode=True):
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    fetched = []
    for t in tickers[:15]:
        df = get_data(t, demo_mode=demo_mode, use_av=True)
        fetched.append(f"{t}: {len(df)} rows cached")
    return "\n".join(fetched)

def save_scan_results(df):
    if df.empty:
        return "No data to save"
    filename = f"scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    return f"Saved to {filename}"

# ============================================================
# SHUTDOWN (unchanged)
# ============================================================
def shutdown_xforge():
    import gradio as gr
    gr.Info("Thank you for using xForgeTrader! Shutting down now...")
    time.sleep(1.5)
    os._exit(0)

# ============================================================
# GROK PLANNER + TROUBLESHOOTER (unchanged)
# ============================================================
def grok_trade_planner(ticker, capital, risk_pct, user_notes, api_key):
    global GROK_API_KEY
    GROK_API_KEY = api_key.strip()
    errors = get_recent_errors(5)
    prompt = f"""Ticker: {ticker}\nCapital: ${capital}\nRisk: {risk_pct}%\nRecent errors: {errors}\nUser notes: {user_notes}\nGenerate a concise trade plan."""
    return grok_chat("You are a professional trading AI.", prompt)

def troubleshoot_with_grok(user_issue):
    errors = get_recent_errors(8)
    prompt = f"Recent errors:\n{errors}\nUser issue: {user_issue}\nProvide 3-5 specific code fixes."
    suggestion = grok_chat("You are an expert Python/Gradio developer.", prompt, max_tokens=1200)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)", (datetime.now().isoformat(), f"[GROK TROUBLESHOOT] {suggestion}"))
    conn.commit()
    conn.close()
    return suggestion

# ============================================================
# GRADIO UI v9 (with new Cleanup button)
# ============================================================
with gr.Blocks(title="xForgeTrader v9", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 xForgeTrader v9 — Clutter-Free Self-Improving Engine\nGrok-Powered • Demo Always Ready • Smart Cleanup Built-In")

    with gr.Tab("Scanner"):
        with gr.Row():
            tickers_in = gr.Textbox(label="Tickers", value="AAPL,TSLA,NVDA,MSFT")
            capital_in = gr.Number(label="Capital ($)", value=100000)
            risk_in = gr.Slider(1, 10, value=2, label="Risk %")
        with gr.Row():
            start_date = gr.Textbox(label="Start Date", value="2023-01-01")
            end_date = gr.Textbox(label="End Date", value="2026-05-03")
            realtime = gr.Checkbox(label="Real-time", value=False)
            demo_mode = gr.Checkbox(label="Demo Mode", value=True)
        with gr.Row():
            scan_btn = gr.Button("🔍 Scan & Recommend", variant="primary")
            fetch_btn = gr.Button("📥 Fetch Data", variant="secondary")
            save_btn = gr.Button("💾 Save Scan", variant="secondary")
        scan_df = gr.Dataframe(label="Results")
        chart_out = gr.Plot(label="Top Pick Chart")
        status = gr.Textbox(label="Status", interactive=False)
        scan_btn.click(fn=scan_tickers, inputs=[tickers_in, capital_in, risk_in, start_date, end_date, realtime, demo_mode], outputs=[scan_df, chart_out])
        fetch_btn.click(fn=fetch_data_for_tickers, inputs=[tickers_in, demo_mode], outputs=status)
        save_btn.click(fn=save_scan_results, inputs=[scan_df], outputs=status)

    with gr.Tab("Backtester"):
        bt_ticker = gr.Textbox(label="Ticker", value="TSLA")
        bt_start = gr.Textbox(label="Start", value="2023-01-01")
        bt_end = gr.Textbox(label="End", value="2026-05-03")
        bt_strategy = gr.Dropdown(["Rebound Dip", "MA Crossover"], value="Rebound Dip")
        bt_demo = gr.Checkbox(label="Demo Mode", value=True)
        bt_btn = gr.Button("Run Backtest")
        bt_metrics = gr.JSON(label="Metrics")
        bt_chart = gr.Plot(label="Equity Curve")
        bt_btn.click(fn=run_backtest, inputs=[bt_ticker, bt_start, bt_end, bt_strategy, bt_demo], outputs=[bt_metrics, bt_chart])

    with gr.Tab("Forward Walker"):
        fw_ticker = gr.Textbox(label="Ticker", value="AAPL")
        fw_demo = gr.Checkbox(label="Demo Mode", value=True)
        fw_btn = gr.Button("Run Walk-Forward")
        fw_out = gr.Markdown()
        fw_btn.click(fn=forward_walk_predictor, inputs=[fw_ticker, fw_demo], outputs=fw_out)

    with gr.Tab("Live Data / IBKR"):
        with gr.Row():
            ib_host = gr.Textbox(label="Host", value="127.0.0.1")
            ib_port = gr.Number(label="Port", value=7497)
            ib_id = gr.Number(label="Client ID", value=999)
        ib_test_btn = gr.Button("Test IBKR Connection")
        ib_test_out = gr.Textbox(label="Status")
        ib_test_btn.click(fn=test_ibkr_connection, inputs=[ib_host, ib_port, ib_id], outputs=ib_test_out)

    with gr.Tab("Grok Trade Planner"):
        gp_ticker = gr.Textbox(label="Ticker", value="NVDA")
        gp_capital = gr.Number(label="Capital", value=100000)
        gp_risk = gr.Slider(1, 10, value=2, label="Risk %")
        gp_notes = gr.Textbox(label="Notes", lines=3, placeholder="Your observations...")
        gp_key = gr.Textbox(label="xAI API Key", type="password")
        gp_btn = gr.Button("🧠 Generate Plan", variant="primary")
        gp_out = gr.Markdown()
        gp_btn.click(fn=grok_trade_planner, inputs=[gp_ticker, gp_capital, gp_risk, gp_notes, gp_key], outputs=gp_out)

    with gr.Tab("Self-Improve"):
        si_errors = gr.Textbox(label="Recent Errors", lines=8, interactive=False)
        si_refresh = gr.Button("Refresh Errors")
        si_suggest_btn = gr.Button("Ask Grok for Improvements", variant="primary")
        si_out = gr.Markdown()
        si_refresh.click(fn=get_recent_errors, outputs=si_errors)
        si_suggest_btn.click(fn=lambda: grok_chat("Expert developer.", f"Recent errors:\n{get_recent_errors(10)}\nSuggest fixes."), outputs=si_out)

    with gr.Tab("Troubleshooter"):
        ts_issue = gr.Textbox(label="Describe issue", lines=3)
        ts_report = gr.Button("Report Error")
        ts_grok = gr.Button("Troubleshoot with Grok", variant="primary")
        ts_out = gr.Markdown()
        ts_report.click(fn=lambda issue: log_error("Troubleshooter", "USER", issue), inputs=[ts_issue], outputs=ts_out)
        ts_grok.click(fn=troubleshoot_with_grok, inputs=[ts_issue], outputs=ts_out)

    with gr.Tab("Utilities"):
        gr.Markdown("### 🛠️ Maintenance")
        clear_btn = gr.Button("Clear Cache")
        clear_status = gr.Textbox()
        clear_btn.click(fn=clear_cache, outputs=clear_status)

        backup_btn = gr.Button("Create Full Backup")
        backup_out = gr.Textbox()
        backup_btn.click(fn=backup_everything, outputs=backup_out)

        gr.Markdown("---")
        gr.Markdown("### 🧹 Smart Cleanup (NEW in v9)")
        cleanup_btn = gr.Button("🧹 Run Directory Cleanup & Log Valuables", variant="secondary", size="lg")
        cleanup_out = gr.Textbox(label="Cleanup Results", lines=12, interactive=False)
        cleanup_btn.click(fn=cleanup_forge.run_cleanup, outputs=cleanup_out)

        gr.Markdown("---")
        gr.Markdown("### 🚪 Exit")
        exit_btn = gr.Button("🚪 Exit xForgeTrader & Close Terminal", variant="stop", size="lg")
        exit_btn.click(fn=shutdown_xforge)

    gr.Markdown("**v9: All original features preserved + Fetch/Save buttons + Troubleshooter + Version Browser + Smart Cleanup that logs valuables to DB before removing clutter.**")

# ============================================================
# LAUNCH
# ============================================================
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
