"""Tavily platform plugin"""
import random, string
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.mailbox.base import BaseMailbox
from core.registration import BrowserRegistrationAdapter, LinkSpec, OtpSpec, ProtocolMailboxAdapter, ProtocolOAuthAdapter, RegistrationCapability, RegistrationResult
from core.registry import register


@register
class TavilyPlatform(BasePlatform):
    name = "tavily"
    display_name = "Tavily"
    version = "1.0.0"
    supported_executors = ["protocol", "headless", "headed"]
    supported_identity_modes = ["mailbox", "oauth_browser"]
    capabilities = ["query_state"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _browser_registration_label(self, identity) -> str:
        return getattr(identity, "email", "") or "(manual oauth)"

    def _prepare_registration_password(self, password: str | None) -> str | None:
        if password:
            return password
        return "".join(random.choices(string.ascii_letters + string.digits + "!@#", k=14))

    def _map_tavily_result(self, result: dict) -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password=result["password"],
            status=AccountStatus.REGISTERED,
            extra={"api_key": result["api_key"]},
        )

    def _browser_preflight(self, ctx) -> None:
        if ctx.identity.identity_provider != "mailbox":
            return
        solver_key = ctx.platform._resolve_captcha_solver()
        from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository

        definition = ProviderDefinitionsRepository().get_by_key("captcha", solver_key)
        if definition and definition.driver_type == "local_solver":
            from services.solver_manager import start

            start()

    def build_browser_registration_adapter(self):
        return BrowserRegistrationAdapter(
            result_mapper=lambda ctx, result: self._map_tavily_result(result),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.tavily.browser_register", fromlist=["TavilyBrowserRegister"]).TavilyBrowserRegister(
                captcha=artifacts.captcha_solver if ctx.identity.identity_provider == "mailbox" else None,
                headless=(ctx.executor_type == "headless"),
                proxy=ctx.proxy,
                otp_callback=artifacts.otp_callback,
                verification_link_callback=artifacts.verification_link_callback,
                api_key_timeout=int(ctx.extra.get("api_key_timeout", 20) or 20),
                log_fn=ctx.log,
            ),
            browser_register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password,
            ),
            oauth_runner=self._run_browser_oauth,
            capability=RegistrationCapability(oauth_allowed_executor_types=("headed",)),
            otp_spec=OtpSpec(wait_message="Waiting for verification code email..."),
            link_spec=LinkSpec(wait_message="Waiting for verification link email..."),
            use_captcha_for_mailbox=True,
            preflight=self._browser_preflight,
        )

    def _run_browser_oauth(self, ctx) -> dict:
        from platforms.tavily.browser_oauth import register_with_browser_oauth

        return register_with_browser_oauth(
            proxy=ctx.proxy,
            oauth_provider=ctx.identity.oauth_provider,
            email_hint=ctx.identity.email,
            timeout=int(ctx.extra.get("browser_oauth_timeout", ctx.extra.get("manual_oauth_timeout", 300)) or 300),
            log_fn=ctx.log,
            chrome_user_data_dir=ctx.identity.chrome_user_data_dir,
            chrome_cdp_url=ctx.identity.chrome_cdp_url,
        )

    def build_protocol_oauth_adapter(self):
        return ProtocolOAuthAdapter(
            oauth_runner=lambda ctx: (_ for _ in ()).throw(RuntimeError("Tavily currently only supports oauth_browser in browser mode, please use executor_type=headed")),
            result_mapper=lambda ctx, result: self._map_tavily_result(result),
        )

    def build_protocol_mailbox_adapter(self):
        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_tavily_result(result),
            worker_builder=lambda ctx, artifacts: __import__("platforms.tavily.protocol_mailbox", fromlist=["TavilyProtocolMailboxWorker"]).TavilyProtocolMailboxWorker(
                executor=artifacts.executor,
                captcha=artifacts.captcha_solver,
                log_fn=ctx.log,
            ),
            register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password,
                otp_callback=artifacts.otp_callback,
            ),
            otp_spec=OtpSpec(wait_message="Waiting for verification code email..."),
            use_captcha=True,
            use_executor=True,
        )

    def check_valid(self, account: Account) -> bool:
        api_key = account.extra.get("api_key", "")
        if not api_key:
            return False
        import requests
        try:
            r = requests.post("https://api.tavily.com/search",
                              json={"api_key": api_key, "query": "test", "max_results": 1},
                              timeout=10)
            return r.status_code != 401
        except Exception:
            return False
