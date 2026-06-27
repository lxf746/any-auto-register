"""Trae.ai platform plugin"""
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.mailbox.base import BaseMailbox
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, ProtocolOAuthAdapter, RegistrationCapability, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register


@register
class TraePlatform(BasePlatform):
    name = "trae"
    display_name = "Trae.ai"
    version = "1.0.0"
    supported_executors = ["protocol", "headless", "headed"]
    supported_identity_modes = ["mailbox", "oauth_browser"]
    capabilities = ["query_state", "generate_link"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return password or ""

    def _map_trae_result(self, result: dict, *, password: str = "") -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password=password or result.get("password", ""),
            user_id=result.get("user_id", ""),
            token=result.get("token", ""),
            region=result.get("region", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "cashier_url": result.get("cashier_url", ""),
                "ai_pay_host": result.get("ai_pay_host", ""),
                "final_url": result.get("final_url", ""),
            },
        )

    def _run_protocol_oauth(self, ctx) -> dict:
        from platforms.trae.browser_oauth import register_with_browser_oauth

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
            result_mapper=lambda ctx, result: self._map_trae_result(result),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.trae.browser_register", fromlist=["TraeBrowserRegister"]).TraeBrowserRegister(
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
            result_mapper=lambda ctx, result: self._map_trae_result(result),
        )

    def build_protocol_mailbox_adapter(self):
        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_trae_result(result),
            worker_builder=lambda ctx, artifacts: __import__("platforms.trae.protocol_mailbox", fromlist=["TraeProtocolMailboxWorker"]).TraeProtocolMailboxWorker(
                executor=artifacts.executor,
                log_fn=ctx.log,
            ),
            register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password,
                otp_callback=artifacts.otp_callback,
            ),
            otp_spec=OtpSpec(wait_message="Waiting for verification code..."),
            use_executor=True,
        )

    def check_valid(self, account: Account) -> bool:
        return bool(account.token)

    def get_platform_actions(self) -> list:
        """Return the list of supported platform actions"""
        return [
            {"id": "switch_account", "label": "Switch to desktop app", "params": []},
            {"id": "get_user_info", "label": "Get user info", "params": []},
            {"id": "get_cashier_url", "label": "Get upgrade link", "params": []},
        ]

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        """Execute platform action"""
        if action_id == "switch_account":
            from platforms.trae.switch import switch_trae_account, restart_trae_ide
            
            token = account.token
            user_id = account.user_id or ""
            email = account.email or ""
            region = account.region or ""
            
            if not token:
                return {"ok": False, "error": "Account missing token"}
            
            ok, msg = switch_trae_account(token, user_id, email, region)
            if not ok:
                return {"ok": False, "error": msg}
            
            restart_ok, restart_msg = restart_trae_ide()
            return {
                "ok": True,
                "data": {
                    "message": f"{msg}. {restart_msg}" if restart_ok else msg,
                }
            }
        
        elif action_id == "get_user_info":
            from platforms.trae.switch import get_trae_user_info
            
            token = account.token
            if not token:
                return {"ok": False, "error": "Account missing token"}
            
            user_info = get_trae_user_info(token)
            if user_info:
                return {"ok": True, "data": user_info}
            return {"ok": False, "error": "Failed to get user info"}
        
        elif action_id == "get_cashier_url":
            from platforms.trae.core import TraeRegister
            with self._make_executor() as ex:
                reg = TraeRegister(executor=ex)
                # Re-login to refresh session, then get new token and cashier_url
                reg.step4_trae_login()
                token = reg.step5_get_token()
                if not token:
                    token = account.token
                cashier_url = reg.step7_create_order(token)
            if not cashier_url:
                return {"ok": False, "error": "Failed to get upgrade link, token may be expired, please re-register"}
            return {"ok": True, "data": {"cashier_url": cashier_url, "message": "Please open the upgrade link in browser to complete Pro subscription"}}

        raise NotImplementedError(f"Unknown action: {action_id}")
