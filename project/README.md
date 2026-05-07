# Live Trading Bot — Operations Manual

## Quick Start

### 1. Fill in credentials
```bash
cp .env.example .env
nano .env   # Fill in API_KEY, API_SECRET, USER_ID, PASSWORD, TOTP_SECRET, TELEGRAM tokens
```

### 2. Install dependencies
```bash
pip install kiteconnect pyotp python-dotenv requests pandas numpy
```

### 3. Test with dry-run
```bash
python3 live_bot.py --dry-run
```
This runs the full pipeline without placing real orders. Check logs for output.

### 4. Install systemd service
```bash
sudo cp trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
```

### 5. Setup AWS scheduler
```bash
python3 setup_aws_scheduler.py --instance-id i-YOUR_INSTANCE_ID --region ap-south-1
```

---

## Telegram Bot Setup

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → name it (e.g., "Ashish Trading Bot")
3. Copy the **Bot Token** → paste in `.env` as `TELEGRAM_BOT_TOKEN`
4. Send any message to your new bot
5. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
6. Find your `chat.id` in the response → paste in `.env` as `TELEGRAM_CHAT_ID`

---

## File Structure

```
project/
├── live_bot.py              # Main orchestrator (runs daily)
├── main.py                  # Backtest engine (for research)
├── config.py                # All parameters (reads .env)
├── .env                     # Credentials (NEVER commit)
├── .env.example             # Template
├── trading-bot.service      # systemd service
├── setup_aws_scheduler.py   # AWS EventBridge setup
├── modules/
│   ├── auto_login.py        # Automated Kite login
│   ├── orders.py            # Order placement (BUY, SELL, GTT)
│   ├── state.py             # Persistent portfolio state
│   ├── notifications.py     # Telegram alerts
│   ├── indicators.py        # Technical indicators
│   ├── rs.py                # Relative strength
│   ├── strategy.py          # Entry signals
│   ├── portfolio.py         # Position sizing & exits
│   ├── data.py              # Data fetching (backtest)
│   └── report.py            # Report generation (backtest)
├── state/
│   ├── portfolio_state.json # Current positions
│   └── trades_history.csv   # All completed trades
├── logs/
│   ├── bot_YYYY-MM-DD.log   # Execution log
│   ├── orders_YYYY-MM-DD.log # Order log
│   └── errors_YYYY-MM-DD.log # Error log
├── backups/                 # Daily state backups
├── data/                    # Cached OHLCV data
└── reports/                 # Backtest reports
```

---

## Emergency Procedures

### Manual override — stop the bot
```bash
sudo systemctl stop trading-bot
```

### Manual override — place order
```python
from kiteconnect import KiteConnect
kite = KiteConnect(api_key="xxx")
kite.set_access_token("xxx")
kite.place_order(variety="regular", exchange="NSE", tradingsymbol="SYMBOL",
                 transaction_type="SELL", quantity=100, product="CNC", order_type="MARKET")
```

### Recover from bad state
```bash
cp backups/state_YYYY-MM-DD.json state/portfolio_state.json
```

---

## Monitoring Checklist (Daily)

- [ ] Check Telegram for daily summary
- [ ] Verify no error alerts received
- [ ] Spot-check one position in Kite Console vs state file
- [ ] Confirm EC2 auto-stopped (check AWS Console)
