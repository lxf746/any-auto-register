"""Blackbox AI platform plugin."""
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.base_mailbox import BaseMailbox
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, RegistrationCapability, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register


@register
class BlackboxPlatform(BasePlatform):
    name = "blackbox"
    display_name = "Blackbox AI"
    version = "1.0.0"
    supported_executors = ["headless", "headed"]
    supported_identity_modes = ["mailbox"]

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

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return password or self._make_random_password()

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
            capability=RegistrationCapability(),
            otp_spec=OtpSpec(
                wait_message="Waiting for Blackbox verification code...",
                timeout=resolve_timeout(self.config.extra or {}, ("otp_timeout",), 120),
            ),
        )

    def check_valid(self, account: Account) -> bool:
        """Verify account is valid by logging in."""
        email = account.email
        password = account.password
        if not email or not password:
            self._last_check_overview = {"validity_status": "invalid", "check_error": "missing credentials"}
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
        return [
            {"id": "login_check", "label": "Verify login", "params": []},
        ]

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        if action_id == "login_check":
            email = account.email
            password = account.password
            if not email or not password:
                return {"ok": False, "error": "Missing email or password"}
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
