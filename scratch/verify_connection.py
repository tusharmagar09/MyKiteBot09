import os
import sys
import logging
from datetime import datetime

# Add project to path
sys.path.append(os.path.join(os.getcwd(), "project"))
import config
from modules import auto_login

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("verify")

def verify():
    logger.info("--- Kite Connectivity Diagnostic ---")
    
    try:
        # Step 1: Attempt Login
        logger.info("Attempting to initialize Kite session...")
        kite = auto_login.auto_login()
        
        if not kite:
            logger.error("FAILED: Could not initialize Kite instance. Check your .env file.")
            return

        # Step 2: Fetch Profile
        profile = kite.profile()
        logger.info(f"SUCCESS: Connected as {profile.get('user_name')} ({profile.get('user_id')})")

        # Step 3: Fetch Real-time Quote
        logger.info("Fetching real-time quote for NIFTY 50...")
        quote = kite.quote("NSE:NIFTY 50")
        ltp = quote.get("NSE:NIFTY 50", {}).get("last_price")
        
        if ltp:
            logger.info(f"SUCCESS: NIFTY 50 Spot Price = ₹{ltp:,.2f}")
            logger.info("--- DIAGNOSTIC COMPLETE: SYSTEM READY ---")
        else:
            logger.warning("WARNING: Connected but could not fetch price. Market might be closed or API restricted.")

    except Exception as e:
        logger.error(f"CRITICAL ERROR during verification: {e}")

if __name__ == "__main__":
    verify()
