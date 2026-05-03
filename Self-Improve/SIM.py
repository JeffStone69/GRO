#!/usr/bin/env python3
"""
XForge Self-Improvement Module - Secure Production Version
- API key NEVER saved to disk or repo (env var injection or memory-only UI)
- Full GitHub support, file creation, export, logging, and iteration.
- Security hardened: no persistent secrets.
"""

import subprocess
import sys
import importlib
import os
from pathlib import Path

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
import json
import requests
from datetime import datetime
from openai import OpenAI
from pydantic import BaseModel, Field, SecretStr
import gradio as gr

class SelfImproveConfig(BaseModel):
    db_name: str = "xforge_self_improve.db"
    grok_model: str = "grok-4.3"  # Update if xAI changes model names
    max_errors: int = 20

CONFIG = SelfImproveConfig()

# ==================== SECURE API KEY HANDLING (NO FILE SAVING) ====================
def get_grok_api_key() -> str:
    """Get API key from environment variable (preferred injection method).
    Falls back to None if not set (UI will handle it).
    """
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

def fetch_github_content(url: str) -> str:
    try:
        if "github.com" in url and not url.startswith("https://raw.githubusercontent.com"):
            if "/blob/" in url:
                url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            else:
                candidates = [
                    url.replace("github.com", "raw.githubusercontent.com") + "/main/README.md",
                    url.replace("github.com", "raw.githubusercontent.com") + "/main/main.py",
                    url.replace("github.com", "raw.githubusercontent.com") + "/main/app.py"
                ]
                for candidate in candidates:
                    r = requests.get(candidate, timeout=10)
                    if r.status_code == 200:
                        return r.text
                return "Could not fetch default files."
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.text
        return f"HTTP Error {r.status_code}"
    except Exception as e:
        return f"Fetch failed: {str(e)}"

def self_improve(script_content: str = "", github_url: str = "", user_feedback: str = "") -> tuple[str, str]:
    api_key = CONFIG.grok_api_key.get_secret_value() if CONFIG.grok_api_key else get_grok_api_key()
    if not api_key:
        return "Error: Grok API key required. Set XAI_API_KEY environment variable or enter it in the UI.", ""
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        errors_df = pd.read_sql_query(f"SELECT * FROM errors ORDER BY timestamp DESC LIMIT {CONFIG.max_errors}", conn)
        conn.close()
        
        context = ""
        if not errors_df.empty:
            context += "Recent Errors:\n" + errors_df.to_string(index=False) + "\n\n"
        if github_url.strip():
            github_content = fetch_github_content(github_url.strip())
            context += f"GitHub Content:\n{github_content[:12000]}\n\n"
        if script_content.strip():
            context += "Provided Script:\n" + script_content[:12000] + "\n\n"
        if user_feedback.strip():
            context += f"User Iteration Instructions:\n{user_feedback}\n\n"
        
        if not context:
            return "No content provided to analyze.", ""
        
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        prompt = (
            "You are an expert Python engineer. Analyze the provided code, errors, and user instructions. "
            "Return TWO parts clearly separated by '---IMPROVED-CODE---':\n"
            "1. Detailed explanation of improvements.\n"
            "2. The complete, ready-to-run improved Python script.\n\n"
            f"{context}"
        )
        response = client.chat.completions.create(model=CONFIG.grok_model, messages=[{"role": "user", "content": prompt}], max_tokens=2000)
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

def save_improved_file(improved_code: str, base_name: str = "improved_script") -> str:
    if not improved_code:
        return "No improved code to save."
    try:
        counter = 1
        while True:
            filename = f"{base_name}_v{counter}.py"
            if not Path(filename).exists():
                break
            counter += 1
        with open(filename, "w", encoding="utf-8") as f:
            f.write(improved_code)
        return f"Saved as {filename}"
    except Exception as e:
        return f"Save failed: {str(e)}"

def export_errors_csv() -> str:
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        df = pd.read_sql_query("SELECT * FROM errors ORDER BY timestamp DESC", conn)
        conn.close()
        filename = f"errors_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        return f"Errors exported to {filename}"
    except Exception as e:
        return f"Export failed: {str(e)}"

def export_improvements_csv() -> str:
    try:
        conn = sqlite3.connect(CONFIG.db_name)
        df = pd.read_sql_query("SELECT * FROM improvements ORDER BY timestamp DESC", conn)
        conn.close()
        filename = f"improvements_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        return f"Improvements exported to {filename}"
    except Exception as e:
        return f"Export failed: {str(e)}"

def build_ui():
    splash_html = """
    <div style="text-align:center;padding:80px;background:linear-gradient(135deg,#0f172a,#1e2937);color:white;height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;">
        <div style="font-size:3.2em;font-weight:700;margin-bottom:8px;">XFORGE</div>
        <h2 style="color:#22c55e;">Self-Improvement Module</h2>
        <div style="border:8px solid #334155;border-top:8px solid #22c55e;border-radius:50%;width:72px;height:72px;animation:spin 1.2s linear infinite;margin:30px auto;"></div>
        <style>@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style>
    </div>
    """
    with gr.Blocks(title="XForge Self-Improvement (Secure)") as demo:
        splash = gr.HTML(value=splash_html, visible=True)
        
        with gr.Row(visible=False) as api_key_section:
            with gr.Column():
                gr.Markdown("### 🔒 Grok API Key (Memory-Only - Never Saved to Disk or Repo)")
                gr.Markdown("**Recommended:** Set `XAI_API_KEY` environment variable before running for automatic injection.")
                api_key_input = gr.Textbox(label="xAI Grok API Key", type="password", placeholder="xai-...")
                save_btn = gr.Button("Validate & Continue", variant="primary")
                status = gr.Textbox(label="Status", interactive=False)
        
        with gr.Row(visible=False) as main_section:
            gr.Markdown("# XForge Self-Improvement Analysis")
            with gr.Tabs():
                with gr.Tab("Analyze & Iterate"):
                    script_input = gr.Textbox(label="Paste Script / Code / Log", lines=8)
                    github_input = gr.Textbox(label="GitHub Raw or Repo URL", placeholder="https://raw.githubusercontent.com/... or https://github.com/user/repo")
                    file_input = gr.File(label="Upload file", file_types=[".py", ".log", ".txt"])
                    feedback_input = gr.Textbox(label="Iteration Instructions / Feedback (optional)", lines=3, placeholder="e.g. Make it faster, add error handling...")
                    improve_btn = gr.Button("Run / Iterate Analysis", variant="primary", size="large")
                    output_explanation = gr.Textbox(label="Analysis & Recommendations", lines=12, interactive=False)
                    output_code = gr.Textbox(label="Improved Code (ready to save)", lines=12, interactive=False)
                    save_file_btn = gr.Button("Save as New .py File", variant="secondary")
                    save_status = gr.Textbox(label="File Status", interactive=False)
                
                with gr.Tab("Export & Logs"):
                    export_errors_btn = gr.Button("Export Errors to CSV")
                    export_improvements_btn = gr.Button("Export Improvements to CSV")
                    export_status = gr.Textbox(label="Export Status", interactive=False)
        
        def init_app():
            init_db()
            env_key = get_grok_api_key()
            if env_key:
                CONFIG.grok_api_key = SecretStr(env_key)
            has_key = bool(CONFIG.grok_api_key.get_secret_value().strip() if CONFIG.grok_api_key else False)
            return gr.update(visible=False), gr.update(visible=not has_key), gr.update(visible=has_key)
        
        demo.load(init_app, outputs=[splash, api_key_section, main_section])
        
        def save_handler(key):
            success, msg = validate_grok_key(key)
            if success:
                CONFIG.grok_api_key = SecretStr(key.strip())
                # NOTE: Key is stored ONLY in memory for this session. Never saved to file or repo.
                return msg, gr.update(visible=False), gr.update(visible=True)
            return msg, gr.update(visible=True), gr.update(visible=False)
        
        def analyze(script_text, github_url, uploaded_file, feedback):
            content = script_text or ""
            if uploaded_file is not None:
                try:
                    with open(uploaded_file.name, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    content = "Failed to read file."
            explanation, improved_code = self_improve(content, github_url, feedback)
            return explanation, improved_code, ""
        
        def save_file(improved_code):
            return save_improved_file(improved_code)
        
        def export_errors():
            return export_errors_csv()
        
        def export_improvements():
            return export_improvements_csv()
        
        save_btn.click(save_handler, inputs=api_key_input, outputs=[status, api_key_section, main_section])
        improve_btn.click(analyze, inputs=[script_input, github_input, file_input, feedback_input], outputs=[output_explanation, output_code, save_status])
        save_file_btn.click(save_file, inputs=output_code, outputs=save_status)
        export_errors_btn.click(export_errors, outputs=export_status)
        export_improvements_btn.click(export_improvements, outputs=export_status)
    
    return demo

def validate_grok_key(api_key: str):
    key = api_key.strip() if api_key else ""
    if not key:
        return False, "Please enter a key."
    try:
        client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
        client.chat.completions.create(model=CONFIG.grok_model, messages=[{"role": "user", "content": "Test"}], max_tokens=10)
        return True, "Key validated successfully!"
    except Exception as e:
        return False, f"Validation failed: {str(e)[:100]}"

if __name__ == "__main__":
    print("\nStarting XForge Self-Improvement (Secure Mode)...")
    print("API Key Injection: Set XAI_API_KEY environment variable for best security (no UI prompt).")
    app = build_ui()
    app.launch(server_name="127.0.0.1", server_port=7860, share=False, theme=gr.themes.Base())
