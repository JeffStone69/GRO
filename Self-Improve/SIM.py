#!/usr/bin/env python3
"""
XForge Self-Improvement Module - Secure + Premium Tech UI
- API key NEVER saved to disk
- Beautiful dark cyber/tech design with large text
- Live improvement & log metrics dashboard
- Model selector with latest xAI models
- Large prominent Save & Exit buttons
"""

import subprocess
import sys
import importlib
import os
from pathlib import Path
from datetime import datetime

def ensure_dependencies() -> None:
    packages = ["openai", "pandas", "pydantic", "gradio", "requests"]
    for pkg in packages:
        try:
            importlib.import_module(pkg.replace("-", "_"))
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "jinja2>=3.1.5", "--quiet", "--upgrade"])
    print("Dependencies ready.")

ensure_dependencies()

import sqlite3
import pandas as pd
import requests
from openai import OpenAI
from pydantic import BaseModel, Field, SecretStr
import gradio as gr

class SelfImproveConfig(BaseModel):
    db_name: str = "xforge_self_improve.db"
    grok_model: str = "grok-4.3"
    max_errors: int = 20
    grok_api_key: SecretStr = Field(default=SecretStr(""))

CONFIG = SelfImproveConfig()

# ==================== SECURE API KEY HANDLING ====================
def get_grok_api_key() -> str:
    key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    return key.strip() if key else ""

def init_db() -> None:
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY, timestamp TEXT, section TEXT, error TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS improvements (id INTEGER PRIMARY KEY, timestamp TEXT, suggestion TEXT, user_feedback TEXT)""")
        conn.commit()
        conn.close()
    except Exception:
        pass

def log_error(section: str, error_msg: str) -> None:
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        conn.execute("INSERT INTO errors (timestamp, section, error) VALUES (?, ?, ?)",
                     (datetime.now().isoformat(), section, error_msg))
        conn.commit()
        conn.close()
    except Exception:
        pass

def log_improvement(suggestion: str, user_feedback: str = "") -> None:
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        conn.execute("INSERT INTO improvements (timestamp, suggestion, user_feedback) VALUES (?, ?, ?)",
                     (datetime.now().isoformat(), suggestion, user_feedback))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_metrics() -> tuple[int, int, str]:
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        errors = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
        improvements = conn.execute("SELECT COUNT(*) FROM improvements").fetchone()[0]
        last = conn.execute("SELECT MAX(timestamp) FROM improvements").fetchone()[0]
        conn.close()
        last_str = last[:19] if last else "Never"
        return errors, improvements, last_str
    except Exception:
        return 0, 0, "Never"

def fetch_github_content(url: str) -> str:
    try:
        if "github.com" in url and not url.startswith("https://raw.githubusercontent.com"):
            if "/blob/" in url:
                url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            else:
                for candidate in [
                    url.replace("github.com", "raw.githubusercontent.com") + "/main/README.md",
                    url.replace("github.com", "raw.githubusercontent.com") + "/main/main.py",
                    url.replace("github.com", "raw.githubusercontent.com") + "/main/app.py"
                ]:
                    r = requests.get(candidate, timeout=10)
                    if r.status_code == 200:
                        return r.text
                return "Could not fetch default files."
        r = requests.get(url, timeout=15)
        return r.text if r.status_code == 200 else f"HTTP Error {r.status_code}"
    except Exception as e:
        return f"Fetch failed: {str(e)}"

def self_improve(script_content: str = "", github_url: str = "", user_feedback: str = "") -> tuple[str, str]:
    api_key = CONFIG.grok_api_key.get_secret_value().strip() or get_grok_api_key()
    if not api_key:
        return "Error: Grok API key required. Set XAI_API_KEY or enter in UI.", ""

    try:
        conn = sqlite3.connect(CONFIG.db_name)
        errors_df = pd.read_sql_query(f"SELECT * FROM errors ORDER BY timestamp DESC LIMIT {CONFIG.max_errors}", conn)
        conn.close()

        context = ""
        if not errors_df.empty:
            context += "Recent Errors:\n" + errors_df.to_string(index=False) + "\n\n"
        if github_url.strip():
            context += f"GitHub Content:\n{fetch_github_content(github_url.strip())[:12000]}\n\n"
        if script_content.strip():
            context += "Provided Script:\n" + script_content[:12000] + "\n\n"
        if user_feedback.strip():
            context += f"User Instructions:\n{user_feedback}\n\n"

        if not context:
            return "No content provided to analyze.", ""

        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        prompt = (
            "You are an expert Python engineer. Return TWO parts separated by '---IMPROVED-CODE---':\n"
            "1. Detailed explanation of improvements.\n"
            "2. The complete, ready-to-run improved Python script.\n\n" + context
        )
        response = client.chat.completions.create(
            model=CONFIG.grok_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        full_text = response.choices[0].message.content.strip()

        if "---IMPROVED-CODE---" in full_text:
            explanation, improved_code = full_text.split("---IMPROVED-CODE---", 1)
        else:
            explanation = full_text
            improved_code = ""

        log_improvement(full_text, user_feedback)
        return explanation.strip(), improved_code.strip()

    except Exception as e:
        log_error("Self-Improve", str(e))
        return f"Analysis failed: {str(e)}", ""

def save_improved_file(improved_code: str) -> str:
    if not improved_code:
        return "No code to save."
    counter = 1
    while Path(f"improved_script_v{counter}.py").exists():
        counter += 1
    filename = f"improved_script_v{counter}.py"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(improved_code)
    return f"✅ Saved as {filename}"

def export_csv(table: str) -> str:
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY timestamp DESC", conn)
        conn.close()
        filename = f"{table}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        return f"✅ Exported to {filename}"
    except Exception as e:
        return f"Export failed: {str(e)}"

# ==================== PREMIUM TECH UI ====================
def build_ui():
    custom_css = """
    .gradio-container { background: linear-gradient(135deg, #0a0f1a 0%, #111827 100%) !important; color: #e0e7ff; font-size: 1.1em; }
    .gr-button { font-size: 1.35em !important; padding: 18px 40px !important; border-radius: 12px !important; font-weight: 700 !important; }
    .gr-button-primary { background: linear-gradient(90deg, #22c55e, #16a34a) !important; color: white !important; }
    .gr-button-stop { background: linear-gradient(90deg, #ef4444, #b91c1c) !important; color: white !important; }
    .gr-textbox, .gr-dropdown, .gr-textbox textarea { font-size: 1.15em !important; }
    .gr-markdown h1, .gr-markdown h2 { font-size: 2.1em !important; color: #22c55e; }
    .metric-card { background: #1f2937; border: 2px solid #22c55e; border-radius: 16px; padding: 24px; text-align: center; margin: 10px; box-shadow: 0 0 20px rgba(34,197,94,0.2); }
    .metric-number { font-size: 3.2em; font-weight: 800; color: #22c55e; }
    .section-header { font-size: 1.8em; color: #22c55e; border-bottom: 3px solid #22c55e; padding-bottom: 8px; }
    """

    with gr.Blocks(title="XForge • Self-Improvement", theme=gr.themes.Base(), css=custom_css) as demo:
        # Top bar
        with gr.Row():
            gr.Markdown("# XFORGE", elem_classes=["section-header"])
            with gr.Column(scale=1):
                model_dropdown = gr.Dropdown(
                    choices=["grok-4.3", "grok-4.20-reasoning", "grok-4.20-non-reasoning",
                             "grok-4.20-multi-agent-0309", "grok-4-1-fast-reasoning", "grok-4-1-fast-non-reasoning"],
                    value=CONFIG.grok_model,
                    label="🧠 AI Model",
                    scale=1
                )
            with gr.Column(scale=1):
                api_status = gr.Markdown("🔑 **API Key:** Not validated", visible=True)

        # API Key Section (hidden after validation)
        with gr.Row(visible=False) as api_key_row:
            with gr.Column():
                gr.Markdown("### 🔐 Enter xAI API Key (Memory Only)")
                api_key_input = gr.Textbox(label="API Key", type="password", placeholder="xai-...", scale=3)
                validate_btn = gr.Button("✅ Validate Key", variant="primary", size="lg")
                key_status = gr.Markdown("")

        # Main Content
        with gr.Tabs() as tabs:
            # DASHBOARD TAB
            with gr.Tab("📊 Dashboard", id=0):
                gr.Markdown("## Live Improvement & Log Metrics")
                with gr.Row():
                    with gr.Column():
                        error_card = gr.HTML("<div class='metric-card'><div class='metric-number'>0</div><div style='font-size:1.4em'>Total Errors Logged</div></div>")
                    with gr.Column():
                        improve_card = gr.HTML("<div class='metric-card'><div class='metric-number'>0</div><div style='font-size:1.4em'>Improvements Generated</div></div>")
                    with gr.Column():
                        last_card = gr.HTML("<div class='metric-card'><div style='font-size:1.8em;font-weight:700'>Never</div><div style='font-size:1.4em'>Last Activity</div></div>")

                refresh_metrics_btn = gr.Button("🔄 Refresh Metrics", variant="secondary", size="lg")

                def update_metrics():
                    errors, improves, last = get_metrics()
                    return (
                        f"<div class='metric-card'><div class='metric-number'>{errors}</div><div style='font-size:1.4em'>Total Errors Logged</div></div>",
                        f"<div class='metric-card'><div class='metric-number'>{improves}</div><div style='font-size:1.4em'>Improvements Generated</div></div>",
                        f"<div class='metric-card'><div style='font-size:1.8em;font-weight:700'>{last}</div><div style='font-size:1.4em'>Last Activity</div></div>"
                    )

                refresh_metrics_btn.click(update_metrics, outputs=[error_card, improve_card, last_card])

            # ANALYZE TAB
            with gr.Tab("🔍 Analyze & Iterate", id=1):
                with gr.Row():
                    script_input = gr.Textbox(label="Paste Script / Code / Log", lines=10)
                    github_input = gr.Textbox(label="GitHub URL", placeholder="https://github.com/... or raw URL")
                feedback_input = gr.Textbox(label="Iteration Instructions (optional)", lines=3)
                file_input = gr.File(label="Upload .py / .log file", file_types=[".py", ".log", ".txt"])

                with gr.Row():
                    improve_btn = gr.Button("🚀 RUN SELF-IMPROVEMENT ANALYSIS", variant="primary", size="lg", scale=2)
                    save_btn = gr.Button("💾 SAVE IMPROVED CODE", variant="primary", size="lg", scale=1)

                with gr.Row():
                    output_explanation = gr.Textbox(label="Analysis & Recommendations", lines=14, interactive=False)
                    output_code = gr.Textbox(label="Improved Code", lines=14, interactive=False)

                save_status = gr.Textbox(label="Save Status", interactive=False)

            # EXPORT TAB
            with gr.Tab("📁 Logs & Export", id=2):
                with gr.Row():
                    export_errors_btn = gr.Button("📥 Export Errors CSV", size="lg")
                    export_improvements_btn = gr.Button("📥 Export Improvements CSV", size="lg")
                export_status = gr.Textbox(label="Export Status", interactive=False)

            # EXIT BUTTON (always visible at bottom)
            with gr.Row():
                exit_btn = gr.Button("🛑 EXIT APPLICATION", variant="stop", size="lg", scale=1)

        # ==================== EVENT HANDLERS ====================
        def init_app():
            init_db()
            env_key = get_grok_api_key()
            if env_key:
                CONFIG.grok_api_key = SecretStr(env_key)
            has_key = bool(CONFIG.grok_api_key.get_secret_value().strip())
            errors, improves, last = get_metrics()
            return (
                gr.update(visible=not has_key),
                "🔑 **API Key:** ✅ Validated (from environment)" if has_key else "🔑 **API Key:** Not validated",
                f"<div class='metric-card'><div class='metric-number'>{errors}</div><div style='font-size:1.4em'>Total Errors Logged</div></div>",
                f"<div class='metric-card'><div class='metric-number'>{improves}</div><div style='font-size:1.4em'>Improvements Generated</div></div>",
                f"<div class='metric-card'><div style='font-size:1.8em;font-weight:700'>{last}</div><div style='font-size:1.4em'>Last Activity</div></div>"
            )

        def validate_key(key):
            if not key.strip():
                return "❌ Please enter a key", gr.update(visible=True), "🔑 **API Key:** Not validated"
            try:
                client = OpenAI(api_key=key.strip(), base_url="https://api.x.ai/v1")
                client.chat.completions.create(model=CONFIG.grok_model, messages=[{"role": "user", "content": "test"}], max_tokens=5)
                CONFIG.grok_api_key = SecretStr(key.strip())
                return "✅ Key validated successfully!", gr.update(visible=False), "🔑 **API Key:** ✅ Validated"
            except Exception as e:
                return f"❌ Validation failed: {str(e)[:80]}", gr.update(visible=True), "🔑 **API Key:** Invalid"

        def update_model(new_model):
            CONFIG.grok_model = new_model
            return f"✅ Model switched to **{new_model}**"

        def analyze(script, github, file, feedback):
            content = script or ""
            if file:
                try:
                    with open(file.name, "r", encoding="utf-8") as f:
                        content = f.read()
                except:
                    content = "Failed to read file."
            explanation, code = self_improve(content, github, feedback)
            return explanation, code, ""

        def save_code(code):
            return save_improved_file(code)

        def do_export(table):
            return export_csv(table)

        def shutdown():
            gr.Info("🛑 Application shutting down... You can now close this tab.")
            return "Shutting down..."

        # Wire everything
        demo.load(init_app, outputs=[api_key_row, api_status, error_card, improve_card, last_card])
        model_dropdown.change(update_model, inputs=model_dropdown, outputs=api_status)
        validate_btn.click(validate_key, inputs=api_key_input, outputs=[key_status, api_key_row, api_status])
        improve_btn.click(analyze, inputs=[script_input, github_input, file_input, feedback_input],
                          outputs=[output_explanation, output_code, save_status])
        save_btn.click(save_code, inputs=output_code, outputs=save_status)
        export_errors_btn.click(do_export, inputs=gr.State("errors"), outputs=export_status)
        export_improvements_btn.click(do_export, inputs=gr.State("improvements"), outputs=export_status)
        exit_btn.click(shutdown)

    return demo

if __name__ == "__main__":
    print("\n🚀 XForge Self-Improvement — Premium Tech Edition")
    print("   • Set XAI_API_KEY in terminal for instant login")
    print("   • Beautiful dark UI with live metrics & model switching")
    print("   • http://127.0.0.1:7860\n")

    app = build_ui()
    app.launch(server_name="127.0.0.1", server_port=7860, share=False)
