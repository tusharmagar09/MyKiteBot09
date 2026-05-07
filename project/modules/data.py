import os
import time
import pandas as pd
from kiteconnect import KiteConnect
import sys

# Add parent dir to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def get_kite_client():
    try:
        with open(config.TOKEN_FILE, "r") as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        print(f"Error: {config.TOKEN_FILE} not found. Run login.py first.")
        sys.exit()

    kite = KiteConnect(api_key=config.API_KEY)
    kite.set_access_token(access_token)
    return kite

def fetch_data(kite, symbol, token, start, end, interval):
    safe_symbol = str(symbol).replace(":", "_").replace("/", "_")
    filepath = os.path.join(config.DATA_DIR, f"{safe_symbol}_{interval}.csv")
    
    # Return from cache if it exists and is not empty
    if os.path.exists(filepath):
        if os.path.getsize(filepath) > 0:
            try:
                df = pd.read_csv(filepath, parse_dates=['date'])
                if not df.empty:
                    return df
            except Exception:
                pass
        # If we reach here, file was empty or corrupted
        os.remove(filepath)

    # Otherwise fetch from Kite
    try:
        time.sleep(0.4) # Respect 3 requests/sec rate limit
        data = kite.historical_data(token, start, end, interval)
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.to_csv(filepath, index=False)
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Failed to fetch data for {symbol}: {e}")
        return pd.DataFrame()

def load_universe(kite):
    try:
        instruments_df = pd.read_csv(config.INSTRUMENTS_FILE)
    except FileNotFoundError:
        print(f"Error: {config.INSTRUMENTS_FILE} not found.")
        sys.exit()
    
    universe_data = {}
    print("Pre-fetching data for all universe instruments... (This takes a while the first time)")
    for idx, row in instruments_df.iterrows():
        symbol = row['symbol']
        token = int(row['instrument_token'])
        
        df = fetch_data(kite, symbol, token, config.START_DATE, config.END_DATE, config.TIMEFRAME)
        if not df.empty:
            # Set index for easy date alignment later
            df.set_index('date', inplace=True)
            universe_data[symbol] = df
            
    print(f"Successfully loaded {len(universe_data)} instruments into memory.")
    return universe_data

def load_benchmark(kite, symbol, token=256265):
    # Default token 256265 is NIFTY 50
    print(f"Pre-fetching benchmark {symbol}...")
    df = fetch_data(kite, symbol, token, config.START_DATE, config.END_DATE, config.TIMEFRAME)
    if not df.empty:
        df.set_index('date', inplace=True)
    return df
