"""State machine logic for ChatGPT browser registration."""

import re
import time
import uuid
from urllib.parse import urljoin

from ..constants import (
    OPENAI_AUTH,
    CHATGPT_APP,
    PLATFORM_LOGIN_ENTRY,
)
from .selectors import (
    EMAIL_INPUT_SELECTORS,
    PASSWORD_INPUT_SELECTORS,
    OTP_INPUT_SELECTORS,
    EMAIL_SUBMIT_SELECTORS,
)
from .browser_utils import (
    find_first_selector,
    wait_for_any_selector,
    click_first,
    is_login_password_url,
    build_manual_flow_state,
    get_visible_page_text,
    has_signup_registration_choice,
    click_passwordless_login_if_available,
    extract_auth_error_text,
    fill_input_like_user,
    submit_form_with_fallback,
    requires_registration_navigation,
    get_cookies,
    seed_browser_device_id,
    get_page_oauth_url,
    oauth_url_matches_state,
    random_chrome_ua,
    browser_pause,
    dump_debug,
    browser_fetch,
    build_browser_headers,
    generate_datadog_trace_headers,
)
from .sentinel import build_browser_sentinel_token


def infer_page_type(data: dict | None, current_url: str = "") -> str:
    raw = data if isinstance(data, dict) else {}
    page_type = str(((raw.get("page") or {}).get("type")) or "").strip().lower().replace("-", "_").replace("/", "_").replace(" ", "_")
    if page_type:
        return page_type
    url = (current_url or "").lower()
    if "code=" in url:
        return "oauth_callback"
    if "create-account/password" in url:
        return "create_account_password"
    if "email-verification" in url or "email-otp" in url:
        return "email_otp_verification"
    if "about-you" in url:
        return "about_you"
    if "log-in/password" in url:
        return "login_password"
    if "sign-in-with-chatgpt" in url and "consent" in url:
        return "consent"
    if "workspace" in url and "select" in url:
        return "workspace_selection"
    if "organization" in url and "select" in url:
        return "organization_selection"
    if "add-phone" in url:
        return "add_phone"
    if "/api/oauth/oauth2/auth" in url:
        return "external_url"
    if "chatgpt.com" in url:
        return "chatgpt_home"
    return ""


def extract_flow_state(data: dict | None, current_url: str = "") -> dict:
    raw = data if isinstance(data, dict) else {}
    page = raw.get("page") or {}
    payload = page.get("payload") or {}
    continue_url = str(raw.get("continue_url") or payload.get("url") or "").strip()
    if continue_url and continue_url.startswith("/"):
        continue_url = urljoin(OPENAI_AUTH, continue_url)
    effective_url = continue_url or current_url
    return {
        "page_type": infer_page_type(raw, effective_url),
        "continue_url": continue_url,
        "method": str(raw.get("method") or payload.get("method") or "GET").upper(),
        "current_url": effective_url,
        "payload": payload if isinstance(payload, dict) else {},
        "raw": raw,
    }


def extract_code_from_url(url: str) -> str:
    if not url or "code=" not in url:
        return ""
    try:
        from urllib.parse import parse_qs, urlparse as _up

        parsed = _up(url)
        values = parse_qs(parsed.query, keep_blank_values=True)
        return str((values.get("code") or [""])[0] or "").strip()
    except Exception:
        return ""


def normalize_url(target_url: str, base_url: str = OPENAI_AUTH) -> str:
    value = str(target_url or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    try:
        return urljoin(base_url, value)
    except Exception:
        return value


def decode_jwt_payload(token: str) -> dict:
    import base64
    import json
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        pad = "=" * ((4 - (len(payload) % 4)) % 4)
        return json.loads(base64.urlsafe_b64decode((payload + pad).encode("ascii")).decode("utf-8"))
    except Exception:
        return {}


def derive_registration_state_from_page(page) -> dict:
    current_url = str(page.url or "")
    state = extract_flow_state(None, current_url)
    if state.get("page_type"):
        return state

    if find_first_selector(page, PASSWORD_INPUT_SELECTORS):
        page_type = "login_password" if is_login_password_url(current_url) else "create_account_password"
        return build_manual_flow_state(page_type, current_url)

    otp_selector = find_first_selector(page, OTP_INPUT_SELECTORS)
    if otp_selector and "password" not in otp_selector:
        return build_manual_flow_state("email_otp_verification", current_url)

    try:
        about_visible = bool(
            page.evaluate(
                """
                () => {
                  const inputs = Array.from(document.querySelectorAll("input:not([type='hidden'])"));
                  const text = String(document.body?.innerText || '').toLowerCase();
                  const hasName = inputs.some((el) => {
                    const hint = `${el.name || ''} ${el.id || ''} ${el.placeholder || ''}`.toLowerCase();
                    return hint.includes('name') || hint.includes('Name') || hint.includes('Full name');
                  });
                  const hasAgeOrBirth = inputs.some((el) => {
                    const hint = `${el.name || ''} ${el.id || ''} ${el.placeholder || ''}`.toLowerCase();
                    return hint.includes('age') || hint.includes('birth') || hint.includes('birthday') || hint.includes('Age') || hint.includes('Birthday');
                  });
                  return (hasName && hasAgeOrBirth) || text.includes('about you');
                }
                """
            )
        )
    except Exception:
        about_visible = False
    if about_visible:
        return build_manual_flow_state("about_you", current_url)

    return state


def recover_signup_password_page(page, log) -> bool:
    if not is_login_password_url(str(page.url or "")):
        return False
    if not has_signup_registration_choice(page):
        return False
    selector = click_first(page, [
        'a:has-text("Sign up")',
        'button:has-text("Sign up")',
        'a:has-text("sign up")',
        'button:has-text("sign up")',
        'a:has-text("Register")',
        'button:has-text("Register")',
        'a:has-text("Create account")',
        'button:has-text("Create account")',
    ], timeout=2)
    if not selector:
        return False
    log(f"Password page fell to login state, try clicking registration entry to recover: {selector}")
    time.sleep(1.2)
    return True


def wait_for_signup_entry_transition(page, log, timeout: int = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if click_passwordless_login_if_available(page, log, context="After email page submission"):
            time.sleep(0.5)
            continue
        state = derive_registration_state_from_page(page)
        if state.get("page_type") in {
            "create_account_password",
            "login_password",
            "email_otp_verification",
            "about_you",
            "add_phone",
            "chatgpt_home",
            "oauth_callback",
        }:
            if state.get("page_type") == "login_password" and recover_signup_password_page(page, log):
                return derive_registration_state_from_page(page)
            return state
        error_text = extract_auth_error_text(page)
        if error_text:
            raise RuntimeError(f"Email page submission failed: {error_text[:300]}")
        time.sleep(0.25)
    raise RuntimeError("Did not enter password/verification page after email page submission")


def start_browser_signup_via_page(page, email: str, log) -> dict:
    for entry_url in (PLATFORM_LOGIN_ENTRY, f"{OPENAI_AUTH}/log-in"):
        try:
            log(f"Open OpenAI registration entry: {entry_url}")
            page.goto(entry_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            log(f"Registration entry access failed: {entry_url} -> {exc}")
            continue

        initial_state = derive_registration_state_from_page(page)
        if initial_state.get("page_type") in {
            "create_account_password",
            "login_password",
            "email_otp_verification",
            "about_you",
            "add_phone",
        }:
            return initial_state

        email_selector = wait_for_any_selector(page, EMAIL_INPUT_SELECTORS, timeout=12)
        if not email_selector:
            continue
        if not fill_input_like_user(page, email_selector, email):
            raise RuntimeError("Email page fill failed")
        log(f"Email page input box: {email_selector}")

        inline_state = derive_registration_state_from_page(page)
        if inline_state.get("page_type") in {"create_account_password", "login_password"}:
            if inline_state.get("page_type") == "login_password" and recover_signup_password_page(page, log):
                return derive_registration_state_from_page(page)
            return inline_state

        submit_selector = click_first(page, EMAIL_SUBMIT_SELECTORS, timeout=8)
        if submit_selector:
            log(f"Email page continue button clicked: {submit_selector}")
        elif submit_form_with_fallback(page, email_selector):
            log("Email page clickable Continue not found, used form fallback submission")
        else:
            raise RuntimeError("Email page Continue button not found")

        return wait_for_signup_entry_transition(page, log)

    raise RuntimeError("OpenAI registration entry email input box not found")


def start_browser_signup_via_authorize(page, email: str, device_id: str, log) -> dict:
    log("Visit ChatGPT homepage...")
    page.goto(f"{CHATGPT_APP}/", wait_until="domcontentloaded", timeout=30000)

    log("Get CSRF token...")
    csrf_token = get_browser_csrf_token(page)
    if not csrf_token:
        raise RuntimeError("Failed to get CSRF token")

    log(f"Submit email: {email}")
    authorize_url = start_browser_signin(page, email, device_id, csrf_token)
    if not authorize_url:
        raise RuntimeError("Email submission failed, did not get authorize URL")

    final_url = browser_authorize(page, authorize_url, log)
    if not final_url:
        raise RuntimeError("Failed to visit authorize URL")
    return derive_registration_state_from_page(page)


def get_browser_csrf_token(page) -> str:
    result = browser_fetch(
        page,
        f"{CHATGPT_APP}/api/auth/csrf",
        method="GET",
        headers={
            "accept": "application/json",
            "referer": f"{CHATGPT_APP}/",
            "sec-fetch-site": "same-origin",
        },
        redirect="follow",
    )
    if result.get("ok") and isinstance(result.get("data"), dict):
        return str((result.get("data") or {}).get("csrfToken") or "").strip()
    return ""


def start_browser_signin(page, email: str, device_id: str, csrf_token: str) -> str:
    from urllib.parse import urlencode

    query = urlencode(
        {
            "prompt": "login",
            "ext-oai-did": device_id,
            "auth_session_logging_id": str(uuid.uuid4()),
            "screen_hint": "login_or_signup",
            "login_hint": email,
        }
    )
    body = urlencode(
        {
            "callbackUrl": f"{CHATGPT_APP}/",
            "csrfToken": csrf_token,
            "json": "true",
        }
    )
    result = browser_fetch(
        page,
        f"{CHATGPT_APP}/api/auth/signin/openai?{query}",
        method="POST",
        headers={
            "accept": "application/json",
            "referer": f"{CHATGPT_APP}/",
            "origin": CHATGPT_APP,
            "content-type": "application/x-www-form-urlencoded",
            "sec-fetch-site": "same-origin",
        },
        body=body,
        redirect="follow",
    )
    if result.get("ok") and isinstance(result.get("data"), dict):
        return str((result.get("data") or {}).get("url") or "").strip()
    return ""


def browser_authorize(page, auth_url: str, log) -> str:
    if not auth_url:
        return ""
    try:
        page.goto(auth_url, wait_until="domcontentloaded", timeout=30000)
        final_url = page.url
        log(f"Authorize -> {final_url[:120]}")
        return final_url
    except Exception as exc:
        log(f"Authorize failed: {exc}")
        return ""


def is_registration_complete(state: dict) -> bool:
    page_type = str(state.get("page_type") or "")
    url = str(state.get("current_url") or state.get("continue_url") or "").lower()
    return page_type in {"callback", "oauth_callback", "chatgpt_home"} or (
        "chatgpt.com" in url and "redirect_uri" not in url and "about-you" not in url
    )


def handle_post_signup_onboarding(page, log) -> None:
    from .selectors import ALLOW_BLOCK_POPUP_SELECTORS, ONBOARDING_SKIP_SELECTORS
    current_url = str(page.url or "")
    if "chatgpt.com" not in current_url:
        return
    try:
        allow_selector = click_first(page, ALLOW_BLOCK_POPUP_SELECTORS, timeout=1)
        if allow_selector:
            log(f"Handled browser popup: {allow_selector}")
    except Exception:
        pass

    try:
        if page.locator("text=What brings you to ChatGPT?").first.count() > 0:
            skip_selector = click_first(page, ONBOARDING_SKIP_SELECTORS, timeout=5)
            if skip_selector:
                log(f"Handled onboarding page: {skip_selector}")
                browser_pause(page)
    except Exception:
        pass


def is_password_registration(state: dict) -> bool:
    return str(state.get("page_type") or "") in {"create_account_password", "password"}


def is_email_otp(state: dict) -> bool:
    target = f"{state.get('continue_url') or ''} {state.get('current_url') or ''}".lower()
    return str(state.get("page_type") or "") == "email_otp_verification" or "email-verification" in target or "email-otp" in target


def is_about_you(state: dict) -> bool:
    target = f"{state.get('continue_url') or ''} {state.get('current_url') or ''}".lower()
    return str(state.get("page_type") or "") == "about_you" or "about-you" in target


def is_add_phone(state: dict) -> bool:
    target = f"{state.get('continue_url') or ''} {state.get('current_url') or ''}".lower()
    return str(state.get("page_type") or "") == "add_phone" or "add-phone" in target
