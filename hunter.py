import requests
import os
import json

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
MORALIS_API_KEY = os.environ.get('MORALIS_API_KEY')

# --- TEST MODE CONFIGURATION ---
# Using a known, older pump.fun token ($MICHI) to test the Moralis connection
TEST_MODE_TOKEN_ADDRESS = "5mbK36g4T4o1sN7p2t21vSYLh642d2j2v2yKx6a1p2aM"

if not HELIUS_API_KEY or not GOOGLE_API_KEY or not MORALIS_API_KEY:
    print("Error: Make sure HELIUS, GOOGLE, and MORALIS API key secrets are set!")
    exit(1)

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
HELIUS_API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# --- HELPER FUNCTIONS ---
def get_asset_details(token_id):
    # This function is unchanged
    print(f"Fetching on-chain details for token: {token_id}")
    payload = {"jsonrpc": "2.0", "id": "test-mode-details", "method": "getAsset", "params": {"id": token_id}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']

def get_socials_from_moralis(token_id):
    # This function is unchanged
    print(f"  - Querying Moralis API for pump.fun data on {token_id}...")
    moralis_url = f"https://solana-gateway.moralis.io/pump/api/v1/coin-data/{token_id}"
    headers = {"X-API-Key": MORALIS_API_KEY}
    socials = {}
    try:
        response = requests.get(moralis_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('twitter'): socials['twitter'] = data['twitter']
        if data.get('telegram'): socials['telegram'] = data['telegram']
        if data.get('website'): socials['website'] = data['website']
        if socials: print(f"  - Success! Found socials via Moralis API: {socials}")
        else: print("  - Moralis API responded, but no social links were listed.")
    except Exception as e:
        print(f"  - Could not get details from Moralis API: {e}")
    return socials

def get_ai_analysis(token_data):
    # This function is unchanged
    print(f"Token {token_data['id']} passed filters! Sending data to Google Gemini AI...")
    headers = {'Content-Type': 'application/json'}
    prompt_data = {"name": token_data.get('content', {}).get('metadata', {}).get('name', 'N/A'), "symbol": token_data.get('content', {}).get('metadata', {}).get('symbol', 'N/A'), "description": token_data.get('content', {}).get('metadata', {}).get('description', 'N/A'), "links": token_data.get('all_links', {}), "is_mutable": token_data.get('mutable', 'N/A')}
    prompt = f"Analyze the following new Solana fungible token...\n\nToken Data:\n{json.dumps(prompt_data, indent=2)}\n\nYour analysis should include...\n1. Summary\n2. Narrative/Hype Potential\n3. Red Flags\n4. Conclusion"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    # This logic is unchanged
    try:
        if TEST_MODE_TOKEN_ADDRESS:
            print(f"--- RUNNING IN TEST MODE FOR TOKEN: {TEST_MODE_TOKEN_ADDRESS} ---")
            asset = get_asset_details(TEST_MODE_TOKEN_ADDRESS)
            scraped_socials = get_socials_from_moralis(TEST_MODE_TOKEN_ADDRESS)
            asset['all_links'] = {**asset.get('content', {}).get('links', {}), **scraped_socials}
            print(f"\n--- Test token passed to AI ---")
            ai_report = get_ai_analysis(asset)
            print("\n--- AI REPORT ---")
            print(ai_report)
            print("-------------------")
        else:
            print("--- AUTONOMOUS HUNTING MODE IS NOT YET IMPLEMENTED ---")
    except Exception as e:
        print(f"An error occurred in the main process: {e}")
