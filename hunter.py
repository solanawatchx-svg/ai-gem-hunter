import requests
import os
import json

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# --- TEST MODE CONFIGURATION ---
TEST_MODE_TOKEN_ADDRESS = "EUikxTuKGKq7YcAHYed4dwSCXSEM2cqYZ7FPumMUpump"

if not HELIUS_API_KEY or not GOOGLE_API_KEY:
    print("Error: Make sure HELIUS_API_KEY and GOOGLE_API_KEY secrets are set!")
    exit(1)

HELIUS_API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
TOKENS_TO_ANALYZE = 100 

# --- HELPER FUNCTIONS ---
def get_new_tokens():
    print("Making our single API call to Helius to fetch new assets...")
    payload = {"jsonrpc": "2.0", "id": "gem-hunter-search", "method": "searchAssets", "params": {"page": 1, "limit": TOKENS_TO_ANALYZE, "sortBy": {"sortBy": "created", "sortDirection": "desc"}}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']['items']

def get_asset_details(token_id):
    print(f"Fetching details for token: {token_id}")
    payload = {"jsonrpc": "2.0", "id": "test-mode-details", "method": "getAsset", "params": {"id": token_id}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']

def get_pump_fun_details(token_id):
    """-- API METHOD V4 --
    Calls the internal pump.fun API to get clean, reliable data."""
    pump_api_url = f"https://frontend-api.pump.fun/coins/{token_id}"
    print(f"  - Querying pump.fun API: {pump_api_url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    socials = {}
    try:
        response = requests.get(pump_api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Extract the socials directly from the JSON response
        if data.get('twitter'): socials['twitter'] = data['twitter']
        if data.get('telegram'): socials['telegram'] = data['telegram']
        if data.get('website'): socials['website'] = data['website']
        
        if socials: print(f"  - Success! Found socials via pump.fun API: {socials}")
        else: print("  - pump.fun API responded, but no social links were listed.")
            
    except Exception as e:
        print(f"  - Could not get details from pump.fun API: {e}")
    return socials

def get_ai_analysis(token_data):
    # This function remains the same
    print(f"Token {token_data['id']} passed all filters! Sending data to Google Gemini AI...")
    # ... (rest is identical)
    headers = {'Content-Type': 'application/json'}
    prompt_data = {
        "name": token_data.get('name', 'N/A'),
        "symbol": token_data.get('symbol', 'N/A'),
        "on_chain_description": token_data.get('description', 'N/A'),
        "all_known_links": token_data.get('all_links', {}),
    }
    prompt = f"Analyze the following new Solana fungible token. Data is from the pump.fun API.\n\nToken Data:\n{json.dumps(prompt_data, indent=2)}\n\nYour analysis should include:\n1.  **Summary:** A brief overview of what the token purports to be.\n2.  **Narrative/Hype Potential:** Does the name or description tap into any current crypto trends (e.g., memecoin, AI, DePIN)?\n3.  **Red Flags:** List any remaining red flags.\n4.  **Conclusion:** A final verdict (e.g., 'High Risk, but has potential', 'Interesting Concept', 'Still looks low-effort')."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        if TEST_MODE_TOKEN_ADDRESS:
            print(f"--- RUNNING IN TEST MODE FOR TOKEN: {TEST_MODE_TOKEN_ADDRESS} ---")
            # In test mode, we get all our data from the pump.fun API
            pump_details = get_pump_fun_details(TEST_MODE_TOKEN_ADDRESS)
            # We need to structure it a bit to match what the AI function expects
            asset = {
                'id': TEST_MODE_TOKEN_ADDRESS,
                'name': pump_details.get('name', 'N/A'),
                'symbol': pump_details.get('symbol', 'N/A'),
                'description': pump_details.get('description', 'N/A'),
                'all_links': pump_details
            }
            assets_to_process = [asset]
        else:
            # ... (normal hunting mode would be here)
            print("To run in hunting mode, set TEST_MODE_TOKEN_ADDRESS to None.")
            assets_to_process = []
        
        for asset in assets_to_process:
            # The filter is implicitly passed since we are only testing one token
            print(f"\n--- Found a High-Quality Candidate! ---")
            try:
                ai_report = get_ai_analysis(asset)
                print("\n--- AI REPORT ---")
                print(ai_report)
                print("-------------------")
            except Exception as e: print(f"Could not get AI analysis for token {asset.get('id')}. Reason: {e}")

    except Exception as e: print(f"An error occurred in the main process: {e}")
