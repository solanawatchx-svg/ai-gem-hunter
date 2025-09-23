import requests
import os
import json

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
CEREBRAS_API_KEY = os.environ.get('CEREBRAS_API_KEY')

if not HELIUS_API_KEY or not CEREBRAS_API_KEY:
    print("Error: Make sure both HELIUS_API_KEY and CEREBRAS_API_KEY secrets are set!")
    exit(1)

HELIUS_API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
CEREBRAS_API_URL = "https://api.cerebras.com/v1/chat/completions"
# Set how many of the newest tokens we want to analyze
TOKENS_TO_ANALYZE = 5

# --- HELPER FUNCTIONS ---
def get_new_tokens():
    """Gets the latest tokens created on Solana."""
    print("Fetching new tokens from Helius...")
    payload = {
        "jsonrpc": "2.0", "id": "gem-hunter-search", "method": "searchAssets",
        "params": {"page": 1, "limit": 100, "sortBy": {"sortBy": "created", "sortDirection": "desc"}}
    }
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']['items']

def get_token_details(token_id):
    """Gets detailed metadata for a single token."""
    print(f"Fetching details for token: {token_id}")
    payload = {
        "jsonrpc": "2.0", "id": "gem-hunter-details", "method": "getAsset",
        "params": {"id": token_id}
    }
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']

def get_ai_analysis(token_data):
    """Sends token data to Cerebras AI for analysis."""
    print("Sending data to Cerebras AI for analysis...")
    headers = {"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"}
    
    # Create a clean summary of the token data for the AI
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
    
    payload = {
        "model": "BTLM-3B-8K-chat", # Using a fast and efficient model
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    response = requests.post(CEREBRAS_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        new_tokens = get_new_tokens()
        print(f"Found {len(new_tokens)} new tokens. Analyzing the top {TOKENS_TO_ANALYZE}...")
        
        for i, token in enumerate(new_tokens[:TOKENS_TO_ANALYZE]):
            print(f"\n--- Analyzing Token {i+1}/{TOKENS_TO_ANALYZE} ---")
            token_id = token.get('id')
            
            try:
                details = get_token_details(token_id)
                
                # --- AUTOMATED VET (SCAM FILTER) ---
                is_mutable = details.get('mutable', True)
                has_website = 'website' in details.get('content', {}).get('links', {})
                
                if is_mutable:
                    print(f"RED FLAG: Token metadata is mutable. Skipping AI analysis. Address: {token_id}")
                    continue
                
                # You can add more rules here, e.g., if not has_website: continue

                # If it passes the filter, send to AI
                ai_report = get_ai_analysis(details)
                print("\n--- AI REPORT ---")
                print(ai_report)
                print("-------------------")
                
            except Exception as e:
                print(f"Could not analyze token {token_id}. Reason: {e}")

    except Exception as e:
        print(f"An error occurred in the main process: {e}")

