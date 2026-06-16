"""Blackbox AI browser registration worker."""
from __future__ import annotations

from typing import Callable


class BlackboxBrowserRegister:
    def __init__(self, *, headless: bool = True, proxy: str | None = None, log_fn: Callable[[str], None] = print):
        self.headless = headless
        self.proxy = proxy
        self.log = log_fn

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
                page.goto("https://www.blackbox.ai/signup", wait_until="networkidle")
                page.wait_for_timeout(2000)

                # Fill in email
                self.log("Filling email...")
                email_input = page.locator('input[type="email"]').first
                if email_input.is_visible():
                    email_input.fill(email)
                else:
                    # Try to find any email input
                    email_input = page.locator('input[placeholder*="email" i]').first
                    if email_input.is_visible():
                        email_input.fill(email)

                # Fill in password
                self.log("Filling password...")
                password_input = page.locator('input[type="password"]').first
                if password_input.is_visible():
                    password_input.fill(password)

                # Click sign up button
                self.log("Clicking sign up...")
                signup_btn = page.locator('button:has-text("Sign Up")').first
                if signup_btn.is_visible():
                    signup_btn.click()
                else:
                    signup_btn = page.locator('button[type="submit"]').first
                    if signup_btn.is_visible():
                        signup_btn.click()

                page.wait_for_timeout(5000)

                # Check if registration succeeded
                self.log("Checking registration result...")
                url = page.url
                if "chat" in url or "dashboard" in url or "app" in url:
                    self.log("Registration appears successful!")
                    return {"email": email, "password": password, "token": "", "name": "Blackbox User"}

                # Check for error messages
                error_msg = page.locator('.error, [role="alert"], .Toastify__toast-body').first
                if error_msg.is_visible():
                    raise RuntimeError(f"Registration error: {error_msg.text_content()}")

                # If we got here, maybe success
                self.log(f"Final URL: {url}")
                return {"email": email, "password": password, "token": "", "name": "Blackbox User"}
        except Exception as e:
            self.log(f"Browser registration failed: {e}")
            raise
