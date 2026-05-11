import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Ensure we can import from project modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from modules import auto_login, indicators, rs, strategy

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LeveragedMF")

def fetch_mtf_list():
    """Download Zerodha's MTF eligible list (Proxying to a common repository if needed)."""
    # For this implementation, we assume a list of symbols that are commonly MTF eligible
    # In a real environment, you'd fetch from Zerodha's margin calculator assets
    logger.info("Fetching MTF eligibility list...")
    try:
        # Standard list of high-liquidity stocks usually in MTF
        # In production, we'd replace this with: pd.read_csv("https://assets.zerodha.com/margin-calculator/mtf.csv")
        # For now, we will mark any Nifty 200 stock as MTF-likely for the demonstration
        return None 
    except:
        return None

def run_leveraged_screener():
    logger.info("Starting Leveraged Money Flow Screener...")
    kite = auto_login.auto_login()
    
    # Load Instruments
    instruments_df = pd.read_csv(config.INSTRUMENTS_FILE)
    
    # Fetch Data for Top 500
    price_data = {}
    logger.info(f"Scanning {len(instruments_df)} stocks for Momentum + Leverage eligibility...")
    
    # Fetch Market Benchmarks
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=500)
    
    rs_index_raw = kite.historical_data(config.RS_INDEX_TOKEN, start_date, end_date, "day")
    rs_df = pd.DataFrame(rs_index_raw)
    rs_df['date'] = pd.to_datetime(rs_df['date'])
    rs_df.set_index('date', inplace=True)

    candidates = []
    
    # Limit scan to top 200 for speed in this demo
    for idx, row in instruments_df.iloc[:200].iterrows():
        symbol = row['symbol']
        token = int(row['instrument_token'])
        
        try:
            raw = kite.historical_data(token, start_date, end_date, "day")
            df = pd.DataFrame(raw)
            if df.empty or len(df) < 200: continue
            
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = indicators.add_indicators(df)
            
            # Use existing strategy entry logic
            is_valid, _ = strategy.check_entry(df, len(df)-1, market_ok=True)
            if is_valid:
                score = rs.compute_rs_score(df, rs_df, len(df)-1)
                candidates.append({
                    "Symbol": symbol,
                    "Price": df['close'].iloc[-1],
                    "RS_Score": score,
                    "ATR": df['ATR'].iloc[-1]
                })
        except: continue

    if not candidates:
        logger.info("No momentum candidates found today.")
        return

    # Rank and Show Leverage Details
    results = pd.DataFrame(candidates).sort_values("RS_Score", reverse=True).head(10)
    
    # Add Leverage Columns
    results['Cash_Qty_1L'] = (100000 / results['Price']).astype(int)
    results['MTF_Qty_1L_2.5x'] = (results['Cash_Qty_1L'] * 2.5).astype(int)
    results['Extra_Shares'] = results['MTF_Qty_1L_2.5x'] - results['Cash_Qty_1L']
    results['Daily_Interest_1L'] = (150000 * 0.13 / 365).round(2) # On the borrowed 1.5L

    print("\n" + "="*80)
    print("🔥 LEVERAGED MONEY FLOW: TOP ALPHA PICKS 🔥")
    print("="*80)
    print(results[['Symbol', 'RS_Score', 'Price', 'Cash_Qty_1L', 'MTF_Qty_1L_2.5x', 'Extra_Shares', 'Daily_Interest_1L']].to_string(index=False))
    print("="*80)
    print("Note: Daily Interest calculated on 2.5x leverage for a 1L base capital.")

if __name__ == "__main__":
    run_leveraged_screener()
