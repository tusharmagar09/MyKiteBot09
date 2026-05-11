import os
import sys
import logging
import json

# Add project to path
sys.path.append(os.path.join(os.getcwd(), "project"))
from modules import auto_login

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("margins")

def check():
    try:
        kite = auto_login.auto_login()
        margins = kite.margins()
        
        print("\n--- FULL MARGIN REPORT ---")
        print(json.dumps(margins, indent=2))
        
        equity_margins = margins.get("equity", {})
        available = equity_margins.get("available", {})
        
        print("\n--- SUMMARY ---")
        print(f"Cash: {available.get('cash')}")
        print(f"Payin: {available.get('payin')}")
        print(f"Collateral: {available.get('collateral')}")
        print(f"Live Balance: {available.get('live_balance')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
