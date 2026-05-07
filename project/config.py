import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# --- API Configuration (from .env) ---
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")
KITE_USER_ID = os.getenv("KITE_USER_ID", "")
KITE_PASSWORD = os.getenv("KITE_PASSWORD", "")
KITE_TOTP_SECRET = os.getenv("KITE_TOTP_SECRET", "")

# --- Telegram (from .env) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "access_token.txt")
INSTRUMENTS_FILE = os.path.join(os.path.dirname(BASE_DIR), "instruments.csv")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
STATE_FILE = os.path.join(BASE_DIR, "state", "portfolio_state.json")
TRADES_HISTORY_FILE = os.path.join(BASE_DIR, "state", "trades_history.csv")
LOG_DIR = os.path.join(BASE_DIR, "logs")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# Ensure directories exist
for d in [DATA_DIR, REPORTS_DIR, LOG_DIR, BACKUP_DIR, os.path.join(BASE_DIR, "state")]:
    os.makedirs(d, exist_ok=True)

# --- Strategy Parameters ---
INITIAL_CAPITAL = 1000000
MAX_DEPLOYMENT = 1.0     # 100% capital deployed
NORMAL_RISK_PER_TRADE = 0.01    # 1.0% risk (Nifty 50 < 200 EMA)
HIGH_RISK_PER_TRADE = 0.0125    # 1.25% risk (Nifty 50 > 200 EMA)
MAX_POSITIONS = 12
MAX_ENTRIES_PER_DAY = 5          # Circuit breaker
MAX_HOLDING_DAYS = 42            # 6 weeks time stop
PRICE_DEVIATION_LIMIT = 0.05    # 5% sanity check

SL_ATR_MULT = 1.2
TARGET_ATR_MULT = 3.5
TRAIL_ATR_MULT = 2.5

TIMEFRAME = "day"

# --- Benchmarks ---
MARKET_INDEX_SYMBOL = "NIFTY 50"
MARKET_INDEX_TOKEN = 256265
RS_INDEX_SYMBOL = "NIFTY 500"
RS_INDEX_TOKEN = 268041

# --- Backtest-only (not used in live) ---
START_DATE = "2021-01-01"
END_DATE = "2026-03-31"
