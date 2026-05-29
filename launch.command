#!/bin/bash
cd "$(dirname "$0")"
python3 -m streamlit run elite_dashboard.py --server.port 8501
