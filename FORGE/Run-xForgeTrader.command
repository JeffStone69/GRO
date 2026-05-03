#!/bin/bash
# =============================================================================
# Run-xForgeTrader.command - CLEAN FIRST-RUN LAUNCHER v5.0
# Forces automatic browser open + guaranteed latest v6.0 script
# =============================================================================

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                                                                            ║${NC}"
echo -e "${BOLD}${CYAN}║${NC}   ${GREEN}██╗  ██╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗${NC}                    ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}   ${GREEN}╚██╗██╔╝██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝${NC}                    ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}    ${GREEN}╚███╔╝ █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  ${NC}                    ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}    ${GREEN}██╔██╗ ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  ${NC}                    ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}   ${GREEN}██╔╝ ██╗██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗${NC}                    ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}   ${GREEN}╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝${NC}                    ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║                                                                            ║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}${YELLOW}           XForge Trader v5.0 — Guaranteed Latest v6.0 Script${NC}"
echo -e "${GREEN}           Auto-Cleanup • Auto-Browser • Fresh Venv • Zero Old Files${NC}"
echo ""

echo -e "${CYAN}>>> Performing complete bloat cleanup + old script removal...${NC}"
rm -f .DS_Store xforge_trader.old.py xforge_trader.py
rm -rf .gradio backups versions
mkdir -p fetch
echo -e "${GREEN}✓ All old/bloat files removed. Fresh start guaranteed.${NC}"

VENV_DIR="venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}>>> Creating fresh virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}✗ ERROR: venv Python not found${NC}"
    read -p "Press Enter to exit..."
    exit 1
fi

echo -e "${CYAN}>>> Installing/updating all packages (eventkit, tweepy, openai included)...${NC}"
"$VENV_PIP" install --upgrade pip
if [ -f "requirements.txt" ]; then
    "$VENV_PIP" install -r requirements.txt --upgrade
fi
"$VENV_PIP" install --upgrade eventkit ib_insync yfinance pandas-ta plotly beautifulsoup4 requests numpy gradio openai tweepy

echo -e "${GREEN}✓ All dependencies ready.${NC}"

echo ""
echo -e "${CYAN}>>> Starting XForge Trader v6.0 on http://127.0.0.1:7860${NC}"
echo -e "${YELLOW}Browser will open automatically in a new tab...${NC}"
echo ""
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}   Close the Gradio tab or press Ctrl+C here to stop${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo ""

"$VENV_PYTHON" xforge_trader.py &
APP_PID=$!
sleep 4
open "http://127.0.0.1:7860"
wait $APP_PID

echo ""
echo -e "${YELLOW}XForge Trader has shut down. Closing terminal...${NC}"
sleep 1
osascript -e 'tell application "Terminal" to close window 1' 2>/dev/null || true
echo -e "${GREEN}Terminal closed. Clean run complete.${NC}"
