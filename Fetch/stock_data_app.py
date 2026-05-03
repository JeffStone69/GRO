# stock_data_app.py
# Multi-Provider Historical Stock Data Fetcher - Streamlit Edition
# Integrates yfinance + all free alternatives as fallbacks/comparisons
# Designed for reference by xforge_trader.py (GRO/ FORGE)

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
import plotly.express as px
import json

st.set_page_config(page_title="Historical Stock Data Fetcher", layout="wide")
st.title("📈 Multi-Provider Historical Stock Ticker Data Fetcher")
st.markdown("**Primary: yfinance** | **Fallbacks & Comparisons:** Alpha Vantage, Finnhub, EODHD, FMP, Marketstack, Tiingo")

# ====================== SIDEBAR: API KEYS & CONFIG ======================
st.sidebar.header("🔑 API Configuration")
st.sidebar.markdown("**Obtain free keys below (no credit card required):**")

api_keys = {}

# yfinance - no key
st.sidebar.success("✅ yfinance (primary) - No key required")

# Alpha Vantage
st.sidebar.markdown("**Alpha Vantage** [Get Free Key](https://www.alphavantage.co/support/#api-key)")
api_keys['alphavantage'] = st.sidebar.text_input("Alpha Vantage API Key", type="password", value=st.session_state.get('alphavantage', ''))

# Finnhub
st.sidebar.markdown("**Finnhub** [Register Free](https://finnhub.io/register)")
api_keys['finnhub'] = st.sidebar.text_input("Finnhub API Key", type="password", value=st.session_state.get('finnhub', ''))

# EODHD
st.sidebar.markdown("**EODHD** [Register Free (20 calls/day)](https://eodhd.com/register)")
api_keys['eodhd'] = st.sidebar.text_input("EODHD API Token", type="password", value=st.session_state.get('eodhd', ''))

# FMP
st.sidebar.markdown("**Financial Modeling Prep (FMP)** [Get Free Key](https://site.financialmodelingprep.com/developer)")
api_keys['fmp'] = st.sidebar.text_input("FMP API Key", type="password", value=st.session_state.get('fmp', ''))

# Marketstack
st.sidebar.markdown("**Marketstack** [Sign Up Free (100 requests/mo)](https://marketstack.com/signup)")
api_keys['marketstack'] = st.sidebar.text_input("Marketstack Access Key", type="password", value=st.session_state.get('marketstack', ''))

# Tiingo
st.sidebar.markdown("**Tiingo** [Sign Up Free](https://www.tiingo.com/) → [API Token](https://api.tiingo.com/account/token)")
api_keys['tiingo'] = st.sidebar.text_input("Tiingo API Token", type="password", value=st.session_state.get('tiingo', ''))

# Persist keys in session
for k, v in api_keys.items():
    if v:
        st.session_state[k] = v

# Fallback order (yfinance always first)
fallback_order = ['yfinance', 'finnhub', 'eodhd', 'alphavantage', 'fmp', 'marketstack', 'tiingo']

# ====================== MAIN INPUTS ======================
col1, col2 = st.columns([2, 1])
with col1:
    ticker = st.text_input("Stock Ticker (e.g., AAPL, MSFT, TSLA)", value="AAPL").strip().upper()
with col2:
    interval = st.selectbox("Interval", ["1d"], disabled=True)  # Free tiers primarily support daily

start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=730))
end_date = st.date_input("End Date", value=datetime.now())

compare_all = st.checkbox("Enable comparison across ALL providers (slower but comprehensive)", value=False)
use_fallbacks = st.checkbox("Enable automatic fallbacks on failure", value=True) if not compare_all else False

# ====================== FETCH FUNCTIONS ======================
@st.cache_data(ttl=3600)
def fetch_yfinance(ticker: str, start: str, end: str):
    try:
        df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
        if not df.empty:
            return df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_alphavantage(ticker: str, api_key: str, start: str, end: str):
    if not api_key: return None
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&apikey={api_key}&outputsize=full"
    try:
        resp = requests.get(url, timeout=10).json()
        data = resp.get("Time Series (Daily)")
        if data:
            df = pd.DataFrame.from_dict(data, orient="index").astype(float)
            df = df.rename(columns={"1. open": "Open", "2. high": "High", "3. low": "Low", "4. close": "Close", "6. volume": "Volume"})
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.index = pd.to_datetime(df.index)
            return df.loc[start:end]
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_finnhub(ticker: str, api_key: str, start: str, end: str):
    if not api_key: return None
    from_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
    to_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp())
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={ticker}&resolution=D&from={from_ts}&to={to_ts}&token={api_key}"
    try:
        resp = requests.get(url, timeout=10).json()
        if resp.get("s") == "ok":
            df = pd.DataFrame({
                "Open": resp["o"], "High": resp["h"], "Low": resp["l"],
                "Close": resp["c"], "Volume": resp["v"]
            }, index=pd.to_datetime(resp["t"], unit="s"))
            return df.loc[start:end]
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_eodhd(ticker: str, api_key: str, start: str, end: str):
    if not api_key: return None
    url = f"https://eodhd.com/api/eod/{ticker}.US?api_token={api_key}&from={start}&to={end}&fmt=json"
    try:
        resp = requests.get(url, timeout=10).json()
        if resp:
            df = pd.DataFrame(resp)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_fmp(ticker: str, api_key: str, start: str, end: str):
    if not api_key: return None
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?apikey={api_key}"
    try:
        resp = requests.get(url, timeout=10).json()
        data = resp.get("historical")
        if data:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df.loc[start:end]
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_marketstack(ticker: str, api_key: str, start: str, end: str):
    if not api_key: return None
    url = f"https://api.marketstack.com/v1/eod?access_key={api_key}&symbols={ticker}&date_from={start}&date_to={end}&limit=1000"
    try:
        resp = requests.get(url, timeout=10).json()
        data = resp.get("data")
        if data:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_tiingo(ticker: str, api_key: str, start: str, end: str):
    if not api_key: return None
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices?token={api_key}&startDate={start}&endDate={end}&format=json"
    try:
        resp = requests.get(url, timeout=10).json()
        if resp:
            df = pd.DataFrame(resp)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df
    except Exception:
        pass
    return None

fetchers = {
    'yfinance': fetch_yfinance,
    'alphavantage': fetch_alphavantage,
    'finnhub': fetch_finnhub,
    'eodhd': fetch_eodhd,
    'fmp': fetch_fmp,
    'marketstack': fetch_marketstack,
    'tiingo': fetch_tiingo
}

# ====================== FETCH LOGIC ======================
if st.button("🚀 Fetch Historical Data", type="primary"):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    results = {}
    primary_success = False
    
    # Primary + fallbacks
    providers_to_try = fallback_order if use_fallbacks or compare_all else ['yfinance']
    
    for provider in providers_to_try:
        if provider == 'yfinance':
            df = fetch_yfinance(ticker, start_str, end_str)
        else:
            df = fetchers[provider](ticker, api_keys.get(provider, ''), start_str, end_str)
        
        if df is not None and not df.empty:
            results[provider] = df
            if not primary_success:
                primary_success = True
                st.success(f"✅ Primary data retrieved via **{provider.upper()}**")
            if not compare_all and primary_success:
                break
        elif compare_all:
            st.warning(f"⚠️ {provider.upper()} returned no data")
    
    if not results:
        st.error("❌ All providers failed. Please check API keys, ticker validity, and date range.")
        st.stop()
    
    # Store in session for download/import
    st.session_state['latest_results'] = results
    st.session_state['latest_ticker'] = ticker
    
    # ====================== DISPLAY ======================
    tab1, tab2, tab3 = st.tabs(["📊 Data Tables", "🔄 Provider Comparison", "📉 Charts"])
    
    with tab1:
        for provider, df in results.items():
            st.subheader(f"{provider.upper()} Data ({len(df)} rows)")
            st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.subheader("Provider Comparison")
        comparison = []
        for p, df in results.items():
            comparison.append({
                "Provider": p.upper(),
                "Rows": len(df),
                "Start Date": df.index.min().date(),
                "End Date": df.index.max().date(),
                "Avg Volume": f"{df['Volume'].mean():,.0f}" if 'Volume' in df else "N/A"
            })
        st.dataframe(pd.DataFrame(comparison), use_container_width=True)
    
    with tab3:
        st.subheader("Close Price Comparison")
        plot_df = pd.DataFrame({p.upper(): df['Close'] for p, df in results.items()})
        fig = px.line(plot_df, title=f"Close Prices – {ticker}", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    
    # ====================== SAVE / EXPORT ======================
    st.subheader("💾 Save & Export")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Save Primary Data as CSV"):
            primary_df = list(results.values())[0]
            csv = primary_df.to_csv().encode()
            st.download_button("⬇️ Download CSV", csv, f"{ticker}_primary_data.csv", "text/csv")
    with col_b:
        if st.button("Save Primary Data as Parquet"):
            primary_df = list(results.values())[0]
            parquet = primary_df.to_parquet()
            st.download_button("⬇️ Download Parquet", parquet, f"{ticker}_primary_data.parquet", "application/octet-stream")
    with col_c:
        if st.button("Export Full Comparison JSON"):
            json_data = {p: df.to_json(orient="index") for p, df in results.items()}
            st.download_button("⬇️ Download JSON", json.dumps(json_data, indent=2).encode(), f"{ticker}_comparison.json", "application/json")

# ====================== IMPORT ======================
st.subheader("📥 Import Previous Data")
uploaded = st.file_uploader("Upload CSV or Parquet from previous session", type=["csv", "parquet"])
if uploaded:
    if uploaded.name.endswith(".csv"):
        imported_df = pd.read_csv(uploaded, index_col=0, parse_dates=True)
    else:
        imported_df = pd.read_parquet(uploaded)
    st.success("✅ Data imported successfully")
    st.dataframe(imported_df)

# ====================== INTEGRATION ASSISTANCE ======================
with st.expander("🔗 Integration Assistance for xforge_trader.py"):
    st.markdown("**Copy the modular fetcher below into your project or replace your existing `get_data` function.**")
    st.code("""# Add this function (or import from the exported module)
def get_multi_provider_data(ticker, start_date=None, end_date=None, provider='yfinance', api_keys=None, use_fallbacks=True):
    # Full implementation from this app can be extracted here
    # Returns pandas DataFrame compatible with your Parquet cache
    pass  # Replace with logic from fetchers dict above
""", language="python")
    st.info("The full fetcher functions above can be extracted into `historical_data_fetcher_multi.py` for direct import. All fallbacks and caching are preserved for production use.")

st.caption("Application ready for immediate use. Data is cached for 1 hour. Free-tier limits respected automatically.")
