import requests
import os
import json
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# --- TEST MODE CONFIGURATION ---
# Paste a token address here to test only that one.
# Set to None to return to normal, hourly hunting mode.
TEST_MODE_TOKEN_ADDRESS = "EUikxTuKGKq7YcAHYed4dwSCXSEM2cqYZ7FPumMUpump"

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

def get_asset_details(token_id):
    """Gets detailed metadata for a single token, used in Test Mode."""
    print(f"Fetching details for token: {token_id}")
    payload = {"jsonrpc": "2.0", "id": "test-mode-details", "method": "getAsset", "params": {"id": token_id}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']

def scrape_pump_fun_socials(token_id):
    """-- UPGRADED SCRAPER --"""
    pump_url = f"https://pump.fun/{token_id}"
    print(f"  - Scraping URL: {pump_url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    socials = {}
    try:
        response = requests.get(pump_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        socials_container = soup.find('div', class_=lambda c: c and 'justify-center' in c and 'gap-2' in c)
        if socials_container:
            for a_tag in socials_container.find_all('a', href=True):
                href = a_tag['href']
                if 'twitter.com' in href: socials['twitter'] = href
                if 't.me' in href: socials['telegram'] = href
                if 'twitter' not in href and 't.me' not in href: socials['website'] = href
        if socials: print(f"  - Success! Found socials: {socials}")
        else: print("  - No social links found on the page.")
    except Exception as e: print(f"  - Could not scrape pump.fun page: {e}")
    return socials

def get_ai_analysis(token_data):
    # This function remains the same
    print(f"Token {token_data['id']} passed all filters! Sending data to Google Gemini AI...")
    # ... (rest of the function is identical to before)
    headers = {'Content-Type': 'application/json'}
    prompt_data = {
        "name": token_data.get('content', {}).get('metadata', {}).get('name', 'N/A'),
        "symbol": token_data.get('content', {}).get('metadata', {}).get('symbol', 'N/A'),
        "on_chain_description": token_data.get('content', {}).get('metadata', {}).get('description', 'N/A'),
        "all_known_links": token_data.get('all_links', {}),
        "is_mutable": token_data.get('mutable', 'N/A')
    }
    prompt = f"Analyze the following new Solana fungible token. It has passed multiple automated filters.\n\nToken Data:\n{json.dumps(prompt_data, indent=2)}\n\nYour analysis should include:\n1.  **Summary:** A brief overview of what the token purports to be.\n2.  **Narrative/Hype Potential:** Does the name or description tap into any current crypto trends (e.g., memecoin, AI, DePIN)?\n3.  **Red Flags:** List any remaining red flags.\n4.  **Conclusion:** A final verdict (e.g., 'High Risk, but has potential', 'Interesting Concept', 'Still looks low-effort')."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        if TEST_MODE_TOKEN_ADDRESS:
            print(f"--- RUNNING IN TEST MODE FOR TOKEN: {TEST_MODE_TOKEN_ADDRESS} ---")
            asset = get_asset_details(TEST_MODE_TOKEN_ADDRESS)
            assets_to_process = [asset]
        else:
            print("--- RUNNING IN AUTONOMOUS HUNTING MODE ---")
            assets_to_process = get_new_tokens()
            print(f"Found {len(assets_to_process)} new assets. Applying expert filters...")

        for asset in assets_to_process:
            if 'Fungible' not in asset.get('interface', 'Unknown'): continue
            
            pump_fun_socials = scrape_pump_fun_socials(asset.get('id'))
            all_links = {**asset.get('content', {}).get('links', {}), **pump_fun_socials}
            asset['all_links'] = all_links

            if 'website' not in all_links or 'twitter' not in all_links: continue

            print(f"\n--- Found a High-Quality Candidate! ---")
            try:
                ai_report = get_ai_analysis(asset)
                print("\n--- AI REPORT ---")
                print(ai_report)
                print("-------------------")
            except Exception as e: print(f"Could not get AI analysis for token {asset.get('id')}. Reason: {e}")

    except Exception as e: print(f"An error occurred in the main process: {e}")

