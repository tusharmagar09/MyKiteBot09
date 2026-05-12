"""
live_bot.py — Production Live Trading Orchestrator.
Runs once per day at 3:00 PM IST (near market close).
Handles: auto-login → holiday check → exits → entries → GTT → state → notify → shutdown.
"""
import os
import sys
import logging
import subprocess
import argparse
from datetime import datetime, timedelta

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from modules import auto_login, indicators, rs, strategy, portfolio, orders, state, notifications

# ─────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────────
def setup_logging():
    today = datetime.now().strftime("%Y-%m-%d")
    log_format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    # Root logger
    logging.basicConfig(level=logging.INFO, format=log_format)

    # File handler — main bot log
    fh = logging.FileHandler(os.path.join(config.LOG_DIR, f"bot_{today}.log"))
    fh.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(fh)

    # File handler — orders only
    oh = logging.FileHandler(os.path.join(config.LOG_DIR, f"orders_{today}.log"))
    oh.setFormatter(logging.Formatter(log_format))
    logging.getLogger("orders").addHandler(oh)

    # File handler — errors only
    eh = logging.FileHandler(os.path.join(config.LOG_DIR, f"errors_{today}.log"))
    eh.setLevel(logging.ERROR)
    eh.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(eh)

logger = logging.getLogger("live_bot")


# ─────────────────────────────────────────────────────────────────
# HOLIDAY DETECTION
# ─────────────────────────────────────────────────────────────────
def check_market_status(kite):
    """
    Check if the market is currently open.
    Uses IST timezone regardless of server timezone.
    Returns: (is_open: bool, reason: str)
    """
    from datetime import timezone
    # IST = UTC + 5:30
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    today = now.date()
    
    logger.info(f"Current IST time: {now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    # Check if weekend
    if today.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False, "Weekend"
    
    # Check if within market hours (9:00 AM - 3:30 PM IST)
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < market_open or now > market_close:
        return False, f"After market hours (IST: {now.strftime('%H:%M')})"
    
    # Market hours on a weekday — verify with Kite API for holidays
    try:
        quote = kite.quote("NSE:NIFTY 50")
        nifty = quote.get("NSE:NIFTY 50", {})
        logger.info(f"Nifty quote keys: {list(nifty.keys())}")
        
        last_trade_time = nifty.get("last_trade_time")
        last_price = nifty.get("last_price", 0)
        
        # Method 1: Check last_trade_time for Nifty 50
        if last_trade_time is not None and hasattr(last_trade_time, 'date'):
            if last_trade_time.date() == today:
                return True, "Market is open"
            else:
                return False, f"Market Holiday (Last trade: {last_trade_time.strftime('%Y-%m-%d')})"
        
        # Method 2: Check a liquid stock (RELIANCE) as fallback
        try:
            stock_quote = kite.quote("NSE:RELIANCE")
            reliance = stock_quote.get("NSE:RELIANCE", {})
            stock_trade_time = reliance.get("last_trade_time")
            if stock_trade_time and hasattr(stock_trade_time, 'date'):
                if stock_trade_time.date() == today:
                    return True, "Market is open"
                else:
                    return False, f"Market Holiday (RELIANCE last trade: {stock_trade_time.strftime('%Y-%m-%d')})"
            
        return False, "Could not verify live market activity (Holiday suspected)"

    except Exception as e:
        logger.warning(f"Market status check failed: {e}. Assuming market is open.")
        return True, "Assumed open (API check failed)"


# ─────────────────────────────────────────────────────────────────
# DATA FETCHING (LIVE)
# ─────────────────────────────────────────────────────────────────
def fetch_historical_data(kite, symbol, token, days=500):
    """Fetch recent historical data for a single stock."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    try:
        data = kite.historical_data(token, start_date, end_date, "day")
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        return df
    except Exception as e:
        logger.warning(f"Data fetch failed for {symbol}: {e}")
        return pd.DataFrame()


def load_all_data(kite):
    """Load historical data for the entire universe + benchmarks."""
    import time

    # Load instruments
    try:
        instruments_df = pd.read_csv(config.INSTRUMENTS_FILE)
    except FileNotFoundError:
        logger.error(f"Instruments file not found: {config.INSTRUMENTS_FILE}")
        return {}, pd.DataFrame(), pd.DataFrame()

    # Fetch universe
    price_data = {}
    total = len(instruments_df)
    logger.info(f"Fetching data for {total} instruments...")

    for idx, row in instruments_df.iterrows():
        symbol = row['symbol']
        token = int(row['instrument_token'])
        time.sleep(0.35)  # Rate limit: 3 req/sec

        df = fetch_historical_data(kite, symbol, token)
        if not df.empty and len(df) >= 200:
            price_data[symbol] = indicators.add_indicators(df)

        if (idx + 1) % 50 == 0:
            logger.info(f"  Progress: {idx+1}/{total} instruments loaded. ({len(price_data)} valid so far)")

    logger.info(f"Loaded {len(price_data)} instruments with sufficient data.")

    # Fetch benchmarks
    time.sleep(0.35)
    market_df = fetch_historical_data(kite, config.MARKET_INDEX_SYMBOL, config.MARKET_INDEX_TOKEN)
    if not market_df.empty:
        market_df['EMA50'] = market_df['close'].ewm(span=50, adjust=False).mean()
        market_df['EMA200'] = market_df['close'].ewm(span=200, adjust=False).mean()

    time.sleep(0.35)
    rs_df = fetch_historical_data(kite, config.RS_INDEX_SYMBOL, config.RS_INDEX_TOKEN)
    if rs_df.empty:
        rs_df = market_df

    return price_data, market_df, rs_df


# ─────────────────────────────────────────────────────────────────
# PRICE SANITY CHECK
# ─────────────────────────────────────────────────────────────────
def price_sanity_check(kite, symbol, yesterday_close):
    """Reject if live price deviates > 5% from yesterday's close."""
    try:
        quote = kite.quote(f"NSE:{symbol}")
        live_price = quote[f"NSE:{symbol}"]["last_price"]
        deviation = abs(live_price - yesterday_close) / yesterday_close

        if deviation > config.PRICE_DEVIATION_LIMIT:
            logger.warning(f"Price sanity FAILED: {symbol} | Yesterday={yesterday_close:.2f}, Live={live_price:.2f}, Dev={deviation:.2%}")
            return None
        return live_price
    except Exception as e:
        logger.warning(f"Price check failed for {symbol}: {e}. Using yesterday's close.")
        return yesterday_close


# ─────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────
def run(dry_run=False):
    setup_logging()
    logger.info("=" * 60)
    logger.info("LIVE TRADING BOT STARTED")
    logger.info("=" * 60)

    entries_today = []
    exits_today = []

    try:
        # ── Step 1: Auto Login ──
        logger.info("Step 1: Auto-login to Kite...")
        kite = auto_login.auto_login()
        notifications.send_startup_msg()

        # ── Step 2: Market Status Check ──
        logger.info("Step 2: Checking if market is open...")
        is_open, reason = check_market_status(kite)
        if not is_open:
            logger.info(f"Market is closed. Reason: {reason}. Exiting.")
            notifications.send_holiday_msg(reason)
            return

        # ── Step 3: Load State ──
        logger.info("Step 3: Loading portfolio state...")
        state.backup_state()
        state.backup_trades_history()
        current_portfolio, capital = state.load_state()

        # ── Step 3b: Check Actual Available Cash ──
        try:
            margins = kite.margins()
            equity_margins = margins.get("equity", {})
            # Use 'live_balance' or 'net' as the source of truth
            actual_cash = equity_margins.get("available", {}).get("live_balance", 
                          equity_margins.get("net", 0))
            
            # Sync internal capital with live broker balance
            if actual_cash > 0:
                if capital != actual_cash:
                    logger.info(f"Syncing internal capital with broker: Rs.{capital:,.2f} -> Rs.{actual_cash:,.2f}")
                capital = actual_cash
            
            logger.info(f"Final Trading Capital: Rs.{capital:,.2f}")
            
            if capital < 10000:
                logger.warning(f"Low cash balance: Rs.{capital:,.2f}. Some entries may be skipped.")
                notifications.send_error_alert(f"⚠️ Low cash balance: Rs.{capital:,.2f}. Bot may not be able to place full orders.")
        except Exception as e:
            logger.warning(f"Could not fetch margins: {e}. Falling back to saved state capital.")

        # ── Step 4: Reconcile with Broker ──
        logger.info("Step 4: Reconciling with Kite holdings...")
        discrepancies = state.reconcile(kite, current_portfolio)
        if discrepancies:
            notifications.send_error_alert(f"Reconciliation mismatch: {len(discrepancies)} discrepancies found. Check logs.")

        # ── Step 5: Fetch Data ──
        logger.info("Step 5: Fetching market data...")
        price_data, market_df, rs_df = load_all_data(kite)

        if not price_data or market_df.empty:
            logger.error("No data available. Aborting.")
            notifications.send_error_alert("Data fetch failed. No trades executed.")
            shutdown_ec2(dry_run)
            return

        # ── Step 6: Market Regime ──
        today_idx = -1  # Last available row = today's (or yesterday's close)
        market_close = market_df['close'].iloc[today_idx]
        market_ema50 = market_df['EMA50'].iloc[today_idx]
        market_ema200 = market_df['EMA200'].iloc[today_idx]

        market_ok = market_close > market_ema50
        market_supertrend = market_close > market_ema200
        current_risk_pct = config.HIGH_RISK_PER_TRADE if market_supertrend else config.NORMAL_RISK_PER_TRADE

        logger.info(f"Market Regime: Close={market_close:.2f} | EMA50={market_ema50:.2f} ({'ABOVE' if market_ok else 'BELOW'}) | EMA200={market_ema200:.2f} ({'SUPER' if market_supertrend else 'SHAKY'}) | Risk={current_risk_pct*100:.2f}%")

        # ── Step 7: Process Exits ──
        logger.info(f"Step 7: Processing {len(current_portfolio)} open positions...")
        current_date = pd.Timestamp(datetime.now().date())

        for trade in current_portfolio[:]:
            symbol = trade['symbol']
            if symbol not in price_data:
                logger.warning(f"No data for {symbol}. Skipping exit check.")
                continue

            df = price_data[symbol]
            i = len(df) - 1  # Latest bar
            price = df['close'].iloc[i]
            atr = df['ATR'].iloc[i] if not pd.isna(df['ATR'].iloc[i]) else trade['atr']

            wma10 = df['WMA10'].iloc[i] if 'WMA10' in df.columns and not pd.isna(df['WMA10'].iloc[i]) else None
            wma30 = df['WMA30'].iloc[i] if 'WMA30' in df.columns and not pd.isna(df['WMA30'].iloc[i]) else None

            exit_flag, partial_qty_sold = portfolio.manage_trade(trade, price, atr, current_date, wma10, wma30)

            # Handle partial exit
            if partial_qty_sold > 0:
                if not dry_run:
                    order_id = orders.place_sell(kite, symbol, partial_qty_sold)
                    if order_id:
                        orders.verify_order(kite, order_id)
                        # Cancel old OCO GTT, place single-leg trailing GTT
                        orders.cancel_gtt(kite, trade.get('gtt_id'))
                        new_gtt = orders.place_gtt_single(kite, symbol, trade['qty'], trade['sl'], price)
                        trade['gtt_id'] = new_gtt
                else:
                    logger.info(f"[DRY RUN] SELL PARTIAL: {symbol} x {partial_qty_sold} @ {price:.2f}")

                capital += partial_qty_sold * price
                pnl = (price - trade['entry_price']) * partial_qty_sold
                trade_record = {
                    "symbol": symbol, "entry_date": str(trade['entry_date']),
                    "exit_date": str(current_date), "entry_price": trade['entry_price'],
                    "exit_price": price, "qty": partial_qty_sold, "pnl": round(pnl, 2),
                    "exit_type": "PARTIAL"
                }
                state.log_trade(trade_record)
                exits_today.append({"symbol": symbol, "qty": partial_qty_sold, "price": price, "pnl": pnl})
                notifications.send_trade_alert("SELL (Partial)", symbol, partial_qty_sold, price)

            # Handle full exit
            if exit_flag:
                if not dry_run:
                    order_id = orders.place_sell(kite, symbol, trade['qty'])
                    if order_id:
                        orders.verify_order(kite, order_id)
                    orders.cancel_gtt(kite, trade.get('gtt_id'))
                else:
                    logger.info(f"[DRY RUN] SELL FULL: {symbol} x {trade['qty']} @ {price:.2f}")

                capital += trade['qty'] * price
                pnl = (price - trade['entry_price']) * trade['qty']
                trade_record = {
                    "symbol": symbol, "entry_date": str(trade['entry_date']),
                    "exit_date": str(current_date), "entry_price": trade['entry_price'],
                    "exit_price": price, "qty": trade['qty'], "pnl": round(pnl, 2),
                    "exit_type": "FULL"
                }
                state.log_trade(trade_record)
                exits_today.append({"symbol": symbol, "qty": trade['qty'], "price": price, "pnl": pnl})
                notifications.send_trade_alert("SELL", symbol, trade['qty'], price)
                current_portfolio.remove(trade)
                continue

            # Update trailing GTT if SL moved up
            old_sl = trade.get('_prev_sl', trade['sl'])
            if trade['sl'] > old_sl:
                if not dry_run:
                    orders.update_trailing_gtt(kite, trade, trade['sl'], price)
                else:
                    logger.info(f"[DRY RUN] UPDATE GTT: {symbol} SL {old_sl:.2f} → {trade['sl']:.2f}")
            trade['_prev_sl'] = trade['sl']
            
            # Update current RS score for replacement logic
            try:
                sym_df = price_data[trade['symbol']]
                cur_rs = rs.compute_rs_score(sym_df, rs_df, len(sym_df)-1)
                if cur_rs is not None:
                    trade['rs_score'] = cur_rs
            except Exception as e:
                logger.warning(f"Could not update RS for {trade['symbol']}: {e}")

        # ── LIQUIDITY REFRESH ──
        if exits_today:
            logger.info(f"Exits executed: {len(exits_today)}. Pausing 5s for margin settlement...")
            import time
            time.sleep(5)
            try:
                margins = kite.margins()
                equity_margins = margins.get("equity", {})
                
                # Robust detection: use live_balance if available, fallback to net
                live_bal = equity_margins.get("available", {}).get("live_balance", 0)
                net_bal = equity_margins.get("net", 0)
                capital = live_bal if live_bal > 0 else net_bal
                
                logger.info(f"Revised Available Margin after sales: Rs.{capital:,.2f}")
            except Exception as e:
                logger.warning(f"Could not refresh margins after sales: {e}")

        # ── Step 8: Scan for New Entries ──
        logger.info("Step 8: Scanning for entry signals...")

        # Compute total equity for deployment check
        open_value = sum(
            t['qty'] * price_data[t['symbol']]['close'].iloc[-1]
            for t in current_portfolio if t['symbol'] in price_data
        )
        total_equity = capital + open_value
        min_cash = total_equity * (1.0 - config.MAX_DEPLOYMENT)

        # Build candidate pool (Check technicals for ALL stocks first)
        candidate_pool = []
        diag_file = os.path.join(REPORTS_DIR, "diagnostic_scan.log")
        
        with open(diag_file, "a") as f:
            f.write(f"\n--- SCAN START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            for symbol, df in price_data.items():
                i = len(df) - 1
                overall, det = strategy.check_entry(df, i, market_ok, True, return_details=True)
                rs_val = rs.compute_rs_score(df, rs_df, i)
                
                # Write to Diagnostic Log
                if det:
                    f.write(f"{symbol:10} | Cross:{int(det['cross'])} EMA:{int(det['ema'])} RSI:{int(det['rsi'])} High:{int(det['high'])} Vol:{int(det['vol'])} Mkt:{int(det['market'])} | RS:{rs_val if rs_val else 0:.2f} | {'PASS' if overall else 'FAIL'}\n")

                if overall:
                    if rs_val is not None:
                        candidate_pool.append({
                            "symbol": symbol, "rs_score": rs_val,
                            "price": df['close'].iloc[i], "atr": df['ATR'].iloc[i]
                        })
        
        # Rank by RS
        candidate_pool.sort(key=lambda x: x['rs_score'], reverse=True)
        candidates = candidate_pool  # We will apply slot limits in the loop with replacement logic

        entries_placed = 0
        for c in candidates:
            if entries_placed >= config.MAX_ENTRIES_PER_DAY:
                logger.info(f"Max entries per day ({config.MAX_ENTRIES_PER_DAY}) reached. Stopping.")
                break

            # Duplicate prevention
            if any(t['symbol'] == c['symbol'] for t in current_portfolio):
                continue
            
            is_replacement = False
            weakest_holding = None

            # Check Slots
            if len(current_portfolio) >= config.MAX_POSITIONS:
                # Try Replacement Logic
                current_portfolio.sort(key=lambda x: x.get('rs_score', -999))
                weakest_holding = current_portfolio[0]
                
                if c['rs_score'] > weakest_holding.get('rs_score', -999) + 0.2:
                    logger.info(f"SIGNAL: {c['symbol']} (RS={c['rs_score']:.2f}) is significantly stronger than {weakest_holding['symbol']} (RS={weakest_holding.get('rs_score', 0):.2f}). Attempting replacement.")
                    is_replacement = True
                else:
                    continue # No slot and not strong enough to replace

            # Size position
            qty = portfolio.calculate_qty(capital, c['price'], c['atr'], current_risk_pct)
            if qty <= 0:
                continue

            required_capital = qty * c['price']
            
            # For replacement, we assume released cash from sell will cover the buy
            # But let's check current cash + expected release
            if not is_replacement:
                if (capital - required_capital) < min_cash:
                    logger.info(f"Skipping {c['symbol']}: Insufficient cash buffer.")
                    continue
            
            # --- EXECUTION ---
            if is_replacement:
                logger.info(f"REPLACING {weakest_holding['symbol']} with {c['symbol']}")
                if not dry_run:
                    # 1. Cancel GTT
                    orders.cancel_gtt(kite, weakest_holding.get('gtt_id'))
                    # 2. Sell Weakest
                    sell_id = orders.place_sell(kite, weakest_holding['symbol'], weakest_holding['qty'])
                    if sell_id:
                        orders.verify_order(kite, sell_id)
                    # 3. Remove from state
                    current_portfolio.remove(weakest_holding)
                    # Note: We don't wait for cash to settle as NSE/Kite allow 80% immediate reuse
                    capital += weakest_holding['qty'] * c['price'] # Approximate for internal tracking
                else:
                    logger.info(f"[DRY RUN] SELL: {weakest_holding['symbol']} for replacement.")
                    current_portfolio.remove(weakest_holding)

            # Price sanity check
            live_price = price_sanity_check(kite, c['symbol'], c['price']) if not dry_run else c['price']
            if live_price is None:
                continue

            sl_price = live_price - (config.SL_ATR_MULT * c['atr'])
            target_price = live_price + (config.TARGET_ATR_MULT * c['atr'])

            # Calculate risk-free partial qty for GTT target leg
            if live_price > sl_price:
                sell_fraction = (live_price - sl_price) / (target_price - sl_price)
                partial_qty = max(1, int(qty * sell_fraction))
            else:
                partial_qty = qty // 2

            # Place order
            if not dry_run:
                order_id = orders.place_buy(kite, c['symbol'], qty)
                if not order_id:
                    continue
                filled = orders.verify_order(kite, order_id)
                if not filled:
                    continue

                fill_price = filled.get('average_price', live_price)

                # Place GTT OCO
                gtt_id = orders.place_gtt_oco(
                    kite, c['symbol'], qty, sl_price, target_price, fill_price, partial_qty
                )
            else:
                logger.info(f"[DRY RUN] BUY: {c['symbol']} x {qty} @ {live_price:.2f} | SL={sl_price:.2f} | Target={target_price:.2f}")
                fill_price = live_price
                gtt_id = None

            trade = {
                "symbol": c['symbol'],
                "entry_price": fill_price,
                "qty": qty,
                "sl": sl_price,
                "initial_sl": sl_price,
                "atr": c['atr'],
                "partial_done": False,
                "entry_date": current_date,
                "gtt_id": gtt_id,
                "rs_score": c['rs_score']
            }

            current_portfolio.append(trade)
            capital -= required_capital
            entries_placed += 1

            entries_today.append({"symbol": c['symbol'], "qty": qty, "price": fill_price})
            notifications.send_trade_alert("BUY", c['symbol'], qty, fill_price, sl_price, target_price)

        # ── Step 9: Save State ──
        logger.info("Step 9: Saving state...")
        # Clean internal fields before saving
        for t in current_portfolio:
            t.pop('_prev_sl', None)
        state.save_state(current_portfolio, capital)
        state.cleanup_old_backups()

        # ── Step 10: Daily Summary & Report Update ──
        logger.info("Step 10: Sending daily summary & updating live report...")
        total_equity = capital + sum(
            t['qty'] * price_data[t['symbol']]['close'].iloc[-1]
            for t in current_portfolio if t['symbol'] in price_data
        )
        
        # Update live performance log for dashboard
        live_report_path = os.path.join(config.REPORTS_DIR, "live_equity.csv")
        new_row = pd.DataFrame([{
            "date": current_date.strftime("%Y-%m-%d"),
            "equity": round(total_equity, 2),
            "cash": round(capital, 2),
            "deployed": round(total_equity - capital, 2),
            "positions_count": len(current_portfolio)
        }])
        
        if not os.path.exists(live_report_path):
            new_row.to_csv(live_report_path, index=False)
        else:
            new_row.to_csv(live_report_path, mode='a', header=False, index=False)

        notifications.send_daily_summary(entries_today, exits_today, current_portfolio, capital, total_equity)

        logger.info(f"Run complete: {len(entries_today)} entries, {len(exits_today)} exits, Equity={total_equity:,.2f}")

    except Exception as e:
        logger.exception(f"CRITICAL ERROR: {e}")
        notifications.send_error_alert(f"Critical error: {str(e)}")

    # ── Step 11: Shutdown ──
    shutdown_ec2(dry_run)


def shutdown_ec2(dry_run=False):
    """Shutdown the EC2 instance after execution."""
    if dry_run:
        logger.info("[DRY RUN] Would sync and shutdown EC2 now.")
        return
    
    # Sync reports to GitHub so they are available locally
    sync_reports_to_git()
    
    logger.info("Shutting down EC2 instance...")
    notifications.send_shutdown_msg()

    try:
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
    except Exception as e:
        logger.error(f"Shutdown command failed: {e}")

def sync_reports_to_git():
    """Commit and push updated reports to GitHub before shutdown."""
    logger.info("Syncing reports to GitHub...")
    try:
        # Add only the reports folder
        # Add reports, logs, and diagnostic files
        subprocess.run(["git", "add", "project/reports/*.csv", "project/reports/*.log", "project/logs/*.log"], check=True)
        
        # Commit with today's date
        date_str = datetime.now().strftime("%Y-%m-%d")
        msg = f"Auto-update reports: {date_str}"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        
        # Push to remote
        subprocess.run(["git", "push"], check=True)
        logger.info("Reports synced successfully!")
    except Exception as e:
        logger.warning(f"Git sync skipped or failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Trading Bot")
    parser.add_argument("--dry-run", action="store_true", help="Run without placing real orders")
    args = parser.parse_args()

    run(dry_run=args.dry_run)
