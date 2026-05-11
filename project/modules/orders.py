"""
orders.py — Order execution layer for Kite Connect.
Handles BUY, SELL, GTT OCO placement, cancellation, and trailing updates.
"""
import logging
import time

logger = logging.getLogger("orders")


def place_buy(kite, symbol, qty, exchange="NSE"):
    """Place a MARKET BUY order. Returns order_id or None."""
    import config
    if config.DRY_RUN:
        logger.info(f"[DRY RUN] Would BUY {symbol} x {qty}")
        return f"DRY_BUY_{symbol}_{int(time.time())}"
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=symbol,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=qty,
            product=kite.PRODUCT_CNC,
            order_type=kite.ORDER_TYPE_MARKET
        )
        logger.info(f"BUY order placed: {symbol} x {qty} | order_id={order_id}")
        return order_id
    except Exception as e:
        logger.error(f"BUY order FAILED for {symbol} x {qty}: {e}")
        return None


def place_sell(kite, symbol, qty, exchange="NSE"):
    """Place a MARKET SELL order. Returns order_id or None."""
    import config
    if config.DRY_RUN:
        logger.info(f"[DRY RUN] Would SELL {symbol} x {qty}")
        return f"DRY_SELL_{symbol}_{int(time.time())}"
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=symbol,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=qty,
            product=kite.PRODUCT_CNC,
            order_type=kite.ORDER_TYPE_MARKET
        )
        logger.info(f"SELL order placed: {symbol} x {qty} | order_id={order_id}")
        return order_id
    except Exception as e:
        logger.error(f"SELL order FAILED for {symbol} x {qty}: {e}")
        return None


def place_gtt_oco(kite, symbol, qty, sl_trigger, target_trigger, last_price, 
                  partial_qty=None, exchange="NSE"):
    """
    Place a GTT OCO (One Cancels Other) order with two legs:
      Leg 1 (Stop-Loss): Sell full qty at sl_trigger
      Leg 2 (Target/Partial): Sell partial_qty at target_trigger
    
    If partial_qty is None, both legs sell full qty (used after partial is already done).
    Returns gtt_id or None.
    """
    if partial_qty is None:
        partial_qty = qty

    import config
    if config.DRY_RUN:
        logger.info(f"[DRY RUN] Would place GTT OCO: {symbol} | SL={sl_trigger:.1f} Target={target_trigger:.1f}")
        return f"DRY_GTT_OCO_{symbol}"

    try:
        # Kite GTT OCO requires trigger_values as [lower, upper]
        # and corresponding orders list
        gtt_id = kite.place_gtt(
            trigger_type=kite.GTT_TYPE_OCO,
            tradingsymbol=symbol,
            exchange=exchange,
            trigger_values=[round(sl_trigger, 1), round(target_trigger, 1)],
            last_price=round(last_price, 1),
            orders=[
                {
                    "exchange": exchange,
                    "tradingsymbol": symbol,
                    "transaction_type": "SELL",
                    "quantity": qty,
                    "price": round(sl_trigger, 1),
                    "order_type": "LIMIT",
                    "product": "CNC"
                },
                {
                    "exchange": exchange,
                    "tradingsymbol": symbol,
                    "transaction_type": "SELL",
                    "quantity": partial_qty,
                    "price": round(target_trigger, 1),
                    "order_type": "LIMIT",
                    "product": "CNC"
                }
            ]
        )
        logger.info(f"GTT OCO placed: {symbol} | SL={sl_trigger:.1f} Target={target_trigger:.1f} | gtt_id={gtt_id}")
        return gtt_id
    except Exception as e:
        logger.error(f"GTT OCO FAILED for {symbol}: {e}")
        return None


def place_gtt_single(kite, symbol, qty, sl_trigger, last_price, exchange="NSE"):
    """
    Place a single-leg GTT (Stop-Loss only).
    Used after partial exit is done — only trailing SL remains.
    Returns gtt_id or None.
    """
    import config
    if config.DRY_RUN:
        logger.info(f"[DRY RUN] Would place GTT Single: {symbol} | SL={sl_trigger:.1f}")
        return f"DRY_GTT_SL_{symbol}"

    try:
        gtt_id = kite.place_gtt(
            trigger_type=kite.GTT_TYPE_SINGLE,
            tradingsymbol=symbol,
            exchange=exchange,
            trigger_values=[round(sl_trigger, 1)],
            last_price=round(last_price, 1),
            orders=[
                {
                    "exchange": exchange,
                    "tradingsymbol": symbol,
                    "transaction_type": "SELL",
                    "quantity": qty,
                    "price": round(sl_trigger, 1),
                    "order_type": "LIMIT",
                    "product": "CNC"
                }
            ]
        )
        logger.info(f"GTT Single placed: {symbol} | SL={sl_trigger:.1f} | gtt_id={gtt_id}")
        return gtt_id
    except Exception as e:
        logger.error(f"GTT Single FAILED for {symbol}: {e}")
        return None


def cancel_gtt(kite, gtt_id):
    """Cancel an existing GTT order."""
    if gtt_id is None:
        return True
    try:
        kite.delete_gtt(gtt_id)
        logger.info(f"GTT cancelled: gtt_id={gtt_id}")
        return True
    except Exception as e:
        logger.warning(f"GTT cancel failed (may already be triggered): gtt_id={gtt_id} | {e}")
        return False


def update_trailing_gtt(kite, trade, new_sl, current_price):
    """
    Cancel the old GTT and place a new one with the updated trailing SL.
    Updates the trade dict in-place with the new gtt_id.
    """
    old_gtt_id = trade.get('gtt_id')
    cancel_gtt(kite, old_gtt_id)
    time.sleep(0.3)  # Brief pause between cancel and new placement

    symbol = trade['symbol']
    qty = trade['qty']

    if trade.get('partial_done', False):
        # After partial, only trailing SL remains
        new_gtt_id = place_gtt_single(kite, symbol, qty, new_sl, current_price)
    else:
        # Full OCO with updated SL + original target
        import config
        target = trade['entry_price'] + (config.TARGET_ATR_MULT * trade['atr'])
        # Calculate risk-free partial qty
        if current_price > trade['initial_sl']:
            sell_fraction = (trade['entry_price'] - trade['initial_sl']) / (current_price - trade['initial_sl'])
            partial_qty = max(1, int(qty * sell_fraction))
        else:
            partial_qty = qty // 2
        new_gtt_id = place_gtt_oco(kite, symbol, qty, new_sl, target, current_price, partial_qty)

    trade['gtt_id'] = new_gtt_id
    trade['sl'] = new_sl
    logger.info(f"Trailing GTT updated: {symbol} | new SL={new_sl:.1f} | gtt_id={new_gtt_id}")
    return new_gtt_id


def verify_order(kite, order_id, max_retries=3):
    """Check if an order was successfully executed. Handles Dry Run IDs."""
    if str(order_id).startswith("DRY_"):
        logger.info(f"[DRY RUN] Simulated order {order_id} verified as COMPLETE")
        return {'status': 'COMPLETE', 'average_price': 0, 'tradingsymbol': order_id.split('_')[-1]}

    for attempt in range(max_retries):
        try:
            time.sleep(1)
            order_history = kite.order_history(order_id)
            latest = order_history[-1]
            if latest['status'] == 'COMPLETE':
                logger.info(f"Order {order_id} COMPLETE: {latest['tradingsymbol']} @ {latest['average_price']}")
                return latest
            elif latest['status'] == 'REJECTED':
                logger.error(f"Order {order_id} REJECTED: {latest.get('status_message', 'Unknown')}")
                return None
        except Exception as e:
            logger.warning(f"Order verification attempt {attempt+1} failed: {e}")
            time.sleep(2)
    
    logger.warning(f"Order {order_id} status unclear after {max_retries} attempts.")
    return None
