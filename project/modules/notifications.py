"""
notifications.py — Telegram notification system for trade alerts and daily summaries.
"""
import os
import sys
import logging
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger("notifications")

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def _send_message(text, parse_mode="HTML"):
    """Send a message to the configured Telegram chat."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured. Skipping notification.")
        return False

    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": parse_mode
            },
            timeout=10
        )
        if resp.status_code == 200:
            return True
        else:
            logger.error(f"Telegram send failed: {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram request failed: {e}")
        return False


def send_trade_alert(action, symbol, qty, price, sl=None, target=None):
    """Send an instant alert for a single trade action."""
    emoji = "🟢" if action == "BUY" else "🔴"
    msg = f"{emoji} <b>{action}: {symbol}</b>\n"
    msg += f"Qty: {qty} | Price: ₹{price:,.2f}\n"
    if sl:
        msg += f"SL: ₹{sl:,.2f}\n"
    if target:
        msg += f"Target: ₹{target:,.2f}\n"
    
    _send_message(msg)


def send_daily_summary(entries_today, exits_today, portfolio, capital, total_equity):
    """Send the end-of-day summary with full portfolio overview."""
    msg = "📊 <b>DAILY TRADING SUMMARY</b>\n"
    msg += f"{'='*30}\n\n"

    # Entries
    if entries_today:
        msg += f"🟢 <b>New Entries ({len(entries_today)}):</b>\n"
        for e in entries_today:
            msg += f"  • {e['symbol']} x {e['qty']} @ ₹{e['price']:,.2f}\n"
        msg += "\n"
    else:
        msg += "🟢 <b>New Entries:</b> None\n\n"

    # Exits
    if exits_today:
        msg += f"🔴 <b>Exits ({len(exits_today)}):</b>\n"
        for e in exits_today:
            pnl = e.get('pnl', 0)
            emoji = "✅" if pnl >= 0 else "❌"
            msg += f"  {emoji} {e['symbol']} x {e['qty']} @ ₹{e['price']:,.2f} | PnL: ₹{pnl:,.2f}\n"
        msg += "\n"
    else:
        msg += "🔴 <b>Exits:</b> None\n\n"

    # Open Positions
    msg += f"📂 <b>Open Positions ({len(portfolio)}/{config.MAX_POSITIONS}):</b>\n"
    for t in portfolio:
        msg += f"  • {t['symbol']} x {t['qty']} @ ₹{t['entry_price']:,.2f} | SL: ₹{t['sl']:,.2f}\n"

    if not portfolio:
        msg += "  No open positions.\n"

    msg += f"\n💰 <b>Cash:</b> ₹{capital:,.2f}\n"
    msg += f"💼 <b>Total Equity:</b> ₹{total_equity:,.2f}\n"

    _send_message(msg)


def send_error_alert(error_msg):
    """Send a critical error alert."""
    msg = f"🚨 <b>BOT ERROR</b>\n\n{error_msg}"
    _send_message(msg)


def send_startup_msg():
    """Notify that the bot has started."""
    msg = "🤖 <b>Trading Bot Started</b>\nScanning market..."
    _send_message(msg)


def send_holiday_msg(reason=""):
    """Notify that market is closed."""
    msg = f"🏖️ <b>Market Closed</b>\nReason: {reason}. Shutting down."
    _send_message(msg)


def send_shutdown_msg():
    """Notify clean shutdown."""
    msg = "✅ <b>Bot Shutdown</b>\nAll operations complete. EC2 stopping."
    _send_message(msg)
