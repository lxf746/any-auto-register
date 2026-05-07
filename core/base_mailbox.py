"""邮箱池基类 - 抽象临时邮箱/收件服务"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import html
import logging
import re
from urllib.parse import urlencode, urlparse

logger = logging.getLogger(__name__)

from core.tls import insecure_request, mark_session_insecure, suppress_insecure_request_warning

# ── 邮箱服务默认 API 地址（统一维护，需要时在此修改） ──
DEFAULT_LAOUDO_API_URL = "https://laoudo.com/api/email"
DEFAULT_AITRE_API_URL = "https://mail.aitre.cc/api/tempmail"
DEFAULT_TEMPMAIL_LOL_API_URL = "https://api.tempmail.lol/v2"
DEFAULT_TEMPMAIL_WEB_BASE_URL = "https://web2.temp-mail.org"


@dataclass
class MailboxAccount:
    email: str
    account_id: str = ""
    extra: dict = None  # 平台额外信息


class BaseMailbox(ABC):
    @abstractmethod
    def get_email(self) -> MailboxAccount:
        """获取一个可用邮箱"""
        ...

    @abstractmethod
    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        """等待并返回验证码，code_pattern 为自定义正则（默认匹配6位数字）"""
        ...

    @abstractmethod
    def get_current_ids(self, account: MailboxAccount) -> set:
        """返回当前邮件 ID 集合（用于过滤旧邮件）"""
        ...

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        """等待并返回验证链接。默认由具体 provider 自行实现。"""
        raise NotImplementedError(f"{self.__class__.__name__} 暂不支持 wait_for_link()")


class FallbackMailbox(BaseMailbox):
    """按顺序尝试多个 provider，创建邮箱成功后固定使用同一 provider 收件。"""

    def __init__(self, providers: list[tuple[str, 'BaseMailbox']]):
        self.providers = [(str(key or "").strip(), mailbox) for key, mailbox in providers if str(key or "").strip() and mailbox]
        self._accounts: dict[str, BaseMailbox] = {}

    @staticmethod
    def _inject_provider_metadata(account: MailboxAccount, provider_key: str) -> MailboxAccount:
        account.extra = dict(account.extra or {})
        account.extra["mailbox_provider_key"] = provider_key
        provider_resource = dict((account.extra.get("provider_resource") or {}))
        if provider_resource and not provider_resource.get("provider_name"):
            provider_resource["provider_name"] = provider_key
            account.extra["provider_resource"] = provider_resource
        return account

    def _resolve_mailbox(self, account: MailboxAccount) -> BaseMailbox:
        provider_key = str((account.extra or {}).get("mailbox_provider_key") or "").strip()
        if provider_key:
            for key, mailbox in self.providers:
                if key == provider_key:
                    return mailbox
        mailbox = self._accounts.get(str(account.email or "").strip())
        if mailbox is not None:
            return mailbox
        raise RuntimeError(f"未找到邮箱 provider 上下文: {account.email}")

    def get_email(self) -> MailboxAccount:
        errors: list[str] = []
        for provider_key, mailbox in self.providers:
            try:
                print(f"[Mailbox] 尝试 provider: {provider_key}")
                account = mailbox.get_email()
                self._accounts[str(account.email or "").strip()] = mailbox
                self._inject_provider_metadata(account, provider_key)
                print(f"[Mailbox] 使用 provider 成功: {provider_key} -> {account.email}")
                return account
            except Exception as exc:
                message = str(exc).strip() or exc.__class__.__name__
                errors.append(f"{provider_key}: {message}")
                print(f"[Mailbox] provider 失败: {provider_key} -> {message}")
                continue
        raise RuntimeError("所有邮箱 provider 均创建失败: " + " | ".join(errors))

    def get_current_ids(self, account: MailboxAccount) -> set:
        return self._resolve_mailbox(account).get_current_ids(account)

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        return self._resolve_mailbox(account).wait_for_code(
            account,
            keyword=keyword,
            timeout=timeout,
            before_ids=before_ids,
            code_pattern=code_pattern,
        )

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        return self._resolve_mailbox(account).wait_for_link(
            account,
            keyword=keyword,
            timeout=timeout,
            before_ids=before_ids,
        )


def _extract_verification_link(text: str, keyword: str = "") -> str | None:
    combined = str(text or "")
    lowered = combined.lower()
    if keyword and keyword.lower() not in lowered:
        return None

    urls = [
        html.unescape(raw).rstrip(").,;")
        for raw in re.findall(r'https?://[^\s<>"\']+', combined, re.IGNORECASE)
    ]
    if not urls:
        return None

    primary_link_hints = ("verif", "confirm", "magic", "auth", "callback", "signin", "signup", "continue")
    primary_host_hints = ("tavily", "firecrawl", "clerk", "stytch", "auth", "login")
    for url in urls:
        url_lower = url.lower()
        if any(token in url_lower for token in primary_link_hints) and any(host in url_lower for host in primary_host_hints):
            return url

    verification_hints = ("verify", "verification", "confirm", "magic link", "sign in", "login", "auth", "tavily", "firecrawl")
    if not any(token in lowered for token in verification_hints):
        return None

    for url in urls:
        url_lower = url.lower()
        if any(token in url_lower for token in primary_link_hints):
            return url

    return urls[0]


def _normalize_api_base_url(value: str | None, *, default: str, label: str) -> str:
    raw = str(value or "").strip() or default
    if "://" not in raw:
        raw = f"https://{raw.lstrip('/')}"
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"{label} 无效: {value!r}")
    return raw.rstrip("/")


def _create_tempmail(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return TempMailLolMailbox(proxy=proxy)


def _create_tempmail_web(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return TempMailWebMailbox(
        base_url=extra.get("tempmail_web_base_url", ""),
        proxy=proxy,
    )


def _create_duckmail(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return DuckMailMailbox(
        api_url=extra.get("duckmail_api_url", ""),
        provider_url=extra.get("duckmail_provider_url", ""),
        bearer=extra.get("duckmail_bearer", ""),
        proxy=proxy,
    )


def _create_ddg_email(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return DDGEmailMailbox(
        bearer=extra.get("ddg_bearer", ""),
        imap_host=extra.get("ddg_imap_host", ""),
        imap_user=extra.get("ddg_imap_user", ""),
        imap_pass=extra.get("ddg_imap_pass", ""),
        proxy=proxy,
    )


def _create_freemail(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return FreemailMailbox(
        api_url=extra.get("freemail_api_url", ""),
        admin_token=extra.get("freemail_admin_token", ""),
        username=extra.get("freemail_username", ""),
        password=extra.get("freemail_password", ""),
        proxy=proxy,
    )


def _create_moemail(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return MoeMailMailbox(
        api_url=extra.get("moemail_api_url"),
        username=extra.get("moemail_username", ""),
        password=extra.get("moemail_password", ""),
        session_token=extra.get("moemail_session_token", ""),
        proxy=proxy,
    )


def _create_cfworker(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return CFWorkerMailbox(
        api_url=extra.get("cfworker_api_url", ""),
        admin_token=extra.get("cfworker_admin_token", ""),
        domain=extra.get("cfworker_domain", ""),
        fingerprint=extra.get("cfworker_fingerprint", ""),
        proxy=proxy,
    )


def _create_testmail(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return TestmailMailbox(
        api_url=extra.get("testmail_api_url", ""),
        api_key=extra.get("testmail_api_key", ""),
        namespace=extra.get("testmail_namespace", ""),
        tag_prefix=extra.get("testmail_tag_prefix", ""),
        proxy=proxy,
    )


def _create_luckmail(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return LuckMailMailbox(
        api_url=extra.get("luckmail_api_url", ""),
        api_key=extra.get("luckmail_api_key", ""),
        project_code=extra.get("luckmail_project_code", ""),
        email_type=extra.get("luckmail_email_type", ""),
        domain=extra.get("luckmail_domain", ""),
        variant_mode=extra.get("luckmail_variant_mode", ""),
        proxy=proxy,
    )


def _create_local_ms_pool(extra: dict, proxy: str | None) -> 'BaseMailbox':
    from core.local_ms_mailbox import LocalMicrosoftMailboxPool

    return LocalMicrosoftMailboxPool(
        pool_text=extra.get("local_ms_pool_text", ""),
        pool_file=extra.get("local_ms_pool_file", ""),
        state_file=extra.get("local_ms_pool_state_file", ""),
        graph_scope=extra.get("local_ms_graph_scope", ""),
        allow_reuse=str(extra.get("local_ms_pool_allow_reuse", "")).strip().lower() in {"1", "true", "yes", "on"},
        proxy=proxy,
    )


def _create_laoudo(extra: dict, proxy: str | None) -> 'BaseMailbox':
    return LaoudoMailbox(
        auth_token=extra.get("laoudo_auth", ""),
        email=extra.get("laoudo_email", ""),
        account_id=extra.get("laoudo_account_id", ""),
    )


def _create_generic_http(extra: dict, proxy: str | None, *, pipeline_config: dict | None = None) -> 'BaseMailbox':
    from core.generic_http_mailbox import GenericHttpMailbox
    return GenericHttpMailbox(
        pipeline_config=pipeline_config or {},
        settings=extra,
        proxy=proxy,
    )


MAILBOX_FACTORY_REGISTRY = {
    "generic_http_mailbox": _create_generic_http,
    "tempmail_lol_api": _create_tempmail,
    "tempmail_web_api": _create_tempmail_web,
    "duckmail_api": _create_duckmail,
    "ddg_email": _create_ddg_email,
    "ddg_email_api": _create_ddg_email,
    "freemail_api": _create_freemail,
    "moemail_api": _create_moemail,
    "cfworker_admin_api": _create_cfworker,
    "testmail_api": _create_testmail,
    "luckmail_api": _create_luckmail,
    "local_ms_pool": _create_local_ms_pool,
    "laoudo_api": _create_laoudo,
    # backward-compat fallback
    "generic_http": _create_generic_http,
    "tempmail_lol": _create_tempmail,
    "tempmail_web": _create_tempmail_web,
    "duckmail": _create_duckmail,
    "freemail": _create_freemail,
    "moemail": _create_moemail,
    "cfworker": _create_cfworker,
    "testmail": _create_testmail,
    "luckmail": _create_luckmail,
    "local_ms": _create_local_ms_pool,
    "laoudo": _create_laoudo,
}


def create_mailbox(provider: str, extra: dict = None, proxy: str = None) -> 'BaseMailbox':
    """工厂方法：根据 provider 创建对应的 mailbox 实例"""
    from infrastructure.provider_definitions_repository import ProviderDefinitionsRepository
    from infrastructure.provider_settings_repository import ProviderSettingsRepository

    definitions_repo = ProviderDefinitionsRepository()
    settings_repo = ProviderSettingsRepository()
    provider_key = str(provider or "").strip()
    if not provider_key:
        raise RuntimeError("未选择邮箱 provider，请先在设置页配置并启用默认邮箱 provider")
    definition = definitions_repo.get_by_key("mailbox", provider_key)
    if not definition or not definition.enabled:
        raise RuntimeError(f"邮箱 provider 不存在或未启用: {provider_key}")
    base_extra = dict(extra or {})

    raw_fallbacks = base_extra.get("mail_provider_fallbacks")
    explicit_fallbacks: list[str] = []
    if isinstance(raw_fallbacks, str):
        explicit_fallbacks = [item.strip() for item in raw_fallbacks.split(",") if item.strip()]
    elif isinstance(raw_fallbacks, (list, tuple, set)):
        explicit_fallbacks = [str(item or "").strip() for item in raw_fallbacks if str(item or "").strip()]

    enabled_items = settings_repo.list_enabled("mailbox")
    enabled_keys = [str(item.provider_key or "").strip() for item in enabled_items if str(item.provider_key or "").strip()]
    ordered_keys: list[str] = [provider_key]
    for key in explicit_fallbacks:
        if key not in ordered_keys:
            ordered_keys.append(key)
    for key in enabled_keys:
        if key == provider_key or key == "laoudo" or key in ordered_keys:
            continue
        ordered_keys.append(key)

    providers: list[tuple[str, BaseMailbox]] = []
    for key in ordered_keys:
        current_definition = definitions_repo.get_by_key("mailbox", key)
        if not current_definition or not current_definition.enabled:
            continue
        resolved_extra = settings_repo.resolve_runtime_settings("mailbox", key, base_extra)
        lookup_key = current_definition.driver_type if current_definition else key
        factory = MAILBOX_FACTORY_REGISTRY.get(lookup_key)
        if not factory:
            continue
        try:
            if lookup_key in ("generic_http_mailbox", "generic_http"):
                pipeline_config = current_definition.get_metadata() if current_definition else {}
                providers.append((key, factory(resolved_extra, proxy, pipeline_config=pipeline_config)))
            else:
                providers.append((key, factory(resolved_extra, proxy)))
        except Exception as exc:
            if key == provider_key:
                raise RuntimeError(f"邮箱 provider {key} 初始化失败: {exc}") from exc
            logger.warning("邮箱 provider %s 初始化失败，已跳过: %s", key, exc)

    if not providers:
        raise RuntimeError("没有可用的邮箱 provider 实例")
    if len(providers) == 1:
        return providers[0][1]
    return FallbackMailbox(providers)


class LaoudoMailbox(BaseMailbox):
    """laoudo.com 邮箱服务"""
    def __init__(self, auth_token: str, email: str, account_id: str, api_url: str = ""):
        self.auth = auth_token
        self._email = email
        self._account_id = account_id
        self.api = (api_url or DEFAULT_LAOUDO_API_URL).rstrip("/")
        self._ua = "Mozilla/5.0"

    def get_email(self) -> MailboxAccount:
        return MailboxAccount(
            email=self._email,
            account_id=self._account_id,
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "laoudo",
                    "login_identifier": self._email,
                    "display_name": self._email,
                    "credentials": {
                        "authorization": self.auth,
                    },
                    "metadata": {
                        "account_id": self._account_id,
                        "email": self._email,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "laoudo",
                    "resource_type": "mailbox",
                    "resource_identifier": self._account_id,
                    "handle": self._email,
                    "display_name": self._email,
                    "metadata": {
                        "account_id": self._account_id,
                        "email": self._email,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        from curl_cffi import requests as curl_requests
        try:
            r = curl_requests.get(
                f"{self.api}/list",
                params={"accountId": account.account_id, "allReceive": 0,
                        "emailId": 0, "timeSort": 1, "size": 50, "type": 0},
                headers={"authorization": self.auth, "user-agent": self._ua},
                timeout=15, impersonate="chrome131"
            )
            if r.status_code == 200:
                mails = r.json().get("data", {}).get("list", []) or []
                return {m.get("id") or m.get("emailId") for m in mails if m.get("id") or m.get("emailId")}
        except Exception:
            pass
        return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "trae",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re, time
        from curl_cffi import requests as curl_requests
        seen = set(before_ids) if before_ids else set()
        start = time.time()
        h = {"authorization": self.auth, "user-agent": self._ua}
        while time.time() - start < timeout:
            try:
                r = curl_requests.get(
                    f"{self.api}/list",
                    params={"accountId": account.account_id, "allReceive": 0,
                            "emailId": 0, "timeSort": 1, "size": 50, "type": 0},
                    headers=h, timeout=15, impersonate="chrome131"
                )
                if r.status_code == 200:
                    mails = r.json().get("data", {}).get("list", []) or []
                    for mail in mails:
                        mid = mail.get("id") or mail.get("emailId")
                        if not mid or mid in seen:
                            continue
                        seen.add(mid)
                        text = (str(mail.get("subject", "")) + " " +
                                str(mail.get("content") or mail.get("html") or ""))
                        if keyword and keyword.lower() not in text.lower():
                            continue
                        m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', text)
                        if m:
                            return m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
            time.sleep(4)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time
        from curl_cffi import requests as curl_requests
        seen = set(before_ids or [])
        start = time.time()
        headers = {"authorization": self.auth, "user-agent": self._ua}
        while time.time() - start < timeout:
            try:
                r = curl_requests.get(
                    f"{self.api}/list",
                    params={"accountId": account.account_id, "allReceive": 0,
                            "emailId": 0, "timeSort": 1, "size": 50, "type": 0},
                    headers=headers, timeout=15, impersonate="chrome131"
                )
                if r.status_code == 200:
                    mails = r.json().get("data", {}).get("list", []) or []
                    for mail in mails:
                        mid = mail.get("id") or mail.get("emailId")
                        if not mid or mid in seen:
                            continue
                        seen.add(mid)
                        text = (str(mail.get("subject", "")) + " " +
                                str(mail.get("content") or mail.get("html") or ""))
                        link = _extract_verification_link(text, keyword)
                        if link:
                            return link
            except Exception:
                pass
            time.sleep(4)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class AitreMailbox(BaseMailbox):
    """mail.aitre.cc 临时邮箱"""
    def __init__(self, email: str, api_url: str = ""):
        self._email = email
        self.api = (api_url or DEFAULT_AITRE_API_URL).rstrip("/")

    def get_email(self) -> MailboxAccount:
        return MailboxAccount(email=self._email)

    def get_current_ids(self, account: MailboxAccount) -> set:
        import requests
        try:
            r = requests.get(f"{self.api}/emails", params={"email": account.email}, timeout=10)
            emails = r.json().get("emails", [])
            return {str(m["id"]) for m in emails if "id" in m}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "trae",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re, time, requests
        seen = set(before_ids) if before_ids else set()
        last_check = None
        start = time.time()
        while time.time() - start < timeout:
            params = {"email": account.email}
            if last_check:
                params["lastCheck"] = last_check
            try:
                r = requests.get(f"{self.api}/poll", params=params, timeout=10)
                data = r.json()
                last_check = data.get("lastChecked")
                if data.get("count", 0) > 0:
                    r2 = requests.get(f"{self.api}/emails", params={"email": account.email}, timeout=10)
                    for mail in r2.json().get("emails", []):
                        mid = str(mail.get("id", ""))
                        if mid in seen:
                            continue
                        seen.add(mid)
                        text = mail.get("preview", "") + mail.get("content", "")
                        if keyword and keyword.lower() not in text.lower():
                            continue
                        m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', text)
                        if m:
                            return m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time, requests
        seen = set(before_ids or [])
        last_check = None
        start = time.time()
        while time.time() - start < timeout:
            params = {"email": account.email}
            if last_check:
                params["lastCheck"] = last_check
            try:
                r = requests.get(f"{self.api}/poll", params=params, timeout=10)
                data = r.json()
                last_check = data.get("lastChecked")
                if data.get("count", 0) > 0:
                    r2 = requests.get(f"{self.api}/emails", params={"email": account.email}, timeout=10)
                    for mail in r2.json().get("emails", []):
                        mid = str(mail.get("id", ""))
                        if mid in seen:
                            continue
                        seen.add(mid)
                        text = str(mail.get("preview", "")) + " " + str(mail.get("content", ""))
                        link = _extract_verification_link(text, keyword)
                        if link:
                            return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class TempMailLolMailbox(BaseMailbox):
    """tempmail.lol 免费临时邮箱（无需注册，自动生成）"""

    def __init__(self, proxy: str = None, api_url: str = ""):
        self.api = (api_url or DEFAULT_TEMPMAIL_LOL_API_URL).rstrip("/")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._token = None
        self._email = None

    def get_email(self) -> MailboxAccount:
        import requests
        r = requests.post(f"{self.api}/inbox/create",
            json={},
            proxies=self.proxy, timeout=15)
        data = r.json()
        self._email = data.get("address") or data.get("email", "")
        self._token = data.get("token", "")
        return MailboxAccount(
            email=self._email,
            account_id=self._token,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "tempmail_lol",
                    "resource_type": "mailbox",
                    "resource_identifier": self._token,
                    "handle": self._email,
                    "display_name": self._email,
                    "metadata": {
                        "email": self._email,
                        "token": self._token,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        import requests
        try:
            r = requests.get(f"{self.api}/inbox",
                params={"token": account.account_id},
                proxies=self.proxy, timeout=10)
            return {str(m["id"]) for m in r.json().get("emails", [])}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re, time, requests
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.api}/inbox",
                    params={"token": account.account_id},
                    proxies=self.proxy, timeout=10)
                for mail in sorted(r.json().get("emails", []), key=lambda x: x.get("date", 0), reverse=True):
                    mid = str(mail.get("id", ""))
                    if mid in seen:
                        continue
                    seen.add(mid)
                    text = mail.get("subject", "") + " " + mail.get("body", "") + " " + mail.get("html", "")
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', text)
                    if m:
                        return m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time, requests
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.api}/inbox",
                    params={"token": account.account_id},
                    proxies=self.proxy, timeout=10)
                for mail in sorted(r.json().get("emails", []), key=lambda x: x.get("date", 0), reverse=True):
                    mid = str(mail.get("id", ""))
                    if mid in seen:
                        continue
                    seen.add(mid)
                    text = str(mail.get("subject", "")) + " " + str(mail.get("body", "")) + " " + str(mail.get("html", ""))
                    link = _extract_verification_link(text, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class TempMailWebMailbox(BaseMailbox):
    """参考项目同款 Temp-Mail Web API。"""

    def __init__(self, base_url: str = "", proxy: str = None):
        self.base_url = _normalize_api_base_url(
            base_url,
            default=DEFAULT_TEMPMAIL_WEB_BASE_URL,
            label="Temp-Mail Web URL",
        )
        self.proxy = str(proxy or "").strip()
        self._accounts: dict[str, str] = {}
        self._executor = None
        self._browser = None
        self._page = None

    def _ensure_browser(self):
        if self._page is not None:
            return self._page
        from camoufox.sync_api import Camoufox

        launch_opts = {"headless": True}
        if self.proxy:
            parsed = urlparse(self.proxy)
            if parsed.scheme and parsed.hostname and parsed.port:
                proxy_config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
                if parsed.username:
                    proxy_config["username"] = parsed.username
                if parsed.password:
                    proxy_config["password"] = parsed.password
                launch_opts["proxy"] = proxy_config
            else:
                launch_opts["proxy"] = {"server": self.proxy}
            launch_opts["geoip"] = True
        self._browser = Camoufox(**launch_opts)
        browser = self._browser.__enter__()
        self._page = browser.new_page()
        self._page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        return self._page

    def _run_in_browser_thread(self, fn):
        from concurrent.futures import ThreadPoolExecutor

        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tempmail-web")
        future = self._executor.submit(fn)
        return future.result()

    @staticmethod
    def _decode_json_response(response: dict, action: str):
        import json

        status = int((response or {}).get("status", 0) or 0)
        text = str((response or {}).get("body", "") or "")
        if status != 200:
            raise RuntimeError(
                f"Temp-Mail Web {action} 失败: HTTP {status} {text[:300]}"
            )
        try:
            return json.loads(text)
        except Exception as exc:
            raise RuntimeError(
                f"Temp-Mail Web {action} 返回非 JSON: {exc}; body={text[:300]}"
            ) from exc

    def _request_json(self, method: str, path: str, *, auth_header: str = "") -> dict | list:
        import random
        import time

        target_url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        action = "创建邮箱" if path.lstrip("/") == "mailbox" else "拉取消息"
        max_attempts = 4 if path.lstrip("/") == "mailbox" else 2

        for attempt in range(1, max_attempts + 1):
            def _browser_call():
                page = self._ensure_browser()
                return page.evaluate(
                    """
                    async ({ targetUrl, method, authHeader, baseUrl }) => {
                      try {
                        const response = await fetch(targetUrl, {
                          method,
                          credentials: 'include',
                          referrer: baseUrl,
                          headers: {
                            'Accept': 'application/json',
                            ...(method === 'GET' ? { 'Cache-Control': 'no-cache' } : {}),
                            ...(authHeader ? { 'Authorization': authHeader } : {}),
                          },
                          ...(method === 'POST' ? { body: '{}' } : {}),
                        });
                        return {
                          status: response.status,
                          body: await response.text(),
                        };
                      } catch (error) {
                        return {
                          status: 0,
                          body: error instanceof Error ? error.message : String(error),
                        };
                      }
                    }
                    """,
                    {
                        "targetUrl": target_url,
                        "method": method,
                        "authHeader": auth_header,
                        "baseUrl": self.base_url,
                    },
                )

            result = self._run_in_browser_thread(_browser_call)
            status = int((result or {}).get("status", 0) or 0)
            if status != 429 or attempt >= max_attempts:
                return self._decode_json_response(result, action)
            wait_seconds = min(20, 3 * attempt + random.uniform(0.5, 2.5))
            print(f"[TempMailWeb] {action} 遇到 429，等待 {wait_seconds:.1f}s 后重试 ({attempt}/{max_attempts})")
            time.sleep(wait_seconds)

        return self._decode_json_response(result, action)

    def get_email(self) -> MailboxAccount:
        import json

        data = self._request_json("POST", "/mailbox")
        address = str(data.get("address") or data.get("mailbox") or data.get("email") or "").strip()
        token = str(data.get("token") or "").strip()
        if not address or not token:
            raise RuntimeError(f"Temp-Mail Web 创建邮箱失败: {json.dumps(data, ensure_ascii=False)[:300]}")
        self._accounts[address] = token
        print(f"[TempMailWeb] 生成邮箱: {address}")
        return MailboxAccount(
            email=address,
            account_id=token,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "tempmail_web",
                    "resource_type": "mailbox",
                    "resource_identifier": token,
                    "handle": address,
                    "display_name": address,
                    "metadata": {
                        "email": address,
                        "token": token,
                        "base_url": self.base_url,
                    },
                },
            },
        )

    def _fetch_messages(self, account: MailboxAccount) -> list[dict]:
        token = str(account.account_id or self._accounts.get(account.email) or "").strip()
        if not token:
            raise RuntimeError(f"Temp-Mail Web 缺少 token: {account.email}")
        data = self._request_json("GET", "/messages", auth_header=f"Bearer {token}")
        if isinstance(data, dict) and isinstance(data.get("messages"), list):
            return list(data.get("messages") or [])
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _message_id(message: dict) -> str:
        return str(
            message.get("id")
            or message.get("_id")
            or f"{message.get('createdAt', '')}:{message.get('subject', '')}"
        )

    @staticmethod
    def _extract_code(message: dict, code_pattern: str | None = None) -> str:
        subject = str(message.get("subject") or "").strip()
        if subject:
            last_token = subject.split()[-1]
            if re.fullmatch(r"\d{6}", last_token):
                return last_token
        text = " ".join(
            str(message.get(key) or "")
            for key in ("subject", "body", "text", "content", "html")
        )
        match = re.search(code_pattern or r"(?<!#)(?<!\d)(\d{6})(?!\d)", text)
        if not match:
            return ""
        return match.group(1) if match.groups() else match.group(0)

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            return {
                self._message_id(item)
                for item in self._fetch_messages(account)
                if self._message_id(item)
            }
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import time

        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                messages = self._fetch_messages(account)
                for item in messages:
                    mid = self._message_id(item)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = " ".join(
                        str(item.get(key) or "")
                        for key in ("subject", "body", "text", "content", "html")
                    )
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    code = self._extract_code(item, code_pattern=code_pattern)
                    if code:
                        print(f"[TempMailWeb] 收到验证码: {code}")
                        return code
            except Exception:
                pass
            time.sleep(5)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time

        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                messages = self._fetch_messages(account)
                for item in messages:
                    mid = self._message_id(item)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = " ".join(
                        str(item.get(key) or "")
                        for key in ("subject", "body", "text", "content", "html")
                    )
                    link = _extract_verification_link(text, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(5)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")

    def __del__(self):
        executor = getattr(self, "_executor", None)
        browser = getattr(self, "_browser", None)
        if executor is not None and browser is not None:
            try:
                executor.submit(browser.__exit__, None, None, None).result(timeout=5)
            except Exception:
                pass
        if executor is not None:
            try:
                executor.shutdown(wait=False, cancel_futures=False)
            except Exception:
                pass


class DuckMailMailbox(BaseMailbox):
    """DuckMail 自动生成邮箱（随机创建账号）"""

    def __init__(self, api_url: str = "",
                 provider_url: str = "",
                 bearer: str = "",
                 proxy: str = None):
        self.api = api_url.rstrip("/")
        self.provider_url = provider_url
        self.bearer = bearer
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._token = None
        self._address = None

    def _common_headers(self) -> dict:
        return {
            "authorization": f"Bearer {self.bearer}",
            "content-type": "application/json",
            "x-api-provider-base-url": self.provider_url,
        }

    def get_email(self) -> MailboxAccount:
        import requests, random, string
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = "Test" + "".join(random.choices(string.digits, k=8)) + "!"
        domain = self.provider_url.replace("https://api.", "").replace("https://", "")
        address = f"{username}@{domain}"
        # 创建账号
        r = insecure_request(requests.post, f"{self.api}/api/mail?endpoint=%2Faccounts",
            json={"address": address, "password": password},
            headers=self._common_headers(), proxies=self.proxy, timeout=15)
        data = r.json()
        self._address = data.get("address", address)
        # 登录获取 token
        r2 = insecure_request(requests.post, f"{self.api}/api/mail?endpoint=%2Ftoken",
            json={"address": self._address, "password": password},
            headers=self._common_headers(), proxies=self.proxy, timeout=15)
        self._token = r2.json().get("token", "")
        return MailboxAccount(
            email=self._address,
            account_id=self._token,
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "duckmail",
                    "login_identifier": self._address,
                    "display_name": self._address,
                    "credentials": {
                        "address": self._address,
                        "password": password,
                        "token": self._token,
                    },
                    "metadata": {
                        "provider_url": self.provider_url,
                        "api_url": self.api,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "duckmail",
                    "resource_type": "mailbox",
                    "resource_identifier": self._token,
                    "handle": self._address,
                    "display_name": self._address,
                    "metadata": {
                        "email": self._address,
                        "provider_url": self.provider_url,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        import requests
        try:
            r = insecure_request(requests.get, f"{self.api}/api/mail?endpoint=%2Fmessages%3Fpage%3D1",
                headers={"authorization": f"Bearer {account.account_id}",
                         "x-api-provider-base-url": self.provider_url},
                proxies=self.proxy, timeout=10)
            return {str(m["id"]) for m in r.json().get("hydra:member", [])}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re, time, requests
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = insecure_request(requests.get, f"{self.api}/api/mail?endpoint=%2Fmessages%3Fpage%3D1",
                    headers={"authorization": f"Bearer {account.account_id}",
                             "x-api-provider-base-url": self.provider_url},
                    proxies=self.proxy, timeout=10)
                msgs = r.json().get("hydra:member", [])
                for msg in msgs:
                    mid = str(msg.get("id") or msg.get("msgid") or "")
                    if mid in seen: continue
                    seen.add(mid)
                    # 请求邮件详情获取完整 text
                    try:
                        r2 = insecure_request(requests.get, f"{self.api}/api/mail?endpoint=%2Fmessages%2F{mid}",
                            headers={"authorization": f"Bearer {account.account_id}",
                                     "x-api-provider-base-url": self.provider_url},
                            proxies=self.proxy, timeout=10)
                        detail = r2.json()
                        body = str(detail.get("text") or "") + " " + str(detail.get("subject") or "")
                    except Exception:
                        body = str(msg.get("subject") or "")
                    body = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', body)
                    m = re.search(r"(?<!#)(?<!\d)(\d{6})(?!\d)", body)
                    if m: return m.group(1)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time, requests
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = insecure_request(requests.get, f"{self.api}/api/mail?endpoint=%2Fmessages%3Fpage%3D1",
                    headers={"authorization": f"Bearer {account.account_id}",
                             "x-api-provider-base-url": self.provider_url},
                    proxies=self.proxy, timeout=10)
                msgs = r.json().get("hydra:member", [])
                for msg in msgs:
                    mid = str(msg.get("id") or msg.get("msgid") or "")
                    if mid in seen:
                        continue
                    seen.add(mid)
                    try:
                        r2 = insecure_request(requests.get, f"{self.api}/api/mail?endpoint=%2Fmessages%2F{mid}",
                            headers={"authorization": f"Bearer {account.account_id}",
                                     "x-api-provider-base-url": self.provider_url},
                            proxies=self.proxy, timeout=10)
                        detail = r2.json()
                        body = str(detail.get("text") or "") + " " + str(detail.get("html") or "") + " " + str(detail.get("subject") or "")
                    except Exception:
                        body = str(msg.get("subject") or "")
                    link = _extract_verification_link(body, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class CFWorkerMailbox(BaseMailbox):
    """Cloudflare Worker 自建临时邮箱服务"""

    def __init__(self, api_url: str, admin_token: str = "", domain: str = "",
                 fingerprint: str = "", proxy: str = None):
        self.api = api_url.rstrip("/")
        self.admin_token = admin_token
        self.domain = domain
        self.fingerprint = fingerprint
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._token = None

    def _headers(self) -> dict:
        h = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "x-admin-auth": self.admin_token,
        }
        if self.fingerprint:
            h["x-fingerprint"] = self.fingerprint
        return h

    def get_email(self) -> MailboxAccount:
        import requests, random, string
        name = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        payload = {"enablePrefix": True, "name": name}
        if self.domain:
            payload["domain"] = self.domain
        r = requests.post(f"{self.api}/admin/new_address",
            json=payload, headers=self._headers(),
            proxies=self.proxy, timeout=15)
        print(f"[CFWorker] new_address status={r.status_code} resp={r.text[:200]}")
        data = r.json()
        email = data.get("email", data.get("address", ""))
        token = data.get("token", data.get("jwt", ""))
        self._token = token
        print(f"[CFWorker] 生成邮箱: {email} token={token[:40] if token else 'NONE'}...")
        return MailboxAccount(
            email=email,
            account_id=token,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "cfworker",
                    "resource_type": "mailbox",
                    "resource_identifier": token or email,
                    "handle": email,
                    "display_name": email,
                    "metadata": {
                        "email": email,
                        "token": token,
                        "api_url": self.api,
                        "domain": self.domain,
                    },
                },
            },
        )

    def _get_mails(self, email: str) -> list:
        import requests
        r = requests.get(f"{self.api}/admin/mails",
            params={"limit": 20, "offset": 0, "address": email},
            headers=self._headers(), proxies=self.proxy, timeout=10)
        data = r.json()
        return data.get("results", data) if isinstance(data, dict) else data

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            mails = self._get_mails(account.email)
            return {str(m.get("id", "")) for m in mails}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re, time
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                mails = self._get_mails(account.email)
                for mail in sorted(mails, key=lambda x: x.get("id", 0), reverse=True):
                    mid = str(mail.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    raw = str(mail.get("raw", ""))
                    # 1. 优先匹配 <span>XXXXXX</span> （Trae 邮件格式）
                    code_m = re.search(r'<span[^>]*>\s*(\d{6})\s*</span>', raw)
                    if code_m:
                        return code_m.group(1)
                    # 2. 跳过 MIME header，只搜 body 部分，避免匹配时间戳
                    body_start = raw.find('\r\n\r\n')
                    search_text = raw[body_start:] if body_start != -1 else raw
                    search_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', search_text)
                    # 排除时间戳模式 m=+XXXXXX. 和 t=XXXXXXXXXX
                    search_text = re.sub(r'm=\+\d+\.\d+', '', search_text)
                    search_text = re.sub(r'\bt=\d+\b', '', search_text)
                    m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', search_text)
                    if m:
                        return m.group(1) if m.groups() else m.group(0)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                mails = self._get_mails(account.email)
                for mail in sorted(mails, key=lambda x: x.get("id", 0), reverse=True):
                    mid = str(mail.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    raw = str(mail.get("raw", ""))
                    link = _extract_verification_link(raw, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class MoeMailMailbox(BaseMailbox):
    """MoeMail (sall.cc) 邮箱服务 - 自动注册账号并生成临时邮箱"""

    def __init__(
        self,
        api_url: str = "",
        username: str = "",
        password: str = "",
        session_token: str = "",
        proxy: str = None,
    ):
        self.api = _normalize_api_base_url(api_url, default="", label="MoeMail API URL")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._configured_username = str(username or "").strip()
        self._configured_password = str(password or "")
        self._configured_session_token = str(session_token or "").strip()
        self._session_token = self._configured_session_token or None
        self._email = None
        self._session = None
        self._username = self._configured_username
        self._password = self._configured_password

    def _new_session(self):
        import requests

        s = requests.Session()
        s.proxies = self.proxy
        mark_session_insecure(s)
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        s.headers.update({"user-agent": ua, "origin": self.api, "referer": f"{self.api}/zh-CN/login"})
        return s

    def _extract_session_token(self, session) -> str:
        for cookie in session.cookies:
            if "session-token" in cookie.name:
                return cookie.value
        return ""

    def _apply_session_token(self, session, token: str) -> None:
        domain = urlparse(self.api).hostname or ""
        cookie_names = [
            "__Secure-authjs.session-token",
            "authjs.session-token",
            "__Secure-next-auth.session-token",
            "next-auth.session-token",
        ]
        for name in cookie_names:
            session.cookies.set(name, token, domain=domain, path="/")
            session.cookies.set(name, token, path="/")

    def _login_with_existing_account(self) -> str:
        s = self._new_session()

        if self._configured_session_token:
            self._apply_session_token(s, self._configured_session_token)
            self._session = s
            self._session_token = self._configured_session_token
            print("[MoeMail] 使用已提供的 session-token")
            return self._configured_session_token

        if not (self._configured_username and self._configured_password):
            raise RuntimeError("MoeMail 未配置可复用账号，请提供用户名密码或 session-token")

        with suppress_insecure_request_warning():
            csrf_r = s.get(f"{self.api}/api/auth/csrf", timeout=10)
        csrf = csrf_r.json().get("csrfToken", "")
        with suppress_insecure_request_warning():
            login_resp = s.post(
                f"{self.api}/api/auth/callback/credentials",
                headers={"content-type": "application/x-www-form-urlencoded"},
                data=urlencode({
                    "username": self._configured_username,
                    "password": self._configured_password,
                    "csrfToken": csrf,
                    "redirect": "false",
                    "callbackUrl": self.api,
                }),
                allow_redirects=True,
                timeout=15,
            )
        self._session = s
        self._username = self._configured_username
        self._password = self._configured_password
        token = self._extract_session_token(s)
        if token:
            self._session_token = token
            print("[MoeMail] 使用手动注册账号登录成功")
            return token
        raise RuntimeError(
            f"MoeMail 登录失败: 已提供用户名密码，但未获取到 session-token (HTTP {login_resp.status_code})"
        )

    def _ensure_session(self) -> str:
        if self._session_token and self._session is not None:
            return self._session_token
        if self._configured_session_token or self._configured_username:
            return self._login_with_existing_account()
        return self._register_and_login()

    def _register_and_login(self) -> str:
        import random, string

        s = self._new_session()
        # 注册
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        password = "Test" + "".join(random.choices(string.digits, k=8)) + "!"
        self._username = username
        self._password = password
        print(f"[MoeMail] 注册账号: {username} / {password}")
        with suppress_insecure_request_warning():
            r_reg = s.post(f"{self.api}/api/auth/register",
                json={"username": username, "password": password, "turnstileToken": ""},
                timeout=15)
        print(f"[MoeMail] 注册结果: {r_reg.status_code} {r_reg.text[:80]}")
        if r_reg.status_code >= 400:
            try:
                register_error = r_reg.json().get("error") or r_reg.text
            except Exception:
                register_error = r_reg.text
            raise RuntimeError(f"MoeMail 注册失败: {str(register_error).strip() or f'HTTP {r_reg.status_code}'}")
        # 获取 CSRF
        with suppress_insecure_request_warning():
            csrf_r = s.get(f"{self.api}/api/auth/csrf", timeout=10)
        csrf = csrf_r.json().get("csrfToken", "")
        # 登录
        with suppress_insecure_request_warning():
            login_resp = s.post(f"{self.api}/api/auth/callback/credentials",
                headers={"content-type": "application/x-www-form-urlencoded"},
                data=urlencode({
                    "username": username,
                    "password": password,
                    "csrfToken": csrf,
                    "redirect": "false",
                    "callbackUrl": self.api,
                }),
                allow_redirects=True, timeout=15)
        self._session = s
        token = self._extract_session_token(s)
        if token:
            self._session_token = token
            print(f"[MoeMail] 登录成功")
            return token
        print(f"[MoeMail] 登录失败，cookies: {[c.name for c in s.cookies]}")
        raise RuntimeError(
            f"MoeMail 登录失败: 未获取到 session-token (HTTP {login_resp.status_code})"
        )

    # 优先用这些域名（信誉较好，不易被 AWS/Google 等拒绝）
    _PREFERRED_DOMAINS = ("sall.cc", "cnmlgb.de", "zhooo.org", "coolkid.icu")

    def get_email(self) -> MailboxAccount:
        self._session_token = self._configured_session_token or None
        self._session = None
        self._ensure_session()
        import random, string
        name = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        # 获取可用域名列表，优先选信誉好的域名，避免被 AWS 等平台拒绝
        domain = "sall.cc"
        try:
            with suppress_insecure_request_warning():
                cfg_r = self._session.get(f"{self.api}/api/config", timeout=10)
            all_domains = [d.strip() for d in cfg_r.json().get("emailDomains", "sall.cc").split(",") if d.strip()]
            if all_domains:
                # 从可用域名中筛选优先域名，按 _PREFERRED_DOMAINS 顺序选择
                preferred = [d for d in self._PREFERRED_DOMAINS if d in all_domains]
                if preferred:
                    domain = random.choice(preferred)
                else:
                    # 无优先域名可用，从剩余中随机选
                    domain = random.choice(all_domains)
        except Exception:
            pass
        with suppress_insecure_request_warning():
            r = self._session.post(f"{self.api}/api/emails/generate",
                json={"name": name, "domain": domain, "expiryTime": 86400000},
                timeout=15)
        data = r.json()
        self._email = data.get("email", data.get("address", ""))
        email_id = data.get("id", "")
        print(f"[MoeMail] 生成邮箱: {self._email} id={email_id} domain={domain} status={r.status_code}")
        if not email_id:
            print(f"[MoeMail] 生成失败: {data}")
            generate_error = data.get("error") or data.get("message") or r.text
            raise RuntimeError(f"MoeMail 生成邮箱失败: {str(generate_error).strip() or f'HTTP {r.status_code}'}")
        if not self._email:
            raise RuntimeError("MoeMail 生成邮箱失败: 返回结果缺少 email")
        self._email_count = getattr(self, '_email_count', 0) + 1
        return MailboxAccount(
            email=self._email,
            account_id=str(email_id),
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "moemail",
                    "login_identifier": getattr(self, "_username", ""),
                    "display_name": getattr(self, "_username", "") or self._email,
                    "credentials": {
                        "username": getattr(self, "_username", ""),
                        "password": getattr(self, "_password", ""),
                        "session_token": self._session_token,
                    },
                    "metadata": {
                        "api_url": self.api,
                        "email": self._email,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "moemail",
                    "resource_type": "mailbox",
                    "resource_identifier": str(email_id),
                    "handle": self._email,
                    "display_name": self._email,
                    "metadata": {
                        "email": self._email,
                        "api_url": self.api,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            with suppress_insecure_request_warning():
                r = self._session.get(f"{self.api}/api/emails/{account.account_id}", timeout=10)
            return {str(m.get("id", "")) for m in r.json().get("messages", [])}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        import re, time
        seen = set(before_ids or [])
        start = time.time()
        pattern = re.compile(code_pattern) if code_pattern else None
        while time.time() - start < timeout:
            try:
                with suppress_insecure_request_warning():
                    r = self._session.get(f"{self.api}/api/emails/{account.account_id}",
                        timeout=10)
                msgs = r.json().get("messages", [])
                for msg in msgs:
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen: continue
                    seen.add(mid)
                    body = str(msg.get("content") or msg.get("text") or msg.get("body") or msg.get("html") or "") + " " + str(msg.get("subject") or "")
                    body = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', body)
                    if pattern:
                        m = pattern.search(body)
                    else:
                        m = re.search(code_pattern or r'(?<!#)(?<!\d)(\d{6})(?!\d)', body)
                    if m: return m.group(1) if m.groups() else m.group(0) if code_pattern else m.group(1)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                with suppress_insecure_request_warning():
                    r = self._session.get(f"{self.api}/api/emails/{account.account_id}",
                        timeout=10)
                msgs = r.json().get("messages", [])
                for msg in msgs:
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    body = (
                        str(msg.get("content") or "") + " " +
                        str(msg.get("text") or "") + " " +
                        str(msg.get("body") or "") + " " +
                        str(msg.get("html") or "") + " " +
                        str(msg.get("subject") or "")
                    )
                    link = _extract_verification_link(body, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class FreemailMailbox(BaseMailbox):
    """
    Freemail 自建邮箱服务（基于 Cloudflare Worker）
    项目: https://github.com/idinging/freemail
    支持管理员令牌或账号密码两种认证方式
    """

    def __init__(self, api_url: str, admin_token: str = "",
                 username: str = "", password: str = "",
                 proxy: str = None):
        self.api = api_url.rstrip("/")
        self.admin_token = admin_token
        self.username = username
        self.password = password
        self.proxy = {"http": proxy, "https": proxy} if proxy else None
        self._session = None
        self._email = None

    def _get_session(self):
        import requests
        s = requests.Session()
        s.proxies = self.proxy
        if self.admin_token:
            s.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        elif self.username and self.password:
            s.post(f"{self.api}/api/login",
                json={"username": self.username, "password": self.password},
                timeout=15)
        self._session = s
        return s

    def get_email(self) -> MailboxAccount:
        if not self._session:
            self._get_session()
        import requests
        r = self._session.get(f"{self.api}/api/generate", timeout=15)
        data = r.json()
        email = data.get("email", "")
        self._email = email
        print(f"[Freemail] 生成邮箱: {email}")
        provider_account = {
            "provider_type": "mailbox",
            "provider_name": "freemail",
            "login_identifier": self.username or email,
            "display_name": self.username or email,
            "credentials": {},
            "metadata": {
                "api_url": self.api,
                "auth_mode": "admin_token" if self.admin_token else "username_password",
            },
        }
        if self.admin_token:
            provider_account["credentials"]["admin_token"] = self.admin_token
        if self.username:
            provider_account["credentials"]["username"] = self.username
        if self.password:
            provider_account["credentials"]["password"] = self.password
        return MailboxAccount(
            email=email,
            account_id=email,
            extra={
                "provider_account": provider_account,
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "freemail",
                    "resource_type": "mailbox",
                    "resource_identifier": email,
                    "handle": email,
                    "display_name": email,
                    "metadata": {
                        "email": email,
                        "api_url": self.api,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        try:
            r = self._session.get(f"{self.api}/api/emails",
                params={"mailbox": account.email, "limit": 50}, timeout=10)
            return {str(m["id"]) for m in r.json() if "id" in m}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re, time
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = self._session.get(f"{self.api}/api/emails",
                    params={"mailbox": account.email, "limit": 20}, timeout=10)
                for msg in r.json():
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen: continue
                    seen.add(mid)
                    # 直接用 verification_code 字段
                    code = str(msg.get("verification_code") or "")
                    if code and code != "None":
                        return code
                    # 兜底：从 preview 提取
                    text = str(msg.get("preview", "")) + " " + str(msg.get("subject", ""))
                    m = re.search(r"(?<!\d)(\d{6})(?!\d)", text)
                    if m: return m.group(1)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time
        seen = set(before_ids or [])
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = self._session.get(f"{self.api}/api/emails",
                    params={"mailbox": account.email, "limit": 20}, timeout=10)
                for msg in r.json():
                    mid = str(msg.get("id", ""))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = " ".join(
                        str(msg.get(key, ""))
                        for key in ("preview", "subject", "html", "text", "content", "body")
                    )
                    link = _extract_verification_link(text, keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class TestmailMailbox(BaseMailbox):
    """testmail.app 邮箱服务，地址格式为 {namespace}.{tag}@inbox.testmail.app。"""

    def __init__(
        self,
        api_url: str = "",
        api_key: str = "",
        namespace: str = "",
        tag_prefix: str = "",
        proxy: str = None,
    ):
        self.api = _normalize_api_base_url(api_url, default="", label="Testmail API URL")
        self.api_key = str(api_key or "").strip()
        self.namespace = str(namespace or "").strip()
        self.tag_prefix = str(tag_prefix or "").strip().strip(".")
        self.proxy = {"http": proxy, "https": proxy} if proxy else None

    def _assert_ready(self) -> None:
        if not self.api_key:
            raise RuntimeError("Testmail 未配置 API Key")
        if not self.namespace:
            raise RuntimeError("Testmail 未配置 namespace")

    def _build_tag(self) -> str:
        import random
        import string

        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"{self.tag_prefix}.{suffix}" if self.tag_prefix else suffix

    def _query_inbox(
        self,
        *,
        tag: str,
        timestamp_from: int | None,
        livequery: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        import requests

        params = {
            "apikey": self.api_key,
            "namespace": self.namespace,
            "tag": tag,
            "limit": limit,
        }
        if timestamp_from is not None:
            params["timestamp_from"] = int(timestamp_from)
        if livequery:
            params["livequery"] = "true"
        response = requests.get(self.api, params=params, proxies=self.proxy, timeout=15)
        payload = response.json()
        if payload.get("result") == "fail":
            raise RuntimeError(f"Testmail 查询失败: {payload.get('message') or response.text}")
        return payload.get("emails", []) or []

    @staticmethod
    def _message_id(mail: dict) -> str:
        return str(
            mail.get("id")
            or mail.get("message_id")
            or f"{mail.get('timestamp', '')}:{mail.get('tag', '')}:{mail.get('subject', '')}"
        )

    @staticmethod
    def _message_text(mail: dict) -> str:
        return " ".join(
            str(mail.get(key, "") or "")
            for key in ("subject", "text", "html")
        )

    def get_email(self) -> MailboxAccount:
        import time

        self._assert_ready()
        tag = self._build_tag()
        email = f"{self.namespace}.{tag}@inbox.testmail.app"
        created_at_ms = int(time.time() * 1000)
        return MailboxAccount(
            email=email,
            account_id=tag,
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "testmail",
                    "login_identifier": self.namespace,
                    "display_name": self.namespace,
                    "credentials": {
                        "api_key": self.api_key,
                    },
                    "metadata": {
                        "api_url": self.api,
                        "namespace": self.namespace,
                        "tag_prefix": self.tag_prefix,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "testmail",
                    "resource_type": "mailbox",
                    "resource_identifier": email,
                    "handle": email,
                    "display_name": email,
                    "metadata": {
                        "email": email,
                        "namespace": self.namespace,
                        "tag": tag,
                        "api_url": self.api,
                        "created_at_ms": created_at_ms,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        tag = str(account.account_id or "")
        if not tag:
            return set()
        started = ((account.extra or {}).get("provider_resource") or {}).get("metadata", {}).get("created_at_ms")
        try:
            mails = self._query_inbox(tag=tag, timestamp_from=started, limit=20)
            return {self._message_id(mail) for mail in mails if self._message_id(mail)}
        except Exception:
            return set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re
        import time

        tag = str(account.account_id or "")
        if not tag:
            raise RuntimeError("Testmail mailbox 缺少 tag")
        seen = set(before_ids or [])
        started = ((account.extra or {}).get("provider_resource") or {}).get("metadata", {}).get("created_at_ms")
        pattern = re.compile(code_pattern) if code_pattern else None
        start = time.time()
        while time.time() - start < timeout:
            try:
                mails = self._query_inbox(tag=tag, timestamp_from=started, limit=20)
                for mail in sorted(mails, key=lambda item: item.get("timestamp", 0), reverse=True):
                    mid = self._message_id(mail)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    text = self._message_text(mail)
                    if keyword and keyword.lower() not in text.lower():
                        continue
                    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
                    match = pattern.search(text) if pattern else re.search(r'(?<!#)(?<!\d)(\d{6})(?!\d)', text)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time

        tag = str(account.account_id or "")
        if not tag:
            raise RuntimeError("Testmail mailbox 缺少 tag")
        seen = set(before_ids or [])
        started = ((account.extra or {}).get("provider_resource") or {}).get("metadata", {}).get("created_at_ms")
        start = time.time()
        while time.time() - start < timeout:
            try:
                mails = self._query_inbox(tag=tag, timestamp_from=started, limit=20)
                for mail in sorted(mails, key=lambda item: item.get("timestamp", 0), reverse=True):
                    mid = self._message_id(mail)
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    link = _extract_verification_link(self._message_text(mail), keyword)
                    if link:
                        return link
            except Exception:
                pass
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class LuckMailMailbox(BaseMailbox):
    """LuckMail 第三方邮箱服务（通过创单拿邮箱并轮询验证码）。"""

    def __init__(
        self,
        api_url: str = "",
        api_key: str = "",
        project_code: str = "",
        email_type: str = "",
        domain: str = "",
        variant_mode: str = "",
        proxy: str = None,
    ):
        self.api = _normalize_api_base_url(api_url, default="", label="LuckMail API URL")
        self.api_key = str(api_key or "").strip()
        self.project_code = str(project_code or "").strip()
        self.email_type = str(email_type or "").strip()
        self.domain = str(domain or "").strip()
        self.variant_mode = str(variant_mode or "").strip()
        self.proxy = {"http": proxy, "https": proxy} if proxy else None

    def _assert_ready(self) -> None:
        if not self.api:
            raise RuntimeError("LuckMail 未配置 API 地址")
        if not self.api_key:
            raise RuntimeError("LuckMail 未配置 API Key")
        if not self.project_code:
            raise RuntimeError("LuckMail 未配置项目编码（project_code）")

    def _headers(self) -> dict:
        return {
            "accept": "application/json",
            "content-type": "application/json",
            # 与 SDK 对齐：X-API-Key
            "X-API-Key": self.api_key,
        }

    def _request(self, method: str, path: str, *, json_data: dict | None = None) -> dict:
        import requests

        url = f"{self.api}{path}"
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=self._headers(),
            json=json_data or {},
            proxies=self.proxy,
            timeout=20,
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"LuckMail 接口返回异常: {payload!r}")
        # 兼容多种返回格式：
        # 1) {"code": 0, "message": "...", "data": {...}}
        # 2) {"code": "success", "message": "success", "data": {...}}
        # 3) {"success": true, "message": "success", "data": {...}}
        # 4) 字段直接在顶层（无 data 包裹）
        code = payload.get("code", None)
        success_flag = payload.get("success", None)

        # 判断调用是否成功
        ok = True
        if code is not None:
            try:
                ok = int(code) == 0
            except (TypeError, ValueError):
                ok = str(code).strip().lower() in {"success", "ok", "true", "1"}
        elif success_flag is not None:
            ok = bool(success_flag)

        if not ok:
            raise RuntimeError(str(payload.get("message") or response.text or "LuckMail 请求失败"))

        # 提取实际业务数据：优先使用 data，其次使用顶层字段
        data = payload.get("data", None)
        if isinstance(data, dict):
            return dict(data)

        # data 可能为空或不存在：如果顶层就包含业务字段，直接返回顶层
        business_keys = {
            "order_no",
            "email_address",
            "status",
            "verification_code",
            "mail_from",
            "mail_subject",
            "mail_body_html",
        }
        if business_keys.intersection(set(payload.keys())):
            return dict(payload)

        # 兜底：data 为空时返回空 dict，让上层按状态继续轮询（避免直接抛异常）
        return dict(data or {})

    def _create_order(self) -> dict:
        body = {"project_code": self.project_code}
        if self.email_type:
            body["email_type"] = self.email_type
        if self.domain:
            body["domain"] = self.domain
        if self.variant_mode:
            body["variant_mode"] = self.variant_mode
        return self._request("POST", "/api/v1/openapi/order/create", json_data=body)

    def _get_order_code(self, order_no: str) -> dict:
        return self._request("GET", f"/api/v1/openapi/order/{order_no}/code")

    def get_email(self) -> MailboxAccount:
        self._assert_ready()
        data = self._create_order()
        order_no = str(data.get("order_no") or "").strip()
        email = str(data.get("email_address") or "").strip()
        if not order_no:
            raise RuntimeError("LuckMail 创建订单失败：缺少 order_no")
        if not email:
            raise RuntimeError("LuckMail 创建订单失败：缺少 email_address")
        return MailboxAccount(
            email=email,
            account_id=order_no,
            extra={
                "provider_account": {
                    "provider_type": "mailbox",
                    "provider_name": "luckmail",
                    "login_identifier": self.project_code,
                    "display_name": "LuckMail",
                    "credentials": {
                        "api_key": self.api_key,
                    },
                    "metadata": {
                        "api_url": self.api,
                        "project_code": self.project_code,
                        "email_type": self.email_type,
                        "domain": self.domain,
                    },
                },
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "luckmail",
                    "resource_type": "order",
                    "resource_identifier": order_no,
                    "handle": email,
                    "display_name": email,
                    "metadata": {
                        "email": email,
                        "order_no": order_no,
                        "project_code": self.project_code,
                    },
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        order_no = str(account.account_id or "").strip()
        return {order_no} if order_no else set()

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None, code_pattern: str = None) -> str:
        import re
        import time

        order_no = str(account.account_id or "").strip()
        if not order_no:
            raise RuntimeError("LuckMail 订单号为空，无法查询验证码")

        pattern = re.compile(code_pattern) if code_pattern else None
        start = time.time()
        last_status = None
        logged_any = False
        while time.time() - start < timeout:
            data = self._get_order_code(order_no)
            status_raw = data.get("status", data.get("state", None))
            status = str(status_raw or "").lower()

            # 尝试从多个字段名里直接拿 code
            verification_code = (
                data.get("verification_code")
                or data.get("verificationCode")
                or data.get("code")
                or data.get("mail_code")
                or ""
            )
            verification_code = str(verification_code or "").strip()

            # 组合可疑文本（尽量覆盖不同实现返回结构）
            extra_text = []
            for key in (
                "mail_subject",
                "mail_body_html",
                "mail_body_text",
                "mail_from",
                "verification_code",
                "verificationCode",
                "subject",
                "body",
                "html",
                "text",
            ):
                if data.get(key) is not None:
                    extra_text.append(str(data.get(key) or ""))
            # mail 结构可能嵌套在 data["mail"]
            mail_obj = data.get("mail", None)
            if isinstance(mail_obj, dict):
                for key in ("subject", "body_text", "body_html", "html_body", "from", "code", "verification_code", "verificationCode"):
                    if mail_obj.get(key) is not None:
                        extra_text.append(str(mail_obj.get(key) or ""))

            text = " ".join(extra_text)

            # 调试：状态变化时记录一次
            if status != last_status:
                last_status = status
                if status or not logged_any:
                    logged_any = True
                    print(f"[LuckMail] poll order={order_no[:10]}... status={status!r} code_present={bool(verification_code)}")

            # 1) 状态成功或 code 字段直接返回
            if status in {"success", "completed", "done", "ok"} or verification_code:
                if verification_code:
                    m = re.search(code_pattern or r"(?<!#)(?<!\d)(\d{6})(?!\d)", verification_code)
                    if m:
                        return m.group(1) if m.groups() else m.group(0)
                    # 如果 code_pattern 为空且 verification_code 本身就是纯数字，也直接返回
                    if re.fullmatch(r"\d{6}", verification_code):
                        return verification_code

                # 2) 从正文文本提取
                if code_pattern:
                    match = re.search(code_pattern, text)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
                match = re.search(r"(?<!#)(?<!\d)(\d{6})(?!\d)", text)
                if match:
                    return match.group(1)

            # 失败状态直接退出
            if status in {"cancelled", "timeout", "canceled"}:
                break

            # 关键词过滤：仅在 keyword 存在且目前还没提取到 code 时进行
            if keyword and keyword.lower() not in text.lower():
                time.sleep(3)
                continue

            time.sleep(3)
        raise TimeoutError(f"等待验证码超时 ({timeout}s)")

    def wait_for_link(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None) -> str:
        import time

        order_no = str(account.account_id or "").strip()
        if not order_no:
            raise RuntimeError("LuckMail 订单号为空，无法查询验证链接")

        start = time.time()
        while time.time() - start < timeout:
            data = self._get_order_code(order_no)
            status = str(data.get("status") or "").lower()
            text = " ".join(
                str(data.get(key) or "")
                for key in ("mail_subject", "mail_body_html", "mail_from")
            )
            link = _extract_verification_link(text, keyword)
            if link:
                return link
            if status in {"cancelled", "timeout"}:
                break
            time.sleep(3)
        raise TimeoutError(f"等待验证链接超时 ({timeout}s)")


class DDGEmailMailbox(BaseMailbox):
    """DuckDuckGo Email Protection — 生成 @duck.com 私密别名，通过 IMAP 从转发邮箱读取验证码"""

    DDG_API = "https://quack.duckduckgo.com/api/email/addresses"

    # 常见邮箱 IMAP 地址自动匹配
    _IMAP_HOSTS = {
        "163.com": "imap.163.com",
        "126.com": "imap.126.com",
        "qq.com": "imap.qq.com",
        "gmail.com": "imap.gmail.com",
        "outlook.com": "imap-mail.outlook.com",
        "hotmail.com": "imap-mail.outlook.com",
        "yahoo.com": "imap.mail.yahoo.com",
    }

    def __init__(self, bearer: str = "", imap_host: str = "",
                 imap_user: str = "", imap_pass: str = "", proxy: str = None):
        self.bearer = bearer
        self.imap_host = imap_host
        self.imap_user = imap_user
        self.imap_pass = imap_pass
        self.proxy = {"http": proxy, "https": proxy} if proxy else None

        # 自动推断 IMAP host
        if not self.imap_host and self.imap_user and "@" in self.imap_user:
            domain = self.imap_user.split("@", 1)[1].lower()
            self.imap_host = self._IMAP_HOSTS.get(domain, f"imap.{domain}")

    def _headers(self) -> dict:
        return {
            "authorization": f"Bearer {self.bearer}",
            "origin": "https://duckduckgo.com",
            "referer": "https://duckduckgo.com/",
        }

    def get_email(self) -> MailboxAccount:
        import requests
        r = insecure_request(
            requests.post, self.DDG_API,
            headers=self._headers(),
            proxies=self.proxy,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        address = data.get("address", "")
        if not address:
            raise RuntimeError(f"DDG Email 创建别名失败: {r.text[:200]}")
        email = f"{address}@duck.com"
        print(f"[DDG Email] 创建别名: {email}")
        return MailboxAccount(
            email=email,
            account_id=address,
            extra={
                "provider_resource": {
                    "provider_type": "mailbox",
                    "provider_name": "ddg_email",
                    "resource_type": "mailbox",
                    "resource_identifier": address,
                    "handle": email,
                    "display_name": email,
                },
            },
        )

    def get_current_ids(self, account: MailboxAccount) -> set:
        return set()

    def _imap_search_code(self, alias_email: str, timeout: int, code_pattern: str = None) -> str:
        import imaplib
        import email as email_lib
        import time

        if not self.imap_user or not self.imap_pass:
            raise RuntimeError("DDG Email 未配置 IMAP（ddg_imap_user / ddg_imap_pass），无法读取验证码")

        pattern = code_pattern or r'(?<!\d)(\d{6})(?!\d)'
        start = time.time()
        seen_ids: set[bytes] = set()
        baseline_done = False

        while time.time() - start < timeout:
            conn = None
            try:
                conn = imaplib.IMAP4_SSL(self.imap_host, 993, timeout=10)
                # 163/126 要求先发 ID 命令
                if any(h in self.imap_host for h in ("163.com", "126.com", "yeah.net")):
                    imaplib.Commands['ID'] = ('NONAUTH', 'AUTH', 'SELECTED')
                    conn._simple_command('ID', '("name" "IMAPClient" "version" "1.0")')
                conn.login(self.imap_user, self.imap_pass)
                conn.select("INBOX", readonly=True)

                _, msg_nums = conn.search(None, "ALL")
                ids = msg_nums[0].split() if msg_nums and msg_nums[0] else []

                # 首次轮询：把所有已有邮件标记为已读，只等新邮件
                if not baseline_done:
                    seen_ids = set(ids)
                    baseline_done = True
                    print(f"[DDG Email] IMAP baseline: {len(seen_ids)} existing emails skipped")
                    conn.logout()
                    conn = None
                    time.sleep(5)
                    continue

                for mid in reversed(ids[-30:]):
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)

                    _, msg_data = conn.fetch(mid, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)

                    # 检查是否是发给 alias 的（DDG 转发会保留原始 To）
                    to_addr = str(msg.get("To", "") or "").lower()
                    from_addr = str(msg.get("From", "") or "").lower()
                    subject = str(msg.get("Subject", "") or "")

                    # 只看发给 alias 或来自 openai/noreply 的
                    if alias_email.lower() not in to_addr and "openai" not in from_addr and "noreply" not in from_addr:
                        continue

                    # 提取正文
                    body_parts = []
                    if msg.is_multipart():
                        for part in msg.walk():
                            ct = part.get_content_type()
                            if ct in ("text/plain", "text/html"):
                                payload = part.get_payload(decode=True)
                                if payload:
                                    charset = part.get_content_charset() or "utf-8"
                                    body_parts.append(payload.decode(charset, errors="replace"))
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            charset = msg.get_content_charset() or "utf-8"
                            body_parts.append(payload.decode(charset, errors="replace"))

                    combined = subject + " " + " ".join(body_parts)
                    # 去掉 style/script 标签内容，避免匹配 CSS 颜色值如 #000000
                    combined = re.sub(r'<style[^>]*>.*?</style>', '', combined, flags=re.DOTALL | re.IGNORECASE)
                    combined = re.sub(r'<script[^>]*>.*?</script>', '', combined, flags=re.DOTALL | re.IGNORECASE)
                    combined = re.sub(r'<[^>]+>', ' ', combined)
                    m = re.search(pattern, combined)
                    if m:
                        code = m.group(1) if m.groups() else m.group(0)
                        print(f"[DDG Email] IMAP 获取验证码: {code}")
                        return code

                conn.logout()
            except (imaplib.IMAP4.error, OSError) as e:
                print(f"[DDG Email] IMAP 连接异常: {e}")
            finally:
                if conn:
                    try:
                        conn.logout()
                    except Exception:
                        pass
            time.sleep(5)

        raise TimeoutError(f"DDG Email IMAP 等待验证码超时 ({timeout}s)")

    def wait_for_code(self, account: MailboxAccount, keyword: str = "",
                      timeout: int = 120, before_ids: set = None,
                      code_pattern: str = None) -> str:
        return self._imap_search_code(account.email, timeout, code_pattern)
