"""Grok (x.ai) platform plugin"""
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.mailbox.base import BaseMailbox
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, ProtocolOAuthAdapter, RegistrationCapability, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register


@register
class GrokPlatform(BasePlatform):
    name = "grok"
    display_name = "Grok"
    version = "1.0.0"
    supported_executors = ["protocol", "headless", "headed"]
    supported_identity_modes = ["mailbox", "oauth_browser"]
    capabilities = ["query_state", "generate_link"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return password or ""

    def _map_grok_result(self, result: dict, *, password: str = "") -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password=password or result.get("password", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "sso": result.get("sso", ""),
                "sso_rw": result.get("sso_rw", ""),
                "given_name": result.get("given_name", ""),
                "family_name": result.get("family_name", ""),
            },
        )

    def _run_protocol_oauth(self, ctx) -> dict:
        from platforms.grok.browser_oauth import register_with_browser_oauth

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
            result_mapper=lambda ctx, result: self._map_grok_result(result),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.grok.browser_register", fromlist=["GrokBrowserRegister"]).GrokBrowserRegister(
                headless=(ctx.executor_type == "headless"),
                proxy=ctx.proxy,
                otp_callback=artifacts.otp_callback,
                log_fn=ctx.log,
            ),
            browser_register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email or "",
                password=ctx.password or "",
            ),
            oauth_runner=self._run_protocol_oauth,
            capability=RegistrationCapability(oauth_allowed_executor_types=("headed",)),
            otp_spec=OtpSpec(wait_message="Waiting for verification code...", code_pattern=r"[A-Z0-9]{3}-[A-Z0-9]{3}"),
        )

    def build_protocol_oauth_adapter(self):
        return ProtocolOAuthAdapter(
            oauth_runner=self._run_protocol_oauth,
            result_mapper=lambda ctx, result: self._map_grok_result(result),
        )

    def build_protocol_mailbox_adapter(self):
        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_grok_result(result),
            worker_builder=lambda ctx, artifacts: __import__("platforms.grok.protocol_mailbox", fromlist=["GrokProtocolMailboxWorker"]).GrokProtocolMailboxWorker(
                captcha_solver=artifacts.captcha_solver,
                proxy=ctx.proxy,
                log_fn=ctx.log,
            ),
            register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password,
                otp_callback=artifacts.otp_callback,
            ),
            otp_spec=OtpSpec(wait_message="Waiting for verification code...", code_pattern=r"[A-Z0-9]{3}-[A-Z0-9]{3}"),
            use_captcha=True,
        )

    def check_valid(self, account: Account) -> bool:
        return bool((account.extra or {}).get("sso"))

    def get_platform_actions(self) -> list:
        return []

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        raise NotImplementedError(f"Unknown action: {action_id}")
