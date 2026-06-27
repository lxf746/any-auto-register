"""OTP/邮箱 verification flow for ChatGPT browser registration."""

import json
import random
import re
import time

from ..constants import OPENAI_AUTH
from .selectors import OTP_INPUT_SELECTORS, OTP_SUBMIT_SELECTORS
from .browser_utils import (
    wait_for_any_selector,
    click_first,
    browser_pause,
    extract_auth_error_text,
    dump_debug,
    build_browser_headers,
    generate_datadog_trace_headers,
    browser_fetch,
)
from .sentinel import build_browser_sentinel_token
from .state_machine import (
    normalize_url,
    extract_flow_state,
    derive_registration_state_from_page,
    extract_code_from_url,
)


def submit_otp_via_page(page, code: str, log) -> dict:
    otp = str(code or "").strip()
    if not otp:
        return {"ok": False, "status": 400, "url": page.url, "data": None, "text": "Verification code is empty"}

    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    time.sleep(1)

    filled = False

    # first try 6 grid OTP input box
    try:
        digit_inputs = page.locator(
            "input[inputmode='numeric'], input[autocomplete='one-time-code'], input[type='tel'], input[type='number']"
        )
        count = digit_inputs.count()
        if count >= len(otp):
            done = 0
            for i in range(min(count, len(otp))):
                box = digit_inputs.nth(i)
                try:
                    box.wait_for(state="visible", timeout=800)
                    box.fill("")
                    box.type(otp[i], delay=random.randint(20, 60))
                    done += 1
                except Exception:
                    break
            if done >= len(otp):
                filled = True
                log(f"Verification code page already filled {done} digit grid input box")
    except Exception:
        pass

    # try single input box again
    if not filled:
        otp_candidates = [
            page.get_by_label(re.compile(r"verification code|code|otp", re.IGNORECASE)),
            page.get_by_role("textbox", name=re.compile(r"verification code|code|otp", re.IGNORECASE)),
            page.locator("input[autocomplete='one-time-code']"),
            page.locator("input[name*='code' i]"),
            page.locator("input[id*='code' i]"),
            page.locator("input[type='text']"),
            page.locator("input"),
        ]
        for candidate in otp_candidates:
            try:
                target = candidate.first
                target.wait_for(state="visible", timeout=1200)
                target.click(timeout=1200)
                target.fill("")
                target.type(otp, delay=random.randint(18, 45))
                final_value = str(target.input_value() or "").strip()
                if final_value:
                    filled = True
                    log("Verification code page filled single input box")
                    break
            except Exception:
                continue

    if not filled:
        time.sleep(3)
        otp_retry_selectors = [
            "input[inputmode='numeric']",
            "input[autocomplete='one-time-code']",
            "input[name*='code' i]",
            "input[type='text']",
        ]
        for sel in otp_retry_selectors:
            try:
                target = page.locator(sel).first
                if target.is_visible(timeout=2000):
                    target.click(timeout=1500)
                    target.fill("")
                    target.type(otp, delay=random.randint(18, 45))
                    if str(target.input_value() or "").strip():
                        filled = True
                        log("Verification code page filled single input box (retry)")
                        break
            except Exception:
                continue

    if not filled:
        return {"ok": False, "status": 0, "url": page.url, "data": None, "text": "Verification code page no fillable input box found"}

    browser_pause(page)
    submit_selector = click_first(page, OTP_SUBMIT_SELECTORS, timeout=8)
    if not submit_selector:
        return {"ok": False, "status": 0, "url": page.url, "data": None, "text": "Verification code page not found Continue button"}
    log(f"Verification code page continue button clicked: {submit_selector}")

    deadline = time.time() + 20
    last_url = page.url
    while time.time() < deadline:
        current_url = page.url
        last_url = current_url or last_url
        if "about-you" in current_url:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        if "add-phone" in current_url or "chatgpt.com" in current_url or "code=" in current_url:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        if "consent" in current_url or "sign-in-with-chatgpt" in current_url or "workspace" in current_url or "organization" in current_url:
            return {"ok": True, "status": 200, "url": current_url, "data": None, "text": ""}
        try:
            error_text = page.locator("text=Invalid code").first.text_content(timeout=400)
        except Exception:
            error_text = ""
        if error_text:
            return {"ok": False, "status": 400, "url": current_url, "data": None, "text": error_text}
        time.sleep(0.5)
    return {"ok": False, "status": 0, "url": last_url, "data": None, "text": "Verification code page submission did not redirect"}


def validate_browser_email_otp(page, code: str, device_id: str, user_agent: str, referer: str) -> dict:
    headers = build_browser_headers(
        user_agent=user_agent,
        accept="application/json",
        referer=referer or f"{OPENAI_AUTH}/email-verification",
        origin=OPENAI_AUTH,
        content_type="application/json",
        extra_headers={
            "sec-fetch-site": "same-origin",
            "oai-device-id": device_id,
            **generate_datadog_trace_headers(),
        },
    )
    sentinel = build_browser_sentinel_token(page, device_id, "email_otp_validate", user_agent)
    if sentinel:
        headers["openai-sentinel-token"] = sentinel
    browser_pause(page)
    return browser_fetch(
        page,
        f"{OPENAI_AUTH}/api/accounts/email-otp/validate",
        method="POST",
        headers=headers,
        body=json.dumps({"code": code}),
        redirect="follow",
    )


def send_browser_email_otp(page) -> dict:
    browser_pause(page)
    return browser_fetch(
        page,
        f"{OPENAI_AUTH}/api/accounts/email-otp/send",
        method="GET",
        headers={
            "accept": "application/json, text/plain, */*",
            "referer": f"{OPENAI_AUTH}/create-account/password",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-language": "en-US,en;q=0.9",
        },
        redirect="follow",
    )
