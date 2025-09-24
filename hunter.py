import requests
import os
import json
from bs4 import BeautifulSoup
from apify_client import ApifyClient

# --- CONFIGURATION ---
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN')

# --- TEST MODE CONFIGURATION ---
TEST_MODE_TOKEN_ADDRESS = "EUikxTuKGKq7YcAHYed4dwSCXSEM2cqYZ7FPumMUpump"

if not HELIUS_API_KEY or not GOOGLE_API_KEY or not APIFY_API_TOKEN:
    print("Error: Make sure HELIUS, GOOGLE, and APIFY API key secrets are set!")
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

def scrape_with_apify(token_id):
    """-- FINAL VERSION V15 --
    Uses the correct Apify 'web-scraper' actor."""
    pump_url = f"https://pump.fun/coin/{token_id}"
    print(f"  - Starting Apify 'web-scraper' for {pump_url}...")
    socials = {}
    try:
        client = ApifyClient(APIFY_API_TOKEN)
        # THE FIX: Using the correct, more powerful 'web-scraper' actor.
        actor_run = client.actor("apify/web-scraper").call(
            run_input={"startUrls": [{"url": pump_url}], "runMode": "production"}
        )
        
        html_content = ""
        for item in client.dataset(actor_run["defaultDatasetId"]).iterate_items():
            html_content = item.get("html", "")
            break 

        if not html_content:
            print("  - Apify ran but returned no HTML content.")
            return socials

        soup = BeautifulSoup(html_content, 'html.parser')
        
        anchor_badge = soup.find(attrs={"data-testid": lambda value: value and value.endswith('-social-badge')})
        if anchor_badge:
            print("  - Target Lock Acquired in Apify result via data-testid.")
            container = anchor_badge.find_parent('a').parent
            if container:
                for a in container.find_all('a', href=True):
                    href = a['href'].strip().split('#')[0]
                    if a.find(attrs={"data-testid": "twitter-social-badge"}): socials['twitter'] = href
                    if a.find(attrs={"data-testid": "website-social-badge"}): socials['website'] = href
                    if a.find(attrs={"data-testid": "telegram-social-badge"}): socials['telegram'] = href

        if socials: print(f"  - Success! Found socials via Apify: {socials}")
        else: print("  - Apify returned HTML, but no social badges were found.")

    except Exception as e:
        print(f"  - Apify scrape error: {str(e)}")
    return socials

def get_ai_analysis(token_data):
    # This function is unchanged
    print(f"Token {token_data['id']} passed filters! Sending data to Google Gemini AI...")
    # ... (rest is identical)
    headers = {'Content-Type': 'application/json'}
    prompt_data = {"name": token_data.get('content', {}).get('metadata', {}).get('name', 'N/A'), "symbol": token_data.get('content', {}).get('metadata', {}).get('symbol', 'N/A'), "description": token_data.get('content', {}).get('metadata', {}).get('description', 'N/A'), "links": token_data.get('all_links', {}), "is_mutable": token_data.get('mutable', 'N/A')}
    prompt = f"Analyze the following new Solana fungible token...\n\nToken Data:\n{json.dumps(prompt_data, indent=2)}\n\nYour analysis should include...\n1. Summary\n2. Narrative/Hype Potential\n3. Red Flags\n4. Conclusion"
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
            scraped_socials = scrape_with_apify(TEST_MODE_TOKEN_ADDRESS)
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

