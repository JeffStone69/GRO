#!/bin/bash
cd ~/Downloads/a
streamlit run geosupply_analyzer.py --server.port 8501 --server.headless true &
cloudflared tunnel --url http://localhost:8501 run
