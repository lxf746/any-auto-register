"""
注册流程引擎
从 main.py 中提取并重构的注册流程
"""

from __future__ import annotations

import re
import json
import time
import logging
import secrets
import string
from typing import Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

from curl_cffi import requests as cffi_requests

from .oauth import OAuthManager, OAuthStart
from .http_client import OpenAIHTTPClient, HTTPClientError
# from ..services import EmailServiceFactory, BaseEmailService, EmailServiceType  # removed: external dep
# from ..database import crud  # removed: external dep
# from ..database.session import get_db  # removed: external dep
from .constants import (
    OPENAI_API_ENDPOINTS,
    OPENAI_PAGE_TYPES,
    generate_random_user_info,
    OTP_CODE_PATTERN,
    DEFAULT_PASSWORD_LENGTH,
    PASSWORD_CHARSET,
    AccountStatus,
    TaskStatus,
)
# from ..config.settings import get_settings  # removed: external dep


logger = logging.getLogger(__name__)

SESSION_API_URL = "https://chatgpt.com/api/auth/session"
ME_API_URL = "https://chatgpt.com/backend-api/me"
PASSWORDLESS_SEND_OTP_URL = "https://auth.openai.com/api/accounts/passwordless/send-otp"


@dataclass
class RegistrationResult:
    """注册结果"""
    success: bool
    email: str = ""
    password: str = ""  # 注册密码
    account_id: str = ""
    workspace_id: str = ""
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""
    session_token: str = ""  # 会话令牌
    error_message: str = ""
    logs: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source: str = "register"  # 'register' 或 'login'，区分账号来源

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "email": self.email,
            "password": self.password,
            "account_id": self.account_id,
            "workspace_id": self.workspace_id,
            "access_token": self.access_token[:20] + "..." if self.access_token else "",
            "refresh_token": self.refresh_token[:20] + "..." if self.refresh_token else "",
            "id_token": self.id_token[:20] + "..." if self.id_token else "",
            "session_token": self.session_token[:20] + "..." if self.session_token else "",
            "error_message": self.error_message,
            "logs": self.logs or [],
            "metadata": self.metadata or {},
            "source": self.source,
        }


@dataclass
class SignupFormResult:
    """提交注册表单的结果"""
    success: bool
    page_type: str = ""  # 响应中的 page.type 字段
    is_existing_account: bool = False  # 是否为已注册账号
    response_data: Optional[Dict[str, Any]] = None  # 完整的响应数据
    error_message: str = ""


class RegistrationEngine:
    """
    注册引擎
    负责协调邮箱服务、OAuth 流程和 OpenAI API 调用
    """

    def __init__(
        self,
        email_service: Any,
        proxy_url: Optional[str] = None,
        callback_logger: Optional[Callable[[str], None]] = None,
        task_uuid: Optional[str] = None
    ):
        """
        初始化注册引擎

        Args:
            email_service: 邮箱服务实例
            proxy_url: 代理 URL
            callback_logger: 日志回调函数
            task_uuid: 任务 UUID（用于数据库记录）
        """
        self.email_service = email_service
        self.proxy_url = proxy_url
        self.callback_logger = callback_logger or (lambda msg: logger.info(msg))
        self.task_uuid = task_uuid

        # 创建 HTTP 客户端
        self.http_client = OpenAIHTTPClient(proxy_url=proxy_url)

        # 创建 OAuth 管理器
        from .constants import OAUTH_CLIENT_ID, OAUTH_AUTH_URL, OAUTH_TOKEN_URL, OAUTH_REDIRECT_URI, OAUTH_SCOPE
        self.oauth_manager = OAuthManager(
            client_id=OAUTH_CLIENT_ID,
            auth_url=OAUTH_AUTH_URL,
            token_url=OAUTH_TOKEN_URL,
            redirect_uri=OAUTH_REDIRECT_URI,
            scope=OAUTH_SCOPE,
            proxy_url=proxy_url  # 传递代理配置
        )

        # 状态变量
        self.email: Optional[str] = None
        self.password: Optional[str] = None  # 注册密码
        self.email_info: Optional[Dict[str, Any]] = None
        self.oauth_start: Optional[OAuthStart] = None
        self.session: Optional[cffi_requests.Session] = None
        self.session_token: Optional[str] = None  # 会话令牌
        self.logs: list = []
        self._otp_sent_at: Optional[float] = None  # OTP 发送时间戳
        self._is_existing_account: bool = False  # 是否为已注册账号（用于自动登录）
        self._login_requires_email_otp: bool = False

    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # 添加到日志列表
        self.logs.append(log_message)

        # 调用回调函数
        if self.callback_logger:
            self.callback_logger(log_message)

        # 记录到数据库（如果有关联任务）
        if self.task_uuid and "get_db" in globals() and "crud" in globals():
            try:
                with globals()["get_db"]() as db:
                    globals()["crud"].append_task_log(db, self.task_uuid, log_message)
            except Exception as e:
                logger.warning(f"记录任务日志失败: {e}")

        # 根据级别记录到日志系统
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    def _generate_password(self, length: int = DEFAULT_PASSWORD_LENGTH) -> str:
        """生成随机密码"""
        return ''.join(secrets.choice(PASSWORD_CHARSET) for _ in range(length))

    def _check_ip_location(self) -> Tuple[bool, Optional[str]]:
        """检查 IP 地理位置"""
        try:
            return self.http_client.check_ip_location()
        except Exception as e:
            self._log(f"检查 IP 地理位置失败: {e}", "error")
            return False, None

    def _create_email(self) -> bool:
        """创建邮箱"""
        try:
            self._log(f"正在创建 {self.email_service.service_type.value} 邮箱...")
            self.email_info = self.email_service.create_email()

            if not self.email_info or "email" not in self.email_info:
                self._log("创建邮箱失败: 返回信息不完整", "error")
                return False

            self.email = self.email_info["email"]
            self._log(f"成功创建邮箱: {self.email}")
            return True

        except Exception as e:
            self._log(f"创建邮箱失败: {e}", "error")
            return False

    def _start_oauth(self) -> bool:
        """开始 OAuth 流程"""
        try:
            self._log("开始 OAuth 授权流程...")
            self.oauth_start = self.oauth_manager.start_oauth()
            self._log(f"OAuth URL 已生成: {self.oauth_start.auth_url[:80]}...")
            return True
        except Exception as e:
            self._log(f"生成 OAuth URL 失败: {e}", "error")
            return False

    def _init_session(self) -> bool:
        """初始化会话"""
        try:
            self.session = self.http_client.session
            return True
        except Exception as e:
            self._log(f"初始化会话失败: {e}", "error")
            return False

    def _get_device_id(self) -> Optional[str]:
        """获取 Device ID"""
        try:
            if not self.oauth_start:
                return None

            response = self.http_client.session.get(
                self.oauth_start.auth_url,
                timeout=15
            )
            did = self.http_client.session.cookies.get("oai-did")
            self._log(f"Device ID: {did}")
            return did

        except Exception as e:
            self._log(f"获取 Device ID 失败: {e}", "error")
            return None

    def _check_sentinel(self, did: str) -> Optional[str]:
        """检查 Sentinel 拦截"""
        try:
            sen_req_body = f'{{"p":"","id":"{did}","flow":"authorize_continue"}}'

            response = self.http_client.post(
                OPENAI_API_ENDPOINTS["sentinel"],
                headers={
                    "origin": "https://sentinel.openai.com",
                    "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                    "content-type": "text/plain;charset=UTF-8",
                },
                data=sen_req_body,
            )

            if response.status_code == 200:
                sen_token = response.json().get("token")
                self._log(f"Sentinel token 获取成功")
                return sen_token
            else:
                self._log(f"Sentinel 检查失败: {response.status_code}", "warning")
                return None

        except Exception as e:
            self._log(f"Sentinel 检查异常: {e}", "warning")
            return None

    def _submit_account_flow_form(
        self,
        did: str,
        sen_token: Optional[str],
        screen_hint: str = "signup",
    ) -> SignupFormResult:
        """
        提交账号流程表单

        Returns:
            SignupFormResult: 提交结果，包含账号状态判断
        """
        try:
            referer = "https://auth.openai.com/create-account"
            if screen_hint == "login":
                referer = "https://auth.openai.com/log-in"

            signup_body = json.dumps({
                "username": {"value": self.email, "kind": "email"},
                "screen_hint": screen_hint,
            })

            headers = {
                "referer": referer,
                "accept": "application/json",
                "content-type": "application/json",
            }

            if sen_token:
                sentinel = f'{{"p": "", "t": "", "c": "{sen_token}", "id": "{did}", "flow": "authorize_continue"}}'
                headers["openai-sentinel-token"] = sentinel

            response = self.http_client.session.post(
                OPENAI_API_ENDPOINTS["signup"],
                headers=headers,
                data=signup_body,
            )

            action_label = "登录" if screen_hint == "login" else "注册"
            self._log(f"提交{action_label}表单状态: {response.status_code}")

            if response.status_code != 200:
                return SignupFormResult(
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                )

            # 解析响应判断账号状态
            try:
                response_data = response.json()
                page_type = response_data.get("page", {}).get("type", "")
                self._log(f"响应页面类型: {page_type}")

                # 判断是否为已注册账号
                is_existing = page_type == OPENAI_PAGE_TYPES["EMAIL_OTP_VERIFICATION"]

                if is_existing:
                    self._log(f"检测到已注册账号，将自动切换到登录流程")
                    self._is_existing_account = True

                return SignupFormResult(
                    success=True,
                    page_type=page_type,
                    is_existing_account=is_existing,
                    response_data=response_data
                )

            except Exception as parse_error:
                self._log(f"解析响应失败: {parse_error}", "warning")
                # 无法解析，默认成功
                return SignupFormResult(success=True)

        except Exception as e:
            action_label = "登录" if screen_hint == "login" else "注册"
            self._log(f"提交{action_label}表单失败: {e}", "error")
            return SignupFormResult(success=False, error_message=str(e))

    def _submit_signup_form(self, did: str, sen_token: Optional[str]) -> SignupFormResult:
        return self._submit_account_flow_form(did, sen_token, screen_hint="signup")

    def _submit_login_form(self, did: str, sen_token: Optional[str]) -> SignupFormResult:
        return self._submit_account_flow_form(did, sen_token, screen_hint="login")

    def _register_password(self) -> Tuple[bool, Optional[str]]:
        """注册密码"""
        try:
            # 生成密码
            password = self._generate_password()
            self.password = password  # 保存密码到实例变量
            self._log(f"生成密码: {password}")

            # 提交密码注册
            register_body = json.dumps({
                "password": password,
                "username": self.email
            })

            response = self.http_client.session.post(
                OPENAI_API_ENDPOINTS["register"],
                headers={
                    "referer": "https://auth.openai.com/create-account/password",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=register_body,
            )

            self._log(f"提交密码状态: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text[:500]
                self._log(f"密码注册失败: {error_text}", "warning")

                # 解析错误信息，判断是否是邮箱已注册
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", "")
                    error_code = error_json.get("error", {}).get("code", "")

                    # 检测邮箱已注册的情况
                    if "already" in error_msg.lower() or "exists" in error_msg.lower() or error_code == "user_exists":
                        self._log(f"邮箱 {self.email} 可能已在 OpenAI 注册过", "error")
                        # 标记此邮箱为已注册状态
                        self._mark_email_as_registered()
                except Exception:
                    pass

                return False, None

            return True, password

        except Exception as e:
            self._log(f"密码注册失败: {e}", "error")
            return False, None

    def _mark_email_as_registered(self):
        """标记邮箱为已注册状态（用于防止重复尝试）"""
        if "get_db" not in globals() or "crud" not in globals():
            return
        try:
            with globals()["get_db"]() as db:
                # 检查是否已存在该邮箱的记录
                existing = globals()["crud"].get_account_by_email(db, self.email)
                if not existing:
                    # 创建一个失败记录，标记该邮箱已注册过
                    globals()["crud"].create_account(
                        db,
                        email=self.email,
                        password="",  # 空密码表示未成功注册
                        email_service=self.email_service.service_type.value,
                        email_service_id=self.email_info.get("service_id") if self.email_info else None,
                        status="failed",
                        extra_data={"register_failed_reason": "email_already_registered_on_openai"}
                    )
                    self._log(f"已在数据库中标记邮箱 {self.email} 为已注册状态")
        except Exception as e:
            logger.warning(f"标记邮箱状态失败: {e}")

    def _send_verification_code(self) -> bool:
        """发送验证码"""
        try:
            # 记录发送时间戳
            self._otp_sent_at = time.time()

            response = self.http_client.session.get(
                OPENAI_API_ENDPOINTS["send_otp"],
                headers={
                    "referer": "https://auth.openai.com/create-account/password",
                    "accept": "application/json",
                },
            )

            self._log(f"验证码发送状态: {response.status_code}")
            return response.status_code == 200

        except Exception as e:
            self._log(f"发送验证码失败: {e}", "error")
            return False

    def _get_verification_code(self) -> Optional[str]:
        """获取验证码"""
        try:
            self._log(f"正在等待邮箱 {self.email} 的验证码...")

            email_id = self.email_info.get("service_id") if self.email_info else None
            code = self.email_service.get_verification_code(
                email=self.email,
                email_id=email_id,
                timeout=120,
                pattern=OTP_CODE_PATTERN,
                otp_sent_at=self._otp_sent_at,
            )

            if code:
                self._log(f"成功获取验证码: {code}")
                return code
            else:
                self._log("等待验证码超时", "error")
                return None

        except Exception as e:
            self._log(f"获取验证码失败: {e}", "error")
            return None

    def _validate_verification_code(self, code: str) -> bool:
        """验证验证码"""
        try:
            code_body = f'{{"code":"{code}"}}'

            response = self.http_client.session.post(
                OPENAI_API_ENDPOINTS["validate_otp"],
                headers={
                    "referer": "https://auth.openai.com/email-verification",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=code_body,
            )

            self._log(f"验证码校验状态: {response.status_code}")
            return response.status_code == 200

        except Exception as e:
            self._log(f"验证验证码失败: {e}", "error")
            return False

    def _create_user_account(self) -> bool:
        """创建用户账户"""
        try:
            user_info = generate_random_user_info()
            self._log(f"生成用户信息: {user_info['name']}, 生日: {user_info['birthdate']}")
            create_account_body = json.dumps(user_info)

            response = self.http_client.session.post(
                OPENAI_API_ENDPOINTS["create_account"],
                headers={
                    "referer": "https://auth.openai.com/about-you",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=create_account_body,
            )

            self._log(f"账户创建状态: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text[:500]
                self._log(f"账户创建失败: {error_text}", "warning")

                recoverable_codes = {"registration_disallowed"}
                recoverable_messages = (
                    "cannot create your account with the given information",
                )
                try:
                    error_json = response.json()
                    error_obj = error_json.get("error", {}) if isinstance(error_json, dict) else {}
                    error_code = str(error_obj.get("code") or "").strip().lower()
                    error_message = str(error_obj.get("message") or "").strip().lower()
                    if error_code in recoverable_codes or any(msg in error_message for msg in recoverable_messages):
                        self._log(
                            "账户创建返回可恢复错误，继续切换到全新登录会话验证账号是否已落库",
                            "warning",
                        )
                        return True
                except Exception:
                    pass

                return False

            return True

        except Exception as e:
            self._log(f"创建账户失败: {e}", "error")
            return False

    def _reset_auth_session(self):
        """丢弃当前注册阶段的会话与 Cookie，重新创建全新会话。"""
        try:
            self.http_client.close()
        except Exception:
            pass

        self.http_client = OpenAIHTTPClient(proxy_url=self.proxy_url)
        self.session = None
        self.oauth_start = None
        self.session_token = None
        self._otp_sent_at = None
        self._is_existing_account = False
        self._login_requires_email_otp = False

    def _extract_workspace_id_from_payload(self, payload: Any) -> Optional[str]:
        """从不同接口返回结构中提取 workspace/org ID。"""
        if not isinstance(payload, dict):
            return None

        for key in (
            "workspace_id",
            "default_workspace_id",
            "active_workspace_id",
            "workspaceId",
            "defaultWorkspaceId",
            "activeWorkspaceId",
            "id",
        ):
            value = str(payload.get(key) or "").strip()
            if value:
                return value

        workspaces = payload.get("workspaces") or payload.get("workspace") or []
        if isinstance(workspaces, dict):
            workspaces = workspaces.get("data") or workspaces.get("items") or [workspaces]
        if isinstance(workspaces, list):
            for workspace in workspaces:
                workspace_id = self._extract_workspace_id_from_payload(workspace)
                if workspace_id:
                    return workspace_id

        orgs = payload.get("orgs") or payload.get("organizations") or []
        if isinstance(orgs, dict):
            orgs = orgs.get("data") or orgs.get("items") or [orgs]
        if isinstance(orgs, list):
            for org in orgs:
                org_id = self._extract_workspace_id_from_payload(org)
                if org_id:
                    return org_id

        user_info = payload.get("user")
        if isinstance(user_info, dict):
            user_workspace_id = self._extract_workspace_id_from_payload(user_info)
            if user_workspace_id:
                return user_workspace_id

        return None

    def _extract_workspace_id_from_cookie(self, cookie_value: str) -> Optional[str]:
        """尝试从 Cookie 的各个段中解码 JSON 并提取 workspace。"""
        import base64
        import json as json_module

        for segment in cookie_value.split("."):
            raw = (segment or "").strip()
            if not raw:
                continue
            pad = "=" * ((4 - (len(raw) % 4)) % 4)
            try:
                decoded = base64.urlsafe_b64decode((raw + pad).encode("ascii"))
                payload = json_module.loads(decoded.decode("utf-8"))
            except Exception:
                continue
            workspace_id = self._extract_workspace_id_from_payload(payload)
            if workspace_id:
                return workspace_id
        return None

    def _fetch_workspace_id_from_session_api(self) -> Optional[str]:
        """通过新的登录 Cookie 调用 session/me 接口，提取 workspace。"""
        try:
            response = self.http_client.session.get(
                SESSION_API_URL,
                headers={"accept": "application/json"},
                timeout=15,
            )
            self._log(f"会话状态接口: {response.status_code}")
            if response.status_code != 200:
                return None

            session_data = response.json() if response.text else {}
            workspace_id = self._extract_workspace_id_from_payload(session_data)
            if workspace_id:
                return workspace_id

            access_token = str(session_data.get("accessToken") or "").strip()
            session_token = self.http_client.session.cookies.get("__Secure-next-auth.session-token")
            if session_token:
                self.session_token = session_token

            if not access_token:
                return None

            me_response = self.http_client.session.get(
                ME_API_URL,
                headers={
                    "authorization": f"Bearer {access_token}",
                    "accept": "application/json",
                },
                timeout=15,
            )
            self._log(f"用户信息接口: {me_response.status_code}")
            if me_response.status_code != 200:
                return None

            me_data = me_response.json() if me_response.text else {}
            return self._extract_workspace_id_from_payload(me_data)
        except Exception as e:
            self._log(f"通过 session/me 提取 Workspace ID 失败: {e}", "warning")
            return None

    def _send_passwordless_login_code(self) -> bool:
        """在密码登录页切换到一次性验证码登录。"""
        try:
            response = self.http_client.session.post(
                PASSWORDLESS_SEND_OTP_URL,
                headers={
                    "referer": "https://auth.openai.com/log-in/password",
                    "accept": "application/json",
                },
                timeout=15,
            )
            self._log(f"密码页发送登录验证码状态: {response.status_code}")

            if response.status_code != 200:
                self._log(f"密码页发送登录验证码失败: {response.text[:200]}", "warning")
                return False

            page_type = ""
            try:
                response_data = response.json() if response.text else {}
                page_type = str((response_data.get("page") or {}).get("type") or "").strip()
                if page_type:
                    self._log(f"密码页验证码响应页面类型: {page_type}")
            except Exception:
                pass

            self._otp_sent_at = time.time()
            return True

        except Exception as e:
            self._log(f"密码页发送登录验证码异常: {e}", "warning")
            return False

    def _submit_login_password(self) -> SignupFormResult:
        """在登录页提交密码，进入后续验证码或授权流程。"""
        try:
            if not self.password:
                return SignupFormResult(success=False, error_message="缺少登录密码")

            response = self.http_client.session.post(
                "https://auth.openai.com/api/accounts/password/verify",
                headers={
                    "referer": "https://auth.openai.com/log-in/password",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=json.dumps({"password": self.password}),
            )

            self._log(f"提交登录密码状态: {response.status_code}")

            if response.status_code != 200:
                return SignupFormResult(
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                )

            try:
                response_data = response.json()
                page_type = str((response_data.get("page") or {}).get("type") or "").strip()
                self._log(f"密码登录后页面类型: {page_type}")
                return SignupFormResult(
                    success=True,
                    page_type=page_type,
                    is_existing_account=page_type == OPENAI_PAGE_TYPES["EMAIL_OTP_VERIFICATION"],
                    response_data=response_data,
                )
            except Exception as parse_error:
                self._log(f"解析密码登录响应失败: {parse_error}", "warning")
                return SignupFormResult(success=True)

        except Exception as e:
            self._log(f"提交登录密码失败: {e}", "error")
            return SignupFormResult(success=False, error_message=str(e))

    def _restart_with_fresh_login_session(self) -> bool:
        """注册完成后丢弃注册态 session，使用全新会话重新进入 OTP 登录流程。"""
        for attempt in range(1, 4):
            self._log(f"切换到全新登录会话，第 {attempt}/3 次尝试...")
            self._reset_auth_session()

            if not self._init_session():
                continue
            if not self._start_oauth():
                continue

            did = self._get_device_id()
            if not did:
                continue

            sen_token = self._check_sentinel(did)
            if sen_token:
                self._log("新会话 Sentinel 检查通过")
            else:
                self._log("新会话 Sentinel 检查失败或未启用", "warning")

            signup_result = self._submit_login_form(did, sen_token)
            if not signup_result.success:
                self._log(f"新会话提交登录表单失败: {signup_result.error_message}", "warning")
                time.sleep(attempt)
                continue

            if signup_result.is_existing_account:
                self._login_requires_email_otp = True
                self._otp_sent_at = time.time()
                self._log("新会话已进入验证码登录页")
                return True

            if signup_result.page_type == "login_password":
                self._log("新会话进入密码登录页，提交密码继续登录...")
                password_result = self._submit_login_password()
                if not password_result.success:
                    self._log(f"新会话提交登录密码失败: {password_result.error_message}", "warning")
                    time.sleep(attempt)
                    continue

                if password_result.page_type == OPENAI_PAGE_TYPES["EMAIL_OTP_VERIFICATION"]:
                    self._login_requires_email_otp = True
                    self._otp_sent_at = time.time()
                    self._log("密码登录成功，已进入邮箱验证码页")
                    return True

                if password_result.page_type and password_result.page_type != "login_password":
                    self._login_requires_email_otp = False
                    self._log(f"密码登录成功，进入后续页面: {password_result.page_type}")
                    return True

            self._log(
                f"新会话尚未进入验证码登录页，页面类型: {signup_result.page_type or '<empty>'}",
                "warning",
            )
            time.sleep(attempt)

        self._log("切换到全新登录会话失败", "error")
        return False

    def _get_workspace_id(self) -> Optional[str]:
        """获取 Workspace ID"""
        try:
            auth_cookie = self.http_client.session.cookies.get("oai-client-auth-session")
            if auth_cookie:
                workspace_id = self._extract_workspace_id_from_cookie(auth_cookie)
                if workspace_id:
                    self._log(f"Workspace ID: {workspace_id}")
                    return workspace_id
                self._log("授权 Cookie 里没有 workspace 信息，尝试 session/me 回退", "warning")
            else:
                self._log("未能获取到授权 Cookie，尝试 session/me 回退", "warning")

            workspace_id = self._fetch_workspace_id_from_session_api()
            if workspace_id:
                self._log(f"Workspace ID: {workspace_id}")
                return workspace_id

            self._log("无法提取 Workspace ID", "error")
            return None

        except Exception as e:
            self._log(f"获取 Workspace ID 失败: {e}", "error")
            return None

    def _select_workspace(self, workspace_id: str) -> Optional[str]:
        """选择 Workspace"""
        try:
            select_body = f'{{"workspace_id":"{workspace_id}"}}'

            response = self.http_client.session.post(
                OPENAI_API_ENDPOINTS["select_workspace"],
                headers={
                    "referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
                    "content-type": "application/json",
                },
                data=select_body,
            )

            if response.status_code != 200:
                self._log(f"选择 workspace 失败: {response.status_code}", "error")
                self._log(f"响应: {response.text[:200]}", "warning")
                return None

            continue_url = str((response.json() or {}).get("continue_url") or "").strip()
            if not continue_url:
                self._log("workspace/select 响应里缺少 continue_url", "error")
                return None

            self._log(f"Continue URL: {continue_url[:100]}...")
            return continue_url

        except Exception as e:
            self._log(f"选择 Workspace 失败: {e}", "error")
            return None

    def _follow_redirects(self, start_url: str) -> Optional[str]:
        """跟随重定向链，寻找回调 URL"""
        try:
            current_url = start_url
            max_redirects = 6

            for i in range(max_redirects):
                self._log(f"重定向 {i+1}/{max_redirects}: {current_url[:100]}...")

                response = self.http_client.session.get(
                    current_url,
                    allow_redirects=False,
                    timeout=15
                )

                location = response.headers.get("Location") or ""

                # 如果不是重定向状态码，停止
                if response.status_code not in [301, 302, 303, 307, 308]:
                    self._log(f"非重定向状态码: {response.status_code}")
                    break

                if not location:
                    self._log("重定向响应缺少 Location 头")
                    break

                # 构建下一个 URL
                import urllib.parse
                next_url = urllib.parse.urljoin(current_url, location)

                # 检查是否包含回调参数
                if "code=" in next_url and "state=" in next_url:
                    self._log(f"找到回调 URL: {next_url[:100]}...")
                    return next_url

                current_url = next_url

            self._log("未能在重定向链中找到回调 URL", "error")
            return None

        except Exception as e:
            self._log(f"跟随重定向失败: {e}", "error")
            return None

    def _handle_oauth_callback(self, callback_url: str) -> Optional[Dict[str, Any]]:
        """处理 OAuth 回调"""
        try:
            if not self.oauth_start:
                self._log("OAuth 流程未初始化", "error")
                return None

            self._log("处理 OAuth 回调...")
            token_info = self.oauth_manager.handle_callback(
                callback_url=callback_url,
                expected_state=self.oauth_start.state,
                code_verifier=self.oauth_start.code_verifier
            )

            self._log("OAuth 授权成功")
            return token_info

        except Exception as e:
            self._log(f"处理 OAuth 回调失败: {e}", "error")
            return None

    def run(self) -> RegistrationResult:
        """
        执行完整的注册流程

        支持已注册账号自动登录：
        - 如果检测到邮箱已注册，自动切换到登录流程
        - 已注册账号跳过：设置密码、发送验证码、创建用户账户
        - 共用步骤：获取验证码、验证验证码、Workspace 和 OAuth 回调

        Returns:
            RegistrationResult: 注册结果
        """
        result = RegistrationResult(success=False, logs=self.logs)

        try:
            self._log("=" * 60)
            self._log("开始注册流程")
            self._log("=" * 60)
            initial_existing_account = False

            # 1. 检查 IP 地理位置
            self._log("1. 检查 IP 地理位置...")
            ip_ok, location = self._check_ip_location()
            if not ip_ok:
                result.error_message = f"IP 地理位置不支持: {location}"
                self._log(f"IP 检查失败: {location}", "error")
                return result

            self._log(f"IP 位置: {location}")

            # 2. 创建邮箱
            self._log("2. 创建邮箱...")
            if not self._create_email():
                result.error_message = "创建邮箱失败"
                return result

            result.email = self.email or ""

            # 3. 初始化会话
            self._log("3. 初始化会话...")
            if not self._init_session():
                result.error_message = "初始化会话失败"
                return result

            # 4. 开始 OAuth 流程
            self._log("4. 开始 OAuth 授权流程...")
            if not self._start_oauth():
                result.error_message = "开始 OAuth 流程失败"
                return result

            # 5. 获取 Device ID
            self._log("5. 获取 Device ID...")
            did = self._get_device_id()
            if not did:
                result.error_message = "获取 Device ID 失败"
                return result

            # 6. 检查 Sentinel 拦截
            self._log("6. 检查 Sentinel 拦截...")
            sen_token = self._check_sentinel(did)
            if sen_token:
                self._log("Sentinel 检查通过")
            else:
                self._log("Sentinel 检查失败或未启用", "warning")

            # 7. 提交注册表单 + 解析响应判断账号状态
            self._log("7. 提交注册表单...")
            signup_result = self._submit_signup_form(did, sen_token)
            if not signup_result.success:
                result.error_message = f"提交注册表单失败: {signup_result.error_message}"
                return result

            initial_existing_account = self._is_existing_account

            # 8. [已注册账号跳过] 注册密码
            if self._is_existing_account:
                self._log("8. [已注册账号] 跳过密码设置，OTP 已自动发送")
            else:
                self._log("8. 注册密码...")
                password_ok, password = self._register_password()
                if not password_ok:
                    result.error_message = "注册密码失败"
                    return result

            # 9. [已注册账号跳过] 发送验证码
            if self._is_existing_account:
                self._log("9. [已注册账号] 跳过发送验证码，使用自动发送的 OTP")
                # 已注册账号的 OTP 在提交表单时已自动发送，记录时间戳
                self._otp_sent_at = time.time()
            else:
                self._log("9. 发送验证码...")
                if not self._send_verification_code():
                    result.error_message = "发送验证码失败"
                    return result

            # 10. 获取验证码
            self._log("10. 等待验证码...")
            code = self._get_verification_code()
            if not code:
                result.error_message = "获取验证码失败"
                return result

            # 11. 验证验证码
            self._log("11. 验证验证码...")
            if not self._validate_verification_code(code):
                result.error_message = "验证验证码失败"
                return result

            # 12. [已注册账号跳过] 创建用户账户
            if self._is_existing_account:
                self._log("12. [已注册账号] 跳过创建用户账户")
            else:
                self._log("12. 创建用户账户...")
                if not self._create_user_account():
                    result.error_message = "创建用户账户失败"
                    return result

                self._log("13. 切换全新会话，进入验证码登录流程...")
                if not self._restart_with_fresh_login_session():
                    result.error_message = "切换全新登录会话失败"
                    return result

                if self._login_requires_email_otp:
                    self._log("14. 等待登录邮箱验证码...")
                    code = self._get_verification_code()
                    if not code:
                        result.error_message = "获取登录验证码失败"
                        return result

                    self._log("15. 验证登录邮箱验证码...")
                    if not self._validate_verification_code(code):
                        result.error_message = "验证登录验证码失败"
                        return result
                else:
                    self._log("14. 登录后无需邮箱验证码，直接继续...")

            # 16. 获取 Workspace ID
            self._log("16. 获取 Workspace ID...")
            workspace_id = self._get_workspace_id()
            if not workspace_id:
                result.error_message = "获取 Workspace ID 失败"
                return result

            result.workspace_id = workspace_id

            # 17. 选择 Workspace
            self._log("17. 选择 Workspace...")
            continue_url = self._select_workspace(workspace_id)
            if not continue_url:
                result.error_message = "选择 Workspace 失败"
                return result

            # 18. 跟随重定向链
            self._log("18. 跟随重定向链...")
            callback_url = self._follow_redirects(continue_url)
            if not callback_url:
                result.error_message = "跟随重定向链失败"
                return result

            # 19. 处理 OAuth 回调
            self._log("19. 处理 OAuth 回调...")
            token_info = self._handle_oauth_callback(callback_url)
            if not token_info:
                result.error_message = "处理 OAuth 回调失败"
                return result

            # 提取账户信息
            result.account_id = token_info.get("account_id", "")
            result.access_token = token_info.get("access_token", "")
            result.refresh_token = token_info.get("refresh_token", "")
            result.id_token = token_info.get("id_token", "")
            result.password = self.password or ""  # 保存密码（已注册账号为空）

            # 设置来源标记
            result.source = "login" if initial_existing_account else "register"

            # 尝试获取 session_token 从 cookie
            session_cookie = self.http_client.session.cookies.get("__Secure-next-auth.session-token")
            if session_cookie:
                self.session_token = session_cookie
                result.session_token = session_cookie
                self._log(f"获取到 Session Token")

            # 17. 完成
            self._log("=" * 60)
            if initial_existing_account:
                self._log("登录成功! (已注册账号)")
            else:
                self._log("注册成功!")
            self._log(f"邮箱: {result.email}")
            self._log(f"Account ID: {result.account_id}")
            self._log(f"Workspace ID: {result.workspace_id}")
            self._log("=" * 60)

            result.success = True
            result.metadata = {
                "email_service": self.email_service.service_type.value,
                "proxy_used": self.proxy_url,
                "registered_at": datetime.now().isoformat(),
                "is_existing_account": initial_existing_account,
            }

            return result

        except Exception as e:
            self._log(f"注册过程中发生未预期错误: {e}", "error")
            result.error_message = str(e)
            return result

    def save_to_database(self, result: RegistrationResult) -> bool:
        """
        保存注册结果到数据库

        Args:
            result: 注册结果

        Returns:
            是否保存成功
        """
        if not result.success:
            return False

        return True  # 由 account_manager 统一处理存库
