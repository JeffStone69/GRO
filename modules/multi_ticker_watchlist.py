TAB_NAME = "📡 Multi-Ticker Watchlist"

def build_tab():
    import gradio as gr
    import yfinance as yf
    import pandas as pd
    from datetime import datetime

    default_tickers = "TSLA,AAPL,GOOGL,MSFT,NVDA"

    with gr.Blocks() as tab_block:
        gr.Markdown("## 📡 Real-Time Multi-Ticker Watchlist")
        gr.Markdown("Monitor multiple tickers with live prices, % changes, volume, and signals. Enhances accuracy by comparing relative performance.")
        tickers_input = gr.Textbox(label="Tickers (comma-separated)", value=default_tickers, placeholder="TSLA,AAPL,GOOGL")
        refresh_interval = gr.Slider(label="Auto-Refresh Interval (seconds)", minimum=5, maximum=60, value=10, step=5)
        watchlist_table = gr.DataFrame(label="Live Watchlist Data", value=pd.DataFrame(columns=["Ticker", "Price", "% Change", "Volume", "Signal", "Last Updated"]))
        status = gr.Markdown("🔄 Live updates active")

        def update_watchlist(tickers_str):
            tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
            data = []
            for t in tickers[:10]:  # limit for performance
                try:
                    ticker = yf.Ticker(t)
                    info = ticker.fast_info
                    price = round(info.get('lastPrice') or info.get('regularMarketPrice', 0), 2)
                    change_pct = round((info.get('regularMarketChangePercent') or 0) * 100, 2)
                    volume = int(info.get('regularMarketVolume', 0))
                    # Simple signal from optimizer style
                    signal = "BUY" if change_pct > 0.5 else "SELL" if change_pct < -0.5 else "HOLD"
                    data.append({"Ticker": t, "Price": price, "% Change": change_pct, "Volume": volume, "Signal": signal, "Last Updated": datetime.now().strftime("%H:%M:%S")})
                except Exception:
                    data.append({"Ticker": t, "Price": "N/A", "% Change": 0, "Volume": 0, "Signal": "ERROR", "Last Updated": "N/A"})
            df = pd.DataFrame(data)
            return df

        timer = gr.Timer(every=10)
        timer.tick(update_watchlist, inputs=tickers_input, outputs=watchlist_table)

        def initial_load(tickers_str):
            return update_watchlist(tickers_str)

        tab_block.load(initial_load, inputs=tickers_input, outputs=watchlist_table)

        gr.Button("🔄 Manual Refresh", variant="primary").click(update_watchlist, inputs=tickers_input, outputs=watchlist_table)

    return tab_block