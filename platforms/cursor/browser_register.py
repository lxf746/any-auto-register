"""Cursor browser registration flow (Camoufox).

Actual flow:
  1. https://authenticator.cursor.sh/sign-up
  2. Fill FirstName / LastName / Email (same page)
  3. Submit → Cloudflare Turnstile verification (auto/inject)
  4. Receive email OTP (6 digits) → enter
  5. Jump to cursor.com → get WorkosCursorSessionToken
"""
import asyncio
import random, string, time, uuid
from typing import Callable, Optional
from urllib.parse import unquote, urlparse

from camoufox.sync_api import Camoufox
from core.turnstile_pool import create_browser_pool

AUTH = "https://authenticator.cursor.sh"
CURSOR = "https://cursor.com"
TURNSTILE_SITEKEY = "0x4AAAAAAAMNIvC45A4Wjjln"


def _build_proxy_config(proxy: Optional[str]) -> Optional[dict]:
    if not proxy:
        return None
    parsed = urlparse(proxy)
    if not parsed.scheme or not parsed.hostname or not parsed.port:
        return {"server": proxy}
    config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        config["username"] = parsed.username
    if parsed.password:
        config["password"] = parsed.password
    return config


def _get_turnstile_sitekey(page) -> str:
    try:
        sitekey = page.evaluate(
            """() => {
                const node = document.querySelector('[data-sitekey], .cf-turnstile, [data-captcha-sitekey]');
                return node ? (node.getAttribute('data-sitekey') || node.getAttribute('data-captcha-sitekey') || '') : '';
            }"""
        )
        if sitekey:
            return sitekey.strip()
    except Exception:
        pass
    return TURNSTILE_SITEKEY


def _inject_turnstile(page, token: str) -> bool:
    """Inject Turnstile token, compatible with explicit rendering mode (used by Cursor)."""
    safe = token.replace("\\", "\\\\").replace("'", "\\'")
    script = f"""(function() {{
        const token = '{safe}';

        // 1. override window.turnstile API (server calls getResponse in explicit mode)
        if (window.turnstile) {{
            const orig = window.turnstile;
            window.turnstile = new Proxy(orig, {{
                get(target, prop) {{
                    if (prop === 'getResponse') return () => token;
                    if (prop === 'isExpired') return () => false;
                    return Reflect.get(target, prop);
                }}
            }});
        }}

        // 2. Trigger all registered callbacks
        const fns = [
            window._turnstileTokenCallback,
            window.turnstileCallback,
            window.onTurnstileSuccess,
            window.cfTurnstileCallback,
        ];
        fns.forEach(fn => {{ if (typeof fn === 'function') {{ try {{ fn(token); }} catch(e) {{}} }} }});

        // 3. Inject hidden input (compatible with form submit mode)
        const names = ['captcha', 'cf-turnstile-response'];
        const form = document.querySelector('form') || document.body;
        names.forEach(name => {{
            let f = document.querySelector('input[name="' + name + '"], textarea[name="' + name + '"]');
            if (!f) {{ f = document.createElement('input'); f.type = 'hidden'; f.name = name; form.appendChild(f); }}
            f.value = token;
            f.dispatchEvent(new Event('input', {{bubbles: true}}));
            f.dispatchEvent(new Event('change', {{bubbles: true}}));
        }});

        // 4. Try to directly trigger Turnstile internal callback (via iframe postMessage)
        try {{
            document.querySelectorAll('iframe').forEach(iframe => {{
                if (iframe.src && iframe.src.includes('cloudflare.com')) {{
                    iframe.contentWindow.postMessage(JSON.stringify({{
                        source: 'cloudflare-challenge',
                        token: token,
                    }}), '*');
                }}
            }});
        }} catch(e) {{}}

        return true;
    }})();"""
    return bool(page.evaluate(script))


def _click_continue(page) -> bool:
    """Try to click Continue/Next/Sign up button, fallback to Enter."""
    for sel in [
        'button[data-action-button-primary="true"]',
        'button[type="submit"]:not([aria-hidden="true"])',
        'button:has-text("Continue")',
        'button:has-text("Next")',
        'button:has-text("Sign up")',
        'button[type="submit"]',
        'button',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible() and el.is_enabled():
                el.click(timeout=3000)
                return True
        except Exception:
            continue
    return False


def _get_token_from_cookies(page) -> str:
    for cookie in page.context.cookies():
        if cookie["name"] == "WorkosCursorSessionToken":
            return unquote(cookie["value"])
    return ""


def _wait_for_token(page, timeout: int = 120) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        tok = _get_token_from_cookies(page)
        if tok:
            return tok
        time.sleep(1)
    return ""


def _is_cf_full_block(page) -> bool:
    """Detect if CF full-page block is present (different from inline Turnstile widget).
    
    Full-page block characteristics: page only has CF challenge, no normal form content.
    Inline Turnstile: page form displays normally, just has CF iframe inside.
    """
    try:
        content = page.content().lower()
        # Keywords for full-page block (excluding challenges.cloudflare.com, as that's widget script)
        full_block_signals = [
            "just a moment",
            "checking your browser",
            "verifying you are human",
            "verify you are human",
            "performing security verification",
            "security check to access",
            "ray id",
        ]
        if any(kw in content for kw in full_block_signals):
            # Also confirm no normal form is present (form present = inline widget only, not full-page block)
            has_form = bool(page.query_selector('input[name="email"], input[name="firstName"], input[name="otp"], input[name="code"]'))
            if not has_form:
                return True
    except Exception:
        pass
    return False


def _wait_cf_full_block_clear(page, timeout: int = 120, log_fn=print) -> None:
    """Wait for CF full-page block to clear, and actively click Interstitial Turnstile checkbox.
    
    CF full-page block has two types:
    1. Interactive Turnstile: shows checkbox, needs click
    2. Managed Challenge: no-checkbox passive verification, shows circle/loading, just wait
    """
    deadline = time.time() + timeout
    warned = False
    clicked = False
    while time.time() < deadline:
        if not _is_cf_full_block(page):
            break
        if not warned:
            log_fn("Detected Cloudflare full-page block, trying to click verification checkbox...")            
            warned = True
        # Simulate human mouse movement (CF passive detection observes mouse behavior)
        try:
            w = page.viewport_size or {"width": 1280, "height": 720}
            for _ in range(3):
                page.mouse.move(
                    random.randint(100, w["width"] - 100),
                    random.randint(100, w["height"] - 100)
                )
                time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass
        # Try to find CF interstitial Turnstile iframe and click
        if not clicked:
            try:
                for frame in page.frames:
                    if "challenges.cloudflare.com" in frame.url:
                        iframe_el = frame.frame_element()
                        box = iframe_el.bounding_box()
                        if box:
                            cx = box["x"] + 24
                            cy = box["y"] + box["height"] / 2
                            # Simulate human behavior: wait a few seconds to "view page", then slowly move to target
                            time.sleep(random.uniform(1.5, 3.0))
                            # Smoothly move from current position to checkbox (in multiple steps)
                            w = page.viewport_size or {"width": 1280, "height": 720}
                            cur_x = random.randint(200, w["width"] - 200)
                            cur_y = random.randint(200, w["height"] - 200)
                            page.mouse.move(cur_x, cur_y)
                            steps = random.randint(8, 15)
                            for i in range(steps):
                                t = (i + 1) / steps
                                # Bezier curve smooth interpolation
                                mid_x = cur_x + (cx - cur_x) * t + random.randint(-15, 15)
                                mid_y = cur_y + (cy - cur_y) * t + random.randint(-8, 8)
                                page.mouse.move(mid_x, mid_y)
                                time.sleep(random.uniform(0.02, 0.07))
                            # Finally move to target and click
                            page.mouse.move(cx, cy)
                            time.sleep(random.uniform(0.1, 0.3))
                            page.mouse.down()
                            time.sleep(random.uniform(0.08, 0.15))
                            page.mouse.up()
                            log_fn(f"✅ Clicked Interstitial checkbox at: ({cx:.0f}, {cy:.0f})")
                            clicked = True
                            time.sleep(3)
                            break
            except Exception:
                pass
            if not clicked:
                # iframe not loaded yet, wait and retry
                time.sleep(1)
        else:
            # Already clicked, wait for CF passive verification to complete (Managed Challenge may take longer)
            time.sleep(2)


def _has_turnstile_iframe(page) -> bool:
    """Detect if Turnstile iframe exists on page (including inline widget)."""
    try:
        for frame in page.frames:
            if "challenges.cloudflare.com" in frame.url:
                return True
        result = page.evaluate(
            """() => {
                const iframes = document.querySelectorAll('iframe');
                for (const f of iframes) {
                    if (f.src && f.src.includes('challenges.cloudflare.com')) return true;
                }
                return false;
            }"""
        )
        return bool(result)
    except Exception:
        return False

def _is_turnstile_modal_visible(page) -> bool:
    """Detect if Turnstile challenge is visible (using body text, because iframe loads lazily)."""
    try:
        content = page.content().lower()
        signals = [
            "confirm you are human",
            "we need to confirm you are human",
        ]
        if any(s in content for s in signals):
            return True
        # Also check iframe (in some environments iframe may have src)
        return _has_turnstile_iframe(page)
    except Exception:
        return False


def _click_turnstile_in_iframe(page, log_fn=print) -> bool:
    """Directly find Turnstile iframe in Camoufox browser and click checkbox.
    
    Turnstile iframe uses closed Shadow DOM internally, JS querySelector cannot access it.
    Use bounding box coordinate click instead: checkbox is at about 1/4 from left of iframe.
    Returns True if clicked (does not mean Turnstile has passed).
    """
    # Wait for iframe's frame to appear in page.frames list
    deadline = time.time() + 15
    cf_frame_obj = None  # playwright Frame object
    while time.time() < deadline:
        for frame in page.frames:
            if "challenges.cloudflare.com" in frame.url:
                cf_frame_obj = frame
                break
        if cf_frame_obj:
            break
        time.sleep(0.5)

    if not cf_frame_obj:
        log_fn("Cloudflare iframe frame not found, skipping direct click")
        return False

    log_fn(f"Found Turnstile frame: {cf_frame_obj.url[:80]}...")

    # Find iframe DOM element, get bounding box
    iframe_el = None
    for el in page.query_selector_all("iframe"):
        try:
            src = el.get_attribute("src") or ""
            if "cloudflare.com" in src:
                iframe_el = el
                break
        except Exception:
            continue

    if not iframe_el:
        # src may be empty (dynamically set), use frame owner element
        try:
            iframe_el = cf_frame_obj.frame_element()
        except Exception:
            pass

    if iframe_el:
        try:
            # Wait for bounding box to be valid (iframe rendering takes time, can't click when height=0)
            box = None
            for _ in range(10):
                b = iframe_el.bounding_box()
                if b and b["height"] > 10 and b["y"] > 0:
                    box = b
                    break
                time.sleep(1)
            if box:
                # checkbox is on the left side of iframe, approx x=24, y=center
                cx = box["x"] + 24
                cy = box["y"] + box["height"] / 2
                # Simulate human click: move to target then press/release
                page.mouse.move(cx + random.randint(-5, 5), cy + random.randint(-3, 3))
                time.sleep(random.uniform(0.1, 0.25))
                page.mouse.down()
                time.sleep(random.uniform(0.08, 0.15))
                page.mouse.up()
                log_fn(f"✅ Clicked Turnstile checkbox at: ({cx:.0f}, {cy:.0f})")
                time.sleep(1.5)
                # If not passed yet, try once more slightly to the right
                if _is_turnstile_modal_visible(page):
                    page.mouse.move(cx + 12, cy)
                    time.sleep(0.1)
                    page.mouse.down()
                    time.sleep(0.1)
                    page.mouse.up()
                    time.sleep(1)
                return True
            else:
                log_fn("Bounding box invalid (height=0), skipping click")
        except Exception as e:
            log_fn(f"Bounding box click failed: {e}")

    # Fallback: use Playwright frame coordinate click (relative to frame)
    try:
        log_fn("Trying frame coordinate click...")
        cf_frame_obj.locator("body").click(position={"x": 24, "y": 32}, timeout=5000)
        log_fn("✅ Frame coordinate click succeeded")
        return True
    except Exception as e:
        log_fn(f"Frame coordinate click failed: {e}")

    log_fn("All click methods failed")
    return False


def _handle_turnstile(page, log_fn=print, solve_fn=None, wait_secs: int = 12) -> bool:
    """Generic Turnstile handling: detect Turnstile then click checkbox.
    
    Can be called at any stage after form submission, password submission, etc.
    Returns True if Turnstile was detected and handled.
    """
    # Detect if Turnstile appears (wait up to wait_secs seconds)
    deadline = time.time() + wait_secs
    has_turnstile = False
    while time.time() < deadline:
        if _is_turnstile_modal_visible(page):
            has_turnstile = True
            break
        if page.query_selector('input[name="otp"], input[name="code"], input[type="password"]'):
            # Already reached next step, skip
            return False
        time.sleep(1)

    if not has_turnstile:
        return False

    log_fn("Detected Turnstile, trying direct iframe checkbox click...")
    solved = _click_turnstile_in_iframe(page, log_fn)
    if not solved:
        # Try token solver as fallback
        if solve_fn:
            token = solve_fn(page.url, _get_turnstile_sitekey(page))
            if token:
                log_fn(f"Injected Turnstile token ({token[:40]}...)")
                _inject_turnstile(page, token)
                time.sleep(2)
                _click_continue(page)
                time.sleep(3)
                return True
        log_fn("⚠️ Auto-solving failed, waiting for manual pass (max 90s)...")
        dl = time.time() + 90
        while time.time() < dl:
            if not _is_turnstile_modal_visible(page):
                break
            time.sleep(2)
    else:
        time.sleep(3)
        if _is_turnstile_modal_visible(page):
            log_fn("Turnstile still visible, waiting for auto pass...")
            time.sleep(5)
        # If next step not reached after Turnstile passes, try clicking Continue
        if not page.query_selector('input[name="otp"], input[name="code"]'):
            _click_continue(page)
            time.sleep(3)
    return True


class CursorBrowserRegister:
    """Cursor browser form registration (Camoufox + mailbox OTP)."""

    def __init__(
        self,
        *,
        captcha=None,
        headless: bool = True,
        proxy: Optional[str] = None,
        otp_callback: Optional[Callable[[], str]] = None,
        phone_callback: Optional[Callable[[], str]] = None,
        log_fn: Callable[[str], None] = print,
    ):
        self.captcha = captcha
        self.headless = headless
        self.proxy = proxy
        self.otp_callback = otp_callback
        self.phone_callback = phone_callback
        self.log = log_fn

    def _solve_turnstile(self, url: str, sitekey: str) -> Optional[str]:
        """Call Captcha Solver to solve Turnstile, return token or None."""
        if not self.captcha:
            self.log("Captcha Solver not configured, skipping auto-solving")
            return None
        try:
            self.log(f"Calling Captcha Solver ({sitekey[:20]}...)...")
            token = self.captcha.solve_turnstile(url, sitekey or TURNSTILE_SITEKEY)
            if token:
                self.log(f"✅ Solver returned token: {token[:50]}...")
            return token
        except Exception as e:
            self.log(f"⚠️ Captcha Solver failed: {e}")
            return None

    def run(self, email: str, password: str = "") -> dict:
        first = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()
        last = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()

        proxy = _build_proxy_config(self.proxy)
        launch_opts = {"headless": self.headless}
        if proxy:
            launch_opts["proxy"] = proxy

        with Camoufox(**launch_opts) as browser:
            pool = create_browser_pool(
                max_size=1,
                create_context_fn=lambda: browser.new_page(),
            )

            async def _pool_run():
                page = await pool.acquire()
                # Inject MouseEvent screenX/screenY patcher
                # CF Turnstile detects CDP-triggered MouseEvent.screenX == clientX (Chrome bug)
                # Even in Firefox/Camoufox, Playwright internal mouse events may have the same issue
                # Inject override via add_init_script before every page load to bypass Turnstile detection
                # Source: https://github.com/Xewdy444/CDP-bug-MouseEvent-.screenX-.screenY-patcher
                page.add_init_script("""
(function() {
    var screenX = Math.floor(Math.random() * (1200 - 800 + 1)) + 800;
    var screenY = Math.floor(Math.random() * (600 - 400 + 1)) + 400;
    Object.defineProperty(MouseEvent.prototype, 'screenX', {
        get: function() { return this.clientX + screenX; },
        configurable: true
    });
    Object.defineProperty(MouseEvent.prototype, 'screenY', {
        get: function() { return this.clientY + screenY; },
        configurable: true
    });
    // Also patch PointerEvent (CF checks this too)
    Object.defineProperty(PointerEvent.prototype, 'screenX', {
        get: function() { return this.clientX + screenX; },
        configurable: true
    });
    Object.defineProperty(PointerEvent.prototype, 'screenY', {
        get: function() { return this.clientY + screenY; },
        configurable: true
    });
})();
""")

                self.log("Opening Cursor registration page")
                # Must visit with state (containing random nonce) for WorkOS to generate authorization_session_id
                # Without authorization_session_id, form POST to /user_management/initiate_login will 404
                import json, urllib.parse as _up
                _nonce = str(uuid.uuid4())
                _state = _up.quote(json.dumps({"returnTo": "/dashboard", "nonce": _nonce}))
                _redirect = _up.quote("https://cursor.com/api/auth/callback", safe="")
                _signup_url = (
                    f"{AUTH}/sign-up"
                    f"?client_id=client_01GS6W3C96KW4WRS6Z93JCE2RJ"
                    f"&redirect_uri={_redirect}"
                    f"&state={_state}"
                )
                page.goto(_signup_url, wait_until="domcontentloaded", timeout=30000)

                # Only wait for actual CF full-page block (not triggered by inline Turnstile widget)
                _wait_cf_full_block_clear(page, log_fn=self.log)  # default 120s
                # Wait for page to fully load after CF passes (CF pass triggers redirect)
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass

                # Wait for registration form to appear
                self.log("Waiting for registration form...")
                try:
                    page.wait_for_selector(
                        'input[name="firstName"], input[name="first_name"], input[name="email"]',
                        timeout=60000,  # 60s - CF Managed Challenge may take longer
                    )
                except Exception:
                    raise RuntimeError(f"Cursor registration page failed to load form: {page.url}")

                # Fill FirstName / LastName
                for sel, val in [
                    ('input[name="firstName"]', first),
                    ('input[name="first_name"]', first),
                    ('input[name="lastName"]', last),
                    ('input[name="last_name"]', last),
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill(val)
                        time.sleep(0.3)

                # Fill email
                email_sel = 'input[name="email"]'
                try:
                    page.wait_for_selector(email_sel, timeout=5000)
                except Exception:
                    raise RuntimeError("Email input not found")
                self.log(f"Filling email: {email}")
                page.fill(email_sel, email)
                time.sleep(0.5)

                # Click Continue to submit form
                self.log("Clicking Continue")
                clicked = _click_continue(page)
                if not clicked:
                    self.log("Button not found, submitting with Enter")
                    page.keyboard.press("Enter")

                # --- Turnstile handling ---
                # Strategy: directly click iframe checkbox in Camoufox browser
                # External Solver is useless (it opens its own browser but won't submit form, won't see Turnstile)
                self.log("Waiting for Turnstile verification...")
                turnstile_deadline = time.time() + 15
                has_turnstile = False
                while time.time() < turnstile_deadline:
                    if _is_turnstile_modal_visible(page):
                        has_turnstile = True
                        break
                    if page.query_selector('input[name="otp"], input[name="code"]'):
                        self.log("Already jumped to OTP page, skipping Turnstile")
                        break
                    time.sleep(1)

                if has_turnstile:
                    self.log("Detected Turnstile, trying direct iframe checkbox click...")
                    solved = _click_turnstile_in_iframe(page, self.log)
                    if not solved:
                        token = self._solve_turnstile(page.url, _get_turnstile_sitekey(page))
                        if token:
                            self.log(f"Injected Turnstile token ({token[:40]}...)")
                            _inject_turnstile(page, token)
                            time.sleep(2)
                            _click_continue(page)
                            time.sleep(3)
                        else:
                            self.log("⚠️ Auto-solving failed, waiting for manual pass (max 90s)...")
                            dl = time.time() + 90
                            while time.time() < dl:
                                if not _is_turnstile_modal_visible(page):
                                    break
                                if page.query_selector('input[name="otp"], input[name="code"]'):
                                    break
                                time.sleep(2)
                    else:
                        # Wait for Turnstile processing after click
                        time.sleep(3)
                        if _is_turnstile_modal_visible(page):
                            self.log("Turnstile still visible, waiting for auto pass...")
                            time.sleep(5)

                # --- Handle password setup page (Cursor requires password after Turnstile passes) ---
                try:
                    page.wait_for_selector('input[type="password"]', timeout=8000)
                    use_password = password or (
                        ''.join(random.choices(string.ascii_uppercase, k=2))
                        + ''.join(random.choices(string.digits, k=3))
                        + ''.join(random.choices(string.ascii_lowercase, k=5))
                        + '!'
                    )
                    self.log("Detected password setup page, filling password...")
                    for el in page.query_selector_all('input[type="password"]'):
                        if el.is_visible():
                            el.fill(use_password)
                            time.sleep(0.3)
                    password = use_password
                    time.sleep(0.5)
                    _click_continue(page)
                    time.sleep(2)
                except Exception:
                    pass  # No password page, skip

                # --- Turnstile may appear again after password submission (e.g., "Welcome to Cursor" page) ---
                _handle_turnstile(page, self.log, self._solve_turnstile)

                # --- Detect phone number verification page ("Phone number" + "Send verification code") ---
                try:
                    phone_input = page.query_selector('input[type="tel"], input[placeholder*="555"], input[autocomplete="tel"]')
                    if not phone_input:
                        # Wait a few seconds to see if it jumps to phone page
                        page.wait_for_selector('input[type="tel"]', timeout=4000)
                        phone_input = page.query_selector('input[type="tel"]')
                except Exception:
                    phone_input = None

                if phone_input and phone_input.is_visible():
                    if self.phone_callback:
                        phone_number = self.phone_callback()
                        if phone_number:
                            self.log(f"Detected phone number verification page, filling phone: {phone_number[:4]}****")
                            phone_input.click()
                            phone_input.fill(str(phone_number).strip())
                            time.sleep(0.5)
                            _click_continue(page)
                            time.sleep(3)
                            # Wait for SMS code input box (6 digits)
                            try:
                                page.wait_for_selector(
                                    'input[autocomplete="one-time-code"], input[inputmode="numeric"], input[maxlength="1"]',
                                    timeout=30000
                                )
                                sms_code = self.phone_callback()  # Reuse callback to get SMS code
                                if sms_code:
                                    self.log(f"Filling SMS code: {sms_code}")
                                    for digit in str(sms_code).strip():
                                        page.keyboard.press(digit)
                                        time.sleep(0.1)
                                    time.sleep(1)
                                    page.keyboard.press("Enter")
                                    time.sleep(3)
                            except Exception as e:
                                self.log(f"⚠️ Failed to wait for SMS code: {e}")
                    else:
                        raise RuntimeError(
                            "Cursor registration requires phone verification, but phone_callback is not configured."
                            "Please configure SMS service in RegisterConfig.extra, or manually complete phone verification."
                        )

                # Wait for OTP input box (WorkOS email-verification page uses 6 separate cells)
                self.log("Waiting for OTP input field...")
                OTP_SELECTORS = [
                    'input[name="otp"]',
                    'input[name="code"]',
                    'input[autocomplete="one-time-code"]',
                    'input[inputmode="numeric"]',
                    'input[maxlength="1"]',
                    'input[type="text"]',
                    'input[type="number"]',
                ]
                otp_input = None
                deadline_otp = time.time() + 60
                while time.time() < deadline_otp:
                    # Also check if URL has reached email-verification
                    if "email-verification" in page.url or "verify" in page.url:
                        for sel in OTP_SELECTORS:
                            el = page.query_selector(sel)
                            if el and el.is_visible():
                                otp_input = el
                                break
                        if otp_input:
                            break
                    else:
                        for sel in OTP_SELECTORS[:2]:  # Quickly check the first two
                            el = page.query_selector(sel)
                            if el and el.is_visible():
                                otp_input = el
                                break
                        if otp_input:
                            break
                    time.sleep(1)

                if not otp_input:
                    raise RuntimeError(f"OTP input field did not appear (url={page.url})")

                if not self.otp_callback:
                    raise RuntimeError("Cursor registration requires email OTP but otp_callback was not provided")
                self.log("Waiting for email OTP")
                otp = self.otp_callback()
                if not otp:
                    raise RuntimeError("Failed to get OTP")
                self.log(f"OTP: {otp}")

                # WorkOS 6-cell OTP: click first cell then type digit by digit
                try:
                    otp_input.click()
                    time.sleep(0.3)
                except Exception:
                    pass
                for digit in str(otp).strip():
                    page.keyboard.press(digit)
                    time.sleep(random.uniform(0.08, 0.2))
                time.sleep(1)
                # WorkOS auto-submits, no need to click Continue; if not submitted, press Enter
                if "email-verification" in page.url:
                    page.keyboard.press("Enter")
                time.sleep(5)

                # Wait for Session Token
                self.log("Waiting for WorkosCursorSessionToken")
                tok = _wait_for_token(page, timeout=60)
                if not tok:
                    raise RuntimeError("Failed to get WorkosCursorSessionToken")

                from platforms.cursor.switch import get_cursor_user_info
                user_info = get_cursor_user_info(tok) or {}
                resolved_email = user_info.get("email", email)
                self.log(f"Registration successful: {resolved_email}")
                return {"email": resolved_email, "password": "", "token": tok}

            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_pool_run())
            finally:
                loop.run_until_complete(pool.close())
                loop.close()
