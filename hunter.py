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

HELIUS_API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
TOKENS_TO_ANALYZE = 100 

# --- HELPER FUNCTIONS ---
def get_new_tokens():
    # ... (this function is unchanged)
    print("Making our single API call to Helius to fetch new assets...")
    payload = {"jsonrpc": "2.0", "id": "gem-hunter-search", "method": "searchAssets", "params": {"page": 1, "limit": TOKENS_TO_ANALYZE, "sortBy": {"sortBy": "created", "sortDirection": "desc"}}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']['items']

def get_asset_details(token_id):
    # ... (this function is unchanged)
    print(f"Fetching details for token: {token_id}")
    payload = {"jsonrpc": "2.0", "id": "test-mode-details", "method": "getAsset", "params": {"id": token_id}}
    response = requests.post(HELIUS_API_URL, headers={'Content-Type': 'application/json'}, json=payload)
    response.raise_for_status()
    return response.json()['result']

def scrape_pump_fun_socials(token_id):
    """-- SURGICAL SCRAPER V3 --
    Uses ScrapingBee and targets the specific social links container."""
    pump_url = f"https://pump.fun/{token_id}"
    print(f"  - Sending scrape request for {pump_url} to ScrapingBee...")
    socials = {}
    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params={'api_key': SCRAPINGBEE_API_KEY, 'url': pump_url, 'render_js': 'true'},
            timeout=60
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # New Surgical Logic: Find the div that contains the name/ticker, then find the social links div next to it.
        # This is a much more reliable way to target the correct links.
        header_div = soup.find('div', class_=lambda c: c and 'flex' in c and 'items-center' in c and 'gap-4' in c)
        if header_div:
            # The social links are usually in the same container or a sibling. Let's search within this parent container.
            for a_tag in header_div.find_all('a', href=True):
                href = a_tag['href']
                if 'twitter.com' in href: socials['twitter'] = href
                if 't.me' in href: socials['telegram'] = href
                # Check for website link via an icon, a common pattern
                svg_use = a_tag.find('use')
                if svg_use and '#website' in svg_use.get('xlink:href', ''):
                    socials['website'] = href

        if socials: print(f"  - Success! Found socials via Surgical Scraping: {socials}")
        else: print("  - Surgical Scraping ran, but no social links were found in the target area.")

    except Exception as e:
        print(f"  - Could not scrape using ScrapingBee: {e}")
    return socials

def get_ai_analysis(token_data):
    # ... (this function is unchanged)
    print(f"Token {token_data['id']} passed all filters! Sending data to Google Gemini AI...")
    # ... (rest of the function is identical)
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
    # ... (this logic is unchanged)
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
