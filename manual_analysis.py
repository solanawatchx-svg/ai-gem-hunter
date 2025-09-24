import requests
import os
import json

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
# The specific token address our hunter found
TOKEN_TO_ANALYZE = "44d1Tgm8Xn4DdRNY8e9tycoQFNSn3HqKByX9FMqjXoWB"

if not HELIUS_API_KEY or not GOOGLE_API_KEY:
    print("Error: Make sure HELIUS_API_KEY and GOOGLE_API_KEY secrets are set!")
    exit(1)

HELIUS_API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
# --- UPDATE --- Using the latest 'gemini-1.5-flash' model
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"

# --- HELPER FUNCTIONS ---
def get_token_details(token_id):
    """Gets detailed metadata for our specific token from Helius."""
    print(f"Fetching details for token: {token_id}")
    payload = {
        "jsonrpc": "2.0", "id": "manual-analysis-details", "method": "getAsset",
        "params": {"id": token_id}
    }
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']

def get_ai_analysis(token_data):
    """Sends token data to Google Gemini AI for analysis."""
    print(f"Sending data for token {token_data['id']} to Google Gemini AI...")
    headers = {'Content-Type': 'application/json'}
    
    prompt_data = {
        "name": token_data.get('content', {}).get('metadata', {}).get('name', 'N/A'),
        "symbol": token_data.get('content', {}).get('metadata', {}).get('symbol', 'N/A'),
        "description": token_data.get('content', {}).get('metadata', {}).get('description', 'N/A'),
        "links": token_data.get('content', {}).get('links', {}),
        "is_mutable": token_data.get('mutable', 'N/A')
    }

    prompt = f"""
    Analyze the following new Solana token based on its on-chain metadata.
    Provide a risk assessment and summary. Evaluate it as a potential 'crypto gem' or a likely 'scam/low value' token.

    Token Data:
    {json.dumps(prompt_data, indent=2)}

    Your analysis should include:
    1.  **Summary:** A brief overview of what the token purports to be.
    2.  **Narrative/Hype Potential:** Does the name or description tap into any current crypto trends?
    3.  **Red Flags:** Explicitly list any red flags based on the data (e.g., mutable metadata, no website, generic description).
    4.  **Conclusion:** A final verdict (e.g., "High Risk, Likely a Scam", "Low Risk, Interesting Concept", "Needs More Info").
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        print(f"--- Starting Manual Analysis for {TOKEN_TO_ANALYZE} ---")
        details = get_token_details(TOKEN_TO_ANALYZE)
        ai_report = get_ai_analysis(details)
        print("\n--- AI REPORT ---")
        print(ai_report)
        print("-------------------")
    except Exception as e:
        print(f"An error occurred during manual analysis: {e}")
