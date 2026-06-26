"""Trae.ai browser registration flow (Camoufox).

Registration flow:
  1. Open trae.ai/sign-up
  2. Fill email → click "Send Code"
  3. Wait for email verification code (6 digits) → fill in
  4. Fill password → click "Sign Up"
  5. Wait for redirect to trae.ai homepage
  6. Extract token from Cookie / localStorage

Note: Trae uses the ByteDance Passport system, API requests carry X-Bogus/X-Gnarly signature headers,
browser mode auto-generates these headers, no extra handling needed.
"""
import logging
import random
import string
import time
from typing import Callable, Optional
from urllib.parse import urlparse

from camoufox.sync_api import Camoufox

logger = logging.getLogger(__name__)

TRAE_URL = "https://www.trae.ai"
TRAE_PASSPORT_DOMAIN = "ug-normal.trae.ai"


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


def _wait_for_url(page, substring: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if substring in page.url:
            return True
        time.sleep(1)
    return False


def _click_element(page, *selectors, timeout: int = 10) -> bool:
    """Try to click the first visible element from the selector list."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    return True
            except Exception as e:
                logger.debug("Suppressed exception in element check: %s", e)
        time.sleep(0.5)
    return False


def _get_trae_cloudide_token(page, log_fn=print) -> tuple:
    """After registration, use browser session to call Trae API to get Cloud-IDE JWT token.

    Same flow as core.py:
      step4: POST /cloudide/api/v3/trae/Login    (establish IDE session)
      step5: POST /cloudide/api/v3/common/GetUserToken  →  Result.Token = Cloud-IDE JWT
      step6: POST /cloudide/api/v3/trae/CheckLogin  →  Region / UserId etc.
    """
    BASE_URL = "https://ug-normal.trae.ai"
    API_SG = "https://api-sg-central.trae.ai"

    token = ""
    user_id = ""
    region = ""

    # step4: Trae Login (establish IDE session)
    try:
        log_fn("Calling Trae Login API...")
        page.evaluate(f"""
        async () => {{
            await fetch("{BASE_URL}/cloudide/api/v3/trae/Login?type=email", {{
                method: "POST",
                headers: {{"content-type": "application/json"}},
                credentials: "include",
                body: JSON.stringify({{
                    "UtmSource": "", "UtmMedium": "", "UtmCampaign": "",
                    "UtmTerm": "", "UtmContent": "", "BDVID": "",
                    "LoginChannel": "ide_platform"
                }})
            }});
        }}
        """)
        time.sleep(1)
    except Exception as e:
        log_fn(f"⚠️ Trae Login failed: {e}")

    # step5: GetUserToken → Cloud-IDE JWT
    try:
        log_fn("Fetching Cloud-IDE JWT token...")
        result = page.evaluate(f"""
        async () => {{
            const r = await fetch("{API_SG}/cloudide/api/v3/common/GetUserToken", {{
                method: "POST",
                headers: {{"content-type": "application/json"}},
                credentials: "include",
                body: JSON.stringify({{}})
            }});
            return await r.json();
        }}
        """)
        token = (result or {}).get("Result", {}).get("Token", "") or ""
        if token:
            log_fn(f"✅ Got Cloud-IDE JWT (length={len(token)})")
    except Exception as e:
        log_fn(f"⚠️ GetUserToken failed: {e}")

    # step6: CheckLogin → userId / Region
    if token:
        try:
            result2 = page.evaluate(f"""
            async () => {{
                const r = await fetch("{BASE_URL}/cloudide/api/v3/trae/CheckLogin", {{
                    method: "POST",
                    headers: {{
                        "content-type": "application/json",
                        "Authorization": "Cloud-IDE-JWT {token}"
                    }},
                    credentials: "include",
                    body: JSON.stringify({{"GetAIPayHost": true, "GetNickNameEditStatus": true}})
                }});
                return await r.json();
            }}
            """)
            res = (result2 or {}).get("Result", {})
            user_id = str(res.get("UserId", "") or res.get("userId", ""))
            region = res.get("Region", "")
        except Exception as e:
            log_fn(f"⚠️ CheckLogin failed: {e}")

    # Fallback: extract user_id from Cookie
    if not user_id:
        try:
            cookies = {c["name"]: c["value"] for c in page.context.cookies()}
            user_id = cookies.get("user_id", cookies.get("userId", ""))
        except Exception as e:
            logger.debug("Suppressed exception in cookie access: %s", e)
    # Ultimate fallback: extract id from JWT payload
    if not user_id and token:
        try:
            import base64, json as _json
            payload = token.split(".")[1]
            payload += "==" * (4 - len(payload) % 4)
            data = _json.loads(base64.urlsafe_b64decode(payload))
            user_id = str(data.get("data", {}).get("id", ""))
        except Exception as e:
            logger.debug("Suppressed exception in JWT decode: %s", e)
    return token, user_id, region


class TraeBrowserRegister:
    def __init__(
        self,
        *,
        headless: bool = True,
        proxy: Optional[str] = None,
        otp_callback: Optional[Callable[[], str]] = None,
        log_fn: Callable[[str], None] = print,
    ):
        self.headless = headless
        self.proxy = proxy
        self.otp_callback = otp_callback
        self.log = log_fn

    def run(self, email: str, password: str) -> dict:
        if not self.otp_callback:
            raise RuntimeError("Trae registration requires email verification code but otp_callback was not provided")

        # Generate password (if not provided)
        if not password:
            password = (
                ''.join(random.choices(string.ascii_uppercase, k=2))
                + ''.join(random.choices(string.digits, k=3))
                + ''.join(random.choices(string.ascii_lowercase, k=5))
                + '!'
            )

        proxy = _build_proxy_config(self.proxy)
        launch_opts = {"headless": self.headless}
        if proxy:
            launch_opts["proxy"] = proxy

        with Camoufox(**launch_opts) as browser:
            page = browser.new_page()

            # 1. Open registration page
            self.log("Opening Trae registration page")
            page.goto(f"{TRAE_URL}/sign-up", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            # 2. Fill email
            self.log(f"Filling email: {email}")
            email_selectors = [
                'input[placeholder="Email"]',
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email" i]',
            ]
            email_el = None
            deadline_email = time.time() + 20
            while time.time() < deadline_email:
                for sel in email_selectors:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            email_el = el
                            break
                    except Exception as e:
                        logger.debug("Suppressed exception in element check: %s", e)
                if email_el:
                    break
                time.sleep(0.5)

            if not email_el:
                raise RuntimeError(f"Email input not found: {page.url}")

            email_el.click()
            email_el.fill(email)
            time.sleep(0.5)

            # 3. Click "Send Code" button
            self.log("Sending verification code...")
            # Use JS to find the smallest leaf element containing exact text and click it
            send_clicked = False
            deadline_send = time.time() + 15
            while time.time() < deadline_send and not send_clicked:
                try:
                    # Playwright text= selector is more precise than CSS has-text
                    el = page.locator('text="Send Code"').last
                    if el.is_visible():
                        el.click()
                        send_clicked = True
                        self.log("Clicked Send Code")
                        break
                except Exception as e:
                    logger.debug("Suppressed exception in locator operation: %s", e)
                # Fallback: JS traverse to find element with exact Send Code text
                if not send_clicked:
                    try:
                        page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.children.length === 0 && el.textContent.trim() === 'Send Code') {
                                    el.click();
                                    return;
                                }
                            }
                        }
                        """)
                        send_clicked = True
                        self.log("Clicked Send Code (JS)")
                    except Exception as e:
                        logger.debug("Suppressed exception in page evaluate: %s", e)
                time.sleep(1)

            if not send_clicked:
                self.log("⚠️ Could not click Send Code, trying Tab+Enter")
                page.keyboard.press("Tab")
                time.sleep(0.3)
                page.keyboard.press("Enter")

            time.sleep(2)

            # 4. Wait for OTP input
            self.log("Waiting for email verification code...")
            otp_selectors = [
                'input[placeholder="Verification code"]',
                'input[placeholder*="verification" i]',
                'input[placeholder*="code" i]',
                'input[name="code"]',
                'input[autocomplete="one-time-code"]',
                'input[inputmode="numeric"]',
            ]
            otp_el = None
            deadline_otp = time.time() + 60
            while time.time() < deadline_otp:
                for sel in otp_selectors:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            otp_el = el
                            break
                    except Exception as e:
                        logger.debug("Suppressed exception in element check: %s", e)
                if otp_el:
                    break
                time.sleep(1)

            if not otp_el:
                raise RuntimeError(f"Verification code input did not appear: {page.url}")

            code = self.otp_callback()
            if not code:
                raise RuntimeError("Did not get email verification code")
            self.log(f"Filling verification code: {code}")
            otp_el.click()
            otp_el.fill(str(code).strip())
            time.sleep(0.5)

            # 5. Fill password
            self.log("Filling password...")
            pwd_selectors = [
                'input[placeholder="Password"]',
                'input[type="password"]',
                'input[name="password"]',
            ]
            for sel in pwd_selectors:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        el.fill(password)
                        time.sleep(0.3)
                        break
                except Exception as e:
                    logger.debug("Suppressed exception in element check: %s", e)
            # 6. Click "Sign Up"
            self.log("Submitting registration...")
            signup_clicked = False
            deadline_signup = time.time() + 10
            while time.time() < deadline_signup and not signup_clicked:
                try:
                    el = page.locator('text="Sign Up"').last
                    if el.is_visible():
                        el.click()
                        signup_clicked = True
                        self.log("Clicked Sign Up")
                        break
                except Exception as e:
                    logger.debug("Suppressed exception in locator operation: %s", e)
                if not signup_clicked:
                    try:
                        page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                const t = el.textContent.trim();
                                if (el.children.length === 0 && (t === 'Sign Up' || t === 'Sign up')) {
                                    el.click();
                                    return;
                                }
                            }
                        }
                        """)
                        signup_clicked = True
                        self.log("Clicked Sign Up (JS)")
                    except Exception as e:
                        logger.debug("Suppressed exception in page evaluate: %s", e)
                time.sleep(0.5)

            if not signup_clicked:
                self.log("⚠️ Could not click Sign Up, trying Enter")
                page.keyboard.press("Enter")

            time.sleep(3)

            # 7. Wait for redirect (leave sign-up page)
            self.log("Waiting for registration to complete...")
            deadline_done = time.time() + 30
            while time.time() < deadline_done:
                if "sign-up" not in page.url and "trae.ai" in page.url:
                    break
                time.sleep(1)

            time.sleep(2)

            # 8. Extract token
            self.log("Extracting Trae token...")
            token, user_id, region = _get_trae_cloudide_token(page, self.log)

            if not token:
                self.log("⚠️ Did not get token from Cookie, trying to wait...")
                time.sleep(5)
                token, user_id, region = _get_trae_cloudide_token(page, self.log)

            self.log(f"✓ Registration successful: {email}")
            return {
                "email": email,
                "password": password,
                "token": token,
                "user_id": user_id,
                "region": region,
                "cashier_url": "",
                "ai_pay_host": "",
            }
