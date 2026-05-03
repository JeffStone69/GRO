#!/usr/bin/env python3
# =============================================================================
# multi_tws_connector.py  (Improved v2)
# =============================================================================

import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Auto-install pandas if missing
try:
    import pandas as pd
except ImportError:
    print("pandas not found – installing now...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
    import pandas as pd

try:
    from ib_insync import IB, Stock, util
except ImportError:
    print("❌ ib_insync is not installed.")
    print("   Please run:  pip install ib_insync")
    sys.exit(1)

# ====================== CONFIGURATION ======================
TWS_INSTANCES = {
    "LIVE":  { "host": "127.0.0.1", "port": 7496, "client_id_base": 900 },
    "PAPER": { "host": "127.0.0.1", "port": 7497, "client_id_base": 910 },
}

TEST_TICKERS = ["TSLA", "AAPL", "NVDA"]
DURATION = "1 D"
BAR_SIZE = "1 min"

DB_PATH = Path("xforge_self_improve.db")
# ==========================================================

def connect_to_tws(name: str, host: str, port: int, client_id: int):
    ib = IB()
    try:
        ib.connect(host=host, port=port, clientId=client_id, timeout=15)
        print(f"✅ Connected to {name} TWS (port {port}, Client ID {client_id})")
        return ib
    except Exception as e:
        print(f"❌ Failed to connect to {name} TWS (port {port}): {e}")
        print("   → Make sure the corresponding TWS instance is running and API is enabled on that port.")
        return None

def fetch_and_store_data(ib, ticker: str, source_label: str):
    if not ib:
        return
    try:
        contract = Stock(ticker, 'SMART', 'USD')
        bars = ib.reqHistoricalData(
            contract, endDateTime='', durationStr=DURATION,
            barSizeSetting=BAR_SIZE, whatToShow='TRADES',
            useRTH=True, formatDate=1
        )
        if not bars:
            print(f"   No data returned for {ticker} from {source_label}")
            return

        df = util.df(bars)
        print(f"   Fetched {len(df)} bars for {ticker} from {source_label}")

        if DB_PATH.exists():
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            for _, row in df.iterrows():
                conn.execute('''
                    INSERT OR REPLACE INTO stock_data 
                    (ticker, timestamp, open, high, low, close, volume, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ticker, row['date'].isoformat(),
                    float(row['open']), float(row['high']),
                    float(row['low']), float(row['close']),
                    int(row['volume']), f'IBKR_{source_label}'
                ))
            conn.commit()
            conn.close()
            print(f"   Data for {ticker} saved with source = IBKR_{source_label}")
    except Exception as e:
        print(f"   Error fetching {ticker} from {source_label}: {e}")

def main():
    print("=" * 70)
    print("Multi-TWS Connector v2 – Connecting to multiple TWS instances")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    connections = {}
    for name, config in TWS_INSTANCES.items():
        ib = connect_to_tws(name, config["host"], config["port"], config["client_id_base"])
        if ib:
            connections[name] = ib
        time.sleep(1)

    if not connections:
        print("\n❌ No successful connections.")
        return

    print(f"\n✅ Successfully connected to {len(connections)} TWS instance(s): {list(connections.keys())}")

    print("\nFetching data for tickers:", TEST_TICKERS)
    for ticker in TEST_TICKERS:
        print(f"\n─── {ticker} ───")
        for name, ib in connections.items():
            fetch_and_store_data(ib, ticker, name)
            time.sleep(0.5)

    print("\nDisconnecting all TWS instances...")
    for name, ib in connections.items():
        try:
            ib.disconnect()
            print(f"   Disconnected {name}")
        except:
            pass

    print("\n🎉 Multi-TWS task completed successfully.")
    print("Your main xForgeTrader script can now use data from both LIVE and PAPER sources.")

if __name__ == "__main__":
    main()