"""共享的 OAuth 浏览器辅助（支持普通 Playwright / Chrome Profile / CDP）。"""
import time
from typing import Callable, Iterable, Optional

from playwright.sync_api import sync_playwright

from .base_identity import normalize_oauth_provider
from .browser_utils import build_proxy_config


OAUTH_PROVIDER_LABELS = {
    "google": "Google",
    "github": "GitHub",
    "linkedin": "LinkedIn",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "x": "X",
    "builderid": "Builder ID",
}

OAUTH_PROVIDER_HINTS = {
    "google": ("google", "google-oauth2"),
    "github": ("github",),
    "linkedin": ("linkedin", "linkedin-openid"),
    "microsoft": ("microsoft", "windowslive", "live"),
    "apple": ("apple",),
    "x": ("x", "twitter"),
    "builderid": ("builder id", "builderid", "aws builder id", "amazon q"),
}


def oauth_provider_label(provider: str) -> str:
    normalized = normalize_oauth_provider(provider)
    return OAUTH_PROVIDER_LABELS.get(normalized, normalized.title() if normalized else "")


def oauth_provider_hint_text(provider: str) -> str:
    label = oauth_provider_label(provider)
    if label:
        return label
    return "邮箱、Google、GitHub 等任一可用方式"


# backward-compat alias
browser_login_method_text = oauth_provider_hint_text


def finalize_oauth_email(actual_email: str, email_hint: str, platform_name: str) -> str:
    actual = (actual_email or "").strip()
    hint = (email_hint or "").strip()
    if actual and hint and actual.lower() != hint.lower():
        raise RuntimeError(
            f"{platform_name} OAuth 登录邮箱与预期不一致: 实际 {actual}，预期 {hint}"
        )
    resolved = actual or hint
    if not resolved:
        raise RuntimeError(
            f"{platform_name} OAuth 流程未识别到邮箱，请在任务里传入 email 或 oauth_email_hint"
        )
    return resolved


def _detect_running_chrome_cdp(ports: tuple = (9222, 9223, 9224)) -> str:
    """检测本机是否有 Chrome 开启了远程调试端口，返回 CDP URL 或空字符串。"""
    import urllib.request
    for port in ports:
        try:
            url = f"http://127.0.0.1:{port}/json/version"
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return f"http://127.0.0.1:{port}"
        except Exception:
            pass
    return ""


def _detect_chrome_user_data_dir() -> str:
    """自动检测系统 Chrome 用户数据目录。"""
    import os, sys
    if sys.platform == "darwin":
        path = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    elif sys.platform == "win32":
        path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
    else:
        path = os.path.expanduser("~/.config/google-chrome")
    return path if os.path.isdir(path) else ""


def _relaunch_chrome_with_debug_port(port: int = 9222) -> bool:
    """macOS: 关闭 Chrome 并用远程调试端口重启，成功返回 True。"""
    import subprocess, sys, time
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(["pkill", "-x", "Google Chrome"], capture_output=True)
        time.sleep(1.5)
        subprocess.Popen([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            f"--remote-debugging-port={port}",
            "--no-first-run",
        ])
        # wait for CDP to be ready
        import urllib.request
        for _ in range(20):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1):
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False
_GOOGLE_ACCOUNT_SELECTORS = [
    "[data-email]",
    ".JDAKTe",
    "[data-authuser]",
    ".account-name",
    "li[data-identifier]",
]


class OAuthBrowser:
    """全自动 OAuth 浏览器（支持普通 Playwright / Chrome Profile / CDP）。"""

    def __init__(
        self,
        *,
        proxy: Optional[str] = None,
        headless: bool = False,
        chrome_user_data_dir: str = "",
        chrome_cdp_url: str = "",
        log_fn: Callable[[str], None] = print,
    ):
        self.proxy = proxy
        self.headless = headless
        self.chrome_user_data_dir = chrome_user_data_dir
        self.chrome_cdp_url = chrome_cdp_url
        self.log = log_fn
        self._pw = None
        self.browser = None
        self.context = None
        self.page = None
        self._persistent = False  # launch_persistent_context path

    def __enter__(self):
        self._pw = sync_playwright().start()
        proxy_cfg = build_proxy_config(self.proxy)

        if self.chrome_cdp_url:
            # Connect to a running Chrome instance via CDP
            self.browser = self._pw.chromium.connect_over_cdp(self.chrome_cdp_url)
            self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
            pages = self.context.pages
            self.page = pages[0] if pages else self.context.new_page()
        elif self.chrome_user_data_dir:
            # Load user Chrome profile (carries Google/GitHub sessions)
            launch_kwargs = {
                "channel": "chrome",
                "headless": False,  # persistent context doesn't support headless
            }
            if proxy_cfg:
                launch_kwargs["proxy"] = proxy_cfg
            self.context = self._pw.chromium.launch_persistent_context(
                self.chrome_user_data_dir,
                **launch_kwargs,
            )
            self._persistent = True
            pages = self.context.pages
            self.page = pages[0] if pages else self.context.new_page()
        else:
            # Auto-detect system Chrome: try CDP first (Chrome already running),
            # then launch_persistent_context, then fallback to plain Chromium.
            cdp_url = _detect_running_chrome_cdp()
            if not cdp_url:
                # Try to relaunch Chrome with debug port
                user_data_dir = _detect_chrome_user_data_dir()
                if user_data_dir:
                    self.log("[OAuthBrowser] 正在重启 Chrome 并开启远程调试端口...")
                    if _relaunch_chrome_with_debug_port(9222):
                        cdp_url = "http://127.0.0.1:9222"
            if cdp_url:
                self.log(f"[OAuthBrowser] 连接已运行的 Chrome (CDP): {cdp_url}")
                self.browser = self._pw.chromium.connect_over_cdp(cdp_url)
                self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
                pages = self.context.pages
                self.page = pages[0] if pages else self.context.new_page()
            else:
                # Fallback: plain Playwright Chromium
                self.log("[OAuthBrowser] 未找到系统 Chrome，使用 Playwright Chromium")
                launch_kwargs = {"headless": self.headless}
                if proxy_cfg:
                    launch_kwargs["proxy"] = proxy_cfg
                self.browser = self._pw.chromium.launch(**launch_kwargs)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()

        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._persistent:
                if self.context:
                    self.context.close()
            else:
                try:
                    if self.context:
                        self.context.close()
                finally:
                    if self.browser:
                        self.browser.close()
        finally:
            if self._pw:
                self._pw.stop()

    def pages(self) -> list:
        if not self.context:
            return []
        pages = [page for page in self.context.pages if not page.is_closed()]
        return pages or ([self.page] if self.page else [])

    def active_page(self):
        pages = self.pages()
        return pages[-1] if pages else self.page

    def goto(self, url: str, *, wait_until: str = "networkidle", timeout: int = 30000) -> None:
        self.active_page().goto(url, wait_until=wait_until, timeout=timeout)

    def try_click_provider(self, provider: str) -> bool:
        provider = normalize_oauth_provider(provider)
        if not provider:
            return False
        page = self.active_page()
        label = oauth_provider_label(provider)
        hints = list(OAUTH_PROVIDER_HINTS.get(provider, (provider,)))
        try:
            clicked = page.evaluate(
                """
                ({hints, label}) => {
                    const nodes = Array.from(
                        document.querySelectorAll('button, a, [role="button"], input[type="submit"], input[type="button"]')
                    );
                    let best = null;
                    for (const node of nodes) {
                        if (!node || node.disabled) {
                            continue;
                        }
                        const text = [
                            node.innerText || '',
                            node.textContent || '',
                            node.value || '',
                            node.getAttribute('aria-label') || '',
                            node.getAttribute('name') || '',
                            node.getAttribute('value') || '',
                            node.getAttribute('data-provider') || '',
                            node.getAttribute('data-connection') || '',
                            node.getAttribute('href') || '',
                            node.getAttribute('title') || '',
                        ].join(' ').toLowerCase();
                        let score = 0;
                        if (text.includes(label.toLowerCase())) {
                            score += 3;
                        }
                        for (const hint of hints) {
                            if (hint && text.includes(hint.toLowerCase())) {
                                score += 2;
                            }
                        }
                        if (score <= 0) {
                            continue;
                        }
                        if (!best || score > best.score) {
                            best = { node, score };
                        }
                    }
                    if (!best) {
                        return false;
                    }
                    best.node.click();
                    return true;
                }
                """,
                {"hints": hints, "label": label},
            )
        except Exception:
            clicked = False
        return bool(clicked)

    def auto_select_google_account(self, timeout: int = 15) -> bool:
        """Google 账号选择器出现时自动点击第一个账号。
        适用于 Chrome Profile 模式：Google 已登录，弹出账号选择器。
        """
        deadline = time.time() + timeout
        selectors = ", ".join(_GOOGLE_ACCOUNT_SELECTORS)
        while time.time() < deadline:
            for page in self.pages():
                url = page.url or ""
                if "accounts.google.com" not in url:
                    continue
                try:
                    el = page.query_selector(selectors)
                    if el:
                        el.click()
                        self.log("[OAuthBrowser] Google 账号选择器：已自动点击第一个账号")
                        return True
                except Exception:
                    pass
            time.sleep(0.5)
        return False

    def wait_for_url(
        self,
        predicate: Callable[[str], bool],
        *,
        timeout: int = 300,
        interval: float = 1.0,
    ) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for page in self.pages():
                current_url = (page.url or "").strip()
                if current_url and predicate(current_url):
                    return current_url
            time.sleep(interval)
        return ""

    def wait_for_cookie_value(
        self,
        names: Iterable[str],
        *,
        timeout: int = 300,
        domain_substrings: Iterable[str] = (),
        interval: float = 1.0,
    ) -> str:
        deadline = time.time() + timeout
        wanted = {name.strip() for name in names if name}
        while time.time() < deadline:
            value = self.cookie_value(*wanted, domain_substrings=domain_substrings)
            if value:
                return value
            time.sleep(interval)
        return ""

    def cookies(self) -> list[dict]:
        return list(self.context.cookies()) if self.context else []

    def cookie_value(self, *names: str, domain_substrings: Iterable[str] = ()) -> str:
        wanted = {name for name in names if name}
        domain_filters = tuple(filter(None, domain_substrings))
        for cookie in self.cookies():
            if wanted and cookie.get("name") not in wanted:
                continue
            domain = cookie.get("domain", "")
            if domain_filters and not any(part in domain for part in domain_filters):
                continue
            return cookie.get("value", "")
        return ""

    def cookie_header(self, *, domain_substrings: Iterable[str] = ()) -> str:
        cookie_map = {}
        domain_filters = tuple(filter(None, domain_substrings))
        for cookie in self.cookies():
            domain = cookie.get("domain", "")
            if domain_filters and not any(part in domain for part in domain_filters):
                continue
            cookie_map[cookie.get("name", "")] = cookie.get("value", "")
        return "; ".join(f"{name}={value}" for name, value in cookie_map.items() if name)

    def cookie_dict(self, *, domain_substrings: Iterable[str] = ()) -> dict:
        cookie_map = {}
        domain_filters = tuple(filter(None, domain_substrings))
        for cookie in self.cookies():
            domain = cookie.get("domain", "")
            if domain_filters and not any(part in domain for part in domain_filters):
                continue
            cookie_map[cookie.get("name", "")] = cookie.get("value", "")
        return cookie_map


# Backward-compat alias
ManualOAuthBrowser = OAuthBrowser


def try_click_provider_on_page(page, provider: str) -> bool:
    """Standalone helper: click an OAuth provider button on any Playwright-compatible page."""
    provider = normalize_oauth_provider(provider)
    if not provider:
        return False
    label = oauth_provider_label(provider)
    hints = list(OAUTH_PROVIDER_HINTS.get(provider, (provider,)))
    try:
        clicked = page.evaluate(
            """
            ({hints, label}) => {
                const nodes = Array.from(
                    document.querySelectorAll('button, a, [role="button"], input[type="submit"], input[type="button"]')
                );
                let best = null;
                for (const node of nodes) {
                    if (!node || node.disabled) {
                        continue;
                    }
                    const text = [
                        node.innerText || '',
                        node.textContent || '',
                        node.value || '',
                        node.getAttribute('aria-label') || '',
                        node.getAttribute('name') || '',
                        node.getAttribute('value') || '',
                        node.getAttribute('data-provider') || '',
                        node.getAttribute('data-connection') || '',
                        node.getAttribute('href') || '',
                        node.getAttribute('title') || '',
                    ].join(' ').toLowerCase();
                    let score = 0;
                    if (text.includes(label.toLowerCase())) {
                        score += 3;
                    }
                    for (const hint of hints) {
                        if (hint && text.includes(hint.toLowerCase())) {
                            score += 2;
                        }
                    }
                    if (score <= 0) {
                        continue;
                    }
                    if (!best || score > best.score) {
                        best = { node, score };
                    }
                }
                if (!best) {
                    return false;
                }
                best.node.click();
                return true;
            }
            """,
            {"hints": hints, "label": label},
        )
    except Exception:
        clicked = False
    return bool(clicked)
