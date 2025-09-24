import requests
import os
import json
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
SCRAPINGBEE_API_KEY = os.environ.get('SCRAPINGBEE_API_KEY')

# --- TEST MODE CONFIGURATION ---
# We are putting our test token back in for one final verification run.
TEST_MODE_TOKEN_ADDRESS = "EUikxTuKGKq7YcAHYed4dwSCXSEM2cqYZ7FPumMUpump"

if not HELIUS_API_KEY or not GOOGLE_API_KEY or not SCRAPINGBEE_API_KEY:
    print("Error: Make sure HELIUS, GOOGLE, and SCRAPINGBEE API key secrets are set!")
    exit(1)

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
HELIUS_API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# --- HELPER FUNCTIONS ---
def get_asset_details(token_id):
    """Gets on-chain details from Helius."""
    print(f"Fetching on-chain details for token: {token_id}")
    payload = {"jsonrpc": "2.0", "id": "test-mode-details", "method": "getAsset", "params": {"id": token_id}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']

def scrape_pump_fun_page(token_id):
    """-- PRODUCTION SCRAPER (Dev-Tuned) --"""
    pump_url = f"https://pump.fun/coin/{token_id}"
    print(f"  - Scraping (rendered) {pump_url} via ScrapingBee...")
    socials = {}
    try:
        params = {
            'api_key': SCRAPINGBEE_API_KEY,
            'url': pump_url,
            'render_js': 'true',
            'wait': '3'
        }
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0'}
        r = requests.get('https://app.scrapingbee.com/api/v1/', params=params, headers=headers, timeout=90)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find the first badge that exists to use as an anchor
        anchor_badge = soup.find(attrs={"data-testid": lambda value: value and value.endswith('-social-badge')})
        
        if anchor_badge:
            print("  - Target Lock Acquired: Found a social badge via data-testid.")
            # Find the parent container that holds all the links
            container = anchor_badge.find_parent('a').parent
            
            if container:
                print("  - Located social links container relative to the badge.")
                for a in container.find_all('a', href=True):
                    href = a['href'].strip().split('#')[0]
                    if a.find(attrs={"data-testid": "twitter-social-badge"}): socials['twitter'] = href
                    if a.find(attrs={"data-testid": "website-social-badge"}): socials['website'] = href
                    if a.find(attrs={"data-testid": "telegram-social-badge"}): socials['telegram'] = href
        
        if socials:
            print("  - Socials found:", socials)
        else:
            print("  - No socials found on page. Dumping HTML snippet for debugging:")
            print(r.text[:1000])

    except Exception as e:
        print("  - Scrape error:", str(e))
    return socials

def get_ai_analysis(token_data):
    """Sends token data to Google Gemini AI for analysis."""
    print(f"Token {token_data['id']} passed filters! Sending data to Google Gemini AI...")
    headers = {'Content-Type': 'application/json'}
    prompt_data = {
        "name": token_data.get('content', {}).get('metadata', {}).get('name', 'N/A'),
        "symbol": token_data.get('content', {}).get('metadata', {}).get('symbol', 'N/A'),
        "description": token_data.get('content', {}).get('metadata', {}).get('description', 'N/A'),
        "links": token_data.get('all_links', {}),
        "is_mutable": token_data.get('mutable', 'N/A')
    }
    prompt = f"Analyze the following new Solana fungible token...\n\nToken Data:\n{json.dumps(prompt_data, indent=2)}\n\nYour analysis should include...\n1. Summary\n2. Narrative/Hype Potential\n3. Red Flags\n4. Conclusion" # Abbreviated
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
            scraped_socials = scrape_pump_fun_page(TEST_MODE_TOKEN_ADDRESS)
            asset['all_links'] = {**asset.get('content', {}).get('links', {}), **scraped_socials}
            print(f"\n--- Test token passed to AI ---")
            ai_report = get_ai_analysis(asset)
            print("\n--- AI REPORT ---")
            print(ai_report)
            print("-------------------")
        else:
            # Live hunting logic
            print("--- RUNNING IN AUTONOMOUS HUNTING MODE ---")
            new_assets = get_new_tokens()
            # ... (Full logic will be restored after test)
    except Exception as e:
        print(f"An error occurred in the main process: {e}")
