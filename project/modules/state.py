"""
state.py — Persistent portfolio state management.
Saves/loads portfolio and capital to JSON so it survives EC2 restarts.
Includes backup and reconciliation logic.
"""
import os
import sys
import json
import shutil
import logging
from datetime import datetime, date

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger("state")


class DateEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle date/datetime objects."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)


def save_state(portfolio, capital):
    """Save portfolio state to JSON with atomic write."""
    state = {
        "capital": round(capital, 2),
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions": portfolio
    }

    tmp_path = config.STATE_FILE + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2, cls=DateEncoder)
        # Atomic rename to prevent corruption
        shutil.move(tmp_path, config.STATE_FILE)
        logger.info(f"State saved: {len(portfolio)} positions, capital={capital:.2f}")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def load_state():
    """Load portfolio state from JSON. Returns (portfolio_list, capital)."""
    if not os.path.exists(config.STATE_FILE):
        logger.info("No existing state file found. Starting fresh.")
        return [], config.INITIAL_CAPITAL

    try:
        with open(config.STATE_FILE, "r") as f:
            state = json.load(f)

        portfolio = state.get("positions", [])
        capital = state.get("capital", config.INITIAL_CAPITAL)

        # Convert date strings back to date objects
        for trade in portfolio:
            if isinstance(trade.get('entry_date'), str):
                trade['entry_date'] = pd.Timestamp(trade['entry_date'])

        logger.info(f"State loaded: {len(portfolio)} positions, capital={capital:.2f}, last_run={state.get('last_run', 'unknown')}")
        return portfolio, capital

    except Exception as e:
        logger.error(f"Failed to load state: {e}. Starting fresh.")
        return [], config.INITIAL_CAPITAL


def backup_state():
    """Create a timestamped backup of the current state file."""
    if not os.path.exists(config.STATE_FILE):
        return

    today = datetime.now().strftime("%Y-%m-%d")
    backup_path = os.path.join(config.BACKUP_DIR, f"state_{today}.json")

    try:
        shutil.copy2(config.STATE_FILE, backup_path)
        logger.info(f"State backed up to: {backup_path}")
    except Exception as e:
        logger.error(f"Backup failed: {e}")


def backup_trades_history():
    """Create a timestamped backup of the trades history."""
    if not os.path.exists(config.TRADES_HISTORY_FILE):
        return

    today = datetime.now().strftime("%Y-%m-%d")
    backup_path = os.path.join(config.BACKUP_DIR, f"trades_history_{today}.csv")

    try:
        shutil.copy2(config.TRADES_HISTORY_FILE, backup_path)
        logger.info(f"Trades history backed up to: {backup_path}")
    except Exception as e:
        logger.error(f"Trades history backup failed: {e}")


def log_trade(trade_record):
    """Append a completed trade to the persistent trades history CSV."""
    try:
        df = pd.DataFrame([trade_record])
        header = not os.path.exists(config.TRADES_HISTORY_FILE)
        df.to_csv(config.TRADES_HISTORY_FILE, mode='a', header=header, index=False)
        logger.info(f"Trade logged: {trade_record['symbol']} | PnL={trade_record.get('pnl', 0):.2f}")
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")


def reconcile(kite, portfolio):
    """
    Cross-check local portfolio state with actual Kite holdings.
    Logs any discrepancies for manual review.
    """
    try:
        holdings = kite.holdings()
        kite_holdings = {}
        for h in holdings:
            if h['quantity'] > 0:
                kite_holdings[h['tradingsymbol']] = h['quantity']

        local_holdings = {t['symbol']: t['qty'] for t in portfolio}

        # Check for discrepancies
        all_symbols = set(list(kite_holdings.keys()) + list(local_holdings.keys()))

        discrepancies = []
        for symbol in all_symbols:
            kite_qty = kite_holdings.get(symbol, 0)
            local_qty = local_holdings.get(symbol, 0)
            if kite_qty != local_qty:
                discrepancies.append({
                    "symbol": symbol,
                    "kite_qty": kite_qty,
                    "local_qty": local_qty,
                    "diff": kite_qty - local_qty
                })

        if discrepancies:
            logger.warning(f"RECONCILIATION MISMATCH: {len(discrepancies)} discrepancies found!")
            for d in discrepancies:
                logger.warning(f"  {d['symbol']}: Kite={d['kite_qty']}, Local={d['local_qty']}, Diff={d['diff']}")
        else:
            logger.info("Reconciliation OK: Local state matches Kite holdings.")

        return discrepancies

    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        return []


def cleanup_old_backups(days_to_keep=90):
    """Remove backup files older than specified days."""
    cutoff = datetime.now().timestamp() - (days_to_keep * 86400)
    removed = 0
    try:
        for f in os.listdir(config.BACKUP_DIR):
            fpath = os.path.join(config.BACKUP_DIR, f)
            if os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
                removed += 1
        if removed:
            logger.info(f"Cleaned up {removed} old backup files.")
    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
