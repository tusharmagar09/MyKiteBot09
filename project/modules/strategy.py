import pandas as pd

def check_entry(df, i, market_ok, sector_ok, return_details=False):
    # --- Preconditions ---
    if i < 252:
        return False if not return_details else (False, {})

    # Check for NaN in critical cols
    cols = ['WMA10', 'WMA30', 'EMA20', 'EMA50', 'RSI', '52W_HIGH', 'close', 'Weekly_Vol', 'Vol_Avg_20']
    for col in cols:
        if col not in df.columns or pd.isna(df[col].iloc[i]):
            return False if not return_details else (False, {})

    # 1. Crossover condition: 10 WMA crossed 30 WMA from below in the last 5 days
    cross_happened = False
    for lookback in range(5):
        idx = i - lookback
        if idx <= 0: break
        if df['WMA10'].iloc[idx-1] <= df['WMA30'].iloc[idx-1] and df['WMA10'].iloc[idx] > df['WMA30'].iloc[idx]:
            cross_happened = True
            break

    # 2. Individual Conditions
    ema_cond = df['EMA20'].iloc[i] > df['EMA50'].iloc[i]
    rsi_cond = df['RSI'].iloc[i] > 55
    high_cond = df['close'].iloc[i] >= 0.85 * df['close'].iloc[i-252:i].max()
    vol_cond = df['Weekly_Vol'].iloc[i] >= 1.5 * df['Vol_Avg_20'].iloc[i]

    # Overall respects market_ok
    overall = market_ok and cross_happened and ema_cond and rsi_cond and high_cond and vol_cond

    if return_details:
        details = {
            "cross": cross_happened,
            "ema": ema_cond,
            "rsi": rsi_cond,
            "high": high_cond,
            "vol": vol_cond,
            "market": market_ok
        }
        return overall, details
    
    return overall
