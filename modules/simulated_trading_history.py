TAB_NAME = "📜 Simulated Trading History & Portfolio"

def build_tab():
    import gradio as gr
    import pandas as pd
    from datetime import datetime
    import sqlite3
    import plotly.express as px

    # Reuse or create simple DB table (compatible with core)
    DB_NAME = "xforge_historical.db"

    def init_history_db():
        conn = sqlite3.connect(DB_NAME)
        conn.execute('''CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            ticker TEXT,
            action TEXT,
            price REAL,
            quantity REAL,
            strategy TEXT,
            pnl REAL DEFAULT 0
        )''')
        conn.commit()
        conn.close()

    init_history_db()

    with gr.Blocks() as tab_block:
        gr.Markdown("## 📜 Simulated Trading History")
        gr.Markdown("Persistent record of paper trades from Strategy Optimizer. Enhances accuracy with performance analytics and equity tracking.")

        history_table = gr.DataFrame(label="Trade History", value=pd.DataFrame())
        equity_plot = gr.Plot(label="Equity Curve")
        summary = gr.Markdown("Summary Stats")

        refresh_btn = gr.Button("🔄 Refresh History", variant="primary")

        def load_history():
            try:
                conn = sqlite3.connect(DB_NAME)
                df = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY timestamp DESC", conn)
                conn.close()
                if df.empty:
                    return pd.DataFrame(columns=["timestamp", "ticker", "action", "price", "quantity", "strategy", "pnl"]), None, "No trades yet."
                # Simple equity curve simulation
                df['cum_pnl'] = df['pnl'].cumsum()
                fig = px.line(df, x='timestamp', y='cum_pnl', title="Simulated Equity Curve")
                total_pnl = df['pnl'].sum()
                num_trades = len(df)
                win_rate = (df['pnl'] > 0).mean() * 100 if num_trades > 0 else 0
                stats = f"**Total P&L: ${total_pnl:.2f}** | Trades: {num_trades} | Win Rate: {win_rate:.1f}%"
                return df, fig, stats
            except Exception as e:
                return pd.DataFrame(), None, f"Error: {str(e)}"

        refresh_btn.click(load_history, outputs=[history_table, equity_plot, summary])

        # Auto load
        tab_block.load(load_history, outputs=[history_table, equity_plot, summary])

        gr.Markdown("**Tip:** Trades from Paper Trader in Strategy Optimizer are logged here for full history and analysis.")

    return tab_block