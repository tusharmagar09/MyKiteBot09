import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from modules import data, indicators, rs, strategy, portfolio, report, auto_login

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def main():
    kite = auto_login.auto_login()
    print(f"Using instruments file: {os.path.abspath(config.INSTRUMENTS_FILE)}")
    
    # 1. Load Data
    price_data = data.load_universe(kite)
    if not price_data:
        print("No stock data available.")
        return
        
    market_df = data.load_benchmark(kite, config.MARKET_INDEX_SYMBOL, token=config.MARKET_INDEX_TOKEN)
    if market_df.empty:
        print("Could not load Market Filter index.")
        return
        
    nifty500_df = data.load_benchmark(kite, config.RS_INDEX_SYMBOL, token=config.RS_INDEX_TOKEN) 
    if nifty500_df.empty:
        nifty500_df = market_df 

    # 2. Add Indicators
    print("Computing Indicators (this might take a moment)...")
    for symbol, df in price_data.items():
        price_data[symbol] = indicators.add_indicators(df)
        
    trading_days = market_df.index.intersection(price_data[list(price_data.keys())[0]].index)

    # 3. Setup Portfolio Engine
    current_portfolio = []
    capital = config.INITIAL_CAPITAL
    
    trades_log = []
    equity_curve = []
    rejected_signals = []
    
    print("Starting Backtest Engine...")

    market_df['EMA50'] = market_df['close'].ewm(span=50, adjust=False).mean()
    market_df['EMA200'] = market_df['close'].ewm(span=200, adjust=False).mean()

    # 4. Main Simulation Loop
    for current_date in trading_days:
        
        market_ok = market_df.loc[current_date, 'close'] > market_df.loc[current_date, 'EMA50']
        market_supertrend = market_df.loc[current_date, 'close'] > market_df.loc[current_date, 'EMA200']
        current_risk_pct = config.HIGH_RISK_PER_TRADE if market_supertrend else config.NORMAL_RISK_PER_TRADE
        
        sector_ok_map = {} # Placeholder

        # --- Process Open Positions (Exits) ---
        for trade in current_portfolio[:]:
            df = price_data[trade['symbol']]
            
            if current_date not in df.index:
                continue
                
            i = df.index.get_loc(current_date)
            price = df['close'].iloc[i]
            atr = df['ATR'].iloc[i]
            
            wma10 = df['WMA10'].iloc[i] if 'WMA10' in df.columns else None
            wma30 = df['WMA30'].iloc[i] if 'WMA30' in df.columns else None
            
            exit_flag, partial_qty_sold = portfolio.manage_trade(trade, price, atr, current_date, wma10, wma30)
            
            if partial_qty_sold > 0:
                capital += partial_qty_sold * price
                pnl = (price - trade['entry_price']) * partial_qty_sold
                trades_log.append({
                    "symbol": trade['symbol'],
                    "entry_date": trade['entry_date'],
                    "exit_date": current_date,
                    "entry_price": trade['entry_price'],
                    "exit_price": price,
                    "qty": partial_qty_sold,
                    "pnl": pnl
                })
            
            if exit_flag:
                capital += trade['qty'] * price
                
                pnl = (price - trade['entry_price']) * trade['qty']
                trades_log.append({
                    "symbol": trade['symbol'],
                    "entry_date": trade['entry_date'],
                    "exit_date": current_date,
                    "entry_price": trade['entry_price'],
                    "exit_price": price,
                    "qty": trade['qty'],
                    "pnl": pnl
                })
                current_portfolio.remove(trade)

        # --- Record daily equity (early for capital buffer check) ---
        open_portfolio_value = sum(
            t['qty'] * price_data[t['symbol']].loc[current_date, 'close'] 
            for t in current_portfolio if current_date in price_data[t['symbol']].index
        )
        total_equity = capital + open_portfolio_value
        min_cash_required = total_equity * (1.0 - config.MAX_DEPLOYMENT)

        # --- Build Signal Book (New Logic: Technicals first, then RS ranking) ---
        candidate_pool = []
        for symbol, df in price_data.items():
            if current_date not in df.index:
                continue
            i = df.index.get_loc(current_date)
            
            # 1. Apply Technical entry Conditions to ALL stocks
            sector_ok = sector_ok_map.get(symbol, True)
            if strategy.check_entry(df, i, market_ok, sector_ok):
                # 2. If passes, compute RS for ranking
                rs_score = rs.compute_rs_score(df, nifty500_df, i)
                if rs_score is not None:
                    candidate_pool.append({
                        "symbol": symbol,
                        "rs_score": rs_score,
                        "price": df['close'].iloc[i],
                        "atr": df['ATR'].iloc[i]
                    })
                
        # 3. Rank ONLY Candidates by RS (highest score first)
        candidate_pool.sort(key=lambda x: x['rs_score'], reverse=True)
        
        # 4. Update Current Portfolio RS scores for replacement check
        for trade in current_portfolio:
            df = price_data[trade['symbol']]
            if current_date in df.index:
                i = df.index.get_loc(current_date)
                updated_rs = rs.compute_rs_score(df, nifty500_df, i)
                if updated_rs is not None:
                    trade['rs_score'] = updated_rs

        # 5. Selection & Tracking Rejections (with Replacement Logic)
        daily_entries_count = 0
        for rank, c in enumerate(candidate_pool):
            if any(t['symbol'] == c['symbol'] for t in current_portfolio):
                continue
            
            rejection_reason = None
            
            # Check Daily Entry Cap
            if daily_entries_count >= config.MAX_ENTRIES_PER_DAY:
                rejection_reason = "daily entry cap"
                rejected_signals.append({
                    "date": current_date, "symbol": c['symbol'],
                    "rs_score": round(c['rs_score'], 2), "reason": rejection_reason
                })
                continue

            # Check Slots
            if len(current_portfolio) < config.MAX_POSITIONS:
                # Normal Entry
                qty = portfolio.calculate_qty(capital, c['price'], c['atr'], current_risk_pct)
                required_capital = qty * c['price']
                if qty > 0 and (capital - required_capital) >= min_cash_required:
                    sl_price = c['price'] - (config.SL_ATR_MULT * c['atr'])
                    trade = {
                        "symbol": c['symbol'], "entry_price": c['price'], "qty": qty,
                        "sl": sl_price, "initial_sl": sl_price, "atr": c['atr'],
                        "partial_done": False, "entry_date": current_date, "rs_score": c['rs_score']
                    }
                    current_portfolio.append(trade)
                    capital -= required_capital
                    daily_entries_count += 1
                else:
                    rejection_reason = "no cash"
                    rejected_signals.append({
                        "date": current_date, "symbol": c['symbol'],
                        "rs_score": round(c['rs_score'], 2), "reason": rejection_reason
                    })
            else:
                # PORTFOLIO FULL - Try Replacement Logic
                # Sort portfolio by RS to find the weakest
                current_portfolio.sort(key=lambda x: x.get('rs_score', -999))
                weakest = current_portfolio[0]
                
                # If candidate RS is significantly better than weakest (e.g., > 0.2 higher)
                if c['rs_score'] > weakest.get('rs_score', -999) + 0.2:
                    # EXIT WEAKEST
                    df_w = price_data[weakest['symbol']]
                    exit_price = df_w.loc[current_date, 'close']
                    capital += weakest['qty'] * exit_price
                    pnl = (exit_price - weakest['entry_price']) * weakest['qty']
                    trades_log.append({
                        "symbol": weakest['symbol'], "entry_date": weakest['entry_date'],
                        "exit_date": current_date, "entry_price": weakest['entry_price'],
                        "exit_price": exit_price, "qty": weakest['qty'], "pnl": pnl,
                        "exit_reason": "RS replacement"
                    })
                    current_portfolio.remove(weakest)
                    
                    # ENTER NEW
                    qty = portfolio.calculate_qty(capital, c['price'], c['atr'], current_risk_pct)
                    required_capital = qty * c['price']
                    if qty > 0:
                        sl_price = c['price'] - (config.SL_ATR_MULT * c['atr'])
                        trade = {
                            "symbol": c['symbol'], "entry_price": c['price'], "qty": qty,
                            "sl": sl_price, "initial_sl": sl_price, "atr": c['atr'],
                            "partial_done": False, "entry_date": current_date, "rs_score": c['rs_score']
                        }
                        current_portfolio.append(trade)
                        capital -= required_capital
                        daily_entries_count += 1
                else:
                    rejection_reason = "max positions (RS gap too small)"
                    rejected_signals.append({
                        "date": current_date, "symbol": c['symbol'],
                        "rs_score": round(c['rs_score'], 2), "reason": rejection_reason
                    })
        
        equity_curve.append({
            "date": current_date,
            "equity": total_equity,
            "positions_count": len(current_portfolio),
            "holdings": [t['symbol'] for t in current_portfolio]
        })

    # 5. Generate Report
    if equity_curve:
        start_date = trading_days[0]
        equity_curve.insert(0, {
            "date": start_date, 
            "equity": config.INITIAL_CAPITAL,
            "positions_count": 0,
            "holdings": []
        })

    report.generate_report(trades_log, equity_curve, rejected_signals, config.REPORTS_DIR)

if __name__ == "__main__":
    main()
