"""fireworks.ai protocol registration core implementation.

Proven working flow:
  1. Browser signup → POST /signup with form
  2. Poll tempmail.lol for verification email → extract confirm URL
  3. Browser confirm → navigate to confirm URL (JS auto-fires POST /signup/confirm)
  4. Browser login → two-step form (email → password) with Enter key
  5. Browser onboarding → profile form + survey skip
  6. Navigate to API keys page → create API key
  7. Validate API key against api.fireworks.ai
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Optional

from curl_cffi import requests as curl_requests
import requests as std_requests

FIREWORKS_APP = "https://app.fireworks.ai"
FIREWORKS_API = "https://api.fireworks.ai"
COGNITO_ENDPOINT = "https://cognito-idp.us-west-2.amazonaws.com"
COGNITO_CLIENT_ID = "sueas7prsfrdp16nantbeqcjv"

TEMPMAIL_API = "https://api.tempmail.lol/v2"


class FireworksAuthError(Exception):
    def __init__(self, message: str, code: str = "", status_code: int = 0, raw: Any = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.raw = raw


class FireworksRateLimitError(FireworksAuthError):
    pass


def _dc(page) -> None:
    """Remove cookie consent overlay from page."""
    try:
        page.evaluate(
            "document.querySelectorAll('.cky-consent-container,[data-cky-tag]').forEach(e=>e.remove())"
        )
    except Exception:
        pass


class FireworksRegister:
    def __init__(self, proxy: str | None = None, log_fn: Callable[[str], None] = print):
        self._proxy = proxy
        self._log = log_fn

    def log(self, msg: str) -> None:
        self._log(msg)

    # ── Step 1: Signup via browser ──

    def browser_signup(self, email: str, password: str, *, headless: bool = True) -> None:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            ctx = browser.new_context()
            page = ctx.new_page()

            page.goto(f"{FIREWORKS_APP}/signup", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            _dc(page)
            time.sleep(1)

            page.fill('input[name="email"]', email)
            time.sleep(1)
            page.click('button[type="submit"]:has-text("Next")', force=True)
            time.sleep(5)
            _dc(page)

            page.fill('input[name="password"]', password)
            time.sleep(1)
            page.fill('input[name="confirmPassword"]', password)
            time.sleep(1)
            _dc(page)

            page.click('button[type="submit"]:has-text("Create Account")', force=True)
            time.sleep(5)

            self.log("  Signup submitted via browser")
            browser.close()

    # ── Step 2: Poll tempmail.lol for verification email ──

    def wait_for_verification_email(
        self, token: str, *, timeout: int = 300, poll_interval: int = 5
    ) -> dict | None:
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = std_requests.get(f"{TEMPMAIL_API}/inbox", params={"token": token}, timeout=10)
                if r.status_code == 200:
                    msgs = r.json().get("emails") or []
                    if msgs:
                        body = str(msgs[0].get("body", "")) + str(msgs[0].get("html", ""))
                        urls = re.findall(r'https?://[^\s<>"\'\\]+', body)
                        for u in urls:
                            u = u.rstrip(".,;:!?)")
                            if "signup/confirm" in u:
                                m = re.search(r'confirmation_code=(\d+)', u)
                                confirmation_code = m.group(1) if m else ""
                                m = re.search(r'user_name=([^&]+)', u)
                                user_name = m.group(1) if m else ""
                                return {
                                    "url": u,
                                    "user_name": user_name,
                                    "confirmation_code": confirmation_code,
                                }
            except Exception:
                pass
            elapsed = int(time.time() - start)
            if elapsed % 30 == 0:
                self.log(f"  {elapsed}s waiting for email...")
            time.sleep(poll_interval)
        return None

    # ── Step 3: Confirm email via browser (JS auto-fires POST /signup/confirm) ──

    def browser_confirm_email(self, confirm_url: str, *, headless: bool = True) -> bool:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            ctx = browser.new_context()
            page = ctx.new_page()

            confirm_result = {}

            def on_resp(resp):
                if "signup/confirm" in resp.url and resp.request.method == "POST":
                    try:
                        confirm_result["body"] = resp.text()
                    except Exception:
                        pass

            page.on("response", on_resp)

            page.goto(confirm_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            body = confirm_result.get("body", "")
            success = '"success":true' in body
            if success:
                self.log("  Email confirmed (server-side account created)")
            else:
                self.log(f"  Confirm response: {body[:200]}")

            browser.close()
            return success

    # ── Steps 4-6: Login → Onboarding → API Keys (single browser session) ──

    def browser_login_onboard_create_key(
        self,
        email: str,
        password: str,
        account_id: str,
        *,
        headless: bool = True,
    ) -> dict[str, Any]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            ctx = browser.new_context()
            page = ctx.new_page()

            # ── Login ──
            self.log("  Logging in...")
            page.goto(f"{FIREWORKS_APP}/login/email", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            _dc(page)

            page.fill('input[name="email"]', email)
            time.sleep(1)
            _dc(page)
            page.locator('button[type="submit"]:has-text("Next")').click(force=True)

            try:
                page.wait_for_selector('input[name="password"]', state="visible", timeout=15000)
            except Exception:
                browser.close()
                raise FireworksAuthError("Password field not found after email step")

            time.sleep(2)
            _dc(page)
            page.fill('input[name="password"]', password)
            time.sleep(2)
            page.press('input[name="password"]', 'Enter')

            try:
                page.wait_for_url("^(?!.*login).*$", timeout=30000)
            except Exception:
                pass
            time.sleep(5)

            if "/login" in page.url:
                browser.close()
                raise FireworksAuthError("Login failed - still on login page")

            self.log(f"  Login OK -> {page.url}")

            # ── Onboarding ──
            if "/onboarding" in page.url or "/account" not in page.url:
                page.goto(f"{FIREWORKS_APP}/onboarding", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)
                _dc(page)

            if "/onboarding" in page.url:
                self.log("  Completing onboarding...")

                # Profile form
                acc = page.locator('input[name="accountId"]')
                if acc.is_visible():
                    acc.fill(account_id)
                    time.sleep(0.5)

                fn = page.locator('input[name="firstName"]')
                if fn.is_visible():
                    fn.fill("Test")
                    time.sleep(0.5)

                ln = page.locator('input[name="lastName"]')
                if ln.is_visible():
                    ln.fill("User")
                    time.sleep(0.5)

                # Click checkbox (must use .last and scroll)
                agree_btn = page.locator('button[role="checkbox"]').last
                try:
                    agree_btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    agree_btn.click(force=True)
                    time.sleep(1)
                except Exception:
                    pass

                _dc(page)
                time.sleep(1)

                # Submit profile form via Continue
                cont = page.locator("button:has-text('Continue')")
                if cont.count() > 0 and cont.first.is_visible():
                    cont.first.click(force=True)
                    time.sleep(5)

                # Survey steps - click Skip or first option
                for step in range(10):
                    _dc(page)
                    if "/onboarding" not in page.url:
                        break

                    # Try Skip first
                    skip = page.locator("button:has-text('Skip')")
                    if skip.count() > 0 and skip.first.is_visible():
                        skip.first.click(force=True)
                        time.sleep(3)
                        continue

                    # Try clicking first option button
                    clicked = page.evaluate("""() => {
                        const buttons = document.querySelectorAll('button');
                        for (const b of buttons) {
                            const text = (b.innerText || '').trim();
                            const rect = b.getBoundingClientRect();
                            if (text && text.length > 2 && text.length < 120 &&
                                rect.width > 0 && rect.height > 0 &&
                                !['Continue','Back','Skip','Previous slide','Next slide','Blog','Docs'].includes(text)) {
                                b.click();
                                return text.substring(0, 40);
                            }
                        }
                        return null;
                    }""")
                    if clicked:
                        time.sleep(1)
                        _dc(page)
                        # Try Continue
                        cont = page.locator("button:has-text('Continue')")
                        if cont.count() > 0 and cont.first.is_visible():
                            cont.first.click(force=True)
                            time.sleep(3)
                    else:
                        break

                self.log(f"  Onboarding done -> {page.url}")

            # ── Create API Key ──
            self.log("  Creating API key...")
            api_key = None

            # Navigate to API keys via sidebar link (direct URL returns 404)
            page.evaluate("""() => {
                const links = document.querySelectorAll('a');
                for (const a of links) {
                    if (a.innerText?.trim() === 'API Keys') { a.click(); return; }
                }
            }""")
            time.sleep(10)
            _dc(page)

            if "/login" in page.url:
                browser.close()
                raise FireworksAuthError("Session expired during API key creation")

            # Click "Create API Key" button → opens dropdown menu
            create_btn = page.locator("button:has-text('Create API Key')")
            if create_btn.count() > 0 and create_btn.first.is_visible():
                create_btn.first.click(force=True)
                time.sleep(3)
                _dc(page)

                # Click "API Key" from dropdown menu
                menu_item = page.locator('[role="menuitem"]:has-text("API Key")')
                if menu_item.count() > 0 and menu_item.first.is_visible():
                    menu_item.first.click(force=True)
                else:
                    # Fallback: click "API Key" text in menu
                    page.evaluate("""() => {
                        const items = document.querySelectorAll('[role="menuitem"], [role="menu"] button, [data-state="open"] button');
                        for (const item of items) {
                            if (item.innerText?.trim() === 'API Key') {
                                item.click();
                                return;
                            }
                        }
                    }""")
                time.sleep(5)
                _dc(page)

                # Fill name in dialog
                name_input = page.locator('input[name="name"]')
                for i in range(name_input.count()):
                    inp = name_input.nth(i)
                    try:
                        if inp.is_visible():
                            inp.fill("auto-register")
                            time.sleep(1)
                            break
                    except Exception:
                        pass

                # Click "Generate Key" button in dialog
                dialog = page.locator('[role="dialog"]')
                if dialog.count() > 0:
                    gen_btn = dialog.locator('button:has-text("Generate"), button[type="submit"]')
                    if gen_btn.count() > 0 and gen_btn.first.is_visible():
                        gen_btn.first.click(force=True)
                    else:
                        # Fallback: press Enter
                        page.keyboard.press("Enter")
                else:
                    page.keyboard.press("Enter")
                time.sleep(5)
                _dc(page)

                # Extract API key from "Copy your API Key" dialog
                body = page.inner_text("body")
                key_match = re.search(r'fw_[a-zA-Z0-9_-]{20,}', body)
                if key_match:
                    api_key = key_match.group(0)
                    self.log(f"  API key created: {api_key[:20]}...")

                    # Close the key display dialog
                    close_btn = dialog.locator('button:has-text("Close"), button:has-text("Done")')
                    if close_btn.count() > 0 and close_btn.first.is_visible():
                        close_btn.first.click(force=True)
                        time.sleep(2)

            # Get account info from cookie
            account_id_result = ""
            for c in ctx.cookies():
                if c["name"] == "auth_v2_user_context":
                    import urllib.parse
                    decoded = urllib.parse.unquote(c["value"])
                    try:
                        ctx_data = json.loads(decoded)
                        account_id_result = ctx_data.get("accountID", "")
                    except Exception:
                        pass
                    break

            browser.close()

            return {
                "api_key": api_key or "",
                "account_id": account_id_result,
            }

    # ── Validate API key ──

    def check_api_key_valid(self, api_key: str) -> dict[str, Any]:
        try:
            r = curl_requests.get(
                f"{FIREWORKS_API}/inference/v1/models",
                headers={"authorization": f"Bearer {api_key}", "accept": "application/json"},
                impersonate="chrome131",
                timeout=15,
            )
            if r.status_code == 200:
                models = [m.get("id", "") for m in r.json().get("data", []) if m.get("id")]
                self.log(f"  Valid, {len(models)} models")
                return {"valid": True, "models": models}
            # 412 = account suspended (free tier) but key is valid
            if r.status_code == 412:
                self.log(f"  Key valid but account suspended (free tier)")
                return {"valid": True, "models": [], "warning": "Account suspended (free tier)"}
            return {"valid": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    # ── Full registration flow ──

    def register(
        self,
        email: str,
        password: str,
        *,
        api_key_name: str = "auto-register",
        account_id: str = "",
        mailbox_token: str = "",
        mailbox_create_fn: Callable[[], tuple[str, str]] | None = None,
        headless: bool = True,
        max_verify_wait: int = 300,
    ) -> dict[str, Any]:
        import uuid

        self.log("=== Fireworks.ai registration ===")

        if not account_id:
            account_id = f"fw-{uuid.uuid4().hex[:8]}"

        # 1. Signup
        self.log("\n[1/6] Signup...")
        self.browser_signup(email, password, headless=headless)

        # 2. Wait for verification email
        self.log("\n[2/6] Waiting for verification email...")
        if mailbox_create_fn:
            email, mailbox_token = mailbox_create_fn()
        elif not mailbox_token:
            raise FireworksAuthError("No mailbox_token or mailbox_create_fn provided")

        confirm = self.wait_for_verification_email(mailbox_token, timeout=max_verify_wait)
        if not confirm:
            raise FireworksAuthError("Verification email not received")
        self.log(f"  Confirm URL: {confirm['url'][:80]}...")

        # 3. Confirm email (creates server-side account)
        self.log("\n[3/6] Confirm email...")
        self.browser_confirm_email(confirm["url"], headless=headless)

        # 4-6. Login → Onboarding → Create API key (single browser session)
        self.log("\n[4-6/6] Login → Onboarding → Create API key...")
        result = self.browser_login_onboard_create_key(
            email, password, account_id, headless=headless
        )

        api_key = result.get("api_key", "")

        # 7. Validate
        validation = self.check_api_key_valid(api_key) if api_key else {"valid": False, "error": "No API key"}

        return {
            "email": email,
            "password": password,
            "api_key": api_key,
            "account_id": result.get("account_id", ""),
            "user_id": confirm.get("user_name", ""),
            "validation": validation,
        }
