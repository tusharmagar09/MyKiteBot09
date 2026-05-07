import pandas as pd

def generate_report(trades_log, equity_curve, rejected_signals, reports_dir):
    if not trades_log:
        print("No trades executed. Report generation skipped.")
        return

    trades_df = pd.DataFrame(trades_log)
    equity_df = pd.DataFrame(equity_curve)
    rejected_df = pd.DataFrame(rejected_signals)
    
    # Save raw logs
    trades_df.to_csv(f"{reports_dir}/trades.csv", index=False)
    equity_df.to_csv(f"{reports_dir}/equity_curve.csv", index=False)
    rejected_df.to_csv(f"{reports_dir}/rejected_signals.csv", index=False)
    
    # --- Metrics ---
    total_trades = len(trades_df)
    win_trades = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
    total_pnl = trades_df['pnl'].sum()
    avg_return = trades_df['pnl'].mean()
    start_equity = equity_df.iloc[0]['equity']
    end_equity = equity_df.iloc[-1]['equity']
    
    first_trade_date = pd.to_datetime(trades_df['entry_date'].min())
    end_date = pd.to_datetime(equity_df.iloc[-1]['date'])
    active_days = (end_date - first_trade_date).days
    active_years = max(active_days / 365.25, 0.1)
    cagr = ((end_equity / start_equity) ** (1/active_years) - 1) * 100
    
    equity_df['peak'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
    max_dd = equity_df['drawdown'].min() * 100
    
    avg_positions = equity_df['positions_count'].mean()
    
    # --- Advanced Quant Metrics ---
    # Daily Returns for Sharpe
    equity_df['returns'] = equity_df['equity'].pct_change()
    daily_vol = equity_df['returns'].std()
    sharpe = (equity_df['returns'].mean() / daily_vol) * (252**0.5) if daily_vol > 0 else 0
    
    # Profit Factor
    gains = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    profit_factor = (gains / losses) if losses > 0 else gains
    
    metrics = {
        "Total Trades": total_trades,
        "Win Rate %": round(win_rate, 2),
        "Profit Factor": round(profit_factor, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Avg Profit/Loss": round(avg_return, 2),
        "Avg Open Positions": round(avg_positions, 2),
        "Starting Capital": start_equity,
        "Ending Capital": round(end_equity, 2),
        "Total Net PnL": round(total_pnl, 2),
        "CAGR %": round(cagr, 2),
        "Max Drawdown %": round(max_dd, 2)
    }
    
    summary_df = pd.DataFrame([metrics])
    summary_df.to_csv(f"{reports_dir}/summary.csv", index=False)
    
    # --- Sector Exposure Analysis ---
    print("Generating Sector Exposure Report...")
    try:
        nifty_url = "https://raw.githubusercontent.com/kprohith/nse-stock-analysis/master/ind_nifty500list.csv"
        nifty_info = pd.read_csv(nifty_url)
        sector_map = dict(zip(nifty_info['Symbol'], nifty_info['Industry']))
    except Exception as e:
        print(f"Warning: Could not fetch sector info: {e}")
        sector_map = {}

    # Flatten daily holdings to analyze sector concentration
    all_holdings = []
    for _, row in equity_df.iterrows():
        for sym in row.get('holdings', []):
            all_holdings.append({
                "date": row['date'],
                "symbol": sym,
                "sector": sector_map.get(sym, "Unknown")
            })
    
    exposure_df = pd.DataFrame(all_holdings)
    if not exposure_df.empty:
        sector_concentration = exposure_df.groupby('sector').size() / len(exposure_df) * 100
        sector_concentration.sort_values(ascending=False).to_csv(f"{reports_dir}/sector_exposure.csv")
    
    print("\n--- STRATEGY REPORT ---")
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print(f"Reports saved to {reports_dir}")
