import sys
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

# Force logs to show in Railway
sys.stdout.reconfigure(line_buffering=True)

PROMO = "@chatxbt_bot - yo bestie chat with strangers worldwide, it's free, it's anonymous, search up on telegram"


def send_message(page, message):
    """Send a message to the chat input with multiple fallback strategies."""

    # Comprehensive list of selectors for chat inputs
    selectors = [
        # Contenteditable (most modern chat apps use this)
        "div[contenteditable='true']",
        "[contenteditable='true']",
        "div[role='textbox']",
        "[role='textbox']",
        # Input fields with various placeholders
        "input[placeholder*='message' i]",
        "input[placeholder*='type' i]",
        "input[placeholder*='chat' i]",
        "input[placeholder*='send' i]",
        "input[placeholder*='text' i]",
        "input[placeholder*='say' i]",
        # Generic inputs
        "textarea",
        "textarea:not([readonly])",
        "input[type='text']",
        "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='checkbox']):not([type='radio'])",
        # Common chat app specific selectors
        "[data-testid='message-input']",
        "[data-testid='chat-input']",
        "[data-testid='composer']",
        ".message-input",
        ".chat-input",
        ".composer",
        "#message-input",
        "#chat-input",
        # Form-based inputs
        "form input",
        "form textarea",
        "form [contenteditable]",
    ]

    # Try each selector
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
            if count == 0:
                continue

            # Check first 3 matches for visibility
            for i in range(min(count, 3)):
                el = locator.nth(i)
                try:
                    if el.is_visible(timeout=2000):
                        el.scroll_into_view_if_needed()
                        el.click()
                        time.sleep(0.5)

                        if "contenteditable" in selector or "role='textbox'" in selector:
                            el.click()
                            page.keyboard.type(message)
                        else:
                            el.fill(message)

                        page.keyboard.press("Enter")
                        print(f"[{datetime.now()}] Sent via selector: {selector} (index {i})")
                        return True
                except Exception:
                    continue
        except Exception:
            continue

    # JS fallback — comprehensive DOM search
    try:
        result = page.evaluate("""
            (function() {
                const selectors = [
                    "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='checkbox']):not([type='radio']):not([disabled])",
                    "textarea:not([readonly]):not([disabled])",
                    "[contenteditable='true']",
                    "[role='textbox']",
                    "[contenteditable]"
                ];

                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.width > 0 && rect.height > 0 && 
                            style.display !== 'none' && style.visibility !== 'hidden' &&
                            style.opacity !== '0' && !el.disabled) {
                            el.focus();
                            el.click();
                            return {found: true, tag: el.tagName, class: el.className, id: el.id};
                        }
                    }
                }
                return {found: false};
            })()
        """)

        if result and result.get('found'):
            print(f"[{datetime.now()}] JS fallback found element: {result}")
            time.sleep(0.5)
            page.keyboard.type(message)
            page.keyboard.press("Enter")
            print(f"[{datetime.now()}] Sent via JS focus + keyboard fallback")
            return True
    except Exception as e:
        print(f"[{datetime.now()}] JS fallback error: {e}")

    print(f"[{datetime.now()}] WARNING: Could not find message input!")
    return False


def click_element_with_fallbacks(page, primary_selector, fallback_selectors, timeout=5000, label="element"):
    """Try to click an element with multiple fallback selectors."""
    all_selectors = [primary_selector] + fallback_selectors

    for selector in all_selectors:
        try:
            page.click(selector, timeout=timeout)
            print(f"[{datetime.now()}] Clicked {label} via: {selector}")
            return True
        except Exception:
            continue

    print(f"[{datetime.now()}] Could not click {label}")
    return False


def wait_for_connection(page, timeout_per_selector=10000):
    """Wait for chat connection with multiple indicators."""
    connection_selectors = [
        "text=Connected",
        "text=connected",
        "text=Chatting",
        "text=Stranger",
        "text=Online",
        ".connected",
        "[data-status='connected']",
        ".chat-active"
    ]

    for sel in connection_selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout_per_selector)
            print(f"[{datetime.now()}] Connected (detected via: {sel})")
            return True
        except Exception:
            continue

    print(f"[{datetime.now()}] Warning: Could not detect connection state, continuing anyway...")
    return False


def log_page_inputs(page):
    """Debug: Log all input elements found on the page."""
    try:
        inputs = page.locator("input, textarea, [contenteditable='true'], [role='textbox']").all()
        print(f"[{datetime.now()}] Found {len(inputs)} input(s) on page")
        for i, inp in enumerate(inputs[:10]):
            try:
                ph = inp.get_attribute("placeholder") or "N/A"
                tp = inp.get_attribute("type") or "N/A"
                ce = inp.get_attribute("contenteditable") or "N/A"
                role = inp.get_attribute("role") or "N/A"
                cls = inp.get_attribute("class") or "N/A"
                visible = inp.is_visible()
                print(f"  Input {i}: type={tp} placeholder={ph} contenteditable={ce} role={role} class={cls} visible={visible}")
            except Exception as e:
                print(f"  Input {i}: Error getting attributes: {e}")
    except Exception as e:
        print(f"[{datetime.now()}] Error listing inputs: {e}")


def log_html_snippet(page):
    """Debug: Log HTML snippet around potential input areas."""
    try:
        html_snippet = page.evaluate("""
            (function() {
                const possibleAreas = document.querySelectorAll(
                    'footer, .chat-footer, .input-area, .message-area, form, [class*="input"], [class*="chat"]'
                );
                let html = '';
                for (const area of possibleAreas) {
                    if (area.innerHTML.length > 0) {
                        html += area.tagName + (area.className ? '.' + area.className : '') + ':\n' + area.innerHTML.substring(0, 500) + '\n\n';
                    }
                }
                return html || document.body.innerHTML.substring(0, 2000);
            })()
        """)
        print(f"[{datetime.now()}] HTML snippet: {html_snippet[:1500]}")
    except Exception as e:
        print(f"[{datetime.now()}] Error getting HTML: {e}")


def run_session(duration_hours=12):
    start_time = datetime.now()
    print(f"[{datetime.now()}] Session started. Running for {duration_hours} hours...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        while (datetime.now() - start_time).total_seconds() < duration_hours * 3600:
            try:
                print(f"[{datetime.now()}] Opening site...")
                page.goto("https://knot.chat", wait_until="domcontentloaded", timeout=60000)

                # Wait for page to fully load
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                time.sleep(3)

                # Click Start Chatting
                start_selectors = [
                    "text=Start",
                    "text=Chat",
                    "text=Begin",
                    "button:has-text('Chat')",
                    "[data-testid='start-chat']",
                    ".start-button",
                    "#start-chat"
                ]
                click_element_with_fallbacks(
                    page, 
                    "button:has-text('Start Chatting')", 
                    start_selectors, 
                    timeout=15000, 
                    label="Start Chatting"
                )

                # Gender/age selection
                try:
                    page.click("text=FEMALE", timeout=3000)
                    print(f"[{datetime.now()}] Selected FEMALE")
                except Exception:
                    pass

                try:
                    page.click("text=25+", timeout=3000)
                    print(f"[{datetime.now()}] Selected 25+")
                except Exception:
                    pass

                try:
                    page.click("text=START CHATTING", timeout=3000)
                    print(f"[{datetime.now()}] Clicked START CHATTING")
                except Exception:
                    pass

                # Wait for connection
                wait_for_connection(page)

                # Give chat UI time to render
                time.sleep(5)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                # Debug logging
                log_page_inputs(page)
                log_html_snippet(page)

                # Send messages
                send_message(page, "F")
                time.sleep(3)
                send_message(page, PROMO)
                print(f"[{datetime.now()}] Promo sent")
                time.sleep(2)

                # Leave chat
                leave_selectors = [
                    "text=leave",
                    "text=Skip",
                    "text=skip",
                    "text=Next",
                    "text=Disconnect",
                    "button:has-text('Leave')",
                    "button:has-text('Skip')",
                    "[data-action='leave']",
                    ".leave-button"
                ]
                click_element_with_fallbacks(
                    page, 
                    "text=Leave", 
                    leave_selectors, 
                    timeout=5000, 
                    label="Leave"
                )

                time.sleep(5)

                # Restart
                restart_selectors = [
                    "text=restart",
                    "text=Start New",
                    "text=New Chat",
                    "text=Chat Again",
                    "button:has-text('Restart')",
                    "button:has-text('New')",
                    "[data-action='restart']"
                ]
                click_element_with_fallbacks(
                    page, 
                    "text=Restart", 
                    restart_selectors, 
                    timeout=10000, 
                    label="Restart"
                )

                time.sleep(2)

            except Exception as e:
                print(f"[{datetime.now()}] Error: {e}")
                time.sleep(10)

        browser.close()
        print(f"[{datetime.now()}] Session complete")


if __name__ == "__main__":
    print(f"[{datetime.now()}] Bot starting immediately...")
    run_session(duration_hours=12)
