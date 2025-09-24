import requests
import os
import json
from bs4 import BeautifulSoup

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
    """Gets the latest 100 assets created on Solana."""
    print("Making our single API call to Helius to fetch new assets...")
    payload = {"jsonrpc": "2.0", "id": "gem-hunter-search", "method": "searchAssets", "params": {"page": 1, "limit": TOKENS_TO_ANALYZE, "sortBy": {"sortBy": "created", "sortDirection": "desc"}}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']['items']

def scrape_pump_fun_socials(token_id):
    """Visits the pump.fun page for a token and scrapes social links."""
    print(f"Scraping pump.fun for off-chain social links for {token_id}...")
    pump_url = f"https://pump.fun/{token_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    socials = {}
    try:
        response = requests.get(pump_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for specific social links based on common href patterns
        twitter_link = soup.find('a', href=lambda href: href and "twitter.com" in href)
        telegram_link = soup.find('a', href=lambda href: href and "t.me" in href)
        website_link = soup.find('a', class_=lambda c: c and 'link' in c and 'website' in c) # pump.fun uses specific classes

        if twitter_link: socials['twitter'] = twitter_link['href']
        if telegram_link: socials['telegram'] = telegram_link['href']
        if website_link: socials['website'] = website_link['href']

    except Exception as e:
        print(f"  - Could not scrape pump.fun page: {e}")
    return socials

def get_ai_analysis(token_data):
    """Sends token data to Google Gemini AI for analysis."""
    print(f"Token {token_data['id']} passed all filters! Sending data to Google Gemini AI...")
    headers = {'Content-Type': 'application/json'}
    
    prompt_data = {
        "name": token_data.get('content', {}).get('metadata', {}).get('name', 'N/A'),
        "symbol": token_data.get('content', {}).get('metadata', {}).get('symbol', 'N/A'),
        "on_chain_description": token_data.get('content', {}).get('metadata', {}).get('description', 'N/A'),
        "all_known_links": token_data.get('all_links', {}),
        "is_mutable": token_data.get('mutable', 'N/A')
    }

    prompt = f"""
    Analyze the following new Solana fungible token. It has passed multiple automated filters.

    Token Data:
    {json.dumps(prompt_data, indent=2)}

    Your analysis should include:
    1.  **Summary:** A brief overview of what the token purports to be.
    2.  **Narrative/Hype Potential:** Does the name or description tap into any current crypto trends (e.g., memecoin, AI, DePIN)?
    3.  **Red Flags:** List any remaining red flags.
    4.  **Conclusion:** A final verdict (e.g., "High Risk, but has potential", "Interesting Concept", "Still looks low-effort").
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        new_assets = get_new_tokens()
        print(f"Found {len(new_assets)} new assets. Applying expert filters...")
        
        for asset in new_assets:
            # VET 1: NFT FILTER
            if 'Fungible' not in asset.get('interface', 'Unknown'):
                continue

            # VET 2: OFF-CHAIN INTELLIGENCE & DATA ENRICHMENT
            pump_fun_socials = scrape_pump_fun_socials(asset.get('id'))
            on_chain_links = asset.get('content', {}).get('links', {})
            # Combine all found links into one dictionary
            all_links = {**on_chain_links, **pump_fun_socials}
            asset['all_links'] = all_links # Save it for the AI report

            # VET 3: THE "PROOF OF EFFORT" FILTER
            # New Rule: We now require AT LEAST a website AND a twitter to be considered.
            if 'website' not in all_links or 'twitter' not in all_links:
                continue

            # If we are here, it's a non-NFT AND has both a website and a twitter.
            # This is a much stronger candidate for our expensive AI analysis.
            print(f"\n--- Found a High-Quality Candidate! ---")
            try:
                ai_report = get_ai_analysis(asset)
                print("\n--- AI REPORT ---")
                print(ai_report)
                print("-------------------")
            except Exception as e:
                print(f"Could not get AI analysis for token {asset.get('id')}. Reason: {e}")

    except Exception as e:
        print(f"An error occurred in the main process: {e}")
