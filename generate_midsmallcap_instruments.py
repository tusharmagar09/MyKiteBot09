"""
Generate instruments.csv for Nifty MidSmallcap 400 stocks.
Fetches the official NSE constituent list, then matches each symbol
against the full Kite instruments dump to get instrument_tokens.
"""
import pandas as pd
from kiteconnect import KiteConnect
import sys, os

# --- Config ---
API_KEY = "qzlyy9b8wnyijett"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_token.txt")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instruments_midsmallcap400.csv")

# 1. Get access token
try:
    with open(TOKEN_FILE, "r") as f:
        access_token = f.read().strip()
except FileNotFoundError:
    print(f"Error: {TOKEN_FILE} not found. Run login.py first.")
    sys.exit(1)

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(access_token)

# 2. Fetch the full Kite instruments dump (NSE only)
print("Fetching full Kite instruments dump (NSE)...")
all_instruments = kite.instruments("NSE")
kite_df = pd.DataFrame(all_instruments)
print(f"  Total Kite NSE instruments: {len(kite_df)}")

# Filter to EQ (equity) tradingsymbol
kite_eq = kite_df[kite_df['segment'] == 'NSE'].copy()
# Build a lookup: tradingsymbol -> instrument_token
kite_lookup = dict(zip(kite_eq['tradingsymbol'], kite_eq['instrument_token']))

# 3. Fetch the official NSE MidSmallcap 400 constituent list
print("Fetching Nifty MidSmallcap 400 list from NSE...")
nse_url = "https://archives.nseindia.com/content/indices/ind_niftymidsmallcap400list.csv"
nse_df = pd.read_csv(nse_url)
print(f"  Total MidSmallcap 400 constituents from NSE: {len(nse_df)}")

# 4. Match symbols
matched = []
unmatched = []

for _, row in nse_df.iterrows():
    symbol = row['Symbol'].strip()
    if symbol in kite_lookup:
        matched.append({
            "symbol": symbol,
            "instrument_token": int(kite_lookup[symbol])
        })
    else:
        unmatched.append(symbol)

# 5. Save
result_df = pd.DataFrame(matched)
result_df.to_csv(OUTPUT_FILE, index=False)

print(f"\n--- RESULTS ---")
print(f"Matched: {len(matched)} / {len(nse_df)}")
print(f"Unmatched: {len(unmatched)}")
if unmatched:
    print(f"Unmatched symbols: {unmatched[:20]}...")
print(f"Saved to: {OUTPUT_FILE}")
