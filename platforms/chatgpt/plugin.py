"""ChatGPT / Codex CLI platform plugin"""
import secrets
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.mailbox.base import BaseMailbox
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, ProtocolOAuthAdapter, RegistrationCapability, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register


def _result_text(result, key: str) -> str:
    if isinstance(result, dict):
        return str(result.get(key, "") or "")
    return str(getattr(result, key, "") or "")


def _assert_complete_oauth_callback(result) -> None:
    # NextAuth flow only returns account_id + access_token (+ session_token)
    # Traditional Codex CLI flow returns all 4 fields
    required = ("account_id", "access_token")
    missing = [key for key in required if not _result_text(result, key)]
    if missing:
        raise RuntimeError(
            "ChatGPT registration did not complete full OAuth callback, missing: " + ", ".join(missing)
        )


def _generate_chatgpt_registration_password(length: int = 16) -> str:
    """Generate a password that more stably passes OpenAI registration page validation.

    The old protocol flow has verified: when it contains at least lowercase, digits, and symbols, the success rate is significantly more stable.
    Add an uppercase character here to avoid the browser flow randomly generating a password that "looks long enough but the combination is not strong enough".
    """
    specials = ",._!@#"
    minimum_length = 12
    size = max(int(length or minimum_length), minimum_length)
    required = [
        secrets.choice("abcdefghijklmnopqrstuvwxyz"),
        secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        secrets.choice("0123456789"),
        secrets.choice(specials),
    ]
    pool = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" + specials
    required.extend(secrets.choice(pool) for _ in range(size - len(required)))
    secrets.SystemRandom().shuffle(required)
    return "".join(required)


@register
class ChatGPTPlatform(BasePlatform):
    name = "chatgpt"
    display_name = "ChatGPT"
    version = "1.0.0"
    supported_executors = ["protocol", "headless", "headed"]
    supported_identity_modes = ["mailbox", "oauth_browser"]
    supported_oauth_providers = ["google", "microsoft"]
    protocol_captcha_order = ("2captcha", "capsolver", "auto")

    # Declarative capabilities
    capabilities = [
        "query_state",      # Query account state/quota
        "refresh_token",    # Refresh auth token
        "generate_link",    # Generate payment link
        "switch_desktop",   # Switch to Codex desktop
        "upload_cpa",       # Upload to CPA system
        "upload_tm",        # Upload to Team Manager
    ]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def check_valid(self, account: Account) -> bool:
        self._last_check_overview = {}
        try:
            from platforms.chatgpt.payment import fetch_subscription_status_details
            from core.proxy_pool import proxy_pool
            class _A: pass
            a = _A()
            extra = account.extra or {}
            a.access_token = extra.get("access_token") or account.token
            a.id_token = extra.get("id_token", "")
            a.cookies = extra.get("cookies", "")
            a.extra = extra

            region = str(getattr(account, "region", "") or extra.get("region", "") or "").strip()
            configured_proxy = self.config.proxy if self.config else None
            proxy_candidates: list[tuple[str | None, bool]] = []
            if configured_proxy:
                proxy_candidates.append((configured_proxy, False))
            else:
                pooled_proxy = proxy_pool.get_next(region=region)
                if pooled_proxy:
                    proxy_candidates.append((pooled_proxy, True))
            proxy_candidates.append((None, False))

            for proxy, should_report in proxy_candidates:
                try:
                    details = fetch_subscription_status_details(a, proxy=proxy)
                    if should_report and proxy:
                        proxy_pool.report_success(proxy)
                    status = details.get("status")
                    overview = {
                        "plan": status,
                        "plan_name": status,
                        "check_source": details.get("source"),
                    }
                    if isinstance(details.get("usage"), dict):
                        overview["chatgpt_usage"] = details["usage"]
                    self._last_check_overview = overview
                    return status not in ("expired", "invalid", "banned", None)
                except Exception:
                    if should_report and proxy:
                        proxy_pool.report_fail(proxy)
                    continue
        except Exception:
            return False
        return False

    def get_last_check_overview(self) -> dict:
        return dict(getattr(self, "_last_check_overview", {}) or {})

    def _prepare_registration_password(self, password: str | None) -> str | None:
        if password:
            return password
        return _generate_chatgpt_registration_password()

    def _map_chatgpt_result(self, result: dict, *, password: str = "", user_id: str = "") -> RegistrationResult:
        _assert_complete_oauth_callback(result)
        return RegistrationResult(
            email=result.get("email", ""),
            password=password or result.get("password", ""),
            user_id=user_id or result.get("account_id", ""),
            token=result.get("access_token", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "access_token": result.get("access_token", ""),
                "refresh_token": result.get("refresh_token", ""),
                "id_token": result.get("id_token", ""),
                "session_token": result.get("session_token", ""),
                "workspace_id": result.get("workspace_id", ""),
                "cookies": result.get("cookies", ""),
                "profile": result.get("profile", {}),
            },
        )

    def _run_protocol_oauth(self, ctx) -> dict:
        from platforms.chatgpt.browser_oauth import register_with_browser_oauth

        return register_with_browser_oauth(
            proxy=ctx.proxy,
            oauth_provider=ctx.identity.oauth_provider,
            email_hint=ctx.identity.email,
            timeout=resolve_timeout(ctx.extra, ("browser_oauth_timeout", "manual_oauth_timeout"), 300),
            log_fn=ctx.log,
            headless=(ctx.executor_type == "headless"),
            chrome_user_data_dir=ctx.identity.chrome_user_data_dir,
            chrome_cdp_url=ctx.identity.chrome_cdp_url,
        )

    def build_browser_registration_adapter(self):
        return BrowserRegistrationAdapter(
            result_mapper=lambda ctx, result: self._map_chatgpt_result(result),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.chatgpt.browser_register", fromlist=["ChatGPTBrowserRegister"]).ChatGPTBrowserRegister(
                headless=(ctx.executor_type == "headless"),
                proxy=ctx.proxy,
                otp_callback=artifacts.otp_callback,
                phone_callback=artifacts.phone_callback,
                log_fn=ctx.log,
            ),
            browser_register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email or "",
                password=ctx.password or "",
            ),
            oauth_runner=self._run_protocol_oauth,
            capability=RegistrationCapability(oauth_headless_requires_browser_reuse=True),
            otp_spec=OtpSpec(wait_message="Waiting for verification code...", timeout=600),
        )

    def build_protocol_oauth_adapter(self):
        return ProtocolOAuthAdapter(
            oauth_runner=self._run_protocol_oauth,
            result_mapper=lambda ctx, result: self._map_chatgpt_result(result, user_id=result.get("account_id", "")),
        )

    def build_protocol_mailbox_adapter(self):
        def _build_worker(ctx, artifacts):
            from platforms.chatgpt.protocol_mailbox import ChatGPTProtocolMailboxWorker

            return ChatGPTProtocolMailboxWorker(
                mailbox=self.mailbox,
                mailbox_account=ctx.identity.mailbox_account,
                provider=(self.config.extra or {}).get("mail_provider", ""),
                proxy_url=ctx.proxy,
                log_fn=ctx.log,
            )

        def _map_result(ctx, result):
            _assert_complete_oauth_callback(result)
            access_token = result.access_token or ""
            refresh_token = result.refresh_token or ""
            session_token = result.session_token or ""

            return RegistrationResult(
                email=result.email,
                password=result.password or (ctx.password or ""),
                user_id=result.account_id,
                token=access_token,
                status=AccountStatus.REGISTERED,
                extra={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "id_token": result.id_token,
                    "session_token": session_token,
                    "workspace_id": result.workspace_id,
                },
            )

        return ProtocolMailboxAdapter(
            result_mapper=_map_result,
            worker_builder=_build_worker,
            register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password,
            ),
        )

    def get_platform_actions(self) -> list:
        return [
            {"id": "switch_account", "label": "Switch to Codex desktop", "params": []},
            {"id": "get_account_state", "label": "Query account status/subscription", "params": []},
            {"id": "refresh_token", "label": "Refresh Token", "params": []},
            {"id": "payment_link", "label": "Generate payment link",
             "params": [
                 {"key": "country", "label": "Region", "type": "select",
                  "options": ["US","SG","TR","HK","JP","GB","AU","CA"]},
                 {"key": "plan", "label": "Plan", "type": "select",
                  "options": ["plus", "team"]},
             ]},
            {"id": "upload_cpa", "label": "Upload CPA",
             "params": [
                 {"key": "api_url", "label": "CPA API URL", "type": "text"},
                 {"key": "api_key", "label": "CPA API Key", "type": "text"},
             ]},
            {"id": "upload_tm", "label": "Upload Team Manager",
             "params": [
                 {"key": "api_url", "label": "TM API URL", "type": "text"},
                 {"key": "api_key", "label": "TM API Key", "type": "text"},
             ]},
        ]

    def get_desktop_state(self) -> dict:
        from platforms.chatgpt.switch import get_codex_desktop_state

        return get_codex_desktop_state()

    def _execute_platform_action(self, action_id: str, account: Account, params: dict) -> dict:
        """Handle ChatGPT-specific actions."""
        proxy = self.config.proxy if self.config else None
        extra = account.extra or {}

        class _A: pass
        a = _A()
        a.email = account.email
        a.access_token = extra.get("access_token") or account.token
        a.refresh_token = extra.get("refresh_token", "")
        a.id_token = extra.get("id_token", "")
        a.session_token = extra.get("session_token", "")
        from .constants import OAUTH_CLIENT_ID
        a.client_id = extra.get("client_id", OAUTH_CLIENT_ID)
        a.cookies = extra.get("cookies", "")
        a.user_id = account.user_id or ""
        a.account_id = account.user_id or ""

        if action_id == "switch_desktop":
            from platforms.chatgpt.switch import (
                close_codex_app,
                extract_session_token,
                fetch_chatgpt_account_state,
                get_codex_desktop_state,
                read_current_codex_account,
                restart_codex_app,
                switch_codex_account,
            )

            session_token = extract_session_token(a.session_token, a.cookies)
            if not session_token:
                return {"ok": False, "error": "Switch to Codex desktop requires session_token"}

            close_ok, close_msg = close_codex_app()
            switch_ok, switch_data = switch_codex_account(session_token=session_token, cookies=a.cookies)
            if not switch_ok:
                return {"ok": False, "error": switch_data.get("error", "Switch failed")}

            remote_state = fetch_chatgpt_account_state(
                access_token=a.access_token,
                session_token=session_token,
                cookies=a.cookies,
                proxy=proxy,
            )
            local_state = read_current_codex_account()
            restart_ok, restart_msg = restart_codex_app()
            message_parts = [switch_data.get("message", "Codex credentials written")]
            if close_msg:
                message_parts.append(close_msg)
            if restart_msg:
                message_parts.append(restart_msg)
            data = {
                "message": ".".join(part for part in message_parts if part),
                "close": {"ok": close_ok, "message": close_msg},
                "restart": {"ok": restart_ok, "message": restart_msg},
                "local_app_account": local_state,
                "desktop_app_state": get_codex_desktop_state(),
                "remote_state": remote_state,
                "switch_details": switch_data,
            }
            if remote_state.get("access_token"):
                data["access_token"] = remote_state["access_token"]
            if remote_state.get("refresh_token"):
                data["refresh_token"] = remote_state["refresh_token"]
            return {"ok": True, "data": data}

        if action_id == "upload_cpa":
            from platforms.chatgpt.cpa_upload import upload_to_cpa, generate_token_json
            token_data = generate_token_json(a)
            ok, msg = upload_to_cpa(token_data, api_url=params.get("api_url"),
                                    api_key=params.get("api_key"))
            return {"ok": ok, "data": msg}

        if action_id == "upload_tm":
            from platforms.chatgpt.cpa_upload import upload_to_team_manager
            ok, msg = upload_to_team_manager(a, api_url=params.get("api_url"),
                                             api_key=params.get("api_key"))
            return {"ok": ok, "data": msg}

        raise NotImplementedError(f"Unknown action: {action_id}")

    # Override specific capability handlers
    def _handle_query_state(self, account: Account, params: dict) -> dict:
        """Handle query_state capability for ChatGPT."""
        proxy = self.config.proxy if self.config else None
        extra = account.extra or {}

        class _A: pass
        a = _A()
        a.access_token = extra.get("access_token") or account.token
        a.session_token = extra.get("session_token", "")
        a.cookies = extra.get("cookies", "")

        from platforms.chatgpt.switch import fetch_chatgpt_account_state, get_codex_desktop_state, read_current_codex_account

        data = fetch_chatgpt_account_state(
            access_token=a.access_token,
            session_token=a.session_token,
            cookies=a.cookies,
            proxy=proxy,
        )
        data["local_app_account"] = read_current_codex_account()
        data["desktop_app_state"] = get_codex_desktop_state()
        return {"ok": True, "data": data}

    def _handle_refresh_token(self, account: Account, params: dict) -> dict:
        """Handle refresh_token capability for ChatGPT."""
        proxy = self.config.proxy if self.config else None
        extra = account.extra or {}

        class _A: pass
        a = _A()
        a.access_token = extra.get("access_token") or account.token
        a.refresh_token = extra.get("refresh_token", "")
        a.session_token = extra.get("session_token", "")
        a.cookies = extra.get("cookies", "")

        from platforms.chatgpt.token_refresh import TokenRefreshManager
        manager = TokenRefreshManager(proxy_url=proxy)
        result = manager.refresh_account(a)
        if result.success:
            data = {"access_token": result.access_token, "refresh_token": result.refresh_token}
            try:
                from platforms.chatgpt.switch import fetch_chatgpt_account_state
                data["account_state"] = fetch_chatgpt_account_state(
                    access_token=result.access_token,
                    session_token=a.session_token,
                    cookies=a.cookies,
                    proxy=proxy,
                )
            except Exception:
                pass
            return {"ok": True, "data": data}
        return {"ok": False, "error": result.error_message}

    def _handle_generate_link(self, account: Account, params: dict) -> dict:
        """Handle generate_link capability for ChatGPT."""
        proxy = self.config.proxy if self.config else None
        extra = account.extra or {}

        class _A: pass
        a = _A()
        a.email = account.email
        a.password = account.password
        a.session_token = extra.get("session_token", "")
        a.cookies = extra.get("cookies", "")

        from platforms.chatgpt.payment import generate_plus_link, generate_team_link, open_url_incognito
        plan = params.get("plan", "plus")
        country = params.get("country", "US")

        # Manually construct basic cookie in case old accounts don't have complete cookie string
        if not a.cookies and a.session_token:
            a.cookies = f"__Secure-next-auth.session-token={a.session_token}"

        if plan == "plus":
            url = generate_plus_link(a, proxy=proxy, country=country)
        else:
            url = generate_team_link(a, proxy=proxy, country=country)

        # Use local fingerprint browser incognito to mount Cookie and force open payment page
        if url and a.cookies:
            open_url_incognito(url, a.cookies)

        return {"ok": bool(url), "data": {"url": url, "message": "Payment link generated, opening browser with credentials..."}} 

    
