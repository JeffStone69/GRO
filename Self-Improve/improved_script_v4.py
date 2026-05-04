'" output format required by the self-improvement prompt.

These changes make the module production-ready, fix the blocking errors users were seeing, and eliminate the incompleteness while keeping the original secure + beautiful design intact.

---IMPROVED-CODE---
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
        return "Error: Grok API key required. Set XAI_API_KEY env var or enter it in the UI.", ""

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
            max_tokens=3000
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
        error_str = str(e)
        log_error("Self-Improve", error_str)
        if "403" in error_str or "blocked" in error_str.lower() or "permission" in error_str.lower():
            return "Error: API key is currently blocked or lacks permissions. Please check your xAI account at https://x.ai, generate a fresh key, and ensure it has the correct permissions. Never share your key publicly.", ""
        return f"Analysis failed: {error_str}", ""

def save_improved_file(improved_code: str) -> str:
    if not improved_code:
        return "No code to save."
    counter = 1
    while Path(f"