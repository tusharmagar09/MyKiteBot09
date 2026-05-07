import pandas as pd
from kiteconnect import KiteConnect
import sys
import os
import config

# Setup Reports Directory
os.makedirs("reports", exist_ok=True)

# Read access token
try:
    with open(config.TOKEN_FILE, "r") as f:
        ACCESS_TOKEN = f.read().strip()
except FileNotFoundError:
    print(f"Error: {config.TOKEN_FILE} not found. Please run login.py first.")
    sys.exit()

kite = KiteConnect(api_key=config.API_KEY)
kite.set_access_token(ACCESS_TOKEN)

import time

# Load Instruments
try:
    instruments_df = pd.read_csv("instruments.csv")
except FileNotFoundError:
    print("Error: instruments.csv not found.")
    sys.exit()

all_trades_log = []
summary_log = []
equity = 100.0 # Starting with 100%
equity_curve = []

print("Starting Backtest...")

for index, row in instruments_df.iterrows():
    symbol = row['symbol']
    instrument_token = int(row['instrument_token'])
    print(f"Testing {symbol}...")
    
    # Kite API allows max 3 historical requests per second. Sleep to prevent being blocked.
    time.sleep(0.4)

    try:
        data = kite.historical_data(
            instrument_token,
            config.START_DATE,
            config.END_DATE,
            config.TIMEFRAME
        )
        df = pd.DataFrame(data)
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        continue

    if df.empty:
        print(f"No data for {symbol}.")
        continue

    # Indicators
    df['EMA_SHORT'] = df['close'].ewm(span=config.EMA_SHORT).mean()
    df['EMA_LONG'] = df['close'].ewm(span=config.EMA_LONG).mean()

    trades = []
    
    for i in range(max(config.EMA_LONG, 1), len(df)):
        if df['EMA_SHORT'][i] > df['EMA_LONG'][i]:
            entry_price = df['close'][i]
            entry_date = df['date'][i]
            sl = entry_price * config.SL_PERCENT
            target = entry_price * config.TARGET_PERCENT

            for j in range(i+1, min(i+10, len(df))):
                exit_price = None
                exit_date = df['date'][j]
                pnl_pct = 0
                
                if df['low'][j] <= sl:
                    exit_price = sl
                    pnl_pct = round((config.SL_PERCENT - 1) * 100, 2)
                elif df['high'][j] >= target:
                    exit_price = target
                    pnl_pct = round((config.TARGET_PERCENT - 1) * 100, 2)
                
                if exit_price is not None:
                    trades.append(pnl_pct)
                    equity *= (1 + (pnl_pct / 100))
                    
                    all_trades_log.append({
                        "Symbol": symbol,
                        "Entry Date": entry_date,
                        "Entry Price": entry_price,
                        "Exit Date": exit_date,
                        "Exit Price": exit_price,
                        "PnL %": pnl_pct
                    })
                    
                    equity_curve.append({
                        "Date": exit_date,
                        "Equity %": round(equity, 2)
                    })
                    break

    # Results per symbol
    total_trades = len(trades)
    if total_trades > 0:
        win_trades = len([t for t in trades if t > 0])
        win_rate = win_trades / total_trades * 100
        avg_return = sum(trades) / total_trades
    else:
        win_rate = 0
        avg_return = 0
        
    summary_log.append({
        "Symbol": symbol,
        "Total Trades": total_trades,
        "Win Rate %": round(win_rate, 2),
        "Avg Return %": round(avg_return, 2)
    })

# Output Reports
print("\nGenerating Reports...")

pd.DataFrame(all_trades_log).to_csv("reports/trades.csv", index=False)
print("Saved reports/trades.csv")

pd.DataFrame(summary_log).to_csv("reports/summary.csv", index=False)
print("Saved reports/summary.csv")

pd.DataFrame(equity_curve).to_csv("reports/equity_curve.csv", index=False)
print("Saved reports/equity_curve.csv")

print("Backtest Complete!")
