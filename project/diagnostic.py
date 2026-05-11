import os
import sys
import requests
import logging

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Diagnostic")

def check_telegram():
    logger.info("Checking Telegram connectivity...")
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Telegram Bot Token is VALID.")
            return True
        else:
            logger.error(f"❌ Telegram Error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram Connection Failed: {e}")
        return False

def check_kite_access():
    logger.info("Checking Kite Access Token...")
    if os.path.exists(config.TOKEN_FILE):
        with open(config.TOKEN_FILE, "r") as f:
            token = f.read().strip()
            if token:
                logger.info("✅ Access Token found locally.")
                return True
    logger.warning("⚠️ Access Token missing or empty. A fresh login is required.")
    return False

if __name__ == "__main__":
    logger.info("=== MONEY FLOW SYSTEM DIAGNOSTIC ===")
    t_ok = check_telegram()
    k_ok = check_kite_access()
    
    if t_ok and k_ok:
        logger.info("\n✅ Local configuration looks GOOD.")
        logger.info("The issue is likely the AWS Scheduler (EventBridge) or the EC2 Instance not starting.")
    else:
        logger.error("\n❌ Configuration issues found. Check the errors above.")
