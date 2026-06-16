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
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return password or ""

    def _map_result(self, result: dict, *, password: str = "") -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password=password or result.get("password", ""),
            token=result.get("token", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "name": result.get("name", ""),
                "token": result.get("token", ""),
            },
        )

    def build_browser_registration_adapter(self):
        return BrowserRegistrationAdapter(
            result_mapper=lambda ctx, result: self._map_result(result),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.blackbox.browser_register", fromlist=["BlackboxBrowserRegister"]).BlackboxBrowserRegister(
                headless=(ctx.executor_type == "headless"),
                proxy=ctx.proxy,
                log_fn=ctx.log,
            ),
            browser_register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email or "",
                password=ctx.password or "",
            ),
            capability=RegistrationCapability(),
            otp_spec=OtpSpec(wait_message="Waiting for OTP..."),
        )

    def check_valid(self, account: Account) -> bool:
        return bool(account.token or (account.extra or {}).get("token", ""))

    def get_platform_actions(self) -> list:
        return []

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        raise NotImplementedError(f"Unknown action: {action_id}")
