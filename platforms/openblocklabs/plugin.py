"""OpenBlockLabs platform plugin"""
import random, string
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.mailbox.base import BaseMailbox
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, ProtocolOAuthAdapter, RegistrationCapability, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register


@register
class OpenBlockLabsPlatform(BasePlatform):
    name = "openblocklabs"
    display_name = "OpenBlockLabs"
    version = "1.0.0"
    supported_executors = ["protocol", "headless", "headed"]
    supported_identity_modes = ["mailbox", "oauth_browser"]
    capabilities = ["query_state"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return password or ""

    def _map_openblocklabs_result(self, result: dict, *, password: str = "") -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password=password or result.get("password", ""),
            token=result.get("wos_session", ""),
            status=AccountStatus.REGISTERED,
            extra={"wos_session": result.get("wos_session", "")},
        )

    def _run_protocol_oauth(self, ctx) -> dict:
        from platforms.openblocklabs.browser_oauth import register_with_browser_oauth

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
            result_mapper=lambda ctx, result: self._map_openblocklabs_result(result),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.openblocklabs.browser_register", fromlist=["OpenBlockLabsBrowserRegister"]).OpenBlockLabsBrowserRegister(
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
            otp_spec=OtpSpec(wait_message="Waiting for verification code..."),
        )

    def build_protocol_oauth_adapter(self):
        return ProtocolOAuthAdapter(
            oauth_runner=self._run_protocol_oauth,
            result_mapper=lambda ctx, result: self._map_openblocklabs_result(result),
        )

    def build_protocol_mailbox_adapter(self):
        def _build_worker(ctx, artifacts):
            from platforms.openblocklabs.protocol_mailbox import OpenBlockLabsProtocolMailboxWorker

            return OpenBlockLabsProtocolMailboxWorker(proxy=ctx.proxy, log_fn=ctx.log)

        def _run_worker(worker, ctx, artifacts):
            return worker.run(
                email=ctx.identity.email,
                password=ctx.password,
                first_name="".join(random.choices(string.ascii_lowercase, k=5)).capitalize(),
                last_name="".join(random.choices(string.ascii_lowercase, k=5)).capitalize(),
                otp_callback=artifacts.otp_callback,
            )

        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_openblocklabs_result(result),
            worker_builder=_build_worker,
            register_runner=_run_worker,
            otp_spec=OtpSpec(wait_message="Waiting for verification code..."),
        )

    def check_valid(self, account: Account) -> bool:
        return bool(account.extra.get("wos_session"))
