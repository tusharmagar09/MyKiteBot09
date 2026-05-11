"""
auto_login.py — Fully automated Kite Connect login using pyotp.
Generates a fresh access_token daily without any manual browser interaction.
"""
import os
import sys
import time
import logging
import requests
import pyotp
from datetime import datetime
from kiteconnect import KiteConnect

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger("auto_login")


def auto_login():
    """
    Automates the full Kite Connect login flow. 
    Caches token to prevent multiple logins (dual session issues).
    """
    # Check for existing token from today
    if os.path.exists(config.TOKEN_FILE):
        mod_time = os.path.getmtime(config.TOKEN_FILE)
        if datetime.fromtimestamp(mod_time).date() == datetime.now().date():
            try:
                with open(config.TOKEN_FILE, "r") as f:
                    cached_token = f.read().strip()
                
                kite = KiteConnect(api_key=config.API_KEY)
                kite.set_access_token(cached_token)
                
                # Verify if token is still valid
                kite.profile()
                logger.info("Using cached access token from today. (No fresh login required)")
                return kite
            except Exception:
                logger.info("Cached token invalid or expired. Proceeding with fresh login...")

    api_key = config.API_KEY
    api_secret = config.API_SECRET
    user_id = config.KITE_USER_ID
    password = config.KITE_PASSWORD
    totp_secret = config.KITE_TOTP_SECRET

    if not all([api_key, api_secret, user_id, password, totp_secret]):
        raise Exception("Missing credentials in .env file. Check API_KEY, API_SECRET, KITE_USER_ID, KITE_PASSWORD, KITE_TOTP_SECRET.")

    session = requests.Session()

    # --- Step 1: Login with user_id and password ---
    logger.info(f"Logging in as {user_id}...")
    try:
        login_resp = session.post(
            "https://kite.zerodha.com/api/login",
            data={"user_id": user_id, "password": password},
            timeout=30
        )
        login_data = login_resp.json()

        if login_data.get("status") != "success":
            raise Exception(f"Kite Login failed: {login_data.get('message', 'Unknown error')}")

        request_id = login_data["data"]["request_id"]
        logger.info("Step 1/4: Login successful.")
    except Exception as e:
        raise Exception(f"Login request failed: {e}")

    # --- Step 2: Submit TOTP for two-factor auth ---
    try:
        # Clean the TOTP secret: remove spaces, dashes, and ensure uppercase
        clean_secret = totp_secret.strip().replace(" ", "").replace("-", "").upper()
        totp = pyotp.TOTP(clean_secret)
        totp_value = totp.now()
        logger.info(f"Generated TOTP code: {totp_value}")

        # Try different 2FA types (Kite may use "totp" or "app" depending on setup)
        twofa_success = False
        for twofa_type in ["totp", "app"]:
            logger.info(f"Trying 2FA type: '{twofa_type}'...")
            twofa_resp = session.post(
                "https://kite.zerodha.com/api/twofa",
                data={
                    "user_id": user_id,
                    "request_id": request_id,
                    "twofa_value": totp_value,
                    "twofa_type": twofa_type
                },
                timeout=30
            )
            twofa_data = twofa_resp.json()

            if twofa_data.get("status") == "success":
                twofa_success = True
                logger.info(f"Step 2/4: Two-factor auth successful (type='{twofa_type}').")
                break
            else:
                logger.warning(f"2FA type '{twofa_type}' failed: {twofa_data.get('message', 'Unknown')}")

        if not twofa_success:
            # Retry once with a fresh TOTP code
            logger.warning("All 2FA types failed. Retrying with fresh TOTP code...")
            time.sleep(2)
            totp_value = totp.now()
            for twofa_type in ["totp", "app"]:
                twofa_resp = session.post(
                    "https://kite.zerodha.com/api/twofa",
                    data={
                        "user_id": user_id,
                        "request_id": request_id,
                        "twofa_value": totp_value,
                        "twofa_type": twofa_type
                    },
                    timeout=30
                )
                twofa_data = twofa_resp.json()
                if twofa_data.get("status") == "success":
                    twofa_success = True
                    logger.info(f"Step 2/4: Two-factor auth successful on retry (type='{twofa_type}').")
                    break

        if not twofa_success:
            raise Exception(f"2FA FAILED with all types: {twofa_data.get('message', 'Unknown error')}")
    except Exception as e:
        raise Exception(f"2FA request failed: {e}")

    # --- Step 3: Get request_token via redirect ---
    try:
        from urllib.parse import urlparse, parse_qs

        # Use kite.zerodha.com (same domain as login) for proper cookie handling
        connect_url = f"https://kite.zerodha.com/connect/login?api_key={api_key}&v=3"
        
        # First try: follow all redirects and check the final URL
        logger.info("Following redirect chain to get request_token...")
        redirect_resp = session.get(connect_url, allow_redirects=True, timeout=30)
        
        # Check if request_token is in the final URL
        final_url = redirect_resp.url
        parsed = urlparse(final_url)
        params = parse_qs(parsed.query)
        request_token = params.get("request_token", [None])[0]
        
        # If not found in final URL, try without following redirects
        if not request_token:
            logger.info("Trying without auto-redirect...")
            redirect_resp = session.get(connect_url, allow_redirects=False, timeout=30)
            
            if redirect_resp.status_code in (301, 302, 303, 307, 308):
                location = redirect_resp.headers.get("Location", "")
                parsed = urlparse(location)
                params = parse_qs(parsed.query)
                request_token = params.get("request_token", [None])[0]
                
                # Sometimes need to follow one more redirect
                if not request_token and location:
                    logger.info(f"Following redirect to: {location[:80]}...")
                    resp2 = session.get(location, allow_redirects=False, timeout=30)
                    if resp2.status_code in (301, 302, 303, 307, 308):
                        loc2 = resp2.headers.get("Location", "")
                        parsed2 = urlparse(loc2)
                        params2 = parse_qs(parsed2.query)
                        request_token = params2.get("request_token", [None])[0]

        if not request_token:
            raise Exception(f"Could not extract request_token. Final URL: {final_url}. Check your Redirect URL.")

        logger.info("Step 3/4: Got request_token.")
    except Exception as e:
        raise Exception(f"Redirect capture failed: {e}")

    # --- Step 4: Exchange request_token for access_token ---
    try:
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]

        kite.set_access_token(access_token)

        # Save token to file for other modules
        with open(config.TOKEN_FILE, "w") as f:
            f.write(access_token)

        logger.info("Step 4/4: Access token generated and saved.")
        return kite

    except Exception as e:
        raise Exception(f"Session generation failed: {e}")
