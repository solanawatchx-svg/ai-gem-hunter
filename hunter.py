import requests
import os
import json

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

# --- HELPER FUNCTIONS ---
def get_pump_fun_details(token_id):
    """-- FINAL VERSION V5 --
    Uses ScrapingBee to reliably call the internal pump.fun API, bypassing bot detection."""
    pump_api_url = f"https://frontend-api.pump.fun/coins/{token_id}"
    print(f"  - Sending request for {pump_api_url} via ScrapingBee to bypass bot detection...")
    
    params = {'api_key': SCRAPINGBEE_API_KEY, 'url': pump_api_url}
    response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=60)
    
    response.raise_for_status()
    data = response.json()
    
    socials = {}
    if data.get('twitter'): socials['twitter'] = data['twitter']
    if data.get('telegram'): socials['telegram'] = data['telegram']
    if data.get('website'): socials['website'] = data['website']
    
    if socials: print(f"  - Success! Found socials via pump.fun API: {socials}")
    else: print("  - pump.fun API responded, but no social links were listed.")
    
    # Also return the name, symbol, and description from this API call
    full_details = {
        'name': data.get('name', 'N/A'),
        'symbol': data.get('symbol', 'N/A'),
        'description': data.get('description', 'N/A'),
        'all_links': socials
    }
    return full_details

def get_ai_analysis(token_data):
    """Sends token data to Google Gemini AI for analysis."""
    print(f"Token {token_data['id']} passed filters! Sending data to Google Gemini AI...")
    headers = {'Content-Type': 'application/json'}
    
    # We now use the clean data directly from the pump.fun API
    prompt_data = {
        "name": token_data.get('name'),
        "symbol": token_data.get('symbol'),
        "description": token_data.get('description'),
        "links": token_data.get('all_links')
    }

    prompt = f"""
    Analyze the following new Solana fungible token based on its data from the pump.fun API.

    Token Data:
    {json.dumps(prompt_data, indent=2)}

    Your analysis should include:
    1.  **Summary:** A brief overview of the token's theme.
    2.  **Narrative/Hype Potential:** Does this look like a typical memecoin? Does the name or theme tap into any current trends?
    3.  **Red Flags:** Are there any red flags based on the provided data? (e.g., missing website, generic description).
    4.  **Conclusion:** A final verdict (e.g., "High Risk Memecoin", "Seems higher-effort than average", "Low-effort, avoid").
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['candidates'][0]['content']['parts'][0]['text']

# --- MAIN LOGIC ---
if __name__ == "__main__":
    try:
        if TEST_MODE_TOKEN_ADDRESS:
            print(f"--- RUNNING IN TEST MODE FOR TOKEN: {TEST_MODE_TOKEN_ADDRESS} ---")
            details = get_pump_fun_details(TEST_MODE_TOKEN_ADDRESS)
            details['id'] = TEST_MODE_TOKEN_ADDRESS # Add the ID for the AI function
            ai_report = get_ai_analysis(details)
            print("\n--- AI REPORT ---")
            print(ai_report)
            print("-------------------")
        else:
            # We will implement the full hunting logic here once testing is complete.
            print("--- AUTONOMOUS HUNTING MODE IS NOT YET IMPLEMENTED IN THIS VERSION ---")
            print("To run the hunter, set TEST_MODE_TOKEN_ADDRESS to None.")

    except Exception as e:
        print(f"An error occurred in the main process: {e}")

