import os
import sys
import json
import logging

# Add project to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import auto_login

def debug_margins():
    print("Connecting to Kite...")
    kite = auto_login.auto_login()
    if not kite:
        print("Login failed!")
        return

    print("Fetching full margin details...")
    margins = kite.margins()
    
    print("\n--- EQUITY MARGINS ---")
    equity = margins.get("equity", {})
    print(json.dumps(equity, indent=4))
    
    available = equity.get("available", {})
    print("\n--- AVAILABLE BREAKDOWN ---")
    print(f"Live Balance:  {available.get('live_balance')}")
    print(f"Cash:          {available.get('cash')}")
    print(f"Intraday Payin: {available.get('intraday_payin')}")
    
    print("\n--- NET FIELD ---")
    print(f"Net: {equity.get('net')}")

if __name__ == "__main__":
    debug_margins()
