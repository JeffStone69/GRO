#!/usr/bin/env python3
"""
XForge Trader v9.2 Beta – Main App (Import-safe + API Key Validation + Large Text)
"""
import sys
import os
from pathlib import Path

# === CRITICAL FIX: Make FORGE importable when running directly ===
sys.path.insert(0, str(Path(__file__).parent))

import gradio as gr
from config import XAI_API_KEY, DB_PATH, SIM_DB_PATH
from modules.multi_ticker_watchlist import build_watchlist_tab
from modules.strategy_optimizer import build_optimizer_tab
from modules.simulated_trading_history import build_history_tab
from Self_Improve.SIM import build_ui as build_sim_tab
from FORGE.utils.logging import setup_logging

logger = setup_logging("XForgeMain")

def create_xforge_app():
    fullscreen = os.getenv("XFORGE_FULLSCREEN") == "true"
    large_text = os.getenv("XFORGE_LARGE_TEXT") == "true"

    css = f"""
    .gradio-container {{ 
        background: linear-gradient(135deg, #0a0f1a 0%, #1f2937 100%) !important;
        font-size: {'1.45rem' if large_text else '1.15rem'} !important;
    }}
    .gr-button, .gr-textbox, .gr-dropdown {{ 
        font-size: {'1.6em' if large_text else '1.25em'} !important; 
        padding: 22px !important; 
    }}
    .gr-markdown h1 {{ font-size: {'3.6em' if large_text else '2.6em'} !important; color: #22c55e; }}
    """

    with gr.Blocks(title="XForge Trader + SIM v9.2 Beta", theme=gr.themes.Dark(), css=css, fill_height=True) as demo:
        gr.Markdown("# XFORGE TRADER + SIM\n**v9.2 Beta – Self-Improving Autonomous Trading**")

        # === API KEY INPUT + VALIDATION ===
        with gr.Row():
            api_key_input = gr.Textbox(
                label="XAI_API_KEY (or GROK_API_KEY)",
                type="password",
                placeholder="sk-...",
                value=XAI_API_KEY or "",
                interactive=True
            )
            validate_btn = gr.Button("Validate & Save Key", variant="primary")
            status = gr.Markdown("")

        def validate_api_key(key):
            if not key or not key.startswith("sk-"):
                return "❌ Invalid key. Must start with 'sk-'"
            os.environ["XAI_API_KEY"] = key
            os.environ["GROK_API_KEY"] = key
            logger.info("API key validated and saved to environment")
            return "✅ API key validated successfully! All features now active."

        validate_btn.click(validate_api_key, inputs=api_key_input, outputs=status)

        with gr.Tabs():
            build_watchlist_tab()
            build_optimizer_tab()
            build_history_tab()
            with gr.Tab("Self-Improvement (SIM)"):
                build_sim_tab()

    logger.info("Gradio app initialized successfully")
    return demo

if __name__ == "__main__":
    app = create_xforge_app()
    app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, show_api=False)
    logger.info("Browser window opened at http://127.0.0.1:7860")
