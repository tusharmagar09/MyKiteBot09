import pandas as pd

print("Downloading Nifty 500 list...")
# Get Nifty 500 list (from a reliable github mirror of the NSE file)
nifty_url = "https://raw.githubusercontent.com/kprohith/nse-stock-analysis/master/ind_nifty500list.csv"
nifty_df = pd.read_csv(nifty_url)
nifty_symbols = nifty_df['Symbol'].tolist()

print("Downloading Kite instruments list...")
# Get all Kite instruments
kite_url = "https://api.kite.trade/instruments"
kite_df = pd.read_csv(kite_url)

# Filter for NSE equity instruments
nse_eq = kite_df[(kite_df['exchange'] == 'NSE') & (kite_df['segment'] == 'NSE')]

print("Matching tokens...")
# Filter Kite instruments to only include Nifty 500 symbols
final_df = nse_eq[nse_eq['tradingsymbol'].isin(nifty_symbols)]

# Select only the columns we need
output_df = final_df[['tradingsymbol', 'instrument_token']].copy()
output_df.rename(columns={'tradingsymbol': 'symbol'}, inplace=True)

# Save to instruments.csv
output_df.to_csv("instruments.csv", index=False)
print(f"Successfully generated instruments.csv with {len(output_df)} Nifty 500 stocks!")
