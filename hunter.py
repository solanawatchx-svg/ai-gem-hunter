import requests
import os
import json
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
SCRAPINGBEE_API_KEY = os.environ.get('SCRAPINGBEE_API_KEY')

# --- TEST MODE CONFIGURATION ---
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
    """-- DATA-TESTID SCRAPER V10 (Dev Approved) --
    Implements the professional strategy of locating the container via stable data-testid attributes."""
    pump_url = f"https://pump.fun/{token_id}"
    print(f"  - Sending scrape request for VISUAL page {pump_url} to ScrapingBee...")
    socials = {}
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params={'api_key': SCRAPINGBEE_API_KEY, 'url': pump_url, 'render_js': 'true'},
            timeout=60
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # DEV STRATEGY: Find any social badge, then find its parent container.
        # This is the most stable method.
        any_social_badge = soup.find(attrs={"data-testid": lambda value: value and value.endswith('-badge')})
        
        if any_social_badge:
            # Navigate up to the parent 'div' that holds all the badges
            # Based on inspection, it's usually 2 levels up.
            socials_container = any_social_badge.find_parent('div').find_parent('div')
            print("  - Target Lock Acquired: Found the social links container via data-testid.")
            
            # Now, we ONLY search for links inside this specific container.
            twitter_badge = socials_container.find(attrs={"data-testid": "twitter-badge"})
            website_badge = socials_container.find(attrs={"data-testid": "website-badge"})
            telegram_badge = socials_container.find(attrs={"data-testid": "telegram-badge"})

            if twitter_badge: socials['twitter'] = twitter_badge.find_parent('a')['href']
            if website_badge: socials['website'] = website_badge.find_parent('a')['href']
            if telegram_badge: socials['telegram'] = telegram_badge.find_parent('a')['href']

        if socials: print(f"  - Success! Found socials using data-testid: {socials}")
        else: print("  - data-testid strategy failed: Could not find any social badges.")

    except Exception as e:
        print(f"  - Could not scrape pump.fun page: {e}")
    return socials

def get_ai_analysis(token_data):
    # This function is unchanged
    print(f"Token {token_data['id']} passed filters! Sending data to Google Gemini AI...")
    # ... (rest is identical)
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
    # This logic is unchanged
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
            print("--- AUTONOMOUS HUNTING MODE IS NOT YET IMPLEMENTED IN THIS VERSION ---")
    except Exception as e:
        print(f"An error occurred in the main process: {e}")
