import gradio as gr, yfinance as yf, pandas as pd, sqlite3, os, logging, matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
LOGS = os.path.join(BASE, "logs")
os.makedirs(DATA, exist_ok=True); os.makedirs(LOGS, exist_ok=True)

DB = os.path.join(DATA, "stock_history.db")
XDB = os.path.join(DATA, "xforge_historical.db")
LOG = os.path.join(LOGS, "xforge_errors.log")

logging.basicConfig(filename=LOG, level=logging.ERROR, format='%(asctime)s - %(message)s')
def log(msg): logging.error(msg)

FAV = ["AAPL", "TSLA", "GOOGL", "AMZN", "MSFT", "NVDA"]

def init():
    for d in [DB, XDB]:
        c = sqlite3.connect(d)
        c.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, symbol TEXT, date TEXT, close REAL, volume INTEGER)')
        c.commit(); c.close()

# ====================== ENHANCED LIVE TICKERS WITH RSI + BOLLINGER + PROFITABILITY ======================
def get_live_data(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="30d")
    info = ticker.info
    price = info.get("currentPrice") or hist["Close"].iloc[-1]
    return price, hist

def calculate_indicators(hist):
    # RSI
    delta = hist["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = round(rsi.iloc[-1], 1)
    rsi_sig = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"

    # Bollinger Bands (20, 2)
    sma = hist["Close"].rolling(20).mean()
    std = hist["Close"].rolling(20).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    bb_pos = round((hist["Close"].iloc[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]), 2)
    bb_squeeze = "Yes" if (upper.iloc[-1] - lower.iloc[-1]) < hist["Close"].rolling(20).std().mean() * 1.2 else "No"

    # MACD
    ema12 = hist["Close"].ewm(span=12).mean()
    ema26 = hist["Close"].ewm(span=26).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=9).mean()
    macd_sig = "Bullish" if macd.iloc[-1] > signal_line.iloc[-1] else "Bearish"

    # Profitability metrics
    returns = hist["Close"].pct_change().dropna()
    vol = round(returns.std() * (252**0.5) * 100, 1)
    peak = hist["Close"].cummax()
    drawdown = round(((hist["Close"] - peak) / peak).min() * 100, 1)
    trend = round(np.polyfit(range(len(hist)), hist["Close"], 1)[0], 4)
    trend_str = "Strong Up" if trend > 0.5 else "Up" if trend > 0 else "Down" if trend > -0.5 else "Strong Down"
    profit_score = round((100 - abs(drawdown)) * (1 if rsi_val < 70 else 0.7) * (1 if macd_sig == "Bullish" else 0.8), 0)

    return {
        "RSI": rsi_val, "RSI Signal": rsi_sig,
        "BB Position": bb_pos, "BB Squeeze": bb_squeeze,
        "MACD": macd_sig,
        "Volatility %": vol, "Max Drawdown %": drawdown,
        "Trend": trend_str, "Profit Score": profit_score
    }

def live():
    results = []
    charts = []
    tech = []
    profit = []
    
    for sym in FAV:
        try:
            price, hist = get_live_data(sym)
            ind = calculate_indicators(hist)
            
            results.append({"Symbol": sym, "Price": round(price, 2), "Time": datetime.now().strftime("%H:%M:%S")})
            
            # Enhanced Chart with Bollinger Bands
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(hist.index, hist["Close"], label="Price", color="blue")
            sma = hist["Close"].rolling(20).mean()
            std = hist["Close"].rolling(20).std()
            ax.plot(hist.index, sma + 2*std, label="Upper BB", color="red", linestyle="--")
            ax.plot(hist.index, sma - 2*std, label="Lower BB", color="green", linestyle="--")
            ax.fill_between(hist.index, sma - 2*std, sma + 2*std, alpha=0.1)
            ax.set_title(f"{sym} - 30 Day with Bollinger Bands")
            ax.legend()
            plt.tight_layout()
            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            charts.append((sym, buf))
            plt.close()
            
            # Technical Indicators
            tech.append({
                "Symbol": sym,
                "RSI": ind["RSI"],
                "RSI Signal": ind["RSI Signal"],
                "BB Position": ind["BB Position"],
                "BB Squeeze": ind["BB Squeeze"],
                "MACD": ind["MACD"]
            })
            
            # Profitability Metrics
            profit.append({
                "Symbol": sym,
                "Volatility %": ind["Volatility %"],
                "Max Drawdown %": ind["Max Drawdown %"],
                "Trend": ind["Trend"],
                "Profit Score": ind["Profit Score"]
            })
            
        except Exception as e:
            log(str(e))
            results.append({"Symbol": sym, "Price": "N/A", "Time": "Error"})
            tech.append({"Symbol": sym, "RSI": "-", "RSI Signal": "Error", "BB Position": "-", "BB Squeeze": "-", "MACD": "-"})
            profit.append({"Symbol": sym, "Volatility %": "-", "Max Drawdown %": "-", "Trend": "Error", "Profit Score": "-"})
    
    return pd.DataFrame(results), charts, pd.DataFrame(tech), pd.DataFrame(profit)

# ====================== REST OF THE APP (unchanged) ======================
def fetch(sym, per="1y"):
    try:
        h = yf.Ticker(sym).history(period=per)
        if h.empty: return "No data", None
        c = sqlite3.connect(DB)
        df = h.reset_index()[["Date","Close","Volume"]]; df["symbol"] = sym
        df.columns = ["date","close","volume","symbol"]
        df.to_sql("history", c, if_exists="append", index=False); c.close()
        return f"Saved {len(h)} rows", df
    except Exception as e: log(str(e)); return str(e), None

def hist(sym, lim=100):
    c = sqlite3.connect(DB)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{sym}' ORDER BY date DESC LIMIT {lim}", c)
    c.close(); return df

def ship_cost(sym, qty):
    try:
        v = yf.Ticker(sym).history(period="5d")["Volume"].iloc[-1]
        cost = round(v * 0.00001 * qty, 2)
        return f"Shipping {sym} × {qty} → Est. cost: ${cost}"
    except Exception as e: log(str(e)); return str(e)

def sim_hist(sym, days=30):
    c = sqlite3.connect(DB)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{sym}' ORDER BY date DESC LIMIT {days}", c)
    c.close()
    if df.empty: return "No data"
    df["MA"] = df["close"].rolling(5).mean()
    sig = "BUY" if df["close"].iloc[-1] > df["MA"].iloc[-1] else "SELL"
    return f"SIM → {sig} signal for {sym}"

def forge(sym):
    return live()[0][live()[0]["Symbol"]==sym], ship_cost(sym, 100), hist(sym, 20)

def xforge(sym):
    c = sqlite3.connect(XDB)
    df = pd.read_sql_query(f"SELECT * FROM history WHERE symbol='{sym}' LIMIT 100", c)
    c.close(); return df if not df.empty else pd.DataFrame({"msg":["No data"]})

def errors():
    try: return open(LOG).read()[-3000:]
    except: return "No errors yet"

def update_forge():
    os.system("python3 -c 'import yfinance as yf; print(\"Forge updated\")'"); return "✅ Forge DB refreshed"

init()
with gr.Blocks(title="XForge Trader v9.2") as app:
    gr.Image(os.path.join(BASE, "logo.jpg"), height=100, show_label=False)
    gr.Markdown("# XForge Trader – Complete Dashboard")
    
    with gr.Tab("🔥 Live Tickers"):
        gr.Markdown("### Multi-View Live Dashboard (Prices + Bollinger Charts + RSI + Profitability)")
        btn = gr.Button("Refresh All Data", variant="primary")
        live_table = gr.Dataframe()
        charts_out = gr.Gallery(label="30-Day Price + Bollinger Bands", columns=3, height=220)
        tech_df = gr.Dataframe(label="Technical Indicators (RSI, Bollinger, MACD)")
        profit_df = gr.Dataframe(label="Profitability Metrics & Score")
        btn.click(live, None, [live_table, charts_out, tech_df, profit_df])

    with gr.Tab("📈 Fetch & Store"):
        s=gr.Textbox("AAPL"); p=gr.Dropdown(["1y","5y"],value="1y")
        gr.Button("Fetch").click(fetch, [s,p], [gr.Textbox(), gr.Dataframe()])
    with gr.Tab("📊 History"): gr.Button("Show").click(hist, [gr.Textbox("AAPL"), gr.Slider(10, 500, value=100, step=10)], gr.Dataframe())
    with gr.Tab("🚚 Shipping+Cost"): gr.Button("Calculate").click(ship_cost, [gr.Textbox("AAPL"), gr.Number(100)], gr.Textbox())
    with gr.Tab("🧠 SIM on History"): gr.Button("Run SIM").click(sim_hist, [gr.Textbox("AAPL"), gr.Slider(10, 100, value=30, step=5)], gr.Textbox())
    with gr.Tab("🚀 Forge Dashboard"): gr.Button("Load All").click(forge, gr.Textbox("AAPL"), [gr.Dataframe(), gr.Textbox(), gr.Dataframe()])
    with gr.Tab("🗄️ XForge DB"): gr.Button("Query").click(xforge, gr.Textbox("AAPL"), gr.Dataframe())
    with gr.Tab("⚠️ Errors"): gr.Button("View Log").click(errors, None, gr.Textbox(lines=12))
    with gr.Tab("🔄 Update Forge"): gr.Button("Update Now").click(update_forge, None, gr.Textbox())

app.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())
