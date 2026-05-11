"""
morning_check.py — System Health & Margin Verification.
Runs at 9:15 AM IST to ensure the system is ready for the day.
Alerts the user if funds are missing (e.g., due to SEBI settlement).
"""
import os
import sys
import logging
from datetime import datetime

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from modules import auto_login, notifications, state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("morning_check")

def run_check():
    logger.info("--- Starting Morning Health Check ---")
    
    try:
        # 1. Verify Connectivity & Login
        kite = auto_login.auto_login()
        if not kite:
            notifications.send_error_alert("❌ Morning Check FAILED: Could not login to Kite API.")
            return

        profile = kite.profile()
        user_name = profile.get('user_name', 'User')

        margins = kite.margins()
        equity_margins = margins.get("equity", {})
        available_margin = equity_margins.get("available", {}).get("live_balance", 
                           equity_margins.get("net", 0))
        
        # 3. Fetch Portfolio Valuation
        holdings = kite.holdings()
        invested_value = sum(h['quantity'] * h['last_price'] for h in holdings)
        
        portfolio_state = state.load_state()
        active_positions = len(portfolio_state)
        
        # 4. Analyze Health (Alert only on Zero/Near-Zero Balance)
        status = "✅ HEALTHY"
        warning_msg = ""
        
        # Alert only if balance is almost zero (SEBI sweep or missing funds)
        if available_margin < 1000:
            status = "⚠️ ACTION REQUIRED"
            warning_msg = (
                f"\n\n🚨 *ALERT: ZERO BALANCE!*\n"
                f"Available Margin: Rs.{available_margin:,.2f}\n"
                f"Please Top-up before 3:00 PM if you wish to allow new entries today."
            )

        # 5. Send Report
        report = (
            f"☀️ <b>MoneyFlow Morning Report</b>\n"
            f"----------------------------------\n"
            f"<b>Status:</b> {status}\n"
            f"<b>User:</b> {user_name}\n"
            f"<b>Available Trading Cash:</b> Rs.{available_margin:,.2f}\n"
            f"<b>Manual Portfolio Value:</b> Rs.{invested_value:,.2f}\n"
            f"<b>Bot Active Positions:</b> {active_positions}/12\n"
            f"{warning_msg}\n"
            f"----------------------------------\n"
            f"Bot is ready for the 3:00 PM Momentum Scan."
        )
        
        notifications.send_custom_msg(report)
        logger.info(f"Morning report sent. Status: {status}")

    except Exception as e:
        logger.error(f"Error during morning check: {e}")
        notifications.send_error_alert(f"❌ Morning Check CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    run_check()
