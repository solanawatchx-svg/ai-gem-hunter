import requests
import os

# --- CONFIGURATION ---
# This line safely gets the API key from the GitHub Secrets we set up.
# It will not work if you run it locally, only in GitHub Actions.
BIRDEYE_API_KEY = os.environ.get('BIRDEYE_API_KEY')

# The address for the dogwifhat (WIF) token.
token_address = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzL7M6fNazkOCA"

# Check if the API key was found.
if not BIRDEYE_API_KEY:
    print("Error: BIRDEYE_API_KEY secret not found!")
    exit(1) # Exit the script with an error code.

# --- API REQUEST ---
api_url = f"https://public-api.birdeye.so/public/price?address={token_address}"
headers = {"X-API-KEY": BIRDEYE_API_KEY}

# --- EXECUTION & RESULTS ---
print(f"Attempting to fetch data for token: {token_address}")

try:
    response = requests.get(api_url, headers=headers)
    # This will raise an error for bad status codes (4xx or 5xx)
    response.raise_for_status() 

    print("Success! Data received.")
    data = response.json()
    print("--- Token Data ---")
    print(data)
    print("------------------")

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error occurred: {err}")
    print("Response Text:", response.text)
except Exception as err:
    print(f"An other error occurred: {err}")

