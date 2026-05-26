import sys
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

# Force logs to show in Railway
sys.stdout.reconfigure(line_buffering=True)

PROMO = "@chatxbt_bot - yo bestie chat with strangers worldwide, it's free, it's anonymous, search up on telegram"

def send_message(page, message):
    input_box = page.locator("input[placeholder*='message']")
    input_box.wait_for(timeout=10000)
    input_box.fill(message)
    input_box.press("Enter")

def run_session(duration_hours=12):
    start_time = datetime.now()
    print(f"[{datetime.now()}] Session started. Running for {duration_hours} hours...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        while (datetime.now() - start_time).total_seconds() < duration_hours * 3600:
            try:
                print(f"[{datetime.now()}] Opening site...")
                page.goto(
                    "https://knot.chat",
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                # Start chatting
                page.click(
                    "button:has-text('Start Chatting')",
                    timeout=15000
                )
                # Preference modal (optional)
                try:
                    page.click("text=FEMALE", timeout=3000)
                    page.click("text=25+", timeout=3000)
                    page.click("text=START CHATTING", timeout=3000)
                except:
                    pass
                # Wait for stranger connection
                page.wait_for_selector(
                    "text=Connected",
                    timeout=30000
                )
                print(f"[{datetime.now()}] Connected")
                # Send F immediately
                send_message(page, "F")
                # Ignore all incoming messages
                time.sleep(3)
                # Send promo
                send_message(page, PROMO)
                print(f"[{datetime.now()}] Promo sent")
                # Wait 2 sec
                time.sleep(2)
                # Leave chat
                try:
                    page.click("text=Leave", timeout=5000)
                    try:
                        page.click("text=Leave", timeout=2000)
                    except:
                        pass
                    print(f"[{datetime.now()}] Left chat")
                except:
                    print(f"[{datetime.now()}] Stranger already skipped")
                # Wait before next chat
                time.sleep(5)
                # Restart
                try:
                    page.click("text=Restart", timeout=10000)
                except:
                    pass
                time.sleep(2)
            except Exception as e:
                print(f"[{datetime.now()}] Error: {e}")
                try:
                    page.screenshot(path=f"error_{int(time.time())}.png")
                except:
                    pass
                time.sleep(10)
        browser.close()
    print(f"[{datetime.now()}] Session complete")

if __name__ == "__main__":
    print(f"[{datetime.now()}] Bot starting immediately...")
    run_session(duration_hours=12)
