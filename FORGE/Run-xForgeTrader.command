#!/bin/bash
# =============================================================================
# Run-xForgeTrader.command - CLEAN FIRST-RUN LAUNCHER v4.0
# Forces automatic browser open (new Chrome tab) + all previous fixes
# =============================================================================

cd "$(dirname "$0")"

# ── Color Definitions ───────────────────────────────────────────────────────
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
echo -e "${BOLD}${YELLOW}           XForge Trader v4.0 — Auto-Browser Edition${NC}"
echo -e "${GREEN}           Auto-Cleanup • Eventkit Fixed • Browser Opens Automatically${NC}"
echo ""

echo -e "${CYAN}>>> Performing complete bloat cleanup...${NC}"
rm -f .DS_Store
rm -rf .gradio backups versions
rm -f xforge_trader.old.py
mkdir -p fetch
echo -e "${GREEN}✓ Bloat removed. fetch/ folder ready.${NC}"

# ── Robust Virtual Environment ──────────────────────────────────────────────
VENV_DIR="venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}>>> First run — creating fresh virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created.${NC}"
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}✗ ERROR: venv Python not found${NC}"
    read -p "Press Enter to exit..."
    exit 1
fi

echo -e "${CYAN}>>> Using venv Python: $VENV_PYTHON${NC}"

# ── Auto-Install All Dependencies ───────────────────────────────────────────
echo -e "${CYAN}>>> Installing/updating all packages...${NC}"
"$VENV_PIP" install --upgrade pip
if [ -f "requirements.txt" ]; then
    "$VENV_PIP" install -r requirements.txt --upgrade
fi
"$VENV_PIP" install --upgrade eventkit ib_insync yfinance pandas-ta plotly beautifulsoup4 requests numpy gradio openai
echo -e "${GREEN}✓ All dependencies ready.${NC}"

# ── Launch with Automatic Browser Open (new Chrome tab) ─────────────────────
echo ""
echo -e "${CYAN}>>> Starting XForge Trader on http://127.0.0.1:7860${NC}"
echo -e "${YELLOW}Browser will open automatically in a new tab...${NC}"
echo ""
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}   Close the Gradio tab or press Ctrl+C here to stop${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo ""

# Run Python in background so we can open browser immediately
"$VENV_PYTHON" xforge_trader.py &
APP_PID=$!

# Give Gradio a moment to start the server
sleep 4

# Force open in default browser (Chrome will receive new tab if already running)
open "http://127.0.0.1:7860"

# Keep terminal alive until Gradio is stopped
wait $APP_PID

# ── POST-EXIT: Auto-Close Terminal ──────────────────────────────────────────
echo ""
echo -e "${YELLOW}xForge Trader has shut down. Closing terminal...${NC}"
sleep 1

osascript -e '
tell application "Terminal"
    set targetWindows to every window whose name contains "xForgeTrader" or name contains "Run-xForgeTrader"
    repeat with w in targetWindows
        close w
    end repeat
end tell
' 2>/dev/null || osascript -e 'tell application "Terminal" to close window 1' 2>/dev/null || true

echo -e "${GREEN}Terminal closed. Clean run complete.${NC}"
