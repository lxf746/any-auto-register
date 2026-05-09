"""Cursor 平台插件"""
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.base_mailbox import BaseMailbox
from core.registration import BrowserRegistrationAdapter, OtpSpec, ProtocolMailboxAdapter, ProtocolOAuthAdapter, RegistrationCapability, RegistrationResult
from core.registration.helpers import resolve_timeout
from core.registry import register
from platforms.cursor.core import UA, CURSOR


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return value
    return f"{value[:6]}...{value[-4:]}"


@register
class CursorPlatform(BasePlatform):
    name = "cursor"
    display_name = "Cursor"
    version = "1.0.0"
    supported_executors = ["protocol", "headless", "headed"]
    supported_identity_modes = ["mailbox"]
    protocol_captcha_order = ("2captcha", "capsolver", "auto")

    # Declarative capabilities
    capabilities = [
        "switch_desktop",   # Switch to desktop app
        "query_state",      # Query account state/quota
        "generate_link",    # Generate trial link
    ]

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def _prepare_registration_password(self, password: str | None) -> str | None:
        return password

    def _map_mailbox_result(self, result: dict) -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password=result.get("password", ""),
            token=result.get("token", ""),
            status=AccountStatus.REGISTERED,
        )

    def _map_oauth_result(self, result: dict) -> RegistrationResult:
        return RegistrationResult(
            email=result["email"],
            password="",
            token=result.get("token", ""),
            status=AccountStatus.REGISTERED,
            extra={"user_info": result.get("user_info", {})},
        )

    def _run_browser_oauth(self, ctx) -> dict:
        from platforms.cursor.browser_oauth import register_with_browser_oauth

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
            result_mapper=lambda ctx, result: self._map_oauth_result(result) if ctx.identity.identity_provider == "oauth_browser" else self._map_mailbox_result(result),
            browser_worker_builder=lambda ctx, artifacts: __import__("platforms.cursor.browser_register", fromlist=["CursorBrowserRegister"]).CursorBrowserRegister(
                captcha=artifacts.captcha_solver,
                headless=(ctx.executor_type == "headless"),
                proxy=ctx.proxy,
                otp_callback=artifacts.otp_callback,
                phone_callback=artifacts.phone_callback,
                log_fn=ctx.log,
            ),
            browser_register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password or "",
            ),
            oauth_runner=self._run_browser_oauth,
            capability=RegistrationCapability(oauth_headless_requires_browser_reuse=True),
            otp_spec=OtpSpec(wait_message="等待 Cursor 邮箱验证码...", success_label="验证码"),
            use_captcha_for_mailbox=True,
        )

    def build_protocol_oauth_adapter(self):
        return ProtocolOAuthAdapter(
            oauth_runner=self._run_browser_oauth,
            result_mapper=lambda ctx, result: self._map_oauth_result(result),
        )

    def build_protocol_mailbox_adapter(self):
        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: self._map_mailbox_result(result),
            worker_builder=lambda ctx, artifacts: __import__("platforms.cursor.protocol_mailbox", fromlist=["CursorProtocolMailboxWorker"]).CursorProtocolMailboxWorker(
                proxy=ctx.proxy,
                log_fn=ctx.log,
                extra={**dict(ctx.extra or {}), "cursor_diag_mode": (ctx.extra or {}).get("cursor_diag_mode", True)},
            ),
            register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password,
                otp_callback=artifacts.otp_callback,
                captcha_solver=artifacts.captcha_solver,
                phone_callback=artifacts.phone_callback,
            ),
            otp_spec=OtpSpec(wait_message="等待验证码..."),
            use_captcha=True,
        )

    def check_valid(self, account: Account) -> bool:
        from curl_cffi import requests as curl_req
        try:
            r = curl_req.get(
                f"{CURSOR}/api/auth/me",
                headers={"Cookie": f"WorkosCursorSessionToken={account.token}",
                         "user-agent": UA},
                impersonate="chrome124", timeout=15,
            )
            return r.status_code == 200
        except Exception:
            return False

    def get_platform_actions(self) -> list:
        """返回平台支持的操作列表"""
        return [
            {"id": "switch_account", "label": "切换到桌面应用", "params": []},
            {"id": "get_account_state", "label": "查询账号状态/额度提示", "params": []},
            {"id": "generate_trial_link", "label": "生成 7 天 Pro 链接", "params": []},
        ]

    def get_desktop_state(self) -> dict:
        from platforms.cursor.switch import get_cursor_desktop_state

        return get_cursor_desktop_state()

    def execute_action(self, action_id: str, account: Account, params: dict) -> dict:
        """执行平台操作"""
        if action_id == "switch_account":
            from platforms.cursor.switch import (
                get_cursor_billing_info,
                get_cursor_usage,
                get_cursor_user_info,
                has_cursor_valid_payment_method,
                read_current_cursor_account,
                restart_cursor_ide,
                summarize_cursor_usage,
                switch_cursor_account,
                get_cursor_desktop_state,
            )
            
            token = account.token
            if not token:
                return {"ok": False, "error": "账号缺少 token"}
            
            ok, msg = switch_cursor_account(token)
            if not ok:
                return {"ok": False, "error": msg}
            
            user_info = get_cursor_user_info(token) or {}
            billing_info = get_cursor_billing_info(token) or {}
            has_payment_method = has_cursor_valid_payment_method(token)
            usage_info = get_cursor_usage(token, user_info.get("sub", "")) or {}
            usage_summary = summarize_cursor_usage(usage_info)
            current = read_current_cursor_account() or {}
            restart_ok, restart_msg = restart_cursor_ide()
            return {
                "ok": True,
                "data": {
                    "message": f"{msg}。{restart_msg}" if restart_ok else msg,
                    "valid": bool(user_info),
                    "remote_user": user_info,
                    "billing_info": billing_info,
                    "has_valid_payment_method": has_payment_method,
                    "usage_info": usage_info,
                    "usage_summary": usage_summary,
                    "local_app_account": {
                        "token_preview": _mask_secret(current.get("token", "")),
                        "matches_target": current.get("token") == token if current.get("token") else False,
                    },
                    "desktop_app_state": get_cursor_desktop_state(),
                    "restart": {"ok": restart_ok, "message": restart_msg},
                    "quota_note": "Cursor 可查询 usage，但部分账号只返回已用量；maxRequestUsage/maxTokenUsage 可能为空，无法保证总能计算剩余额度。",
                }
            }
        
        elif action_id in {"get_user_info", "get_account_state"}:
            from platforms.cursor.switch import (
                get_cursor_billing_info,
                get_cursor_usage,
                get_cursor_user_info,
                has_cursor_valid_payment_method,
                read_current_cursor_account,
                summarize_cursor_usage,
                get_cursor_desktop_state,
            )
            
            token = account.token
            if not token:
                return {"ok": False, "error": "账号缺少 token"}
            
            user_info = get_cursor_user_info(token)
            if user_info:
                billing_info = get_cursor_billing_info(token) or {}
                has_payment_method = has_cursor_valid_payment_method(token)
                usage_info = get_cursor_usage(token, user_info.get("sub", "")) or {}
                usage_summary = summarize_cursor_usage(usage_info)
                current = read_current_cursor_account() or {}
                return {
                    "ok": True,
                    "data": {
                        "valid": True,
                        "remote_user": user_info,
                        "billing_info": billing_info,
                        "has_valid_payment_method": has_payment_method,
                        "trial_eligible": billing_info.get("trialEligible"),
                        "trial_length_days": billing_info.get("trialLengthDays"),
                        "membership_type": billing_info.get("membershipType") or billing_info.get("individualMembershipType", ""),
                        "usage_info": usage_info,
                        "usage_summary": usage_summary,
                        "local_app_account": {
                            "token_preview": _mask_secret(current.get("token", "")),
                            "matches_target": current.get("token") == token if current.get("token") else False,
                        },
                        "desktop_app_state": get_cursor_desktop_state(),
                        "quota_note": "Cursor 可查询 usage，但部分账号只返回已用量；maxRequestUsage/maxTokenUsage 可能为空，无法保证总能计算剩余额度。",
                    },
                }
            return {"ok": False, "error": "获取用户信息失败"}

        elif action_id == "generate_trial_link":
            from platforms.cursor.switch import generate_cursor_checkout_link, get_cursor_billing_info

            token = account.token
            if not token:
                return {"ok": False, "error": "账号缺少 token"}

            billing_info = get_cursor_billing_info(token) or {}
            checkout_url = generate_cursor_checkout_link(
                token,
                tier="pro",
                allow_trial=True,
                allow_automatic_payment=False,
                yearly=False,
            )
            if not checkout_url:
                return {"ok": False, "error": "生成 7 天 Pro 链接失败"}
            return {
                "ok": True,
                "data": {
                    "url": checkout_url,
                    "message": "7 天 Cursor Pro 试用链接已生成",
                    "billing_info": billing_info,
                    "trial_eligible": billing_info.get("trialEligible"),
                    "trial_length_days": billing_info.get("trialLengthDays"),
                },
            }
        
        raise NotImplementedError(f"未知操作: {action_id}")
