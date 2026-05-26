import sys
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

# Force logs to show in Railway
sys.stdout.reconfigure(line_buffering=True)

PROMO = "@chatxbt_bot - yo bestie chat with strangers worldwide, it's free, it's anonymous, search up on telegram"


def send_message(page, message, max_retries=3):
    """Send a message to the chat input with retry logic and multiple fallback strategies."""

    for attempt in range(max_retries):
        print(f"[{datetime.now()}] Message send attempt {attempt + 1}/{max_retries}")

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
                () => {
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
                }
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

        # Wait before retry
        if attempt < max_retries - 1:
            wait_time = 3 * (attempt + 1)
            print(f"[{datetime.now()}] Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            # Try to wait for any new elements to appear
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass

    print(f"[{datetime.now()}] WARNING: Could not find message input after {max_retries} attempts!")
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


def wait_for_chat_input(page, max_wait_seconds=30):
    """Wait for chat input to appear with polling."""
    print(f"[{datetime.now()}] Waiting for chat input to appear...")

    start_time = time.time()
    check_interval = 2

    while time.time() - start_time < max_wait_seconds:
        try:
            # Check for any input-like elements
            inputs = page.locator("input, textarea, [contenteditable='true'], [role='textbox']").all()
            visible_inputs = []

            for inp in inputs:
                try:
                    if inp.is_visible():
                        visible_inputs.append(inp)
                except:
                    pass

            if visible_inputs:
                print(f"[{datetime.now()}] Found {len(visible_inputs)} visible input(s) after {int(time.time() - start_time)}s")
                return True

            # Also check via JS for any editable elements
            has_input = page.evaluate("""
                () => {
                    const all = document.querySelectorAll('input, textarea, [contenteditable="true"], [role="textbox"]');
                    for (const el of all) {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.width > 0 && rect.height > 0 && 
                            style.display !== 'none' && style.visibility !== 'hidden') {
                            return true;
                        }
                    }
                    return false;
                }
            """)

            if has_input:
                print(f"[{datetime.now()}] Found input via JS check after {int(time.time() - start_time)}s")
                return True

        except Exception as e:
            print(f"[{datetime.now()}] Error checking inputs: {e}")

        time.sleep(check_interval)

    print(f"[{datetime.now()}] Timeout: No chat input found after {max_wait_seconds}s")
    return False


def log_page_inputs(page):
    """Debug: Log all input elements found on the page."""
    try:
        inputs = page.locator("input, textarea, [contenteditable='true'], [role='textbox']").all()
        print(f"[{datetime.now()}] Found {len(inputs)} total input(s) on page")

        visible_count = 0
        for i, inp in enumerate(inputs[:15]):  # Check up to 15
            try:
                ph = inp.get_attribute("placeholder") or "N/A"
                tp = inp.get_attribute("type") or "N/A"
                ce = inp.get_attribute("contenteditable") or "N/A"
                role = inp.get_attribute("role") or "N/A"
                cls = inp.get_attribute("class") or "N/A"
                id_attr = inp.get_attribute("id") or "N/A"
                visible = inp.is_visible()
                if visible:
                    visible_count += 1
                print(f"  Input {i}: tag={inp.evaluate('el => el.tagName')} type={tp} placeholder={ph} contenteditable={ce} role={role} class={cls} id={id_attr} visible={visible}")
            except Exception as e:
                print(f"  Input {i}: Error: {e}")

        print(f"[{datetime.now()}] {visible_count} visible input(s) found")
    except Exception as e:
        print(f"[{datetime.now()}] Error listing inputs: {e}")


def log_page_structure(page):
    """Debug: Log key page structure elements."""
    try:
        structure = page.evaluate("""
            () => {
                const result = {
                    title: document.title,
                    bodyChildren: document.body.children.length,
                    iframes: document.querySelectorAll('iframe').length,
                    shadowHosts: document.querySelectorAll('*').length,
                    hasChatClasses: {
                        chat: document.querySelectorAll('[class*="chat"]').length,
                        message: document.querySelectorAll('[class*="message"]').length,
                        input: document.querySelectorAll('[class*="input"]').length,
                        composer: document.querySelectorAll('[class*="composer"]').length
                    }
                };
                return result;
            }
        """)
        print(f"[{datetime.now()}] Page structure: {structure}")
    except Exception as e:
        print(f"[{datetime.now()}] Error getting page structure: {e}")


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

                # CRITICAL FIX: Wait for chat input to actually appear
                # The input loads dynamically after connection
                chat_input_ready = wait_for_chat_input(page, max_wait_seconds=30)

                if not chat_input_ready:
                    print(f"[{datetime.now()}] Chat input not found, skipping to next iteration...")
                    time.sleep(5)
                    continue

                # Additional wait for network to settle
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                # Debug logging
                log_page_structure(page)
                log_page_inputs(page)

                # Send messages with retry
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
