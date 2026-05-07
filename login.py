from kiteconnect import KiteConnect

API_KEY = "qzlyy9b8wnyijett"
API_SECRET = "rv4c15s9mh39mvsw2e7v1d09j5xxzudq"

kite = KiteConnect(api_key=API_KEY)

# Step 1: Get login URL
print("Open this URL in browser:")
print(kite.login_url())

# Step 2: Paste request_token after login
request_token = input("Enter request token here: ")

# Step 3: Generate access token
try:
    data = kite.generate_session(request_token, api_secret=API_SECRET)
    access_token = data["access_token"]
    print("\nACCESS TOKEN:")
    print(access_token)
    
    # Save token to file
    with open("access_token.txt", "w") as f:
        f.write(access_token)
    print("Token successfully saved to access_token.txt")
except Exception as e:
    print(f"Error generating token: {e}")