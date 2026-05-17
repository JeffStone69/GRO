#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from openai import OpenAI

st.set_page_config(page_title="GeoSupply Rebound Analyzer", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

SAVED_LOG = "saved.log"

# ====================== SECTOR TICKERS ======================
ASX_MINING = ["BHP.AX", "RIO.AX", "FMG.AX", "S32.AX", "MIN.AX"]
ASX_SHIPPING = ["QUB.AX", "TCL.AX", "ASX.AX"]
ASX_ENERGY = ["STO.AX", "WDS.AX", "ORG.AX", "WHC.AX", "BPT.AX"]
ASX_TECH = ["WTC.AX", "XRO.AX", "TNE.AX", "NXT.AX", "REA.AX", "360.AX", "PME.AX"]
ASX_RENEW = ["ORG.AX", "AGL.AX", "IGO.AX", "IFT.AX", "MCY.AX", "CEN.AX", "MEZ.AX", "JNS.AX"]

US_MINING = ["FCX", "NEM", "VALE", "SCCO", "GOLD", "AEM"]
US_SHIPPING = ["ZIM", "MATX", "SBLK", "DAC", "CMRE"]
US_ENERGY = ["XOM", "CVX", "COP", "OXY", "CCJ"]
US_TECH = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMD", "TSLA"]
US_RENEW = ["NEE", "BEPC", "CWEN", "FSLR", "ENPH"]

ALL_ASX = list(dict.fromkeys(ASX_MINING + ASX_SHIPPING + ASX_ENERGY + ASX_TECH + ASX_RENEW))
ALL_US = list(dict.fromkeys(US_MINING + US_SHIPPING + US_ENERGY + US_TECH + US_RENEW))
ALL_TICKERS = ALL_ASX + ALL_US

API_BASE = "https://api.x.ai/v1"
AVAILABLE_MODELS = ["grok-4.20-reasoning", "grok-4.20-non-reasoning", "grok-4.20-multi-agent-0309", "grok-4-1-fast-reasoning", "grok-4-1-fast-non-reasoning"]

logging.basicConfig(filename="geosupply_errors.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ====================== GROK API ======================
def call_grok_api(prompt: str, model: str, temperature: float = 0.7) -> str:
    if not st.session_state.get("grok_api_key"):
        return "❌ Please enter your Grok API key in the sidebar."
    headers = {"Authorization": f"Bearer {st.session_state.grok_api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
    try:
        resp = requests.post(f"{API_BASE}/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"Grok API error: {e}")
        return f"❌ Grok API error: {str(e)}"

# ====================== POLYMARKET ======================
@st.cache_data(ttl=180)
def fetch_polymarket_markets(show_open_only: bool = True) -> pd.DataFrame:
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 200}
        if show_open_only:
            params["active"] = "true"
            params["closed"] = "false"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        markets = resp.json()

        GEO_KEYWORDS = ["oil", "energy", "copper", "gold", "lithium", "shipping", "mining", "tariff", "china", "ev",
                        "renewable", "commodity", "geopolitic", "opec", "lng", "uranium", "iron ore"]

        relevant = []
        for m in markets:
            question = (m.get("question") or "").lower()
            if not any(kw in question for kw in GEO_KEYWORDS):
                continue

            outcomes_raw = m.get("outcomes")
            prices_raw = m.get("outcomePrices")
            try:
                outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw or []
                prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw or []
            except:
                continue
            if len(outcomes) < 2 or len(prices) < 2:
                continue

            try:
                prob_yes = float(prices[0]) * 100
            except:
                prob_yes = 0.0

            vol = m.get("volume") or m.get("volumeNum") or m.get("clobVolume") or 0
            volume = float(vol) if vol else 0.0

            relevant.append({
                "Question": m.get("question", "N/A"),
                "Primary Outcome": outcomes[0] if outcomes else "Yes",
                "Prob %": round(prob_yes, 1),
                "Volume Num": volume,
                "Volume": f"${volume:,.0f}",
                "Link": f"https://polymarket.com/{m.get('slug')}" if m.get("slug") else "",
                "Status": "Open" if m.get("active") else "Closed"
            })

        df = pd.DataFrame(relevant)
        if not df.empty:
            df = df.sort_values("Volume Num", ascending=False).head(15)
            df = df.drop(columns=["Volume Num"])
        return df

    except Exception as e:
        logging.error(f"Polymarket API error: {e}")
        return pd.DataFrame()

# ====================== POLYMARKET ↔ REBOUND CORRELATION ======================
def analyze_polymarket_correlation(pm_df: pd.DataFrame, summary_df: pd.DataFrame) -> pd.DataFrame:
    if pm_df.empty or summary_df.empty:
        return pd.DataFrame()
    KEYWORD_TO_TICKERS = {
        "oil": ["XOM", "CVX", "STO.AX", "WDS.AX", "ORG.AX"],
        "energy": ["XOM", "CVX", "STO.AX", "WDS.AX", "ORG.AX"],
        "copper": ["FCX", "SCCO", "BHP.AX", "RIO.AX"],
        "gold": ["GOLD", "NEM", "AEM"],
        "lithium": ["IGO.AX"],
        "mining": ["BHP.AX", "RIO.AX", "FMG.AX"],
        "shipping": ["ZIM", "MATX", "QUB.AX"],
        "tariff": ["BHP.AX", "RIO.AX", "FCX"],
        "ev": ["TSLA", "NEE", "ENPH"],
        "renewable": ["NEE", "BEPC", "FSLR", "ENPH"]
    }
    rows = []
    top_rebound = summary_df.head(10).copy()
    for _, market in pm_df.iterrows():
        question_lower = market["Question"].lower()
        matched = []
        impact = 0.0
        for kw, tickers in KEYWORD_TO_TICKERS.items():
            if kw in question_lower:
                hits = top_rebound[top_rebound["Ticker"].isin(tickers)]
                if not hits.empty:
                    matched.extend(hits["Ticker"].tolist())
                    impact += hits["Rebound Score"].sum() * (market["Prob %"] / 100)
        if matched:
            rows.append({
                "Polymarket Event": market["Question"][:60] + "..." if len(market["Question"]) > 60 else market["Question"],
                "Prob %": market["Prob %"],
                "Volume": market["Volume"],
                "Affected Tickers": ", ".join(sorted(set(matched))),
                "Est. Rebound Impact": round(impact, 1),
                "Link": market["Link"]
            })
    corr_df = pd.DataFrame(rows)
    if not corr_df.empty:
        corr_df = corr_df.sort_values("Est. Rebound Impact", ascending=False).head(8)
    return corr_df

# ====================== HELPER FUNCTIONS (streamlined) ======================
def get_data_timeframe(raw_data: Dict[str, pd.DataFrame], real_time_mode: bool, period: str) -> str:
    if not raw_data:
        return "No data loaded"
    sample_df = next(iter(raw_data.values()), pd.DataFrame())
    if sample_df.empty:
        return f"📅 {period} data"
    latest_ts = sample_df.index[-1]
    if real_time_mode:
        return f"📈 LIVE INTRA-DAY (1-minute candles) • Last price: {latest_ts.strftime('%H:%M %d %b %Y')}"
    else:
        return f"📅 {period.upper()} HISTORICAL DATA • Last close: {latest_ts.strftime('%Y-%m-%d')}"

def load_saved_analyses():
    if "saved_analyses" not in st.session_state:
        st.session_state.saved_analyses = []
        if os.path.exists(SAVED_LOG):
            try:
                with open(SAVED_LOG, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            analysis = json.loads(line)
                            if not any(a.get("timestamp") == analysis.get("timestamp") and a.get("tab") == analysis.get("tab")
                                       for a in st.session_state.saved_analyses):
                                st.session_state.saved_analyses.append(analysis)
            except Exception as e:
                st.warning(f"Could not load saved.log: {e}")
    return st.session_state.saved_analyses

def save_analysis(analysis: dict):
    try:
        os.makedirs(os.path.dirname(SAVED_LOG) or ".", exist_ok=True)
        with open(SAVED_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(analysis, ensure_ascii=False) + "\n")
        st.session_state.setdefault("saved_analyses", []).append(analysis)
        return True
    except Exception as e:
        st.error(f"Failed to save to saved.log: {e}")
        return False

def clear_all_saved_analyses():
    try:
        if os.path.exists(SAVED_LOG):
            os.remove(SAVED_LOG)
        st.session_state.saved_analyses = []
        st.success("✅ All saved analyses permanently deleted from saved.log")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to clear saved.log: {e}")

def build_sector_df(tickers: List[str], raw_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        if ticker not in raw_data or raw_data[ticker].empty or len(raw_data[ticker]) < 15:
            continue
        df = raw_data[ticker]
        score, rsi_val, mom = calculate_rebound_score(df)
        info = get_ticker_info(ticker)
        latest = df.iloc[-1]
        prev_close = df.iloc[-2]["Close"] if len(df) > 1 else latest["Close"]
        change_pct = ((latest["Close"] / prev_close) - 1) * 100
        rows.append({
            "Ticker": ticker, "Company": info["name"], "Market": "ASX" if ".AX" in ticker else "US",
            "Currency": info["currency"], "Price": round(latest["Close"], 3),
            "Change %": round(change_pct, 2), "RSI": rsi_val,
            "Rebound Score": round(score, 1), "Momentum": mom,
            "Volume": int(latest.get("Volume", 0))
        })
    df_sector = pd.DataFrame(rows)
    if not df_sector.empty:
        df_sector = df_sector.sort_values("Rebound Score", ascending=False)
    return df_sector

def evaluate_custom_ticker(ticker: str, period: str, real_time_mode: bool) -> Tuple[Optional[pd.DataFrame], Optional[float], Optional[float], Optional[float], str]:
    if not ticker:
        return None, None, None, None, "Enter a ticker"
    try:
        custom_data = fetch_batch_data([ticker.strip().upper()], period, real_time_mode)
        if ticker not in custom_data or custom_data[ticker].empty:
            return None, None, None, None, f"❌ No data returned for {ticker}"
        df = custom_data[ticker].copy()
        if "Close" not in df.columns:
            if "Adj Close" in df.columns:
                df["Close"] = df["Adj Close"]
            else:
                return None, None, None, None, f"❌ Missing price column for {ticker}"
        score, rsi_val, mom = calculate_rebound_score(df)
        return df, score, rsi_val, mom, ""
    except Exception as e:
        return None, None, None, None, f"Error fetching {ticker}: {str(e)}"

@st.cache_data(ttl=300)
def fetch_batch_data(tickers: List[str], period: str = "6mo", real_time_mode: bool = False) -> Dict[str, pd.DataFrame]:
    if real_time_mode:
        period = "5d"
    if not tickers:
        return {}
    try:
        data = yf.download(tickers, period=period, group_by="ticker", auto_adjust=True, progress=False,
                           interval="1m" if real_time_mode else "1d")
        data_dict = {}
        for ticker in tickers:
            if len(tickers) == 1:
                df = data.copy()
            elif isinstance(data.columns, pd.MultiIndex) and ticker in data.columns.get_level_values(0):
                df = data[ticker].copy()
            else:
                continue
            df = df.dropna(how="all")
            if not df.empty:
                if "Close" not in df.columns and "Adj Close" in df.columns:
                    df["Close"] = df["Adj Close"]
                data_dict[ticker] = df
        return data_dict
    except Exception as e:
        logging.error(f"Data fetch failed for tickers {tickers}: {e}")
        return {}

@st.cache_data(ttl=180)
def get_usd_aud_rate() -> Optional[float]:
    try:
        rate_data = yf.download("AUD=X", period="1d", progress=False)
        return float(rate_data["Close"].iloc[-1]) if not rate_data.empty else None
    except:
        return None

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, float('nan'))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_rebound_score(df: pd.DataFrame) -> Tuple[float, float, float]:
    """Single-point score for live dashboard (kept for compatibility)"""
    if df.empty or len(df) < 20 or "Close" not in df.columns:
        return 0.0, 50.0, 0.0
    close = df["Close"].iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]
    rsi = max(min(rsi, 100), 0)
    rolling_high = df["Close"].rolling(window=252, min_periods=20).max().iloc[-1]
    percent_from_high = ((close - rolling_high) / rolling_high * 100) if rolling_high > 0 else -30.0
    momentum = df["Close"].pct_change(periods=10).iloc[-1] * 100
    rsi_comp = max(0, (50 - rsi) * 2.2) if rsi < 50 else max(0, (30 - rsi) * 1.5)
    high_comp = max(0, -percent_from_high * 1.8)
    mom_comp = max(0, -momentum * 1.4)
    score = rsi_comp * 0.55 + high_comp * 0.30 + mom_comp * 0.15
    return max(0, min(100, score)), round(rsi, 1), round(momentum, 2)

def calculate_rebound_score_series(df: pd.DataFrame) -> pd.Series:
    """Vectorized version for fast backtesting (new in v12.3)"""
    if len(df) < 20 or "Close" not in df.columns:
        return pd.Series(0.0, index=df.index)
    close = df["Close"]
    rsi = calculate_rsi(close)
    rolling_high = close.rolling(window=252, min_periods=20).max()
    percent_from_high = ((close - rolling_high) / rolling_high * 100).fillna(-30.0)
    momentum = close.pct_change(periods=10) * 100
    rsi_comp = pd.Series(0.0, index=df.index)
    oversold = rsi < 50
    rsi_comp[oversold] = (50 - rsi[oversold]) * 2.2
    rsi_comp[~oversold] = (30 - rsi[~oversold]) * 1.5
    rsi_comp = rsi_comp.clip(lower=0)
    high_comp = (-percent_from_high * 1.8).clip(lower=0)
    mom_comp = (-momentum * 1.4).clip(lower=0)
    score = rsi_comp * 0.55 + high_comp * 0.30 + mom_comp * 0.15
    return score.clip(0, 100)

def create_price_rsi_chart(df: pd.DataFrame, ticker: str, company_name: str) -> go.Figure:
    if "Close" not in df.columns and "Adj Close" in df.columns:
        df = df.copy()
        df["Close"] = df["Adj Close"]
    rsi_series = calculate_rsi(df["Close"])
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.70, 0.30],
                        subplot_titles=(f"{ticker} — {company_name}", "RSI (14)"))
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=rsi_series, name="RSI", line=dict(color="#FF6B6B", width=2.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF4757", row=2, col=1, annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color="#2ED573", row=2, col=1, annotation_text="Oversold")
    fig.update_layout(height=680, template="plotly_dark", margin=dict(l=30,r=30,t=60,b=30), legend=dict(orientation="h", y=1.05))
    fig.update_xaxes(rangeslider_visible=False)
    return fig

@st.cache_data(ttl=3600)
def get_ticker_info(ticker: str) -> Dict:
    try:
        info = yf.Ticker(ticker).info
        return {"name": info.get("longName") or info.get("shortName") or ticker.replace(".AX", ""),
                "sector": info.get("sector", "Multi-Sector"),
                "currency": "AUD" if ".AX" in ticker else "USD"}
    except:
        return {"name": ticker.replace(".AX", ""), "sector": "Resources/Tech/Energy", "currency": "AUD" if ".AX" in ticker else "USD"}

def add_page_analyzer(tab_name: str, page_context: str = "", raw_data: Dict = None,
                      selected_model: str = None, real_time_mode: bool = False, period: str = "6mo"):
    key_prefix = f"grok_{tab_name.lower().replace(' ', '_')}"
    if f"{key_prefix}_response" not in st.session_state:
        st.session_state[f"{key_prefix}_response"] = None
        st.session_state[f"{key_prefix}_timestamp"] = None
        st.session_state[f"{key_prefix}_user_prompt"] = None

    with st.expander("🤖 Analyse this page with Grok", expanded=False):
        st.caption(f"**{tab_name}** tab • Model: **{selected_model}** • {get_data_timeframe(raw_data or {}, real_time_mode, period)}")
        user_prompt = st.text_area("Optional instructions to guide Grok", placeholder="e.g. Suggest better layout...", key=f"user_prompt_{tab_name}", height=80)

        if st.button("🚀 Analyse Page with Grok", key=f"analyze_btn_{tab_name}", use_container_width=True):
            with st.spinner("Grok is analysing..."):
                full_prompt = f"""You are analysing the **'{tab_name}'** tab of the GeoSupply Rebound Analyzer v12.3.
DATA TIMEFRAME: {get_data_timeframe(raw_data or {}, real_time_mode, period)}
CURRENT PAGE CONTEXT: {page_context or "No specific data summary."}
USER REQUEST: {user_prompt or "General troubleshooting and improvement suggestions."}
TASK: 1. Bugs/UX issues 2. Actionable improvements 3. Ideas for $500 users 4. Code optimisations.
Be concise and number your suggestions."""
                response = call_grok_api(full_prompt, selected_model, temperature=0.7)
                st.session_state[f"{key_prefix}_response"] = response
                st.session_state[f"{key_prefix}_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state[f"{key_prefix}_user_prompt"] = user_prompt or "General"
                st.success("✅ Grok analysis complete!")

        if st.session_state.get(f"{key_prefix}_response"):
            st.markdown("### 🤖 Grok's Page Analysis")
            st.write(st.session_state[f"{key_prefix}_response"])
            col_save, col_clear = st.columns([3, 1])
            with col_save:
                if st.button("💾 Save this Grok Analysis to saved.log", key=f"save_btn_{tab_name}", use_container_width=True):
                    analysis = {"tab": tab_name, "timestamp": st.session_state[f"{key_prefix}_timestamp"], "model_used": selected_model,
                                "user_prompt": st.session_state[f"{key_prefix}_user_prompt"], "response": st.session_state[f"{key_prefix}_response"],
                                "data_timeframe": get_data_timeframe(raw_data or {}, real_time_mode, period)}
                    if save_analysis(analysis):
                        st.success(f"✅ Saved permanently at {analysis['timestamp']}")
            with col_clear:
                if st.button("🗑️ Clear this analysis", key=f"clear_btn_{tab_name}"):
                    st.session_state[f"{key_prefix}_response"] = None
                    st.rerun()

# ====================== GROK CHAT ======================
@st.cache_resource
def get_grok_client():
    if not st.session_state.get("grok_api_key"):
        return None
    return OpenAI(api_key=st.session_state.grok_api_key, base_url="https://api.x.ai/v1")

# ====================== ENHANCED BACKTESTER (v12.3) ======================
@st.cache_data(ttl=1800)
def run_enhanced_backtest(tickers: Union[str, List[str]], test_period: str = "5y",
                          entry_threshold: float = 65.0, exit_threshold: float = 40.0,
                          commission_pct: float = 0.10, walk_forward: bool = True,
                          max_hold_days: int = 20) -> Dict:
    """Full walk-forward, commission-aware, portfolio-level backtester.
    Leverages yfinance for all historical + benchmark data (SPY as market proxy)."""
    if isinstance(tickers, str):
        tickers = [tickers]
    results = {"portfolio": {}, "individual": {}, "benchmark": {}}

    # Fetch full history for walk-forward
    try:
        data_dict = fetch_batch_data(tickers, period=test_period, real_time_mode=False)
    except:
        return {"error": "Data fetch failed"}

    all_trades = []
    portfolio_daily_returns = []
    benchmark = yf.download("SPY", period=test_period, progress=False)["Close"].pct_change().fillna(0)  # outside market benchmark

    for ticker in tickers:
        if ticker not in data_dict or data_dict[ticker].empty:
            continue
        df = data_dict[ticker].copy()
        df["Rebound_Score"] = calculate_rebound_score_series(df)

        # Walk-forward split: 75% in-sample train window, 25% OOS test (rolling approximation)
        split_idx = int(len(df) * 0.75) if walk_forward else 0
        test_df = df.iloc[split_idx:].copy() if walk_forward else df.copy()

        # Simulate trades
        in_position = False
        entry_price = 0
        entry_idx = 0
        trades = []

        for i in range(1, len(test_df)):
            score = test_df["Rebound_Score"].iloc[i]
            if not in_position and score >= entry_threshold:
                in_position = True
                entry_price = test_df["Close"].iloc[i]
                entry_idx = i
            elif in_position and (score <= exit_threshold or (i - entry_idx) > max_hold_days):
                gross_ret = (test_df["Close"].iloc[i] / entry_price - 1) * 100
                net_ret = gross_ret - (commission_pct * 2)  # round-trip
                trades.append({
                    "Ticker": ticker,
                    "Entry_Date": test_df.index[entry_idx],
                    "Exit_Date": test_df.index[i],
                    "Gross_%": round(gross_ret, 2),
                    "Net_%": round(net_ret, 2)
                })
                all_trades.append(trades[-1])
                in_position = False

        if trades:
            trades_df = pd.DataFrame(trades)
            win_rate = (trades_df["Net_%"] > 0).mean() * 100
            avg_ret = trades_df["Net_%"].mean()
            total_ret = trades_df["Net_%"].sum()
            results["individual"][ticker] = {
                "Num_Trades": len(trades_df),
                "Win_Rate_%": round(win_rate, 1),
                "Avg_Return_%": round(avg_ret, 2),
                "Total_Return_%": round(total_ret, 2),
                "Trades_DF": trades_df
            }

    # Portfolio aggregation (equal-weight across assets)
    if all_trades:
        trades_df_all = pd.DataFrame(all_trades)
        win_rate_p = (trades_df_all["Net_%"] > 0).mean() * 100
        avg_ret_p = trades_df_all["Net_%"].mean()
        total_ret_p = trades_df_all["Net_%"].sum() / len(tickers) if tickers else 0
        results["portfolio"] = {
            "Num_Trades": len(trades_df_all),
            "Win_Rate_%": round(win_rate_p, 1),
            "Avg_Return_%": round(avg_ret_p, 2),
            "Total_Return_%": round(total_ret_p, 2),
            "Trades_DF": trades_df_all
        }

    # Benchmark comparison
    bench_ret = (benchmark.iloc[-1] / benchmark.iloc[0] - 1) * 100 if len(benchmark) > 1 else 0
    results["benchmark"] = {"SPY_Total_Return_%": round(bench_ret, 2)}

    return results

# ====================== MAIN APP ======================
def main():
    load_saved_analyses()

    if "grok_api_key" not in st.session_state: st.session_state.grok_api_key = ""
    if "selected_model" not in st.session_state: st.session_state.selected_model = AVAILABLE_MODELS[0]
    if "real_time_mode" not in st.session_state: st.session_state.real_time_mode = False
    if "market_filter" not in st.session_state: st.session_state.market_filter = "Both"
    if "period" not in st.session_state: st.session_state.period = "6mo"

    st.title("📈 GeoSupply Rebound Analyzer")
    st.caption("**v12.3** • Walk-Forward Backtester + Commission + Portfolio Testing • Top-5 Market Summary • Vectorized + yfinance benchmark")

    with st.sidebar:
        st.header("Controls")
        st.text_input("Grok API Key", type="password", value=st.session_state.grok_api_key, key="grok_api_key")
        st.selectbox("Grok Model", AVAILABLE_MODELS, index=AVAILABLE_MODELS.index(st.session_state.selected_model), key="selected_model")
        st.checkbox("📈 Real-time intra-day mode (1m candles)", value=st.session_state.real_time_mode, key="real_time_mode")
        st.radio("Market Focus", ["Both", "ASX Only", "US Only"], horizontal=True, key="market_filter")
        st.selectbox("Historical Period", ["1mo", "3mo", "6mo", "1y"], index=["1mo", "3mo", "6mo", "1y"].index(st.session_state.period), key="period")
        
        st.divider()
        st.subheader("USD ↔ AUD")
        rate = get_usd_aud_rate()
        if rate:
            st.metric("1 USD =", f"{rate:.4f} AUD")
            c1, c2 = st.columns(2)
            with c1: usd = st.number_input("USD", value=1000.0, step=100.0, key="usd_input")
            with c2: st.number_input("AUD", value=round(usd * rate, 2), step=100.0, key="aud_input", disabled=True)
            st.caption(f"{usd:,.0f} USD = **{usd*rate:,.2f} AUD**")
        st.divider()
        st.info("**Rebound Score explained**  \n55% RSI (oversold) + 30% distance from 52w high + 15% momentum")
        if st.button("Refresh All Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    active_tickers = ALL_TICKERS if st.session_state.market_filter == "Both" else (ALL_ASX if st.session_state.market_filter == "ASX Only" else ALL_US)
    raw_data = fetch_batch_data(active_tickers, st.session_state.period, st.session_state.real_time_mode)
    summary_df = build_sector_df(active_tickers, raw_data)

    # Top-5 by market (final display enhancement)
    top5_asx = summary_df[summary_df["Market"] == "ASX"].head(5).copy() if not summary_df.empty else pd.DataFrame()
    top5_us = summary_df[summary_df["Market"] == "US"].head(5).copy() if not summary_df.empty else pd.DataFrame()

    # Tabs
    tab1, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🌍 Dashboard (All Sectors)",
        "🧠 Strategy & Grok Insights",
        "📋 Saved Analyses",
        "🔗 IBKR AU Portfolio",
        "🔮 Polymarket Insights",
        "🚀 Grok Chat",
        "📊 Enhanced Backtester"
    ])

    # TAB 1: Dashboard with Top-5 summary
    with tab1:
        st.subheader("🌍 Top Rebound Opportunities — All Sectors Combined")
        st.caption(f"**Data timeframe:** {get_data_timeframe(raw_data, st.session_state.real_time_mode, st.session_state.period)}")
        if not summary_df.empty:
            styled = summary_df.style.format({"Price": "${:.3f}", "Change %": "{:.2f}%", "Rebound Score": "{:.1f}", "RSI": "{:.1f}"}).map(
                lambda x: "color: #2ED573; font-weight: bold" if x >= 65 else ("color: #FFC107; font-weight: bold" if x >= 45 else "color: #FF4757; font-weight: bold"),
                subset=["Rebound Score"]
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)
            st.download_button("📥 Download Rebound Table as CSV", summary_df.to_csv(index=False), "rebound_opportunities.csv", "text/csv", use_container_width=True)

            # Top 5 by market
            col_asx, col_us = st.columns(2)
            with col_asx:
                st.markdown("**🇦🇺 Top 5 ASX**")
                if not top5_asx.empty:
                    st.dataframe(top5_asx[["Ticker", "Company", "Rebound Score", "Price", "Momentum"]].style.format({"Rebound Score": "{:.1f}"}), hide_index=True, use_container_width=True)
            with col_us:
                st.markdown("**🇺🇸 Top 5 US**")
                if not top5_us.empty:
                    st.dataframe(top5_us[["Ticker", "Company", "Rebound Score", "Price", "Momentum"]].style.format({"Rebound Score": "{:.1f}"}), hide_index=True, use_container_width=True)

            top_ticker = summary_df.iloc[0]["Ticker"]
            if top_ticker in raw_data:
                info = get_ticker_info(top_ticker)
                st.plotly_chart(create_price_rsi_chart(raw_data[top_ticker], top_ticker, info["name"]), use_container_width=True)
        st.subheader("🔍 Custom Ticker Rebound Evaluator")
        col1, col2 = st.columns([3, 1])
        with col1: custom_ticker = st.text_input("Ticker symbol", placeholder="e.g. AAPL, BHP.AX, JNS.AX", value="", key="custom_ticker_input")
        with col2:
            if st.button("Evaluate Rebound", use_container_width=True, type="primary"):
                df_custom, score, rsi_val, mom, error = evaluate_custom_ticker(custom_ticker, st.session_state.period, st.session_state.real_time_mode)
                if error:
                    st.error(error)
                else:
                    info = get_ticker_info(custom_ticker)
                    st.success(f"**{custom_ticker}** — Rebound Score: **{score:.1f}** | RSI: **{rsi_val}** | Momentum: **{mom}%**")
                    st.plotly_chart(create_price_rsi_chart(df_custom, custom_ticker, info["name"]), use_container_width=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Latest Price", f"${df_custom['Close'].iloc[-1]:.3f}")
                    c2.metric("Rebound Score", f"{score:.1f}")
                    c3.metric("RSI (14)", f"{rsi_val}")
        context = summary_df.head(10).to_string(index=False) if not summary_df.empty else "No data"
        add_page_analyzer("Dashboard", context, raw_data, st.session_state.selected_model, st.session_state.real_time_mode, st.session_state.period)

    # TAB 3–7 unchanged (streamlined calls only)
    with tab3:
        st.subheader("🧠 Strategy & Grok Insights")
        strategy_context = summary_df.to_string(index=False) if not summary_df.empty else "No data loaded yet"
        add_page_analyzer("Strategy & Grok Insights", strategy_context, raw_data, st.session_state.selected_model, st.session_state.real_time_mode, st.session_state.period)

    with tab4:
        st.subheader("📋 Saved Grok Analyses")
        st.caption(f"{len(st.session_state.get('saved_analyses', []))} analyses stored")
        if st.button("🗑️ Clear ALL saved analyses", type="secondary", use_container_width=True):
            clear_all_saved_analyses()
        if st.session_state.get("saved_analyses"):
            for analysis in reversed(st.session_state.saved_analyses):
                with st.expander(f"📌 {analysis['tab']} • {analysis['timestamp']}"):
                    st.caption(analysis['data_timeframe'])
                    st.write(analysis['response'])
        else:
            st.info("No analyses saved yet.")

    with tab5:
        st.subheader("🔗 IBKR AU – Auto Portfolio & Position Sizer")
        st.caption("IBKR-ready • Rebound Score weighted • Monthly/Yearly/Daily summaries")
        col_a, col_b = st.columns([2, 2])
        with col_a:
            account_size = st.number_input("Account Size (AUD)", value=50000.0, step=1000.0, format="%.0f")
            risk_percent = st.slider("Max Risk per Trade (%)", 0.5, 3.0, 1.0, 0.1)
        with col_b:
            stop_method = st.radio("Stop-Loss Method", ["ATR-based", "Fixed %"], horizontal=True)
            fixed_stop_pct = st.number_input("Fixed Stop %", value=5.0, step=0.5) if stop_method == "Fixed %" else 5.0
        if not summary_df.empty:
            portfolio_df = summary_df.head(12).copy()
            portfolio_df["Account Risk $"] = account_size * (risk_percent / 100)
            portfolio_df["Position Size"] = (portfolio_df["Account Risk $"] / (portfolio_df["Price"] * (portfolio_df["Rebound Score"] / 150)))
            portfolio_df["Shares"] = portfolio_df["Position Size"].astype(int)
            if stop_method == "ATR-based":
                for idx, row in portfolio_df.iterrows():
                    if row["Ticker"] in raw_data and not raw_data[row["Ticker"]].empty:
                        df = raw_data[row["Ticker"]]
                        tr = pd.concat([df["High"]-df["Low"], abs(df["High"]-df["Close"].shift()), abs(df["Low"]-df["Close"].shift())], axis=1).max(axis=1)
                        atr = tr.rolling(14).mean().iloc[-1]
                        portfolio_df.at[idx, "Stop %"] = round((atr / row["Price"]) * 100, 1) if atr > 0 else fixed_stop_pct
                    else:
                        portfolio_df.at[idx, "Stop %"] = fixed_stop_pct
            else:
                portfolio_df["Stop %"] = fixed_stop_pct
            portfolio_df["Stop Price"] = portfolio_df["Price"] * (1 - portfolio_df["Stop %"]/100)
            portfolio_df["Target Price"] = portfolio_df["Price"] * (1 + (100 - portfolio_df["Rebound Score"]) / 100)
            portfolio_df["Expected Edge"] = round(portfolio_df["Rebound Score"] * (portfolio_df["Momentum"] / 100 + 0.5), 1)
            portfolio_df["Daily Chg %"] = round(portfolio_df["Change %"], 2)
            display_cols = ["Ticker", "Company", "Rebound Score", "Price", "Shares", "Stop %", "Stop Price", "Target Price", "Expected Edge", "Daily Chg %"]
            styled_port = portfolio_df[display_cols].style.format({"Price": "${:.3f}", "Stop Price": "${:.3f}", "Target Price": "${:.3f}", "Rebound Score": "{:.1f}", "Expected Edge": "{:.1f}"}).background_gradient(subset=["Rebound Score"], cmap="RdYlGn")
            st.dataframe(styled_port, use_container_width=True, hide_index=True)
            export_df = portfolio_df[["Ticker", "Shares", "Price", "Stop Price", "Target Price", "Account Risk $", "Expected Edge"]].copy()
            export_df.columns = ["Symbol", "Quantity", "Entry", "Stop", "Target", "Risk_$", "Edge"]
            export_df["Action"] = "BUY"
            st.download_button(label="📤 Export IBKR Trade List CSV (ready for TWS import)", data=export_df.to_csv(index=False), file_name="IBKR_GeoSupply_Portfolio.csv", mime="text/csv", use_container_width=True)
        else:
            st.warning("Load Dashboard data first (refresh if needed)")
        add_page_analyzer("IBKR AU", "Portfolio & risk sizer", None, st.session_state.selected_model, st.session_state.real_time_mode, st.session_state.period)

    with tab6:
        st.subheader("🔮 Polymarket GeoSupply Insights")
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1: show_open = st.checkbox("Open Markets Only", value=True, key="pm_open_only")
        with col_btn2:
            if st.button("🔄 Refresh Open Markets", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        pm_df = fetch_polymarket_markets(show_open_only=show_open)
        if not pm_df.empty:
            st.dataframe(pm_df, use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Trade →")})
            st.subheader("🔗 Polymarket ↔ Rebound Correlation")
            corr_df = analyze_polymarket_correlation(pm_df, summary_df)
            if not corr_df.empty:
                st.dataframe(corr_df, use_container_width=True, hide_index=True, column_config={"Link": st.column_config.LinkColumn("Trade →")})
            else:
                st.info("No strong correlation matches found.")
            context_pm = pm_df.to_string(index=False)
            add_page_analyzer("Polymarket Insights", context_pm, None, st.session_state.selected_model, st.session_state.real_time_mode, st.session_state.period)
        else:
            st.warning("No relevant open markets right now.")

    with tab7:
        st.subheader("🚀 Grok Chat")
        st.caption("Full conversational Grok (streaming) — same API key & model as the rest of the app")
        client = get_grok_client()
        if not client:
            st.error("Please enter your Grok API key in the sidebar first.")
            st.stop()
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = [{"role": "system", "content": "You are Grok, a helpful and maximally truthful AI built by xAI."}]
        for msg in st.session_state.chat_messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        if prompt := st.chat_input("Ask Grok anything..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                stream = client.chat.completions.create(model=st.session_state.selected_model, messages=st.session_state.chat_messages, stream=True, temperature=0.7, max_tokens=4096)
                response = st.write_stream(chunk.choices[0].delta.content or "" for chunk in stream)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_messages = [{"role": "system", "content": "You are Grok, a helpful and maximally truthful AI built by xAI."}]
            st.rerun()

    # TAB 8: Enhanced Backtester
    with tab8:
        st.subheader("📊 Enhanced GeoSupply Rebound Backtester")
        st.caption("Walk-forward OOS • Commission costs • Portfolio across all sectors • yfinance benchmark (SPY)")

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            scope = st.selectbox("Backtest Scope", ["Single Ticker", "ASX Portfolio", "US Portfolio", "Full GeoSupply Portfolio"], index=0)
            if scope == "Single Ticker":
                backtest_ticker = st.text_input("Ticker", value=summary_df.iloc[0]["Ticker"] if not summary_df.empty else "BHP.AX", key="backtest_ticker")
                tickers_list = [backtest_ticker]
            elif scope == "ASX Portfolio":
                tickers_list = ALL_ASX[:15]  # limit for speed
            elif scope == "US Portfolio":
                tickers_list = ALL_US[:15]
            else:
                tickers_list = ALL_TICKERS[:20]

        with col2:
            test_period = st.selectbox("History Length", ["2y", "5y"], index=1)
            entry_threshold = st.slider("Entry Threshold", 50, 90, 65)
        with col3:
            exit_threshold = st.slider("Exit Threshold", 20, 60, 40)
            commission = st.number_input("Commission % (round-trip)", value=0.10, step=0.05, format="%.2f")
            wf = st.checkbox("Walk-Forward OOS Validation", value=True)

        if st.button("🚀 Run Full Backtest", type="primary", use_container_width=True):
            with st.spinner(f"Running walk-forward backtest on {len(tickers_list)} symbols..."):
                results = run_enhanced_backtest(tickers_list, test_period, entry_threshold, exit_threshold, commission, wf)
                if "error" in results:
                    st.error(results["error"])
                else:
                    st.success("✅ Backtest Complete")
                    if results.get("portfolio"):
                        p = results["portfolio"]
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Portfolio Trades", p["Num_Trades"])
                        c2.metric("Win Rate", f"{p['Win_Rate_%']}%")
                        c3.metric("Avg Return", f"{p['Avg_Return_%']}%")
                        c4.metric("Total Return", f"{p['Total_Return_%']}%")
                        st.caption(f"SPY Benchmark: {results['benchmark']['SPY_Total_Return_%']}%")
                        if not p["Trades_DF"].empty:
                            st.dataframe(p["Trades_DF"].head(20), use_container_width=True, hide_index=True)

                    st.info("**Individual ticker results** (expand for details)")
                    for t, r in results.get("individual", {}).items():
                        with st.expander(f"{t} — {r['Num_Trades']} trades"):
                            st.write(f"Win Rate: **{r['Win_Rate_%']}%** | Avg: **{r['Avg_Return_%']}%** | Total: **{r['Total_Return_%']}%**")

        st.info("**Model enhancements**: Vectorized scoring • Walk-forward OOS split • Real commission drag • Equal-weight portfolio • External SPY benchmark via yfinance.")

        add_page_analyzer("Enhanced Backtester", "Walk-forward + portfolio results", None, st.session_state.selected_model, st.session_state.real_time_mode, st.session_state.period)

if __name__ == "__main__":
    main()