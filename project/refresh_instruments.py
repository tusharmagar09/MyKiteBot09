"""
refresh_instruments.py — Regenerate instruments.csv with fresh tokens from Kite API.
Run this whenever you get "0 instruments loaded" errors.
"""
import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from modules.auto_login import auto_login


def refresh():
    print("Logging in to Kite...")
    kite = auto_login()

    print("Fetching all NSE instruments from Kite...")
    all_instruments = kite.instruments("NSE")
    inst_df = pd.DataFrame(all_instruments)

    print(f"Total NSE instruments: {len(inst_df)}")
    print(f"Columns: {list(inst_df.columns)}")
    print(f"\nSample:\n{inst_df.head()}")

    # Load existing instruments list (symbols only)
    old_file = config.INSTRUMENTS_FILE
    if os.path.exists(old_file):
        old_df = pd.read_csv(old_file)
        target_symbols = old_df['symbol'].tolist()
        print(f"\nExisting instruments file has {len(target_symbols)} symbols.")
    else:
        print(f"\nNo existing instruments file at {old_file}")
        print("Filtering for EQ (equity) segment only...")
        # Filter for equities only
        eq_df = inst_df[inst_df['segment'] == 'NSE']
        eq_df = eq_df[eq_df['instrument_type'] == 'EQ']
        target_symbols = eq_df['tradingsymbol'].tolist()
        print(f"Found {len(target_symbols)} equity symbols.")

    # Match symbols with fresh tokens
    eq_instruments = inst_df[inst_df['instrument_type'] == 'EQ']
    matched = eq_instruments[eq_instruments['tradingsymbol'].isin(target_symbols)]

    result = matched[['tradingsymbol', 'instrument_token', 'exchange_token', 'name']].copy()
    result.columns = ['symbol', 'instrument_token', 'exchange_token', 'name']
    result = result.sort_values('symbol').reset_index(drop=True)

    print(f"\nMatched {len(result)} out of {len(target_symbols)} symbols.")

    # Check for Nifty 500 index token
    nifty500 = inst_df[inst_df['tradingsymbol'].str.contains('NIFTY 500', case=False, na=False)]
    nifty50 = inst_df[inst_df['tradingsymbol'].str.contains('NIFTY 50', case=False, na=False)]
    print(f"\nNIFTY 50 index entries: {len(nifty50)}")
    if not nifty50.empty:
        for _, row in nifty50.head(5).iterrows():
            print(f"  {row['tradingsymbol']}: token={row['instrument_token']}, type={row['instrument_type']}")
    print(f"\nNIFTY 500 index entries: {len(nifty500)}")
    if not nifty500.empty:
        for _, row in nifty500.head(5).iterrows():
            print(f"  {row['tradingsymbol']}: token={row['instrument_token']}, type={row['instrument_type']}")

    # Save
    result.to_csv(old_file, index=False)
    print(f"\n✅ Saved {len(result)} instruments to {old_file}")

    # Quick test: fetch data for first 3 stocks
    print("\nTesting data fetch for first 3 stocks...")
    for _, row in result.head(3).iterrows():
        symbol = row['symbol']
        token = int(row['instrument_token'])
        try:
            from datetime import datetime, timedelta
            end = datetime.now().date()
            start = end - timedelta(days=350)
            data = kite.historical_data(token, start, end, "day")
            print(f"  {symbol} (token={token}): {len(data)} bars ✅")
        except Exception as e:
            print(f"  {symbol} (token={token}): FAILED — {e}")


if __name__ == "__main__":
    refresh()
