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
# We can now check all 100 tokens from the initial call with no extra cost.
TOKENS_TO_ANALYZE = 100 

# --- HELPER FUNCTIONS ---
def get_new_tokens():
    """Gets the latest 100 tokens created on Solana. This is our ONLY call to Helius."""
    print("Making our single API call to Helius to fetch new tokens...")
    payload = {
        "jsonrpc": "2.0", "id": "gem-hunter-search", "method": "searchAssets",
        "params": {"page": 1, "limit": TOKENS_TO_ANALYZE, "sortBy": {"sortBy": "created", "sortDirection": "desc"}}
    }
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']['items']

def get_ai_analysis(token_data):
    """Sends token data to Cerebras AI for analysis."""
    print(f"Token {token_data['id']} passed the filter! Sending data to Cerebras AI...")
    headers = {"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"}
    
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
    
    payload = { "model": "BTLM-3B-8K-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7 }
    
    response = requests.post(CEREBRAS_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        new_tokens = get_new_tokens()
        print(f"Found {len(new_tokens)} new tokens. Applying filter and analyzing...")
        
        for i, token in enumerate(new_tokens):
            token_id = token.get('id')
            
            # --- THE ULTRA-EFFICIENT VET ---
            # We apply the filter using data we already have from the first call.
            is_mutable = token.get('mutable', True)
            links = token.get('content', {}).get('links', {})
            has_socials = any(key in links for key in ['website', 'twitter', 'telegram', 'discord'])

            # If it's mutable AND has no links, it's junk. We don't print anything, just skip.
            if is_mutable and not has_socials:
                continue # Silently skip to the next token
            
            # If we are here, the token has passed our filter! Now we can analyze it.
            print(f"\n--- Found a Potential Candidate! ---")
            try:
                ai_report = get_ai_analysis(token)
                print("\n--- AI REPORT ---")
                print(ai_report)
                print("-------------------")
            except Exception as e:
                print(f"Could not get AI analysis for token {token_id}. Reason: {e}")

    except Exception as e:
        print(f"An error occurred in the main process: {e}")
