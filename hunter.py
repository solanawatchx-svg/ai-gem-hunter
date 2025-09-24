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
        # Find all links on the page
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if 'twitter.com' in href:
                socials['twitter'] = href
            if 't.me' in href:
                socials['telegram'] = href
            # pump.fun doesn't always have a clear website link, but we can look for it
            if 'website' in a_tag.text.lower():
                 socials['website'] = href
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
        "on_chain_links": token_data.get('content', {}).get('links', {}),
        "scraped_pump_fun_links": token_data.get('pump_fun_links', {}), # Add scraped links
        "is_mutable": token_data.get('mutable', 'N/A')
    }

    prompt = f"""
    Analyze the following new Solana fungible token. I have provided both its permanent on-chain data and any social links I could find by scraping its pump.fun page.

    Token Data:
    {json.dumps(prompt_data, indent=2)}

    Your analysis should include:
    1.  **Summary:** A brief overview of what the token purports to be.
    2.  **Narrative/Hype Potential:** Does the name or description tap into any current crypto trends?
    3.  **Red Flags:** List any red flags. Pay close attention if on-chain data is missing but scraped data is present (indicates low effort). Is it mutable?
    4.  **Conclusion:** A final verdict (e.g., "High Risk, Likely a Scam", "Interesting, but risky", "Needs More Info").
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        new_assets = get_new_tokens()
        print(f"Found {len(new_assets)} new assets. Applying filters and off-chain intelligence...")
        
        for asset in new_assets:
            # --- VET STEP 1: NFT FILTER ---
            if 'Fungible' not in asset.get('interface', 'Unknown'):
                continue

            # --- VET STEP 2: SCAM FILTER ---
            is_mutable = asset.get('mutable', True)
            has_on_chain_socials = any(key in asset.get('content', {}).get('links', {}) for key in ['website', 'twitter', 'telegram', 'discord'])
            if is_mutable and not has_on_chain_socials:
                continue
            
            # --- VET STEP 3: OFF-CHAIN INTELLIGENCE ---
            # If it passes the basic filters, we enrich it with scraped data
            pump_fun_socials = scrape_pump_fun_socials(asset.get('id'))
            asset['pump_fun_links'] = pump_fun_socials # Add the scraped links to our asset data
            
            # If the token has NO on-chain socials AND NO scraped socials, we skip it.
            if not has_on_chain_socials and not pump_fun_socials:
                continue

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
