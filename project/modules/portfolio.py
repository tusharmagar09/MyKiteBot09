import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def calculate_qty(capital, price, atr, risk_per_trade):
    risk_amt = capital * risk_per_trade  
    stop_distance = atr * config.SL_ATR_MULT

    if stop_distance <= 0 or pd.isna(stop_distance):
        return 0

    qty = int(risk_amt / stop_distance)

    # Ensure affordability
    max_affordable = int(capital / price)
    return max(0, min(qty, max_affordable))

def manage_trade(trade, current_price, current_atr, current_date, wma10=None, wma30=None):
    exit_flag = False
    partial_qty_sold = 0

    if pd.isna(current_atr) or current_atr == 0:
        current_atr = trade['atr']

    # 1) Partial at 2.4 ATR (Risk-Free Cover)
    if not trade['partial_done']:
        target = trade['entry_price'] + (config.TARGET_ATR_MULT * trade['atr'])
        if current_price >= target:
            # Calculate exactly how many shares to sell so the realized profit 
            # equals the maximum potential loss if the remaining shares hit the initial SL.
            # This makes it a perfectly mathematically risk-free trade.
            if current_price > trade['initial_sl']:
                sell_fraction = (trade['entry_price'] - trade['initial_sl']) / (current_price - trade['initial_sl'])
                sell_qty = int(trade['qty'] * sell_fraction)
            else:
                sell_qty = trade['qty'] // 2
                
            if sell_qty > 0:
                trade['qty'] -= sell_qty
                trade['partial_done'] = True
                partial_qty_sold = sell_qty
            else:
                trade['partial_done'] = True # Only 1 share, can't partial

    # 2) Trailing stop
    trail_sl = current_price - (config.TRAIL_ATR_MULT * current_atr)
    trade['sl'] = max(trade['sl'], trail_sl)

    # 3) Time stop
    holding_days = (current_date - trade['entry_date']).days
    if holding_days >= config.MAX_HOLDING_DAYS:
        exit_flag = True

    # 4) Trend Reversal Stop
    if wma10 is not None and wma30 is not None:
        if wma10 < wma30:
            exit_flag = True

    # 5) SL hit
    if current_price <= trade['sl']:
        exit_flag = True

    return exit_flag, partial_qty_sold
