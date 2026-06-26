"""Cerebras Cloud platform plugin"""
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.base_mailbox import BaseMailbox
from core.registration import OtpSpec, ProtocolMailboxAdapter, RegistrationResult
from core.registry import register


@register
class CerebrasPlatform(BasePlatform):
    name = "cerebras"
    display_name = "Cerebras"
    version = "1.0.0"
    supported_executors = ["protocol"]
    supported_identity_modes = ["mailbox"]
    capabilities = ["query_state", "create_api_key"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        # Cerebras uses passwordless auth (Stytch OTP)
        return ""

    def _map_result(self, result: dict) -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password="",
            user_id=result.get("user_id", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "api_key": result.get("api_key", ""),
                "session_token": result.get("session_token", ""),
                "session_jwt": result.get("session_jwt", ""),
            },
        )

    def build_protocol_mailbox_adapter(self):
        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_result(result),
            worker_builder=lambda ctx, artifacts: __import__(
                "platforms.cerebras.protocol_mailbox",
                fromlist=["CerebrasProtocolMailboxWorker"],
            ).CerebrasProtocolMailboxWorker(
                executor=artifacts.executor,
                log_fn=ctx.log,
            ),
            register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password="",
                otp_callback=artifacts.otp_callback,
            ),
            otp_spec=OtpSpec(wait_message="Waiting for OTP email..."),
            use_executor=True,
        )

    def check_valid(self, account: Account) -> bool:
        api_key = (account.extra or {}).get("api_key", "")
        if not api_key:
            return False
        try:
            from core.executors.protocol import ProtocolExecutor
            with ProtocolExecutor(proxy=self.config.proxy if self.config else None) as ex:
                r = ex.get(
                    "https://api.cerebras.ai/v1/models",
                    headers={
                        "authorization": f"Bearer {api_key}",
                        "accept": "application/json",
                    },
                )
                return r.status_code == 200
        except Exception:
            return False

    def get_platform_actions(self) -> list:
        return [
            {"id": "get_account_state", "label": "Query account state", "params": []},
        ]

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        if action_id == "get_account_state":
            valid = self.check_valid(account)
            api_key = (account.extra or {}).get("api_key", "")
            return {
                "ok": True,
                "data": {
                    "valid": valid,
                    "api_key_preview": f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else api_key,
                },
            }
        raise NotImplementedError(f"Unknown action: {action_id}")
