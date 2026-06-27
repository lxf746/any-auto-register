"""Consent/data processing flow for ChatGPT browser registration."""

import json
import re
import time

from ..constants import OPENAI_AUTH, OAUTH_CONSENT_FORM_SELECTOR
from .browser_utils import (
    extract_callback_url_from_exception,
    browser_fetch,
)
from .state_machine import (
    normalize_url,
    extract_flow_state,
    extract_code_from_url,
)


def decode_oauth_session_cookie(cookies_dict: dict) -> dict:
    import base64
    raw = str(cookies_dict.get("oai-client-auth-session") or "").strip()
    if not raw:
        return {}
    first = raw.split(".")[0]
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            pad = "=" * ((4 - (len(first) % 4)) % 4)
            decoded = decoder((first + pad).encode("ascii")).decode("utf-8")
            parsed = json.loads(decoded)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return {}


def extract_workspace_from_consent_html(session, consent_url: str) -> dict:
    try:
        response = session.get(consent_url, allow_redirects=True, timeout=30)
        html = response.text or ""
        if "workspaces" not in html:
            return {}
        ids = re.findall(r'"id"(?:,|:)"([0-9a-f-]{36})"', html, flags=re.I)
        kinds = re.findall(r'"kind"(?:,|:)"([^"]+)"', html, flags=re.I)
        if not ids:
            return {}
        seen: set[str] = set()
        workspaces: list[dict] = []
        for idx, workspace_id in enumerate(ids):
            if workspace_id in seen:
                continue
            seen.add(workspace_id)
            item = {"id": workspace_id}
            if idx < len(kinds):
                item["kind"] = kinds[idx]
            workspaces.append(item)
        return {"workspaces": workspaces} if workspaces else {}
    except Exception:
        return {}


def seed_session_cookies(session, cookies_dict: dict):
    for name, value in cookies_dict.items():
        for domain in [".openai.com", ".chatgpt.com", ".auth.openai.com", "auth.openai.com", "chatgpt.com"]:
            try:
                session.cookies.set(name, value, domain=domain, path="/")
            except Exception:
                pass


def follow_redirects_for_code(session, start_url: str, log, *, max_redirects: int = 12) -> str:
    current_url = start_url
    for idx in range(max_redirects):
        response = session.get(current_url, allow_redirects=False, timeout=30)
        log(f"  redirect-follow[{idx+1}] {response.status_code} {str(current_url)[:140]}")
        location = str(response.headers.get("Location") or "").strip()
        if not location:
            break
        next_url = normalize_url(location, current_url)
        code = extract_code_from_url(next_url)
        if code:
            return next_url
        if response.status_code not in (301, 302, 303, 307, 308):
            break
        current_url = next_url
    return ""


def complete_oauth_with_session(cookies_dict: dict, oauth_start, proxy: str | None, log) -> dict | None:
    from ..oauth import submit_callback_url
    from curl_cffi import requests as cffi_requests

    s = cffi_requests.Session(impersonate="chrome131")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    seed_session_cookies(s, cookies_dict)

    try:
        session_meta = decode_oauth_session_cookie(cookies_dict)
        consent_url = "https://auth.openai.com/sign-in-with-chatgpt/codex/consent"
        workspaces = list(session_meta.get("workspaces") or [])
        if not workspaces:
            session_meta = extract_workspace_from_consent_html(s, consent_url)
            workspaces = list(session_meta.get("workspaces") or [])
        if not workspaces:
            log("  Missing oai-client-auth-session workspaces, OAuth failed")
            return None
        workspace_id = str((workspaces[0] or {}).get("id") or "").strip()
        log(f"  Select workspace: {workspace_id}")
        ws_resp = s.post(
            "https://auth.openai.com/api/accounts/workspace/select",
            headers={
                "accept": "application/json",
                "referer": consent_url,
                "origin": OPENAI_AUTH,
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            },
            data=json.dumps({"workspace_id": workspace_id}),
            allow_redirects=False,
            timeout=30,
        )
        log(f"  workspace/select -> {ws_resp.status_code}")

        next_url = str(ws_resp.headers.get("Location") or "").strip()
        next_data = {}
        if not next_url:
            try:
                next_data = ws_resp.json() or {}
            except Exception:
                next_data = {}
            next_url = str(next_data.get("continue_url") or "").strip()
        next_url = normalize_url(next_url, consent_url)
        direct_code = extract_code_from_url(next_url)
        if direct_code:
            result_json = submit_callback_url(
                callback_url=next_url,
                expected_state=oauth_start.state,
                code_verifier=oauth_start.code_verifier,
                proxy_url=proxy,
            )
            return json.loads(result_json)

        orgs = list((((next_data.get("data") or {}).get("orgs")) or []))
        if orgs and orgs[0].get("id"):
            org_id = str(orgs[0].get("id") or "").strip()
            org_body = {"org_id": org_id}
            projects = list(orgs[0].get("projects") or [])
            if projects and projects[0].get("id"):
                org_body["project_id"] = str(projects[0].get("id") or "").strip()
            log(f"  Select organization: {org_id}")
            org_resp = s.post(
                "https://auth.openai.com/api/accounts/organization/select",
                headers={
                    "accept": "application/json",
                    "referer": consent_url,
                    "origin": OPENAI_AUTH,
                    "content-type": "application/json",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                },
                data=json.dumps(org_body),
                allow_redirects=False,
                timeout=30,
            )
            log(f"  organization/select -> {org_resp.status_code}")
            next_url = str(org_resp.headers.get("Location") or "").strip() or next_url
            if not next_url:
                try:
                    org_data = org_resp.json() or {}
                    next_url = str(org_data.get("continue_url") or "").strip()
                    if not next_url:
                        org_state = extract_flow_state(org_data, str(org_resp.url))
                        next_url = org_state.get("continue_url") or org_state.get("current_url") or ""
                except Exception:
                    next_url = ""
            next_url = normalize_url(next_url, consent_url)

        if not next_url and next_data:
            state = extract_flow_state(next_data, str(ws_resp.url))
            next_url = state.get("continue_url") or state.get("current_url") or ""
            next_url = normalize_url(next_url, consent_url)

        if not next_url:
            next_url = "https://auth.openai.com/api/oauth/oauth2/auth?" + oauth_start.auth_url.split("?", 1)[1]

        callback_url = follow_redirects_for_code(s, next_url, log)
        if not callback_url:
            log("  Failed to follow OAuth callback")
            return None
        result_json = submit_callback_url(
            callback_url=callback_url,
            expected_state=oauth_start.state,
            code_verifier=oauth_start.code_verifier,
            proxy_url=proxy,
        )
        return json.loads(result_json)
    except Exception as e:
        log(f"  OAuth session completion exception: {e}")
        return None


def submit_callback_result(callback_url: str, oauth_start, proxy: str | None) -> dict:
    from ..oauth import submit_callback_url

    result_json = submit_callback_url(
        callback_url=callback_url,
        expected_state=oauth_start.state,
        code_verifier=oauth_start.code_verifier,
        redirect_uri=oauth_start.redirect_uri,
        client_id=oauth_start.client_id,
        proxy_url=proxy,
    )
    return json.loads(result_json)


def complete_oauth_in_browser(page, oauth_start, proxy, log) -> dict | None:
    """Complete OAuth consent flow in browser, multi-strategy retry clicking Continue."""
    from ..oauth import submit_callback_url

    CONSENT_FORM_SEL = OAUTH_CONSENT_FORM_SELECTOR
    MAX_ROUNDS = 4
    CLICK_EFFECT_TIMEOUT = 30

    def _try_extract_callback(url: str) -> dict | None:
        if not url or "code=" not in url:
            return None
        try:
            return json.loads(submit_callback_url(
                callback_url=url,
                expected_state=oauth_start.state,
                code_verifier=oauth_start.code_verifier,
                redirect_uri=oauth_start.redirect_uri,
                client_id=oauth_start.client_id,
                proxy_url=proxy,
            ))
        except ValueError as ve:
            if "state" in str(ve) and "localhost" in url and "code=" in url:
                try:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    code = (params.get("code") or [""])[0]
                    if code:
                        from ..oauth import _post_form, _jwt_claims_no_verify, OAUTH_TOKEN_URL
                        import time as _time
                        token_resp = _post_form(
                            OAUTH_TOKEN_URL,
                            {
                                "grant_type": "authorization_code",
                                "client_id": oauth_start.client_id,
                                "code": code,
                                "redirect_uri": oauth_start.redirect_uri,
                                "code_verifier": oauth_start.code_verifier,
                            },
                            proxy_url=proxy,
                        )
                        access_token = (token_resp.get("access_token") or "").strip()
                        refresh_token = (token_resp.get("refresh_token") or "").strip()
                        id_token = (token_resp.get("id_token") or "").strip()
                        if access_token:
                            claims = _jwt_claims_no_verify(id_token)
                            auth_claims = claims.get("https://api.openai.com/auth") or {}
                            now = int(_time.time())
                            expires_in = int(token_resp.get("expires_in") or 0)
                            return {
                                "id_token": id_token,
                                "access_token": access_token,
                                "refresh_token": refresh_token,
                                "account_id": str(auth_claims.get("chatgpt_account_id") or ""),
                                "email": str(claims.get("email") or ""),
                                "expired": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(now + max(expires_in, 0))),
                                "last_refresh": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(now)),
                            }
                except Exception:
                    pass
            return None
        except Exception:
            return None

    def _check_current_url() -> dict | None:
        url = str(page.url or "")
        result = _try_extract_callback(url)
        if result:
            return result
        cb = extract_callback_url_from_exception(Exception(url))
        return _try_extract_callback(cb) if cb else None

    def _wait_for_callback(timeout_sec: int) -> dict | None:
        deadline = time.time() + timeout_sec
        checked_urls = set()
        while time.time() < deadline:
            try:
                url = str(page.url or "")
            except Exception:
                url = ""
            if url and url not in checked_urls:
                checked_urls.add(url)
                if "code=" in url or "localhost" in url:
                    log(f"  [callback_wait] Detected URL change: {url[:150]}")
            result = _check_current_url()
            if result:
                return result
            if "localhost" in url and "code=" in url:
                result = _try_extract_callback(url)
                if result:
                    return result
            time.sleep(0.8)
        try:
            final_url = str(page.url or "")
            if "code=" in final_url:
                log(f"  [callback_wait] Final URL after timeout: {final_url[:150]}")
                result = _try_extract_callback(final_url)
                if result:
                    return result
        except Exception:
            pass
        return None

    def _find_consent_button():
        _sel = CONSENT_FORM_SEL
        btn = page.evaluate("""(sel) => {
            const form = document.querySelector(sel);
            if (!form) return null;
            const buttons = form.querySelectorAll('button[type="submit"], input[type="submit"], [role="button"]');
            for (const el of buttons) {
                if (el.offsetParent === null) continue;
                const text = (el.textContent || '').trim().toLowerCase();
                const ddName = el.getAttribute('data-dd-action-name') || '';
                if (ddName === 'Continue' || /continue|continue|continuar|fortfahren|continuer|continue/i.test(text)) return 'form-continue';
            }
            const first = Array.from(buttons).find(el => el.offsetParent !== null);
            if (first) return 'form-submit';
            return null;
        }""", _sel)
        if btn:
            return btn
        for sel in [
            'button[type="submit"][data-dd-action-name="Continue"]',
            'button:has-text("Continue")',
            'button:has-text("Continuar")',
            'button:has-text("Fortfahren")',
            'button:has-text("Continuer")',
            'button:has-text("Allow")',
            'button:has-text("Authorize")',
            'button[type="submit"]',
        ]:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=500):
                    return sel
            except Exception:
                continue
        return None

    def _click_strategy_request_submit(log_round: int) -> bool:
        try:
            result = page.evaluate("""(sel) => {
                const form = document.querySelector(sel);
                if (!form) return 'no-form';
                const buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
                let target = null;
                for (const el of buttons) {
                    if (el.offsetParent === null) continue;
                    const text = (el.textContent || '').trim().toLowerCase();
                    const ddName = el.getAttribute('data-dd-action-name') || '';
                    if (ddName === 'Continue' || /continue|continue|continuar|fortfahren|continuer/i.test(text)) { target = el; break; }
                }
                if (!target) target = Array.from(buttons).find(el => el.offsetParent !== null);
                if (!target) return 'no-button';
                if (typeof form.requestSubmit === 'function') {
                    form.requestSubmit(target);
                    return 'requestSubmit';
                }
                target.click();
                return 'click-fallback';
            }""", CONSENT_FORM_SEL)
            log(f"  consent round {log_round} requestSubmit: {result}")
            return result not in ("no-form", "no-button")
        except Exception as e:
            log(f"  consent requestSubmit exception: {e}")
            return False

    def _click_strategy_playwright(log_round: int) -> bool:
        for sel in [
            'button:has-text("Continue")',
            'button:has-text("Continuar")',
            'button:has-text("Fortfahren")',
            'button:has-text("Continuer")',
            'button[type="submit"]',
        ]:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=1500):
                    loc.click()
                    log(f"  consent round {log_round} playwright click: {sel}")
                    return True
            except Exception:
                continue
        return False

    def _click_strategy_js_dispatch(log_round: int) -> bool:
        try:
            result = page.evaluate("""() => {
                const buttons = document.querySelectorAll('button, [role="button"]');
                for (const el of buttons) {
                    if (el.offsetParent === null) continue;
                    const text = (el.textContent || '').trim().toLowerCase();
                    const ddName = el.getAttribute('data-dd-action-name') || '';
                    if (ddName === 'Continue' || /continue|continuar|fortfahren|continuer/i.test(text)) {
                        el.focus();
                        el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                        return text || 'dispatched';
                    }
                }
                return null;
            }
            """)
            if result:
                log(f"  consent round {log_round} JS dispatch: {result}")
                return True
            return False
        except Exception:
            return False

    strategies = [
        _click_strategy_request_submit,
        _click_strategy_playwright,
        _click_strategy_js_dispatch,
        _click_strategy_request_submit,
    ]

    try:
        current_url = str(page.url or "")
        log(f"  Browser consent processing: {current_url[:100]}")

        result = _check_current_url()
        if result:
            log("  Page already on callback URL")
            return result

        try:
            page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        time.sleep(1)

        try:
            try_again = page.query_selector('button:has-text("Try again")')
            if try_again and try_again.is_visible():
                log("  Consent page error, click Try again...")
                try_again.click()
                time.sleep(3)
        except Exception:
            pass

        for round_idx in range(MAX_ROUNDS):
            result = _check_current_url()
            if result:
                log("  browser OAuth consent complete")
                return result

            strategy_fn = strategies[min(round_idx, len(strategies) - 1)]
            clicked = strategy_fn(round_idx + 1)

            if clicked:
                try:
                    page.wait_for_url("**/auth/callback*", timeout=15000)
                except Exception:
                    pass
                time.sleep(1)
                result = _wait_for_callback(CLICK_EFFECT_TIMEOUT)
                if result:
                    log("  browser OAuth consent complete")
                    return result
                log(f"  consent round {round_idx + 1} round click after page did not redirect")
            else:
                log(f"  consent round {round_idx + 1} round button not found")

            if round_idx < MAX_ROUNDS - 1:
                log(f"  consent refresh page preparing round {round_idx + 2}...")
                try:
                    page.reload(wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass
                time.sleep(2)

        log(f"  consent {MAX_ROUNDS} round attempt still not completed, current: {str(page.url or '')[:100]}")
        return None
    except Exception as exc:
        cb = extract_callback_url_from_exception(exc)
        if cb:
            result = _try_extract_callback(cb)
            if result:
                log("  extract from exception callback complete OAuth")
                return result
        log(f"  browser OAuth consent abnormal: {exc}")
        return None
