import requests
import json
import re
import logging
import sys
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# ==========================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# ==========================================
load_dotenv()

BASE_DOMAIN = os.getenv("BASE_DOMAIN")
ORIGIN_URL = os.getenv("ORIGIN_URL")
LANDING_URL = os.getenv("LANDING_URL")
API_URL = os.getenv("API_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not all([BASE_DOMAIN, ORIGIN_URL, LANDING_URL, API_URL]):
    print("❌ Critical Error: Missing required URLs or DOMAIN in .env file.")
    sys.exit(1)

# ==========================================
# LOGGING CONFIGURATION (Fixed for Windows)
# ==========================================
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler('availability.log', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
# ==========================================

def send_discord_message(message):
    """Sends a message to Discord, splitting it if it exceeds 2000 characters."""
    if not DISCORD_WEBHOOK_URL or "PASTE_YOUR" in DISCORD_WEBHOOK_URL:
        logger.warning("⚠️ Discord Webhook URL not set in .env file. Skipping Discord notification.")
        return

    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
    
    for chunk in chunks:
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk})
            response.raise_for_status()
        except Exception as e:
            logger.error(f"❌ Failed to send Discord alert: {e}")

def get_fresh_tokens():
    logger.info("🔄 Starting headless browser to fetch fresh tokens...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        captured_token = None
        def intercept_request(request):
            nonlocal captured_token
            if BASE_DOMAIN in request.url and "X-CSRF-Token" in request.headers:
                captured_token = request.headers["X-CSRF-Token"]

        page.on("request", intercept_request)
        page.goto(LANDING_URL, wait_until="networkidle")
        
        csrf_token = None
        
        try:
            meta_tag = page.locator('meta[name="csrf-token"]')
            if meta_tag.count() > 0:
                csrf_token = meta_tag.first.get_attribute('content')
        except Exception:
            pass
            
        if not csrf_token:
            html = page.content()
            patterns = [
                r'window\.__csrfToken\s*=\s*[\'"]([^\'"]+)[\'"]', 
                r'"csrfToken"\s*:\s*"([^"]+)"',
                r'"CSRFToken"\s*:\s*"([^"]+)"',
                r'name="_csrf"\s+content="([^"]+)"',
                r'name="csrf-token"\s+content="([^"]+)"'
            ]
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    csrf_token = match.group(1)
                    break
                    
        if not csrf_token:
            csrf_token = captured_token
            
        cookies = context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        
        if not csrf_token:
            for c in cookies:
                if 'XSRF' in c['name'].upper() or 'CSRF' in c['name'].upper():
                    csrf_token = c['value']
                    break

        browser.close()
        
        if not csrf_token:
            logger.error("❌ Failed to capture X-CSRF-Token from DOM, Cookies, or Network.")
            raise ValueError("Failed to capture X-CSRF-Token.")
            
        logger.info("✅ Tokens successfully retrieved!")
        return csrf_token, cookie_str

def check_availability_for_date(target_date, headers):
    """
    Fetches availability and returns a tuple: (formatted_string_for_discord, boolean_has_availability)
    """
    date_str = target_date.strftime("%Y-%m-%d")
    day_name = target_date.strftime("%A")
    
    is_weekday = target_date.weekday() < 5
    
    logger.info(f"📅 Checking availability for {day_name}, {date_str}")
    
    payload = {
        "facility_group_id": 2,
        "customer_id": 0,
        "company_id": 0,
        "reserve_date": date_str,
        "start_time": None,
        "end_time": None,
        "resident": True,
        "reload": True,
        "change_time_range": False
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        logger.error(f"❌ Error: Received status code {response.status_code}")
        return f"**📅 {day_name}, {date_str}**\n❌ *Error connecting to server.*\n\n", False

    data = response.json()
    
    try:
        availability_data = data["body"]["availability"]
        master_times = availability_data["time_slots"]
        resources = availability_data["resources"]
    except KeyError:
        logger.error("❌ Could not find the expected data in the response.")
        return f"**📅 {day_name}, {date_str}**\n❌ *Unexpected data format.*\n\n", False

    court_results = {}
    has_any_availability_for_day = False

    for resource in resources:
        court_name = resource["resource_name"]
        details = resource["time_slot_details"]
        available_slots_for_court = []
        
        for i, time_str in enumerate(master_times):
            if i < len(details):
                status = details[i]["status"]
                
                if status == 0:
                    time_obj = datetime.strptime(time_str, "%H:%M:%S")
                    formatted_time = time_obj.strftime("%I:%M %p").lstrip("0")
                    
                    if is_weekday and time_obj.hour >= 17:
                        icon = "⭐" 
                    else:
                        icon = "✅"
                        
                    available_slots_for_court.append(f"{icon} {formatted_time}")
        
        court_results[court_name] = available_slots_for_court
        
        if available_slots_for_court:
            has_any_availability_for_day = True

    discord_msg = f"**📅 {day_name}, {date_str}**\n"
    
    if not has_any_availability_for_day:
        discord_msg += "• *No courts available*\n\n"
    else:
        for court_name, slots in court_results.items():
            discord_msg += f"\n**🏟️ {court_name}**\n"
            if slots:
                for slot in slots:
                    discord_msg += f"• {slot}\n"
            else:
                discord_msg += "• *No available slots*\n"
        discord_msg += "\n"
            
    return discord_msg, has_any_availability_for_day

if __name__ == "__main__":
    try:
        fresh_csrf_token, fresh_cookie = get_fresh_tokens()
    except Exception as e:
        logger.critical(f"Critical Error: {e}")
        send_discord_message(f"🚨 **Script Failed!** Could not retrieve fresh tokens.\nError: {e}")
        exit(1)
        
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": ORIGIN_URL,
        "Referer": LANDING_URL,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        "X-CSRF-Token": fresh_csrf_token,
        "X-Requested-With": "XMLHttpRequest",
        "page_info": '{"page_number":1,"total_records_per_page":20}',
        "Cookie": fresh_cookie
    }
    
    today = datetime.now().date()
    dates_to_check = [
        today,
        today + timedelta(days=1),
        today + timedelta(days=2),
        today + timedelta(days=3)
    ]
    
    # Compile the full report for Discord
    full_report = "🎾 **Daily Tennis Court Availability**\n"
    full_report += f"*Checked on {datetime.now().strftime('%Y-%m-%d at %I:%M %p')}*\n\n"
    full_report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    any_availability_found_in_4_days = False
    
    for date in dates_to_check:
        daily_report, day_has_availability = check_availability_for_date(date, headers)
        full_report += daily_report
        full_report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # If any day has availability, flag the whole report to be sent
        if day_has_availability:
            any_availability_found_in_4_days = True
            
    # Only send the message if at least one court is available somewhere in the 4 days
    if any_availability_found_in_4_days:
        logger.info("Sending report to Discord...")
        send_discord_message(full_report)
        logger.info("✅ All checks completed and report sent!")
    else:
        logger.info("💤 No availability found for any of the next 4 days. Skipping Discord notification.") 