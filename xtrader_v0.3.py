import gradio as gr
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
from pathlib import Path
import sqlite3
warnings.filterwarnings('ignore')

try:
    import pandas_ta as pta
    from sklearn.ensemble import RandomForestClassifier
except ImportError:
    print("pip install pandas-ta scikit-learn")
    exit()

# ====================== SELF-IMPROVE DATABASE ======================
DB_PATH = Path("xforge_self_improve.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY, timestamp TEXT, ticker TEXT, 
        signal TEXT, edge REAL, ml_prob TEXT, position_pct REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS improvements (
        id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT)''')
    conn.commit()
    conn.close()

init_db()

def log_recommendation(rec):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO recommendations (timestamp, ticker, signal, edge, ml_prob, position_pct)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), rec["Ticker"], rec["Signal"], 
               rec["Edge"], rec["ML Prob"], rec["Position %"]))
    conn.commit()
    conn.close()

def get_logged_recommendations():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM recommendations ORDER BY timestamp DESC LIMIT 20", conn)
    conn.close()
    return df

def log_improvement(suggestion):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO improvements (timestamp, suggestion) VALUES (?, ?)''',
              (datetime.now().isoformat(), suggestion))
    conn.commit()
    conn.close()

# ====================== CORE LOGIC ======================
RECOMMENDED_MOMENTUM = [
    "TSLA", "AAPL", "NVDA", "AMD", "SMCI", "META", "AVGO", "MSFT", "GOOGL", "RIO.AX"
]

def get_data(ticker: str, period="2y"):
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty: return pd.DataFrame()
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        Path("data_cache").mkdir(exist_ok=True)
        df.to_parquet(f"data_cache/{ticker}.parquet")
        return df
    except:
        try:
            return pd.read_parquet(f"data_cache/{ticker}.parquet")
        except:
            return pd.DataFrame()

def add_indicators(df):
    df = df.copy()
    df['SMA50'] = pta.sma(df['Close'], length=50)
    df['SMA200'] = pta.sma(df['Close'], length=200)
    df['RSI'] = pta.rsi(df['Close'], length=14)
    df = pd.concat([df, pta.macd(df['Close'])], axis=1)
    df = pd.concat([df, pta.bbands(df['Close'], length=20)], axis=1)
    df['ATR'] = pta.atr(df['High'], df['Low'], df['Close'], length=14)
    return df.dropna()

def calculate_ml_prob(df, horizon=5):
    df = df.copy()
    for i in range(1, 11):
        df[f'return_{i}'] = df['Close'].pct_change(i)
    df['target'] = (df['Close'].shift(-horizon) > df['Close']).astype(int)
    df = df.dropna()
    if len(df) < 100: return 0.50
    features = [c for c in df.columns if 'return_' in c or c in ['RSI', 'SMA50']]
    X = df[features]
    y = df['target']
    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X.iloc[:-horizon], y.iloc[:-horizon])
    return model.predict_proba(X.iloc[[-1]])[0][1]

def generate_recommendation(df, ticker, capital=100000, risk_pct=1.0):
    if df.empty or len(df) < 50: return None
    latest = df.iloc[-1]
    prob = calculate_ml_prob(df)
    price = float(latest['Close'])
    atr = float(latest['ATR'])
    
    if prob > 0.57 and latest['RSI'] < 58:
        direction = "BUY"
        sl = price - 1.75 * atr
        tp = price + 4.0 * atr
        risk_per_share = price - sl
        pos_size = (capital * (risk_pct / 100)) / risk_per_share
        position_pct = min(round(pos_size * price / capital * 100, 1), 8.0)
        edge = round((prob * 4.0 - (1 - prob) * 1.75) * 0.65, 2)
        confidence = "High" if prob > 0.67 else "Medium"
    else:
        direction = "AVOID / SELL"
        sl = tp = position_pct = 0.0
        edge = -0.9
        confidence = "Low"
    
    rec = {
        "Ticker": ticker, "Signal": direction, "Price": round(price, 2),
        "Stop Loss": round(sl, 2) if sl else 0, "Target": round(tp, 2) if tp else 0,
        "RR": "1:2.3" if direction == "BUY" else "-", "Position %": position_pct,
        "ML Prob": f"{prob:.1%}", "Edge": edge, "Confidence": confidence,
        "RSI": round(float(latest['RSI']), 1)
    }
    if direction == "BUY": log_recommendation(rec)
    return rec

def create_candlestick(df, ticker):
    if df.empty or len(df) < 20:
        fig = go.Figure()
        fig.add_annotation(text="No data available for chart", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=500, title=f"{ticker} - No Data")
        return fig
    df = add_indicators(df)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name="SMA50", line=dict(color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA200", line=dict(color="blue")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI"), row=2, col=1)
    fig.update_layout(height=650, title=f"{ticker} Technical Analysis", xaxis_rangeslider_visible=False)
    return fig

# ====================== MAIN SCAN ======================
def scan_tickers(tickers_str, capital, risk_pct):
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    results = []
    top_chart = None
    top_rec = None
    
    for ticker in tickers[:10]:
        df_raw = get_data(ticker)
        if df_raw.empty: continue
        df = add_indicators(df_raw)
        rec = generate_recommendation(df, ticker, capital, risk_pct)
        if rec:
            results.append(rec)
            if (top_rec is None or rec["Edge"] > top_rec["Edge"]) and rec["Signal"] == "BUY":
                top_rec = rec
                top_chart = create_candlestick(df_raw, ticker)
    
    if not results:
        return "No data. Check tickers or internet.", None, "No recommendations"
    
    df_out = pd.DataFrame(results).sort_values(by=["Edge", "ML Prob"], ascending=False)
    summary = f"**Top Pick:** {top_rec['Signal']} **{top_rec['Ticker']}** @ ${top_rec['Price']} | Position: {top_rec['Position %']}% | Target: ${top_rec['Target']} | Edge: {top_rec['Edge']}"
    
    # Always return a chart (even placeholder)
    if top_chart is None:
        top_chart = create_candlestick(pd.DataFrame(), "N/A")
    
    return df_out, top_chart, summary

# ====================== API KEY VALIDATION ======================
def validate_api_key(api_key):
    if not api_key or not api_key.startswith("xai-"):
        return "❌ Key must start with 'xai-'"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-4",
            messages=[{"role": "user", "content": "Confirm API key validity with one word: VALID"}],
            max_tokens=5
        )
        text = resp.choices[0].message.content.upper()
        if "VALID" in text:
            return "✅ API Key is VALID and working!"
        return f"❌ Validation failed: {text}"
    except Exception as e:
        return f"❌ Error: {str(e)[:120]}"

def get_grok_analysis(summary, api_key):
    if not api_key or not summary: return "Enter valid xAI key and run a scan first."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        prompt = f"""You are an elite quant trader. Give a clear, specific trade plan for this setup:\n{summary}\nInclude entry, stop-loss, targets, position sizing, conviction, and risks."""
        resp = client.chat.completions.create(model="grok-4", messages=[{"role": "user", "content": prompt}], max_tokens=900)
        return resp.choices[0].message.content
    except Exception as e:
        return f"Grok error: {str(e)}"

# ====================== SELF-IMPROVE ======================
def self_improve(api_key, summary):
    if not api_key: return "Need valid xAI key for AI improvements."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        prompt = f"""Analyze this trading engine output and suggest 3 concrete improvements to the strategy (indicators, risk rules, ML, etc.):\n{summary}"""
        resp = client.chat.completions.create(model="grok-4", messages=[{"role": "user", "content": prompt}], max_tokens=600)
        suggestion = resp.choices[0].message.content
        log_improvement(suggestion)
        return suggestion
    except Exception as e:
        return f"Error: {str(e)}"

def show_self_improve_logs():
    recs = get_logged_recommendations()
    if recs.empty: return "No scans logged yet."
    return recs.to_string(index=False)

# ====================== GRADIO UI ======================
with gr.Blocks(title="xForgeTrader v3", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🧠 xForgeTrader v3 – Competitive Profit Recommender\n**Restored self-improvement, API validation, momentum list & charts from original ReboundForge**")

    with gr.Tab("📊 Profit Scanner"):
        gr.Markdown("### Step 1: Choose your tickers (or click button below for recommended short-term momentum list)")
        
        with gr.Row():
            tickers_input = gr.Textbox(label="Tickers (comma separated)", value="TSLA, AAPL, NVDA, AMD, SMCI", scale=3)
            load_btn = gr.Button("📋 Load Recommended Short-Term Momentum List", variant="secondary")
        
        with gr.Row():
            capital = gr.Number(label="Portfolio Capital ($)", value=100000)
            risk = gr.Slider(label="Risk per Trade (%)", minimum=0.5, maximum=3.0, value=1.0, step=0.1)
        
        scan_btn = gr.Button("🚀 SCAN FOR HIGH-EDGE TRADES", variant="primary", size="large")
        
        gr.Markdown("### Recommended Short-Term Momentum Symbols & Viability (from original ReboundForge + 2026 data)")
        gr.Markdown("""
        | Ticker | Viability | Why Short-Term Momentum |
        |--------|-----------|-------------------------|
        | **NVDA** | ⭐⭐⭐⭐⭐ High | AI leader, 24% implied upside, strong rebound potential |
        | **TSLA** | ⭐⭐⭐⭐ High | High volatility, classic rebound-dip play |
        | **AMD** | ⭐⭐⭐⭐ High | Semiconductor momentum, often follows NVDA |
        | **SMCI** | ⭐⭐⭐⭐ High | AI server play, explosive short-term moves |
        | **META** | ⭐⭐⭐ High | Tech momentum, strong recent trends |
        | **AVGO** | ⭐⭐⭐ High | Broadcom – AI chips, steady momentum |
        | **AAPL** | ⭐⭐⭐ Medium | Stable but lower volatility rebound |
        | **RIO.AX** | ⭐⭐⭐ Medium | Mining rebound (original Australian list) |
        """)
        
        output_table = gr.Dataframe(label="Ranked Recommendations")
        top_summary = gr.Markdown()
        top_plot = gr.Plot(label="Chart of Top Pick")
        
        scan_btn.click(scan_tickers, inputs=[tickers_input, capital, risk], outputs=[output_table, top_plot, top_summary])
        load_btn.click(lambda: ", ".join(RECOMMENDED_MOMENTUM), outputs=tickers_input)

    with gr.Tab("📈 Technical Chart"):
        chart_ticker = gr.Textbox(label="Ticker", value="NVDA")
        chart_btn = gr.Button("Generate Chart")
        chart_output = gr.Plot()
        chart_btn.click(lambda t: create_candlestick(get_data(t), t), inputs=chart_ticker, outputs=chart_output)

    with gr.Tab("⚙️ Backtester"):
        bt_ticker = gr.Textbox(label="Ticker", value="AAPL")
        bt_btn = gr.Button("Run Backtest")
        bt_output = gr.Markdown()
        def bt(t):
            df = get_data(t)
            if df.empty: return "No data"
            df = add_indicators(df)
            df['signal'] = ((df['RSI'] < 40) & (df['Close'] > df['SMA50'])).astype(int)
            df['returns'] = df['Close'].pct_change()
            df['strategy'] = df['signal'].shift(1) * df['returns']
            ret = (1 + df['strategy']).cumprod().iloc[-1] - 1
            return f"**Backtest Return:** {ret*100:.2f}%"
        bt_btn.click(bt, inputs=bt_ticker, outputs=bt_output)

    with gr.Tab("🤖 Grok AI + Self-Improve"):
        api_key = gr.Textbox(label="xAI API Key", type="password", placeholder="xai-...")
        validate_btn = gr.Button("✅ Validate API Key")
        validate_output = gr.Markdown()
        validate_btn.click(validate_api_key, inputs=api_key, outputs=validate_output)
        
        grok_summary = gr.Textbox(label="Paste Top Recommendation Summary (or run scanner)", lines=3)
        grok_btn = gr.Button("Get Grok Trade Plan")
        grok_output = gr.Markdown()
        grok_btn.click(get_grok_analysis, inputs=[grok_summary, api_key], outputs=grok_output)
        
        gr.Markdown("### Self-Improve Engine (restored from original)")
        improve_btn = gr.Button("🧠 Generate & Log AI Improvement Suggestion")
        improve_output = gr.Markdown()
        improve_btn.click(self_improve, inputs=[api_key, grok_summary], outputs=improve_output)
        
        gr.Markdown("**Past Recommendations Log**")
        log_btn = gr.Button("Show Logged Scans")
        log_output = gr.Markdown()
        log_btn.click(show_self_improve_logs, outputs=log_output)

    gr.Markdown("v3 – Self-improving DB + API validation + momentum list + working charts restored. Educational only.")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
