"""ChatGPTBrowserRegister class and main registration flow."""

import json
import time
import uuid
from typing import Callable, Optional

from camoufox.sync_api import Camoufox

from ..constants import OPENAI_AUTH, CHATGPT_APP
from .proxy_config import build_proxy_config
from .browser_utils import (
    get_cookies,
    seed_browser_device_id,
    random_chrome_ua,
    browser_pause,
    requires_registration_navigation,
    extract_auth_error_text,
    fill_input_like_user,
    click_first,
    wait_for_any_selector,
    submit_form_with_fallback,
    normalize_url,
    extract_code_from_url,
    browser_fetch,
    build_browser_headers,
    generate_datadog_trace_headers,
    extract_callback_url_from_exception,
)
from .sentinel import build_browser_sentinel_token
from .state_machine import (
    extract_flow_state,
    derive_registration_state_from_page,
    start_browser_signup_via_page,
    start_browser_signup_via_authorize,
    is_registration_complete,
    handle_post_signup_onboarding,
    is_password_registration,
    is_email_otp,
    is_about_you,
    is_add_phone,
    recover_signup_password_page,
    normalize_url as _normalize_url,
    get_page_oauth_url,
    oauth_url_matches_state,
)
from .otp_flow import submit_otp_via_page, validate_browser_email_otp
from .phone_challenge import handle_add_phone_challenge
from .consent_flow import (
    complete_oauth_with_session,
    complete_oauth_in_browser,
    submit_callback_result,
)
from .about_you_flow import submit_about_you_via_page
from .selectors import PASSWORD_INPUT_SELECTORS, PASSWORD_SUBMIT_SELECTORS, EMAIL_INPUT_SELECTORS, EMAIL_SUBMIT_SELECTORS


def submit_browser_user_register(page, email: str, password: str, device_id: str, user_agent: str) -> dict:
    headers = build_browser_headers(
        user_agent=user_agent,
        accept="application/json",
        referer=f"{OPENAI_AUTH}/create-account/password",
        origin=OPENAI_AUTH,
        content_type="application/json",
        extra_headers={
            "sec-fetch-site": "same-origin",
            "oai-device-id": device_id,
            **generate_datadog_trace_headers(),
        },
    )
    sentinel = build_browser_sentinel_token(page, device_id, "username_password_create", user_agent)
    if sentinel:
        headers["openai-sentinel-token"] = sentinel
    browser_pause(page)
    return browser_fetch(
        page,
        f"{OPENAI_AUTH}/api/accounts/user/register",
        method="POST",
        headers=headers,
        body=json.dumps({"username": email, "password": password}),
        redirect="follow",
    )


def submit_oauth_password_direct(page, password: str, log) -> dict:
    """OAuth flow dedicated: directly fill password login, do not try to recover to registration state."""
    from .browser_utils import wait_for_any_selector, fill_input_like_user, browser_pause, extract_auth_error_text

    input_selector = wait_for_any_selector(page, PASSWORD_INPUT_SELECTORS, timeout=15)
    if not input_selector:
        time.sleep(2)
        input_selector = wait_for_any_selector(page, PASSWORD_INPUT_SELECTORS, timeout=10)
    if not input_selector:
        raise RuntimeError("OAuth password page input box not found")
    if not fill_input_like_user(page, input_selector, password):
        raise RuntimeError("OAuth password page fill failed")
    log(f"  OAuth password page input box: {input_selector}")
    browser_pause(page)

    submit_selector = click_first(page, PASSWORD_SUBMIT_SELECTORS, timeout=8)
    if submit_selector:
        log(f"  OAuth password page continue button clicked: {submit_selector}")
    elif submit_form_with_fallback(page, input_selector):
        log("  OAuth password page use form fallback submit")
    else:
        raise RuntimeError("OAuth password page not found Continue button")

    deadline = time.time() + 20
    while time.time() < deadline:
        current_url = str(page.url or "")
        state = derive_registration_state_from_page(page)
        page_type = str(state.get("page_type") or "")
        if page_type in {"email_otp_verification", "about_you", "consent", "workspace_selection",
                         "organization_selection", "add_phone", "oauth_callback", "chatgpt_home", "external_url"}:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        if "code=" in current_url:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        error_text = extract_auth_error_text(page)
        if error_text:
            return {"ok": False, "status": 400, "url": current_url, "data": None, "text": error_text}
        time.sleep(0.5)
    return {"ok": False, "status": 0, "url": str(page.url or ""), "data": None, "text": "OAuth password submission did not redirect"}


def submit_password_via_page(page, password: str, log) -> dict:
    if recover_signup_password_page(page, log):
        time.sleep(1)

    input_selector = wait_for_any_selector(page, PASSWORD_INPUT_SELECTORS, timeout=15)
    if not input_selector:
        raise RuntimeError("password page input box not found")
    if not fill_input_like_user(page, input_selector, password):
        raise RuntimeError("password page fill failed")
    log(f"password page input box: {input_selector}")
    browser_pause(page)

    start_url = str(page.url or "")
    submit_selector = click_first(page, PASSWORD_SUBMIT_SELECTORS, timeout=8)
    if submit_selector:
        log(f"password page continue button clicked: {submit_selector}")
    elif submit_form_with_fallback(page, input_selector):
        log("password page clickable not found Continue, used form fallback submit")
    else:
        raise RuntimeError("password page not found Continue button")

    deadline = time.time() + 20
    last_url = str(page.url or "")
    while time.time() < deadline:
        current_url = str(page.url or "")
        last_url = current_url or last_url
        state = derive_registration_state_from_page(page)
        page_type = str(state.get("page_type") or "")
        if page_type in {"email_otp_verification", "about_you", "add_phone", "oauth_callback", "chatgpt_home"}:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        if current_url != start_url and page_type and page_type not in {"create_account_password", "login_password"}:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        if page_type == "login_password" and recover_signup_password_page(page, log):
            input_selector = wait_for_any_selector(page, PASSWORD_INPUT_SELECTORS, timeout=5)
            if not input_selector:
                return {"ok": False, "status": 400, "url": current_url, "data": None, "text": "login password page recovery not found Register password input box"}
            if not fill_input_like_user(page, input_selector, password):
                return {"ok": False, "status": 400, "url": current_url, "data": None, "text": "login password page recovery password re-fill failed"}
            submit_selector = click_first(page, PASSWORD_SUBMIT_SELECTORS, timeout=5)
            if submit_selector:
                log(f"recovery re-click password submit button: {submit_selector}")
                start_url = str(page.url or start_url)
                time.sleep(0.4)
                continue
            if submit_form_with_fallback(page, input_selector):
                log("recovery password submit button not found, used form fallback submit")
                start_url = str(page.url or start_url)
                time.sleep(0.4)
                continue
            return {"ok": False, "status": 400, "url": current_url, "data": None, "text": "login password page recovery submission method not found"}
        error_text = extract_auth_error_text(page)
        if error_text:
            from .browser_utils import dump_debug
            dump_debug(page, "chatgpt_password_fail")
            return {"ok": False, "status": 400, "url": current_url, "data": None, "text": error_text}
        time.sleep(0.5)
    from .browser_utils import dump_debug
    dump_debug(page, "chatgpt_password_fail")
    return {"ok": False, "status": 0, "url": last_url, "data": None, "text": "password page submission did not redirect"}


def submit_login_email_via_page(page, email: str, log) -> dict:
    input_selector = wait_for_any_selector(page, EMAIL_INPUT_SELECTORS, timeout=15)
    if not input_selector:
        raise RuntimeError("OAuth email page input box not found")
    if not fill_input_like_user(page, input_selector, email):
        raise RuntimeError("OAuth Email page fill failed")
    log(f"OAuth Email page input box: {input_selector}")
    browser_pause(page)

    start_url = str(page.url or "")
    submit_selector = click_first(page, EMAIL_SUBMIT_SELECTORS, timeout=8)
    if submit_selector:
        log(f"OAuth Email page continue button clicked: {submit_selector}")
    elif submit_form_with_fallback(page, input_selector):
        log("OAuth Email page clickable Continue not found, used form fallback submission")
    else:
        raise RuntimeError("OAuth Email page Continue button not found")

    deadline = time.time() + 20
    last_url = start_url
    while time.time() < deadline:
        current_url = str(page.url or "")
        last_url = current_url or last_url
        from .browser_utils import click_passwordless_login_if_available
        if click_passwordless_login_if_available(page, log, context="OAuth After email page submission"):
            time.sleep(0.5)
            continue
        state = derive_registration_state_from_page(page)
        page_type = str(state.get("page_type") or "")
        if page_type in {
            "login_password",
            "create_account_password",
            "email_otp_verification",
            "about_you",
            "consent",
            "workspace_selection",
            "organization_selection",
            "add_phone",
            "external_url",
            "oauth_callback",
            "chatgpt_home",
        }:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        if current_url != start_url and page_type != "login_email":
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        error_text = extract_auth_error_text(page)
        if error_text:
            return {"ok": False, "status": 400, "url": current_url, "data": None, "text": error_text}
        time.sleep(0.5)
    return {"ok": False, "status": 0, "url": last_url, "data": None, "text": "OAuth did not redirect after email page submission"}


def derive_oauth_state_from_page(page) -> dict:
    state = derive_registration_state_from_page(page)
    if state.get("page_type"):
        return state
    current_url = str(page.url or "")
    from .selectors import EMAIL_INPUT_SELECTORS
    if wait_for_any_selector(page, EMAIL_INPUT_SELECTORS, timeout=0.5):
        from .browser_utils import build_manual_flow_state
        return build_manual_flow_state("login_email", current_url)
    return extract_flow_state(None, current_url)


def do_codex_oauth(page, cookies_dict: dict, email: str, password: str, otp_callback, phone_callback, proxy: str | None, log) -> dict | None:
    """Complete Codex OAuth in real browser session, return full token package."""
    from ..oauth import generate_oauth_url
    from ..constants import CODEX_CLIENT_ID, CODEX_REDIRECT_URI, CODEX_SCOPE

    oauth_start = generate_oauth_url(
        redirect_uri=CODEX_REDIRECT_URI,
        scope=CODEX_SCOPE,
        client_id=CODEX_CLIENT_ID,
    )
    try:
        user_agent = str(page.evaluate("() => navigator.userAgent") or "").strip() or random_chrome_ua()
    except Exception:
        user_agent = random_chrome_ua()
    device_id = str(cookies_dict.get("oai-did") or uuid.uuid4())
    log(f"  OAuth state={oauth_start.state[:20]}...")

    try:
        try:
            page.goto(oauth_start.auth_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            callback_url = extract_callback_url_from_exception(exc)
            if callback_url:
                log(f"  OAuth bootstrap directly captured callback: {callback_url[:100]}...")
                return submit_callback_result(callback_url, oauth_start, proxy)
            raise

        current_url = str(page.url or "")
        log(f"  OAuth bootstrap -> {current_url[:100]}...")

        for step in range(20):
            state = derive_oauth_state_from_page(page)
            current_url = str(page.url or "")
            next_url = str(state.get("continue_url") or "").strip()
            log(
                f"  OAuth state step[{step+1}/20]: "
                f"page={state.get('page_type') or '-'} next={next_url[:60]}"
                f" url={current_url[:120]}"
            )

            callback_url = ""
            if extract_code_from_url(current_url):
                callback_url = current_url
            elif extract_code_from_url(next_url):
                callback_url = next_url
            if callback_url:
                return submit_callback_result(callback_url, oauth_start, proxy)

            page_oauth_url = get_page_oauth_url(page)
            if (
                page_oauth_url
                and page_oauth_url != current_url
                and oauth_url_matches_state(page_oauth_url, oauth_start.state)
            ):
                log("  OAuth page detected updated authorization link, following page authorization link...")
                page.goto(page_oauth_url, wait_until="domcontentloaded", timeout=30000)
                continue

            if state["page_type"] == "login_email":
                log("  OAuth page requires email login, submitting email...")
                email_resp = submit_login_email_via_page(page, email, log)
                log(f"  OAuth email page submission status: {email_resp.get('status', 0)}")
                if not email_resp.get("ok"):
                    raise RuntimeError(f"OAuth Email page submission failed: {(email_resp.get('text') or '')[:300]}")
                continue

            if state["page_type"] in {"login_password", "create_account_password"}:
                log("  OAuth page requires password login, submitting password...")
                password_resp = submit_oauth_password_direct(page, password, log)
                log(f"  OAuth password page submission status: {password_resp.get('status', 0)}")
                if not password_resp.get("ok"):
                    raise RuntimeError(f"OAuth password page submission failed: {(password_resp.get('text') or '')[:300]}")
                continue

            if state["page_type"] == "email_otp_verification":
                if not otp_callback:
                    log("  OAuth requires email OTP but no otp_callback provided")
                    return None
                log("  OAuth waiting for email verification code...")
                code = otp_callback()
                if not code:
                    log("  OAuth OTP acquisition failed")
                    return None
                otp_resp = submit_otp_via_page(page, code, log)
                log(f"  OAuth verification code page submission status: {otp_resp.get('status', 0)}")
                if not otp_resp.get("ok"):
                    raise RuntimeError(f"OAuth verification code validation failed: {(otp_resp.get('text') or '')[:300]}")
                continue

            if state["page_type"] == "about_you":
                log("  OAuth page shows about_you, continuing page fill...")
                about_resp = submit_about_you_via_page(page, log)
                log(f"  OAuth about_you submission status: {about_resp.get('status', 0)}")
                if not about_resp.get("ok"):
                    raise RuntimeError(f"OAuth about_you submission failed: {(about_resp.get('text') or '')[:300]}")
                continue

            if state["page_type"] in {"consent", "workspace_selection", "organization_selection", "external_url"}:
                browser_result = complete_oauth_in_browser(page, oauth_start, proxy, log)
                if browser_result:
                    return browser_result
                cookies_dict = get_cookies(page)
                session_result = complete_oauth_with_session(cookies_dict, oauth_start, proxy, log)
                if session_result:
                    return session_result
                log("  Page reached consent/workspace but session completion failed")
                return None

            if state["page_type"] == "add_phone":
                if phone_callback:
                    log("  OAuth detected add_phone, prioritizing SMS verification...")
                    try:
                        handle_add_phone_challenge(
                            page, phone_callback,
                            device_id=device_id, user_agent=user_agent,
                            log=log, resume_url=oauth_start.auth_url,
                        )
                        continue
                    except Exception as exc:
                        log(f"  SMS verification failed, stopping OAuth flow: {exc}")
                        return None

                log("  Detected add_phone, trying to skip...")
                try:
                    page.goto(oauth_start.auth_url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                    current_url = str(page.url or "")

                    callback_url = ""
                    if "code=" in current_url:
                        callback_url = current_url
                    else:
                        for _ in range(5):
                            time.sleep(1)
                            current_url = str(page.url or "")
                            if "code=" in current_url:
                                callback_url = current_url
                                break

                    if callback_url:
                        log("  successfully skipped add_phone, got OAuth callback")
                        return submit_callback_result(callback_url, oauth_start, proxy)

                    skip_state = derive_registration_state_from_page(page)
                    if skip_state.get("page_type") in {"consent", "workspace_selection", "organization_selection"}:
                        log("  Skipped add_phone to reach consent page")
                        browser_result = complete_oauth_in_browser(page, oauth_start, proxy, log)
                        if browser_result:
                            return browser_result
                        cookies_dict = get_cookies(page)
                        session_result = complete_oauth_with_session(cookies_dict, oauth_start, proxy, log)
                        if session_result:
                            return session_result

                    if skip_state.get("page_type") == "add_phone":
                        log("  Skip failed, still on add_phone page")
                    else:
                        log(f"  Page state after skip: {skip_state.get('page_type') or '-'}")
                        continue

                except Exception as exc:
                    callback_url = extract_callback_url_from_exception(exc)
                    if callback_url:
                        return submit_callback_result(callback_url, oauth_start, proxy)
                    log(f"  Skip add_phone exception: {exc}")

                log("  add_phone cannot be skipped and no SMS service available")
                return None

            if state["page_type"] == "chatgpt_home":
                if "error" in current_url:
                    error_msg = current_url.split("error=")[-1].split("&")[0] if "error=" in current_url else "unknown"
                    log(f"  OAuth error page: {error_msg} url={current_url[:150]}")
                    raise RuntimeError(f"OpenAI OAuth error: {error_msg}")
                time.sleep(2)
                new_url = str(page.url or "")
                if new_url != current_url:
                    continue
                cookies_dict = get_cookies(page)
                for ck, cv in cookies_dict.items():
                    if "session" in ck.lower() and cv:
                        log(f"  chatgpt_home detected session cookie: {ck}")
                        session_result = complete_oauth_with_session(cookies_dict, oauth_start, proxy, log)
                        if session_result:
                            return session_result
                        break
                continue

            target_url = _normalize_url(state.get("continue_url") or "", OPENAI_AUTH)
            if target_url and target_url != current_url:
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as exc:
                    callback_url = extract_callback_url_from_exception(exc)
                    if callback_url:
                        return submit_callback_result(callback_url, oauth_start, proxy)
                    log(f"  OAuth navigation failed: {exc}")
                    break
                continue

            error_text = extract_auth_error_text(page)
            if error_text:
                raise RuntimeError(f"OAuth page error: {error_text[:300]}")
            time.sleep(0.5)
    except Exception as e:
        log(f"  OAuth exception: {e}")
        return None

    cookies_dict = get_cookies(page)
    result = complete_oauth_with_session(cookies_dict, oauth_start, proxy, log)
    if result:
        return result

    session_token = cookies_dict.get("__Secure-next-auth.session-token", "")
    if not session_token:
        log("  No session_token, OAuth failed")
        return None
    log("  Full OAuth failed, falling back to session access_token")
    return None


def browser_registration_flow(page, email: str, password: str, otp_callback, phone_callback, log) -> dict:
    device_id = str(uuid.uuid4())
    try:
        user_agent = str(page.evaluate("() => navigator.userAgent") or "").strip() or random_chrome_ua()
    except Exception:
        user_agent = random_chrome_ua()

    seed_browser_device_id(page, device_id)
    try:
        state = start_browser_signup_via_page(page, email, log)
    except Exception as exc:
        log(f"Page-driven register entry failed, fallback to ChatGPT authorize entry: {exc}")
        state = start_browser_signup_via_authorize(page, email, device_id, log)
    auth_cookies = get_cookies(page)
    log(
        "Authorize state cookies: "
        f"login_session={'yes' if auth_cookies.get('login_session') else 'no'}, "
        f"oai-did={'yes' if auth_cookies.get('oai-did') else 'no'}"
    )
    log(f"Register state start: page={state.get('page_type') or '-'} url={(state.get('current_url') or '')[:100]}")
    register_submitted = False
    seen_states: dict[str, int] = {}

    for step in range(12):
        signature = "|".join(
            [
                str(state.get("page_type") or ""),
                str(state.get("method") or ""),
                str(state.get("continue_url") or ""),
                str(state.get("current_url") or ""),
            ]
        )
        seen_states[signature] = seen_states.get(signature, 0) + 1
        log(
            f"Register state advance: step={step+1} page={state.get('page_type') or '-'} "
            f"next={str(state.get('continue_url') or '')[:60]} seen={seen_states[signature]}"
        )
        if seen_states[signature] > 2:
            raise RuntimeError(f"Register state stuck: page={state.get('page_type') or '-'}")

        if is_registration_complete(state):
            handle_post_signup_onboarding(page, log)
            return extract_flow_state(None, page.url)

        if is_password_registration(state):
            if register_submitted:
                raise RuntimeError("Repeatedly entering password register stage")
            log("Submit register password...")
            pre_cookies = get_cookies(page)
            log(
                "Password stage cookies: "
                f"login_session={'yes' if pre_cookies.get('login_session') else 'no'}, "
                f"oai-client-auth-session={'yes' if pre_cookies.get('oai-client-auth-session') else 'no'}"
            )
            reg_resp = submit_password_via_page(page, password, log)
            log(f"Password page submit state: {reg_resp.get('status', 0)}")
            if not reg_resp.get("ok"):
                raise RuntimeError(f"Password page submit failed: {(reg_resp.get('text') or '')[:300]}")
            register_submitted = True
            state = extract_flow_state(reg_resp.get("data"), reg_resp.get("url", page.url))
            if not state.get("page_type") or is_password_registration(state):
                state = derive_registration_state_from_page(page)
            continue

        if str(state.get("page_type") or "") == "login_password":
            if recover_signup_password_page(page, log):
                state = derive_registration_state_from_page(page)
                continue
            log("Register flow reached existing account login password page, continue authentication via login flow...")
            login_resp = submit_oauth_password_direct(page, password, log)
            log(f"Login password page submit state: {login_resp.get('status', 0)}")
            if not login_resp.get("ok"):
                raise RuntimeError(f"Login password page submit failed: {(login_resp.get('text') or '')[:300]}")
            state = extract_flow_state(login_resp.get("data"), login_resp.get("url", page.url))
            if not state.get("page_type"):
                state = derive_registration_state_from_page(page)
            continue

        if is_email_otp(state):
            if not otp_callback:
                raise RuntimeError("ChatGPT Register requires email verification code but no otp_callback provided")
            log("Waiting for ChatGPT verification code")
            code = otp_callback()
            if not code:
                raise RuntimeError("Did not get verification code")
            otp_resp = submit_otp_via_page(page, code, log)
            log(f"Verification code page submit state: {otp_resp.get('status', 0)}")
            if not otp_resp.get("ok"):
                raise RuntimeError(f"Verification code validation failed: {(otp_resp.get('text') or '')[:300]}")
            state = extract_flow_state(otp_resp.get("data"), otp_resp.get("url", page.url))
            if not state.get("page_type"):
                state = derive_registration_state_from_page(page)
            continue

        if is_about_you(state):
            log("Submit about_you info...")
            target_url = _normalize_url(
                str(state.get("current_url") or state.get("continue_url") or f"{OPENAI_AUTH}/about-you"),
                OPENAI_AUTH,
            )
            if "about-you" not in str(page.url):
                log(f"Redirect to about_you page: {target_url[:120]}")
                page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            about_resp = submit_about_you_via_page(page, log)
            log(f"about_you submit state: {about_resp.get('status', 0)}")
            if not about_resp.get("ok"):
                raise RuntimeError(f"about_you submit failed: {(about_resp.get('text') or '')[:300]}")
            state = extract_flow_state(about_resp.get("data"), about_resp.get("url", page.url))
            if not state.get("page_type"):
                state = derive_registration_state_from_page(page)
            if is_add_phone(state):
                if not phone_callback:
                    return state
                log("After about_you entered add_phone, try SMSVerify...")
                state = handle_add_phone_challenge(
                    page,
                    phone_callback,
                    device_id=device_id,
                    user_agent=user_agent,
                    log=log,
                    resume_url=f"{CHATGPT_APP}/",
                )
            continue

        if is_add_phone(state):
            if not phone_callback:
                return state
            log("Register flow entered add_phone, try SMSVerify...")
            state = handle_add_phone_challenge(
                page,
                phone_callback,
                device_id=device_id,
                user_agent=user_agent,
                log=log,
                resume_url=f"{CHATGPT_APP}/",
            )
            continue

        if requires_registration_navigation(state):
            target_url = _normalize_url(str(state.get("continue_url") or state.get("current_url") or ""), OPENAI_AUTH)
            if not target_url:
                raise RuntimeError("Missing followable continue_url")
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            state = extract_flow_state(None, page.url)
            continue

        raise RuntimeError(f"Unsupported register state: page={state.get('page_type') or '-'}")

    raise RuntimeError("Register state machine exceeded maximum steps")


class ChatGPTBrowserRegister:
    def __init__(
        self,
        *,
        headless: bool,
        proxy: Optional[str] = None,
        otp_callback: Optional[Callable[[], str]] = None,
        phone_callback: Optional[Callable[[], str]] = None,
        log_fn: Callable[[str], None] = print,
    ):
        self.headless = headless
        self.proxy = proxy
        self.otp_callback = otp_callback
        self.phone_callback = phone_callback
        self.log = log_fn

    def run(self, email: str, password: str) -> dict:
        proxy = build_proxy_config(self.proxy)
        launch_opts = {"headless": self.headless}
        if proxy:
            launch_opts["proxy"] = proxy
            launch_opts["geoip"] = True

        with Camoufox(**launch_opts) as browser:
            page = browser.new_page()
            self.log("Starting browser context register state machine")
            final_state = browser_registration_flow(
                page,
                email,
                password,
                self.otp_callback,
                self.phone_callback,
                self.log,
            )
            self.log(f"Register flow complete: page={final_state.get('page_type') or '-'}")

            cookies_dict = get_cookies(page)

            self.log("Executing Codex CLI OAuth flow to get token...")

        codex_result = self._retry_oauth_fresh_browser(email, password)
        if codex_result:
            self.log(f"fresh browser OAuth successful: account_id={codex_result.get('account_id','')}")
            return {
                "email": email, "password": password,
                "account_id": codex_result.get("account_id", ""),
                "access_token": codex_result.get("access_token", ""),
                "refresh_token": codex_result.get("refresh_token", ""),
                "id_token": codex_result.get("id_token", ""),
                "session_token": "", "workspace_id": "",
                "cookies": "", "profile": {},
            }

        raise RuntimeError("ChatGPT Register did not complete full OAuth callback, rejected fallback to session/access_token half-baked results")

    def _retry_oauth_fresh_browser(self, email, password):
        """Do Codex OAuth in fresh browser context (bypass add_phone session)."""
        proxy = build_proxy_config(self.proxy)
        launch_opts = {"headless": self.headless}
        if proxy:
            launch_opts["proxy"] = proxy
        try:
            with Camoufox(**launch_opts) as browser:
                page = browser.new_page()
                self.log("  fresh browser OAuth starting...")
                result = do_codex_oauth(
                    page, {}, email, password,
                    self.otp_callback, self.phone_callback, self.proxy, self.log,
                )
                return result
        except Exception as e:
            self.log(f"  fresh browser OAuth abnormal: {e}")
            return None
