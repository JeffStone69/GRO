#!/bin/bash
# =============================================================================
# Run-xForgeTrader.command - CLEAN FIRST-RUN LAUNCHER v2.2
# Auto-cleans all bloat, resets for fresh start, auto-installs everything,
# then launches XForge Trader with beautiful splash + terminal auto-close.
# Run this from the FORGE/ folder (or double-click the .command file).
# =============================================================================

cd "$(dirname "$0")"

# ── Color Definitions (ANSI for macOS Terminal) ─────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── CLEAN FIRST-RUN SETUP (removes all bloat every launch) ──────────────────
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
echo -e "${BOLD}${YELLOW}           XForge Trader v2.2 — Clean First-Run Edition${NC}"
echo -e "${GREEN}           Auto-Cleanup • Self-Healing • Zero Bloat • Fresh Start${NC}"
echo ""

echo -e "${CYAN}>>> Performing complete bloat cleanup for a true first-run slate...${NC}"

# Remove all bloated junk (safe — script will recreate what it needs)
rm -f .DS_Store
rm -rf .gradio backups versions
rm -f xforge_trader.old.py
rm -f xforge_self_improve.db          # Fresh DB for clean first run

# Ensure clean fetch/ folder exists
mkdir -p fetch
echo -e "${GREEN}✓ Bloat removed. fetch/ folder ready for your generated ticker data.${NC}"

# ── Virtual Environment Setup (auto-create on first run) ────────────────────
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}>>> First run detected — creating fresh virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created.${NC}"
fi

echo -e "${CYAN}>>> Activating virtual environment...${NC}"
if source "$VENV_DIR/bin/activate" 2>/dev/null; then
    echo -e "${GREEN}✓ Virtual environment activated.${NC}"
else
    echo -e "${RED}✗ ERROR: Could not activate venv. Please check Python 3 installation.${NC}"
    read -p "Press Enter to exit..."
    exit 1
fi

# ── Auto-Install All Dependencies (including eventkit fix) ──────────────────
echo -e "${CYAN}>>> Installing/updating all required packages (eventkit + ib_insync included)...${NC}"
pip install --upgrade pip
pip install -r requirements.txt --upgrade
pip install eventkit ib_insync yfinance pandas-ta plotly beautifulsoup4 requests numpy gradio openai --upgrade

echo -e "${GREEN}✓ All dependencies installed and up to date.${NC}"

# ── Launch the Clean Application ────────────────────────────────────────────
echo ""
echo -e "${CYAN}>>> Starting Gradio server on http://0.0.0.0:7860${NC}"
echo -e "${YELLOW}Your browser will open automatically in a few seconds...${NC}"
echo ""
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}   Use the 🚪 Exit button in the Utilities tab to close the app & terminal${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo ""

python3 xforge_trader.py

# ── POST-EXIT: Auto-Close Terminal (macOS) ───────────────────────────────────
echo ""
echo -e "${YELLOW}xForgeTrader has shut down. Closing terminal window...${NC}"
sleep 1

osascript -e '
tell application "Terminal"
    set targetWindows to every window whose name contains "xForgeTrader" or name contains "Run-xForgeTrader"
    repeat with w in targetWindows
        close w
    end repeat
end tell
' 2>/dev/null || osascript -e 'tell application "Terminal" to close window 1' 2>/dev/null || true

echo -e "${GREEN}Terminal window closed. Clean first-run complete. Goodbye!${NC}"
