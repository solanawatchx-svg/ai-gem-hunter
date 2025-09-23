import requests
import os

# --- CONFIGURATION ---
# This line safely gets the API key from the GitHub Secrets we set up.
BIRDEYE_API_KEY = os.environ.get('BIRDEYE_API_KEY')

# Check if the API key was found.
if not BIRDEYE_API_KEY:
    print("Error: BIRDEYE_API_KEY secret not found!")
    exit(1) # Exit the script with an error code.

# --- API REQUEST ---
# We are changing the URL to a different, simpler endpoint to test the API key.
# This endpoint just asks for the list of all supported tokens.
api_url = "https://public-api.birdeye.so/public/tokenlist"
headers = {"X-API-KEY": BIRDEYE_API_KEY}

# --- EXECUTION & RESULTS ---
print(f"Attempting to call the Birdeye tokenlist endpoint...")

try:
    response = requests.get(api_url, headers=headers)
    # This will raise an error for bad status codes (4xx or 5xx)
    response.raise_for_status() 

    print("Success! Connection to Birdeye API is working.")
    data = response.json()
    # The result will be very long, so let's just print the first 500 characters
    # to prove it works.
    print("--- Sample of Token List Data ---")
    print(str(data)[:500])
    print("---------------------------------")

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error occurred: {err}")
    print("This confirms the problem is with the Birdeye API or your key, not the code.")
    print("Response Text:", response.text)
except Exception as err:
    print(f"An other error occurred: {err}")
