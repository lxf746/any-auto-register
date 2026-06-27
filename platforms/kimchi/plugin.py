"""kimchi.dev platform plugin

Auth model: Auth0 email/password registration with email verification.
  - Signup via Auth0 (email/password)
  - Email verification link sent by Auth0
  - After verification: authorization code → tokens → API key
  - API keys via Cast.ai backend API
"""
from core.mailbox.base import BaseMailbox
from core.base_platform import Account, AccountStatus, BasePlatform, RegisterConfig
from core.registration import LinkSpec, ProtocolMailboxAdapter, RegistrationResult
from core.registry import register


@register
class KimchiPlatform(BasePlatform):
    name = "kimchi"
    display_name = "Kimchi.dev"
    version = "1.0.0"
    supported_executors = ["protocol"]
    supported_identity_modes = ["mailbox"]
    capabilities = ["query_state", "create_api_key"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        if password and len(password) >= 8:
            return password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        return "".join(secrets.choice(alphabet) for _ in range(16))

    def _map_result(self, result: dict) -> RegistrationResult:
        return RegistrationResult(
            email=result.get("email", ""),
            password=result.get("password", ""),
            user_id=result.get("user_id", ""),
            status=AccountStatus.REGISTERED,
            extra={
                "api_key": result.get("api_key", ""),
                "access_token": result.get("access_token", ""),
                "id_token": result.get("id_token", ""),
                "refresh_token": result.get("refresh_token", ""),
            },
        )

    def build_protocol_mailbox_adapter(self):
        def _build_worker(ctx, artifacts):
            from platforms.kimchi.protocol_mailbox import KimchiProtocolMailboxWorker
            return KimchiProtocolMailboxWorker(
                proxy=ctx.proxy,
                log_fn=ctx.log,
            )

        def _run_worker(worker, ctx, artifacts):
            mailbox_token = ""
            if ctx.identity.mailbox_account:
                mailbox_token = ctx.identity.mailbox_account.account_id or ""
            return worker.run(
                email=ctx.identity.email,
                password=ctx.password or "",
                link_callback=artifacts.verification_link_callback,
                mailbox_token=mailbox_token,
            )

        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_result(result),
            worker_builder=_build_worker,
            register_runner=_run_worker,
            link_spec=LinkSpec(
                keyword="verify",
                wait_message="Waiting for Auth0 verification email...",
                success_label="Verification link",
            ),
        )

    def check_valid(self, account: Account) -> bool:
        api_key = (account.extra or {}).get("api_key", "")
        if not api_key:
            return False
        try:
            from platforms.kimchi.core import KimchiRegister
            result = KimchiRegister().check_api_key_valid(api_key)
            return result.get("valid", False)
        except Exception:
            return False

    def get_platform_actions(self) -> list:
        return [
            {"id": "get_account_state", "label": "Query account state", "params": []},
            {"id": "validate_api_key", "label": "Validate API key", "params": []},
            {"id": "list_models", "label": "List available models", "params": []},
        ]

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        from platforms.kimchi.core import KimchiRegister

        api_key = (account.extra or {}).get("api_key", "")
        if not api_key:
            return {"ok": False, "error": "No API key in account"}

        client = KimchiRegister()

        if action_id == "get_account_state":
            result = client.check_api_key_valid(api_key)
            return {
                "ok": True,
                "data": {
                    "valid": result.get("valid", False),
                    "models": result.get("models", []),
                    "api_key_preview": f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else api_key,
                },
            }

        if action_id == "validate_api_key":
            result = client.check_api_key_valid(api_key)
            return {"ok": True, "data": result}

        if action_id == "list_models":
            result = client.check_api_key_valid(api_key)
            return {
                "ok": True,
                "data": {
                    "models": result.get("models", []),
                    "count": len(result.get("models", [])),
                },
            }

        raise NotImplementedError(f"Unknown action: {action_id}")
