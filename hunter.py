import requests
import os

# --- CONFIGURATION ---
# Get the Helius API key from GitHub Secrets.
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
if not HELIUS_API_KEY:
    print("Error: HELIUS_API_KEY secret not found!")
    exit(1)

# The Helius API URL. The key is passed as a query parameter.
api_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# The address for Wrapped SOL (SOL).
token_address = "So11111111111111111111111111111111111111112"

# --- API REQUEST ---
# Helius uses POST requests with a JSON body to specify what you want.
headers = {'Content-Type': 'application/json'}
payload = {
    "jsonrpc": "2.0",
    "id": "gem-hunter-test",
    "method": "getAsset",
    "params": {
        "id": "So11111111111111111111111111111111111111112"
    }
}

# --- EXECUTION & RESULTS ---
print(f"Attempting to fetch asset data for {token_address} from Helius...")

try:
    # Note: We are using requests.post() now instead of requests.get()
    response = requests.post(api_url, headers=headers, json=payload)
    response.raise_for_status() # Check for HTTP errors

    print("Success! Data received from Helius.")
    data = response.json()
    print("--- Helius Asset Data (Sample) ---")
    # The result is very long, so let's just print part of it
    if 'result' in data:
        print(f"Interface: {data['result'].get('interface')}")
        print(f"Owner: {data['result'].get('owner')}")
        print(f"Content (Metadata): {data['result'].get('content')}")
    else:
        print(data) # Print the whole response if it's not what we expect
    print("------------------------------------")

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error occurred: {err}")
    print("Response Text:", response.text)
except Exception as err:
    print(f"An other error occurred: {err}")
