"""Blackbox AI OAuth browser flow (Google OAuth)."""
from __future__ import annotations

import time

from core.oauth_browser import (
    OAUTH_PROVIDER_LABELS,
    OAuthBrowser,
    finalize_oauth_email,
    oauth_provider_hint_text,
)


BLACKBOX_URL = "https://www.blackbox.ai"
BLACKBOX_APP_URL = "https://app.blackbox.ai"


def register_with_browser_oauth(
    *,
    proxy: str | None = None,
    oauth_provider: str = "",
    email_hint: str = "",
    timeout: int = 300,
    log_fn=print,
    headless: bool = False,
    chrome_user_data_dir: str = "",
    chrome_cdp_url: str = "",
) -> dict:
    """Blackbox AI OAuth browser flow.

    Blackbox currently only supports Google OAuth.
    """
    provider = (oauth_provider or "").strip().lower() or "google"
    provider_label = OAUTH_PROVIDER_LABELS.get(provider, provider.title()) if provider else "Google"
    method_text = oauth_provider_hint_text(provider)

    with OAuthBrowser(
        proxy=proxy,
        headless=headless,
        chrome_user_data_dir=chrome_user_data_dir,
        chrome_cdp_url=chrome_cdp_url,
        log_fn=log_fn,
    ) as browser:
        # Go to login page
        log_fn("Navigating to Blackbox login page...")
        browser.goto(f"{BLACKBOX_URL}/login", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Click OAuth provider button
        log_fn(f"Clicking {provider_label} OAuth button...")
        if not browser.try_click_provider(provider):
            # Fallback: try exact selectors
            page = browser.active_page()
            try:
                page.locator('button:has-text("GOOGLE")').first.click()
            except Exception:
                raise RuntimeError(f"{provider_label} OAuth button not found on Blackbox login page")
        time.sleep(2)

        # In headless mode without chrome profile, we need user to complete OAuth
        if not chrome_user_data_dir and not chrome_cdp_url:
            log_fn(f"Please complete {method_text} OAuth in browser, maximum wait {timeout} seconds")
            if email_hint:
                log_fn(f"Please confirm the final login account email is: {email_hint}")

        # Wait for redirect to app.blackbox.ai (success) or back to blackbox
        log_fn("Waiting for OAuth completion...")
        deadline = time.time() + timeout
        success = False
        while time.time() < deadline:
            url = browser.active_page().url
            # Successful redirect patterns
            if "app.blackbox.ai" in url or "ref=login-success" in url or "ref=signup-success" in url:
                success = True
                break
            # If we're back on blackbox but not on login page, we might be logged in
            if "blackbox.ai" in url and "login" not in url and "signup" not in url:
                success = True
                break
            time.sleep(1)

        if not success:
            raise RuntimeError(f"Blackbox OAuth did not complete within {timeout} seconds")

        time.sleep(3)
        page = browser.active_page()

        # Extract token from localStorage
        token = ""
        try:
            token = page.evaluate("() => localStorage.getItem('token') || ''")
        except Exception:
            pass
        if not token:
            try:
                token = page.evaluate("() => localStorage.getItem('accessToken') || ''")
            except Exception:
                pass
        if not token:
            try:
                token = page.evaluate("() => localStorage.getItem('auth_token') || ''")
            except Exception:
                pass

        # Extract session token from cookies (next-auth.session-token)
        session_token = ""
        try:
            cookies = browser.context.cookies()
            for c in cookies:
                if c.get("name") == "next-auth.session-token":
                    session_token = c.get("value", "")
                    break
        except Exception:
            pass

        # Try to get email from cookies or page
        actual_email = ""
        try:
            # First check cookies for email
            cookies = browser.context.cookies()
            for c in cookies:
                if c.get("name") == "userEmail":
                    actual_email = c.get("value", "")
                    break
        except Exception:
            pass

        if not actual_email:
            try:
                # Check account-store in localStorage
                account_store = page.evaluate("() => localStorage.getItem('account-store') || '{}'")
                import json
                acc_data = json.loads(account_store)
                current_account = acc_data.get("state", {}).get("currentAccount", "")
                if current_account and "@" in current_account:
                    actual_email = current_account
            except Exception:
                pass

        if not actual_email:
            try:
                # Look for email in account settings or profile
                page.goto(f"{BLACKBOX_APP_URL}/settings", wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                text = page.inner_text("body")
                for line in text.split("\n"):
                    if "@" in line and "." in line:
                        actual_email = line.strip()
                        break
            except Exception:
                pass

        # Get subscription info
        subscription_status = ""
        try:
            sub_cache = page.evaluate("() => localStorage.getItem('subscription-cache') || '{}'")
            import json
            sub_data = json.loads(sub_cache)
            subscription_status = sub_data.get("status", "")
        except Exception:
            pass

        resolved_email = finalize_oauth_email(actual_email, email_hint, "Blackbox")

        return {
            "email": resolved_email,
            "password": "",  # OAuth accounts don't have a password
            "token": token or session_token,
            "name": "Blackbox User",
            "oauth_provider": provider,
            "subscription_status": subscription_status,
        }


# Backward-compat alias
register_with_manual_oauth = register_with_browser_oauth
