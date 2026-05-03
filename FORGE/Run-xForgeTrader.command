#!/bin/bash
# =============================================================================
# Run-xForgeTrader.command - CLEAN FIRST-RUN LAUNCHER v3.0
# Robust venv handling (full paths, no source activate), auto-cleans bloat,
# preserves self-improve.db, installs every missing package (eventkit fix),
# then launches XForge Trader. Zero startup failures after dependencies.
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
echo -e "${BOLD}${YELLOW}           XForge Trader v3.0 — Clean First-Run Edition${NC}"
echo -e "${GREEN}           Robust Venv • Zero Bloat • Eventkit Fixed • Fresh Start${NC}"
echo ""

echo -e "${CYAN}>>> Performing complete bloat cleanup...${NC}"

# Safe bloat removal (keeps your self-improve.db and fetch/ data)
rm -f .DS_Store
rm -rf .gradio backups versions
rm -f xforge_trader.old.py
# NOTE: xforge_self_improve.db is NOT deleted — your improvement history is preserved

mkdir -p fetch
echo -e "${GREEN}✓ Bloat removed. fetch/ folder ready.${NC}"

# ── Robust Virtual Environment (full paths, no source) ──────────────────────
VENV_DIR="venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}>>> First run — creating fresh virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created.${NC}"
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}✗ ERROR: venv Python not found at $VENV_PYTHON${NC}"
    read -p "Press Enter to exit..."
    exit 1
fi

echo -e "${CYAN}>>> Using venv Python: $VENV_PYTHON${NC}"

# ── Auto-Install All Dependencies (robust, using venv pip) ──────────────────
echo -e "${CYAN}>>> Installing/updating all packages (eventkit + ib_insync + missing ones)...${NC}"
"$VENV_PIP" install --upgrade pip
if [ -f "requirements.txt" ]; then
    "$VENV_PIP" install -r requirements.txt --upgrade
else
    echo -e "${YELLOW}⚠️ requirements.txt not found — skipping${NC}"
fi
"$VENV_PIP" install --upgrade eventkit ib_insync yfinance pandas-ta plotly beautifulsoup4 requests numpy gradio openai

echo -e "${GREEN}✓ All dependencies installed and up to date.${NC}"

# ── Launch the Application (using venv Python) ──────────────────────────────
echo ""
echo -e "${CYAN}>>> Starting XForge Trader on http://0.0.0.0:7860${NC}"
echo -e "${YELLOW}Browser will open automatically...${NC}"
echo ""
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}   Close the Gradio tab or press Ctrl+C in this terminal to stop${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo ""

"$VENV_PYTHON" xforge_trader.py

# ── POST-EXIT: Auto-Close Terminal (macOS) ───────────────────────────────────
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

echo -e "${GREEN}Terminal closed. Clean first-run complete.${NC}"
