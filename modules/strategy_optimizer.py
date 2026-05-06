# Strategy Optimizer & Paper Trader Module for XForge Trader v8.4
# Dynamic tab: Finds most profitable strategy via backtest optimization and enables paper trading simulation

import gradio as gr
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import itertools
from typing import Dict, List, Tuple

TAB_NAME = "📈 Strategy Optimizer & Paper Trader"

# Simple reusable Backtester class (self-contained for module)
class SimpleBacktester:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df['signal'] = 0
        self.trades = []

    def run_ma_crossover(self, short_window: int, long_window: int) -> Dict:
        self.df['short_ma'] = self.df['close'].rolling(window=short_window).mean()
        self.df['long_ma'] = self.df['close'].rolling(window=long_window).mean()
        self.df['signal'] = np.where(self.df['short_ma'] > self.df['long_ma'], 1, 0)
        self.df['position'] = self.df['signal'].diff()
        return self._calculate_metrics()

    def run_rsi(self, window: int, oversold: int = 30, overbought: int = 70) -> Dict:
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))
        self.df['signal'] = np.where(self.df['rsi'] < oversold, 1, np.where(self.df['rsi'] > overbought, -1, 0))
        self.df['position'] = self.df['signal'].diff()
        return self._calculate_metrics()

    def _calculate_metrics(self) -> Dict:
        # Simplified metrics for demo
        initial = 10000
        self.df['returns'] = self.df['close'].pct_change()
        self.df['strategy_returns'] = self.df['returns'] * self.df['signal'].shift(1)
        total_return = (1 + self.df['strategy_returns']).cumprod().iloc[-1] * initial - initial
        sharpe = self.df['strategy_returns'].mean() / self.df['strategy_returns'].std() * np.sqrt(252) if self.df['strategy_returns'].std() != 0 else 0
        return {
            'total_return_pct': round((total_return / initial) * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(self._max_drawdown(), 2),
            'num_trades': len(self.trades) if hasattr(self, 'trades') else 0
        }

    def _max_drawdown(self) -> float:
        cum_returns = (1 + self.df['strategy_returns']).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak
        return drawdown.min() * 100

# Paper Trading Simulator
class PaperTrader:
    def __init__(self, ticker: str = 'TSLA'):
        self.ticker = ticker
        self.position = 0
        self.cash = 10000
        self.trade_log = []
        self.equity_curve = []

    def simulate_tick(self) -> Dict:
        # Simulate next price using latest data
        data = yf.download(self.ticker, period='5d', interval='1d')
        current_price = data['Close'].iloc[-1]
        # Simple strategy signal from top strategy (placeholder)
        signal = 1 if np.random.rand() > 0.5 else -1  # Replace with real strategy logic
        if signal == 1 and self.position == 0:
            self.position = self.cash / current_price
            self.cash = 0
            self.trade_log.append(('BUY', current_price, datetime.now()))
        elif signal == -1 and self.position > 0:
            self.cash = self.position * current_price
            self.position = 0
            self.trade_log.append(('SELL', current_price, datetime.now()))
        equity = self.cash + (self.position * current_price if self.position > 0 else 0)
        self.equity_curve.append((datetime.now(), equity))
        return {
            'equity': round(equity, 2),
            'position': round(self.position, 4),
            'cash': round(self.cash, 2),
            'last_price': round(current_price, 2)
        }

def optimize_strategies(ticker: str, period: str, selected_strategies: List[str]) -> Tuple[pd.DataFrame, str]:
    data = yf.download(ticker, period=period)
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    data = data.dropna()

    results = []
    strategy_configs = {
        'MA Crossover': [(5, 20), (10, 50), (20, 100)],
        'RSI': [(14, 30, 70), (10, 25, 75), (21, 35, 65)]
    }

    for strat_name in selected_strategies:
        if strat_name not in strategy_configs:
            continue
        for params in strategy_configs.get(strat_name, []):
            bt = SimpleBacktester(data)
            if strat_name == 'MA Crossover':
                metrics = bt.run_ma_crossover(*params)
            elif strat_name == 'RSI':
                metrics = bt.run_rsi(params[0], params[1], params[2])
            else:
                metrics = {'total_return_pct': 0, 'sharpe_ratio': 0, 'max_drawdown': 0, 'num_trades': 0}
            results.append({
                'Strategy': f'{strat_name} {params}',
                'Return %': metrics['total_return_pct'],
                'Sharpe': metrics['sharpe_ratio'],
                'Drawdown %': metrics['max_drawdown'],
                'Trades': metrics['num_trades']
            })

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by='Return %', ascending=False)
        top = df_results.iloc[0]
        top_strat = f"{top['Strategy']} (Return: {top['Return %']}%, Sharpe: {top['Sharpe']})"
    else:
        top_strat = 'No results'

    return df_results, top_strat

def build_tab():
    paper_trader = PaperTrader()

    def run_optimization(ticker, period, strategies):
        df, top = optimize_strategies(ticker, period, strategies)
        return df, top

    def start_paper_trading(ticker):
        # Reset for demo
        global paper_trader
        paper_trader = PaperTrader(ticker)
        return 'Paper trading activated. Click Simulate Tick to advance.'

    def simulate_next_tick():
        stats = paper_trader.simulate_tick()
        log_text = '\n'.join([f'{t[0]} @ {t[1]:.2f} on {t[2]}' for t in paper_trader.trade_log[-5:]])
        equity_text = f"Equity: ${stats['equity']:,} | Cash: ${stats['cash']:,} | Position: {stats['position']}"
        return stats['last_price'], equity_text, log_text

    with gr.Blocks() as strategy_tab:
        gr.Markdown("## 🚀 Strategy Optimizer & Paper Trader\nFind the most profitable strategy via backtesting and activate paper trading simulation.")
        with gr.Row():
            ticker_input = gr.Textbox(value="TSLA", label="Ticker Symbol")
            period_input = gr.Dropdown(choices=["1y", "2y", "5y", "max"], value="2y", label="Backtest Period")
            strat_input = gr.CheckboxGroup(choices=["MA Crossover", "RSI"], value=["MA Crossover"], label="Strategies to Optimize")
        optimize_btn = gr.Button("🔍 Optimize & Rank Strategies", variant="primary")
        with gr.Row():
            results_df = gr.DataFrame(label="Ranked Strategies", value=pd.DataFrame())
            top_strategy_display = gr.Textbox(label="Most Profitable Strategy", interactive=False)
        activate_btn = gr.Button("✅ Activate Paper Trading with Top Strategy", variant="primary")
        with gr.Row():
            price_display = gr.Number(label="Latest Simulated Price")
            equity_display = gr.Textbox(label="Portfolio Equity")
        trade_log_display = gr.Textbox(label="Recent Trades", lines=8, interactive=False)
        simulate_btn = gr.Button("📌 Simulate Next Market Tick (Paper Trade)")

        # Event handlers
        optimize_btn.click(
            run_optimization,
            inputs=[ticker_input, period_input, strat_input],
            outputs=[results_df, top_strategy_display]
        )
        activate_btn.click(
            start_paper_trading,
            inputs=[ticker_input],
            outputs=[gr.Markdown(visible=False)]  # Placeholder for status
        )
        simulate_btn.click(
            simulate_next_tick,
            inputs=[],
            outputs=[price_display, equity_display, trade_log_display]
        )

        gr.Markdown("**Note**: Paper trading uses simulated signals. Connect to SIM for AI-generated strategies. All data from yfinance.")

    return strategy_tab
