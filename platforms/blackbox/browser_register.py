"""Blackbox AI browser registration worker."""
from __future__ import annotations

from typing import Callable


class BlackboxBrowserRegister:
    def __init__(self, *, headless: bool = True, proxy: str | None = None, log_fn: Callable[[str], None] = print, otp_callback: Callable[[], str] | None = None):
        self.headless = headless
        self.proxy = proxy
        self.log = log_fn
        self.otp_callback = otp_callback

    def _get_token(self, page) -> str:
        """Extract session token from cookies or localStorage."""
        cookies = page.context.cookies()
        for cookie in cookies:
            if any(k in cookie.get("name", "").lower() for k in ["token", "auth", "session", "jwt"]):
                return cookie.get("value", "")
        try:
            token = page.evaluate("() => localStorage.getItem('token') || localStorage.getItem('auth_token') || localStorage.getItem('session') || ''")
            if token:
                return token
        except Exception:
            pass
        return ""

    def _check_login(self, page, email: str, password: str) -> bool:
        """Check if user is logged in by looking for authenticated UI elements."""
        try:
            sign_out = page.locator('text=Sign Out').first
            if sign_out.is_visible():
                return True
            user_menu = page.locator('[data-testid="user-menu"], .user-menu, .avatar').first
            if user_menu.is_visible():
                return True
            if "/chat" in page.url or "/dashboard" in page.url or "/keys" in page.url:
                return True
            return False
        except Exception:
            return False

    def run(self, email: str, password: str) -> dict:
        self.log(f"Starting Blackbox AI registration for {email}...")
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless, proxy={"server": self.proxy} if self.proxy else None)
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()

                # Navigate to signup
                self.log("Navigating to signup page...")
                page.goto("https://www.blackbox.ai/signup", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                # Fill in email
                self.log("Filling email...")
                email_input = page.locator('input[type="email"]').first
                if email_input.is_visible():
                    email_input.fill(email)
                else:
                    email_input = page.locator('input[placeholder*="email" i]').first
                    if email_input.is_visible():
                        email_input.fill(email)

                # Fill in password
                self.log("Filling password...")
                password_input = page.locator('input[type="password"]').first
                if password_input.is_visible():
                    password_input.fill(password)

                # Click CREATE ACCOUNT
                self.log("Clicking CREATE ACCOUNT...")
                try:
                    page.locator('text=CREATE ACCOUNT').first.click()
                except Exception:
                    page.locator('button[type="submit"]').first.click()

                page.wait_for_timeout(5000)

                # Check if verification page appeared
                verify_input = page.locator('input[placeholder*="code" i]').first
                if verify_input.is_visible():
                    self.log("Verification code required")
                    if not self.otp_callback:
                        raise RuntimeError("Verification code required but no otp_callback provided")
                    
                    code = self.otp_callback()
                    if not code:
                        raise RuntimeError("Failed to get verification code")
                    
                    self.log(f"Entering verification code: {code}")
                    verify_input.fill(code)
                    page.wait_for_timeout(500)
                    
                    # Click VERIFY EMAIL
                    self.log("Clicking VERIFY EMAIL...")
                    try:
                        page.locator('text=VERIFY EMAIL').first.click()
                    except Exception:
                        page.locator('button:has-text("VERIFY")').first.click()
                    
                    page.wait_for_timeout(10000)

                # Check if registration succeeded
                self.log("Checking registration result...")
                if self._check_login(page, email, password):
                    self.log("Registration successful!")
                    token = self._get_token(page)
                    return {"email": email, "password": password, "token": token, "name": "Blackbox User"}

                self.log(f"Final URL: {page.url}")
                token = self._get_token(page)
                return {"email": email, "password": password, "token": token, "name": "Blackbox User"}
        except Exception as e:
            self.log(f"Browser registration failed: {e}")
            raise

    def login(self, email: str, password: str) -> dict:
        """Verify login works by opening a fresh browser and logging in."""
        self.log(f"Verifying login for {email}...")
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless, proxy={"server": self.proxy} if self.proxy else None)
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()

                page.goto("https://www.blackbox.ai/login", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                email_input = page.locator('input[type="email"]').first
                if email_input.is_visible():
                    email_input.fill(email)

                password_input = page.locator('input[type="password"]').first
                if password_input.is_visible():
                    password_input.fill(password)

                login_btn = page.locator('button:has-text("Log In")').first
                if login_btn.is_visible():
                    login_btn.click()
                else:
                    page.locator('button[type="submit"]').first.click()

                page.wait_for_timeout(5000)

                if self._check_login(page, email, password):
                    self.log("Login successful!")
                    token = self._get_token(page)
                    return {"email": email, "password": password, "token": token, "logged_in": True}
                else:
                    self.log(f"Login failed. URL: {page.url}")
                    return {"email": email, "password": password, "token": "", "logged_in": False}
        except Exception as e:
            self.log(f"Login verification failed: {e}")
            return {"email": email, "password": password, "token": "", "logged_in": False}
