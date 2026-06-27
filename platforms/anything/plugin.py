"""anything.com platform plugin."""
from __future__ import annotations

from core.mailbox.base import BaseMailbox
from core.base_platform import Account, AccountStatus, BasePlatform, RegisterConfig
from core.registration import LinkSpec, ProtocolMailboxAdapter, RegistrationResult
from core.registry import register
from platforms.anything.core import (
    ANYTHING_BASE,
    ANYTHING_CHECKOUT_LOOKUPS,
    ANYTHING_DEFAULT_REFERRAL_CODE,
    AnythingClient,
    load_anything_account_state,
)


def _status_from_overview(overview: dict) -> AccountStatus:
    plan_state = str((overview or {}).get("plan_state") or "").strip().lower()
    if plan_state == "subscribed":
        return AccountStatus.SUBSCRIBED
    return AccountStatus.REGISTERED


@register
class AnythingPlatform(BasePlatform):
    name = "anything"
    display_name = "Anything"
    version = "1.0.0"
    supported_executors = ["protocol"]
    supported_identity_modes = ["mailbox"]
    capabilities = ["query_state", "generate_link"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return ""

    def _map_anything_result(self, result: dict) -> RegistrationResult:
        overview = dict(result.get("account_overview") or {})
        return RegistrationResult(
            email=result["email"],
            password="",
            user_id=result.get("user_id", ""),
            token=result.get("refresh_token") or result.get("access_token", ""),
            status=_status_from_overview(overview),
            extra={
                "access_token": result.get("access_token", ""),
                "refresh_token": result.get("refresh_token", ""),
                "user_id": result.get("user_id", ""),
                "email": result.get("email", ""),
                "organization_id": result.get("organization_id", ""),
                "project_group_id": result.get("project_group_id", ""),
                "cashier_url": result.get("cashier_url", ""),
                "usage": result.get("usage", {}),
                "account_overview": overview,
                "signup_payload": result.get("signup_payload", {}),
            },
        )

    def build_protocol_mailbox_adapter(self):
        def _build_worker(ctx, artifacts):
            from platforms.anything.protocol_mailbox import AnythingProtocolMailboxWorker

            return AnythingProtocolMailboxWorker(proxy=ctx.proxy, log_fn=ctx.log)

        def _run_worker(worker, ctx, artifacts):
            extra = dict(ctx.extra or {})
            return worker.run(
                email=ctx.identity.email,
                link_callback=artifacts.verification_link_callback,
                referral_code=str(extra.get("anything_referral_code", ANYTHING_DEFAULT_REFERRAL_CODE) or ""),
                language=str(extra.get("anything_language", "zh-CN") or "zh-CN"),
                post_login_redirect=extra.get("anything_post_login_redirect"),
            )

        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_anything_result(result),
            worker_builder=_build_worker,
            register_runner=_run_worker,
            link_spec=LinkSpec(
                keyword="anything",
                wait_message="Waiting for Anything magic link email...",
                success_label="Magic link",
            ),
        )

    def _load_state(self, account: Account, *, force_refresh: bool = False) -> dict:
        return load_anything_account_state(
            account,
            proxy=self.config.proxy if self.config else None,
            log_fn=self.log,
            force_refresh=force_refresh,
        )

    def check_valid(self, account: Account) -> bool:
        try:
            state = self._load_state(account)
        except Exception:
            return False
        return bool((state.get("summary") or {}).get("valid"))

    def get_platform_actions(self) -> list:
        return [
            {"id": "get_account_state", "label": "Query account state", "params": []},
            {"id": "generate_checkout_link", "label": "Generate payment link", "params": []},
        ]

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        if action_id in {"get_user_info", "get_account_state"}:
            state = self._load_state(account)
            return {"ok": True, "data": state.get("summary", {})}

        if action_id in {"generate_checkout_link", "payment_link", "get_cashier_url"}:
            state = self._load_state(account, force_refresh=True)
            summary = dict(state.get("summary") or {})
            organization_id = str(summary.get("organization_id") or "").strip()
            if not organization_id:
                return {"ok": False, "error": "organization_id not obtained, cannot generate Anything payment link"}

            lookup = str(params.get("lookup") or ANYTHING_CHECKOUT_LOOKUPS.get("pro_20_monthly") or "").strip()
            if not lookup:
                return {"ok": False, "error": "checkout lookup not provided"}

            client = AnythingClient(proxy=self.config.proxy if self.config else None, log_fn=self.log)
            checkout = client.create_checkout_session_with_lookup(
                access_token=str(state.get("access_token") or ""),
                organization_id=organization_id,
                lookup=lookup,
                redirect_url=str(params.get("redirect_url") or ANYTHING_BASE).strip() or ANYTHING_BASE,
                referral=str(params.get("referral") or ""),
            )
            return {
                "ok": True,
                "data": {
                    "url": checkout["url"],
                    "cashier_url": checkout["url"],
                    "lookup": checkout["lookup"],
                    "organization_id": organization_id,
                    "account_state": summary,
                    "message": "Anything payment link generated",
                },
            }

        raise NotImplementedError(f"Unknown action: {action_id}")
