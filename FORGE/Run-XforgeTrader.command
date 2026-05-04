#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
rm -f xforge_self_improve.db xforge_trader.log
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade 2>/dev/null || true
pip install gradio yfinance pandas-ta plotly openai tweepy tenacity pydantic numpy requests beautifulsoup4 --upgrade
python3 xforge_trader.py
exec "$SHELL"