import pandas as pd

def check_entry(df, i, market_ok, sector_ok):
    # --- Preconditions ---
    if i < 252:
        return False

    if not market_ok:
        return False

    if not sector_ok:
        return False

    # Check for NaN in critical cols
    cols = ['WMA10', 'WMA30', 'EMA20', 'EMA50', 'RSI', '52W_HIGH', 'close', 'Weekly_Vol', 'Vol_Avg_20']
    for col in cols:
        if col not in df.columns or pd.isna(df[col].iloc[i]):
            return False

    # Crossover condition: 10 WMA crossed 30 WMA from below in the last 5 days
    cross_happened = False
    for lookback in range(5):
        idx = i - lookback
        if idx <= 0: break
        if df['WMA10'].iloc[idx-1] <= df['WMA30'].iloc[idx-1] and df['WMA10'].iloc[idx] > df['WMA30'].iloc[idx]:
            cross_happened = True
            break

    cond = (
        cross_happened and
        df['EMA20'].iloc[i] > df['EMA50'].iloc[i] and
        df['RSI'].iloc[i] > 55 and
        df['close'].iloc[i] >= 0.85 * df['close'].iloc[i-252:i].max() and
        df['Weekly_Vol'].iloc[i] >= 1.5 * df['Vol_Avg_20'].iloc[i]
    )

    return cond
