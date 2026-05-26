import sys
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import requests

# Force logs to show in Railway
sys.stdout.reconfigure(line_buffering=True)

PROMO = "@chatxbt_bot - yo bestie chat with strangers worldwide, it's free, it's anonymous, search up on telegram"

# ⬇️ Fill these in
TELEGRAM_BOT_TOKEN = "8884986704:AAFU3qi5V9tARlukk4xmAMKK9dNpoliymAE"  # from @BotFather
TELEGRAM_CHAT_ID = "642484532"      # from @userinfobot

def send_screenshot(page, label="screenshot"):
    try:
        screenshot = page.screenshot()
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": label},
            files={"photo": ("screen.png", screenshot, "image/png")}
        )
        print(f"[{datetime.now()}] Screenshot sent to Telegram: {label}")
    except Exception as e:
        print(f"[{datetime.now()}] Screenshot failed: {e}")

def send_message(page, message):
    selectors = [
        "div[contenteditable='true']",
        "[contenteditable='true']",
        "input[placeholder*='message' i]",
        "input[placeholder*='type' i]",
        "input[placeholder*='chat' i]",
        "textarea",
        "input[type='text']",
    ]
    for selector in selectors:
        try:
            input_box = page.locator(selector).first
            input_box.wait_for(timeout=1000)
            input_box.click()
            input_box.fill(message)
            input_box.press("Enter")
            print(f"[{datetime.now()}] Sent via selector: {selector}")
            return
        except:
            continue

    # Try clicking bottom-center of page where chat input usually is, then type
    try:
        page.mouse.click(760, 600)
        time.sleep(0.5)
        page.keyboard.type(message)
        page.keyboard.press("Enter")
        print(f"[{datetime.now()}] Sent via mouse click + keyboard fallback")
        return
    except:
        pass

    # Try JS to find and focus any input/contenteditable
    try:
        page.evaluate("""
            const el = document.querySelector(
                "input:not([type='hidden']), textarea, [contenteditable='true']"
            );
            if (el) { el.focus(); }
        """)
        time.sleep(0.5)
        page.keyboard.type(message)
        page.keyboard.press("Enter")
        print(f"[{datetime.now()}] Sent via JS focus + keyboard fallback")
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

                # Wait for chat UI to fully render
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

                # Screenshot after connecting - see what bot sees
                send_screenshot(page, "After connected")

                send_message(page, "F")
                time.sleep(3)
                send_message(page, PROMO)
                print(f"[{datetime.now()}] Promo sent")

                # Screenshot after sending promo - confirm message appeared
                send_screenshot(page, "After promo sent")

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
                # Screenshot on error to see what went wrong
                send_screenshot(page, f"Error: {str(e)[:50]}")
                time.sleep(10)

        browser.close()
    print(f"[{datetime.now()}] Session complete")

if __name__ == "__main__":
    print(f"[{datetime.now()}] Bot starting immediately...")
    run_session(duration_hours=12)
