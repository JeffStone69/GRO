#!/bin/bash
# =============================================================================
# Run-xForgeTrader.command - Enhanced Launcher v2
# Features: Beautiful colored splash screen + automatic Terminal close on exit
# =============================================================================

cd "$(dirname "$0")"

# ── Color Definitions (ANSI for macOS Terminal) ─────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Clear Screen & Display Splash Screen ────────────────────────────────────
clear

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                            ║${NC}"
echo -e "${BLUE}║${NC}   ${CYAN}██╗  ██╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗${NC}                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   ${CYAN}╚██╗██╔╝██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝${NC}                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    ${CYAN}╚███╔╝ █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  ${NC}                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    ${CYAN}██╔██╗ ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  ${NC}                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   ${CYAN}██╔╝ ██╗██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗${NC}                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   ${CYAN}╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝${NC}                    ${BLUE}║${NC}"
echo -e "${BLUE}║                                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"

echo ""
echo -e "${BOLD}${YELLOW}           xForgeTrader v7 — Profit Recommendation Engine${NC}"
echo -e "${GREEN}           Self-Improving • Grok-Powered • Always Demo Ready${NC}"
echo ""

echo -e "${CYAN}Activating Python virtual environment...${NC}"
if source venv/bin/activate 2>/dev/null; then
    echo -e "${GREEN}✓ Virtual environment activated successfully.${NC}"
else
    echo -e "${RED}✗ ERROR: Virtual environment 'venv' not found!${NC}"
    echo -e "${YELLOW}Please run these commands once:${NC}"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo -e "${CYAN}Starting Gradio server on http://0.0.0.0:7860${NC}"
echo -e "${YELLOW}Your browser will open automatically in a few seconds...${NC}"
echo ""
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}   Use the 🚪 Exit button in the Utilities tab to close the app & terminal${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
echo ""

# ── Launch the Application ─────────────────────────────────────────────────
python3 xforge_trader.py

# ── POST-EXIT: Close the Terminal Window ───────────────────────────────────
# This runs automatically when the Python process ends (via UI Exit button)
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

echo -e "${GREEN}Terminal window closed. Goodbye!${NC}"
