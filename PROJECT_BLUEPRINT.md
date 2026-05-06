**Project Blueprint: XForge Trader + SIM System (Rewritten Version)**

**Version:** 1.0  
**Date:** May 2026  
**Author:** Grok (xAI) – Expert Python Architect & Technical Writer  
**Status:** Complete specification for clean, production-grade rewrite  

---

### 1. Project Vision

XForge Trader + SIM is a modular, self-improving algorithmic trading workstation built for macOS. It combines real-time market intelligence, strategy optimization, simulated/paper trading, multi-ticker monitoring, and autonomous code evolution powered by the Grok API (xAI).

The system delivers:
- A unified Gradio-based interface with dynamic tabs for trading operations.
- Persistent SQLite databases for historical data, watchlist signals, paper trades, and improvement logs.
- Automated nightly portfolio rebalancing via GitHub Actions.
- Secure, LLM-driven self-improvement of all Python modules (SIM).
- Native macOS launchers with splash screens for professional user experience.

The rewritten version shall eliminate current fragmentation (minimal core files, abbreviated module logic, mixed launchers), enforce strict modularity, robust error handling, comprehensive type safety, full test coverage, and enterprise-grade security while preserving the original evolutionary intelligence ethos.

---

### 2. Target Directory Structure (Clean Rewrite)

```
XForge-Trader/
├── .github/
│   └── workflows/
│       └── nightly_rebalance.yml          # CI/CD for automated rebalancing + PR creation
├── FORGE/                                 # Core trading engine (refactored)
│   ├── __init__.py
│   ├── xforge_trader.py                   # Main Gradio app orchestrator
│   ├── requirements.txt                   # Project-wide dependencies
│   ├── config.py                          # Pydantic settings & environment validation
│   └── utils.py                           # Shared helpers (DB, logging, API)
├── modules/                               # Self-contained, importable Gradio tabs
│   ├── __init__.py
│   ├── multi_ticker_watchlist.py
│   ├── simulated_trading_history.py
│   ├── strategy_optimizer.py
│   └── __pycache__ (excluded)
├── Self-Improve/                          # Autonomous code evolution engine
│   ├── __init__.py
│   ├── README.md                          # Full documentation
│   ├── SIM.py                             # Gradio self-improvement interface
│   └── sim_config.py                      # Isolated configuration
├── launcher.py                            # Primary macOS splash + orchestrator
├── launch.command                         # Double-click entry point (macOS)
├── run_xforge.command                     # Secondary launcher (preserved)
├── .env.example
├── .gitignore
├── .gitattributes
├── pyproject.toml                         # Modern Python packaging (replaces legacy reqs)
├── README.md                              # Project overview & quick-start
└── docs/                                  # Architecture diagrams & API references (new)
```

All `.db` files shall be generated at runtime and excluded from version control.

---

### 3. Core Components & Functional Requirements

**3.1 Launcher Layer**
- `launcher.py`: Modern Tkinter splash screen (640×420 px, dark cyber theme, SMI-LOGO.jpeg support). Displays animated status messages before launching the main Gradio app. No blocking operations.

**3.2 Trading Core (`FORGE/xforge_trader.py`)**
- Central Gradio Blocks application.
- Dynamically registers tabs from `modules/`.
- Handles global state, database connections, and cross-tab communication (e.g., watchlist signals → optimizer).

**3.3 Modules (Gradio Tabs)**
- `multi_ticker_watchlist.py`: Real-time multi-ticker monitoring (yfinance), signal generation (BUY/SELL/HOLD), automatic logging to watchlist_signals table. Links directly to optimizer.
- `strategy_optimizer.py`: Backtesting engine, strategy comparison, paper-trading simulation. Consumes watchlist signals for rebalancing recommendations. Full `SimpleBacktester` and `PaperTrader` classes required (no placeholders).
- `simulated_trading_history.py`: Persistent trade ledger, equity curve visualization (Plotly), performance analytics (P&L, win rate, drawdown).

**3.4 Self-Improvement Engine (`Self-Improve/SIM.py`)**
- Standalone Gradio application using Grok API (via `openai` client with `https://api.x.ai/v1` base).
- Features: secure memory-only API key handling, file/GitHub URL ingestion, recent error context, structured LLM prompts (explanation + improved code delimited by `---IMPROVED-CODE---`), versioned output files, CSV export of logs, live metrics dashboard, premium dark cyber UI.
- Database: `xforge_self_improve.db` for errors and improvements.
- Model selector: grok-4.3 and latest xAI variants.

**3.5 Automation**
- `.github/workflows/nightly_rebalance.yml`: Scheduled (midnight UTC) + manual trigger. Installs minimal deps, loads signals, runs optimizer logic, commits summary markdown, and creates PR. Uses `XAI_API_KEY` secret.

---

### 4. Architecture & Data Flow

1. **Entry** → `launch.command` / `launcher.py` → splash → `xforge_trader.py`.
2. **Market Data** → yfinance → `multi_ticker_watchlist` → signals → SQLite (`xforge_historical.db`).
3. **Signals** → `strategy_optimizer` → backtest/paper trades → history table → equity analytics.
4. **Nightly** → GitHub Action → rebalance logic → summary + PR.
5. **Self-Improvement Loop** → `SIM.py` (independent) → analyzes any module → generates improved version → developer review → merge.

All components share a unified configuration and logging layer. Databases are initialized on first run with proper schema migration support.

---

### 5. Strengths to Preserve

- Modular Gradio tab architecture for extensibility.
- Grok-powered autonomous code refinement (SIM).
- Persistent SQLite for auditability and analytics.
- macOS-first launch experience.
- CI-driven nightly automation.

---

### 6. Gaps to Address in Rewrite

- Current `FORGE/xforge_trader.py` is minimal; restore full orchestration logic.
- `strategy_optimizer.py` contains placeholder classes; implement complete `SimpleBacktester` and `PaperTrader`.
- Fragmented launchers and duplicate files; consolidate under single modern structure.
- Missing comprehensive error handling, logging, and type hints.
- No unit/integration tests or CI linting.
- Database files committed to repo; enforce `.gitignore` and runtime generation.

---

### 7. Security Considerations

- API keys: Environment variables preferred (`XAI_API_KEY`); UI input is memory-only. Never persist to disk except in `.env.example`.
- No secrets in Git history.
- Input sanitization for GitHub URLs and uploaded files in SIM.
- SQLite connections use context managers; proper error logging without exposing sensitive data.
- Dependency scanning and pinned versions via `pyproject.toml`.

---

### 8. Dependencies & Tech Stack (Rewritten)

**Core (pyproject.toml):**
- Python ≥ 3.11
- gradio, yfinance, pandas, numpy, pandas-ta, plotly, openai, sqlite3, pydantic, requests, tenacity
- (Optional: ib_insync, eventkit, tweepy for future broker integration)

**Development:**
- ruff, mypy, pytest, black

All legacy `requirements.txt` entries shall be migrated and audited.

---

### 9. Non-Functional Requirements for Rewrite

- Full type hints and docstrings.
- Comprehensive test suite (unit + integration for each module).
- 100% lint compliance (ruff).
- Responsive, accessible Gradio UI with consistent dark cyber theme.
- Zero breaking changes to user-facing behavior.
- Backward-compatible database schema.
- Detailed README with installation, usage, and contribution guide.

This blueprint provides the exact specification required to produce a clean, maintainable, and production-ready successor to the current GRO repository. Implementation may begin immediately.