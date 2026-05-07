from kiteconnect import KiteConnect
from datetime import datetime, time
from zoneinfo import ZoneInfo
import sys

# 1. Market Time Check
now = datetime.now(ZoneInfo("Asia/Kolkata")).time()
if not (time(9, 15) <= now <= time(15, 30)):
    print("Market closed – skipping script")
    sys.exit()

print("Market is open. Proceeding with order...")

# 2. Connect
API_KEY = "qzlyy9b8wnyijett"

# Read access token from file
try:
    with open("access_token.txt", "r") as f:
        ACCESS_TOKEN = f.read().strip()
except FileNotFoundError:
    print("Error: access_token.txt not found. Please run login.py first.")
    sys.exit()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# 3. Connection Check
profile = kite.profile()
print("Connected:", profile["user_name"])

# 4. Fetch Price
ltp = kite.ltp("NSE:RELIANCE")["NSE:RELIANCE"]["last_price"]
buy_price = round(ltp * 1.002, 1)

print(f"LTP: {ltp} | Buy Price: {buy_price}")

# 5. Funds Check
margins = kite.margins()['equity']
available_cash = margins.get('net', 0)
print(f"Available Funds: {available_cash}")
if available_cash < buy_price:
    print("Insufficient funds")
    sys.exit()

# 6. Duplicate Check
holdings = kite.holdings()
for h in holdings:
    if h['tradingsymbol'] == "RELIANCE":
        print("Already holding RELIANCE")
        sys.exit()

# 7. Place Order
try:
    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NSE,
        tradingsymbol="RELIANCE",
        transaction_type=kite.TRANSACTION_TYPE_BUY,
        quantity=1,
        order_type=kite.ORDER_TYPE_LIMIT,
        price=buy_price,
        product=kite.PRODUCT_CNC
    )
    print("Order placed:", order_id)

    # Added a short delay to allow the exchange to process the order
    import time as t
    t.sleep(2)

    # Step 8: Get executed buy price
    orders = kite.orders()

    buy_price_executed = None

    for o in orders:
        if o['order_id'] == order_id and o['status'] == "COMPLETE":
            buy_price_executed = o['average_price']
            break

    if buy_price_executed is None:
        print("Buy not executed yet. Cannot place GTT.")
        sys.exit()

    print("Buy executed at:", buy_price_executed)

    # Step 9: Define SL & Target
    sl_price = round(buy_price_executed * 0.98, 1)     # 2% SL
    target_price = round(buy_price_executed * 1.04, 1) # 4% Target

    print(f"SL: {sl_price}, Target: {target_price}")

    # Step 10: Place GTT OCO
    gtt_order = kite.place_gtt(
        trigger_type=kite.GTT_TYPE_OCO,
        tradingsymbol="RELIANCE",
        exchange="NSE",
        trigger_values=[sl_price, target_price],
        last_price=buy_price_executed,
        orders=[
            {
                "transaction_type": kite.TRANSACTION_TYPE_SELL,
                "quantity": 1,
                "order_type": kite.ORDER_TYPE_LIMIT,
                "product": kite.PRODUCT_CNC,
                "price": sl_price
            },
            {
                "transaction_type": kite.TRANSACTION_TYPE_SELL,
                "quantity": 1,
                "order_type": kite.ORDER_TYPE_LIMIT,
                "product": kite.PRODUCT_CNC,
                "price": target_price
            }
        ]
    )

    print("GTT OCO placed successfully:", gtt_order)

except Exception as e:
    print("Order failed:", e)