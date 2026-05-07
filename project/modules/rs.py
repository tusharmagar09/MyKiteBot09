def compute_rs_score(stock_df, index_df, i, lookback=50):
    """
    No look-ahead RS score calculation.
    """
    if i < lookback:
        return None
    
    # Ensure index alignment hasn't caused out-of-bounds
    if i >= len(stock_df) or i >= len(index_df):
        return None
        
    stock_ret = (stock_df['close'].iloc[i] / stock_df['close'].iloc[i - lookback]) - 1
    index_ret = (index_df['close'].iloc[i] / index_df['close'].iloc[i - lookback]) - 1
    
    return stock_ret - index_ret   # excess return
