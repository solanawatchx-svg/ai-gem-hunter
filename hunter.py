import requests
import os

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
if not HELIUS_API_KEY:
    print("Error: HELIUS_API_KEY secret not found!")
    exit(1)

api_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# --- API REQUEST ---
# We are changing the method to 'searchAssets' to find new tokens.
# We will sort by 'created' in descending order to get the newest ones first.
headers = {'Content-Type': 'application/json'}
payload = {
    "jsonrpc": "2.0",
    "id": "gem-hunter-search",
    "method": "searchAssets",
    "params": {
        "page": 1,
        "limit": 100,
        "sortBy": {
            "sortBy": "created",
            "sortDirection": "desc"
        }
    }
}

# --- EXECUTION & RESULTS ---
print("Attempting to find the 100 newest assets on Solana from Helius...")

try:
    response = requests.post(api_url, headers=headers, json=payload)
    response.raise_for_status()

    print("Success! Data received from Helius.")
    data = response.json()

    print("--- Newest Tokens Found ---")
    if 'result' in data and 'items' in data['result']:
        # Loop through each token found and print its details
        for token in data['result']['items']:
            token_id = token.get('id')
            token_name = "Unknown Name"
            # The name is often in the 'content' -> 'metadata' section
            if token.get('content') and token['content'].get('metadata'):
                token_name = token['content']['metadata'].get('name', 'Unknown Name')
            print(f"Name: {token_name:<40} Address: {token_id}")
    else:
        print("Could not find a list of items in the response.")
        print(data)
    print("--------------------------")

except requests.exceptions.HTTPError as err:
    print(f"HTTP Error occurred: {err}")
    print("Response Text:", response.text)
except Exception as err:
    print(f"An other error occurred: {err}")
