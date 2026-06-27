"""blink.new platform plugin"""
from core.mailbox.base import BaseMailbox
from core.base_platform import Account, AccountStatus, BasePlatform, RegisterConfig
from core.registration import LinkSpec, ProtocolMailboxAdapter, RegistrationResult
from core.registry import register
from platforms.blink.core import BLINK_BASE, BLINK_PRICE_IDS, BlinkRegister, load_blink_account_state


def _status_from_overview(overview: dict) -> AccountStatus:
    plan_state = str((overview or {}).get("plan_state") or "").strip().lower()
    if plan_state == "subscribed":
        return AccountStatus.SUBSCRIBED
    if plan_state == "trial":
        return AccountStatus.TRIAL
    if plan_state == "expired":
        return AccountStatus.EXPIRED
    return AccountStatus.REGISTERED


@register
class BlinkPlatform(BasePlatform):
    name = "blink"
    display_name = "Blink.new"
    version = "1.0.0"
    supported_executors = ["protocol"]
    supported_identity_modes = ["mailbox"]
    capabilities = ["query_state", "create_api_key", "refresh_token"]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        # blink.new has no password, magic link login
        return ""

    def _map_blink_result(self, result: dict) -> RegistrationResult:
        overview = dict(result.get("account_overview") or {})
        return RegistrationResult(
            email=result["email"],
            password="",
            user_id=result.get("user_id", ""),
            token=result.get("firebase_refresh_token") or result.get("refresh_token", ""),
            status=_status_from_overview(overview),
            extra={
                "access_token": result.get("access_token", ""),
                "refresh_token": result.get("refresh_token", ""),
                "id_token": result.get("id_token", ""),
                "firebase_refresh_token": result.get("firebase_refresh_token", ""),
                "session_token": result.get("session_token", ""),
                "workspace_slug": result.get("workspace_slug", ""),
                "workspace_id": result.get("workspace_id", ""),
                "customer_id": result.get("customer_id", ""),
                "referral_code": result.get("referral_code", ""),
                "cashier_url": result.get("cashier_url", ""),
                "account_overview": overview,
            },
        )

    def build_protocol_mailbox_adapter(self):
        def _build_worker(ctx, artifacts):
            from platforms.blink.protocol_mailbox import BlinkProtocolMailboxWorker

            return BlinkProtocolMailboxWorker(proxy=ctx.proxy, log_fn=ctx.log)

        def _run_worker(worker, ctx, artifacts):
            return worker.run(
                email=ctx.identity.email,
                link_callback=artifacts.verification_link_callback,
            )

        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_blink_result(result),
            worker_builder=_build_worker,
            register_runner=_run_worker,
            link_spec=LinkSpec(
                keyword="magic_token",
                wait_message="Waiting for magic link email...",
                success_label="Magic link",
            ),
        )

    def _load_state(self, account: Account, *, force_refresh: bool = False) -> dict:
        return load_blink_account_state(
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
            {"id": "get_account_state", "label": "Query account state / quota", "params": []},
            {"id": "generate_checkout_link", "label": "Generate Pro payment link", "params": []},
            {
                "id": "create_api_key",
                "label": "Create API Key",
                "params": [
                    {"key": "name", "label": "Key name", "type": "text"},
                ],
            },
        ]

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        if action_id in {"get_user_info", "get_account_state"}:
            state = self._load_state(account)
            return {"ok": True, "data": state.get("summary", {})}

        if action_id in {"generate_checkout_link", "payment_link", "get_cashier_url"}:
            state = self._load_state(account, force_refresh=True)
            summary = dict(state.get("summary") or {})
            workspace_id = str(state.get("workspace_id") or summary.get("workspace_id") or "")
            if not workspace_id:
                return {"ok": False, "error": "workspace_id not obtained, cannot generate Blink payment link"}

            plan_id = str(params.get("plan_id") or "pro").strip().lower() or "pro"
            price_id = str(params.get("price_id") or BLINK_PRICE_IDS.get(plan_id) or "").strip()
            if not price_id:
                return {"ok": False, "error": f"No price_id configured for plan_id={plan_id}"}

            workspace_slug = str(state.get("workspace_slug") or summary.get("workspace_slug") or "").strip()
            cancel_url = str(
                params.get("cancel_url")
                or (f"{BLINK_BASE}/{workspace_slug}?showPricing=true" if workspace_slug else f"{BLINK_BASE}/?showPricing=true")
            ).strip()

            client = BlinkRegister(proxy=self.config.proxy if self.config else None)
            client._log = self.log
            checkout = client.create_checkout(
                state.get("id_token", ""),
                price_id=price_id,
                plan_id=plan_id,
                workspace_id=workspace_id,
                cancel_url=cancel_url,
                session_token=str(state.get("session_token") or ""),
                workspace_slug=workspace_slug,
                tolt_referral_id=params.get("tolt_referral_id"),
            )
            url = str(checkout.get("url") or "").strip()
            if not url:
                return {"ok": False, "error": "Blink did not return payment link"}
            return {
                "ok": True,
                "data": {
                    "url": url,
                    "cashier_url": url,
                    "session_id": str(checkout.get("sessionId") or ""),
                    "workspace_id": workspace_id,
                    "workspace_slug": workspace_slug,
                    "plan_id": plan_id,
                    "price_id": price_id,
                    "account_state": summary,
                    "message": "Blink Pro payment link generated",
                },
            }

        if action_id == "create_api_key":
            state = self._load_state(account, force_refresh=True)
            summary = dict(state.get("summary") or {})
            workspace_id = str(state.get("workspace_id") or summary.get("workspace_id") or "").strip()
            if not workspace_id:
                return {"ok": False, "error": "workspace_id not obtained, cannot create Blink API Key"}

            workspace_slug = str(state.get("workspace_slug") or summary.get("workspace_slug") or "").strip()
            raw_name = str(params.get("name") or "").strip()
            key_name = raw_name or "Dev Key"

            client = BlinkRegister(proxy=self.config.proxy if self.config else None)
            client._log = self.log
            payload = client.create_api_key(
                state.get("id_token", ""),
                workspace_id=workspace_id,
                name=key_name,
                session_token=str(state.get("session_token") or ""),
                workspace_slug=workspace_slug,
            )
            api_key = str(payload.get("key_value") or "").strip()
            if not api_key:
                return {"ok": False, "error": "Blink did not return API Key plaintext"}
            return {
                "ok": True,
                "data": {
                    "id": str(payload.get("id") or ""),
                    "name": str(payload.get("name") or key_name),
                    "key_prefix": str(payload.get("key_prefix") or ""),
                    "key_value": api_key,
                    "api_key": api_key,
                    "workspace_id": workspace_id,
                    "workspace_slug": workspace_slug,
                    "message": "Blink API Key created",
                },
            }

        raise NotImplementedError(f"Unknown action: {action_id}")
