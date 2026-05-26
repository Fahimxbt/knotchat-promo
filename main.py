import sys
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

# Force logs to show in Railway
sys.stdout.reconfigure(line_buffering=True)

PROMO = "@chatxbt_bot - yo bestie chat with strangers worldwide, it's free, it's anonymous, search up on telegram"


def get_all_frames(page):
    """Get main page and all iframe frames."""
    frames = [page.main_frame]
    for frame in page.frames:
        if frame != page.main_frame:
            frames.append(frame)
    return frames


def find_input_in_frames(page):
    """Search for chat input across all frames including iframes."""
    frames = get_all_frames(page)

    for frame in frames:
        try:
            selectors = [
                "input[placeholder*='message' i]",
                "input[placeholder*='type' i]",
                "input[placeholder*='chat' i]",
                "input[type='text']",
                "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='checkbox']):not([type='radio']):not([disabled])",
                "textarea:not([readonly]):not([disabled])",
                "[contenteditable='true']",
                "[role='textbox']",
                "div[contenteditable='true']",
                "textarea",
            ]

            for selector in selectors:
                try:
                    elements = frame.locator(selector).all()
                    for el in elements:
                        try:
                            if el.is_visible(timeout=1000):
                                return {'found': True, 'element': el, 'frame': frame, 'selector': selector}
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            print(f"[{datetime.now()}] Frame search error: {e}")
            continue

    return {'found': False}


def find_input_with_js(page):
    """Use JavaScript to pierce shadow DOM and find inputs."""
    try:
        result = page.evaluate("""
            () => {
                function searchShadowDOM(root) {
                    const results = [];
                    const selectors = [
                        "input[placeholder*='message' i]",
                        "input[placeholder*='type' i]",
                        "input[placeholder*='chat' i]",
                        "input[type='text']",
                        "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='checkbox']):not([type='radio']):not([disabled])",
                        "textarea:not([readonly]):not([disabled])",
                        "[contenteditable='true']",
                        "[role='textbox']",
                        "[contenteditable]"
                    ];

                    for (const sel of selectors) {
                        const els = root.querySelectorAll(sel);
                        for (const el of els) {
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            if (rect.width > 0 && rect.height > 0 && 
                                style.display !== 'none' && style.visibility !== 'hidden' &&
                                style.opacity !== '0' && !el.disabled) {
                                results.push({
                                    tag: el.tagName,
                                    class: el.className,
                                    id: el.id,
                                    placeholder: el.placeholder || '',
                                    contenteditable: el.contentEditable || 'false',
                                    type: el.type || ''
                                });
                            }
                        }
                    }

                    const allElements = root.querySelectorAll('*');
                    for (const el of allElements) {
                        if (el.shadowRoot) {
                            results.push(...searchShadowDOM(el.shadowRoot));
                        }
                    }

                    return results;
                }

                return searchShadowDOM(document);
            }
        """)

        if result and len(result) > 0:
            print(f"[{datetime.now()}] JS search found {len(result)} input(s):")
            for i, inp in enumerate(result[:5]):
                print(f"  {i}: tag={inp.get('tag')} type={inp.get('type')} class={inp.get('class')} id={inp.get('id')} placeholder={inp.get('placeholder')}")
            return True
        return False
    except Exception as e:
        print(f"[{datetime.now()}] JS search error: {e}")
        return False


def send_message_v2(page, message, max_retries=3):
    """Send message with iframe and shadow DOM support."""

    for attempt in range(max_retries):
        print(f"[{datetime.now()}] Message send attempt {attempt + 1}/{max_retries}")

        # Try 1: Standard selectors in all frames
        frame_result = find_input_in_frames(page)
        if frame_result.get('found'):
            el = frame_result['element']
            frame = frame_result['frame']
            selector = frame_result['selector']

            try:
                el.scroll_into_view_if_needed()
                el.click()
                time.sleep(0.5)

                if "contenteditable" in selector:
                    el.click()
                    page.keyboard.type(message)
                else:
                    el.fill(message)

                page.keyboard.press("Enter")
                print(f"[{datetime.now()}] Sent via frame search: {selector}")
                return True
            except Exception as e:
                print(f"[{datetime.now()}] Frame send failed: {e}")

        # Try 2: Shadow DOM piercing via JS
        if find_input_with_js(page):
            try:
                page.evaluate("""
                    () => {
                        function findAndFocus(root) {
                            const selectors = [
                                "input[placeholder*='message' i]",
                                "input[placeholder*='type' i]",
                                "input[placeholder*='chat' i]",
                                "input[type='text']",
                                "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='checkbox']):not([type='radio']):not([disabled])",
                                "textarea:not([readonly]):not([disabled])",
                                "[contenteditable='true']",
                                "[role='textbox']"
                            ];

                            for (const sel of selectors) {
                                const els = root.querySelectorAll(sel);
                                for (const el of els) {
                                    const rect = el.getBoundingClientRect();
                                    const style = window.getComputedStyle(el);
                                    if (rect.width > 0 && rect.height > 0 && 
                                        style.display !== 'none' && style.visibility !== 'hidden' &&
                                        style.opacity !== '0' && !el.disabled) {
                                        el.focus();
                                        el.click();
                                        return true;
                                    }
                                }
                            }

                            const allElements = root.querySelectorAll('*');
                            for (const el of allElements) {
                                if (el.shadowRoot) {
                                    if (findAndFocus(el.shadowRoot)) return true;
                                }
                            }
                            return false;
                        }
                        return findAndFocus(document);
                    }
                """)

                time.sleep(0.5)
                page.keyboard.type(message)
                page.keyboard.press("Enter")
                print(f"[{datetime.now()}] Sent via shadow DOM piercing")
                return True
            except Exception as e:
                print(f"[{datetime.now()}] Shadow DOM send failed: {e}")

        # Wait before retry
        if attempt < max_retries - 1:
            wait_time = 3 * (attempt + 1)
            print(f"[{datetime.now()}] Waiting {wait_time}s before retry...")
            time.sleep(wait_time)

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
        ".chat-active",
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


def wait_for_chat_input_v2(page, max_wait_seconds=30):
    """Wait for chat input with iframe and shadow DOM support."""
    print(f"[{datetime.now()}] Waiting for chat input (with iframe/shadow DOM support)...")

    start_time = time.time()
    check_interval = 2

    while time.time() - start_time < max_wait_seconds:
        # Check standard inputs
        try:
            inputs = page.locator("input, textarea, [contenteditable='true'], [role='textbox']").all()
            visible_count = 0
            for inp in inputs:
                try:
                    if inp.is_visible():
                        visible_count += 1
                except:
                    pass

            if visible_count > 0:
                print(f"[{datetime.now()}] Found {visible_count} visible input(s) after {int(time.time() - start_time)}s")
                return True
        except:
            pass

        # Check iframes
        try:
            frames = get_all_frames(page)
            for frame in frames:
                try:
                    frame_inputs = frame.locator("input, textarea, [contenteditable='true']").all()
                    for inp in frame_inputs:
                        try:
                            if inp.is_visible(timeout=1000):
                                print(f"[{datetime.now()}] Found input in iframe after {int(time.time() - start_time)}s")
                                return True
                        except:
                            pass
                except:
                    pass
        except:
            pass

        # Check shadow DOM
        try:
            if find_input_with_js(page):
                print(f"[{datetime.now()}] Found input via shadow DOM after {int(time.time() - start_time)}s")
                return True
        except:
            pass

        time.sleep(check_interval)

    print(f"[{datetime.now()}] Timeout: No chat input found after {max_wait_seconds}s")
    return False


def detect_page_state(page):
    """Detect which screen we're currently on."""
    try:
        state = page.evaluate("""
            () => {
                const html = document.body.innerHTML.toLowerCase();
                return {
                    hasAuthModal: html.includes('sign in anonymously') || html.includes('continue with google') || html.includes('phone number'),
                    hasGenderSelection: html.includes('male') && html.includes('female') && html.includes('age group'),
                    hasChatInterface: html.includes('type a message') || html.includes('send') || html.includes('leave'),
                    hasSecurityCheck: html.includes('security check') || html.includes('cloudflare') || html.includes('verifying'),
                    hasStartButton: html.includes('start chatting'),
                    url: window.location.href,
                    title: document.title
                };
            }
        """)
        print(f"[{datetime.now()}] Page state: {state}")
        return state
    except Exception as e:
        print(f"[{datetime.now()}] Error detecting page state: {e}")
        return {}


def log_page_structure(page):
    """Debug: Log page structure including iframes and shadow DOM."""
    try:
        structure = page.evaluate("""
            () => {
                function countShadowRoots(root) {
                    let count = 0;
                    const all = root.querySelectorAll('*');
                    for (const el of all) {
                        if (el.shadowRoot) {
                            count++;
                            count += countShadowRoots(el.shadowRoot);
                        }
                    }
                    return count;
                }

                return {
                    title: document.title,
                    url: window.location.href,
                    iframes: document.querySelectorAll('iframe').length,
                    shadowRoots: countShadowRoots(document),
                    bodyChildren: document.body ? document.body.children.length : 0,
                    hasChatClasses: {
                        chat: document.querySelectorAll('[class*="chat"]').length,
                        message: document.querySelectorAll('[class*="message"]').length,
                        input: document.querySelectorAll('[class*="input"]').length,
                        composer: document.querySelectorAll('[class*="composer"]').length
                    }
                };
            }
        """)
        print(f"[{datetime.now()}] Page structure: {structure}")
    except Exception as e:
        print(f"[{datetime.now()}] Error getting page structure: {e}")


def run_session(duration_hours=12):
    start_time = datetime.now()
    print(f"[{datetime.now()}] Session started. Running for {duration_hours} hours...")

    with sync_playwright() as p:
        # Launch with stealth args to avoid detection
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1280,800',
            ]
        )

        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            color_scheme='light',
        )

        # Add script to remove webdriver property
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        while (datetime.now() - start_time).total_seconds() < duration_hours * 3600:
            try:
                print(f"[{datetime.now()}] Opening site...")
                page.goto("https://knot.chat", wait_until="domcontentloaded", timeout=60000)

                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                time.sleep(3)

                # Detect current page state
                state = detect_page_state(page)

                # Step 1: Click Start Chatting (if on homepage)
                if state.get('hasStartButton', False):
                    start_selectors = [
                        "text=Start",
                        "text=Chat",
                        "text=Begin",
                        "button:has-text('Chat')",
                        "[data-testid='start-chat']",
                        ".start-button",
                        "#start-chat",
                        "button:has-text('Start Chatting')"
                    ]
                    click_element_with_fallbacks(
                        page, 
                        "button:has-text('Start Chatting')", 
                        start_selectors, 
                        timeout=15000, 
                        label="Start Chatting"
                    )
                    time.sleep(2)
                    state = detect_page_state(page)

                # Step 2: Handle Auth Modal (Sign In Anonymously)
                if state.get('hasAuthModal', False):
                    print(f"[{datetime.now()}] Auth modal detected, clicking Sign In Anonymously...")

                    # Try multiple strategies to find and click the anonymous button
                    auth_clicked = False

                    # Strategy 1: Direct text match
                    auth_selectors = [
                        "text=Sign In Anonymously",
                        "text=Anonymous",
                        "text=Sign In",
                        "button:has-text('Anonymous')",
                        "button:has-text('Sign In')",
                    ]
                    for sel in auth_selectors:
                        try:
                            page.click(sel, timeout=3000)
                            print(f"[{datetime.now()}] Clicked auth via: {sel}")
                            auth_clicked = True
                            break
                        except:
                            continue

                    # Strategy 2: Look for buttons in the modal/dialog
                    if not auth_clicked:
                        try:
                            buttons = page.locator("button, [role='button']").all()
                            for btn in buttons:
                                try:
                                    text = btn.inner_text()
                                    if text and ('anonymous' in text.lower() or 'sign in' in text.lower()):
                                        btn.click()
                                        print(f"[{datetime.now()}] Clicked auth button with text: {text}")
                                        auth_clicked = True
                                        break
                                except:
                                    continue
                        except Exception as e:
                            print(f"[{datetime.now()}] Auth button search error: {e}")

                    # Strategy 3: JS click on first button in modal
                    if not auth_clicked:
                        try:
                            page.evaluate("""
                                () => {
                                    const modal = document.querySelector('dialog, [role="dialog"], .modal, [class*="modal"]');
                                    if (modal) {
                                        const btn = modal.querySelector('button');
                                        if (btn) { btn.click(); return true; }
                                    }
                                    // Try any button that looks like primary action
                                    const buttons = document.querySelectorAll('button');
                                    for (const btn of buttons) {
                                        const style = window.getComputedStyle(btn);
                                        if (style.backgroundColor.includes('rgb(220, 95, 95)') || 
                                            style.backgroundColor.includes('rgb(220.95.95)')) {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                    return false;
                                }
                            """)
                            print(f"[{datetime.now()}] Attempted JS auth click")
                            auth_clicked = True
                        except Exception as e:
                            print(f"[{datetime.now()}] JS auth click error: {e}")

                    if not auth_clicked:
                        print(f"[{datetime.now()}] FAILED: Could not click Sign In Anonymously")
                        time.sleep(5)
                        continue

                    time.sleep(3)

                    # Wait for security check
                    print(f"[{datetime.now()}] Waiting for security check...")
                    time.sleep(10)

                    # Check state again
                    state = detect_page_state(page)

                # Step 3: Handle Security Check / CAPTCHA
                if state.get('hasSecurityCheck', False):
                    print(f"[{datetime.now()}] Security check/CAPTCHA detected, waiting longer...")
                    time.sleep(15)  # Give more time for CAPTCHA
                    state = detect_page_state(page)

                    if state.get('hasSecurityCheck', False):
                        print(f"[{datetime.now()}] CAPTCHA still present, skipping iteration...")
                        time.sleep(5)
                        continue

                # Step 4: Gender/age selection
                if state.get('hasGenderSelection', False):
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

                    time.sleep(3)
                    state = detect_page_state(page)

                # Step 5: Verify we're actually in chat before waiting for input
                if not state.get('hasChatInterface', False):
                    print(f"[{datetime.now()}] Not in chat interface yet, current state: {state}")
                    # Try clicking Start Chatting again if we see the button
                    if state.get('hasStartButton', False):
                        click_element_with_fallbacks(
                            page, 
                            "button:has-text('Start Chatting')", 
                            ["text=Start", "text=Chat"], 
                            timeout=5000, 
                            label="Retry Start Chatting"
                        )
                        time.sleep(3)
                        state = detect_page_state(page)

                    if not state.get('hasChatInterface', False):
                        print(f"[{datetime.now()}] Still not in chat, skipping iteration...")
                        time.sleep(5)
                        continue

                # Step 6: Wait for connection indicator
                wait_for_connection(page)

                # Step 7: Wait for chat input
                chat_input_ready = wait_for_chat_input_v2(page, max_wait_seconds=30)

                if not chat_input_ready:
                    print(f"[{datetime.now()}] Chat input not found, checking page state...")
                    state = detect_page_state(page)

                    if not state.get('hasChatInterface', False):
                        print(f"[{datetime.now()}] Not in chat interface, skipping to next iteration...")
                    else:
                        print(f"[{datetime.now()}] In chat but no input found, may need different selector...")

                    time.sleep(5)
                    continue

                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                # Debug logging
                log_page_structure(page)

                # Step 8: Send messages
                send_message_v2(page, "F")
                time.sleep(3)
                send_message_v2(page, PROMO)
                print(f"[{datetime.now()}] Promo sent")
                time.sleep(2)

                # Step 9: Leave chat
                leave_selectors = [
                    "text=leave",
                    "text=Skip",
                    "text=skip",
                    "text=Next",
                    "text=Disconnect",
                    "button:has-text('Leave')",
                    "button:has-text('Skip')",
                    "[data-action='leave']",
                    ".leave-button",
                    "text=Leave (Esc)"
                ]
                click_element_with_fallbacks(
                    page, 
                    "text=Leave", 
                    leave_selectors, 
                    timeout=5000, 
                    label="Leave"
                )

                time.sleep(5)

                # Step 10: Restart
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
