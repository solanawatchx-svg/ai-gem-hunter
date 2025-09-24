import requests
import os
import json

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

if not HELIUS_API_KEY or not GOOGLE_API_KEY:
    print("Error: Make sure HELIUS_API_KEY and GOOGLE_API_KEY secrets are set!")
    exit(1)

HELIUS_API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
TOKENS_TO_ANALYZE = 100 

# --- HELPER FUNCTIONS ---
def get_new_tokens():
    """Gets the latest 100 tokens created on Solana."""
    print("Making our single API call to Helius to fetch new assets...")
    payload = {
        "jsonrpc": "2.0", "id": "gem-hunter-search", "method": "searchAssets",
        "params": {"page": 1, "limit": TOKENS_TO_ANALYZE, "sortBy": {"sortBy": "created", "sortDirection": "desc"}}
    }
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']['items']

def get_ai_analysis(token_data):
    """Sends token data to Google Gemini AI for analysis."""
    print(f"Token {token_data['id']} passed all filters! Sending data to Google Gemini AI...")
    headers = {'Content-Type': 'application/json'}
    
    prompt_data = {
        "name": token_data.get('content', {}).get('metadata', {}).get('name', 'N/A'),
        "symbol": token_data.get('content', {}).get('metadata', {}).get('symbol', 'N/A'),
        "description": token_data.get('content', {}).get('metadata', {}).get('description', 'N/A'),
        "links": token_data.get('content', {}).get('links', {}),
        "is_mutable": token_data.get('mutable', 'N/A')
    }

    prompt = f"""
    Analyze the following new Solana fungible token based on its on-chain metadata.
    Provide a risk assessment and summary. Evaluate it as a potential 'crypto gem' or a likely 'scam/low value' token.

    Token Data:
    {json.dumps(prompt_data, indent=2)}

    Your analysis should include:
    1.  **Summary:** A brief overview of what the token purports to be.
    2.  **Narrative/Hype Potential:** Does the name or description tap into any current crypto trends (e.g., memecoin, AI, DePIN)?
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
        new_assets = get_new_tokens()
        print(f"Found {len(new_assets)} new assets. Applying NFT and scam filters...")
        
        for asset in new_assets:
            # --- FINAL VET, STEP 1: NFT FILTER ---
            # Helius tells us the 'interface' type. We only want 'FungibleToken' or 'FungibleAsset'.
            interface = asset.get('interface', 'Unknown')
            if 'Fungible' not in interface:
                continue # Silently skip because it's an NFT or something else

            # --- FINAL VET, STEP 2: SCAM FILTER ---
            is_mutable = asset.get('mutable', True)
            links = asset.get('content', {}).get('links', {})
            has_socials = any(key in links for key in ['website', 'twitter', 'telegram', 'discord'])

            if is_mutable and not has_socials:
                continue # Silently skip high-risk tokens
            
            # If we are here, we have found a potential fungible token gem!
            print(f"\n--- Found a Potential Token! ---")
            try:
                ai_report = get_ai_analysis(asset)
                print("\n--- AI REPORT ---")
                print(ai_report)
                print("-------------------")
            except Exception as e:
                print(f"Could not get AI analysis for token {asset.get('id')}. Reason: {e}")

    except Exception as e:
        print(f"An error occurred in the main process: {e}")
