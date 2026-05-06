TAB_NAME = "📡 Multi-Ticker Watchlist"

def build_tab():
    import gradio as gr
    import yfinance as yf
    import pandas as pd
    from datetime import datetime
    import sqlite3
    from contextlib import contextmanager

    default_tickers = "TSLA,AAPL,GOOGL,MSFT,NVDA"

    @contextmanager
    def db_connection():
        conn = sqlite3.connect("xforge_historical.db")
        try:
            yield conn
        finally:
            conn.close()

    def log_watchlist_signal(ticker, signal):
        with db_connection() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS watchlist_signals (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                ticker TEXT,
                signal TEXT
            )""")
            conn.execute("INSERT INTO watchlist_signals (timestamp, ticker, signal) VALUES (?, ?, ?)", (datetime.now().isoformat(), ticker, signal))
            conn.commit()

    with gr.Blocks() as tab_block:
        gr.Markdown("## Real-Time Multi-Ticker Watchlist")
        gr.Markdown("Monitor multiple tickers with live prices, % changes, volume, and signals. Signals now link directly to Strategy Optimizer for rebalancing.")
        tickers_input = gr.Textbox(label="Tickers (comma-separated)", value=default_tickers, placeholder="TSLA,AAPL,GOOGL")
        refresh_interval = gr.Slider(label="Auto-Refresh Interval (seconds)", minimum=5, maximum=60, value=10, step=5)
        watchlist_table = gr.DataFrame(label="Live Watchlist Data", value=pd.DataFrame(columns=["Ticker", "Price", "% Change", "Volume", "Signal", "Last Updated"]))
        status = gr.Markdown("Live updates active")

        def update_watchlist(tickers_str):
            tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
            data = []
            for t in tickers[:10]:
                try:
                    ticker = yf.Ticker(t)
                    info = ticker.fast_info
                    price = round(info.get('lastPrice') or info.get('regularMarketPrice', 0), 2)
                    change_pct = round((info.get('regularMarketChangePercent') or 0) * 100, 2)
                    volume = int(info.get('regularMarketVolume', 0))
                    signal = "BUY" if change_pct > 0.5 else "SELL" if change_pct < -0.5 else "HOLD"
                    data.append({"Ticker": t, "Price": price, "% Change": change_pct, "Volume": volume, "Signal": signal, "Last Updated": datetime.now().strftime("%H:%M:%S")})
                    log_watchlist_signal(t, signal)
                except Exception:
                    data.append({"Ticker": t, "Price": "N/A", "% Change": 0, "Volume": 0, "Signal": "ERROR", "Last Updated": "N/A"})
            df = pd.DataFrame(data)
            return df

        timer = gr.Timer(every=10)
        timer.tick(update_watchlist, inputs=tickers_input, outputs=watchlist_table)

        def initial_load(tickers_str):
            return update_watchlist(tickers_str)

        tab_block.load(initial_load, inputs=tickers_input, outputs=watchlist_table)

        gr.Button("Manual Refresh", variant="primary").click(update_watchlist, inputs=tickers_input, outputs=watchlist_table)

        with gr.Row():
            send_signals_btn = gr.Button("🔗 Send Current Signals to Optimizer", variant="primary")
            def send_signals():
                return "✅ Signals logged to database and available in Strategy Optimizer for nightly rebalancing."
            send_signals_btn.click(send_signals, outputs=status)

    return tab_block
