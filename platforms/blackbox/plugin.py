"""Blackbox AI platform plugin."""
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.base_mailbox import BaseMailbox
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, ProtocolOAuthAdapter, RegistrationCapability, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register


@register
class BlackboxPlatform(BasePlatform):
    name = "blackbox"
    display_name = "Blackbox AI"
    version = "1.0.0"
    supported_executors = ["headless", "headed"]
    supported_identity_modes = ["mailbox", "oauth_browser"]
    supported_oauth_providers = ["google"]

    capabilities = []

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        # Actions/runtime may instantiate with default config; defer executor check
        saved_executors = list(self.supported_executors)
        try:
            super().__init__(config)
        except NotImplementedError:
            self.config = config or RegisterConfig()
            self.supported_executors = saved_executors
        self.mailbox = mailbox
        self._last_check_overview: dict = {}

    def _run_browser_oauth(self, ctx) -> dict:
        from platforms.blackbox.browser_oauth import register_with_browser_oauth

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

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return password or self._make_random_password()

    def _map_oauth_result(self, result: dict) -> RegistrationResult:
        subscription_status = result.get("subscription_status", "").lower()
        has_subscription = subscription_status in ("pro", "plus", "max", "enterprise")
        plan_name = "Pro" if has_subscription else "Free"
        plan_state = "subscribed" if has_subscription else "free"
        return RegistrationResult(
            email=result.get("email", ""),
            password=result.get("password", ""),
            token=result.get("token", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "name": result.get("name", ""),
                "token": result.get("token", ""),
                "oauth_provider": result.get("oauth_provider", ""),
                "subscription_status": subscription_status,
                "account_overview": {
                    "plan_state": plan_state,
                    "plan_name": plan_name,
                    "validity_status": "unknown",
                    "display_status": "registered",
                    "lifecycle_status": "registered",
                },
            },
        )

    def _map_result(self, result: dict, *, password: str = "") -> RegistrationResult:
        pwd = password or result.get("password", "")
        return RegistrationResult(
            email=result.get("email", ""),
            password=pwd,
            token=result.get("token", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "name": result.get("name", ""),
                "token": result.get("token", ""),
                "password": pwd,
                "account_overview": {
                    "plan_state": "free",
                    "plan_name": "Free",
                    "validity_status": "unknown",
                    "display_status": "registered",
                    "lifecycle_status": "registered",
                },
            },
        )

    def build_browser_registration_adapter(self):
        return BrowserRegistrationAdapter(
            result_mapper=lambda ctx, result: self._map_result(result, password=ctx.password),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.blackbox.browser_register", fromlist=["BlackboxBrowserRegister"]).BlackboxBrowserRegister(
                headless=(ctx.executor_type == "headless"),
                proxy=ctx.proxy,
                log_fn=ctx.log,
                otp_callback=artifacts.otp_callback,
            ),
            browser_register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email or "",
                password=ctx.password or "",
            ),
            oauth_runner=self._run_browser_oauth,
            capability=RegistrationCapability(
                oauth_allowed_executor_types=("headless", "headed"),
                oauth_headless_requires_browser_reuse=True,
            ),
            otp_spec=OtpSpec(
                wait_message="Waiting for Blackbox verification code...",
                timeout=resolve_timeout(self.config.extra or {}, ("otp_timeout",), 120),
            ),
        )

    def build_protocol_oauth_adapter(self):
        return ProtocolOAuthAdapter(
            oauth_runner=self._run_browser_oauth,
            result_mapper=lambda ctx, result: self._map_oauth_result(result),
        )

    def check_valid(self, account: Account) -> bool:
        """Verify account is valid by logging in or checking OAuth token."""
        email = account.email
        password = account.password
        extra = account.extra or {}
        is_oauth = bool(extra.get("oauth_provider"))
        
        if not email:
            self._last_check_overview = {"validity_status": "invalid", "check_error": "missing email"}
            return False
            
        # For OAuth accounts, check if token is still valid
        if is_oauth:
            token = account.token or extra.get("token", "")
            if token:
                # Try to verify token via API
                try:
                    import requests
                    headers = {"Authorization": f"Bearer {token}"}
                    resp = requests.get("https://app.blackbox.ai/api/auth/session", headers=headers, timeout=10)
                    if resp.status_code == 200:
                        subscription_status = extra.get("subscription_status", "free")
                        has_subscription = subscription_status in ("pro", "plus", "max", "enterprise")
                        self._last_check_overview = {
                            "validity_status": "valid",
                            "plan_state": "subscribed" if has_subscription else "free",
                            "plan_name": "Pro" if has_subscription else "Free",
                            "display_status": "active",
                            "check_source": "oauth_token",
                        }
                        return True
                except Exception:
                    pass
            self._last_check_overview = {"validity_status": "invalid", "check_error": "OAuth token invalid"}
            return False
        
        # For regular accounts with password
        if not password:
            self._last_check_overview = {"validity_status": "invalid", "check_error": "missing password"}
            return False
            
        try:
            from platforms.blackbox.browser_register import BlackboxBrowserRegister
            reg = BlackboxBrowserRegister(headless=True)
            result = reg.login(email, password)
            logged_in = result.get("logged_in", False)
            account_info = result.get("account_info", {})
            if logged_in:
                self._last_check_overview = {
                    "validity_status": "valid",
                    "plan_state": account_info.get("plan", "free"),
                    "plan_name": "Pro" if account_info.get("has_subscription") else "Free",
                    "display_status": "active",
                    "check_source": "browser_login",
                }
            else:
                self._last_check_overview = {
                    "validity_status": "invalid",
                    "check_source": "browser_login",
                }
            return logged_in
        except Exception as exc:
            self._last_check_overview = {"validity_status": "invalid", "check_error": str(exc)}
            return False

    def get_last_check_overview(self) -> dict:
        return dict(self._last_check_overview or {})

    def get_platform_actions(self) -> list:
        actions = [
            {"id": "login_check", "label": "Verify login", "params": []},
        ]
        # Check if account has OAuth provider
        return actions

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        if action_id == "login_check":
            email = account.email
            password = account.password
            extra = account.extra or {}
            is_oauth = bool(extra.get("oauth_provider"))
            
            if not email:
                return {"ok": False, "error": "Missing email"}
                
            # For OAuth accounts, check token
            if is_oauth:
                token = account.token or extra.get("token", "")
                if not token:
                    return {"ok": False, "error": "OAuth account missing token"}
                try:
                    import requests
                    headers = {"Authorization": f"Bearer {token}"}
                    resp = requests.get("https://app.blackbox.ai/api/auth/session", headers=headers, timeout=10)
                    if resp.status_code == 200:
                        return {
                            "ok": True,
                            "data": {
                                "logged_in": True,
                                "token_preview": token[:20] + "..." if token else "",
                            }
                        }
                    else:
                        return {"ok": False, "error": f"OAuth token invalid (HTTP {resp.status_code})"}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
            
            # For regular accounts with password
            if not password:
                return {"ok": False, "error": "Missing password"}
            try:
                from platforms.blackbox.browser_register import BlackboxBrowserRegister
                reg = BlackboxBrowserRegister(headless=True)
                result = reg.login(email, password)
                if result.get("logged_in"):
                    return {
                        "ok": True,
                        "data": {
                            "logged_in": True,
                            "token_preview": result.get("token", "")[:20] + "..." if result.get("token") else "",
                        }
                    }
                else:
                    return {"ok": False, "error": "Login failed - account may not exist or password is wrong"}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        raise NotImplementedError(f"Unknown action: {action_id}")
