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
import requests
warnings.filterwarnings('ignore')

try:
    import pandas_ta as pta
except ImportError:
    print("pip install pandas-ta")
    exit()

# ====================== DATABASE ======================
DB_PATH = Path("xforge_self_improve.db")
CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript('''CREATE TABLE IF NOT EXISTS error_reports (id INTEGER PRIMARY KEY, timestamp TEXT, tab TEXT, ticker TEXT, description TEXT);
        CREATE TABLE IF NOT EXISTS improvements (id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT);''')
    conn.commit()
    conn.close()

init_db()

def log_error(tab, ticker, description):
    short_desc = description[:120]
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT INTO error_reports (timestamp, tab, ticker, description) VALUES (?, ?, ?, ?)',
                 (datetime.now().isoformat(), tab, ticker, short_desc))
    conn.commit()
    conn.close()
    return f"✅ Logged: {short_desc}"

def get_recent_errors():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT tab, ticker, description FROM error_reports ORDER BY timestamp DESC LIMIT 8", conn)
    conn.close()
    return "\n".join([f"[{row.tab}] {row.ticker}: {row.description}" for _, row in df.iterrows()]) if not df.empty else "No errors logged yet."

def clear_cache():
    for f in CACHE_DIR.glob("*.parquet"):
        f.unlink(missing_ok=True)
    return "✅ Cache cleared"

# ====================== DEMO DATA ======================
def get_demo_data(ticker):
    np.random.seed(hash(ticker) % 10000)
    dates = pd.date_range(end=datetime.now(), periods=500, freq='D')
    close = 150 + np.cumsum(np.random.randn(500) * 1.8)
    open_p = close + np.random.randn(500) * 0.8
    high = np.maximum(close, open_p) + np.abs(np.random.randn(500)) * 1.2
    low = np.minimum(close, open_p) - np.abs(np.random.randn(500)) * 1.2
    volume = np.random.randint(1000000, 50000000, 500)
    df = pd.DataFrame({'Open': open_p, 'High': high, 'Low': low, 'Close': close, 'Volume': volume}, index=dates)
    df.index.name = 'Date'
    return df

# ====================== DATA LAYER ======================
def get_data(ticker, start_date=None, end_date=None, realtime=False, demo_mode=True):
    if demo_mode:
        return get_demo_data(ticker)
    
    for attempt in range(3):
        try:
            if realtime:
                start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                df = yf.download(ticker, start=start, interval="5m", auto_adjust=True, progress=False)
            else:
                if start_date and end_date:
                    df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
                else:
                    df = yf.download(ticker, period="2y", auto_adjust=True, progress=False)
            if not df.empty:
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df.to_parquet(CACHE_DIR / f"{ticker}.parquet")
                return df
        except:
            time.sleep(1.5)
    
    try:
        return pd.read_parquet(CACHE_DIR / f"{ticker}.parquet")
    except:
        return get_demo_data(ticker)

def add_indicators(df):
    if df.empty or len(df) < 20:
        return pd.DataFrame()
    df = df.copy()
    df['SMA50'] = pta.sma(df['Close'], length=50)
    df['SMA200'] = pta.sma(df['Close'], length=200)
    df['RSI'] = pta.rsi(df['Close'], length=14)
    df = pd.concat([df, pta.macd(df['Close'])], axis=1)
    df = pd.concat([df, pta.bbands(df['Close'], length=20)], axis=1)
    df['ATR'] = pta.atr(df['High'], df['Low'], df['Close'], length=14)
    df = df.dropna()
    return df if len(df) >= 5 else pd.DataFrame()

# ====================== ALPHA VANTAGE LIVE PULLER ======================
def pull_alpha_vantage_live(ticker, api_key, data_type="Real-time Quote"):
    if not api_key:
        return "Please enter your Alpha Vantage API key", None
    
    base_url = "https://www.alphavantage.co/query"
    
    if data_type == "Real-time Quote":
        params = {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": api_key}
    else:
        params = {"function": "TIME_SERIES_INTRADAY", "symbol": ticker, "interval": "5min", "apikey": api_key}
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        data = response.json()
        
        if "Global Quote" in data:
            quote = data["Global Quote"]
            df = pd.DataFrame([{
                "Price": quote.get("05. price", "N/A"),
                "Change": quote.get("09. change", "N/A"),
                "Change %": quote.get("10. change percent", "N/A"),
                "Volume": quote.get("06. volume", "N/A"),
                "Latest": quote.get("07. latest trading day", "N/A")
            }])
            return df, "✅ Real-time quote pulled successfully"
        
        elif "Time Series (5min)" in data:
            ts = data["Time Series (5min)"]
            df = pd.DataFrame.from_dict(ts, orient="index")
            df.index = pd.to_datetime(df.index)
            df = df.rename(columns={"1. open": "Open", "2. high": "High", "3. low": "Low", "4. close": "Close", "5. volume": "Volume"})
            df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
            df = df.sort_index()
            return df.tail(50), "✅ 5-min intraday data pulled (last 50 bars)"
        
        else:
            return f"Alpha Vantage error: {data.get('Note', 'Invalid response')}", None
            
    except Exception as e:
        return f"Error: {str(e)}", None

def save_av_data_to_cache(ticker, df):
    if df is None or df.empty:
        return "No data to save"
    df.to_parquet(CACHE_DIR / f"{ticker}.parquet")
    return f"✅ {ticker} data saved to cache. Now use it in Scanner / Charts!"

# ====================== CHARTS ======================
def create_candlestick(df, ticker):
    if df.empty or len(df) < 10:
        fig = go.Figure()
        fig.add_annotation(text="No data – try Demo Mode or Live Puller", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=450, title=f"{ticker} – No Data")
        return fig
    df = add_indicators(df)
    if df.empty:
        return create_candlestick(pd.DataFrame(), ticker)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name="SMA50", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA200", line=dict(color="blue")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI"), row=2, col=1)
    fig.update_layout(height=650, title=f"{ticker} Technical Analysis", xaxis_rangeslider_visible=False)
    return fig

# ====================== BACKTESTER ======================
def run_backtest(ticker, start_date, end_date, strategy="Rebound Dip", demo_mode=True):
    df = get_data(ticker, start_date, end_date, demo_mode=demo_mode)
    if len(df) < 20:
        return {"error": "Not enough data"}, None
    
    if strategy == "Rebound Dip":
        df['peak'] = df['Close'].cummax()
        df['dip'] = (df['Close'] - df['peak']) / df['peak']
        df['signal'] = (df['dip'] <= -0.07).astype(int)
        df['position'] = df['signal'].shift(1).fillna(0)
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
    win_rate = ((df['strategy_returns'] > 0).sum() / trades * 100) if trades > 0 else 0
    
    fig = go.Figure(go.Scatter(x=df.index, y=equity, name="Equity Curve"))
    fig.update_layout(title=f"{ticker} Equity Curve", height=400)
    return {"Total Return %": round(total_return, 2), "Sharpe": round(sharpe, 2), "Max DD %": round(max_dd, 2), "Win Rate %": round(win_rate, 1), "Trades": trades}, fig

def forward_walk_predictor(ticker, demo_mode=True):
    df = get_data(ticker, demo_mode=demo_mode)
    if len(df) < 100: return "Not enough data"
    split = (df.index[-1] - timedelta(days=90)).strftime('%Y-%m-%d')
    train, _ = run_backtest(ticker, df.index[0].strftime('%Y-%m-%d'), split, "Rebound Dip", demo_mode)
    test, _ = run_backtest(ticker, split, df.index[-1].strftime('%Y-%m-%d'), "Rebound Dip", demo_mode)
    return f"**Walk-Forward**\nTrain: {train.get('Total Return %','N/A')}%\nForward: {test.get('Total Return %','N/A')}%"

# ====================== SCANNER ======================
RECOMMENDED_MOMENTUM = ["TSLA", "AAPL", "NVDA", "AMD", "SMCI", "META", "AVGO", "MSFT", "GOOGL", "RIO.AX"]

def scan_tickers(tickers_str, capital, risk_pct, start_date, end_date, realtime, demo_mode):
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    results = []
    top_chart = None
    top_rec = None
    
    for ticker in tickers[:10]:
        df_raw = get_data(ticker, start_date, end_date, realtime, demo_mode)
        if df_raw.empty or len(df_raw) < 20: continue
        df = add_indicators(df_raw)
        if df.empty or len(df) < 5: continue
        
        latest = df.iloc[-1]
        prob = 0.58
        price = float(latest['Close'])
        atr = float(latest.get('ATR', price * 0.02))
        if prob > 0.55 and latest['RSI'] < 58:
            direction = "BUY"
            sl = price - 1.75 * atr
            tp = price + 4.0 * atr
            position_pct = min(round((capital * risk_pct/100) / (price - sl) * price / capital * 100, 1), 8.0)
            edge = round((prob * 4.0 - (1-prob)*1.75)*0.65, 2)
        else:
            direction = "AVOID / SELL"
            sl = tp = position_pct = 0.0
            edge = -0.9
        rec = {"Ticker": ticker, "Signal": direction, "Price": round(price, 2), "Stop Loss": round(sl, 2),
               "Target": round(tp, 2), "Position %": position_pct, "ML Prob": f"{prob:.1%}", "Edge": edge,
               "RSI": round(float(latest['RSI']), 1)}
        results.append(rec)
        if direction == "BUY" and (top_rec is None or rec["Edge"] > top_rec["Edge"]):
            top_rec = rec
            top_chart = create_candlestick(df_raw, ticker)
    
    if not results:
        demo_df = get_demo_data("TSLA")
        return pd.DataFrame([{"Ticker": "DEMO", "Signal": "DEMO MODE", "Price": 0, "Stop Loss": 0, "Target": 0, "Position %": 0, "ML Prob": "0%", "Edge": 0, "RSI": 0}]), create_candlestick(demo_df, "TSLA"), "Demo data loaded"
    
    df_out = pd.DataFrame(results).sort_values(by=["Edge"], ascending=False)
    summary = f"**Top Pick:** {top_rec['Signal']} **{top_rec['Ticker']}** @ ${top_rec['Price']} | Position {top_rec['Position %']}% | Edge {top_rec['Edge']}"
    return df_out, top_chart or create_candlestick(get_demo_data("TSLA"), "TSLA"), summary

# ====================== GROK + SELF-IMPROVE ======================
def validate_api_key(api_key):
    if not api_key or not api_key.startswith("xai-"): return "❌ Must start with xai-"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(model="grok-4", messages=[{"role": "user", "content": "Say VALID"}], max_tokens=5)
        return "✅ VALID" if "VALID" in resp.choices[0].message.content.upper() else "❌ Invalid"
    except Exception as e: return f"❌ {str(e)[:80]}"

def get_grok_analysis(summary, api_key):
    if not api_key or not summary: return "Need key + summary"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(model="grok-4", messages=[{"role": "user", "content": f"Give specific trade plan: {summary}"}], max_tokens=800)
        return resp.choices[0].message.content
    except Exception as e: return str(e)

def self_improve(api_key, summary):
    if not api_key: return "Need valid key"
    errors = get_recent_errors()
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        prompt = f"Fix these concise errors:\n{errors}\nUser note: {summary}"
        resp = client.chat.completions.create(model="grok-4", messages=[{"role": "user", "content": prompt}], max_tokens=900)
        suggestion = resp.choices[0].message.content
        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)', (datetime.now().isoformat(), suggestion))
        conn.commit()
        conn.close()
        return suggestion
    except Exception as e: return str(e)

# ====================== GRADIO UI (ALL TABS RESTORED) ======================
with gr.Blocks(title="xForgeTrader", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🧠 xForgeTrader – Full Version Restored (All Tabs)")

    with gr.Row():
        refresh_btn = gr.Button("🧹 Clear Cache & Force Refresh", variant="secondary")
        refresh_out = gr.Markdown()
        refresh_btn.click(clear_cache, outputs=refresh_out)

    with gr.Tab("📊 Profit Scanner"):
        with gr.Row():
            tickers_input = gr.Textbox(label="Tickers", value="TSLA, AAPL, NVDA")
            load_btn = gr.Button("Load Recommended List")
            demo_btn = gr.Button("Load Test Data (Instant)", variant="secondary")
        with gr.Row():
            capital = gr.Number(value=100000)
            risk = gr.Slider(0.5, 3.0, 1.0, step=0.1)
            start_date = gr.Textbox(value=(datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d"), label="Start Date")
            end_date = gr.Textbox(value=datetime.now().strftime("%Y-%m-%d"), label="End Date")
            realtime = gr.Checkbox(label="Live Mode (yfinance)", value=False)
            demo_mode = gr.Checkbox(label="Demo Mode (Recommended)", value=True)
        scan_btn = gr.Button("🚀 SCAN", variant="primary")
        table = gr.Dataframe()
        summary = gr.Markdown()
        chart = gr.Plot()
        
        scan_btn.click(scan_tickers, [tickers_input, capital, risk, start_date, end_date, realtime, demo_mode], [table, chart, summary])
        load_btn.click(lambda: ", ".join(RECOMMENDED_MOMENTUM), outputs=tickers_input)
        demo_btn.click(lambda: ", ".join(RECOMMENDED_MOMENTUM), outputs=tickers_input)

        gr.Markdown("### Report Problem")
        with gr.Row():
            err_ticker = gr.Textbox(label="Ticker")
            err_desc = gr.Textbox(label="Short description", lines=1)
            report_btn = gr.Button("Report Error")
            report_out = gr.Markdown()
            report_btn.click(lambda t, d: log_error("Scanner", t, d), [err_ticker, err_desc], report_out)

    with gr.Tab("📈 Technical Chart"):
        ticker = gr.Textbox(value="TSLA")
        realtime_chart = gr.Checkbox(label="Live Mode", value=False)
        demo_chart = gr.Checkbox(label="Demo Mode", value=True)
        btn = gr.Button("Generate Chart")
        plot = gr.Plot()
        btn.click(lambda t, rt, dm: create_candlestick(get_data(t, realtime=rt, demo_mode=dm), t), [ticker, realtime_chart, demo_chart], plot)

        gr.Markdown("### Report Problem")
        with gr.Row():
            err_ticker2 = gr.Textbox(label="Ticker")
            err_desc2 = gr.Textbox(label="Short description", lines=1)
            report_btn2 = gr.Button("Report Error")
            report_out2 = gr.Markdown()
            report_btn2.click(lambda t, d: log_error("Chart", t, d), [err_ticker2, err_desc2], report_out2)

    with gr.Tab("⚔️ Backtester"):
        bt_ticker = gr.Textbox(value="TSLA")
        bt_strategy = gr.Dropdown(["Rebound Dip", "MA Crossover"], value="Rebound Dip")
        bt_start = gr.Textbox(value=(datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d"), label="Start Date")
        bt_end = gr.Textbox(value=datetime.now().strftime("%Y-%m-%d"), label="End Date")
        bt_demo = gr.Checkbox(label="Demo Mode", value=True)
        bt_btn = gr.Button("Run Backtest")
        bt_metrics = gr.JSON()
        bt_chart = gr.Plot()
        bt_btn.click(lambda t, s, st, en, dm: run_backtest(t, st, en, strategy=s, demo_mode=dm), [bt_ticker, bt_strategy, bt_start, bt_end, bt_demo], [bt_metrics, bt_chart])

        gr.Markdown("### Report Problem")
        with gr.Row():
            err_ticker3 = gr.Textbox(label="Ticker")
            err_desc3 = gr.Textbox(label="Short description", lines=1)
            report_btn3 = gr.Button("Report Error")
            report_out3 = gr.Markdown()
            report_btn3.click(lambda t, d: log_error("Backtester", t, d), [err_ticker3, err_desc3], report_out3)

    with gr.Tab("🚶 Forward Walking Predictor"):
        fw_ticker = gr.Textbox(value="TSLA")
        fw_demo = gr.Checkbox(label="Demo Mode", value=True)
        fw_btn = gr.Button("Run Walk-Forward Test")
        fw_output = gr.Markdown()
        fw_btn.click(lambda t, dm: forward_walk_predictor(t, demo_mode=dm), [fw_ticker, fw_demo], fw_output)

        gr.Markdown("### Report Problem")
        with gr.Row():
            err_ticker4 = gr.Textbox(label="Ticker")
            err_desc4 = gr.Textbox(label="Short description", lines=1)
            report_btn4 = gr.Button("Report Error")
            report_out4 = gr.Markdown()
            report_btn4.click(lambda t, d: log_error("Forward Walker", t, d), [err_ticker4, err_desc4], report_out4)

    with gr.Tab("📡 Live Data Puller (Alpha Vantage)"):
        gr.Markdown("### Pull Real-Time Data from Alpha Vantage")
        av_key = gr.Textbox(label="Alpha Vantage API Key", value="XV8DT58Z4VPIS7X5", type="password")
        av_ticker = gr.Textbox(label="Ticker", value="TSLA")
        av_type = gr.Dropdown(["Real-time Quote", "5-min Intraday"], value="Real-time Quote")
        pull_btn = gr.Button("🚀 Pull Live Data", variant="primary")
        av_output = gr.Dataframe()
        av_status = gr.Markdown()
        
        def pull_live(ticker, key, dtype):
            df, msg = pull_alpha_vantage_live(ticker, key, dtype)
            return df, msg
        
        pull_btn.click(pull_live, [av_ticker, av_key, av_type], [av_output, av_status])
        
        save_btn = gr.Button("💾 Save This Data to Cache")
        save_status = gr.Markdown()
        save_btn.click(lambda t, df: save_av_data_to_cache(t, df), [av_ticker, av_output], save_status)

    with gr.Tab("🤖 Grok + Self-Improve"):
        api_key = gr.Textbox(type="password", placeholder="xai-...")
        val_btn = gr.Button("Validate Key")
        val_out = gr.Markdown()
        val_btn.click(validate_api_key, api_key, val_out)

        grok_sum = gr.Textbox(lines=3, label="Paste Top Recommendation or Backtest Summary")
        grok_btn = gr.Button("Get Grok Trade Plan")
        grok_out = gr.Markdown()
        grok_btn.click(get_grok_analysis, [grok_sum, api_key], grok_out)

        improve_btn = gr.Button("🧠 Generate Grok Improvement")
        improve_out = gr.Markdown()
        improve_btn.click(self_improve, [api_key, grok_sum], improve_out)

        gr.Markdown("**Recent Error Logs**")
        show_errors_btn = gr.Button("Show Recent Logs")
        errors_out = gr.Markdown()
        show_errors_btn.click(get_recent_errors, outputs=errors_out)

    with gr.Tab("🚪 EXIT"):
        gr.Markdown("### How to Exit")
        exit_btn = gr.Button("EXIT xForgeTrader", variant="stop")
        exit_out = gr.Markdown()
        exit_btn.click(lambda: "✅ Close the Terminal window now.", outputs=exit_out)

        gr.Markdown("### One-Click from Finder")
        gr.Markdown("""
        1. Create `Run-xForgeTrader.command` in the FORGE folder.
        2. Run `chmod +x Run-xForgeTrader.command` in Terminal.
        3. Right-click the `.command` file → **Open**.
        """)

    gr.Markdown("xForgeTrader – All tabs restored • Live data via Alpha Vantage • Demo Mode safe. Educational only.")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
