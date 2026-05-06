# XForge Trader Main Orchestrator (Full Rewrite)
import gradio as gr
from FORGE.config import config
from modules.multi_ticker_watchlist import build_watchlist_tab
from modules.strategy_optimizer import build_optimizer_tab
from modules.simulated_trading_history import build_history_tab
from FORGE.utils import db_connection

def create_xforge_app():
    with gr.Blocks(title='XForge Trader', theme=gr.themes.Dark()) as demo:
        gr.Markdown('# XForge Trader + SIM')
        with gr.Tabs():
            build_watchlist_tab()
            build_optimizer_tab()
            build_history_tab()
    return demo

if __name__ == "__main__":
    app = create_xforge_app()
    app.launch()