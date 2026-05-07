import pandas as pd
import numpy as np

def add_indicators(df):
    if df.empty or len(df) < 252:
        return df
        
    # Daily Indicators
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['52W_HIGH'] = df['close'].rolling(252).max()

    # Resample to Weekly
    weekly = df.resample('W').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    if weekly.empty or len(weekly) < 30:
        return df

    # Weekly WMA
    def wma(x):
        weights = np.arange(1, len(x) + 1)
        return np.dot(x, weights) / weights.sum()

    weekly['WMA10'] = weekly['close'].rolling(10).apply(wma, raw=True)
    weekly['WMA30'] = weekly['close'].rolling(30).apply(wma, raw=True)

    # Weekly RSI
    delta = weekly['close'].diff()
    # Simple Wilder's MA approximation for RSI
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    weekly['RSI'] = 100 - (100 / (1 + rs))

    # Weekly ATR
    weekly['prev_close'] = weekly['close'].shift(1)
    weekly['TR1'] = weekly['high'] - weekly['low']
    weekly['TR2'] = (weekly['high'] - weekly['prev_close']).abs()
    weekly['TR3'] = (weekly['low'] - weekly['prev_close']).abs()
    weekly['TR'] = weekly[['TR1', 'TR2', 'TR3']].max(axis=1)
    weekly['ATR'] = weekly['TR'].rolling(14).mean()

    # Weekly Volume Average
    weekly['Vol_Avg_20'] = weekly['volume'].rolling(20).mean()

    # Drop intermediate columns to keep things clean
    weekly = weekly[['WMA10', 'WMA30', 'RSI', 'ATR', 'volume', 'Vol_Avg_20']]
    weekly.rename(columns={'volume': 'Weekly_Vol'}, inplace=True)

    # Ensure indices are sorted for merge_asof
    df.sort_index(inplace=True)
    weekly.sort_index(inplace=True)
    
    # Use merge_asof to perfectly align weekly timestamps to subsequent daily rows
    df = pd.merge_asof(df, weekly, left_index=True, right_index=True, direction='backward')
    
    return df
