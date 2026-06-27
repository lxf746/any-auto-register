"""Phone challenge flow for ChatGPT browser registration."""

import json
import random
import time

from ..constants import OPENAI_AUTH
from .selectors import (
    PHONE_INPUT_SELECTORS,
    PHONE_SEND_SELECTORS,
    OTP_INPUT_SELECTORS,
)
from .browser_utils import (
    wait_for_any_selector,
    find_first_selector,
    click_first,
    fill_input_like_user,
    submit_form_with_fallback,
    browser_pause,
    extract_auth_error_text,
    mask_phone_number,
    normalize_url,
    build_browser_headers,
    generate_datadog_trace_headers,
    browser_fetch,
)
from .sentinel import build_browser_sentinel_token
from .phone_country import parse_phone_country_and_local, select_phone_country_ui
from .otp_flow import submit_otp_via_page
from .state_machine import (
    derive_registration_state_from_page,
    extract_flow_state,
)


def is_invalid_phone_otp_response(result: dict) -> bool:
    status = int((result or {}).get("status") or 0)
    if status != 400:
        return False
    data = (result or {}).get("data")
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "").lower()
            code = str(error.get("code") or "").lower()
            return code == "invalid_input" and "invalid otp code" in message
    text = str((result or {}).get("text") or "").lower()
    return "invalid otp code" in text


def handle_add_phone_challenge(
    page,
    phone_callback,
    *,
    device_id: str,
    user_agent: str,
    log,
    resume_url: str = "",
    max_phone_attempts: int = 3,
) -> dict:
    """Complete phone number verification via UI interaction on add-phone page.

    Flow: select country -> enter local number -> click Send -> fill OTP -> click Verify.
    If verification code not received due to timeout, auto retry with new number (max max_phone_attempts times).
    """
    if not phone_callback:
        raise RuntimeError(
            "ChatGPT Register encountered phone verification but phone_callback not configured. "
            "Please configure SMS service in RegisterConfig.extra, or manually complete phone verification."
        )

    last_error = None
    for phone_attempt in range(max_phone_attempts):
        if phone_attempt > 0:
            log(f"Retrying with new number {phone_attempt + 1}/{max_phone_attempts}...")
            try:
                page.goto(f"{OPENAI_AUTH}/add-phone", wait_until="domcontentloaded", timeout=15000)
                time.sleep(1)
            except Exception:
                pass

        try:
            result = do_add_phone_attempt(
                page, phone_callback,
                device_id=device_id, user_agent=user_agent,
                log=log, resume_url=resume_url,
            )
            return result
        except RuntimeError as exc:
            last_error = exc
            error_msg = str(exc)
            should_retry = (
                "Did not get SMS verification code" in error_msg
                or "phone_number_in_use" in error_msg
                or "already" in error_msg.lower()
                or "in use" in error_msg.lower()
            )
            if not should_retry:
                raise
            log(f"Verification code timeout, preparing to retry with new number...")
            if hasattr(phone_callback, "cleanup"):
                phone_callback.cleanup()
            if hasattr(phone_callback, "phase"):
                phone_callback.phase = "need_number"
                phone_callback.activation = None
                phone_callback.completed = False

    raise last_error or RuntimeError("SMS verification failed: no verification code received after multiple number changes")


def do_add_phone_attempt(
    page,
    phone_callback,
    *,
    device_id: str,
    user_agent: str,
    log,
    resume_url: str = "",
) -> dict:
    """Single phone number verification attempt (internal function)."""

    referer = normalize_url(str(page.url or ""), OPENAI_AUTH) or f"{OPENAI_AUTH}/add-phone"
    headers = build_browser_headers(
        user_agent=user_agent,
        accept="application/json",
        referer=referer,
        origin=OPENAI_AUTH,
        content_type="application/json",
        extra_headers={
            "sec-fetch-site": "same-origin",
            "oai-device-id": device_id,
            **generate_datadog_trace_headers(),
        },
    )

    def _request_openai_resend():
        resend_clicked = click_first(page, [
            'button:has-text("Resend")',
            'button:has-text("resend")',
            'button:has-text("Resend code")',
            'button:has-text("Resend")',
            'a:has-text("Resend")',
            'a:has-text("resend")',
            'a:has-text("Resend code")',
        ], timeout=3)
        if resend_clicked:
            log(f"  phone-otp/resend -> Clicked page Resend button: {resend_clicked}")
        else:
            log("  phone-otp/resend -> Resend button not found on page, skipping (browser mode does not use HTTP)")

    if hasattr(phone_callback, "set_resend_callback"):
        phone_callback.set_resend_callback(_request_openai_resend)

    # ---- Step 1: Get phone number ----
    log("Register flow entered add_phone, starting to prepare number rental and receive SMS verification code...")
    phone_number = str(phone_callback() or "").strip()
    if not phone_number:
        raise RuntimeError("Failed to get phone number")
    log(f"Detected add_phone, submitting phone number (UI): {mask_phone_number(phone_number)}")

    dial_code, local_number, country_name = parse_phone_country_and_local(phone_number)
    log(f"  Parsing number: country={country_name or 'unknown'} dial_code=+{dial_code} local_number={local_number[:4]}...")

    current_url = str(page.url or "")
    if "add-phone" not in current_url:
        page.goto(f"{OPENAI_AUTH}/add-phone", wait_until="domcontentloaded", timeout=30000)
    time.sleep(1)

    # ---- Step 2: Select country ----
    country_selected = select_phone_country_ui(page, dial_code, country_name, log)
    browser_pause(page)

    # ---- Step 3: Fill phone number ----
    phone_input_sel = wait_for_any_selector(page, PHONE_INPUT_SELECTORS, timeout=10)
    if phone_input_sel:
        fill_value = local_number if country_selected else phone_number
        filled = fill_input_like_user(page, phone_input_sel, fill_value)
        if not filled:
            try:
                actual_val = str(page.evaluate(
                    "(sel) => { const el = document.querySelector(sel); return el ? el.value : ''; }",
                    phone_input_sel,
                ) or "")
                if fill_value and fill_value in actual_val.replace(" ", "").replace("-", ""):
                    filled = True
                    log(f"  Phone number filled (with prefix): {actual_val[:12]}...")
            except Exception:
                pass
        if not filled:
            log(f"  fill_input_like_user failed, trying keyboard fallback...")
            try:
                page.click(phone_input_sel)
                time.sleep(0.3)
                for _ in range(3):
                    page.keyboard.press("Meta+a")
                    time.sleep(0.1)
                    page.keyboard.press("Backspace")
                    time.sleep(0.1)
                page.keyboard.type(fill_value, delay=random.randint(30, 70))
                time.sleep(0.3)
                actual = page.evaluate(
                    "(sel) => { const el = document.querySelector(sel); return el ? el.value : ''; }",
                    phone_input_sel,
                )
                actual_clean = str(actual or "").replace(" ", "").replace("-", "")
                if fill_value in actual_clean:
                    filled = True
                    log(f"  keyboard fallback successful: {str(actual or '')[:12]}...")
            except Exception as e:
                log(f"  keyboard fallback failed: {e}")
        if not filled:
            try:
                js_ok = page.evaluate(
                    """
                    ({ selector, value }) => {
                      const input = document.querySelector(selector);
                      if (!input) return false;
                      input.focus();
                      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                      if (setter) setter.call(input, value);
                      else input.value = value;
                      input.dispatchEvent(new Event('input', { bubbles: true }));
                      input.dispatchEvent(new Event('change', { bubbles: true }));
                      const nativeEvent = new Event('input', { bubbles: true });
                      Object.defineProperty(nativeEvent, 'target', { writable: false, value: input });
                      input.dispatchEvent(nativeEvent);
                      return input.value.includes(value);
                    }
                    """,
                    {"selector": phone_input_sel, "value": fill_value},
                )
                if js_ok:
                    filled = True
                    log(f"  JS setValue fallback successful")
            except Exception as e:
                log(f"  JS setValue fallback failed: {e}")
        if not filled:
            raise RuntimeError(f"Phone number input box fill failed: {phone_input_sel}")
        log(f"  Phone number input box filled: {phone_input_sel} value={fill_value[:4]}...")
    else:
        raise RuntimeError("Phone number input box not found")
    browser_pause(page)

    # ---- Step 4: Click Send button ----
    send_sel = click_first(page, PHONE_SEND_SELECTORS, timeout=8)
    if send_sel:
        log(f"  Clicked Send button: {send_sel}")
    elif submit_form_with_fallback(page, phone_input_sel):
        log("  Send button not found, used form fallback submission")
    else:
        raise RuntimeError("Send verification code button not found")

    time.sleep(2)

    error_text = extract_auth_error_text(page)
    if error_text:
        if hasattr(phone_callback, "mark_send_failed"):
            phone_callback.mark_send_failed(error_text)
        raise RuntimeError(f"Phone number submission failed: {error_text[:200]}")

    if hasattr(phone_callback, "mark_send_succeeded"):
        phone_callback.mark_send_succeeded()
    log("Phone number submitted successfully (UI), starting to wait for SMS verification code...")

    # ---- Step 5: Wait for SMS verification code and fill in page OTP input box ----
    for code_attempt in range(3):
        sms_code = str(phone_callback() or "").strip()
        if not sms_code:
            raise RuntimeError("Did not get SMS verification code")

        otp_sel = wait_for_any_selector(page, OTP_INPUT_SELECTORS, timeout=10)
        if not otp_sel:
            otp_sel = find_first_selector(page, PHONE_INPUT_SELECTORS)
        if not otp_sel:
            raise RuntimeError("SMS verification code input box not found")

        otp_resp = submit_otp_via_page(page, sms_code, log)
        otp_status = int(otp_resp.get("status") or 0)
        log(f"  phone-otp page submission status: {otp_status}")

        if otp_resp.get("ok") or otp_status in (200, 201, 204):
            if hasattr(phone_callback, "report_success"):
                phone_callback.report_success()
            time.sleep(1.5)
            state = extract_flow_state(
                otp_resp.get("data"),
                otp_resp.get("url", page.url),
            )
            if not state.get("page_type"):
                state = derive_registration_state_from_page(page)
            next_url = normalize_url(resume_url, OPENAI_AUTH) if resume_url else ""
            if next_url:
                page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
                return extract_flow_state(None, page.url)
            return state

        page_error = extract_auth_error_text(page)
        if page_error and any(kw in page_error.lower() for kw in ("invalid", "incorrect", "wrong", "expired")):
            log(f"SMS verification code deemed invalid: {page_error[:100]}, continue waiting for next one...")
            if hasattr(phone_callback, "mark_code_failed"):
                phone_callback.mark_code_failed(page_error or "invalid otp code")
            continue

        if hasattr(phone_callback, "mark_code_failed"):
            phone_callback.mark_code_failed(page_error or f"status {otp_status}")
        raise RuntimeError(f"SMS verification code validation failed: {page_error[:200] if page_error else f'status {otp_status}'}")

    raise RuntimeError("SMS verification code validation failed: Multiple verification codes invalid or not passed")
