import sys
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

PROMO = "@chatxbt_bot - yo bestie chat with strangers worldwide, it's free, it's anonymous, search up on telegram"

def send_message(page, message):
    selectors = [
        # contenteditable divs (most modern chat apps use these)
        "div[contenteditable='true']",
        "[contenteditable='true']",
        # standard inputs
        "input[placeholder*='message' i]",
        "input[placeholder*='type' i]",
        "input[placeholder*='chat' i]",
        "textarea",
        "input[type='text']",
    ]
    for selector in selectors:
        try:
            input_box = page.locator(selector).first
            input_box.wait_for(timeout=5000)
            input_box.click()
            input_box.fill(message)
            input_box.press("Enter")
            print(f"[{datetime.now()}] Sent via selector: {selector}")
            return
        except:
            continue

    # Last resort: type via keyboard focus
    try:
        page.keyboard.type(message)
        page.keyboard.press("Enter")
        print(f"[{datetime.now()}] Sent via keyboard fallback")
        return
    except:
        pass

    print(f"[{datetime.now()}] WARNING: Could not find message input!")

def run_session(duration_hours=12):
    start_time = datetime.now()
    print(f"[{datetime.now()}] Session started. Running for {duration_hours} hours...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        while (datetime.now() - start_time).total_seconds() < duration_hours * 3600:
            try:
                print(f"[{datetime.now()}] Opening site...")
                page.goto("https://knot.chat", wait_until="domcontentloaded", timeout=60000)

                page.click("button:has-text('Start Chatting')", timeout=15000)

                try:
                    page.click("text=FEMALE", timeout=3000)
                    page.click("text=25+", timeout=3000)
                    page.click("text=START CHATTING", timeout=3000)
                except:
                    pass

                page.wait_for_selector("text=Connected", timeout=30000)
                print(f"[{datetime.now()}] Connected")

                # Wait a bit for chat UI to fully render
                time.sleep(2)

                # Debug: log all inputs including contenteditable
                inputs = page.locator("input, textarea, [contenteditable='true']").all()
                print(f"[{datetime.now()}] Found {len(inputs)} input(s) on page")
                for i, inp in enumerate(inputs):
                    try:
                        ph = inp.get_attribute("placeholder")
                        tp = inp.get_attribute("type")
                        ce = inp.get_attribute("contenteditable")
                        print(f"  Input {i}: type={tp} placeholder={ph} contenteditable={ce}")
                    except:
                        pass

                send_message(page, "F")
                time.sleep(3)
                send_message(page, PROMO)
                print(f"[{datetime.now()}] Promo sent")
                time.sleep(2)

                try:
                    page.click("text=Leave", timeout=5000)
                    try:
                        page.click("text=Leave", timeout=2000)
                    except:
                        pass
                    print(f"[{datetime.now()}] Left chat")
                except:
                    print(f"[{datetime.now()}] Stranger already skipped")

                time.sleep(5)

                try:
                    page.click("text=Restart", timeout=10000)
                except:
                    pass
                time.sleep(2)

            except Exception as e:
                print(f"[{datetime.now()}] Error: {e}")
                time.sleep(10)

        browser.close()
    print(f"[{datetime.now()}] Session complete")

if __name__ == "__main__":
    print(f"[{datetime.now()}] Bot starting immediately...")
    run_session(duration_hours=12)
